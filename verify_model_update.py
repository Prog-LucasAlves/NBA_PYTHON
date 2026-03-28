#!/usr/bin/env python
"""
Verificação rápida do desempenho do modelo otimizado
Mostra as métricas que serão exibidas no betting_app.py
"""

import warnings

from nba_prediction_model import NBAPointsPredictor

warnings.filterwarnings("ignore")

print("\n" + "=" * 70)
print("📊 VERIFICANDO DESEMPENHO DO MODELO OTIMIZADO NO BETTING APP")
print("=" * 70 + "\n")

# Carregar e treinar modelo
data_path = "data/nba_player_stats_multi_season.csv"
predictor = NBAPointsPredictor(data_path)
predictor.train()

print("\n" + "=" * 70)
print("🎯 DESEMPENHO DO MODELO (Que será exibido no app)")
print("=" * 70 + "\n")

print(f"📊 Score R2:  {predictor.model_stats['r2']:.4f}")
print(f"📊 RMSE:      {predictor.model_stats['rmse']:.2f} pts")
print(f"📊 MAE:       {predictor.model_stats['mae']:.2f} pts")

print("\n" + "=" * 70)
print("✅ COMPARAÇÃO COM MODELO ANTERIOR")
print("=" * 70 + "\n")

old_r2 = 0.8654
old_rmse = 2.40
old_mae = 1.76

new_r2 = predictor.model_stats["r2"]
new_rmse = predictor.model_stats["rmse"]
new_mae = predictor.model_stats["mae"]

print(f"R2 Score:     {old_r2:.4f} → {new_r2:.4f}  ({(new_r2 - old_r2) / old_r2 * 100:+.2f}%)")
print(f"RMSE:         {old_rmse:.2f} → {new_rmse:.2f} pts  ({(new_rmse - old_rmse) / old_rmse * 100:+.2f}%)")
print(f"MAE:          {old_mae:.2f} → {new_mae:.2f} pts  ({(new_mae - old_mae) / old_mae * 100:+.2f}%)")

print("\n" + "=" * 70)
print("✨ FEATURES UTILIZADAS")
print("=" * 70 + "\n")

print(f"Features:     {predictor.feature_cols}")
feature_count = len(predictor.feature_cols) if predictor.feature_cols else 0
print(f"Total:        {feature_count} features (antes era 11)")

print("\n" + "=" * 70)
print("💡 O BETTING APP AGORA EXIBE AS NOVAS MÉTRICAS")
print("=" * 70 + "\n")
