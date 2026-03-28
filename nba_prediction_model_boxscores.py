"""
Modelo de previsão avançado baseado em dados de boxscores (partidas)
Com features de lag, momentum, e indicadores de performance
"""

import warnings
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


class NBAPointsPredictorBoxscores:
    def __init__(self, data_path: Optional[str] = None):
        self.df: Optional[pd.DataFrame] = None
        self.df_raw: Optional[pd.DataFrame] = None
        self.model: Optional[Ridge] = None
        self.scaler = StandardScaler()
        self.feature_cols: List[str] = []
        self.model_stats: Dict[str, float] = {}
        self.player_averages: Dict[str, Dict] = {}
        self.X_scaled = None
        self.y = None
        if data_path:
            self.load_data(data_path)

    def load_data(self, data_path: str):
        """Carrega dados brutos de boxscores por jogo"""
        self.df_raw = pd.read_csv(data_path)
        self.df_raw.columns = [c.strip().upper() for c in self.df_raw.columns]

        # Sort by player and game date para criar lag features corretamente
        if "GAME_DATE" in self.df_raw.columns:
            self.df_raw["GAME_DATE"] = pd.to_datetime(self.df_raw["GAME_DATE"], errors="coerce")
            self.df_raw = self.df_raw.sort_values(["PLAYER_NAME", "GAME_DATE"])

        # Criar features de lag POR JOGADOR (crucial para não vazar dados)
        self._create_lag_features()

        # Agregar por PLAYER_NAME + SEASON
        self._aggregate_by_season()

        return self

    def _create_lag_features(self):
        """
        Cria features de lag, momentum e volatilidade para cada jogador
        Processamento profissional evitando data leakage
        """
        # Lag features: média móvel de pontos
        for window in [3, 5, 10, 15]:
            col_name = f"LAG_PTS_{window}"
            self.df_raw[col_name] = self.df_raw.groupby("PLAYER_NAME")["PTS"].shift(1).rolling(window=window, min_periods=1).mean()

        # Lag features: média móvel de minutos
        for window in [5, 10]:
            col_name = f"LAG_MIN_{window}"
            self.df_raw[col_name] = self.df_raw.groupby("PLAYER_NAME")["MIN"].shift(1).rolling(window=window, min_periods=1).mean()

        # Momentum: mudança percentual nos últimos 5 jogos vs 10 jogos
        self.df_raw["LAG_PTS_5"] = self.df_raw["LAG_PTS_5"].fillna(self.df_raw["PTS"].mean())
        self.df_raw["LAG_PTS_10"] = self.df_raw["LAG_PTS_10"].fillna(self.df_raw["PTS"].mean())
        self.df_raw["MOMENTUM"] = (self.df_raw["LAG_PTS_5"] - self.df_raw["LAG_PTS_10"]) / self.df_raw["LAG_PTS_10"].replace(0, 1)

        # Volatilidade: desvio padrão dos últimos 10 jogos
        self.df_raw["VOLATILITY"] = self.df_raw.groupby("PLAYER_NAME")["PTS"].shift(1).rolling(window=10, min_periods=1).std().fillna(0)

        # Consistency: coeficiente de variação (std/mean)
        self.df_raw["CONSISTENCY"] = self.df_raw.groupby("PLAYER_NAME")["PTS"].shift(1).rolling(window=10, min_periods=1).apply(lambda x: x.std() / (x.mean() + 1e-6) if len(x) > 1 else 0).fillna(0)

        # Indicador de forma: % mudança PTS últimos 3 vs últimos 5
        self.df_raw["LAG_PTS_3"] = self.df_raw["LAG_PTS_3"].fillna(self.df_raw["PTS"].mean())
        self.df_raw["FORM_INDICATOR"] = (self.df_raw["LAG_PTS_3"] - self.df_raw["LAG_PTS_5"]) / self.df_raw["LAG_PTS_5"].replace(0, 1)

        # Game streak: número de jogos consecutivos com PTS > média
        streaks_list = []
        for player in self.df_raw["PLAYER_NAME"].unique():
            player_mask = self.df_raw["PLAYER_NAME"] == player
            player_pts = self.df_raw.loc[player_mask, "PTS"].values
            mean_pts = player_pts.mean()
            current_streak = 0
            player_streaks = []
            for pts in player_pts:
                if pts > mean_pts:
                    current_streak += 1
                else:
                    current_streak = 0
                player_streaks.append(current_streak)
            streaks_list.extend(player_streaks)

        self.df_raw["GAME_STREAK"] = streaks_list

        # Seasonality: qual trimestre da temporada
        if "GAME_DATE" in self.df_raw.columns:
            self.df_raw["MONTH"] = self.df_raw["GAME_DATE"].dt.month
            self.df_raw["SEASON_PHASE"] = pd.cut(self.df_raw["MONTH"], bins=[0, 3, 6, 9, 12], labels=["PlayOffs", "Final", "Meio", "Inicial"])

        # Eficiência ofensiva: FG% últimos 5 jogos
        self.df_raw["LAG_FG_PCT_5"] = self.df_raw.groupby("PLAYER_NAME")["FG_PCT"].shift(1).rolling(window=5, min_periods=1).mean().fillna(self.df_raw["FG_PCT"].mean())

        # Taxa de assistência: AST/MIN
        self.df_raw["AST_RATE"] = self.df_raw["AST"] / (self.df_raw["MIN"].replace(0, 1))

        # Taxa de turnovers
        self.df_raw["TOV_RATE"] = self.df_raw["TOV"] / (self.df_raw["MIN"].replace(0, 1))

        # Eficiência defensiva: (STL + BLK) / MIN
        self.df_raw["DEF_RATE"] = (self.df_raw["STL"] + self.df_raw["BLK"]) / (self.df_raw["MIN"].replace(0, 1))

        # Home/Away split
        if "MATCHUP" in self.df_raw.columns:
            self.df_raw["IS_HOME"] = ~self.df_raw["MATCHUP"].str.contains("@", na=False).astype(int)
        else:
            self.df_raw["IS_HOME"] = 0.5

        # Back-to-back indicator
        if "GAME_DATE" in self.df_raw.columns:
            self.df_raw["DAYS_REST"] = self.df_raw.groupby("PLAYER_NAME")["GAME_DATE"].diff().dt.days.fillna(1)
            self.df_raw["IS_BACK_TO_BACK"] = (self.df_raw["DAYS_REST"] == 1).astype(int)
        else:
            self.df_raw["DAYS_REST"] = 1
            self.df_raw["IS_BACK_TO_BACK"] = 0

        return self

    def _aggregate_by_season(self):
        """Agrega features por jogador-temporada"""
        agg_dict = {
            "PTS": ["mean", "std", "min", "max"],
            "MIN": ["mean", "std"],
            "FG_PCT": "mean",
            "FG3_PCT": "mean",
            "FT_PCT": "mean",
            "REB": "mean",
            "AST": "mean",
            "STL": "mean",
            "BLK": "mean",
            "TOV": "mean",
            "PF": "mean",
            "LAG_PTS_3": "mean",
            "LAG_PTS_5": "mean",
            "LAG_PTS_10": "mean",
            "LAG_PTS_15": "mean",
            "LAG_MIN_5": "mean",
            "LAG_MIN_10": "mean",
            "MOMENTUM": "mean",
            "VOLATILITY": "mean",
            "CONSISTENCY": "mean",
            "FORM_INDICATOR": "mean",
            "GAME_STREAK": "max",
            "LAG_FG_PCT_5": "mean",
            "AST_RATE": "mean",
            "TOV_RATE": "mean",
            "DEF_RATE": "mean",
            "IS_HOME": "mean",
            "IS_BACK_TO_BACK": "mean",
            "DAYS_REST": "mean",
            "TEAM_ABBREVIATION": "first",
            "GAME_ID": "count",
        }

        self.df = self.df_raw.groupby(["PLAYER_NAME", "SEASON"], as_index=False).agg(agg_dict)

        # Flatten multi-level columns
        self.df.columns = ["_".join(col).strip("_") if col[1] else col[0] for col in self.df.columns.values]

        self.df = self.df.rename(columns={"GAME_ID_count": "GP"})

        # Remove temporadas com < 10 jogos
        self.df = self.df[self.df["GP"] >= 10].copy()

        # Fill NaN values
        for col in self.df.columns:
            if self.df[col].dtype in ["float64", "int64"]:
                self.df[col] = self.df[col].fillna(0)

        return self

    def build_features(self):
        """Seleciona features para treino"""
        # Features profissionais: lag + momentum + eficiência + volatilidade
        feature_candidates = [
            "MIN_mean",
            "FG_PCT_mean",
            "FG3_PCT_mean",
            "FT_PCT_mean",
            "REB_mean",
            "AST_mean",
            "STL_mean",
            "BLK_mean",
            "TOV_mean",
            "LAG_PTS_3_mean",
            "LAG_PTS_5_mean",
            "LAG_PTS_10_mean",
            "LAG_PTS_15_mean",
            "LAG_MIN_5_mean",
            "LAG_MIN_10_mean",
            "MOMENTUM_mean",
            "VOLATILITY_mean",
            "CONSISTENCY_mean",
            "FORM_INDICATOR_mean",
            "GAME_STREAK_max",
            "LAG_FG_PCT_5_mean",
            "AST_RATE_mean",
            "TOV_RATE_mean",
            "DEF_RATE_mean",
            "IS_HOME_mean",
            "IS_BACK_TO_BACK_mean",
            "DAYS_REST_mean",
        ]

        self.feature_cols = [c for c in feature_candidates if c in self.df.columns]

        # Ponderação por recência
        seasons = sorted(self.df["SEASON"].unique())
        season_weights = {s: i + 1 for i, s in enumerate(seasons)}
        max_w = max(season_weights.values())
        season_weights = {s: w / max_w for s, w in season_weights.items()}
        self.df["WEIGHT"] = self.df["SEASON"].map(season_weights)

        X = self.df[self.feature_cols].copy()
        y = self.df["PTS_mean"].copy()
        weights = self.df["WEIGHT"].copy()

        return X, y, weights

    def train(self):
        """Treina modelo com Ridge Regression e regularização"""
        X, y, weights = self.build_features()
        X_scaled = self.scaler.fit_transform(X)
        self.X_scaled = X_scaled
        self.y = y

        # Ridge com alpha otimizado para evitar overfitting
        self.model = Ridge(alpha=2.0, random_state=42)
        self.model.fit(X_scaled, y, sample_weight=weights)

        y_pred = self.model.predict(X_scaled)
        residuals = y - y_pred

        self.model_stats = {"r2": float(1 - (np.sum(residuals**2) / np.sum((y - y.mean()) ** 2))), "rmse": float(np.sqrt(np.mean(residuals**2))), "mae": float(np.mean(np.abs(residuals))), "std_error": float(np.std(residuals)), "feature_importance": dict(zip(self.feature_cols, np.abs(self.model.coef_)))}

        # Build player_averages
        self.player_averages = {}
        for player in self.df_raw["PLAYER_NAME"].unique():
            player_data = self.df_raw[self.df_raw["PLAYER_NAME"] == player]
            self.player_averages[player] = {
                "avg_pts": float(player_data["PTS"].mean()),
                "avg_min": float(player_data["MIN"].mean()),
                "last_season": str(player_data["SEASON"].max()),
                "seasons": len(self.df[self.df["PLAYER_NAME"] == player]),
                "position": "Desconhecida",
                "team": str(player_data.get("TEAM_ABBREVIATION", pd.Series(["UNK"])).iloc[-1] if "TEAM_ABBREVIATION" in player_data.columns else "UNK"),
            }

        return self

    def predict_points(self, player_name: str, minutes: Optional[float] = None) -> dict:
        """Previsão com features avançadas"""
        if self.model is None or self.df is None:
            raise ValueError("Modelo não treinado")

        if player_name not in self.df["PLAYER_NAME"].values:
            return {"error": "Jogador não encontrado"}

        player_data = self.df[self.df["PLAYER_NAME"] == player_name]
        if minutes is None:
            minutes = float(player_data["MIN_mean"].mean()) if "MIN_mean" in player_data.columns else 0.0

        # Build feature vector
        features = []
        for col in self.feature_cols:
            if "MIN" in col and col.endswith("_mean"):
                features.append(minutes)
            else:
                features.append(float(player_data[col].mean()) if col in player_data.columns else 0.0)

        X = np.array([features])
        Xs = self.scaler.transform(X)
        pred = float(self.model.predict(Xs)[0])
        pred = max(0.0, pred)
        std = float(self.model_stats.get("std_error", 0.0))

        # Trending
        if len(player_data) > 1:
            seasons_list = sorted(player_data["SEASON"].unique())
            if len(seasons_list) > 3:
                recent_seasons = seasons_list[-3:]
                recent = float(player_data[player_data["SEASON"].isin(recent_seasons)]["PTS_mean"].mean())
                historical = float(player_data[~player_data["SEASON"].isin(recent_seasons)]["PTS_mean"].mean())
            else:
                recent = float(player_data["PTS_mean"].mean())
                historical = recent
        else:
            recent = float(player_data["PTS_mean"].mean())
            historical = recent

        trend_pct = round((recent / historical - 1) * 100, 1) if historical > 0 else 0.0

        return {
            "player": player_name,
            "predicted_points": round(pred, 2),
            "confidence_lower": round(max(0.0, pred - std), 2),
            "confidence_upper": round(pred + std, 2),
            "std_error": round(std, 2),
            "minutes_used": round(minutes, 1),
            "recent_avg": round(recent, 2),
            "historical_avg": round(historical, 2),
            "trend": "UP" if recent > historical else "DOWN",
            "trend_pct": trend_pct,
            "model_r2": round(float(self.model_stats.get("r2", 0.0)), 4),
            "model_mae": round(float(self.model_stats.get("mae", 0.0)), 2),
        }

    def calculate_ev_plus(self, predicted_points: float, market_odds: float, line: float) -> dict:
        """Cálculo profissional de EV+"""
        from scipy.stats import norm

        implicit_prob = 1 / market_odds if market_odds > 0 else 0
        std = float(self.model_stats.get("std_error", 0.1))
        z = (line - predicted_points) / (std + 1e-6)
        prob_over = 1 - norm.cdf(z)
        ev_plus = (prob_over * (market_odds - 1)) - ((1 - prob_over) * 1)
        ev_pct = ev_plus * 100
        signal = "BUY" if ev_pct > 0 else "AVOID"
        kelly_criterion = (prob_over * (market_odds - 1) - (1 - prob_over)) / (market_odds - 1) if market_odds > 1 else 0

        return {
            "prob_over": float(prob_over),
            "implied_probability": float(implicit_prob),
            "model_probability": float(prob_over),
            "ev_plus": float(ev_plus),
            "ev_plus_pct": round(ev_pct, 2),
            "kelly_criterion": round(float(kelly_criterion), 4),
            "signal": signal,
            "recommendation": "BUY" if ev_pct > 0 else "AVOID",
            "predicted_points": round(predicted_points, 2),
            "line": round(line, 1),
            "market_odds": round(market_odds, 2),
        }

    def get_player_comparison(self, player_name: str, limit: int = 10) -> pd.DataFrame:
        """Comparação com peers"""
        if self.df is None or player_name not in self.df["PLAYER_NAME"].values:
            return pd.DataFrame()

        top = self.df.groupby("PLAYER_NAME").agg({"PTS_mean": "mean", "MIN_mean": "mean", "FG_PCT_mean": "mean"}).sort_values("PTS_mean", ascending=False).head(limit)

        top.columns = ["Avg PTS", "Avg MIN", "FG%"]
        top.index.name = "Player"
        return top.reset_index().rename(columns={"PLAYER_NAME": "Player"})
