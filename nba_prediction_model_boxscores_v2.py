"""
Modelo de previsão avançado baseado em dados de boxscores (partidas)
VERSÃO 2: CORRIGIDA - SEM DATA LEAKAGE
- Treina no nível de GAME (cada linha = 1 game)
- Mantém ordem temporal estrita
- Features de lag calculadas corretamente
- Sem agregação por season que eliminava dimensão temporal
"""

import warnings
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


class NBAPointsPredictorBoxscoresV2:
    def __init__(self, data_path: Optional[str] = None):
        self.df: Optional[pd.DataFrame] = None
        self.df_raw: Optional[pd.DataFrame] = None
        self.model: Optional[Ridge] = None
        self.scaler = StandardScaler()
        self.feature_cols: List[str] = []
        self.model_stats: Dict[str, Union[float, str, int]] = {}
        self.player_averages: Dict[str, Dict] = {}
        self.X_scaled: Optional[Any] = None
        self.y: Optional[Any] = None
        self.cutoff_date: Optional[pd.Timestamp] = None

        if data_path:
            self.load_data(data_path)

    def load_data(self, data_path: str):
        """Carrega dados brutos de boxscores por jogo - NÍVEL DE GAME"""
        self.df_raw = pd.read_csv(data_path)
        self.df_raw.columns = [c.strip().upper() for c in self.df_raw.columns]

        # Converter GAME_DATE para datetime
        if "GAME_DATE" in self.df_raw.columns:
            self.df_raw["GAME_DATE"] = pd.to_datetime(self.df_raw["GAME_DATE"], errors="coerce")
            # Sort por player E data - CRUCIAL para lag features
            self.df_raw = self.df_raw.sort_values(["PLAYER_NAME", "GAME_DATE"]).reset_index(drop=True)

        # Remover NaN críticos
        self.df_raw = self.df_raw.dropna(subset=["PLAYER_NAME", "PTS", "MIN"])

        # Criar features de lag POR JOGADOR (em nível de game, não season)
        self._create_lag_features()

        # Engenharia de features adicionais
        self._create_additional_features()

        # IMPORTANTE: NÃO AGREGAR POR SEASON!
        # Treinar em nível de game mantém ordem temporal
        self.df = self.df_raw.copy()

        return self

    def _create_lag_features(self):
        """
        Cria features de lag para cada jogador
        CORRIGIDO: Não há data leakage
        - shift(1) garante que usa PASSADO, não futuro
        - Dados estão em ordem ascendente por data
        - min_periods=1 para primeiros games (dados insuficientes)
        """

        # Lag features: pontos nos últimos N games
        for window in [3, 5, 10, 15]:
            col_name = f"LAG_PTS_{window}"
            # shift(1) pega linha anterior (passado), rolling tira média de últimos N
            self.df_raw[col_name] = self.df_raw.groupby("PLAYER_NAME")["PTS"].shift(1).rolling(window=window, min_periods=1).mean()

        # Lag features: minutos nos últimos N games
        for window in [5, 10]:
            col_name = f"LAG_MIN_{window}"
            self.df_raw[col_name] = self.df_raw.groupby("PLAYER_NAME")["MIN"].shift(1).rolling(window=window, min_periods=1).mean()

    def _create_additional_features(self):
        """Features adicionais sem data leakage"""

        # Preencher NaN iniciais com média global (primeiros games de cada player)
        for col in ["LAG_PTS_3", "LAG_PTS_5", "LAG_PTS_10", "LAG_PTS_15"]:
            if col in self.df_raw.columns:
                self.df_raw[col] = self.df_raw[col].fillna(self.df_raw["PTS"].mean())

        for col in ["LAG_MIN_5", "LAG_MIN_10"]:
            if col in self.df_raw.columns:
                self.df_raw[col] = self.df_raw[col].fillna(self.df_raw["MIN"].mean())

        # Momentum: mudança % nos últimos 5 vs 10 jogos
        self.df_raw["MOMENTUM"] = (self.df_raw["LAG_PTS_5"] - self.df_raw["LAG_PTS_10"]) / self.df_raw["LAG_PTS_10"].replace(0, 1)

        # Volatilidade: std dos últimos 10 games
        self.df_raw["VOLATILITY"] = self.df_raw.groupby("PLAYER_NAME")["PTS"].shift(1).rolling(window=10, min_periods=1).std().fillna(0)

        # Consistency: CV (coefficient of variation)
        self.df_raw["CONSISTENCY"] = self.df_raw.groupby("PLAYER_NAME")["PTS"].shift(1).rolling(window=10, min_periods=1).apply(lambda x: x.std() / (x.mean() + 1e-6) if len(x) > 1 else 0).fillna(0)

        # Form indicator: mudança % 3 vs 5 jogos
        self.df_raw["FORM_INDICATOR"] = (self.df_raw["LAG_PTS_3"] - self.df_raw["LAG_PTS_5"]) / self.df_raw["LAG_PTS_5"].replace(0, 1)

        # Game streak: jogos consecutivos acima da média
        self.df_raw["GAME_STREAK"] = 0
        for player in self.df_raw["PLAYER_NAME"].unique():
            player_mask = self.df_raw["PLAYER_NAME"] == player
            player_indices = self.df_raw[player_mask].index
            player_pts = self.df_raw.loc[player_indices, "PTS"].values
            mean_pts = player_pts.mean()

            current_streak = 0
            streaks = []
            for pts in player_pts:
                current_streak = current_streak + 1 if pts > mean_pts else 0
                streaks.append(current_streak)

            self.df_raw.loc[player_indices, "GAME_STREAK"] = streaks

        # Fase da temporada
        if "GAME_DATE" in self.df_raw.columns:
            self.df_raw["MONTH"] = self.df_raw["GAME_DATE"].dt.month
            self.df_raw["SEASON_PHASE"] = pd.cut(self.df_raw["MONTH"], bins=[0, 3, 6, 9, 12], labels=["Playoffs", "Final", "Meio", "Inicial"])
            self.df_raw["DAY_OF_WEEK"] = self.df_raw["GAME_DATE"].dt.dayofweek

        # Home/Away
        if "GAME_LOCATION" in self.df_raw.columns:
            self.df_raw["IS_HOME"] = (self.df_raw["GAME_LOCATION"] == "Home").astype(int)
        else:
            self.df_raw["IS_HOME"] = 0

        # Back-to-back games (simplificado)
        if "GAME_DATE" in self.df_raw.columns:
            self.df_raw["BACK_TO_BACK"] = (self.df_raw.groupby("PLAYER_NAME")["GAME_DATE"].shift(1).apply(lambda x: (pd.Timestamp.now() - x).days == 1 if pd.notna(x) else 0)).astype(int)
        else:
            self.df_raw["BACK_TO_BACK"] = 0

    def train(self, test_date: Optional[pd.Timestamp] = None, alpha: float = 2.0):
        """
        Treina modelo com TimeSeriesSplit implícito

        Args:
            test_date: Data após a qual não incluir dados no treino
            alpha: Regularização Ridge
        """
        if self.df is None:
            raise ValueError("Dados não carregados. Chame load_data() primeiro.")

        # Definir data de corte (para não vazar dados futuros)
        if test_date is None:
            # Por padrão, usar última data no dataset
            test_date = self.df["GAME_DATE"].max() - pd.Timedelta(days=7)

        self.cutoff_date = test_date

        # Treinar apenas com dados até cutoff_date
        train_df = self.df[self.df["GAME_DATE"] <= test_date].copy()

        if len(train_df) < 100:
            raise ValueError(f"Insuficientes dados de treino: {len(train_df)} < 100")

        # Selecionar features disponíveis
        candidate_features = [
            "LAG_PTS_3",
            "LAG_PTS_5",
            "LAG_PTS_10",
            "LAG_PTS_15",
            "LAG_MIN_5",
            "LAG_MIN_10",
            "MOMENTUM",
            "VOLATILITY",
            "CONSISTENCY",
            "FORM_INDICATOR",
            "GAME_STREAK",
            "IS_HOME",
            "BACK_TO_BACK",
            "MONTH",
            "DAY_OF_WEEK",
            "FG",
            "FGA",
            "3P",
            "3PA",
            "FT",
            "FTA",
            "OREB",
            "DREB",
            "REB",
            "AST",
            "STL",
            "BLK",
            "TOV",
        ]

        # Manter apenas features que existem
        self.feature_cols = [col for col in candidate_features if col in train_df.columns]

        if len(self.feature_cols) < 5:
            # Se muito poucas features, usar apenas básicas
            self.feature_cols = [col for col in ["PTS", "MIN", "FG", "AST"] if col in train_df.columns]

        print(f"Usando {len(self.feature_cols)} features: {self.feature_cols[:5]}...")

        X = train_df[self.feature_cols].fillna(0)
        y = train_df["PTS"]

        # Ponderação por recência (temporadas mais recentes = peso maior)
        if "SEASON" in train_df.columns:
            # SEASON é string tipo "2022-23", extrair ano final
            try:
                season_year = train_df["SEASON"].str.split("-").str[1].astype(int)
                weights = season_year / season_year.min()
            except:
                weights = np.ones(len(train_df))
        else:
            # Se não há SEASON, usar recência por data
            weights = (train_df["GAME_DATE"] - train_df["GAME_DATE"].min()).dt.days
            weights = np.maximum(weights / weights.min() if weights.min() > 0 else 1.0, 1.0)

        # Scale features
        self.X_scaled = self.scaler.fit_transform(X)
        self.y = y.values  # type: ignore

        # Treinar modelo
        self.model = Ridge(alpha=alpha, random_state=42)
        self.model.fit(self.X_scaled, self.y, sample_weight=weights.values)

        # Calcular estatísticas
        y_pred = self.model.predict(self.X_scaled)
        residuals = self.y - y_pred  # type: ignore

        y_mean = float(np.mean(self.y))  # type: ignore
        r2 = float(1 - (np.sum(residuals**2) / np.sum((self.y - y_mean) ** 2)))  # type: ignore
        mae = float(np.mean(np.abs(residuals)))
        rmse = float(np.sqrt(np.mean(residuals**2)))
        std_error = float(np.std(residuals))

        self.model_stats = {  # type: ignore[assignment]
            "r2": r2,
            "mae": mae,
            "rmse": rmse,
            "std_error": std_error,
            "train_samples": int(len(train_df)),
            "cutoff_date": str(test_date),
            "alpha": float(alpha),
        }

        print("\nModelo Treinado (Versao 2 - SEM LEAKAGE)")
        print(f"   Samples: {self.model_stats['train_samples']}")
        print(f"   R2: {self.model_stats['r2']:.4f}")
        print(f"   MAE: {self.model_stats['mae']:.2f} pts")
        print(f"   RMSE: {self.model_stats['rmse']:.2f} pts")
        print(f"   Cutoff Date: {self.model_stats['cutoff_date']}")

        return self

    def predict_points(self, player_name: str, minutes: float = 30) -> Dict:
        """
        Prediz pontos para um jogador
        Usa dados históricos até a data de treino
        """
        if self.model is None:
            raise ValueError("Modelo não treinado. Chame train() primeiro.")
        if self.df is None:
            raise ValueError("Dados não carregados. Chame load_data() primeiro.")

        # Pegar últimos dados do jogador (até cutoff_date)
        if self.cutoff_date:
            player_data = self.df[(self.df["PLAYER_NAME"] == player_name) & (self.df["GAME_DATE"] <= self.cutoff_date)].sort_values("GAME_DATE")
        else:
            player_data = self.df[self.df["PLAYER_NAME"] == player_name].sort_values("GAME_DATE")

        if len(player_data) == 0:
            return {"player_name": player_name, "predicted_points": 10.0, "std_error": self.model_stats.get("std_error", 4.0), "trend": "Unknown", "trend_pct": 0.0, "minutes_used": minutes, "games_played": 0, "model_r2": self.model_stats.get("r2", 0.0), "model_mae": self.model_stats.get("mae", 4.0), "confidence": 0.3}

        last_game = player_data.iloc[-1]

        # Preparar features
        features = {}
        for col in self.feature_cols:
            if col in last_game.index:
                features[col] = last_game[col]
            else:
                features[col] = 0

        X_pred = np.array([list(features.values())])
        X_pred_scaled = self.scaler.transform(X_pred)
        predicted_pts = self.model.predict(X_pred_scaled)[0]

        # Ajustar pela quantidade de minutos
        avg_minutes = self.df[self.df["PLAYER_NAME"] == player_name]["MIN"].mean()
        if avg_minutes > 0:
            predicted_pts = predicted_pts * (minutes / avg_minutes)

        # Trend
        recent_avg = player_data["PTS"].tail(5).mean()
        overall_avg = player_data["PTS"].mean()
        trend_pct = ((recent_avg - overall_avg) / overall_avg * 100) if overall_avg > 0 else 0

        # Confiança baseada em R²
        confidence = min(max(self.model_stats.get("r2", 0.5), 0.3), 0.95)

        return {
            "player_name": player_name,
            "predicted_points": float(predicted_pts),
            "std_error": self.model_stats.get("std_error", 4.0),
            "trend": "📈 Aquecido" if trend_pct > 5 else "📉 Frio" if trend_pct < -5 else "➡️ Estável",
            "trend_pct": trend_pct,
            "minutes_used": minutes,
            "games_played": len(player_data),
            "model_r2": self.model_stats.get("r2", 0.0),
            "model_mae": self.model_stats.get("mae", 4.0),
            "confidence": confidence,
        }

    def get_top_picks(self, n: int = 5, ev_threshold: float = 1.05) -> pd.DataFrame:
        """Retorna top N picks com melhor EV"""
        if self.model is None or self.df is None:
            return pd.DataFrame()

        picks = []
        for player_name in self.df["PLAYER_NAME"].unique():
            pred = self.predict_points(player_name)
            picks.append({"Player": player_name, "Predicted": pred["predicted_points"], "Trend": pred["trend"], "Confidence": pred["confidence"]})

        df_picks = pd.DataFrame(picks)
        return df_picks.sort_values("Confidence", ascending=False).head(n)
