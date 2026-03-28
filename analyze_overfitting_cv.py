#!/usr/bin/env python
"""
Análise Completa de Overfitting e Validação Cruzada
Detecta sinais de overfitting e valida a generalização do modelo
"""

import warnings
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import (
    KFold,
    cross_val_predict,
    cross_validate,
    learning_curve,
)

from nba_prediction_model import NBAPointsPredictor

warnings.filterwarnings("ignore")


class OverfittingAnalyzer:
    """Analisa sinais de overfitting no modelo de previsão"""

    def __init__(self, data_path: str):
        self.predictor = NBAPointsPredictor(data_path)
        self.predictor.load_data(data_path)
        self.X, self.y, self.weights = self.predictor.build_features()
        self.X_scaled = self.predictor.scaler.fit_transform(self.X)

    def analyze_overfitting(self) -> Dict:
        """
        Análise completa de overfitting:
        - Treinar no dataset completo
        - Comparar com validação cruzada
        - Detectar padrões de overfitting
        """
        print("\n" + "=" * 70)
        print("ANÁLISE DE OVERFITTING")
        print("=" * 70)

        # 1. Treinar no dataset completo
        model = LinearRegression()
        model.fit(self.X_scaled, self.y, sample_weight=self.weights)
        y_pred_train = model.predict(self.X_scaled)

        # Métricas no dataset completo
        r2_train = r2_score(self.y, y_pred_train)
        rmse_train = np.sqrt(mean_squared_error(self.y, y_pred_train))
        mae_train = mean_absolute_error(self.y, y_pred_train)

        print("\n📊 TREINO (Dataset Completo):")
        print(f"  • R² Score: {r2_train:.4f}")
        print(f"  • RMSE: {rmse_train:.2f} pontos")
        print(f"  • MAE: {mae_train:.2f} pontos")

        # 2. Validação cruzada K-Fold
        print("\n🔄 VALIDAÇÃO CRUZADA (K-Fold, k=5):")
        cv_results = cross_validate(
            LinearRegression(),
            self.X_scaled,
            self.y,
            cv=KFold(n_splits=5, shuffle=True, random_state=42),
            scoring=["r2", "neg_mean_squared_error", "neg_mean_absolute_error"],
            return_train_score=True,
        )

        # Processar resultados de CV
        cv_r2_train = cv_results["train_r2"].mean()
        cv_r2_test = cv_results["test_r2"].mean()
        cv_r2_std = cv_results["test_r2"].std()

        cv_rmse_train = np.sqrt(-cv_results["train_neg_mean_squared_error"].mean())
        cv_rmse_test = np.sqrt(-cv_results["test_neg_mean_squared_error"].mean())
        cv_rmse_std = np.sqrt(-cv_results["test_neg_mean_squared_error"]).std()

        cv_mae_train = -cv_results["train_neg_mean_absolute_error"].mean()
        cv_mae_test = -cv_results["test_neg_mean_absolute_error"].mean()
        cv_mae_std = -cv_results["test_neg_mean_absolute_error"].std()

        print("\n  📈 Treino (média CV):")
        print(f"     • R² Score: {cv_r2_train:.4f}")
        print(f"     • RMSE: {cv_rmse_train:.2f} pontos")
        print(f"     • MAE: {cv_mae_train:.2f} pontos")

        print("\n  📉 Teste (média CV):")
        print(f"     • R² Score: {cv_r2_test:.4f} (±{cv_r2_std:.4f})")
        print(f"     • RMSE: {cv_rmse_test:.2f} (±{cv_rmse_std:.2f}) pontos")
        print(f"     • MAE: {cv_mae_test:.2f} (±{cv_mae_std:.2f}) pontos")

        # 3. Calcular gap (diferença treino vs teste)
        gap_r2 = cv_r2_train - cv_r2_test
        gap_rmse = cv_rmse_test - cv_rmse_train
        gap_mae = cv_mae_test - cv_mae_train

        print("\n⚠️  GAP TREINO-TESTE (indicador de overfitting):")
        print(f"  • R² Gap: {gap_r2:.4f}")
        print(f"  • RMSE Gap: {gap_rmse:.2f} pontos")
        print(f"  • MAE Gap: {gap_mae:.2f} pontos")

        # 4. Diagnóstico de overfitting
        print("\n🔍 DIAGNÓSTICO:")
        overfitting_score = self._diagnose_overfitting(gap_r2, gap_rmse, cv_r2_train, cv_r2_test, cv_rmse_train, cv_rmse_test)

        # 5. Variabilidade entre folds
        print("\n📊 ESTABILIDADE ENTRE FOLDS:")
        print(f"  • Desvio Padrão R² CV: {cv_r2_std:.4f}")
        print(f"  • Desvio Padrão RMSE CV: {cv_rmse_std:.2f} pontos")
        print(f"  • Desvio Padrão MAE CV: {cv_mae_std:.2f} pontos")

        if cv_r2_std < 0.02:
            print("  ✅ Modelo é CONSISTENTE entre folds (baixa variabilidade)")
        elif cv_r2_std < 0.05:
            print("  ⚠️  Modelo tem variabilidade MODERADA entre folds")
        else:
            print("  ❌ Modelo é INSTÁVEL entre folds (alta variabilidade)")

        return {
            "r2_train": cv_r2_train,
            "r2_test": cv_r2_test,
            "rmse_train": cv_rmse_train,
            "rmse_test": cv_rmse_test,
            "mae_train": cv_mae_train,
            "mae_test": cv_mae_test,
            "gap_r2": gap_r2,
            "gap_rmse": gap_rmse,
            "gap_mae": gap_mae,
            "cv_r2_std": cv_r2_std,
            "overfitting_score": overfitting_score,
            "cv_results": cv_results,
        }

    def _diagnose_overfitting(self, gap_r2: float, gap_rmse: float, r2_train: float, r2_test: float, rmse_train: float, rmse_test: float) -> str:
        """Classifica nível de overfitting"""
        print()
        issues = []

        # R² Gap Check
        if gap_r2 > 0.05:
            issues.append(f"❌ GAP R² = {gap_r2:.4f} (muito alto, threshold: 0.05)")
        elif gap_r2 > 0.02:
            issues.append(f"⚠️  GAP R² = {gap_r2:.4f} (moderado, threshold: 0.02)")
        else:
            print(f"✅ GAP R² = {gap_r2:.4f} (saudável)")

        # RMSE Gap Check
        if gap_rmse > 2.0:
            issues.append(f"❌ GAP RMSE = {gap_rmse:.2f} (muito alto, threshold: 2.0)")
        elif gap_rmse > 0.5:
            issues.append(f"⚠️  GAP RMSE = {gap_rmse:.2f} (moderado, threshold: 0.5)")
        else:
            print(f"✅ GAP RMSE = {gap_rmse:.2f} (saudável)")

        # Validação em Teste
        if r2_test < 0.3:
            issues.append(f"❌ R² em teste = {r2_test:.4f} (baixo demais, esperado >= 0.3)")
        elif r2_test < 0.5:
            issues.append(f"⚠️  R² em teste = {r2_test:.4f} (moderado, esperado >= 0.5)")
        else:
            print(f"✅ R² em teste = {r2_test:.4f} (excelente)")

        # RMSE em Teste
        if rmse_test > 5.0:
            issues.append(f"⚠️  RMSE em teste = {rmse_test:.2f} (verificar adequação)")
        else:
            print(f"✅ RMSE em teste = {rmse_test:.2f} (bom)")

        # Resumo
        if not issues:
            print("\n✅ RESULTADO: Modelo SEM sinais graves de overfitting")
            return "GREEN"
        else:
            print("\n⚠️  PROBLEMAS DETECTADOS:")
            for issue in issues:
                print(f"  {issue}")
            if any("❌" in issue for issue in issues):
                return "RED"
            else:
                return "YELLOW"

    def learning_curve_analysis(self, output_file: str | None = None):
        """Gera curva de aprendizado para detectar underfitting/overfitting"""
        print("\n" + "=" * 70)
        print("CURVA DE APRENDIZADO")
        print("=" * 70)

        train_sizes, train_scores, val_scores = learning_curve(
            LinearRegression(),
            self.X_scaled,
            self.y,
            cv=KFold(n_splits=5, shuffle=True, random_state=42),
            train_sizes=np.linspace(0.1, 1.0, 10),
            scoring="r2",
            n_jobs=-1,
        )

        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)
        val_mean = np.mean(val_scores, axis=1)
        val_std = np.std(val_scores, axis=1)

        print("\n📈 Análise:")
        print(f"  • Com 10% dados: Train R²={train_mean[0]:.4f}, Val R²={val_mean[0]:.4f}")
        print(f"  • Com 100% dados: Train R²={train_mean[-1]:.4f}, Val R²={val_mean[-1]:.4f}")

        gap_inicial = train_mean[0] - val_mean[0]
        gap_final = train_mean[-1] - val_mean[-1]

        print(f"  • Gap inicial (10%): {gap_inicial:.4f}")
        print(f"  • Gap final (100%): {gap_final:.4f}")

        if gap_final < 0.02:
            print("  ✅ Gap diminui com mais dados (bom sinal)")
        else:
            print("  ⚠️  Gap persiste mesmo com mais dados (possível overfitting estrutural)")

        # Plot
        if output_file:
            plt.figure(figsize=(10, 6))
            plt.plot(
                train_sizes,
                train_mean,
                "o-",
                color="r",
                label="Score de Treino",
                linewidth=2,
            )
            plt.fill_between(
                train_sizes,
                train_mean - train_std,
                train_mean + train_std,
                alpha=0.1,
                color="r",
            )
            plt.plot(
                train_sizes,
                val_mean,
                "o-",
                color="g",
                label="Score de Validação",
                linewidth=2,
            )
            plt.fill_between(
                train_sizes,
                val_mean - val_std,
                val_mean + val_std,
                alpha=0.1,
                color="g",
            )
            plt.xlabel("Tamanho do Conjunto de Treino")
            plt.ylabel("Score R²")
            plt.title("Curva de Aprendizado - Detecção de Over/Underfitting")
            plt.legend(loc="best")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_file, dpi=100)
            print(f"\n  📊 Gráfico salvo: {output_file}")
            plt.close()

    def residual_analysis(self, output_file: str | None = None):
        """Análise de resíduos para detectar padrões de overfitting"""
        print("\n" + "=" * 70)
        print("ANÁLISE DE RESÍDUOS")
        print("=" * 70)

        # Predições com validação cruzada
        model = LinearRegression()
        y_pred_cv = cross_val_predict(
            model,
            self.X_scaled,
            self.y,
            cv=KFold(n_splits=5, shuffle=True, random_state=42),
        )

        residuals = self.y - y_pred_cv

        print("\n📊 Estatísticas dos Resíduos:")
        print(f"  • Média: {np.mean(residuals):.4f} (esperado ≈ 0)")
        print(f"  • Desvio Padrão: {np.std(residuals):.2f} pontos")
        print(f"  • Min: {np.min(residuals):.2f} pontos")
        print(f"  • Max: {np.max(residuals):.2f} pontos")

        # Teste de normalidade (Shapiro-Wilk para subset)
        from scipy.stats import normaltest

        if len(residuals) > 5000:
            sample_residuals = np.random.choice(residuals, 5000, replace=False)
        else:
            sample_residuals = residuals

        _, p_value = normaltest(sample_residuals)
        print(f"  • Teste de Normalidade (p-value): {p_value:.4f}")
        if p_value > 0.05:
            print("    ✅ Resíduos aproximadamente normais (p > 0.05)")
        else:
            print("    ⚠️  Resíduos podem desviar de normalidade (p ≤ 0.05)")

        # Detecção de heterocedasticidade
        predicted_abs_residuals = np.abs(y_pred_cv - np.mean(y_pred_cv))
        correlation = np.corrcoef(predicted_abs_residuals, np.abs(residuals) - np.mean(np.abs(residuals)))[0, 1]
        print(f"  • Correlação (predito vs |resíduo|): {correlation:.4f}")
        if abs(correlation) < 0.2:
            print("    ✅ Variância homogênea (bom)")
        else:
            print("    ⚠️  Possível heterocedasticidade")

        # Plot
        if output_file:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))

            # Plot 1: Resíduos vs Preditos
            axes[0, 0].scatter(y_pred_cv, residuals, alpha=0.5, s=10)
            axes[0, 0].axhline(y=0, color="r", linestyle="--")
            axes[0, 0].set_xlabel("Valores Preditos")
            axes[0, 0].set_ylabel("Resíduos")
            axes[0, 0].set_title("Resíduos vs Valores Preditos")
            axes[0, 0].grid(True, alpha=0.3)

            # Plot 2: Distribuição de Resíduos
            axes[0, 1].hist(residuals, bins=50, edgecolor="black", alpha=0.7)
            axes[0, 1].set_xlabel("Resíduo")
            axes[0, 1].set_ylabel("Frequência")
            axes[0, 1].set_title("Distribuição de Resíduos")
            axes[0, 1].grid(True, alpha=0.3)

            # Plot 3: Q-Q Plot
            from scipy import stats

            stats.probplot(residuals, dist="norm", plot=axes[1, 0])
            axes[1, 0].set_title("Q-Q Plot")
            axes[1, 0].grid(True, alpha=0.3)

            # Plot 4: Resíduos ao longo do índice (para detectar padrões temporais)
            axes[1, 1].scatter(range(len(residuals)), residuals, alpha=0.5, s=10)
            axes[1, 1].axhline(y=0, color="r", linestyle="--")
            axes[1, 1].set_xlabel("Índice")
            axes[1, 1].set_ylabel("Resíduo")
            axes[1, 1].set_title("Resíduos ao Longo do Dataset")
            axes[1, 1].grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_file, dpi=100)
            print(f"\n  📊 Gráfico salvo: {output_file}")
            plt.close()

    def feature_importance_stability(self):
        """Verifica estabilidade de importância de features entre folds"""
        print("\n" + "=" * 70)
        print("ESTABILIDADE DE IMPORTÂNCIA DE FEATURES")
        print("=" * 70)

        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        importances = []

        for train_idx, _ in kf.split(self.X_scaled):
            X_train, y_train = (
                self.X_scaled[train_idx],
                self.y.iloc[train_idx],
            )
            model = LinearRegression()
            model.fit(X_train, y_train)
            importances.append(np.abs(model.coef_))

        importances = np.array(importances)
        mean_importance = importances.mean(axis=0)
        std_importance = importances.std(axis=0)

        print("\n📊 Importância de Features (média entre folds):\n")
        for feature, mean_imp, std_imp in sorted(
            zip(self.predictor.feature_cols, mean_importance, std_importance),
            key=lambda x: x[1],
            reverse=True,
        ):
            stability = "✅" if std_imp / (mean_imp + 1e-6) < 0.3 else "⚠️"
            print(f"  {stability} {feature:12} | Importância: {mean_imp:8.4f} ± {std_imp:8.4f} (CV: {std_imp / (mean_imp + 1e-6) * 100:5.1f}%)")

        # Identificar features instáveis
        cv_ratios = std_importance / (mean_importance + 1e-6)
        unstable_features = [f for f, cv in zip(self.predictor.feature_cols, cv_ratios) if cv > 0.3]
        if unstable_features:
            print(f"\n  ⚠️  Features instáveis (podem indicar overfitting): {unstable_features}")
        else:
            print("\n  ✅ Todas as features são estáveis entre folds")

    def full_report(self, output_dir: str = "cv_analysis"):
        """Gera relatório completo"""
        import os

        os.makedirs(output_dir, exist_ok=True)

        print("\n" + "=" * 70)
        print("INICIANDO ANÁLISE COMPLETA DE OVERFITTING E VALIDAÇÃO CRUZADA")
        print("=" * 70)

        # Análises
        overfitting_results = self.analyze_overfitting()
        self.learning_curve_analysis(f"{output_dir}/learning_curve.png")
        self.residual_analysis(f"{output_dir}/residual_analysis.png")
        self.feature_importance_stability()

        # Relatório Final
        print("\n" + "=" * 70)
        print("RELATÓRIO FINAL")
        print("=" * 70)

        if overfitting_results["overfitting_score"] == "GREEN":
            print("\n✅ MODELO SAUDÁVEL")
            print("   O modelo não apresenta sinais significativos de overfitting.")
            print("   Recomendação: Modelo pronto para produção.")
        elif overfitting_results["overfitting_score"] == "YELLOW":
            print("\n⚠️  MODELO COM SINAIS MODERADOS DE OVERFITTING")
            print("   Considere: validar em dados reais, aumentar regularização, ou coletar mais dados.")
        else:
            print("\n❌ MODELO COM OVERFITTING SEVERO")
            print("   Recomendação: Reduzir complexidade, aumentar regularização, ou revisar features.")

        print(f"\n📊 Gráficos salvos em: {output_dir}/")
        print("\n" + "=" * 70 + "\n")

        return overfitting_results


def main():
    analyzer = OverfittingAnalyzer("data/nba_player_stats_multi_season.csv")
    analyzer.full_report()


if __name__ == "__main__":
    main()
