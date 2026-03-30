"""
Validação de Dados de Produção - V2
CORRIGIDO: Usa TimeSeriesSplit para manter ordem temporal
Sem data leakage, validação real de performance futura
"""

import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(__file__))

from nba_prediction_model_boxscores_v2 import NBAPointsPredictorBoxscoresV2


def validate_with_time_series_split(data_path: str = "data/nba_player_boxscores_multi_season.csv", n_splits: int = 5, alpha: float = 2.0):
    """
    Validação com TimeSeriesSplit - CORRETO para dados temporais

    Fold 1: Train [2019-20, 2020-21] → Test [2021-22]
    Fold 2: Train [2019-20 até 2021-22] → Test [2022-23]
    ...

    Garante que treino sempre precede teste
    """

    print("\n" + "=" * 80)
    print("🔬 VALIDAÇÃO COM TIMESERIESSPLIT (SEM DATA LEAKAGE)")
    print("=" * 80 + "\n")

    # Carregar dados
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {data_path}")

    df = pd.read_csv(data_path)
    df.columns = [c.strip().upper() for c in df.columns]

    if "GAME_DATE" in df.columns:
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce")

    # Sort por data
    df = df.sort_values("GAME_DATE").reset_index(drop=True)

    # Extrair datas únicas para split
    if "GAME_DATE" in df.columns:
        dates = df["GAME_DATE"].dt.date.unique()
        dates = sorted(dates)
        print(f"Total de datas: {len(dates)}")
        print(f"Data inicial: {dates[0]}")
        print(f"Data final: {dates[-1]}")
    else:
        raise ValueError("GAME_DATE não encontrada no dataset")

    # TimeSeriesSplit: split por tempo, não aleatoriamente
    tscv = TimeSeriesSplit(n_splits=n_splits)

    fold_results = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(df), 1):
        print(f"\n{'─' * 80}")
        print(f"📊 FOLD {fold}/{n_splits}")
        print(f"{'─' * 80}")

        train_df = df.iloc[train_idx].copy()
        test_df = df.iloc[test_idx].copy()

        train_date_range = f"{train_df['GAME_DATE'].min().date()} a {train_df['GAME_DATE'].max().date()}"
        test_date_range = f"{test_df['GAME_DATE'].min().date()} a {test_df['GAME_DATE'].max().date()}"

        print(f"Treino: {len(train_df):,} samples | {train_date_range}")
        print(f"Teste:  {len(test_df):,} samples | {test_date_range}")

        # Preparar features
        feature_cols = ["LAG_PTS_3", "LAG_PTS_5", "LAG_PTS_10", "LAG_PTS_15", "LAG_MIN_5", "LAG_MIN_10", "MOMENTUM", "VOLATILITY", "CONSISTENCY", "FORM_INDICATOR", "GAME_STREAK", "IS_HOME", "BACK_TO_BACK", "MONTH", "DAY_OF_WEEK"]

        # Filtrar features que existem
        available_features = [col for col in feature_cols if col in train_df.columns]

        if len(available_features) < 5:
            print(f"⚠️ Insuficientes features: {len(available_features)}")
            continue

        # Treinar modelo
        try:
            X_train = train_df[available_features].fillna(0)
            y_train = train_df["PTS"]

            # Pesos por recência
            if "SEASON" in train_df.columns:
                weights = train_df["SEASON"].astype(float)
                weights = weights / weights.min()
            else:
                weights = np.ones(len(X_train))

            # Scale e treinar
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)

            model = Ridge(alpha=alpha, random_state=42)
            model.fit(X_train_scaled, y_train, sample_weight=weights.values)

            # Testar em dados FUTUROS (que modelo nunca viu)
            X_test = test_df[available_features].fillna(0)
            y_test = test_df["PTS"]

            X_test_scaled = scaler.transform(X_test)
            y_pred = model.predict(X_test_scaled)

            # Métricas
            residuals = y_test.values - y_pred
            mae = np.mean(np.abs(residuals))
            rmse = np.sqrt(np.mean(residuals**2))
            r2 = 1 - (np.sum(residuals**2) / np.sum((y_test.values - y_test.mean()) ** 2))

            # Acurácia (predictions within 1.5 pts)
            accuracy = (np.abs(residuals) <= 1.5).mean() * 100

            print(f"✅ R² = {r2:.4f}")
            print(f"✅ MAE = {mae:.2f} pts")
            print(f"✅ RMSE = {rmse:.2f} pts")
            print(f"✅ Accuracy (±1.5 pts) = {accuracy:.1f}%")

            fold_results.append(
                {
                    "fold": fold,
                    "train_samples": len(train_df),
                    "test_samples": len(test_df),
                    "r2": r2,
                    "mae": mae,
                    "rmse": rmse,
                    "accuracy": accuracy,
                    "train_date_start": train_df["GAME_DATE"].min(),
                    "train_date_end": train_df["GAME_DATE"].max(),
                    "test_date_start": test_df["GAME_DATE"].min(),
                    "test_date_end": test_df["GAME_DATE"].max(),
                },
            )

        except Exception as e:
            print(f"❌ Erro no fold {fold}: {str(e)}")
            continue

    # Resumo final
    print(f"\n{'=' * 80}")
    print("📈 RESUMO FINAL")
    print(f"{'=' * 80}\n")

    if fold_results:
        results_df = pd.DataFrame(fold_results)

        print("Métricas por Fold:")
        print(results_df[["fold", "r2", "mae", "rmse", "accuracy"]].to_string(index=False))

        print("\n📊 Estatísticas Agregadas:")
        print(f"   R² (média ± std): {results_df['r2'].mean():.4f} ± {results_df['r2'].std():.4f}")
        print(f"   MAE (média): {results_df['mae'].mean():.2f} pts")
        print(f"   RMSE (média): {results_df['rmse'].mean():.2f} pts")
        print(f"   Accuracy (média): {results_df['accuracy'].mean():.1f}%")

        # Verificação: há overfitting?
        print("\n🔍 Análise de Overfitting:")
        r2_variance = results_df["r2"].std()
        if r2_variance < 0.01:
            print(f"   ✓ Modelo CONSISTENTE (low variance: {r2_variance:.4f})")
        elif r2_variance < 0.05:
            print(f"   ⚠️ Modelo com variância média ({r2_variance:.4f})")
        else:
            print(f"   🔴 Modelo INSTÁVEL (high variance: {r2_variance:.4f})")

        return results_df
    else:
        print("❌ Nenhum fold validado com sucesso")
        return pd.DataFrame()


