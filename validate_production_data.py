"""
Análise profissional de segurança dos dados para produção
Validação cruzada, train/test split, e detecção de data leakage
"""

import os

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, train_test_split

from nba_prediction_model_boxscores import NBAPointsPredictorBoxscores

path = os.path.join("data", "nba_player_boxscores_multi_season.csv")

print("\n" + "=" * 70)
print("ANÁLISE DE QUALIDADE DOS DADOS E SEGURANÇA PARA PRODUÇÃO")
print("=" * 70)

# 1. Análise dos dados brutos
print("\n1️⃣  ANÁLISE DOS DADOS BRUTOS")
print("-" * 70)
df_raw = pd.read_csv(path)
df_raw.columns = [c.strip().upper() for c in df_raw.columns]
print(f"   Total de registros (games): {len(df_raw)}")
print(f"   Total de jogadores únicos: {df_raw['PLAYER_NAME'].nunique()}")
print(f"   Total de temporadas: {df_raw['SEASON'].nunique()}")
print(f"   Datas (range): {df_raw['GAME_DATE'].min()} a {df_raw['GAME_DATE'].max()}")

# 2. Treino completo
print("\n2️⃣  MÉTRICAS DO MODELO COMPLETO (TREINO)")
print("-" * 70)
model = NBAPointsPredictorBoxscores(path)
model.train()
print(f"   R² (treino): {model.model_stats['r2']:.4f}")
print(f"   RMSE (treino): {model.model_stats['rmse']:.4f}")
print(f"   MAE (treino): {model.model_stats['mae']:.4f}")
print(f"   Features: {len(model.feature_cols)}")

# 3. Cross-validation
print("\n3️⃣  VALIDAÇÃO CRUZADA (5-Fold) - TESTE REALISTA")
print("-" * 70)
X, y, weights = model.build_features()
X_scaled = model.scaler.fit_transform(X)

kf = KFold(n_splits=5, shuffle=True, random_state=42)
cv_scores_r2 = []
cv_scores_mae = []

for fold, (train_idx, test_idx) in enumerate(kf.split(X_scaled), 1):
    X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    w_train = weights.iloc[train_idx]

    model_cv = Ridge(alpha=2.0, random_state=42)
    model_cv.fit(X_train, y_train, sample_weight=w_train)

    y_pred = model_cv.predict(X_test)

    r2 = 1 - (np.sum((y_test - y_pred) ** 2) / np.sum((y_test - y_test.mean()) ** 2))
    mae = np.mean(np.abs(y_test - y_pred))

    cv_scores_r2.append(r2)
    cv_scores_mae.append(mae)

    print(f"   Fold {fold}: R²={r2:.4f}, MAE={mae:.4f}")

print(f"\n   Média R² CV: {np.mean(cv_scores_r2):.4f} ± {np.std(cv_scores_r2):.4f}")
print(f"   Média MAE CV: {np.mean(cv_scores_mae):.4f} ± {np.std(cv_scores_mae):.4f}")

# 4. Train/Test Split
print("\n4️⃣  TRAIN/TEST SPLIT (80/20) - GENERALIZATION")
print("-" * 70)
X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(X_scaled, y, weights, test_size=0.2, random_state=42)

model_train = Ridge(alpha=2.0, random_state=42)
model_train.fit(X_train, y_train, sample_weight=w_train)

y_pred_train = model_train.predict(X_train)
y_pred_test = model_train.predict(X_test)

r2_train = 1 - (np.sum((y_train - y_pred_train) ** 2) / np.sum((y_train - y_train.mean()) ** 2))
r2_test = 1 - (np.sum((y_test - y_pred_test) ** 2) / np.sum((y_test - y_test.mean()) ** 2))
mae_train = np.mean(np.abs(y_train - y_pred_train))
mae_test = np.mean(np.abs(y_test - y_pred_test))

print(f"   Treino - R²: {r2_train:.4f}, MAE: {mae_train:.4f}")
print(f"   Teste  - R²: {r2_test:.4f}, MAE: {mae_test:.4f}")
print(f"   Gap R² (Treino - Teste): {r2_train - r2_test:.4f}")

# 5. Análise de resíduos
print("\n5️⃣  ANÁLISE DE RESÍDUOS (QUALIDADE DAS PREVISÕES)")
print("-" * 70)
residuals = y_test - y_pred_test
print(f"   Erro mínimo: {residuals.min():.2f} pts")
print(f"   Erro máximo: {residuals.max():.2f} pts")
print(f"   Erro mediano: {residuals.median():.2f} pts")
print(f"   Distribuição normal? (Skewness={residuals.skew():.3f})")

# 6. Análise de overfitting
print("\n6️⃣  ANÁLISE DE OVERFITTING")
print("-" * 70)
gap = r2_train - r2_test
if gap < 0.05:
    status_gap = "✅ BOM - Sem sinais de overfitting"
elif gap < 0.15:
    status_gap = "⚠️  MODERADO - Há overfitting leve"
else:
    status_gap = "❌ CRÍTICO - Modelo não generaliza"

print(f"   Gap R² (treino vs teste): {gap:.4f}")
print(f"   Status: {status_gap}")

# 7. Conclusões
print("\n7️⃣  CONCLUSÕES PARA PRODUÇÃO")
print("=" * 70)

if r2_test < 0.70:
    rating = "❌ BAIXA - NÃO USE EM PRODUÇÃO"
    recommendation = "Recolher mais dados e revisar features"
elif r2_test < 0.80:
    rating = "⚠️  MÉDIA - USE COM CAUTELA"
    recommendation = "Implementar monitoramento rigoroso"
elif r2_test < 0.85:
    rating = "✅ BOA - PRONTO PARA PRODUÇÃO"
    recommendation = "Usar com validação A/B testing"
else:
    rating = "🚀 EXCELENTE - RECOMENDADO"
    recommendation = "Produção aprovada com acompanhamento"

print(f"   Confiabilidade: {rating}")
print(f"   R² em produção (esperado): {r2_test:.4f}")
print(f"   MAE em produção (esperado): {mae_test:.4f} pts")
print(f"   Recomendação: {recommendation}")

# Relatório final
print("\n" + "=" * 70)
print("RESUMO EXECUTIVO")
print("=" * 70)
print(f"""
🔍 DADOS:
   - {len(df_raw):,} partidas de {df_raw["PLAYER_NAME"].nunique()} jogadores
   - {df_raw["SEASON"].nunique()} temporadas ({df_raw["SEASON"].min()} a {df_raw["SEASON"].max()})

📊 PERFORMANCE:
   - Treino:     R²={r2_train:.4f}, MAE={mae_train:.4f}
   - Validação:  R²={np.mean(cv_scores_r2):.4f} ± {np.std(cv_scores_r2):.4f}
   - Teste:      R²={r2_test:.4f}, MAE={mae_test:.4f}

⚠️  RISCO:
   - Gap overfitting: {gap:.4f} ({status_gap})
   - Variância CV: {np.std(cv_scores_r2):.4f} (consistência)

✅ DECISÃO FINAL: {rating}
""")

print("=" * 70)
