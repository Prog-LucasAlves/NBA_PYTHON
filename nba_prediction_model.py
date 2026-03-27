"""
Modelo de Previsão de Pontos de Jogadores da NBA com Calculadora de EV+
Especializado para análise de apostas esportivas
"""

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


class NBAPointsPredictor:
    """
    Prevê pontos de jogadores da NBA usando dados históricos multi-temporada.
    Incorpora ponderação por recência e intervalos de confiança.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.df: Optional[pd.DataFrame] = None
        self.model: Optional[LinearRegression] = None
        self.scaler = StandardScaler()
        self.feature_cols: Optional[list[str]] = None
        self.model_stats: dict = {}
        self.player_averages: dict = {}

        if data_path:
            self.load_data(data_path)

    def load_data(self, data_path: str):
        """Carrega e pré-processa dados de stats da NBA"""
        self.df = pd.read_csv(data_path)

        # Normalizar nomes de colunas
        self.df.columns = [c.strip() for c in self.df.columns]
        self.df.rename(columns={c: c.upper() for c in self.df.columns}, inplace=True)

        # Garantir que colunas obrigatórias existem
        required = ["PLAYER_NAME", "SEASON", "PTS", "MIN", "GP"]
        for col in required:
            if col not in self.df.columns:
                raise ValueError(f"Coluna obrigatória ausente: {col}")

        # Filter: only players with at least 10 games per season
        self.df = self.df[self.df["GP"] >= 10].copy()

        # Criar colunas de features - selecionar preditores significativos
        feature_candidates = ["MIN", "FG_PCT", "FG3_PCT", "FT_PCT", "AST", "REB", "OREB", "DREB", "STL", "BLK", "TOV"]

        self.feature_cols = [col for col in feature_candidates if col in self.df.columns]

        # Preencher valores NaN com 0
        for col in self.feature_cols + ["PTS"]:
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce").fillna(0)

        print(f">> Carregados {len(self.df)} registros, {self.df['PLAYER_NAME'].nunique()} jogadores unicos")
        print(f">> Colunas de features: {self.feature_cols}")

        return self

    def build_features(self):
        """Constrói matriz de features com ponderação por recência"""
        # Ordem de temporadas para ponderação (recente = peso maior)
        seasons = sorted(self.df["SEASON"].unique())
        season_weights = {s: i + 1 for i, s in enumerate(seasons)}  # Aumento linear
        max_weight = max(season_weights.values())
        season_weights = {s: w / max_weight for s, w in season_weights.items()}  # Normalizar para [0,1]

        self.df["WEIGHT"] = self.df["SEASON"].map(season_weights)

        # Garantir que features não têm NaN
        X = self.df[self.feature_cols].copy()
        y = self.df["PTS"].copy()
        weights = self.df["WEIGHT"].copy()

        return X, y, weights

    def train(self):
        """Treina o modelo de previsão"""
        X, y, weights = self.build_features()

        # Normalizar features
        X_scaled = self.scaler.fit_transform(X)

        # Treinar com pesos de amostra (temporadas recentes = mais importantes)
        self.model = LinearRegression()
        self.model.fit(X_scaled, y, sample_weight=weights)

        # Calcular métricas de desempenho
        y_pred = self.model.predict(X_scaled)
        residuals = y - y_pred

        self.model_stats = {"r2": 1 - (np.sum(residuals**2) / np.sum((y - y.mean()) ** 2)), "rmse": np.sqrt(np.mean(residuals**2)), "mae": np.mean(np.abs(residuals)), "std_error": np.std(residuals), "feature_importance": dict(zip(self.feature_cols, np.abs(self.model.coef_)))}

        # Calcular médias dos jogadores
        for player in self.df["PLAYER_NAME"].unique():
            player_data = self.df[self.df["PLAYER_NAME"] == player]
            self.player_averages[player] = {
                "avg_pts": player_data["PTS"].mean(),
                "avg_min": player_data["MIN"].mean(),
                "last_season": player_data["SEASON"].max(),
                "seasons": len(player_data),
                "position": player_data.get("POS", pd.Series(["Desconhecida"])).iloc[0] if "POS" in player_data.columns else "Desconhecida",
                "team": player_data["TEAM_ABBREVIATION"].iloc[-1] if "TEAM_ABBREVIATION" in player_data.columns else "UNK",
            }

        print("\n>> Modelo treinado com sucesso!")
        print(f"  Score R2: {self.model_stats['r2']:.4f}")
        print(f"  RMSE: {self.model_stats['rmse']:.2f} pontos")
        print(f"  MAE: {self.model_stats['mae']:.2f} pontos")
        print(f"  Desvio Padrao Residual: {self.model_stats['std_error']:.2f}")

        return self

    def predict_points(self, player_name: str, minutes: Optional[float] = None) -> dict:
        """
        Prevê pontos para um jogador no próximo jogo

        Args:
            player_name: Nome do jogador
            minutes: Minutos esperados (se None, usa média do jogador)

        Returns:
            Dict com previsão, confiança, etc
        """
        if not self.model:
            raise ValueError("Modelo não foi treinado. Chame train() primeiro.")

        if player_name not in self.player_averages:
            return {"error": f"Jogador '{player_name}' não encontrado no dataset"}

        # Obter stats recentes do jogador
        if self.df is None:
            return {"error": "Dataset não carregado"}

        player_data = self.df[self.df["PLAYER_NAME"] == player_name].copy()

        if len(player_data) == 0:
            return {"error": f"Sem dados para o jogador '{player_name}'"}

        # Usar minutos se fornecido, caso contrário usar média
        if minutes is None:
            minutes = player_data["MIN"].mean()

        # Construir vetor de feature a partir das médias do jogador
        features = {}
        if self.feature_cols:
            for col in self.feature_cols:
                if col == "MIN":
                    features[col] = minutes
                else:
                    features[col] = player_data[col].mean()

        X_pred = np.array([list(features.values())])
        X_pred_scaled = self.scaler.transform(X_pred)

        # Make prediction
        pred_points = float(self.model.predict(X_pred_scaled)[0])
        pred_points = max(0, pred_points)  # No negative points

        # Confidence interval (±1 std of residuals)
        confidence_lower = pred_points - self.model_stats["std_error"]
        confidence_upper = pred_points + self.model_stats["std_error"]
        confidence_lower = max(0, confidence_lower)

        # Get trending info (recent vs earlier)
        if len(player_data) > 3:
            seasons_list = sorted(player_data["SEASON"].unique())
            recent_seasons = seasons_list[-3:]
            recent = player_data[player_data["SEASON"].isin(recent_seasons)]["PTS"].mean()
            historical = player_data[~player_data["SEASON"].isin(recent_seasons)]["PTS"].mean()
        else:
            recent = player_data["PTS"].mean()
            historical = recent

        return {
            "player": player_name,
            "predicted_points": round(pred_points, 2),
            "confidence_lower": round(confidence_lower, 2),
            "confidence_upper": round(confidence_upper, 2),
            "std_error": round(self.model_stats["std_error"], 2),
            "minutes_used": round(minutes, 1),
            "recent_avg": round(recent, 2),
            "historical_avg": round(historical, 2),
            "trend": "UP" if recent > historical else "DOWN",
            "trend_pct": round((recent / historical - 1) * 100, 1) if historical > 0 else 0,
            "model_r2": round(self.model_stats["r2"], 4),
            "model_mae": round(self.model_stats["mae"], 2),
        }

    def calculate_ev_plus(self, predicted_points: float, market_odds: float, line: float) -> dict:
        """
        Calculate EV+ (Expected Value Plus) for betting

        Args:
            predicted_points: Model's prediction
            market_odds: Decimal odds from sportsbook
            line: Line from sportsbook (e.g., 25.5)

        Returns:
            Dict with EV+ metrics and recommendation
        """
        # Calculate implicit win probability from odds
        # odds = 1 / probability (for a bet to "win" against the line)
        # EV = (prob_win * payoff) - (prob_loss * stake)
        # For simpler version: EV+ = (predicted / line * odds) - 1

        implicit_prob = 1 / market_odds if market_odds > 0 else 0

        # Probability our prediction goes OVER the line
        # Assuming normal distribution with our predicted_points and std_error
        z_score = (line - predicted_points) / (self.model_stats["std_error"] + 0.1)
        from scipy.stats import norm

        prob_over = 1 - norm.cdf(z_score)

        # EV calculation
        # If betting OVER: win if predicted > line
        ev_plus = (prob_over * (market_odds - 1)) - ((1 - prob_over) * 1)
        ev_plus_pct = ev_plus * 100

        # Classificação
        if ev_plus_pct > 5:
            signal = "FORTE COMPRA"
            color = "green"
        elif ev_plus_pct > 0:
            signal = "VALOR JUSTO"
            color = "blue"
        elif ev_plus_pct > -5:
            signal = "MARGINAL"
            color = "orange"
        else:
            signal = "EVITAR"
            color = "red"

        return {
            "predicted_points": predicted_points,
            "line": line,
            "market_odds": market_odds,
            "implied_probability": round(implicit_prob, 4),
            "model_probability": round(prob_over, 4),
            "ev_plus": round(ev_plus, 4),
            "ev_plus_pct": round(ev_plus_pct, 2),
            "kelly_criterion": round(prob_over * market_odds - 1, 4),  # Kelly %
            "signal": signal,
            "color": color,
            "recommendation": "OVER" if ev_plus > 0 else "UNDER",
        }

    def get_player_comparison(self, player_name: str, position: Optional[str] = None) -> pd.DataFrame:
        """Get peer comparison stats"""
        if self.df is None:
            return pd.DataFrame()

        player_data = self.df[self.df["PLAYER_NAME"] == player_name]
        if len(player_data) == 0:
            return pd.DataFrame()

        # Get position if not provided
        if not position and "POS" in self.df.columns:
            position = player_data["POS"].mode()[0]

        # Filter peers (same position, similar minutes)
        if position:
            peers = self.df[self.df["POS"] == position].copy()
        else:
            peers = self.df.copy()

        player_avg_min = player_data["MIN"].mean()
        peers = peers[(peers["MIN"] >= player_avg_min * 0.7) & (peers["MIN"] <= player_avg_min * 1.3)].copy()

        # Aggregate per player
        peer_stats = peers.groupby("PLAYER_NAME").agg({"PTS": "mean", "MIN": "mean", "FG_PCT": "mean", "AST": "mean", "REB": "mean"}).reset_index()

        peer_stats.columns = ["Player", "Avg PTS", "Avg MIN", "FG%", "AST", "REB"]
        peer_stats = peer_stats.sort_values("Avg PTS", ascending=False).head(15)

        return peer_stats


def load_or_train_model(data_path: str, model_cache_path: Optional[str] = None):
    """Carrega modelo em cache ou treina um novo"""
    predictor = NBAPointsPredictor(data_path)
    predictor.train()

    # Fazer cache do modelo
    if model_cache_path:
        import joblib

        joblib.dump(predictor, model_cache_path)

    return predictor
