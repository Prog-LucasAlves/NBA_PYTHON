"""
Aplicativo de Previsão de Apostas NBA
Plataforma profissional de análise esportiva com calculadora de EV+
"""

import os
import warnings
from datetime import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from nba_injury_scraper import NBAInjuryScraper
from nba_prediction_model import NBAPointsPredictor
from overfitting_monitor import OverfittingMonitor

warnings.filterwarnings("ignore")


def check_player_injury_status(player_name: str) -> dict:
    """Verifica se o jogador tem lesão registrada"""
    try:
        if not os.path.exists("nba_players_status.csv"):
            return {"status": "Disponível", "lesão": "", "aviso": False}

        df_status = pd.read_csv("nba_players_status.csv")
        player_data = df_status[df_status["Nome"].str.contains(player_name, case=False, na=False)]

        if len(player_data) == 0:
            return {"status": "Disponível", "lesão": "", "aviso": False}

        player_info = player_data.iloc[0]
        status = str(player_info.get("Status", "Disponível")).strip()
        lesao = str(player_info.get("Lesão", "")).strip()

        return {"status": status, "lesão": lesao, "aviso": status.lower() == "indisponível"}
    except Exception as e:
        print(f"Aviso: Erro ao verificar lesões: {e}")
        return {"status": "Disponível", "lesão": "", "aviso": False}


# ============================================================================
# CONFIGURAÇÃO DE PÁGINA E ESTILO
# ============================================================================

st.set_page_config(page_title="Preditor de Apostas NBA Pro", page_icon="🏀", layout="wide", initial_sidebar_state="expanded")

