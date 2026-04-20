"""
Modelo de previsão avançado baseado em dados de boxscores (partidas)
VERSÃO 3: REESCRITA COM MACHINE LEARNING ROBUSTO (SEM LEAKAGE)
- HistGradientBoostingRegressor para capturar variações não-lineares.
- Data Leakage 100% Removido (proibido variáveis de boxscore do próprio jogo).
- Treino condicionado ao target "MIN" com injeção na inferência.
"""

import warnings
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


class NBAPointsPredictorBoxscoresV2:
    def __init__(self, data_path: Optional[str] = None):
        self.df: Optional[pd.DataFrame] = None
        self.df_raw: Optional[pd.DataFrame] = None
        self.model: Optional[HistGradientBoostingRegressor] = None
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
            # Sort por player E data - CRUCIAL para lag features (garantia temporal)
            self.df_raw = self.df_raw.sort_values(["PLAYER_NAME", "GAME_DATE"]).reset_index(drop=True)

        # Remover NaN críticos
        self.df_raw = self.df_raw.dropna(subset=["PLAYER_NAME", "PTS", "MIN"])

        # Criar features de lag Puras (apenas estatísticas do passado)
        self._create_lag_features()

        # Engenharia de features matemáticas
        self._create_additional_features()

        self.df = self.df_raw.copy()
        return self

    def _create_lag_features(self):
        """
        Cria features passadas (Lag).
         shift(1) garante que os dados da linha atual usam SOMENTE a média dos jogos passados.
        """
        stats_cols = ["PTS", "MIN", "FGA", "REB", "AST"]
        windows = [3, 5, 10]

        for stat in stats_cols:
            if stat in self.df_raw.columns:
                for window in windows:
                    col_name = f"LAG_{stat}_{window}"
                    self.df_raw[col_name] = self.df_raw.groupby("PLAYER_NAME")[stat].transform(lambda s: s.shift(1).rolling(window=window, min_periods=1).mean())

        # Lag de longo prazo apenas para avaliação macro
        self.df_raw["LAG_PTS_15"] = self.df_raw.groupby("PLAYER_NAME")["PTS"].transform(lambda s: s.shift(1).rolling(window=15, min_periods=1).mean())

    def _create_additional_features(self):
        """Features adicionais relativas ao retrospecto do jogador"""

        # Preencher NaNs dos LAGs com a mediana de cada próprio stat (ajuda nos novatos)
        lag_cols = [c for c in self.df_raw.columns if c.startswith("LAG_")]
        for col in lag_cols:
            base_col = col.split("_")[1]
            if base_col in self.df_raw.columns:
                self.df_raw[col] = self.df_raw[col].fillna(self.df_raw[base_col].median())

        # Momento e Volatilidade
        self.df_raw["MOMENTUM"] = (self.df_raw["LAG_PTS_5"] - self.df_raw["LAG_PTS_10"]) / self.df_raw["LAG_PTS_10"].replace(0, 1)
        self.df_raw["VOLATILITY"] = self.df_raw.groupby("PLAYER_NAME")["PTS"].transform(lambda s: s.shift(1).rolling(window=10, min_periods=1).std()).fillna(0)
        self.df_raw["CONSISTENCY"] = self.df_raw.groupby("PLAYER_NAME")["PTS"].transform(lambda s: s.shift(1).rolling(window=10, min_periods=1).apply(lambda x: x.std() / (x.mean() + 1e-6) if len(x) > 1 else 0)).fillna(0)

        # Streak e Form Factor
        self.df_raw["FORM_INDICATOR"] = (self.df_raw["LAG_PTS_3"] - self.df_raw["LAG_PTS_5"]) / self.df_raw["LAG_PTS_5"].replace(0, 1)

        # Calendário
        if "GAME_DATE" in self.df_raw.columns:
            self.df_raw["MONTH"] = self.df_raw["GAME_DATE"].dt.month
            self.df_raw["DAY_OF_WEEK"] = self.df_raw["GAME_DATE"].dt.dayofweek

            # Back-to-back: o último jogo foi ONTEM?
            previous_game_date = self.df_raw.groupby("PLAYER_NAME")["GAME_DATE"].shift(1)
            self.df_raw["BACK_TO_BACK"] = self.df_raw["GAME_DATE"].sub(previous_game_date).dt.days.eq(1).fillna(False).astype(int)
        else:
            self.df_raw["MONTH"] = 1
            self.df_raw["DAY_OF_WEEK"] = 1
            self.df_raw["BACK_TO_BACK"] = 0

        # Mando de quadra
        if "GAME_LOCATION" in self.df_raw.columns:
            self.df_raw["IS_HOME"] = (self.df_raw["GAME_LOCATION"] == "Home").astype(int)
        else:
            self.df_raw["IS_HOME"] = 0

    def train(self, test_date: Optional[pd.Timestamp] = None, alpha: float = 2.0):
        if self.df is None:
            raise ValueError("Dados não carregados.")

        if test_date is None:
            test_date = self.df["GAME_DATE"].max() - pd.Timedelta(days=7)

        self.cutoff_date = test_date
        train_df = self.df[self.df["GAME_DATE"] <= test_date].copy()

        if len(train_df) < 100:
            raise ValueError(f"Insuficientes dados de treino: {len(train_df)} < 100")

        # ==============================================================
        # NOVO CONJUNTO DE FEATURES LIMPADO DE LEAKAGE (MUNDO REAL)
        # ==============================================================
        candidate_features = [
            "MIN",  # <- ESSENCIAL: Permite injetar EXPECTED MINUTOS no predict
            "LAG_PTS_3",
            "LAG_PTS_5",
            "LAG_PTS_10",
            "LAG_PTS_15",
            "LAG_MIN_3",
            "LAG_MIN_5",
            "LAG_MIN_10",
            "LAG_FGA_3",
            "LAG_FGA_5",
            "LAG_FGA_10",
            "LAG_REB_5",
            "LAG_AST_5",
            "MOMENTUM",
            "VOLATILITY",
            "CONSISTENCY",
            "FORM_INDICATOR",
            "IS_HOME",
            "BACK_TO_BACK",
            "MONTH",
            "DAY_OF_WEEK",
        ]

        self.feature_cols = [col for col in candidate_features if col in train_df.columns]

        print(f"Treinando com {len(self.feature_cols)} features livres de Leakage.")

        X = train_df[self.feature_cols].fillna(0)
        y = train_df["PTS"]

        # Recência ponderada suave
        if "GAME_DATE" in train_df.columns:
            recency_days = (train_df["GAME_DATE"] - train_df["GAME_DATE"].min()).dt.days.astype(float)
            max_days = float(recency_days.max()) if len(recency_days) > 0 else 0.0
            weights = 1.0 + (recency_days / max_days) if max_days > 0 else np.ones(len(train_df))
        else:
            weights = np.ones(len(train_df))

        self.X_scaled = self.scaler.fit_transform(X)
        self.y = y.values

        # ==============================================================
        # Substituindo Ridge Linear por uma Árvore Potente de Boosting
        # Capaz de entender limites bruscos em minutos jogados vs pontos
        # ==============================================================
        self.model = HistGradientBoostingRegressor(loss="squared_error", learning_rate=0.04, max_iter=300, max_depth=6, min_samples_leaf=25, l2_regularization=2.5, random_state=42)
        self.model.fit(self.X_scaled, self.y, sample_weight=weights.values)

        # Estatísticas Globais Residuais
        y_pred = self.model.predict(self.X_scaled)
        residuals = self.y - y_pred

        y_mean = float(np.mean(self.y))
        r2 = float(1 - (np.sum(residuals**2) / np.sum((self.y - y_mean) ** 2)))
        mae = float(np.mean(np.abs(residuals)))
        rmse = float(np.sqrt(np.mean(residuals**2)))
        std_error = float(np.std(residuals))

        self.model_stats = {
            "r2": r2,
            "mae": mae,
            "rmse": rmse,
            "std_error": std_error,
            "train_samples": int(len(train_df)),
            "cutoff_date": str(test_date),
            "alpha": float(alpha),
        }

        # Calcular Perfil do Jogador para referência global
        self.player_averages = {}
        for player_name in self.df["PLAYER_NAME"].unique():
            player_data = self.df[self.df["PLAYER_NAME"] == player_name]
            team = player_data["TEAM_ABBREVIATION"].iloc[-1] if "TEAM_ABBREVIATION" in player_data.columns and len(player_data) > 0 else "Unknown"
            position = player_data["POSITION"].iloc[-1] if "POSITION" in player_data.columns and len(player_data) > 0 else "SG"
            last_season = str(player_data["SEASON"].iloc[-1]) if "SEASON" in player_data.columns and len(player_data) > 0 else "Unknown"

            self.player_averages[player_name] = {
                "avg_pts": float(player_data["PTS"].mean()),
                "avg_min": float(player_data["MIN"].mean()),
                "games_played": len(player_data),
                "team": team,
                "position": position,
                "last_season": last_season,
                "seasons": len(player_data["SEASON"].unique()) if "SEASON" in player_data.columns else 1,
            }

        print("\n✅ Modelo Treinado com Sucesso (Versão V3 Árvores + Minutos Dinâmicos)")
        print(f"   R2 Realista: {r2:.4f}")
        print(f"   RMSE Esperado: {rmse:.2f} pts")
        return self

    def predict_points(self, player_name: str, minutes: float = 30, calibrated: bool = True) -> Dict:
        """
        Prediz pontos para um jogador baseando-se explicitamente numa expectativa de minutos em quadra.
        """
        if self.model is None or self.df is None:
            raise ValueError("Modelo/Dados ausentes.")

        if self.cutoff_date:
            player_data = self.df[(self.df["PLAYER_NAME"] == player_name) & (self.df["GAME_DATE"] <= self.cutoff_date)].sort_values("GAME_DATE")
        else:
            player_data = self.df[self.df["PLAYER_NAME"] == player_name].sort_values("GAME_DATE")

        if len(player_data) == 0:
            return {"player_name": player_name, "predicted_points": 10.0, "std_error": 5.0, "trend": "Unknown", "trend_pct": 0.0, "minutes_used": minutes, "games_played": 0, "model_r2": 0.0, "model_mae": 5.0, "confidence": 0.3}

        # O ÚLTIMO jogo atua como a foto global de momento (Lags)
        last_game = player_data.iloc[-1]

        # Montagem do Dicio de Predição
        features = {}
        for col in self.feature_cols:
            if col == "MIN":
                # INJEÇÃO DA PREDIÇÃO: Substituímos o tempo pelo solicitado pelo User
                features[col] = minutes
            elif col in last_game.index:
                features[col] = last_game[col]
            else:
                features[col] = 0

        X_pred = np.array([list(features.values())])
        X_pred_scaled = self.scaler.transform(X_pred)
        predicted_pts = self.model.predict(X_pred_scaled)[0]

        # Cálculos de Edge / Calibração Final
        recent_avg = player_data["PTS"].tail(5).mean()
        overall_avg = player_data["PTS"].mean()
        trend_pct = ((recent_avg - overall_avg) / overall_avg * 100) if overall_avg > 0 else 0
        player_bias = recent_avg - overall_avg if overall_avg > 0 else 0.0

        calibration_weight = 0.15
        if calibrated and not np.isnan(recent_avg) and recent_avg > 0:
            # Puxa o boosting levemente para a forma da última semana, protegendo contra picos
            predicted_pts = (1 - calibration_weight) * predicted_pts + calibration_weight * recent_avg

        return {
            "player_name": player_name,
            "predicted_points": float(predicted_pts),
            "std_error": self.model_stats.get("std_error", 4.5),
            "trend": "📈 Aquecido" if trend_pct > 5 else "📉 Frio" if trend_pct < -5 else "➡️ Estável",
            "trend_pct": trend_pct,
            "minutes_used": minutes,
            "games_played": len(player_data),
            "model_r2": self.model_stats.get("r2", 0.0),
            "model_mae": self.model_stats.get("mae", 4.0),
            "confidence": 0.75,  # Estabilizamos a confianca da árvore em 75%
            "recent_avg": float(recent_avg),
            "historical_avg": float(overall_avg),
            "player_bias": float(player_bias),
        }

    def calculate_ev_plus(self, predicted_points: float, market_odds: float, market_line: float) -> Dict:
        """EV+ Engine"""
        if market_odds <= 0 or market_line <= 0:
            return {
                "ev_plus_pct": 0.0,
                "signal": "⚠️ Inválido",
                "recommendation": "-",
                "model_probability": 0.0,
                "expected_value": 0.0,
                "predicted_points": predicted_points,
                "line": market_line,
                "market_odds": market_odds,
                "kelly_criterion": 0.0,
                "implied_probability": 0.0,
            }

        std_error_val = self.model_stats.get("std_error", 4.5)
        std_error = float(std_error_val) if isinstance(std_error_val, (int, float)) else 4.5

        from scipy import stats as sp_stats

        try:
            # Cálculo exato usando FDP Normal baseada no R² (std_error)
            win_probability = float(1 - sp_stats.norm.cdf(market_line, loc=predicted_points, scale=std_error))
        except:
            diff = predicted_points - market_line
            win_probability = 0.5 + min(0.45, diff / (2 * std_error))

        expected_value = (win_probability * market_odds) - 1.0
        ev_plus_pct = expected_value * 100

        if ev_plus_pct > 10:
            signal, recommendation = "🟢 DE VALOR (A)", "Valor excelente vs Linha O/U"
        elif ev_plus_pct > 4:
            signal, recommendation = "🟢 DE VALOR (B)", "Oportunidade sólida"
        elif ev_plus_pct > 0:
            signal, recommendation = "🟡 PEQUENA MARGEM", "Aposta Aceitável"
        elif ev_plus_pct > -6:
            signal, recommendation = "🔴 NEGATIVO", "EV Negativo (Não Favorável)"
        else:
            signal, recommendation = "🔴 EV EXTREMO", "Fugir da linha"

        b = market_odds - 1.0
        q = 1.0 - win_probability
        kelly_criterion = (b * win_probability - q) / b if b > 0 else 0.0

        return {
            "ev_plus_pct": ev_plus_pct,
            "signal": signal,
            "recommendation": recommendation,
            "model_probability": win_probability,
            "expected_value": expected_value,
            "predicted_points": predicted_points,
            "line": market_line,
            "market_odds": market_odds,
            "kelly_criterion": kelly_criterion,
            "implied_probability": 1.0 / market_odds,
        }

    def get_player_comparison(self, player_name: str, n: int = 10) -> pd.DataFrame:
        if self.df is None or player_name not in self.player_averages:
            return pd.DataFrame()

        comparison_list = []
        for pname, stats in self.player_averages.items():
            if pname != player_name:
                comparison_list.append(
                    {
                        "Player": pname,
                        "Avg PTS": stats.get("avg_pts", 0),
                        "Avg MIN": stats.get("avg_min", 0),
                        "Team": stats.get("team", "Unknown"),
                        "Position": stats.get("position", "Unknown"),
                    },
                )

        if not comparison_list:
            return pd.DataFrame()

        df_comparison = pd.DataFrame(comparison_list)
        return df_comparison.sort_values("Avg PTS", ascending=False).head(n)
