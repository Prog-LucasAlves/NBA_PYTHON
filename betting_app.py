"""
Aplicativo de Previsão de Apostas NBA
Plataforma profissional de análise esportiva com calculadora de EV+
"""

import os
import warnings

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from nba_prediction_model import NBAPointsPredictor

warnings.filterwarnings("ignore")

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

st.sidebar.title("⚙️ Configuração")
st.sidebar.divider()

predictor = load_predictor()

if predictor is None:
    st.error("Falha ao carregar o modelo de previsão.")
    st.stop()

# Seleção de jogador com busca
st.sidebar.subheader("🏀 Seleção de Jogador")
all_players = sorted(predictor.player_averages.keys())
selected_player = st.sidebar.selectbox("Selecionar Jogador", options=all_players, help="Escolha um jogador da NBA para analisar")

# Parâmetros de apostas
st.sidebar.subheader("📊 Parâmetros de Apostas")
col1, col2 = st.sidebar.columns(2)
with col1:
    market_line = st.number_input("Linha de Mercado (O/U)", min_value=0.0, max_value=100.0, value=25.5, step=0.5, help="Linha Over/Under da casa de apostas")

with col2:
    market_odds = st.number_input("Odds Decimais", min_value=1.01, max_value=10.0, value=1.95, step=0.05, help="Odds decimais (1.95 = -105 US)")

# Minutos esperados
expected_minutes = st.sidebar.slider("Minutos Esperados", min_value=0, max_value=40, value=int(predictor.player_averages[selected_player]["avg_min"]), help="Minutos estimados que o jogador vai jogar")

st.sidebar.divider()
st.sidebar.info(f"""
📈 **Desempenho do Modelo**
- Score R²: {predictor.model_stats["r2"]:.4f}
- RMSE: {predictor.model_stats["rmse"]:.2f} pts
- MAE: {predictor.model_stats["mae"]:.2f} pts
""")

# ============================================================================
# PAINEL DE CONTROLE PRINCIPAL
# ============================================================================

st.title("🏀 Preditor de Apostas NBA PRO")
st.markdown("**Previsões de pontos de jogadores em tempo real com análise de EV+**")
st.divider()

# Obter previsão
prediction = predictor.predict_points(selected_player, minutes=expected_minutes)

if "error" in prediction:
    st.error(prediction["error"])
    st.stop()

# Obter cálculo de EV+
ev_analysis = predictor.calculate_ev_plus(prediction["predicted_points"], market_odds, market_line)

# ============================================================================
# LINHA DE MÉTRICAS SUPERIORES
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="🎯 Pontos Previstos", value=f"{prediction['predicted_points']}", delta=f"±{prediction['std_error']:.1f}")

with col2:
    st.metric(label="📈 Tendência", value=prediction["trend"], delta=f"{prediction['trend_pct']:+.1f}% vs Histórico", delta_color="inverse")

with col3:
    st.metric(label="⏱️ Minutos Médios", value=f"{prediction['minutes_used']:.1f}", delta="Média do jogador")

with col4:
    st.metric(label="🎲 R² do Modelo", value=f"{prediction['model_r2']:.3f}", delta=f"MAE: {prediction['model_mae']:.1f}")

st.divider()

# ============================================================================
# SEÇÃO DE ANÁLISE EV+
# ============================================================================

st.subheader("💰 Análise de Valor Esperado (EV+)")

# Escolher estilo de card baseado no sinal
if ev_analysis["ev_plus_pct"] > 5:
    card_class = "ev-card-positive"
elif ev_analysis["ev_plus_pct"] > 0:
    card_class = "ev-card-neutral"
else:
    card_class = "ev-card-negative"

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

# ============================================================================
# SEÇÃO DE DESEMPENHO DO JOGADOR
# ============================================================================

st.subheader("📊 Análise de Desempenho do Jogador")

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

# ============================================================================
# DADOS HISTÓRICOS E GRÁFICOS
# ============================================================================

st.subheader("📈 Desempenho Histórico")

# Obter dados históricos do jogador
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
        trend_df["PTS"] = trend_df["MIN"].apply(p)

        trend_line = alt.Chart(trend_df).mark_line(color="red", size=2).encode(x="MIN:Q", y="PTS:Q")

        st.altair_chart(scatter + trend_line, use_container_width=True)

st.divider()

# ============================================================================
# COMPARAÇÃO COM PARES
# ============================================================================

st.subheader("👥 Comparação com Pares (Mesma Posição)")

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

# ============================================================================
# IMPORTÂNCIA DE FEATURES
# ============================================================================

st.subheader("🎯 Importância das Features do Modelo")

features = predictor.model_stats["feature_importance"]
features_df = pd.DataFrame({"Feature": list(features.keys()), "Importância": list(features.values())}).sort_values("Importância", ascending=False)

importance_chart = alt.Chart(features_df).mark_barh().encode(x=alt.X("Importância:Q", title="Coeficiente Absoluto"), y=alt.Y("Feature:N", sort="-x"), color=alt.value("#764ba2")).properties(title="Importância das Features na Previsão de Pontos", height=300)

st.altair_chart(importance_chart, use_container_width=True)

# ============================================================================
# RODAPÉ
# ============================================================================

st.divider()
st.markdown("""
### ⚠️ Aviso Legal
Esta ferramenta é apenas para fins educacionais e de entretenimento.
Apostas esportivas envolvem risco. Por favor, jogue responsavelmente e apenas com dinheiro que pode perder.
Todas as previsões são baseadas em dados históricos e modelos de aprendizado de máquina, que não garantem resultados futuros.
""")

st.markdown("""
---
**Desenvolvido com ❤️ para apostadores sérios | v1.0**
""")
