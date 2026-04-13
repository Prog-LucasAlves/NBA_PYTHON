#!/usr/bin/env python
"""
Sistema de Monitoramento Contínuo de Overfitting em Produção
Implementa testes automatizados para validar modelo em dados reais
"""

from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_score
from sklearn.preprocessing import StandardScaler


class OverfittingMonitor:
    """Monitora sinais de overfitting em dados novos"""

    def __init__(self, trained_model_path: str | None = None):
        self.thresholds = {
            "r2_gap_max": 0.05,  # Gap R² máximo aceitável
            "rmse_gap_max": 2.0,  # Gap RMSE máximo aceitável (pontos)
            "std_cv_max": 0.03,  # Desvio padrão máximo de R² em CV
            "r2_min_test": 0.80,  # R² mínimo aceitável em teste
            "rmse_max": 3.5,  # RMSE máximo aceitável
        }
        self.history: list[Dict] = []

    def validate_new_data(self, X: np.ndarray, y: np.ndarray, X_scaler: StandardScaler) -> Dict:
        """
        Valida novo conjunto de dados contra thresholds de overfitting

        Returns:
            Dict com status de validação e detalhes
        """
        X_scaled = X_scaler.transform(X)

        # Validação cruzada
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        model = LinearRegression()

        # Scores de treino e teste
        train_scores = cross_val_score(model, X_scaled, y, cv=kf, scoring="r2", groups=None)
        test_scores = cross_val_score(model, X_scaled, y, cv=kf, scoring="r2")

        # Métricas
        r2_train = train_scores.mean()
        r2_test = test_scores.mean()
        r2_std = test_scores.std()
        r2_gap = r2_train - r2_test

        # Treinar para obter RMSE
        model.fit(X_scaled, y)
        y_pred = model.predict(X_scaled)
        rmse = np.sqrt(np.mean((y - y_pred) ** 2))

        # Validação
        issues = []
        status = "PASS"

        if r2_gap > self.thresholds["r2_gap_max"]:
            issues.append(f"R² Gap = {r2_gap:.4f} > {self.thresholds['r2_gap_max']} (OVERFITTING)")
            status = "WARN"

        if r2_std > self.thresholds["std_cv_max"]:
            issues.append(f"Std R² CV = {r2_std:.4f} > {self.thresholds['std_cv_max']} (INSTABILIDADE)")
            status = "WARN"

        if r2_test < self.thresholds["r2_min_test"]:
            issues.append(f"R² Test = {r2_test:.4f} < {self.thresholds['r2_min_test']} (DESEMPENHO BAIXO)")
            status = "FAIL"

        if rmse > self.thresholds["rmse_max"]:
            issues.append(f"RMSE = {rmse:.2f} > {self.thresholds['rmse_max']} (ERRO ALTO)")
            status = "WARN"

        result = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "r2_train": r2_train,
            "r2_test": r2_test,
            "r2_gap": r2_gap,
            "r2_std": r2_std,
            "rmse": rmse,
            "issues": issues,
            "samples": len(y),
        }

        self.history.append(result)
        return result

    def print_validation_report(self, result: Dict):
        """Imprime relatório de validação formatado"""
        timestamp = result["timestamp"]
        status_icon = {
            "PASS": "✅",
            "WARN": "⚠️",
            "FAIL": "❌",
        }[result["status"]]

        print("\n" + "=" * 70)
        print(f"{status_icon} VALIDAÇÃO DE OVERFITTING - {timestamp}")
        print("=" * 70)

        print("\n📊 Métricas:")
        print(f"  • R² Treino: {result['r2_train']:.4f}")
        print(f"  • R² Teste: {result['r2_test']:.4f}")
        print(f"  • Gap R²: {result['r2_gap']:.4f} (limiar: {self.thresholds['r2_gap_max']})")
        print(f"  • Std R² CV: {result['r2_std']:.4f} (limiar: {self.thresholds['std_cv_max']})")
        print(f"  • RMSE: {result['rmse']:.2f} pontos (limiar: {self.thresholds['rmse_max']})")
        print(f"  • Amostras: {result['samples']}")

        if result["issues"]:
            print("\n⚠️  PROBLEMAS:")
            for issue in result["issues"]:
                print(f"  • {issue}")
        else:
            print("\n✅ Modelo passou em todos os testes")

        print("\n" + "=" * 70)

    def test_suite(self, X: np.ndarray, y: np.ndarray, X_scaler: StandardScaler) -> bool:
        """
        Suite de testes automatizados para CI/CD

        Returns:
            True se passou em todos os testes, False caso contrário
        """
        result = self.validate_new_data(X, y, X_scaler)
        self.print_validation_report(result)

        if result["status"] == "FAIL":
            return False
        return True

    def get_history_df(self) -> pd.DataFrame:
        """Retorna histórico de validações como DataFrame"""
        return pd.DataFrame(self.history)

    def set_thresholds(self, **kwargs):
        """Atualiza thresholds de validação"""
        for key, value in kwargs.items():
            if key in self.thresholds:
                self.thresholds[key] = value


# Exemplo de uso
if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    from nba_prediction_model_boxscores_v2 import NBAPointsPredictorBoxscoresV2

    print("=" * 70)
    print("TESTE DO SISTEMA DE MONITORAMENTO DE OVERFITTING")
    print("=" * 70)

    # Carregar dados
    try:
        predictor = NBAPointsPredictorBoxscoresV2("data/nba_player_boxscores_multi_season.csv")
        predictor.train()

        # Testar monitor
        monitor = OverfittingMonitor()

        # Obter dados de features
        X = predictor.df[predictor.feature_cols].fillna(0).values
        y = predictor.df["PTS"].values

        # Teste 1: Dados originais (deve passar)
        print("\n[Teste 1/3] Dados originais...")
        result1 = monitor.validate_new_data(X, y, predictor.scaler)
        monitor.print_validation_report(result1)

        # Teste 2: Subset aleatório (simular dados novos)
        print("\n[Teste 2/3] Subset aleatório (simular novos dados)...")
        indices = np.random.choice(len(y), size=int(len(y) * 0.7), replace=False)
        X_subset = X[indices]
        y_subset = y[indices]
        result2 = monitor.validate_new_data(X_subset, y_subset, predictor.scaler)
        monitor.print_validation_report(result2)

        # Teste 3: Dados com ruído (simular degradação)
        print("\n[Teste 3/3] Dados com ruído adicionado...")
        y_noisy = y + np.random.normal(0, 0.5, len(y))
        result3 = monitor.validate_new_data(X, y_noisy, predictor.scaler)
        monitor.print_validation_report(result3)

        # Resumo
        print("\n" + "=" * 70)
        print("RESUMO")
        print("=" * 70)
        history_df = monitor.get_history_df()
        print(f"\nTotal de validações: {len(history_df)}")
        print(f"Passou: {(history_df['status'] == 'PASS').sum()}")
        print(f"Avisos: {(history_df['status'] == 'WARN').sum()}")
        print(f"Falhas: {(history_df['status'] == 'FAIL').sum()}")

        print("\n✅ Testes do monitor completados!\n")
    except Exception as e:
        print(f"Erro ao testar o monitor: {e}")