# CSS Customizado para aparência profissional
st.markdown(
    """
<style>
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #ff7f0e;
        --success-color: #2ca02c;
        --danger-color: #d62728;
    }

    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }

    .ev-card-positive {
        background: linear-gradient(135deg, #00b894 0%, #00a86b 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }

    .ev-card-negative {
        background: linear-gradient(135deg, #d63031 0%, #e17055 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }

    .ev-card-neutral {
        background: linear-gradient(135deg, #fdcb6e 0%, #f9ca24 100%);
        padding: 20px;
        border-radius: 10px;
        color: #333;
        margin: 10px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def load_bets_csv():
    """Carrega histórico de apostas do CSV"""
    bets_file = "historico_apostas.csv"
    if os.path.exists(bets_file):
        try:
            bets_df = pd.read_csv(bets_file)
            expected_columns = [
                "Data",
                "Jogador",
                "Time",
                "Linha",
                "Odd",
                "EV+%",
                "Vitória%",
                "Valor Aposta",
                "Tipo",
                "Resultado",
                "Lucro/Prejuízo",
                "Deletar",
            ]
            for column in expected_columns:
                if column not in bets_df.columns:
                    if column == "Deletar":
                        bets_df[column] = False
                    else:
                        bets_df[column] = "-" if column in {"Resultado", "Lucro/Prejuízo"} else ""

            # Normalizar formatação de EV+% e Vitória% para 2 casas decimais
            for col in ["EV+%", "Vitória%", "Odd"]:
                if col in bets_df.columns:
                    try:
                        bets_df[col] = pd.to_numeric(bets_df[col].astype(str).str.replace("%", "").str.replace(",", "."), errors="coerce")
                        bets_df[col] = bets_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
                    except Exception:
                        pass

            return bets_df[expected_columns]
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def format_bets_df(df):
    """Formata colunas de porcentagem e odds com 2 casas decimais"""
    df_formatted = df.copy()
    for col in ["EV+%", "Vitória%", "Odd"]:
        if col in df_formatted.columns:
            try:
                numeric_vals = pd.to_numeric(df_formatted[col].astype(str).str.replace("%", "").str.replace(",", "."), errors="coerce")
                df_formatted[col] = numeric_vals.apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
            except Exception:
                pass
    return df_formatted


def calculate_profit_loss(result, bet_amount, odds):
    """Calcula lucro/prejuízo com base no resultado da aposta."""
    if pd.isna(result):
        return "-"

    normalized_result = str(result).strip().lower()
    if normalized_result == "green":
        return f"R$ {bet_amount * (odds - 1):.2f}"
    if normalized_result == "red":
        return f"R$ {-bet_amount:.2f}"
    return "-"


def save_bet(player_name, team_name, market_line, odds, ev_plus_pct, model_win_pct, bet_amount, bet_type):
    """Salva uma aposta no CSV"""
    bets_file = "historico_apostas.csv"

    bets_df = load_bets_csv()

    # Nova aposta
    new_bet = {
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Jogador": player_name,
        "Time": team_name,
        "Linha": f"{market_line:.1f}",
        "Odd": f"{odds:.2f}",
        "EV+%": f"{ev_plus_pct:.2f}",
        "Vitória%": f"{model_win_pct:.2f}",
        "Valor Aposta": f"R$ {bet_amount:.2f}",
        "Tipo": bet_type,
        "Resultado": "-",
        "Lucro/Prejuízo": "-",
        "Deletar": False,
    }

    bets_df = pd.concat([bets_df, pd.DataFrame([new_bet])], ignore_index=True)
    bets_df = format_bets_df(bets_df)
    bets_df.to_csv(bets_file, index=False, encoding="utf-8")

    return len(bets_df)


# ============================================================================
# CARREGAMENTO EM CACHE E DADOS
# ============================================================================


@st.cache_resource
def load_predictor():
    """Carrega ou treina o modelo de previsão"""
    data_path = os.path.join(os.path.dirname(__file__), "data", "nba_player_stats_multi_season.csv")
    try:
        predictor = NBAPointsPredictor(data_path)
        predictor.train()
        return predictor
    except Exception as e:
        st.error(f"Erro ao carregar modelo: {e}")
        return None


# ============================================================================
# BARRA LATERAL - FILTROS E CONFIGURAÇÃO
# ============================================================================

st.sidebar.title("Configuração")
st.sidebar.divider()

predictor = load_predictor()

if predictor is None:
    st.error("Falha ao carregar o modelo de previsão.")
    st.stop()

# Seleção de jogador com busca
st.sidebar.subheader("Seleção de Jogador")
all_players = sorted(predictor.player_averages.keys())
selected_player = st.sidebar.selectbox("Selecionar Jogador", options=all_players, help="Escolha um jogador da NBA para analisar")

# ✅ VERIFICAR LESÕES
injury_check = check_player_injury_status(selected_player)
if injury_check["aviso"]:
    st.sidebar.error(f"⚠️ **{selected_player} INDISPONÍVEL**\n\n{injury_check['lesão']}")
elif injury_check["status"].lower() != "disponível":
    st.sidebar.warning(f"⚠️ {selected_player}: {injury_check['status']}")
else:
    st.sidebar.success(f"✅ {selected_player} - Disponível")

# Parâmetros de apostas
st.sidebar.subheader("Parâmetros de Apostas")
col1, col2 = st.sidebar.columns(2)
with col1:
    market_line = st.number_input("Linha de Mercado (O/U)", min_value=0.0, max_value=100.0, value=25.5, step=0.5, help="Linha Over/Under da casa de apostas")

with col2:
    market_odds = st.number_input("Odds Decimais", min_value=1.0, max_value=10.0, value=1.95, step=0.01, help="Odds decimais (ex: 1.60, 1.61, 1.62)")

# Minutos esperados
expected_minutes = st.sidebar.slider("Minutos Esperados", min_value=0, max_value=40, value=int(predictor.player_averages[selected_player]["avg_min"]), help="Minutos estimados que o jogador vai jogar")

st.sidebar.divider()
st.sidebar.info(f"""
Desempenho do Modelo
- Score R2: {predictor.model_stats["r2"]:.4f}
- RMSE: {predictor.model_stats["rmse"]:.2f} pts
- MAE: {predictor.model_stats["mae"]:.2f} pts
""")

# ============================================================================
# ATUALIZAR LESÕES
# ============================================================================

st.sidebar.divider()
st.sidebar.subheader("🏥 Atualizar Lesões")

if st.sidebar.button("🔄 Atualizar Lista de Lesões", use_container_width=True, help="Scraping em tempo real de lesões no ESPN"):
    with st.sidebar.status("Atualizando lesões...", expanded=True) as status:
        try:
            st.write("⏳ Iniciando scraper de lesões...")
            scraper = NBAInjuryScraper()

            st.write("📍 Coletando dados do ESPN...")
            injuries = scraper.get_injuries_data()
            st.write(f"✅ Coletadas {len(injuries)} lesões")

            st.write("📝 Atualizando CSV de jogadores...")
            df_updated = scraper.update_players_csv()

            if df_updated is not None:
                injured_count = len(df_updated[df_updated["Status"] == "Indisponível"])
                available_count = len(df_updated) - injured_count

                st.write("✅ CSV atualizado com sucesso!")
                st.write(f"📊 Total: {len(df_updated)} jogadores")
                st.write(f"❌ Indisponíveis: {injured_count}")
                st.write(f"✅ Disponíveis: {available_count}")

                status.update(label="✅ Lesões atualizadas com sucesso!", state="complete")

                # Recarregar a página para refletir mudanças
                st.success("✨ Dados atualizados! Recarregando aplicação...")
                st.rerun()
            else:
                status.update(label="⚠️ Falha ao atualizar CSV", state="error")
                st.warning("Falha ao atualizar CSV de lesões")

        except Exception as e:
            status.update(label="❌ Erro ao atualizar lesões", state="error")
            st.error(f"Erro ao atualizar lesões: {str(e)[:100]}")
else:
    st.sidebar.caption("Clique para atualizar a lista de jogadores lesionados em tempo real")

# ============================================================================
# MAIN LAYOUT COM ABAS
# ============================================================================

st.title("Preditor de Apostas NBA PRO")
st.markdown("**Previsões de pontos de jogadores em tempo real com análise de EV+**")
st.divider()

# Criar abas
tab_predictor, tab_bets, tab_monitor = st.tabs(["Preditor de Apostas", "Historico de Apostas", "Monitoramento"])

# ============================================================================
# ABA 1: PREDITOR DE APOSTAS
# ============================================================================

with tab_predictor:
    # ✅ AVISO DE LESÃO NA SEÇÃO DE PREVISÃO
    injury_check = check_player_injury_status(selected_player)

    if injury_check["aviso"]:
        st.error(f"""
        ### ⚠️ JOGADOR INDISPONÍVEL

        **{selected_player}** está fora de ação por:

        **{injury_check["lesão"]}**

        ❌ **Não é possível fazer previsão para este jogador no momento.**
        """)
        st.stop()

    # Obter previsão
    prediction = predictor.predict_points(selected_player, minutes=expected_minutes)

    if "error" in prediction:
        st.error(prediction["error"])
        st.stop()

    # Obter cálculo de EV+
    ev_analysis = predictor.calculate_ev_plus(prediction["predicted_points"], market_odds, market_line)

    # ========================================================================
    # LINHA DE MÉTRICAS SUPERIORES
    # ========================================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="Pontos Previstos", value=f"{prediction['predicted_points']}", delta=f"+/- {prediction['std_error']:.1f}")

    with col2:
        st.metric(label="Tendência", value=prediction["trend"], delta=f"{prediction['trend_pct']:+.1f}% vs Histórico", delta_color="inverse")

    with col3:
        st.metric(label="Minutos Médios", value=f"{prediction['minutes_used']:.1f}", delta="Média do jogador")

    with col4:
        st.metric(label="R2 do Modelo", value=f"{prediction['model_r2']:.3f}", delta=f"MAE: {prediction['model_mae']:.1f}")

    st.divider()

    # ========================================================================
    # SEÇÃO DE ANÁLISE EV+
    # ========================================================================

    st.subheader("Análise de Valor Esperado (EV+)")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Valor EV+", value=f"{ev_analysis['ev_plus_pct']:+.2f}%", delta="ROI Esperado" if ev_analysis["ev_plus_pct"] > 0 else "EV Negativo")

    with col2:
        st.metric(label="Sinal", value=ev_analysis["signal"])

    with col3:
        st.metric(label="Recomendação", value=ev_analysis["recommendation"], delta=f"Odds: {market_odds}")

    # Detalhes de EV+
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Detalhes da Aposta**")
        st.dataframe(
            pd.DataFrame({"Métrica": ["Previsão", "Linha de Mercado", "Odds", "Percentual de Vitória do Modelo"], "Valor": [f"{ev_analysis['predicted_points']:.2f} pts", f"{ev_analysis['line']}", f"{ev_analysis['market_odds']}", f"{ev_analysis['model_probability'] * 100:.2f}%"]}),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.write("**Métricas de Valor**")
        st.dataframe(pd.DataFrame({"Métrica": ["EV+ %", "Critério de Kelly", "Percentual de Vitória Implícito"], "Valor": [f"{ev_analysis['ev_plus_pct']:+.2f}%", f"{ev_analysis['kelly_criterion']:+.4f}", f"{ev_analysis['implied_probability'] * 100:.2f}%"]}), use_container_width=True, hide_index=True)

    st.divider()

    # ========================================================================
    # SEÇÃO DE APOSTAS
    # ========================================================================

    st.subheader("Registrar Aposta")

    col1, col2, col3 = st.columns(3)

    with col1:
        bet_amount = st.number_input("Valor da Aposta (R$)", min_value=1.0, max_value=10000.0, value=100.0, step=1.0)

    with col2:
        # Determinar tipo de aposta baseado em EV+
        bet_type = st.selectbox("Tipo de Aposta", options=["Over"], index=0)

    with col3:
        st.write("")
        st.write("")
        bet_button = st.button("REGISTRAR APOSTA", key="bet_button", use_container_width=True)

    if bet_button:
        # Salvar aposta
        num_bets = save_bet(player_name=selected_player, team_name=predictor.player_averages[selected_player]["team"], market_line=market_line, odds=market_odds, ev_plus_pct=ev_analysis["ev_plus_pct"], model_win_pct=ev_analysis["model_probability"] * 100, bet_amount=bet_amount, bet_type=bet_type)

        st.success(f"Aposta registrada com sucesso! Total de apostas: {num_bets}")
        st.balloons()

    st.divider()

    # ========================================================================
    # SEÇÃO DE DESEMPENHO DO JOGADOR
    # ========================================================================

    st.subheader("Análise de Desempenho do Jogador")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Médias de Temporada**")
        player_stats = predictor.player_averages[selected_player]
        stats_df = pd.DataFrame(
            {"Estatística": ["Pontos Médios", "Minutos Médios", "Posição", "Time", "Última Temporada", "Temporadas nos Dados"], "Valor": [f"{player_stats['avg_pts']:.2f}", f"{player_stats['avg_min']:.2f}", player_stats["position"], player_stats["team"], player_stats["last_season"], f"{player_stats['seasons']}"]},
        )
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    with col2:
        st.write("**Recente vs Histórico**")
        comparison_df = pd.DataFrame({"Período": ["Últimos 10 Jogos", "Histórico", "Diferença"], "Pontos Médios": [f"{prediction['recent_avg']:.2f}", f"{prediction['historical_avg']:.2f}", f"{prediction['recent_avg'] - prediction['historical_avg']:+.2f}"]})
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    st.divider()

    # ========================================================================
    # DADOS HISTÓRICOS E GRÁFICOS
    # ========================================================================

    st.subheader("Desempenho Histórico")

    # Obter dados históricos do jogador
    if predictor.df is not None:
        player_df = predictor.df[predictor.df["PLAYER_NAME"] == selected_player].copy()
        player_df = player_df.sort_values("SEASON")

        col1, col2 = st.columns(2)

        with col1:
            # Pontos por temporadas
            if len(player_df) > 0:
                pts_chart = alt.Chart(player_df).mark_line(point=True, color="#667eea").encode(x=alt.X("SEASON:N", title="Temporada"), y=alt.Y("PTS:Q", title="Pontos Por Jogo"), tooltip=["SEASON", "PTS", "MIN", "GP"]).properties(title=f"{selected_player} - Tendência de Pontos Por Jogo", height=300, width=500)

                # Adicionar linha de média
                avg_pts = player_df["PTS"].mean()
                avg_line = alt.Chart(pd.DataFrame({"avg": [avg_pts]})).mark_rule(color="red", strokeDash=[5, 5]).encode(y="avg:Q")

                st.altair_chart(pts_chart + avg_line, use_container_width=True)

        with col2:
            # Correlação de minutos
            if len(player_df) > 0:
                min_chart = alt.Chart(player_df).mark_area(color="#764ba2", opacity=0.3).encode(x=alt.X("SEASON:N", title="Temporada"), y=alt.Y("MIN:Q", title="Minutos Por Jogo"), tooltip=["SEASON", "MIN", "GP"]).properties(title=f"{selected_player} - Tendência de Minutos", height=300, width=500)
                st.altair_chart(min_chart, use_container_width=True)

        # Distribuição de pontos
        col1, col2 = st.columns([1, 1])

        with col1:
            if len(player_df) > 5:
                dist_chart = alt.Chart(player_df).mark_bar(color="#00b894").encode(x=alt.X("PTS:Q", bin=alt.Bin(maxbins=15), title="Pontos"), y=alt.Y("count():Q", title="Frequência"), tooltip=["count()"]).properties(title=f"Distribuição de Pontos - {selected_player}", height=300, width=500)
                st.altair_chart(dist_chart, use_container_width=True)

        with col2:
            # Scatter Minutos vs Pontos
            if len(player_df) > 5:
                scatter = alt.Chart(player_df).mark_circle(size=100, color="#ff7f0e").encode(x=alt.X("MIN:Q", title="Minutos"), y=alt.Y("PTS:Q", title="Pontos"), tooltip=["SEASON", "MIN", "PTS", "FG_PCT"]).properties(title="Correlação Minutos vs Pontos", height=300, width=500)

                # Adicionar linha de tendência
                z = np.polyfit(player_df["MIN"].dropna(), player_df["PTS"].dropna(), 1)
                p = np.poly1d(z)
                trend_df = pd.DataFrame({"MIN": np.linspace(player_df["MIN"].min(), player_df["MIN"].max(), 100)})
                trend_df["PTS"] = p(trend_df["MIN"].values)

                trend_line = alt.Chart(trend_df).mark_line(color="red", size=2).encode(x="MIN:Q", y="PTS:Q")

                st.altair_chart(scatter + trend_line, use_container_width=True)

    st.divider()

    # ========================================================================
    # COMPARAÇÃO COM PARES
    # ========================================================================

    st.subheader("Comparação com Pares (Mesma Posição)")

    peers = predictor.get_player_comparison(selected_player)

    if len(peers) > 0:
        # Destacar jogador selecionado
        peer_color = ["#667eea" if p == selected_player else "#e0e0e0" for p in peers["Player"]]

        peer_chart = alt.Chart(peers).mark_bar().encode(x=alt.X("Avg PTS:Q", title="Pontos Médios Por Jogo"), y=alt.Y("Player:N", sort="-x"), color=alt.value("#667eea"), tooltip=["Player", "Avg PTS", "Avg MIN", "FG%"]).properties(title="Melhores Jogadores na Mesma Posição (por PPG)", height=400)

        st.altair_chart(peer_chart, use_container_width=True)

        st.dataframe(peers, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum par comparável encontrado para este jogador.")

    st.divider()

    st.markdown("""
    ### Aviso Legal
    Esta ferramenta é apenas para fins educacionais e de entretenimento.
    Apostas esportivas envolvem risco. Por favor, jogue responsavelmente e apenas com dinheiro que pode perder.
    Todas as previsões são baseadas em dados históricos e modelos de aprendizado de máquina, que não garantem resultados futuros.
    """)

# ============================================================================
# ABA 2: HISTÓRICO DE APOSTAS
# ============================================================================

with tab_bets:
    st.subheader("Historico de Apostas Registradas")

    bets_df = load_bets_csv()

    if len(bets_df) > 0:
        editable_bets_df = bets_df.copy()
        editable_bets_df["Resultado"] = editable_bets_df["Resultado"].replace("-", "Pendente")

        edited_bets_df = st.data_editor(
            editable_bets_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Resultado": st.column_config.SelectboxColumn(
                    "Resultado",
                    options=["Pendente", "Green", "Red"],
                    required=True,
                ),
                "Lucro/Prejuízo": st.column_config.TextColumn(
                    "Lucro/Prejuízo",
                    disabled=True,
                ),
                "Odd": st.column_config.NumberColumn(
                    "Odd",
                    format="%.2f",
                ),
                "Deletar": st.column_config.CheckboxColumn(
                    "Deletar",
                ),
            },
            disabled=["Data", "Jogador", "Time", "Linha", "Odd", "EV+%", "Vitória%", "Valor Aposta", "Tipo", "Lucro/Prejuízo"],
            key="bets_history_editor",
        )

        editable_result = edited_bets_df["Resultado"].replace("Pendente", "-")
        odds_series = pd.to_numeric(edited_bets_df["Odd"].astype(str).str.replace(",", "."), errors="coerce")
        stake_series = pd.to_numeric(edited_bets_df["Valor Aposta"].astype(str).str.replace("R$ ", "", regex=False).str.replace(",", "."), errors="coerce")
        calculated_profit_loss = [calculate_profit_loss(result, bet_amount, odds) for result, bet_amount, odds in zip(editable_result, stake_series, odds_series, strict=False)]

        edited_bets_df["Resultado"] = editable_result
        edited_bets_df["Lucro/Prejuízo"] = calculated_profit_loss

        # Filtrar linhas marcadas para deletar
        rows_to_delete = edited_bets_df[edited_bets_df["Deletar"]].index
        if len(rows_to_delete) > 0:
            edited_bets_df = edited_bets_df.drop(rows_to_delete).reset_index(drop=True)
            st.warning(f"🗑️ {len(rows_to_delete)} aposta(s) removida(s)")

        if not edited_bets_df.equals(bets_df):
            edited_bets_df = format_bets_df(edited_bets_df)
            edited_bets_df.to_csv("historico_apostas.csv", index=False, encoding="utf-8")
            bets_df = edited_bets_df
            st.rerun()

        # Estatísticas
        st.divider()
        st.subheader("Estatísticas das Apostas")

        profit_loss_series = pd.to_numeric(
            bets_df["Lucro/Prejuízo"].astype(str).str.replace("R$ ", "", regex=False).str.replace(",", "."),
            errors="coerce",
        )
        total_value = pd.to_numeric(
            bets_df["Valor Aposta"].astype(str).str.replace("R$ ", "", regex=False).str.replace(",", "."),
            errors="coerce",
        ).sum()
        accumulated_profit = profit_loss_series.sum()
        roi = (accumulated_profit / total_value * 100) if total_value else 0.0
        average_odds = pd.to_numeric(bets_df["Odd"].astype(str).str.replace(",", "."), errors="coerce").mean()

        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

        with col1:
            st.metric("Total de Apostas", len(bets_df))

        with col2:
            green_bets = len(bets_df[bets_df["Resultado"] == "Green"])
            st.metric("Apostas GREEN", green_bets)

        with col3:
            red_bets = len(bets_df[bets_df["Resultado"] == "Red"])
            st.metric("Apostas RED", red_bets)

        with col4:
            st.metric("Valor Total Apostado", f"R$ {total_value:.2f}")

        with col5:
            st.metric("Acumulado", f"R$ {accumulated_profit:.2f}")

        with col6:
            st.metric("ROI", f"{roi:.2f}%")

        with col7:
            st.metric("Odd Média", f"{average_odds:.2f}")

        # Tabela de resumo por jogador
        st.divider()
        st.subheader("Resumo por Jogador")

        player_summary = (
            bets_df.groupby("Jogador").agg({"Tipo": "count", "Valor Aposta": lambda x: pd.to_numeric(x.astype(str).str.replace("R$ ", "").str.replace(",", "."), errors="coerce").sum(), "EV+%": lambda x: pd.to_numeric(x.astype(str).str.replace("%", ""), errors="coerce").mean()}).rename(columns={"Tipo": "Num Apostas"})
        )

        player_summary["Valor Total"] = player_summary["Valor Aposta"].apply(lambda x: f"R$ {x:.2f}")
        player_summary["EV+ Médio"] = player_summary["EV+%"].apply(lambda x: f"{x:.2f}%")

        st.dataframe(player_summary[["Num Apostas", "Valor Total", "EV+ Médio"]], use_container_width=True)

        # Botão para exportar
        csv_export = bets_df.to_csv(index=False, encoding="utf-8")
        st.download_button(label="Exportar como CSV", data=csv_export, file_name=f"apostas_nba_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")

    else:
        st.info("Nenhuma aposta registrada ainda. Vá para a aba 'Preditor de Apostas' para começar a registrar apostas!")

# ============================================================================
# ABA 3: MONITORAMENTO DE OVERFITTING
# ============================================================================

with tab_monitor:
    st.header("📊 Monitoramento de Desempenho do Modelo")
    st.markdown("Validação contínua contra overfitting e degradação de performance")

    st.divider()

    # ========================================================================
    # MÉTRICAS PRINCIPAIS
    # ========================================================================

    st.subheader("🎯 Desempenho Atual")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Score R²",
            value=f"{predictor.model_stats['r2']:.4f}",
            delta="Treino" if predictor.model_stats["r2"] > 0.85 else "Atenção",
            delta_color="normal" if predictor.model_stats["r2"] > 0.85 else "inverse",
        )

    with col2:
        st.metric(
            label="RMSE (Pontos)",
            value=f"{predictor.model_stats['rmse']:.2f}",
            delta="Erro" if predictor.model_stats["rmse"] < 3.0 else "Alto",
            delta_color="inverse",
        )

    with col3:
        st.metric(
            label="MAE (Pontos)",
            value=f"{predictor.model_stats['mae']:.2f}",
            delta="Bom" if predictor.model_stats["mae"] < 2.0 else "Regular",
            delta_color="normal",
        )

    with col4:
        st.metric(
            label="Features",
            value=f"{len(predictor.feature_cols)}",
            delta="Otimizado" if len(predictor.feature_cols) == 8 else "Legacy",
            delta_color="normal",
        )

    with col5:
        st.metric(
            label="Status",
            value="ATIVO",
            delta="v2.1" if len(predictor.feature_cols) == 8 else "v2.0",
            delta_color="normal",
        )

    st.divider()

    # ========================================================================
    # THRESHOLDS DE MONITORAMENTO
    # ========================================================================

    st.subheader("⚠️ Limites de Monitoramento")

    monitor = OverfittingMonitor()

    col1, col2 = st.columns(2)

    with col1:
        st.info("""
        **Limites Configurados:**
        - R² Gap Máximo: 0.0500
        - RMSE Máximo: 3.5 pts
        - R² Mínimo Teste: 0.8000
        - Desvio Padrão CV: 0.0300
        """)

    with col2:
        # Status do modelo
        r2_status = "✅ BOM" if predictor.model_stats["r2"] > 0.85 else "⚠️ AVISO" if predictor.model_stats["r2"] > 0.80 else "❌ CRÍTICO"
        rmse_status = "✅ BOM" if predictor.model_stats["rmse"] < 2.5 else "⚠️ AVISO" if predictor.model_stats["rmse"] < 3.0 else "❌ CRÍTICO"
        mae_status = "✅ BOM" if predictor.model_stats["mae"] < 1.8 else "⚠️ AVISO" if predictor.model_stats["mae"] < 2.2 else "❌ CRÍTICO"

        st.info(f"""
        **Status Atual:**
        - R²: {r2_status}
        - RMSE: {rmse_status}
        - MAE: {mae_status}
        """)

    st.divider()

    # ========================================================================
    # FEATURE IMPORTANCE
    # ========================================================================

    st.subheader("📈 Importância das Features")

    features_dict = predictor.model_stats["feature_importance"]
    features_df = pd.DataFrame({"Feature": list(features_dict.keys()), "Importância": list(features_dict.values())}).sort_values("Importância", ascending=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        # Gráfico de barras horizontal
        import altair as alt

        chart = (
            alt.Chart(features_df)
            .mark_bar(color="#667eea")
            .encode(
                y=alt.Y("Feature:N", sort="-x", title="Features"),
                x=alt.X("Importância:Q", title="Importância Relativa"),
                tooltip=["Feature", alt.Tooltip("Importância:Q", format=".4f")],
            )
            .properties(title="Importância das Features", height=400, width=400)
        )

        st.altair_chart(chart, use_container_width=True)

    with col2:
        st.write("**Top 8 Features (Otimizadas):**")
        st.dataframe(features_df.sort_values("Importância", ascending=False).head(8), use_container_width=True)

    st.divider()

    # ========================================================================
    # VALIDAÇÃO CRUZADA
    # ========================================================================

    st.subheader("🔄 Validação Cruzada (5-Fold)")

    col1, col2 = st.columns(2)

    with col1:
        st.info("""
        **Configuração:**
        - Estratégia: 5-Fold CV
        - Shuffle: True
        - Random State: 42

        **Objetivo:**
        Validar estabilidade do modelo
        em diferentes subconjuntos dos dados
        """)

    with col2:
        st.warning("""
        **Recomendações:**
        - Monitorar Gap R² < 0.05
        - Verificar variância entre folds
        - Revalidar com novos dados mensalmente
        - Alertar se Gap > 0.05 (overfitting)
        """)

    st.divider()

    # ========================================================================
    # HISTÓRICO & TENDÊNCIAS
    # ========================================================================

    st.subheader("📊 Resumo de Desempenho")

    summary_data = {
        "Métrica": ["R² Score", "RMSE", "MAE", "Features", "Status"],
        "Atual": [
            f"{predictor.model_stats['r2']:.4f}",
            f"{predictor.model_stats['rmse']:.2f} pts",
            f"{predictor.model_stats['mae']:.2f} pts",
            f"{len(predictor.feature_cols)} features",
            "Ativo",
        ],
        "Alvo": ["≥ 0.86", "< 2.5 pts", "< 1.8 pts", "8 features", "v2.1"],
        "Status": [
            "✅" if predictor.model_stats["r2"] >= 0.86 else "⚠️",
            "✅" if predictor.model_stats["rmse"] < 2.5 else "⚠️",
            "✅" if predictor.model_stats["mae"] < 1.8 else "⚠️",
            "✅" if len(predictor.feature_cols) == 8 else "ℹ️",
            "✅",
        ],
    }

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.divider()

    # ========================================================================
    # ALERTAS E AVISOS
    # ========================================================================

    st.subheader("🔔 Avisos de Monitoramento")

    alerts = []

    if predictor.model_stats["r2"] < 0.85:
        alerts.append(("⚠️", "R² abaixo de 0.85 - Verificar qualidade dos dados"))

    if predictor.model_stats["rmse"] > 2.8:
        alerts.append(("⚠️", f"RMSE elevado: {predictor.model_stats['rmse']:.2f} pts"))

    if predictor.model_stats["mae"] > 2.0:
        alerts.append(("⚠️", f"MAE elevado: {predictor.model_stats['mae']:.2f} pts"))

    if len(predictor.feature_cols) != 8:
        alerts.append(("ℹ️", f"Modelo usando {len(predictor.feature_cols)} features (otimizado: 8)"))

    if len(alerts) == 0:
        st.success("✅ Nenhum aviso no momento - Modelo operacional")
    else:
        for icon, message in alerts:
            st.warning(f"{icon} {message}")

    st.divider()

    # ========================================================================
    # LOGS
    # ========================================================================

    st.subheader("📋 Informações Técnicas")

    with st.expander("Ver Detalhes Técnicos"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Modelo:**")
            st.code(f"""
            Tipo: Linear Regression
            Features: {len(predictor.feature_cols)}
            Samples Treino: ~1000
            CV Strategy: 5-Fold
            """)

        with col2:
            st.write("**Features Utilizadas:**")
            st.code(", ".join(predictor.feature_cols))

st.divider()
st.markdown("""
---
**Desenvolvido para apostadores sérios | v2.0**
""")