def validate_with_real_production_data(data_path: str = "data/nba_player_boxscores_multi_season.csv", test_days_back: int = 7, alpha: float = 2.0):
    """
    Validação contra dados reais de produção
    Treina em tudo MENOS os últimos N dias, testa nos últimos N dias
    """

    print("\n" + "=" * 80)
    print("🎯 VALIDAÇÃO COM DADOS REAIS (ÚLTIMOS 7 DIAS)")
    print("=" * 80 + "\n")

    # Carregar dados
    df = pd.read_csv(data_path)
    df.columns = [c.strip().upper() for c in df.columns]

    if "GAME_DATE" in df.columns:
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce")
        df = df.sort_values("GAME_DATE").reset_index(drop=True)

    # Definir cutoff
    max_date = df["GAME_DATE"].max()
    cutoff_date = max_date - pd.Timedelta(days=test_days_back)

    train_df = df[df["GAME_DATE"] <= cutoff_date].copy()
    test_df = df[df["GAME_DATE"] > cutoff_date].copy()

    print(f"Treino até: {cutoff_date.date()}")
    print(f"Teste: {test_df['GAME_DATE'].min().date()} a {test_df['GAME_DATE'].max().date()}")
    print(f"Treino samples: {len(train_df):,}")
    print(f"Teste samples: {len(test_df):,}\n")

    if len(test_df) == 0:
        print("❌ Sem dados para teste (últimos 7 dias vazios)")
        return None

    # Treinar
    predictor = NBAPointsPredictorBoxscoresV2(data_path)
    predictor.train(test_date=cutoff_date, alpha=alpha)

    # Testar
    X_test = test_df[predictor.feature_cols].fillna(0)
    y_test = test_df["PTS"]

    X_test_scaled = predictor.scaler.transform(X_test)
    y_pred = predictor.model.predict(X_test_scaled)

    # Métricas
    residuals = y_test.values - y_pred
    mae = np.mean(np.abs(residuals))
    rmse = np.sqrt(np.mean(residuals**2))
    r2 = 1 - (np.sum(residuals**2) / np.sum((y_test.values - y_test.mean()) ** 2))
    accuracy = (np.abs(residuals) <= 1.5).mean() * 100

    print(f"✅ R² (Teste Real) = {r2:.4f}")
    print(f"✅ MAE (Teste Real) = {mae:.2f} pts")
    print(f"✅ RMSE (Teste Real) = {rmse:.2f} pts")
    print(f"✅ Accuracy (Teste Real) = {accuracy:.1f}%\n")

    # Comparação treino vs teste
    train_mae = predictor.model_stats.get("mae", 0)
    print("📊 Comparação Treino vs Teste:")
    print(f"   MAE Treino: {train_mae:.2f} pts")
    print(f"   MAE Teste: {mae:.2f} pts")
    print(f"   Diferença: {mae - train_mae:+.2f} pts")

    if abs(mae - train_mae) < 0.5:
        print("   ✓ Generalização EXCELENTE (diferença < 0.5)")
    elif abs(mae - train_mae) < 1.0:
        print("   ⚠️ Generalização BOA (diferença < 1.0)")
    else:
        print("   🔴 Generalização POBRE (diferença >= 1.0)")

    return {"r2": r2, "mae": mae, "rmse": rmse, "accuracy": accuracy, "train_mae": train_mae, "test_samples": len(test_df)}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    print("\n[VALIDACAO COMPLETA DO MODELO V2 SEM LEAKAGE]\n")

    # 1. TimeSeriesSplit
    print("\n[1] TimeSeriesSplit Validation...")
    ts_results = validate_with_time_series_split()

    # 2. Dados reais
    print("\n[2] Real Production Data Validation...")
    prod_results = validate_with_real_production_data()

    print("\n" + "=" * 80)
    print("[VALIDACAO COMPLETA]")
    print("=" * 80)
