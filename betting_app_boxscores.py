"""
Aplicativo de Previsão de Apostas NBA (Boxscores)
Professional Fintech Dark Theme — v3.0 Redesigned
"""

import json
import os
import textwrap
import warnings
from datetime import datetime
from typing import Any, cast

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from automatic_model_monitor import AutomaticModelMonitor
from nba_injury_scraper import NBAInjuryScraper
from nba_prediction_model_boxscores_v2 import NBAPointsPredictorBoxscoresV2
from overfitting_monitor import OverfittingMonitor

warnings.filterwarnings("ignore")


# ============================================================================
# DESIGN SYSTEM — COLORS & TOKENS
# ============================================================================


class Theme:
    """Centralized design tokens for the fintech dark theme."""

    BG_PRIMARY = "#0b0f19"
    BG_CARD = "#111827"
    BG_CARD_ALT = "#0f1520"
    BG_ELEVATED = "#1a2332"
    BORDER = "rgba(0, 212, 170, 0.08)"
    BORDER_ACCENT = "rgba(0, 212, 170, 0.15)"
    ACCENT = "#00d4aa"
    ACCENT_2 = "#06b6d4"
    POSITIVE = "#10b981"
    NEGATIVE = "#ef4444"
    WARNING = "#f59e0b"
    INFO = "#38bdf8"
    TEXT_1 = "#f1f5f9"
    TEXT_2 = "#94a3b8"
    TEXT_3 = "#64748b"
    CHART_1 = "#00d4aa"
    CHART_2 = "#06b6d4"
    CHART_3 = "#f59e0b"
    CHART_4 = "#ef4444"
    CHART_5 = "#38bdf8"


# ============================================================================
# BUSINESS LOGIC — HELPER FUNCTIONS (unchanged)
# ============================================================================


def check_player_injury_status(player_name: str) -> dict:
    """Verifica se o jogador tem lesão registrada"""
    try:
        if not os.path.exists("data/nba_players_status.csv"):
            return {"status": "Disponível", "lesão": "", "aviso": False}

        df_status = pd.read_csv("data/nba_players_status.csv")
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


DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "nba_player_boxscores_multi_season.csv")
REVALIDATION_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "model_revalidation_history.json")


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


