"""
Monitoramento Automático do Modelo de Predição em Tempo Real
Rastreia acurácia, degeneração e alertas automáticos
"""

import json
import logging
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AutomaticModelMonitor:
    """
    Monitora automaticamente o desempenho do modelo em tempo real.
    Salva histórico de predições, calcula erros e detecta degradação.
    """

    def __init__(self, monitor_file: str = "model_monitoring.json"):
        self.monitor_file = monitor_file
        self.history: list[dict] = self._load_history()
        self.thresholds = {
            "mae_critical": 2.5,  # Erro absoluto crítico em pontos
            "mae_warning": 1.8,  # Aviso em pontos
            "rmse_critical": 3.5,
            "rmse_warning": 2.5,
            "accuracy_warning": 0.80,  # 80% de acerto
            "degradation_window": 50,  # últimas 50 predições
        }

    def _load_history(self) -> list[dict]:
        """Carrega histórico de predições do arquivo"""
        if not os.path.exists(self.monitor_file):
            return []

        try:
            with open(self.monitor_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar histórico: {e}")
            return []

    def _save_history(self) -> None:
        """Salva histórico de predições"""
        try:
            with open(self.monitor_file, "w") as f:
                json.dump(self.history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")

    def log_prediction(
        self,
        player_name: str,
        actual_pts: float,
        predicted_pts: float,
        confidence: float = 0.0,
    ) -> None:
        """
        Registra uma predição e seu resultado.

        Args:
            player_name: Nome do jogador
            actual_pts: Pontos reais obtidos
            predicted_pts: Pontos preditos
            confidence: Confiança da predição (0-1)
        """
        error = abs(actual_pts - predicted_pts)
        record = {
            "timestamp": datetime.now().isoformat(),
            "player": player_name,
            "actual": float(actual_pts),
            "predicted": float(predicted_pts),
            "error": float(error),
            "confidence": float(confidence),
            "is_accurate": error < 1.5,  # Considera acertado se erro < 1.5 pts
        }

        self.history.append(record)
        self._save_history()

        # Verifica se precisa alertar
        self._check_alerts(record)

    def _check_alerts(self, record: dict) -> None:
        """Verifica se há problemas e emite alertas"""
        error = record["error"]

        if error > self.thresholds["mae_critical"]:
            logger.error(f"❌ ERRO CRÍTICO: {record['player']} | Real: {record['actual']:.1f} pts | Previsto: {record['predicted']:.1f} pts | Erro: {error:.2f} pts")
        elif error > self.thresholds["mae_warning"]:
            logger.warning(f"⚠️  ERRO ALTO: {record['player']} | Real: {record['actual']:.1f} pts | Previsto: {record['predicted']:.1f} pts | Erro: {error:.2f} pts")

    def get_current_metrics(self) -> dict[str, float | int | str]:
        """Retorna métricas atuais do monitoramento"""
        if not self.history:
            return {
                "total_predictions": 0,
                "mae": 0.0,
                "rmse": 0.0,
                "accuracy": 0.0,
                "accuracy_percent": 0.0,
                "status": "Sem dados",
            }

        errors = np.array([r["error"] for r in self.history])
        accuracies = np.array([r["is_accurate"] for r in self.history])

        mae = float(np.mean(errors))
        rmse = float(np.sqrt(np.mean(errors**2)))
        accuracy = float(np.mean(accuracies))

        return {
            "total_predictions": len(self.history),
            "mae": mae,
            "rmse": rmse,
            "accuracy": accuracy,
            "accuracy_percent": accuracy * 100,
            "status": self._get_status(mae, rmse, accuracy),
        }

    def _get_status(self, mae: float, rmse: float, accuracy: float) -> str:
        """Determina status geral do modelo"""
        if mae > self.thresholds["mae_critical"] or rmse > self.thresholds["rmse_critical"]:
            return "❌ CRÍTICO"
        elif mae > self.thresholds["mae_warning"] or rmse > self.thresholds["rmse_warning"]:
            return "⚠️  AVISO"
        elif accuracy < self.thresholds["accuracy_warning"]:
            return "⚠️  ACURÁCIA BAIXA"
        else:
            return "✅ SAUDÁVEL"

    def get_degradation_analysis(self) -> dict[str, bool | int | float | str]:
        """Analisa degradação do modelo ao longo do tempo"""
        degradation_window = int(self.thresholds["degradation_window"])
        if len(self.history) < degradation_window:
            return {
                "has_degradation": False,
                "message": f"Apenas {len(self.history)} predições. Mínimo {degradation_window} para análise.",
            }

        # Últimas N predições
        recent = self.history[-degradation_window:]
        recent_mae = float(np.mean([r["error"] for r in recent]))

        # Predições anteriores
        if len(self.history) > degradation_window * 2:
            older = self.history[-degradation_window * 2 : -degradation_window]
            older_mae = float(np.mean([r["error"] for r in older]))

            degradation = ((recent_mae - older_mae) / older_mae) * 100 if older_mae > 0 else 0

            return {
                "has_degradation": degradation > 10,  # 10% piorou
                "degradation_percent": degradation,
                "recent_mae": recent_mae,
                "older_mae": older_mae,
                "message": f"Degradação: {degradation:+.1f}% | MAE recente: {recent_mae:.2f} | MAE anterior: {older_mae:.2f}",
            }

        return {"has_degradation": False, "message": "Histórico insuficiente para comparação"}

    def get_recent_predictions(self, n: int = 10) -> pd.DataFrame:
        """Retorna as últimas N predições"""
        if not self.history:
            return pd.DataFrame()

        recent = self.history[-n:]
        df = pd.DataFrame(recent)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp", ascending=False)

    def get_player_stats(self, player_name: str) -> dict:
        """Retorna estatísticas para um jogador específico"""
        player_records = [r for r in self.history if r["player"].lower() == player_name.lower()]

        if not player_records:
            return {"player": player_name, "predictions": 0, "message": "Sem histórico"}

        errors = np.array([r["error"] for r in player_records])
        accuracies = np.array([r["is_accurate"] for r in player_records])

        return {
            "player": player_name,
            "predictions": len(player_records),
            "mae": float(np.mean(errors)),
            "rmse": float(np.sqrt(np.mean(errors**2))),
            "accuracy_percent": float(np.mean(accuracies) * 100),
            "recent_10": len([r for r in player_records[-10:] if r["is_accurate"]]),
        }

    def get_player_rankings(self, min_predictions: int = 3, top_n: int = 10) -> pd.DataFrame:
        """Retorna ranking de jogadores com maior volume e erro médio."""
        if not self.history:
            return pd.DataFrame()

        df = pd.DataFrame(self.history)
        grouped = (
            df.groupby("player")
            .agg(
                predictions=("error", "count"),
                mae=("error", "mean"),
                rmse=("error", lambda x: float(np.sqrt(np.mean(np.square(x))))),
                accuracy_percent=("is_accurate", lambda x: float(np.mean(x) * 100)),
                avg_confidence=("confidence", "mean"),
            )
            .reset_index()
        )

        grouped = grouped[grouped["predictions"] >= min_predictions].sort_values(["mae", "predictions"], ascending=[False, False])
        return grouped.head(top_n).reset_index(drop=True)

    def get_line_range_stats(self, bins: list[float] | None = None) -> pd.DataFrame:
        """Retorna métricas por faixa de linha prevista."""
        if not self.history:
            return pd.DataFrame()

        if bins is None:
            bins = [0, 5, 10, 15, 20, 25, 30, 100]

        df = pd.DataFrame(self.history)
        df["predicted_bin"] = pd.cut(df["predicted"], bins=bins, right=False, include_lowest=True)

        range_stats = (
            df.groupby("predicted_bin")
            .agg(
                predictions=("error", "count"),
                mae=("error", "mean"),
                rmse=("error", lambda x: float(np.sqrt(np.mean(np.square(x))))),
                accuracy_percent=("is_accurate", lambda x: float(np.mean(x) * 100)),
            )
            .reset_index()
        )

        range_stats["predicted_bin"] = range_stats["predicted_bin"].astype(str)
        return range_stats

    def get_daily_stats(self, days: int = 7) -> pd.DataFrame:
        """Retorna estatísticas diárias"""
        if not self.history:
            return pd.DataFrame()

        df = pd.DataFrame(self.history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date

        daily_stats = df.groupby("date").agg({"error": ["mean", "std", "max"], "is_accurate": "mean", "player": "count"}).round(3)
        daily_stats.columns = ["MAE", "STD_ERROR", "MAX_ERROR", "ACCURACY", "PREDICTIONS"]
        daily_stats = daily_stats.reset_index()
        daily_stats["ACCURACY"] = (daily_stats["ACCURACY"] * 100).round(1)

        return daily_stats.tail(days)

    def export_report(self, output_file: str = "monitoring_report.csv") -> None:
        """Exporta histórico completo para CSV"""
        if not self.history:
            logger.warning("Nenhum histórico para exportar")
            return

        df = pd.DataFrame(self.history)
        df.to_csv(output_file, index=False)
        logger.info(f"✅ Relatório exportado: {output_file}")

    def clear_old_history(self, days: int = 30) -> None:
        """Remove histórico com mais de N dias"""
        cutoff_date = datetime.now() - timedelta(days=days)
        original_count = len(self.history)

        self.history = [r for r in self.history if datetime.fromisoformat(r["timestamp"]) > cutoff_date]

        self._save_history()
        logger.info(f"🧹 Limpeza: {original_count} → {len(self.history)} registros")


# ============================================================================
# EXEMPLO DE USO (para testes)
# ============================================================================

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    monitor = AutomaticModelMonitor()

    # Simula predições
    test_data = [
        ("LeBron James", 32.5, 31.2, 0.92),
        ("Luka Doncic", 28.3, 30.1, 0.88),
        ("Giannis Antetokounmpo", 26.1, 22.5, 0.85),  # Erro grande
        ("Kevin Durant", 25.7, 26.3, 0.90),
        ("Stephen Curry", 24.5, 28.2, 0.87),  # Erro grande
    ]

    print("\n🔄 Registrando predições...\n")
    for player, actual, predicted, conf in test_data:
        monitor.log_prediction(player, actual, predicted, conf)
        print(f"  {player}: {actual:.1f} pts (real) vs {predicted:.1f} pts (pred)")

    print("\n" + "=" * 70)
    print("📊 MÉTRICAS ATUAIS")
    print("=" * 70)
    metrics = monitor.get_current_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key:.<30} {value:>10.4f}")
        else:
            print(f"  {key:.<30} {str(value):>10}")

    print("\n" + "=" * 70)
    print("📈 DEGRADAÇÃO")
    print("=" * 70)
    degradation = monitor.get_degradation_analysis()
    for key, value in degradation.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("🎮 PREDIÇÕES RECENTES")
    print("=" * 70)
    print(monitor.get_recent_predictions(5))

    print("\n" + "=" * 70)
    print("👤 ESTATÍSTICAS POR JOGADOR")
    print("=" * 70)
    for player, _, _, _ in test_data:
        stats = monitor.get_player_stats(player)
        print(f"  {player}:")
        for k, v in stats.items():
            if k != "player":
                print(f"    {k}: {v}")
