#!/usr/bin/env python
"""
Exemplos Práticos de Uso - Validação Cruzada e Monitoramento de Overfitting
"""

print("=" * 70)
print("EXEMPLOS PRÁTICOS DE USO")
print("=" * 70)

# ===========================================================================
# EXEMPLO 1: Análise Completa Uma Vez
# ===========================================================================
print("\n[EXEMPLO 1] Análise Completa de Overfitting")
print("-" * 70)
print("""
Para fazer uma análise completa do modelo (uma única vez):

    python analyze_overfitting_cv.py

Isso irá gerar:
  • Relatório em console com todas as métricas
  • Gráficos em cv_analysis/learning_curve.png
  • Gráficos em cv_analysis/residual_analysis.png

Tempo: ~60-90 segundos
""")

# ===========================================================================
# EXEMPLO 2: Validação em Pipeline CI/CD
# ===========================================================================
print("\n[EXEMPLO 2] Integração em CI/CD")
print("-" * 70)
print("""
Para validar modelo antes de fazer deploy (automático):

    from overfitting_monitor import OverfittingMonitor
    from nba_prediction_model import NBAPointsPredictor

    # Carregar dados
    predictor = NBAPointsPredictor("data/nba_player_stats_multi_season.csv")
    X, y, _ = predictor.build_features()
    X_scaled = predictor.scaler.fit_transform(X)

    # Validar
    monitor = OverfittingMonitor()
    if not monitor.test_suite(X_scaled, y.values, predictor.scaler):
        raise Exception("Modelo falhou em validação!")

    # Se chegou aqui, está aprovado para deploy ✅

Status esperado: ✅ PASS (3/3 testes)
Tempo: ~30 segundos
""")

# ===========================================================================
# EXEMPLO 3: Monitoramento Semanal em Produção
# ===========================================================================
print("\n[EXEMPLO 3] Monitoramento Semanal")
print("-" * 70)
print("""
Cada semana, validar se modelo ainda está bom:

    from overfitting_monitor import OverfittingMonitor
    from nba_prediction_model import NBAPointsPredictor
    import pandas as pd

    # Carregar dados da semana
    df_semana = pd.read_csv("data/nba_games_this_week.csv")

    # Preparar para validação
    predictor = NBAPointsPredictor()
    predictor.df = df_semana
    X, y, _ = predictor.build_features()
    X_scaled = predictor.scaler.fit_transform(X)

    # Monitorar
    monitor = OverfittingMonitor()
    result = monitor.validate_new_data(X_scaled, y.values, predictor.scaler)
    monitor.print_validation_report(result)

    # Histórico
    if result['status'] == 'FAIL':
        print("⚠️  Alertar responsável - modelo degradado!")

Status esperado: ✅ PASS (com avisos ocasionais ⚠️)
Frequência: Semanal ou quinzenal
""")

# ===========================================================================
# EXEMPLO 4: Testar Nova Feature
# ===========================================================================
print("\n[EXEMPLO 4] Validar Antes de Adicionar Feature")
print("-" * 70)
print("""
Quando quiser adicionar uma nova feature (e.g., "GAME_LOCATION"):

    1. Adicione a feature ao dataset:
       df['GAME_LOCATION'] = ['HOME' if h else 'AWAY' for h in home_games]

    2. Reexecute análise:
       python analyze_overfitting_cv.py

    3. Compare resultados:
       • R² Gap aumentou? (➜ Feature pode estar overfitando)
       • Features estáveis? (➜ Colinearidade com outras?)
       • RMSE melhorou? (➜ Feature útil)

    4. Decisão:
       ✅ Se R² Gap ainda < 0.05 → Manter feature
       ❌ Se R² Gap aumentou muito → Remover feature

Recomendação: Testar features uma de cada vez
""")

# ===========================================================================
# EXEMPLO 5: Customizar Thresholds
# ===========================================================================
print("\n[EXEMPLO 5] Customizar Limites de Validação")
print("-" * 70)
print("""
Se quiser critérios mais rigorosos ou relaxados:

    from overfitting_monitor import OverfittingMonitor

    monitor = OverfittingMonitor()

    # Padrão (atual)
    print("Thresholds padrão:")
    print(monitor.thresholds)

    # Mais rigoroso (para produção crítica)
    monitor.set_thresholds(
        r2_gap_max=0.02,      # Reduzido de 0.05
        rmse_max=2.0,         # Reduzido de 3.5
        r2_min_test=0.85,     # Aumentado de 0.80
        std_cv_max=0.02,      # Reduzido de 0.03
    )

    # Mais relaxado (para experimentação)
    monitor.set_thresholds(
        r2_gap_max=0.10,
        rmse_max=4.0,
        r2_min_test=0.70,
        std_cv_max=0.05,
    )

Recomendação: Manter padrão a menos que haja motivo específico
""")

