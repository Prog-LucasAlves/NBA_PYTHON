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


def _baseline_predict(train_df: pd.DataFrame, test_df: pd.DataFrame, window: int = 5) -> np.ndarray:
    """Baseline simples: média móvel dos últimos N jogos por jogador."""
    global_mean = float(train_df["PTS"].mean())
    baseline_preds = []

    train_groups = train_df.groupby("PLAYER_NAME", sort=False)

    for _, row in test_df.iterrows():
        player = row["PLAYER_NAME"]
        if player in train_groups.groups:
            player_history = train_groups.get_group(player).sort_values("GAME_DATE")["PTS"].tail(window)
            pred = float(player_history.mean()) if len(player_history) > 0 else global_mean
        else:
            pred = global_mean
        baseline_preds.append(pred)

    return np.array(baseline_preds, dtype=float)


def _summarize_metrics(y_true: np.ndarray, y_pred: np.ndarray, accuracy_threshold: float = 1.5) -> dict[str, float]:
    residuals = y_true - y_pred
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals**2)))
    r2 = float(1 - (np.sum(residuals**2) / np.sum((y_true - np.mean(y_true)) ** 2))) if len(y_true) > 1 else 0.0
    accuracy = float((np.abs(residuals) <= accuracy_threshold).mean() * 100)
    return {"r2": r2, "mae": mae, "rmse": rmse, "accuracy": accuracy}


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

    # Carregar dados e gerar features no mesmo pipeline do modelo
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {data_path}")

    predictor = NBAPointsPredictorBoxscoresV2(data_path)
    df = predictor.df.copy() if predictor.df is not None else pd.DataFrame()
    if df.empty:
        raise ValueError("Falha ao carregar dataset com features derivadas")

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
        ]

        available_features = [col for col in candidate_features if col in train_df.columns]

        if len(available_features) < 5:
            print(f"⚠️ Insuficientes features: {len(available_features)}")
            continue

        # Treinar modelo
        try:
            X_train = train_df[available_features].fillna(0)
            y_train = train_df["PTS"]

            # Pesos por recência
            if "SEASON" in train_df.columns:
                season_year = pd.to_numeric(train_df["SEASON"].astype(str).str.split("-").str[-1], errors="coerce")
                if season_year.notna().any():
                    weights = season_year.fillna(season_year.median())
                    weights = weights / weights.min()
                else:
                    weights = np.ones(len(X_train))
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
    test_features = predictor.df[predictor.df["GAME_DATE"] > cutoff_date].copy() if predictor.df is not None else pd.DataFrame()
    X_test = test_features[predictor.feature_cols].fillna(0)
    y_test = test_features["PTS"]

    X_test_scaled = predictor.scaler.transform(X_test)
    y_pred = predictor.model.predict(X_test_scaled)
    y_pred_raw = []
    for _, row in test_features.iterrows():
        pred_row = predictor.predict_points(str(row["PLAYER_NAME"]), minutes=float(row["MIN"]) if pd.notna(row["MIN"]) else 30, calibrated=False)
        y_pred_raw.append(float(pred_row["predicted_points"]))
    y_pred_raw = np.array(y_pred_raw, dtype=float)

    # Métricas
    model_metrics = _summarize_metrics(y_test.values, y_pred)
    model_raw_metrics = _summarize_metrics(y_test.values, y_pred_raw)
    baseline_pred = _baseline_predict(train_df, test_df)
    baseline_metrics = _summarize_metrics(y_test.values, baseline_pred)

    print(f"✅ R² (Teste Real) = {model_metrics['r2']:.4f}")
    print(f"✅ MAE (Teste Real) = {model_metrics['mae']:.2f} pts")
    print(f"✅ RMSE (Teste Real) = {model_metrics['rmse']:.2f} pts")
    print(f"✅ Accuracy (Teste Real) = {model_metrics['accuracy']:.1f}%")
    print(f"🧪 MAE Sem Calibração = {model_raw_metrics['mae']:.2f} pts")
    print(f"🧪 RMSE Sem Calibração = {model_raw_metrics['rmse']:.2f} pts")
    print(f"🧱 Baseline MAE = {baseline_metrics['mae']:.2f} pts")
    print(f"🧱 Baseline RMSE = {baseline_metrics['rmse']:.2f} pts")
    print(f"🧱 Baseline Accuracy = {baseline_metrics['accuracy']:.1f}%")
    print(f"📈 Delta MAE v2.2 vs v2.1 = {model_metrics['mae'] - model_raw_metrics['mae']:+.2f} pts")
    print(f"📉 Delta MAE vs Baseline = {model_metrics['mae'] - baseline_metrics['mae']:+.2f} pts")
    print(f"📉 Delta RMSE vs Baseline = {model_metrics['rmse'] - baseline_metrics['rmse']:+.2f} pts\n")

    # Comparação treino vs teste
    train_mae = predictor.model_stats.get("mae", 0)
    print("📊 Comparação Treino vs Teste:")
    print(f"   MAE Treino: {train_mae:.2f} pts")
    print(f"   MAE Teste: {model_metrics['mae']:.2f} pts")
    print(f"   Diferença: {model_metrics['mae'] - train_mae:+.2f} pts")

    if abs(model_metrics["mae"] - train_mae) < 0.5:
        print("   ✓ Generalização EXCELENTE (diferença < 0.5)")
    elif abs(model_metrics["mae"] - train_mae) < 1.0:
        print("   ⚠️ Generalização BOA (diferença < 1.0)")
    else:
        print("   🔴 Generalização POBRE (diferença >= 1.0)")

    return {
        "model": model_metrics,
        "model_raw": model_raw_metrics,
        "baseline": baseline_metrics,
        "train_mae": train_mae,
        "test_samples": len(test_df),
    }


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

    if isinstance(prod_results, dict) and "model" in prod_results and "baseline" in prod_results:
        print("\n[3] RESUMO COMPARATIVO MODELO VS BASELINE")
        print("-" * 80)
        print(f"Modelo  MAE: {prod_results['model']['mae']:.2f} | RMSE: {prod_results['model']['rmse']:.2f} | Acc: {prod_results['model']['accuracy']:.1f}%")
        print(f"Raw     MAE: {prod_results['model_raw']['mae']:.2f} | RMSE: {prod_results['model_raw']['rmse']:.2f} | Acc: {prod_results['model_raw']['accuracy']:.1f}%")
        print(f"Baseline MAE: {prod_results['baseline']['mae']:.2f} | RMSE: {prod_results['baseline']['rmse']:.2f} | Acc: {prod_results['baseline']['accuracy']:.1f}%")
        print(f"Gain MAE: {prod_results['model_raw']['mae'] - prod_results['model']['mae']:+.2f}")
        print(f"Delta MAE: {prod_results['model']['mae'] - prod_results['baseline']['mae']:+.2f}")
        print(f"Delta RMSE: {prod_results['model']['rmse'] - prod_results['baseline']['rmse']:+.2f}")