def load_revalidation_history() -> list[dict]:
    """Carrega histórico de revalidações do modelo."""
    if not os.path.exists(REVALIDATION_HISTORY_FILE):
        return []

    try:
        with open(REVALIDATION_HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_revalidation_history(history: list[dict]) -> None:
    """Salva histórico de revalidações do modelo."""
    try:
        with open(REVALIDATION_HISTORY_FILE, "w", encoding="utf-8") as file:
            json.dump(history[-20:], file, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Não foi possível salvar histórico de revalidação: {e}")


def append_revalidation_result(result: dict) -> None:
    """Adiciona um resultado de revalidação ao histórico persistido."""
    history = load_revalidation_history()
    history.append(result)
    save_revalidation_history(history)


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="NBA PRO Betting · Boxscores",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# COMPREHENSIVE CSS — FINTECH DARK THEME
# ============================================================================

st.markdown(
    f"""
<style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ── ROOT VARS ── */
    :root {{
        --bg-0: {Theme.BG_PRIMARY};
        --bg-1: {Theme.BG_CARD};
        --bg-2: {Theme.BG_ELEVATED};
        --border: {Theme.BORDER};
        --border-accent: {Theme.BORDER_ACCENT};
        --accent: {Theme.ACCENT};
        --accent-2: {Theme.ACCENT_2};
        --positive: {Theme.POSITIVE};
        --negative: {Theme.NEGATIVE};
        --warning: {Theme.WARNING};
        --text-1: {Theme.TEXT_1};
        --text-2: {Theme.TEXT_2};
        --text-3: {Theme.TEXT_3};
    }}

    /* ── GLOBAL ── */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    .stApp {{
        background: var(--bg-0) !important;
    }}
    .block-container {{
        padding-top: 2rem !important;
        max-width: 1400px;
    }}

    /* ── TYPOGRAPHY ── */
    h1 {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        font-size: 1.8rem !important;
    }}
    h2, h3 {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
    }}
    p, span, li, div {{
        font-family: 'Inter', sans-serif !important;
    }}

    /* ── SIDEBAR ── */
    section[data-testid="stSidebar"] {{
        background: {Theme.BG_CARD_ALT} !important;
        border-right: 1px solid {Theme.BORDER} !important;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        font-size: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-2) !important;
        font-weight: 600 !important;
    }}
    section[data-testid="stSidebar"] .stDivider {{
        border-color: {Theme.BORDER} !important;
    }}

    /* ── TABS (pill-style) ── */
    .stTabs [data-baseweb="tab-list"] {{
        background: {Theme.BG_CARD} !important;
        border-radius: 14px !important;
        padding: 5px !important;
        gap: 4px !important;
        border: 1px solid {Theme.BORDER} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px !important;
        color: {Theme.TEXT_3} !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 10px 20px !important;
        letter-spacing: 0.01em;
        background: transparent !important;
        border: none !important;
        transition: all 0.25s ease !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {Theme.TEXT_1} !important;
        background: rgba(0, 212, 170, 0.06) !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {Theme.ACCENT}, {Theme.ACCENT_2}) !important;
        color: {Theme.BG_PRIMARY} !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 15px rgba(0, 212, 170, 0.25) !important;
    }}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {{
        display: none !important;
    }}

    /* ── METRICS ── */
    [data-testid="stMetric"] {{
        background: linear-gradient(145deg, {Theme.BG_CARD}, {Theme.BG_ELEVATED}) !important;
        border: 1px solid {Theme.BORDER} !important;
        border-radius: 14px !important;
        padding: 18px 22px !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }}
    [data-testid="stMetric"]:hover {{
        border-color: {Theme.BORDER_ACCENT} !important;
        box-shadow: 0 0 20px rgba(0, 212, 170, 0.06) !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: {Theme.TEXT_3} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        color: {Theme.TEXT_1} !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 0.75rem !important;
        font-weight: 500 !important;
    }}

    /* ── BUTTONS ── */
    .stButton > button {{
        background: linear-gradient(135deg, {Theme.ACCENT}, {Theme.ACCENT_2}) !important;
        color: {Theme.BG_PRIMARY} !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.02em;
        padding: 10px 24px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 2px 10px rgba(0, 212, 170, 0.15) !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(0, 212, 170, 0.3) !important;
    }}
    .stButton > button:active {{
        transform: translateY(0) !important;
    }}
    .stDownloadButton > button {{
        background: linear-gradient(135deg, {Theme.BG_ELEVATED}, {Theme.BG_CARD}) !important;
        color: {Theme.TEXT_1} !important;
        border: 1px solid {Theme.BORDER_ACCENT} !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }}
    .stDownloadButton > button:hover {{
        border-color: {Theme.ACCENT} !important;
        box-shadow: 0 4px 15px rgba(0, 212, 170, 0.15) !important;
    }}

    /* ── DATAFRAMES ── */
    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] > div {{
        border-radius: 12px !important;
        overflow: hidden;
    }}
    [data-testid="stDataFrame"] {{
        border: 1px solid {Theme.BORDER} !important;
    }}

    /* ── INPUTS ── */
    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input {{
        border-radius: 10px !important;
        border-color: rgba(0, 212, 170, 0.12) !important;
        transition: border-color 0.25s ease !important;
    }}
    .stSelectbox > div > div:focus-within,
    .stNumberInput > div > div > input:focus {{
        border-color: {Theme.ACCENT} !important;
        box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.1) !important;
    }}

    /* ── SLIDER ── */
    .stSlider [data-testid="stThumbValue"] {{
        color: {Theme.ACCENT} !important;
        font-weight: 700 !important;
    }}

    /* ── DIVIDER ── */
    .stDivider {{
        border-color: {Theme.BORDER} !important;
    }}
    hr {{
        border-color: rgba(0, 212, 170, 0.06) !important;
    }}

    /* ── EXPANDER ── */
    [data-testid="stExpander"] {{
        background: {Theme.BG_CARD} !important;
        border: 1px solid {Theme.BORDER} !important;
        border-radius: 12px !important;
    }}
    [data-testid="stExpander"]:hover {{
        border-color: {Theme.BORDER_ACCENT} !important;
    }}

    /* ── ALERTS ── */
    .stAlert {{
        border-radius: 12px !important;
        border: none !important;
    }}
    div[data-testid="stAlert"] {{
        border-radius: 12px !important;
    }}

    /* ── STATUS ── */
    [data-testid="stStatusWidget"] {{
        border-radius: 12px !important;
    }}

    /* ── CUSTOM COMPONENTS ── */
    .app-header {{
        padding: 8px 0 24px 0;
        border-bottom: 1px solid {Theme.BORDER};
        margin-bottom: 28px;
    }}
    .app-header-row {{
        display: flex;
        align-items: center;
        gap: 16px;
    }}
    .app-logo {{
        font-size: 2.4rem;
        line-height: 1;
    }}
    .app-title {{
        font-size: 1.8rem !important;
        font-weight: 900 !important;
        color: {Theme.TEXT_1} !important;
        margin: 0 !important;
        padding: 0 !important;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }}
    .app-badge {{
        display: inline-block;
        background: linear-gradient(135deg, {Theme.ACCENT}, {Theme.ACCENT_2});
        color: {Theme.BG_PRIMARY};
        font-size: 0.6rem;
        font-weight: 800;
        padding: 3px 10px;
        border-radius: 6px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-left: 4px;
        vertical-align: middle;
    }}
    .app-subtitle {{
        font-size: 0.9rem;
        color: {Theme.TEXT_3};
        margin-top: 6px;
        font-weight: 400;
    }}

    .section-hdr {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 36px 0 20px 0;
        padding-bottom: 14px;
        border-bottom: 1px solid {Theme.BORDER};
    }}
    .section-icon {{
        font-size: 1.4rem;
        line-height: 1;
    }}
    .section-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {Theme.TEXT_1};
        margin: 0;
    }}
    .section-sub {{
        font-size: 0.78rem;
        color: {Theme.TEXT_3};
        margin-top: 2px;
        font-weight: 400;
    }}

    .kpi-card {{
        background: linear-gradient(145deg, {Theme.BG_CARD}, {Theme.BG_ELEVATED});
        border: 1px solid {Theme.BORDER};
        border-radius: 16px;
        padding: 22px 20px;
        text-align: center;
        transition: all 0.3s ease;
    }}
    .kpi-card:hover {{
        border-color: {Theme.BORDER_ACCENT};
        box-shadow: 0 0 25px rgba(0, 212, 170, 0.06);
    }}
    .kpi-icon {{
        font-size: 1.3rem;
        margin-bottom: 6px;
    }}
    .kpi-label {{
        font-size: 0.68rem;
        color: {Theme.TEXT_3};
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600;
        margin-bottom: 8px;
    }}
    .kpi-value {{
        font-size: 1.7rem;
        font-weight: 800;
        color: {Theme.TEXT_1};
        line-height: 1.1;
    }}
    .kpi-delta {{
        font-size: 0.75rem;
        margin-top: 8px;
        font-weight: 500;
    }}

    .ev-hero {{
        border-radius: 20px;
        padding: 32px;
        text-align: center;
        border: 1px solid;
        position: relative;
        overflow: hidden;
    }}
    .ev-hero::before {{
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.02) 0%, transparent 70%);
        pointer-events: none;
    }}
    .ev-positive {{
        background: linear-gradient(145deg, rgba(16, 185, 129, 0.08), rgba(0, 212, 170, 0.04));
        border-color: rgba(16, 185, 129, 0.2);
    }}
    .ev-negative {{
        background: linear-gradient(145deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03));
        border-color: rgba(239, 68, 68, 0.2);
    }}
    .ev-neutral {{
        background: linear-gradient(145deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03));
        border-color: rgba(245, 158, 11, 0.2);
    }}
    .ev-value {{
        font-size: 3rem;
        font-weight: 900;
        line-height: 1;
        letter-spacing: -0.03em;
    }}
    .ev-positive .ev-value {{ color: {Theme.POSITIVE}; }}
    .ev-negative .ev-value {{ color: {Theme.NEGATIVE}; }}
    .ev-neutral .ev-value {{ color: {Theme.WARNING}; }}
    .ev-label {{
        font-size: 0.75rem;
        color: {Theme.TEXT_3};
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 600;
        margin-top: 8px;
    }}
    .ev-signal {{
        font-size: 1rem;
        font-weight: 700;
        margin-top: 12px;
    }}
    .ev-positive .ev-signal {{ color: {Theme.POSITIVE}; }}
    .ev-negative .ev-signal {{ color: {Theme.NEGATIVE}; }}
    .ev-neutral .ev-signal {{ color: {Theme.WARNING}; }}
    .ev-rec {{
        display: inline-block;
        padding: 6px 18px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-top: 16px;
        letter-spacing: 0.04em;
    }}
    .ev-positive .ev-rec {{
        background: rgba(16, 185, 129, 0.15);
        color: {Theme.POSITIVE};
    }}
    .ev-negative .ev-rec {{
        background: rgba(239, 68, 68, 0.15);
        color: {Theme.NEGATIVE};
    }}
    .ev-neutral .ev-rec {{
        background: rgba(245, 158, 11, 0.15);
        color: {Theme.WARNING};
    }}

    .edge-banner {{
        padding: 14px 20px;
        border-radius: 12px;
        font-size: 0.88rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 12px 0;
    }}
    .edge-ok {{
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: {Theme.POSITIVE};
    }}
    .edge-risk {{
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.2);
        color: {Theme.WARNING};
    }}

    .stat-row {{
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid rgba(0, 212, 170, 0.04);
        font-size: 0.88rem;
    }}
    .stat-row:last-child {{
        border-bottom: none;
    }}
    .stat-label {{
        color: {Theme.TEXT_3};
        font-weight: 500;
    }}
    .stat-value {{
        color: {Theme.TEXT_1};
        font-weight: 700;
    }}

    .monitor-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }}
    .badge-ok {{
        background: rgba(16, 185, 129, 0.12);
        color: {Theme.POSITIVE};
    }}
    .badge-warn {{
        background: rgba(245, 158, 11, 0.12);
        color: {Theme.WARNING};
    }}
    .badge-crit {{
        background: rgba(239, 68, 68, 0.12);
        color: {Theme.NEGATIVE};
    }}

    .info-card {{
        background: {Theme.BG_CARD};
        border: 1px solid {Theme.BORDER};
        border-radius: 14px;
        padding: 20px 24px;
    }}
    .info-card h4 {{
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {Theme.TEXT_3};
        margin-bottom: 14px;
        font-weight: 600;
    }}

    .footer {{
        text-align: center;
        color: {Theme.TEXT_3};
        font-size: 0.75rem;
        padding: 32px 0 16px 0;
        border-top: 1px solid {Theme.BORDER};
        margin-top: 48px;
    }}
    .footer span {{
        color: {Theme.ACCENT};
        font-weight: 700;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {Theme.BG_PRIMARY};
    }}
    ::-webkit-scrollbar-thumb {{
        background: rgba(0, 212, 170, 0.15);
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: rgba(0, 212, 170, 0.3);
    }}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================================
# ALTAIR DARK THEME
# ============================================================================


def _nba_dark_theme():
    return {
        "config": {
            "background": Theme.BG_CARD,
            "view": {"stroke": "transparent"},
            "title": {
                "color": Theme.TEXT_1,
                "font": "Inter",
                "fontSize": 14,
                "fontWeight": 700,
                "anchor": "start",
                "offset": 12,
            },
            "axis": {
                "labelColor": Theme.TEXT_3,
                "titleColor": Theme.TEXT_2,
                "gridColor": "rgba(0, 212, 170, 0.05)",
                "domainColor": "rgba(0, 212, 170, 0.1)",
                "tickColor": "rgba(0, 212, 170, 0.08)",
                "labelFont": "Inter",
                "titleFont": "Inter",
                "labelFontSize": 11,
                "titleFontSize": 12,
            },
            "legend": {
                "labelColor": Theme.TEXT_2,
                "titleColor": Theme.TEXT_1,
                "labelFont": "Inter",
                "titleFont": "Inter",
            },
            "range": {
                "category": [Theme.CHART_1, Theme.CHART_2, Theme.CHART_3, Theme.CHART_4, Theme.CHART_5],
            },
        },
    }


alt.themes.register("nba_dark", _nba_dark_theme)
alt.themes.enable("nba_dark")


# ============================================================================
# UI COMPONENT HELPERS
# ============================================================================


def _html(markup: str):
    """Render HTML in Streamlit, auto-stripping indentation to prevent code-block artifacts."""
    st.markdown(textwrap.dedent(markup), unsafe_allow_html=True)


def render_kpi(icon: str, label: str, value: str, delta: str = "", accent: str = "teal"):
    """Renders a custom KPI card."""
    accent_map = {
        "teal": Theme.ACCENT,
        "cyan": Theme.ACCENT_2,
        "green": Theme.POSITIVE,
        "red": Theme.NEGATIVE,
        "amber": Theme.WARNING,
        "blue": Theme.INFO,
    }
    color = accent_map.get(accent, Theme.ACCENT)
    _html(f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-delta" style="color: {color};">{delta}</div>
    </div>
    """)


def render_section(icon: str, title: str, subtitle: str = ""):
    """Renders a styled section header."""
    sub_html = f'<div class="section-sub">{subtitle}</div>' if subtitle else ""
    _html(f"""
    <div class="section-hdr">
        <span class="section-icon">{icon}</span>
        <div>
            <div class="section-title">{title}</div>
            {sub_html}
        </div>
    </div>
    """)


def render_status_badge(status_text: str, level: str = "ok"):
    """Renders a colored status badge (ok, warn, crit)."""
    badge_class = {"ok": "badge-ok", "warn": "badge-warn", "crit": "badge-crit"}.get(level, "badge-ok")
    return f'<span class="monitor-badge {badge_class}">{status_text}</span>'


# ============================================================================
# MODEL LOADING
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
# SIDEBAR
# ============================================================================

st.sidebar.markdown(
    f"""
<div style="text-align:center; padding: 8px 0 16px 0; border-bottom: 1px solid {Theme.BORDER}; margin-bottom: 20px;">
<div style="font-size: 2rem;">🏀</div>
<div style="font-size: 0.85rem; font-weight: 800; color: {Theme.TEXT_1}; letter-spacing: 0.08em; margin-top: 4px;">NBA PRO</div>
<div style="font-size: 0.65rem; color: {Theme.TEXT_3}; letter-spacing: 0.15em; text-transform: uppercase;">Boxscores Engine</div>
</div>
""",
    unsafe_allow_html=True,
)

predictor = load_predictor()

if predictor is None:
    st.error("Falha ao carregar o modelo de previsão.")
    st.stop()

# Seleção de jogador com busca
st.sidebar.markdown(f'<div style="font-size:0.72rem; font-weight:700; color:{Theme.TEXT_3}; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;">JOGADOR</div>', unsafe_allow_html=True)
all_players = sorted(predictor.player_averages.keys())
selected_player = st.sidebar.selectbox("Selecionar Jogador", options=all_players, help="Escolha um jogador da NBA para analisar", label_visibility="collapsed")

# Seleção de time baseada no CSV de boxscores
available_teams = []
if getattr(predictor, "df_raw", None) is not None and "TEAM_ABBREVIATION" in predictor.df_raw.columns:
    available_teams = sorted(predictor.df_raw["TEAM_ABBREVIATION"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist())

default_team = predictor.player_averages.get(selected_player, {}).get("team", "")
if default_team not in available_teams and available_teams:
    default_team = available_teams[0]

st.sidebar.markdown(f'<div style="font-size:0.72rem; font-weight:700; color:{Theme.TEXT_3}; text-transform:uppercase; letter-spacing:0.1em; margin:12px 0 6px 0;">TIME</div>', unsafe_allow_html=True)
selected_team = st.sidebar.selectbox(
    "Selecionar Time",
    options=available_teams if available_teams else [default_team or "Unknown"],
    index=(available_teams.index(default_team) if default_team in available_teams else 0) if (available_teams or default_team) else 0,
    help="Time do jogador",
    label_visibility="collapsed",
)

# ✅ VERIFICAR LESÕES
injury_check: dict[str, object] = {"status": "Disponível", "lesão": "", "aviso": False}
try:
    injury_check = check_player_injury_status(selected_player)
except Exception:
    injury_check = {"status": "Disponível", "lesão": "", "aviso": False}

if injury_check.get("aviso"):
    st.sidebar.markdown(
        f"""
<div style="background: rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:10px; padding:12px 16px; margin:12px 0;">
<div style="font-weight:700; color:{Theme.NEGATIVE}; font-size:0.85rem;">⚠️ INDISPONÍVEL</div>
<div style="color:{Theme.TEXT_2}; font-size:0.78rem; margin-top:4px;">{injury_check.get("lesão", "")}</div>
</div>
""",
        unsafe_allow_html=True,
    )
elif str(injury_check.get("status", "")).lower() != "disponível":
    st.sidebar.warning(f"⚠️ {selected_player}: {injury_check.get('status', '')}")
else:
    st.sidebar.markdown(
        f"""
<div style="background: rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.15); border-radius:10px; padding:10px 16px; margin:12px 0;">
<span style="color:{Theme.POSITIVE}; font-weight:600; font-size:0.82rem;">✅ Disponível</span>
</div>
""",
        unsafe_allow_html=True,
    )

# Parâmetros de apostas
st.sidebar.markdown(f"""<div style="font-size:0.72rem; font-weight:700; color:{Theme.TEXT_3}; text-transform:uppercase; letter-spacing:0.1em; margin:20px 0 10px 0; padding-top:16px; border-top:1px solid {Theme.BORDER};">PARÂMETROS</div>""", unsafe_allow_html=True)
col1, col2 = st.sidebar.columns(2)
with col1:
    market_line = st.number_input("Linha O/U", min_value=0.0, max_value=100.0, value=25.5, step=0.5, help="Linha Over/Under")

with col2:
    market_odds = st.number_input("Odds", min_value=1.0, max_value=10.0, value=1.95, step=0.01, help="Odds decimais")

# Minutos esperados
default_minutes = 30
if selected_player in predictor.player_averages:
    default_minutes = int(predictor.player_averages[selected_player]["avg_min"])
expected_minutes = st.sidebar.slider("Minutos Esperados", min_value=0, max_value=40, value=default_minutes)

# ============================================================================
# SIDEBAR — REVALIDAÇÃO
# ============================================================================

st.sidebar.markdown(f"""<div style="font-size:0.72rem; font-weight:700; color:{Theme.TEXT_3}; text-transform:uppercase; letter-spacing:0.1em; margin:20px 0 10px 0; padding-top:16px; border-top:1px solid {Theme.BORDER};">MANUTENÇÃO</div>""", unsafe_allow_html=True)

if st.sidebar.button("🔬 Revalidar Modelo", use_container_width=True, help="Validação cruzada (5-fold)"):
    with st.sidebar.status("Revalidando modelo...", expanded=True) as status:
        try:
            st.write("⏳ Iniciando validação cruzada...")
            success, result = revalidate_model(predictor)

            if success:
                st.write("✅ Validação concluída!")
                st.write(f"📊 R² Médio: {result['r2_mean']:.4f} (±{result['r2_std']:.4f})")
                st.write(f"📊 RMSE Médio: {result['rmse_mean']:.2f} (±{result['rmse_std']:.2f})")

                if result["is_valid"]:
                    status.update(label="✅ Modelo VÁLIDO", state="complete")
                else:
                    status.update(label="⚠️ Requer atenção", state="error")

                previous_history = load_revalidation_history()
                previous_result = previous_history[-1] if previous_history else None
                comparison = {
                    "timestamp": datetime.now().isoformat(),
                    "r2_mean": float(result["r2_mean"]),
                    "r2_std": float(result["r2_std"]),
                    "rmse_mean": float(result["rmse_mean"]),
                    "rmse_std": float(result["rmse_std"]),
                    "is_valid": bool(result["is_valid"]),
                }

                if previous_result:
                    previous_r2_mean = float(cast(Any, previous_result.get("r2_mean", 0)))
                    previous_rmse_mean = float(cast(Any, previous_result.get("rmse_mean", 0)))
                    comparison["previous_r2_mean"] = previous_r2_mean
                    comparison["previous_rmse_mean"] = previous_rmse_mean
                    current_r2_mean = float(cast(Any, comparison["r2_mean"]))
                    current_rmse_mean = float(cast(Any, comparison["rmse_mean"]))
                    comparison["delta_r2_mean"] = current_r2_mean - previous_r2_mean
                    comparison["delta_rmse_mean"] = current_rmse_mean - previous_rmse_mean

                append_revalidation_result(comparison)
                st.sidebar.success("📌 Resultado salvo.")
            else:
                status.update(label=f"❌ Erro: {result}", state="error")

        except Exception as e:
            status.update(label="❌ Erro ao revalidar", state="error")
            st.error(f"Erro: {str(e)[:100]}")

if st.sidebar.button("🏥 Atualizar Lesões", use_container_width=True, help="Scraping ESPN em tempo real"):
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

                st.write(f"✅ Total: {len(df_updated)} jogadores")
                st.write(f"❌ Indisponíveis: {injured_count}")
                st.write(f"✅ Disponíveis: {available_count}")

                status.update(label="✅ Lesões atualizadas!", state="complete")
                st.rerun()
            else:
                status.update(label="⚠️ Falha ao atualizar", state="error")

        except Exception as e:
            status.update(label="❌ Erro", state="error")
            st.error(f"Erro: {str(e)[:100]}")


# ============================================================================
# MAIN LAYOUT — HEADER
# ============================================================================

_html("""
<div class="app-header">
    <div class="app-header-row">
        <span class="app-logo">🏀</span>
        <div>
            <div class="app-title">NBA PRO Betting <span class="app-badge">BOXSCORES</span></div>
            <div class="app-subtitle">Previsões de pontos com análise de EV+ em tempo real</div>
        </div>
    </div>
</div>
""")

# Tabs
tab_predictor, tab_bets, tab_monitor = st.tabs(["⚡ Preditor de Apostas", "📋 Histórico de Apostas", "📊 Monitoramento"])


# ============================================================================
# TAB 1: PREDITOR DE APOSTAS
# ============================================================================

with tab_predictor:
    # ✅ AVISO DE LESÃO
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
    # HERO KPIs
    # ========================================================================

    render_section("🎯", "Previsão do Modelo", f"Análise para {selected_player} · {selected_team}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi("🎯", "Pontos Previstos", f"{prediction['predicted_points']:.2f}", f"±{prediction['std_error']:.1f} pts", "teal")

    with col2:
        trend_accent = "green" if prediction["trend_pct"] > 0 else "red" if prediction["trend_pct"] < -5 else "amber"
        render_kpi("📈", "Tendência", prediction["trend"], f"{prediction['trend_pct']:+.1f}% vs Histórico", trend_accent)

    with col3:
        render_kpi("⏱️", "Minutos Médios", f"{prediction['minutes_used']:.1f}", "Média do jogador", "cyan")

    with col4:
        r2_accent = "green" if prediction["model_r2"] > 0.85 else "amber"
        render_kpi("🧠", "R² do Modelo", f"{prediction['model_r2']:.3f}", f"MAE: {prediction['model_mae']:.1f} pts", r2_accent)

    # Calibração
    render_section("📐", "Calibração por Jogador")

    cal_col1, cal_col2, cal_col3 = st.columns(3)
    with cal_col1:
        render_kpi("📊", "Média Recente", f"{float(prediction.get('recent_avg', 0.0)):.2f}", "Últimos jogos", "cyan")
    with cal_col2:
        render_kpi("📚", "Média Histórica", f"{float(prediction.get('historical_avg', 0.0)):.2f}", "Todas temporadas", "teal")
    with cal_col3:
        bias_val = float(prediction.get("player_bias", 0.0))
        bias_accent = "green" if bias_val > 0 else "red" if bias_val < -1 else "amber"
        render_kpi("⚖️", "Bias do Jogador", f"{bias_val:+.2f}", "Ajuste aplicado", bias_accent)

    # ========================================================================
    # EV+ ANALYSIS
    # ========================================================================

    render_section("💰", "Análise de Valor Esperado (EV+)", "Identificação de apostas com valor positivo")

    ev_col1, ev_col2 = st.columns([1, 1])

    with ev_col1:
        if ev_analysis["ev_plus_pct"] > 3:
            ev_class = "ev-positive"
        elif ev_analysis["ev_plus_pct"] > 0:
            ev_class = "ev-neutral"
        else:
            ev_class = "ev-negative"

        _html(f"""
        <div class="ev-hero {ev_class}">
            <div class="ev-value">{ev_analysis["ev_plus_pct"]:+.2f}%</div>
            <div class="ev-label">Expected Value</div>
            <div class="ev-signal">{ev_analysis["signal"]}</div>
            <div class="ev-rec">{ev_analysis["recommendation"]}</div>
        </div>
        """)

    with ev_col2:
        _html(f"""
        <div class="info-card">
            <h4>Detalhes da Aposta</h4>
            <div class="stat-row"><span class="stat-label">Previsão</span><span class="stat-value">{ev_analysis["predicted_points"]:.2f} pts</span></div>
            <div class="stat-row"><span class="stat-label">Linha de Mercado</span><span class="stat-value">{ev_analysis["line"]}</span></div>
            <div class="stat-row"><span class="stat-label">Odds</span><span class="stat-value">{ev_analysis["market_odds"]}</span></div>
            <div class="stat-row"><span class="stat-label">Vitória Modelo</span><span class="stat-value">{ev_analysis["model_probability"] * 100:.2f}%</span></div>
            <div class="stat-row"><span class="stat-label">Kelly Criterion</span><span class="stat-value">{ev_analysis["kelly_criterion"]:+.4f}</span></div>
            <div class="stat-row"><span class="stat-label">Prob. Implícita</span><span class="stat-value">{ev_analysis["implied_probability"] * 100:.2f}%</span></div>
        </div>
        """)

    # ========================================================================
    # REGISTRAR APOSTA
    # ========================================================================

    render_section("📝", "Registrar Aposta")

    # Lógica de "Aposta Arriscada"
    rmse = predictor.model_stats.get("rmse", 3.48)
    rmse_val = float(rmse) if isinstance(rmse, (int, float)) else 3.48
    edge = abs(prediction["predicted_points"] - market_line)
    is_risky = edge < rmse_val

    if is_risky:
        _html(f"""
        <div class="edge-banner edge-risk">
            <span>⚠️</span>
            <span><strong>APOSTA ARRISCADA</strong> — Edge de <strong>{edge:.2f} pts</strong> &lt; erro médio do modelo (<strong>{rmse_val:.2f} pts</strong>). Dentro da margem de ruído.</span>
        </div>
        """)
    else:
        _html(f"""
        <div class="edge-banner edge-ok">
            <span>✅</span>
            <span><strong>BOA MARGEM</strong> — Edge de <strong>{edge:.2f} pts</strong> &gt; erro médio do modelo (<strong>{rmse_val:.2f} pts</strong>). Margem de segurança encontrada.</span>
        </div>
        """)

    col1, col2, col3 = st.columns(3)

    with col1:
        bet_amount = st.number_input("Valor da Aposta (R$)", min_value=1.0, max_value=10000.0, value=100.0, step=1.0)

    with col2:
        recommended = 0 if prediction["predicted_points"] > market_line else 1
        bet_type = st.selectbox("Tipo de Aposta", options=["Over", "Under"], index=recommended)

    with col3:
        st.write("")
        st.write("")
        bet_button = st.button("⚡ REGISTRAR APOSTA", key="bet_button_boxscores", use_container_width=True)

    if bet_button:
        auto_monitor = AutomaticModelMonitor()

        num_bets = save_bet(
            player_name=selected_player,
            team_name=selected_team,
            market_line=market_line,
            odds=market_odds,
            ev_plus_pct=ev_analysis["ev_plus_pct"],
            model_win_pct=ev_analysis["model_probability"] * 100,
            bet_amount=bet_amount,
            bet_type=bet_type,
        )

        st.success(f"Aposta registrada com sucesso! Total de apostas: {num_bets}")
        st.balloons()

    # ========================================================================
    # DESEMPENHO DO JOGADOR
    # ========================================================================

    render_section("📊", "Análise de Desempenho", f"Estatísticas detalhadas de {selected_player}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f'<div style="font-size:0.72rem; font-weight:700; color:{Theme.TEXT_3}; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:10px;">Médias de Temporada</div>', unsafe_allow_html=True)
        player_stats = predictor.player_averages[selected_player]
        stats_df = pd.DataFrame(
            {"Estatística": ["Pontos Médios", "Minutos Médios", "Posição", "Time", "Última Temporada", "Temporadas"], "Valor": [f"{player_stats['avg_pts']:.2f}", f"{player_stats['avg_min']:.2f}", player_stats["position"], player_stats["team"], player_stats["last_season"], f"{player_stats['seasons']}"]},
        )
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown(f'<div style="font-size:0.72rem; font-weight:700; color:{Theme.TEXT_3}; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:10px;">Recente vs Histórico</div>', unsafe_allow_html=True)
        recent_avg_display = float(prediction.get("recent_avg", 0.0))
        historical_avg_display = float(prediction.get("historical_avg", 0.0))
        comparison_df = pd.DataFrame({"Período": ["Últimos 10 Jogos", "Histórico", "Diferença"], "Pontos Médios": [f"{recent_avg_display:.2f}", f"{historical_avg_display:.2f}", f"{recent_avg_display - historical_avg_display:+.2f}"]})
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    # ========================================================================
    # GRÁFICOS HISTÓRICOS
    # ========================================================================

    render_section("📈", "Desempenho Histórico", "Tendências e distribuições")

    if predictor.df is not None:
        player_df = predictor.df[predictor.df["PLAYER_NAME"] == selected_player].copy()
        player_df = player_df.sort_values("GAME_DATE")

        col1, col2 = st.columns(2)

        with col1:
            if len(player_df) > 0 and "SEASON" in player_df.columns:
                season_stats = player_df.groupby("SEASON").agg({"PTS": "mean", "MIN": "mean"}).reset_index()
                season_stats.columns = ["SEASON", "PTS_mean", "MIN_mean"]
                pts_chart = (
                    alt.Chart(season_stats)
                    .mark_line(point=alt.OverlayMarkDef(size=60, filled=True), color=Theme.CHART_1, strokeWidth=2.5)
                    .encode(
                        x=alt.X("SEASON:N", title="Temporada"),
                        y=alt.Y("PTS_mean:Q", title="Pontos / Jogo"),
                        tooltip=["SEASON", alt.Tooltip("PTS_mean:Q", format=".1f"), alt.Tooltip("MIN_mean:Q", format=".1f")],
                    )
                    .properties(title=f"{selected_player} — Pontos por Temporada", height=300)
                )

                avg_pts = season_stats["PTS_mean"].mean()
                avg_line = alt.Chart(pd.DataFrame({"avg": [avg_pts]})).mark_rule(color=Theme.NEGATIVE, strokeDash=[5, 5], strokeWidth=1.5).encode(y="avg:Q")

                st.altair_chart(pts_chart + avg_line, use_container_width=True)

        with col2:
            if len(player_df) > 0 and "SEASON" in player_df.columns:
                season_stats = player_df.groupby("SEASON").agg({"PTS": "mean", "MIN": "mean"}).reset_index()
                season_stats.columns = ["SEASON", "PTS_mean", "MIN_mean"]
                min_chart = (
                    alt.Chart(season_stats)
                    .mark_area(color=Theme.CHART_2, opacity=0.25, line={"color": Theme.CHART_2, "strokeWidth": 2})
                    .encode(
                        x=alt.X("SEASON:N", title="Temporada"),
                        y=alt.Y("MIN_mean:Q", title="Minutos / Jogo"),
                        tooltip=["SEASON", alt.Tooltip("MIN_mean:Q", format=".1f")],
                    )
                    .properties(title=f"{selected_player} — Minutos por Temporada", height=300)
                )
                st.altair_chart(min_chart, use_container_width=True)

        col1, col2 = st.columns([1, 1])

        with col1:
            if len(player_df) > 5:
                dist_chart = (
                    alt.Chart(player_df)
                    .mark_bar(color=Theme.CHART_1, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                    .encode(
                        x=alt.X("PTS:Q", bin=alt.Bin(maxbins=15), title="Pontos"),
                        y=alt.Y("count():Q", title="Frequência"),
                        tooltip=["count()"],
                    )
                    .properties(title=f"Distribuição de Pontos — {selected_player}", height=300)
                )
                st.altair_chart(dist_chart, use_container_width=True)

        with col2:
            if len(player_df) > 5:
                scatter = (
                    alt.Chart(player_df)
                    .mark_circle(size=50, color=Theme.CHART_3, opacity=0.6)
                    .encode(
                        x=alt.X("MIN:Q", title="Minutos"),
                        y=alt.Y("PTS:Q", title="Pontos"),
                        tooltip=["GAME_DATE", "MIN", "PTS"],
                    )
                    .properties(title="Correlação Minutos vs Pontos", height=300)
                )

                valid_data = player_df[["MIN", "PTS"]].dropna()
                if len(valid_data) > 2:
                    z = np.polyfit(valid_data["MIN"], valid_data["PTS"], 1)
                    p = np.poly1d(z)
                    trend_df = pd.DataFrame({"MIN": np.linspace(valid_data["MIN"].min(), valid_data["MIN"].max(), 100)})
                    trend_df["PTS"] = p(trend_df["MIN"].values)

                    trend_line = alt.Chart(trend_df).mark_line(color=Theme.NEGATIVE, size=2, strokeDash=[6, 4]).encode(x="MIN:Q", y="PTS:Q")

                    st.altair_chart(scatter + trend_line, use_container_width=True)
                else:
                    st.altair_chart(scatter, use_container_width=True)

    # ========================================================================
    # COMPARAÇÃO COM PARES
    # ========================================================================

    render_section("👥", "Comparação com Pares", "Jogadores da mesma posição")

    peers = predictor.get_player_comparison(selected_player)

    if len(peers) > 0:
        peer_chart = (
            alt.Chart(peers)
            .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
            .encode(
                x=alt.X("Avg PTS:Q", title="Pontos Médios / Jogo"),
                y=alt.Y("Player:N", sort="-x"),
                color=alt.condition(
                    alt.datum.Player == selected_player,
                    alt.value(Theme.ACCENT),
                    alt.value(Theme.CHART_2),
                ),
                tooltip=["Player", "Avg PTS", "Avg MIN"],
            )
            .properties(title="Top Jogadores na Posição (PPG)", height=400)
        )

        st.altair_chart(peer_chart, use_container_width=True)
        st.dataframe(peers, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum par comparável encontrado para este jogador.")

    _html(f"""
    <div style="background:{Theme.BG_CARD}; border:1px solid {Theme.BORDER}; border-radius:12px; padding:20px; margin-top:32px;">
        <div style="font-size:0.82rem; font-weight:600; color:{Theme.TEXT_2}; margin-bottom:8px;">⚠️ Aviso Legal</div>
        <div style="font-size:0.78rem; color:{Theme.TEXT_3}; line-height:1.6;">
            Esta ferramenta é apenas para fins educacionais e de entretenimento.
            Apostas esportivas envolvem risco. Jogue responsavelmente e apenas com dinheiro que pode perder.
            Previsões baseadas em dados históricos e ML não garantem resultados futuros.
        </div>
    </div>
    """)


# ============================================================================
# TAB 2: HISTÓRICO DE APOSTAS
# ============================================================================

with tab_bets:
    render_section("📋", "Histórico de Apostas", "Gerencie e acompanhe suas apostas registradas")

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

            for idx, row in edited_bets_df.iterrows():
                original_row = bets_df.iloc[idx] if idx < len(bets_df) else None

                if original_row is not None and str(row["Pts(Real)"]).strip() != "" and str(original_row["Pts(Real)"]).strip() == "":
                    try:
                        pts_real = float(str(row["Pts(Real)"]).replace(",", "."))
                        predicted_pts = float(str(row["Linha"]).replace(",", "."))
                        player_name = str(row["Jogador"])
                        ev_plus = float(str(row["EV+%"]).replace("%", "").replace(",", "."))

                        auto_monitor.log_prediction(
                            player_name=player_name,
                            actual_pts=pts_real,
                            predicted_pts=predicted_pts,
                            confidence=0.85,
                        )

                        st.success(f"✅ Predição registrada: {player_name} | Real: {pts_real:.1f} pts")
                    except Exception as e:
                        st.warning(f"Erro ao registrar predição: {e}")

            edited_bets_df = format_bets_df(edited_bets_df)
            edited_bets_df.to_csv("data/historico_apostas.csv", index=False, encoding="utf-8")
            bets_df = edited_bets_df
            st.rerun()

        # ========================================================================
        # ESTATÍSTICAS
        # ========================================================================

        render_section("📊", "Estatísticas das Apostas")

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
        odds_series = pd.to_numeric(bets_df["Odd"].astype(str).str.replace(",", "."), errors="coerce")
        odds_series = odds_series.replace(0, np.nan)
        average_odds = odds_series.mean() if odds_series.notna().any() else 0.0
        average_odds_pct = (100 / odds_series).mean() if odds_series.notna().any() else 0.0

        green_bets = len(bets_df[bets_df["Resultado"] == "Green"])
        red_bets = len(bets_df[bets_df["Resultado"] == "Red"])
        hit_rate = ((green_bets / (green_bets + red_bets)) * 100) if (green_bets + red_bets) else 0.0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_kpi("📊", "Total de Apostas", str(len(bets_df)), "", "teal")
        with col2:
            render_kpi("✅", "GREEN", str(green_bets), f"{hit_rate:.1f}% taxa", "green")
        with col3:
            render_kpi("❌", "RED", str(red_bets), "", "red")
        with col4:
            roi_accent = "green" if roi > 0 else "red"
            render_kpi("💰", "ROI", f"{roi:.2f}%", f"R$ {accumulated_profit:.2f}", roi_accent)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        col5, col6, col7 = st.columns(3)
        with col5:
            render_kpi("💵", "Total Apostado", f"R$ {total_value:.2f}", "", "cyan")
        with col6:
            render_kpi("📈", "Odd Média", f"{average_odds:.2f}", f"{average_odds_pct:.1f}% implied", "amber")
        with col7:
            profit_accent = "green" if accumulated_profit > 0 else "red"
            render_kpi("🏦", "Acumulado", f"R$ {accumulated_profit:.2f}", "", profit_accent)

        # Tabela de resumo por jogador
        render_section("👤", "Resumo por Jogador")

        player_summary = (
            bets_df.groupby("Jogador").agg({"Tipo": "count", "Valor Aposta": lambda x: pd.to_numeric(x.astype(str).str.replace("R$ ", "").str.replace(",", "."), errors="coerce").sum(), "EV+%": lambda x: pd.to_numeric(x.astype(str).str.replace("%", ""), errors="coerce").mean()}).rename(columns={"Tipo": "Num Apostas"})
        )

        player_summary["Valor Total"] = player_summary["Valor Aposta"].apply(lambda x: f"R$ {x:.2f}")
        player_summary["EV+ Médio"] = player_summary["EV+%"].apply(lambda x: f"{x:.2f}%")

        st.dataframe(player_summary[["Num Apostas", "Valor Total", "EV+ Médio"]], use_container_width=True)

        csv_export = bets_df.to_csv(index=False, encoding="utf-8")
        st.download_button(label="📥 Exportar CSV", data=csv_export, file_name=f"apostas_nba_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")

    else:
        st.info("Nenhuma aposta registrada ainda. Vá para a aba **⚡ Preditor de Apostas** para começar!")


# ============================================================================
# TAB 3: MONITORAMENTO
# ============================================================================

with tab_monitor:
    render_section("📊", "Monitoramento de Desempenho", "Validação contínua contra overfitting e degradação")

    # ========================================================================
    # MÉTRICAS PRINCIPAIS DO MODELO
    # ========================================================================

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        r2_val = predictor.model_stats["r2"]
        r2_accent = "green" if r2_val > 0.85 else "amber" if r2_val > 0.80 else "red"
        render_kpi("🎯", "R² Score", f"{r2_val:.4f}", "Treino" if r2_val > 0.85 else "Atenção", r2_accent)

    with col2:
        rmse_val_display = predictor.model_stats["rmse"]
        rmse_accent = "green" if rmse_val_display < 3.0 else "amber" if rmse_val_display < 3.5 else "red"
        render_kpi("📏", "RMSE", f"{rmse_val_display:.2f}", "pts", rmse_accent)

    with col3:
        mae_val = predictor.model_stats["mae"]
        mae_accent = "green" if mae_val < 2.0 else "amber" if mae_val < 2.8 else "red"
        render_kpi("📐", "MAE", f"{mae_val:.2f}", "pts", mae_accent)

    with col4:
        n_features = len(predictor.feature_cols)
        render_kpi("🧪", "Features", str(n_features), "Otimizado" if n_features == 8 else "Legacy", "cyan")

    with col5:
        render_kpi("⚡", "Status", "ATIVO", f"v2.{'1' if n_features == 8 else '0'}", "teal")

    # ========================================================================
    # THRESHOLDS
    # ========================================================================

    render_section("⚙️", "Limites de Monitoramento")

    monitor = OverfittingMonitor()

    col1, col2 = st.columns(2)

    with col1:
        r2_status_text = "✅ BOM" if predictor.model_stats["r2"] > 0.80 else "⚠️ AVISO" if predictor.model_stats["r2"] > 0.75 else "❌ CRÍTICO"
        rmse_status_text = "✅ BOM" if predictor.model_stats["rmse"] < 3.5 else "⚠️ AVISO" if predictor.model_stats["rmse"] < 4.0 else "❌ CRÍTICO"
        mae_status_text = "✅ BOM" if predictor.model_stats["mae"] < 2.8 else "⚠️ AVISO" if predictor.model_stats["mae"] < 3.2 else "❌ CRÍTICO"

        _html(f"""
        <div class="info-card">
            <h4>Status Atual</h4>
            <div class="stat-row"><span class="stat-label">R²</span><span class="stat-value">{r2_status_text}</span></div>
            <div class="stat-row"><span class="stat-label">RMSE</span><span class="stat-value">{rmse_status_text}</span></div>
            <div class="stat-row"><span class="stat-label">MAE</span><span class="stat-value">{mae_status_text}</span></div>
        </div>
        """)

    with col2:
        _html("""
        <div class="info-card">
            <h4>Limites Configurados</h4>
            <div class="stat-row"><span class="stat-label">R² Gap Máximo</span><span class="stat-value">0.0500</span></div>
            <div class="stat-row"><span class="stat-label">RMSE Máximo</span><span class="stat-value">3.5 pts</span></div>
            <div class="stat-row"><span class="stat-label">R² Mínimo Teste</span><span class="stat-value">0.8000</span></div>
            <div class="stat-row"><span class="stat-label">Desvio Padrão CV</span><span class="stat-value">0.0300</span></div>
        </div>
        """)

    # ========================================================================
    # MONITORAMENTO AUTOMÁTICO
    # ========================================================================

    render_section("🤖", "Monitoramento Automático", "Métricas em tempo real do histórico de apostas")

    bets_with_real = load_bets_csv()
    bets_with_real_filled = bets_with_real[(bets_with_real["Pts(Real)"].notna()) & (bets_with_real["Pts(Real)"].astype(str).str.strip() != "") & (bets_with_real["Pts(Real)"].astype(str).str.strip() != "-")].copy()

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

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi("🔢", "Predições", str(total_predictions), "Com Pts(Real)", "teal")
    with col2:
        mae_rt_accent = "green" if mae < 3 else "amber" if mae < 5 else "red"
        render_kpi("📏", "MAE Real", f"{mae:.3f}", "pts", mae_rt_accent)
    with col3:
        acc_accent = "green" if accuracy >= 80 else "amber" if accuracy >= 60 else "red"
        render_kpi("🎯", "Acurácia", f"{accuracy:.2f}%", "Taxa de acerto", acc_accent)
    with col4:
        if accuracy >= 58:
            status_level = "ok"
            status_label = "✅ BOM"
        elif accuracy >= 53:
            status_level = "warn"
            status_label = "⚠️ AVISO"
        else:
            status_level = "crit"
            status_label = "❌ CRÍTICO"
        render_kpi("📡", "Status", status_label, "", {"ok": "green", "warn": "amber", "crit": "red"}[status_level])

    if total_predictions >= 500:
        st.error(f"⚠️ O modelo já tem **{total_predictions} registros** com Pts(Real). É um bom momento para revalidar.")
    elif total_predictions >= 450:
        st.warning(f"⏳ Faltam poucos registros para o alerta automático. Atualmente: **{total_predictions}** / 500.")

    # Predições recentes
    render_section("📋", "Últimas Predições Registradas")

    if len(bets_with_real_filled) > 0:
        bets_display = bets_with_real_filled.copy()
        bets_display["timestamp"] = pd.to_datetime(bets_display["Data"])
        bets_display["player"] = bets_display["Jogador"]
        bets_display["actual"] = pd.to_numeric(bets_display["Pts(Real)"].astype(str).str.replace(",", "."), errors="coerce")
        bets_display["predicted"] = pd.to_numeric(bets_display["Linha"].astype(str).str.replace(",", "."), errors="coerce")
        bets_display["error"] = (bets_display["actual"] - bets_display["predicted"]).abs()
        bets_display["confidence"] = 0.85
        bets_display["is_accurate"] = bets_display["Resultado"].str.lower() == "green"

        display_limit = 25
        display_df = bets_display[["timestamp", "player", "actual", "predicted", "error", "confidence", "is_accurate"]].sort_values("timestamp", ascending=False).head(display_limit).copy()
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
        st.caption(f"Mostrando {len(display_df)} de {total_predictions} predições com Pts(Real)")
    else:
        st.info("📝 Nenhuma predição com Pts(Real) preenchido ainda.\n\n**Como usar:**\n1. Faça uma previsão e registre uma aposta\n2. Ao final do jogo, preencha coluna 'Pts(Real)' no histórico de apostas\n3. A predição aparecerá aqui automaticamente")

    # Desempenho Diário
    render_section("📅", "Desempenho Diário", "Últimos 7 dias de operação")

    if len(bets_with_real_filled) > 0:
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

        styled_daily_stats = daily_stats.style.format(
            {
                "MAE": "{:.3f}",
                "RMSE": "{:.3f}",
                "ACCURACY": "{:.2f}",
            },
        )

        st.dataframe(styled_daily_stats, use_container_width=True, hide_index=True)

        if not daily_stats.empty:
            chart = (
                alt.Chart(daily_stats)
                .mark_line(point=alt.OverlayMarkDef(size=60, filled=True), color=Theme.CHART_1, strokeWidth=2.5)
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

    # Erro por Jogador e Faixa
    render_section("🔎", "Erro por Jogador e Faixa")

    monitor_state = AutomaticModelMonitor()

    col1, col2 = st.columns(2)

    with col1:
        player_rankings = monitor_state.get_player_rankings(min_predictions=3, top_n=10)
        if not player_rankings.empty:
            player_rankings_display = player_rankings.copy()
            player_rankings_display["mae"] = player_rankings_display["mae"].round(3)
            player_rankings_display["rmse"] = player_rankings_display["rmse"].round(3)
            player_rankings_display["accuracy_percent"] = player_rankings_display["accuracy_percent"].round(2)
            player_rankings_display["avg_confidence"] = player_rankings_display["avg_confidence"].round(2)
            player_rankings_display.columns = [
                "Jogador",
                "Predições",
                "MAE",
                "RMSE",
                "Acurácia (%)",
                "Confiança Média",
            ]
            st.dataframe(player_rankings_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sem histórico suficiente para ranking por jogador.")

    with col2:
        line_range_stats = monitor_state.get_line_range_stats()
        if not line_range_stats.empty:
            line_range_display = line_range_stats.copy()
            line_range_display["mae"] = line_range_display["mae"].round(3)
            line_range_display["rmse"] = line_range_display["rmse"].round(3)
            line_range_display["accuracy_percent"] = line_range_display["accuracy_percent"].round(2)
            line_range_display.columns = [
                "Faixa Prevista",
                "Predições",
                "MAE",
                "RMSE",
                "Acurácia (%)",
            ]
            st.dataframe(line_range_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sem histórico suficiente para análise por faixa de linha.")

    # Feature Importance
    render_section("📈", "Importância das Features")

    features_dict = predictor.model_stats.get("feature_importance", {})
    features_df = pd.DataFrame({"Feature": list(features_dict.keys()), "Importância": list(features_dict.values())}).sort_values("Importância", ascending=True) if features_dict else pd.DataFrame()

    col1, col2 = st.columns([1, 1])

    with col1:
        if not features_df.empty:
            chart = (
                alt.Chart(features_df)
                .mark_bar(color=Theme.CHART_1, cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
                .encode(
                    y=alt.Y("Feature:N", sort="-x", title="Features"),
                    x=alt.X("Importância:Q", title="Importância Relativa"),
                    tooltip=["Feature", alt.Tooltip("Importância:Q", format=".4f")],
                )
                .properties(title="Importância das Features", height=400)
            )

            st.altair_chart(chart, use_container_width=True)

    with col2:
        if not features_df.empty:
            st.markdown(f'<div style="font-size:0.72rem; font-weight:700; color:{Theme.TEXT_3}; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:10px;">Top Features (Otimizadas)</div>', unsafe_allow_html=True)
            st.dataframe(features_df.sort_values("Importância", ascending=False).head(8), use_container_width=True)

    # Validação Temporal
    render_section("🔄", "Validação Temporal", "TimeSeriesSplit — sem vazamento temporal")

    col1, col2 = st.columns(2)

    with col1:
        _html("""
        <div class="info-card">
            <h4>Configuração</h4>
            <div class="stat-row"><span class="stat-label">Estratégia</span><span class="stat-value">TimeSeriesSplit</span></div>
            <div class="stat-row"><span class="stat-label">Shuffle</span><span class="stat-value">False</span></div>
            <div class="stat-row"><span class="stat-label">Objetivo</span><span class="stat-value">Validar estabilidade</span></div>
        </div>
        """)

    with col2:
        _html("""
        <div class="info-card">
            <h4>Recomendações</h4>
            <div class="stat-row"><span class="stat-label">Gap R²</span><span class="stat-value">&lt; 0.05</span></div>
            <div class="stat-row"><span class="stat-label">Revalidação</span><span class="stat-value">Mensal</span></div>
            <div class="stat-row"><span class="stat-label">Alerta</span><span class="stat-value">Gap &gt; 0.05</span></div>
        </div>
        """)

    # Resumo de Desempenho
    render_section("📊", "Resumo de Desempenho")

    summary_data = {
        "Métrica": ["R² Score", "RMSE", "MAE", "Features", "Status"],
        "Atual": [
            f"{predictor.model_stats.get('r2', 0):.4f}",
            f"{predictor.model_stats.get('rmse', 0):.2f} pts",
            f"{predictor.model_stats.get('mae', 0):.2f} pts",
            f"{len(predictor.feature_cols) if hasattr(predictor, 'feature_cols') else 0} features",
            "Ativo",
        ],
        "Alvo": ["≥ 0.80", "< 3.5 pts", "< 2.8 pts", "24 features", "v2.2"],
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

    revalidation_history = load_revalidation_history()
    if revalidation_history:
        render_section("🧾", "Histórico de Revalidações")
        history_rows = []
        for item in revalidation_history[-5:][::-1]:
            history_rows.append(
                {
                    "Data": pd.to_datetime(item.get("timestamp")).strftime("%d/%m %H:%M") if item.get("timestamp") else "-",
                    "R² Médio": f"{float(item.get('r2_mean', 0)):.4f}",
                    "RMSE Médio": f"{float(item.get('rmse_mean', 0)):.2f}",
                    "Δ R²": f"{float(item.get('delta_r2_mean', 0)):+.4f}" if "delta_r2_mean" in item else "-",
                    "Δ RMSE": f"{float(item.get('delta_rmse_mean', 0)):+.2f}" if "delta_rmse_mean" in item else "-",
                    "Status": "✅" if item.get("is_valid") else "⚠️",
                },
            )

        history_df = pd.DataFrame(history_rows)
        st.dataframe(history_df, use_container_width=True, hide_index=True)

    # Alertas
    render_section("🔔", "Avisos de Monitoramento")

    alerts = []

    if predictor.model_stats.get("r2", 0) < 0.80:
        alerts.append(("⚠️", "R² abaixo de 0.80 — Verificar qualidade dos dados"))

    if predictor.model_stats.get("rmse", 0) > 3.8:
        alerts.append(("⚠️", f"RMSE elevado: {predictor.model_stats.get('rmse', 0):.2f} pts"))

    if predictor.model_stats.get("mae", 0) > 3.0:
        alerts.append(("⚠️", f"MAE elevado: {predictor.model_stats.get('mae', 0):.2f} pts"))

    if not (hasattr(predictor, "feature_cols") and len(predictor.feature_cols) == 8):
        alerts.append(("ℹ️", f"Modelo usando {len(predictor.feature_cols) if hasattr(predictor, 'feature_cols') else 0} features (otimizado: 8)"))

    if len(alerts) == 0:
        _html(f"""
        <div style="background: rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.15); border-radius:12px; padding:16px 20px;">
            <span style="color:{Theme.POSITIVE}; font-weight:700;">✅ Nenhum aviso no momento — Modelo operacional</span>
        </div>
        """)
    else:
        for icon, message in alerts:
            st.warning(f"{icon} {message}")

    # Detalhes Técnicos
    render_section("📋", "Informações Técnicas")

    with st.expander("Ver Detalhes Técnicos"):
        col1, col2 = st.columns(2)

        with col1:
            _html(f"""
            <div class="info-card">
                <h4>Modelo</h4>
                <div class="stat-row"><span class="stat-label">Tipo</span><span class="stat-value">Linear Regression</span></div>
                <div class="stat-row"><span class="stat-label">Features</span><span class="stat-value">{len(predictor.feature_cols) if hasattr(predictor, "feature_cols") else 0}</span></div>
                <div class="stat-row"><span class="stat-label">Samples Treino</span><span class="stat-value">~1000</span></div>
                <div class="stat-row"><span class="stat-label">CV Strategy</span><span class="stat-value">5-Fold</span></div>
            </div>
            """)

        with col2:
            _html(f"""
            <div class="info-card">
                <h4>Features Utilizadas</h4>
                <div style="font-size:0.82rem; color:{Theme.TEXT_2}; line-height:1.8; margin-top:8px;">
                    {", ".join(predictor.feature_cols) if hasattr(predictor, "feature_cols") else "n/a"}
                </div>
            </div>
            """)


# ============================================================================
# FOOTER
# ============================================================================

_html("""
<div class="footer">
    Desenvolvido para apostadores sérios · <span>NBA PRO v3.0</span> · Boxscores Engine
</div>
""")