# ===========================================================================
# EXEMPLO 6: Análise Comparativa Entre Períodos
# ===========================================================================
print("\n[EXEMPLO 6] Comparar Performance Entre Temporadas")
print("-" * 70)
print("""
Validar se modelo mantém qualidade em diferentes períodos:

    from nba_prediction_model import NBAPointsPredictor
    from overfitting_monitor import OverfittingMonitor
    import pandas as pd

    # Período 1 (baseline)
    df1 = pd.read_csv("data/2022_2023_season.csv")
    predictor1 = NBAPointsPredictor()
    predictor1.df = df1
    X1, y1, _ = predictor1.build_features()

    # Período 2 (novo)
    df2 = pd.read_csv("data/2023_2024_season.csv")
    predictor2 = NBAPointsPredictor()
    predictor2.df = df2
    X2, y2, _ = predictor2.build_features()

    # Comparar
    monitor = OverfittingMonitor()
    result1 = monitor.validate_new_data(X1, y1.values, predictor1.scaler)
    result2 = monitor.validate_new_data(X2, y2.values, predictor2.scaler)

    print(f"Temporada 1 R²: {result1['r2_test']:.4f}")
    print(f"Temporada 2 R²: {result2['r2_test']:.4f}")
    print(f"Degradação: {(result1['r2_test'] - result2['r2_test'])*100:.2f}%")

    if abs(result1['r2_test'] - result2['r2_test']) > 0.05:
        print("⚠️  Modelo degradou significativamente!")
    else:
        print("✅ Modelo mantém performance consistente")

Frequência: A cada novo período/temporada
""")

# ===========================================================================
# EXEMPLO 7: Integração com Logging
# ===========================================================================
print("\n[EXEMPLO 7] Integrar com Sistema de Logging")
print("-" * 70)
print("""
Para rastrear validações em arquivo de log:

    from overfitting_monitor import OverfittingMonitor
    import json
    from datetime import datetime

    monitor = OverfittingMonitor()
    result = monitor.validate_new_data(X_scaled, y.values, scaler)

    # Salvar em log
    with open("validation_log.jsonl", "a") as f:
        log_entry = {
            "timestamp": result['timestamp'],
            "status": result['status'],
            "r2_test": result['r2_test'],
            "r2_gap": result['r2_gap'],
            "rmse": result['rmse'],
            "issues": result['issues'],
        }
        f.write(json.dumps(log_entry) + "\\n")

    # Análise histórica
    import pandas as pd
    df = pd.read_json("validation_log.jsonl", lines=True)
    print(df.groupby('status').size())  # Contar PASSes/WARNs/FAILs

Útil para: Dashboards, alertas, auditoria
""")

# ===========================================================================
# EXEMPLO 8: Detecção Automática de Degradação
# ===========================================================================
print("\n[EXEMPLO 8] Alertar se Modelo Degrada")
print("-" * 70)
print("""
Detectar quando modelo piora e enviar alerta:

    from overfitting_monitor import OverfittingMonitor
    import smtplib
    from email.mime.text import MIMEText

    monitor = OverfittingMonitor()
    result = monitor.validate_new_data(X_scaled, y.values, scaler)

    # Verificar degradação
    if result['r2_test'] < 0.80:
        # Enviar alerta
        msg = MIMEText(f"⚠️  R² caiu para {result['r2_test']:.4f}")
        msg['Subject'] = "ALERTA: Modelo degradado"

        # Usar seu servidor SMTP
        # smtp = smtplib.SMTP('localhost')
        # smtp.send_message(msg)

        print(f"🚨 Alerta enviado! R² = {result['r2_test']:.4f}")

    # Ou usar webhook
    import requests
    if result['status'] == 'FAIL':
        requests.post(
            "https://hooks.slack.com/services/YOUR/WEBHOOK",
            json={"text": f"Model validation failed: {result['issues']}"}
        )

Integração: Slack, Email, PagerDuty, etc.
""")

# ===========================================================================
# RESUMO
# ===========================================================================
print("\n" + "=" * 70)
print("RESUMO DE EXEMPLOS")
print("=" * 70)
print("""
Caso de Uso                    | Script              | Frequência
-------------------------------|---------------------|----------------
Análise inicial                | analyze_...cv.py    | Uma vez
Antes de deploy                | overfitting_monitor | Por release
Monitoramento semanal          | overfitting_monitor | Semanal
Testar nova feature            | analyze_...cv.py    | Conforme necessário
Comparar períodos              | overfitting_monitor | Semanal/mensal
Alertas automáticos            | overfitting_monitor | Contínuo
Auditoria/compliance           | logging + histórico | Sob demanda
""")

print("\n✅ Para mais detalhes, ver GUIA_VALIDACAO_CRUZADA.md\n")
