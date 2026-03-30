"""
Aplicativo de Previsão de Apostas NBA (Boxscores)
Mesma estrutura e padrão visual do betting_app.py, mas usando dados de boxscores.
Arquivo: betting_app_boxscores.py
"""

import os
import warnings
from datetime import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from automatic_model_monitor import AutomaticModelMonitor
from nba_injury_scraper import NBAInjuryScraper
from nba_prediction_model_boxscores_v2 import NBAPointsPredictorBoxscoresV2
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

st.set_page_config(page_title="Preditor de Apostas NBA - Boxscores", page_icon="🏀", layout="wide", initial_sidebar_state="expanded")

# CSS Customizado para aparência profissional (mesmo estilo do betting_app.py)
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
# FUNÇÕES AUXILIARES (copiadas do betting_app.py)
# ============================================================================

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "nba_player_boxscores_multi_season.csv")


def load_bets_csv():
    """Carrega histórico de apostas do CSV"""
    bets_file = "data/historico_apostas.csv"
    if os.path.exists(bets_file):
        try:
            bets_df = pd.read_csv(bets_file)
            expected_columns = [
                "Data",
                "Jogador",
                "Time",
                "Linha",
                "Odd",
                "Pts(Real)",
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
    bets_file = "data/historico_apostas.csv"

    bets_df = load_bets_csv()

    # Nova aposta
    new_bet = {
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Jogador": player_name,
        "Time": team_name,
        "Linha": f"{market_line:.1f}",
        "Odd": f"{odds:.2f}",
        "Pts(Real)": "",
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
    """Carrega ou treina o modelo de previsão (boxscores)"""
    data_path = DATA_PATH
    try:
        predictor = NBAPointsPredictorBoxscoresV2(data_path)
        predictor.train()
        return predictor
    except Exception as e:
        st.error(f"Erro ao carregar modelo: {e}")
        return None


def revalidate_model(predictor):
    """
    Revalida o modelo com validação cruzada e exibe relatório
    Retorna True se modelo passou, False caso contrário
    """
    try:
        from sklearn.model_selection import KFold, cross_val_score

        # Preparar dados
        X = predictor.X_scaled
        y = predictor.y

        if X is None or y is None:
            return False, "Dados de treinamento não disponíveis"

        # Validação cruzada
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        r2_scores = cross_val_score(predictor.model, X, y, cv=kf, scoring="r2")
        rmse_scores = -cross_val_score(predictor.model, X, y, cv=kf, scoring="neg_mean_squared_error")
        rmse_scores = [score**0.5 for score in rmse_scores]

        # Calculadora métricas
        r2_mean = r2_scores.mean()
        r2_std = r2_scores.std()
        rmse_mean = float(sum(rmse_scores)) / len(rmse_scores)
        rmse_std = (sum((x - rmse_mean) ** 2 for x in rmse_scores) / len(rmse_scores)) ** 0.5

        # Validar thresholds
        is_valid = r2_mean > 0.85 and rmse_mean < 3.0

        result = {
            "r2_mean": r2_mean,
            "r2_std": r2_std,
            "rmse_mean": rmse_mean,
            "rmse_std": rmse_std,
            "is_valid": is_valid,
        }

        return True, result

    except Exception as e:
        return False, f"Erro na revalidação: {str(e)[:100]}"


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
injury_check: dict[str, object] = {"status": "Disponível", "lesão": "", "aviso": False}
try:
    injury_check = check_player_injury_status(selected_player)
except Exception:
    injury_check = {"status": "Disponível", "lesão": "", "aviso": False}

if injury_check.get("aviso"):
    st.sidebar.error(f"⚠️ **{selected_player} INDISPONÍVEL**\n\n{injury_check.get('lesão', '')}")
elif str(injury_check.get("status", "")).lower() != "disponível":
    st.sidebar.warning(f"⚠️ {selected_player}: {injury_check.get('status', '')}")
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
default_minutes = 30
if selected_player in predictor.player_averages:
    default_minutes = int(predictor.player_averages[selected_player]["avg_min"])
expected_minutes = st.sidebar.slider("Minutos Esperados", min_value=0, max_value=40, value=default_minutes, help="Minutos estimados que o jogador vai jogar")

st.sidebar.divider()

# ============================================================================
# REVALIDAR MODELO
# ============================================================================

st.sidebar.subheader("🔄 Revalidação do Modelo")

st.sidebar.warning("""
⚠️ **Revalidar mensalmente ou a cada 500+ novos dados**

A validação cruzada detecta:
- Degradação de performance
- Sinais de overfitting
- Instabilidade do modelo

Recomendação: Executar a cada 30 dias
""")

if st.sidebar.button("🔬 Revalidar Modelo Agora", use_container_width=True, help="Executa validação cruzada (5-fold)"):
    with st.sidebar.status("Revalidando modelo...", expanded=True) as status:
        try:
            st.write("⏳ Iniciando validação cruzada...")
            success, result = revalidate_model(predictor)

            if success:
                st.write("✅ Validação concluída!")
                st.write(f"📊 R² Médio: {result['r2_mean']:.4f} (±{result['r2_std']:.4f})")
                st.write(f"📊 RMSE Médio: {result['rmse_mean']:.2f} (±{result['rmse_std']:.2f})")

                if result["is_valid"]:
                    status.update(label="✅ Modelo VÁLIDO - Em produção", state="complete")
                    st.success("✅ Modelo passou na validação!")
                else:
                    status.update(label="⚠️ Modelo requer atenção", state="error")
                    st.warning("⚠️ Modelo apresenta degradação - considere retreinar")
            else:
                status.update(label=f"❌ Erro: {result}", state="error")
                st.error(f"Erro na validação: {result}")

        except Exception as e:
            status.update(label="❌ Erro ao revalidar", state="error")
            st.error(f"Erro: {str(e)[:100]}")
else:
    st.sidebar.caption("Clique para verificar saúde do modelo")

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

st.title("Preditor de Apostas NBA PRO - Boxscores")
st.markdown("**Previsões de pontos de jogadores em tempo real com análise de EV+ (Boxscores)**")
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
        st.metric(label="Pontos Previstos", value=f"{prediction['predicted_points']:.2f}", delta=f"+/- {prediction['std_error']:.1f}")

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
        bet_button = st.button("REGISTRAR APOSTA", key="bet_button_boxscores", use_container_width=True)

    if bet_button:
        # Inicializar monitor automático
        auto_monitor = AutomaticModelMonitor()

        # Salvar aposta
        num_bets = save_bet(
            player_name=selected_player,
            team_name=predictor.player_averages[selected_player]["team"],
            market_line=market_line,
            odds=market_odds,
            ev_plus_pct=ev_analysis["ev_plus_pct"],
            model_win_pct=ev_analysis["model_probability"] * 100,
            bet_amount=bet_amount,
            bet_type=bet_type,
        )

        # Registrar no monitoramento automático
        auto_monitor.log_prediction(
            player_name=selected_player,
            predicted_pts=prediction["predicted_points"],
            actual_pts=predictor.player_averages[selected_player]["avg_pts"],  # Usa média histórica como referência
            confidence=ev_analysis["model_probability"],
        )

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
        player_df = player_df.sort_values("GAME_DATE")

        col1, col2 = st.columns(2)

        with col1:
            # Pontos por jogo (linha temporal)
            if len(player_df) > 0:
                # Criar agregação por season para visualização
                if "SEASON" in player_df.columns:
                    season_stats = player_df.groupby("SEASON").agg({"PTS": "mean", "MIN": "mean"}).reset_index()
                    season_stats.columns = ["SEASON", "PTS_mean", "MIN_mean"]
                    pts_chart = (
                        alt.Chart(season_stats).mark_line(point=True, color="#667eea").encode(x=alt.X("SEASON:N", title="Temporada"), y=alt.Y("PTS_mean:Q", title="Pontos Por Jogo"), tooltip=["SEASON", "PTS_mean", "MIN_mean"]).properties(title=f"{selected_player} - Tendência de Pontos Por Jogo", height=300, width=500)
                    )

                    # Adicionar linha de média
                    avg_pts = season_stats["PTS_mean"].mean()
                    avg_line = alt.Chart(pd.DataFrame({"avg": [avg_pts]})).mark_rule(color="red", strokeDash=[5, 5]).encode(y="avg:Q")

                    st.altair_chart(pts_chart + avg_line, use_container_width=True)
                else:
                    st.info("Dados de season não disponíveis")

        with col2:
            # Correlação de minutos
            if len(player_df) > 0 and "SEASON" in player_df.columns:
                season_stats = player_df.groupby("SEASON").agg({"PTS": "mean", "MIN": "mean"}).reset_index()
                season_stats.columns = ["SEASON", "PTS_mean", "MIN_mean"]
                min_chart = alt.Chart(season_stats).mark_area(color="#764ba2", opacity=0.3).encode(x=alt.X("SEASON:N", title="Temporada"), y=alt.Y("MIN_mean:Q", title="Minutos Por Jogo"), tooltip=["SEASON", "MIN_mean"]).properties(title=f"{selected_player} - Tendência de Minutos", height=300, width=500)
                st.altair_chart(min_chart, use_container_width=True)

        # Distribuição de pontos
        col1, col2 = st.columns([1, 1])

        with col1:
            if len(player_df) > 5:
                # Usar PTS direto (game-level data)
                dist_chart = alt.Chart(player_df).mark_bar(color="#00b894").encode(x=alt.X("PTS:Q", bin=alt.Bin(maxbins=15), title="Pontos"), y=alt.Y("count():Q", title="Frequência"), tooltip=["count()"]).properties(title=f"Distribuição de Pontos - {selected_player}", height=300, width=500)
                st.altair_chart(dist_chart, use_container_width=True)

        with col2:
            # Scatter Minutos vs Pontos
            if len(player_df) > 5:
                scatter = alt.Chart(player_df).mark_circle(size=100, color="#ff7f0e").encode(x=alt.X("MIN:Q", title="Minutos"), y=alt.Y("PTS:Q", title="Pontos"), tooltip=["GAME_DATE", "MIN", "PTS"]).properties(title="Correlação Minutos vs Pontos", height=300, width=500)

                # Adicionar linha de tendência
                valid_data = player_df[["MIN", "PTS"]].dropna()
                if len(valid_data) > 2:
                    z = np.polyfit(valid_data["MIN"], valid_data["PTS"], 1)
                    p = np.poly1d(z)
                    trend_df = pd.DataFrame({"MIN": np.linspace(valid_data["MIN"].min(), valid_data["MIN"].max(), 100)})
                    trend_df["PTS"] = p(trend_df["MIN"].values)

                    trend_line = alt.Chart(trend_df).mark_line(color="red", size=2).encode(x="MIN:Q", y="PTS:Q")

                    st.altair_chart(scatter + trend_line, use_container_width=True)
                else:
                    st.altair_chart(scatter, use_container_width=True)

    st.divider()

    # ========================================================================
    # COMPARAÇÃO COM PARES
    # ========================================================================

    st.subheader("Comparação com Pares (Mesma Posição)")

    peers = predictor.get_player_comparison(selected_player)

    if len(peers) > 0:
        peer_chart = alt.Chart(peers).mark_bar().encode(x=alt.X("Avg PTS:Q", title="Pontos Médios Por Jogo"), y=alt.Y("Player:N", sort="-x"), color=alt.value("#667eea"), tooltip=["Player", "Avg PTS", "Avg MIN"]).properties(title="Melhores Jogadores na Mesma Posição (por PPG)", height=400)

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
            key="bets_history_editor_boxscores",
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
            # ✅ Registrar Pts(Real) preenchidos no monitor automático
            auto_monitor = AutomaticModelMonitor()

            # Detectar quais linhas foram atualizadas com Pts(Real)
            for idx, row in edited_bets_df.iterrows():
                original_row = bets_df.iloc[idx] if idx < len(bets_df) else None

                # Se Pts(Real) foi preenchido (e não estava antes)
                if original_row is not None and str(row["Pts(Real)"]).strip() != "" and str(original_row["Pts(Real)"]).strip() == "":
                    try:
                        pts_real = float(str(row["Pts(Real)"]).replace(",", "."))
                        predicted_pts = float(str(row["Linha"]).replace(",", "."))  # Linha é o valor predito
                        player_name = str(row["Jogador"])
                        ev_plus = float(str(row["EV+%"]).replace("%", "").replace(",", "."))

                        # Registrar no monitor
                        auto_monitor.log_prediction(
                            player_name=player_name,
                            actual_pts=pts_real,
                            predicted_pts=predicted_pts,
                            confidence=0.85,  # Confiança padrão
                        )

                        st.success(f"✅ Predição registrada: {player_name} | Real: {pts_real:.1f} pts")
                    except Exception as e:
                        st.warning(f"Erro ao registrar predição: {e}")

            edited_bets_df = format_bets_df(edited_bets_df)
            edited_bets_df.to_csv("data/historico_apostas.csv", index=False, encoding="utf-8")
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
    st.header("📊 Monitoramento de Desempenho do Modelo - Boxscores")
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
        r2_status = "✅ BOM" if predictor.model_stats["r2"] > 0.80 else "⚠️ AVISO" if predictor.model_stats["r2"] > 0.75 else "❌ CRÍTICO"
        rmse_status = "✅ BOM" if predictor.model_stats["rmse"] < 3.5 else "⚠️ AVISO" if predictor.model_stats["rmse"] < 4.0 else "❌ CRÍTICO"
        mae_status = "✅ BOM" if predictor.model_stats["mae"] < 2.8 else "⚠️ AVISO" if predictor.model_stats["mae"] < 3.2 else "❌ CRÍTICO"

        st.info(f"""
        **Status Atual:**
        - R²: {r2_status}
        - RMSE: {rmse_status}
        - MAE: {mae_status}
        """)

    st.divider()

    # ========================================================================
    # MONITORAMENTO AUTOMÁTICO EM TEMPO REAL
    # ========================================================================

    st.subheader("🤖 Monitoramento Automático em Tempo Real")

    # ✅ FONTE ÚNICA DE VERDADE: Histórico de apostas com Pts(Real)
    bets_with_real = load_bets_csv()
    bets_with_real_filled = bets_with_real[(bets_with_real["Pts(Real)"].notna()) & (bets_with_real["Pts(Real)"].astype(str).str.strip() != "") & (bets_with_real["Pts(Real)"].astype(str).str.strip() != "-")].copy()

    # Calcular todas as métricas do CSV
    if len(bets_with_real_filled) > 0:
        bets_with_real_filled["actual"] = pd.to_numeric(bets_with_real_filled["Pts(Real)"].astype(str).str.replace(",", "."), errors="coerce")
        bets_with_real_filled["predicted"] = pd.to_numeric(bets_with_real_filled["Linha"].astype(str).str.replace(",", "."), errors="coerce")
        bets_with_real_filled["error"] = (bets_with_real_filled["actual"] - bets_with_real_filled["predicted"]).abs()
        bets_with_real_filled["is_accurate"] = bets_with_real_filled["Resultado"].str.lower() == "green"

        mae = bets_with_real_filled["error"].mean()
        rmse = np.sqrt((bets_with_real_filled["error"] ** 2).mean())
        accuracy = bets_with_real_filled["is_accurate"].mean() * 100
        total_predictions = len(bets_with_real_filled)
    else:
        mae = 0.0
        rmse = 0.0
        accuracy = 0.0
        total_predictions = 0

    # Mostrar métricas
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Predições Registradas",
            value=total_predictions,
            delta="Com Pts(Real)",
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="MAE (Pontos)",
            value=f"{mae:.2f} pts",
            delta="Erro médio",
            delta_color="inverse",
        )

    with col3:
        st.metric(
            label="Acurácia",
            value=f"{accuracy:.1f}%",
            delta="Taxa de acerto",
            delta_color="normal",
        )

    with col4:
        if accuracy >= 80:
            status = "✅ BOM"
        elif accuracy >= 60:
            status = "⚠️ AVISO"
        else:
            status = "❌ CRÍTICO"
        st.metric(label="Status", value=status, delta_color="normal")

    st.divider()

    # Predições recentes
    st.subheader("📋 Últimas Predições Registradas")

    if len(bets_with_real_filled) > 0:
        # Preparar dados para exibição
        bets_display = bets_with_real_filled.copy()
        bets_display["timestamp"] = pd.to_datetime(bets_display["Data"])
        bets_display["player"] = bets_display["Jogador"]
        bets_display["actual"] = pd.to_numeric(bets_display["Pts(Real)"].astype(str).str.replace(",", "."), errors="coerce")
        bets_display["predicted"] = pd.to_numeric(bets_display["Linha"].astype(str).str.replace(",", "."), errors="coerce")
        bets_display["error"] = (bets_display["actual"] - bets_display["predicted"]).abs()
        bets_display["confidence"] = 0.85
        bets_display["is_accurate"] = bets_display["Resultado"].str.lower() == "green"

        display_df = bets_display[["timestamp", "player", "actual", "predicted", "error", "confidence", "is_accurate"]].sort_values("timestamp", ascending=False).head(15).copy()
        display_df.columns = [
            "Data",
            "Jogador",
            "Real (pts)",
            "Previsto (pts)",
            "Erro (pts)",
            "Confiança",
            "Acertou",
        ]
        display_df["Data"] = pd.to_datetime(display_df["Data"]).dt.strftime("%d/%m %H:%M")
        display_df["Real (pts)"] = display_df["Real (pts)"].round(2)
        display_df["Previsto (pts)"] = display_df["Previsto (pts)"].round(2)
        display_df["Erro (pts)"] = display_df["Erro (pts)"].round(2)
        display_df["Confiança"] = (display_df["Confiança"] * 100).round(0).astype(int).astype(str) + "%"
        display_df["Acertou"] = display_df["Acertou"].map({True: "✅", False: "❌"})

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.success(f"✅ Mostrando **{len(display_df)}** predição(ões) com Pts(Real) registrado(s). Continue preenchendo Pts(Real) para suas apostas!")
    else:
        st.info("📝 Nenhuma predição com Pts(Real) preenchido ainda. \n\n**Como usar:**\n1. Faça uma previsão e registre uma aposta\n2. Ao final do jogo, preencha coluna 'Pts(Real)' no histórico de apostas\n3. A predição aparecerá aqui automaticamente")

    # Estatísticas diárias
    st.subheader("📊 Desempenho Diário (Últimos 7 dias)")

    if len(bets_with_real_filled) > 0:
        # Agrupar por data e calcular estatísticas
        bets_stats = bets_with_real_filled.copy()
        bets_stats["date"] = pd.to_datetime(bets_stats["Data"]).dt.date
        bets_stats["actual"] = pd.to_numeric(bets_stats["Pts(Real)"].astype(str).str.replace(",", "."), errors="coerce")
        bets_stats["predicted"] = pd.to_numeric(bets_stats["Linha"].astype(str).str.replace(",", "."), errors="coerce")
        bets_stats["error"] = (bets_stats["actual"] - bets_stats["predicted"]).abs()
        bets_stats["is_accurate"] = bets_stats["Resultado"].str.lower() == "green"

        daily_stats = (
            bets_stats.groupby("date")
            .agg(
                MAE=("error", "mean"),
                RMSE=("error", lambda x: np.sqrt((x**2).mean())),
                ACCURACY=("is_accurate", lambda x: x.mean() * 100),
                PREDICTIONS=("error", "count"),
            )
            .reset_index()
            .sort_values("date", ascending=False)
            .head(7)
        )

        st.dataframe(daily_stats, use_container_width=True, hide_index=True)

        # Gráfico de acurácia diária
        if not daily_stats.empty:
            chart = (
                alt.Chart(daily_stats)
                .mark_line(point=True, color="#667eea")
                .encode(
                    x=alt.X("date:T", title="Data"),
                    y=alt.Y("ACCURACY:Q", title="Acurácia (%)", scale=alt.Scale(domain=[0, 100])),
                    tooltip=["date", alt.Tooltip("ACCURACY:Q", format=".1f"), "PREDICTIONS"],
                )
                .properties(title="Tendência de Acurácia", height=300)
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("📝 Nenhum dado de desempenho diário disponível ainda.")

    st.divider()
    st.subheader("📈 Importância das Features")

    features_dict = predictor.model_stats.get("feature_importance", {})
    features_df = pd.DataFrame({"Feature": list(features_dict.keys()), "Importância": list(features_dict.values())}).sort_values("Importância", ascending=True) if features_dict else pd.DataFrame()

    col1, col2 = st.columns([1, 1])

    with col1:
        if not features_df.empty:
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
        if not features_df.empty:
            st.write("**Top 8 Features (Otimizadas):**")
            st.dataframe(features_df.sort_values("Importância", ascending=False).head(8), use_container_width=True)

    st.divider()

    # VALIDAÇÃO CRUZADA
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

    # HISTÓRICO & TENDÊNCIAS
    st.subheader("📊 Resumo de Desempenho")

    summary_data = {
        "Métrica": ["R² Score", "RMSE", "MAE", "Features", "Status"],
        "Atual": [
            f"{predictor.model_stats.get('r2', 0):.4f}",
            f"{predictor.model_stats.get('rmse', 0):.2f} pts",
            f"{predictor.model_stats.get('mae', 0):.2f} pts",
            f"{len(predictor.feature_cols) if hasattr(predictor, 'feature_cols') else 0} features",
            "Ativo",
        ],
        "Alvo": ["≥ 0.80", "< 3.5 pts", "< 2.8 pts", "24 features", "v2.1"],
        "Status": [
            "✅" if predictor.model_stats.get("r2", 0) >= 0.80 else "⚠️",
            "✅" if predictor.model_stats.get("rmse", 999) < 3.5 else "⚠️",
            "✅" if predictor.model_stats.get("mae", 999) < 2.8 else "⚠️",
            "✅" if hasattr(predictor, "feature_cols") and len(predictor.feature_cols) >= 20 else "ℹ️",
            "✅",
        ],
    }

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.divider()

    # ALERTAS E AVISOS
    st.subheader("🔔 Avisos de Monitoramento")

    alerts = []

    if predictor.model_stats.get("r2", 0) < 0.80:
        alerts.append(("⚠️", "R² abaixo de 0.80 - Verificar qualidade dos dados"))

    if predictor.model_stats.get("rmse", 0) > 3.8:
        alerts.append(("⚠️", f"RMSE elevado: {predictor.model_stats.get('rmse', 0):.2f} pts"))

    if predictor.model_stats.get("mae", 0) > 3.0:
        alerts.append(("⚠️", f"MAE elevado: {predictor.model_stats.get('mae', 0):.2f} pts"))

    if not (hasattr(predictor, "feature_cols") and len(predictor.feature_cols) == 8):
        alerts.append(("ℹ️", f"Modelo usando {len(predictor.feature_cols) if hasattr(predictor, 'feature_cols') else 0} features (otimizado: 8)"))

    if len(alerts) == 0:
        st.success("✅ Nenhum aviso no momento - Modelo operacional")
    else:
        for icon, message in alerts:
            st.warning(f"{icon} {message}")

    st.divider()

    # LOGS
    st.subheader("📋 Informações Técnicas")

    with st.expander("Ver Detalhes Técnicos"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Modelo:**")
            st.code(f"""
            Tipo: Linear Regression
            Features: {len(predictor.feature_cols) if hasattr(predictor, "feature_cols") else 0}
            Samples Treino: ~1000
            CV Strategy: 5-Fold
            """)

        with col2:
            st.write("**Features Utilizadas:**")
            st.code(", ".join(predictor.feature_cols) if hasattr(predictor, "feature_cols") else "n/a")

st.divider()
st.markdown("""
---
**Desenvolvido para apostadores sérios | v2.0**
""")
