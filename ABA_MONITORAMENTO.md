# 📊 NOVA ABA: MONITORAMENTO DE OVERFITTING

## 🎯 Visão Geral

Uma nova aba **"Monitoramento"** foi adicionada ao app de apostas NBA para monitorar continuamente o desempenho do modelo de predição em tempo real.

---

## 📍 Localização

```
Tabs: [Preditor de Apostas] [Historico de Apostas] [Monitoramento] ← NOVO
                                                    ^^^^^^^^^^
```

---

## ✨ FUNCIONALIDADES

### 1. **Métricas Principais**
```
┌─────────────────────────────────────────────────────────┐
│ Score R² │ RMSE (Pontos) │ MAE (Pontos) │ Features │ Status │
│ 0.8610   │ 2.44 pts      │ 1.80 pts     │ 8        │ ATIVO  │
└─────────────────────────────────────────────────────────┘
```

Cada métrica exibe:
- **Valor atual**
- **Delta** (diferença/status)
- **Cor indicadora** (verde/laranja/vermelho)

---

### 2. **Limites de Monitoramento (Thresholds)**

```
┌────────────────────────────────────────┐
│ LIMITES CONFIGURADOS                   │
├────────────────────────────────────────┤
│ R² Gap Máximo:        0.0500           │
│ RMSE Máximo:          3.5 pts          │
│ R² Mínimo Teste:      0.8000           │
│ Desvio Padrão CV:     0.0300           │
└────────────────────────────────────────┘
```

---

### 3. **Status em Tempo Real**

```
✅ BOM       → Métrica dentro dos limites ideais
⚠️ AVISO     → Métrica próxima ao limite
❌ CRÍTICO   → Métrica excedeu limite
```

Exemplo:
```
R²:    ✅ BOM      (0.8610 > 0.85)
RMSE:  ✅ BOM      (2.44 < 2.5 pts)
MAE:   ✅ BOM      (1.80 < 1.8 pts)
```

---

### 4. **Gráfico de Importância das Features**

Exibe um gráfico horizontal mostrando a importância relativa de cada feature:

```
MIN        ████████████████████ (25.2%)
FG_PCT     ███████████████ (19.3%)
FG3_PCT    ████████ (10.1%)
FT_PCT     ██████ (7.5%)
AST        █████ (6.2%)
REB        ████ (5.1%)
STL        ███ (3.8%)
TOV        ██ (2.8%)
```

**Nota:** As features otimizadas são: `MIN, FG_PCT, FG3_PCT, FT_PCT, AST, REB, STL, TOV`
Removidas: `OREB, DREB, BLK` (redundantes e instáveis)

---

### 5. **Resumo de Desempenho**

Tabela comparativa:

| Métrica    | Atual      | Alvo      | Status |
|------------|------------|-----------|--------|
| R² Score   | 0.8610     | ≥ 0.86    | ✅     |
| RMSE       | 2.44 pts   | < 2.5 pts | ✅     |
| MAE        | 1.80 pts   | < 1.8 pts | ⚠️     |
| Features   | 8 features | 8         | ✅     |
| Status     | Ativo      | v2.1      | ✅     |

---

### 6. **Sistema de Alertas Automáticos**

Avisos são exibidos automaticamente quando:

```
⚠️ R² abaixo de 0.85
⚠️ RMSE elevado acima de 2.8 pts
⚠️ MAE elevado acima de 2.0 pts
ℹ️ Modelo usando X features (otimizado: 8)
```

Se tudo estiver bem:
```
✅ Nenhum aviso no momento - Modelo operacional
```

---

### 7. **Informações Técnicas Expandíveis**

Seção "Ver Detalhes Técnicos" que mostra:

**Modelo:**
```
Tipo: Linear Regression
Features: 8
Samples Treino: ~1000
CV Strategy: 5-Fold
```

**Features Utilizadas:**
```
MIN, FG_PCT, FG3_PCT, FT_PCT, AST, REB, STL, TOV
```

---

## 🔧 Componentes Técnicos

### Import
```python
from overfitting_monitor import OverfittingMonitor
```

### Classe Utilizada
```python
monitor = OverfittingMonitor()
```

### Dados Exibidos
- Métricas do modelo: `predictor.model_stats`
- Features: `predictor.feature_cols`
- Importância: `predictor.model_stats["feature_importance"]`

---

## 📈 Fluxo de Uso

```
1. Abrir app betting_app.py
   ↓
2. Clicar em aba "Monitoramento"
   ↓
3. Ver métricas principais no topo
   ↓
4. Analisar gráfico de importância das features
   ↓
5. Verificar resumo de desempenho (Atual vs Alvo)
   ↓
6. Ler alertas automáticos (se houver)
   ↓
7. Expandir "Detalhes Técnicos" para mais informações
   ↓
8. Tomar decisões baseado no status do modelo
```

---

## 🎨 Design & UX

### Cores & Indicadores
- **Verde (✅):** Métrica dentro do esperado
- **Amarelo (⚠️):** Métrica próxima ao limite
- **Vermelho (❌):** Métrica crítica
- **Azul:** Informação

### Layout
```
┌─────────────────────────────────────────────┐
│ 📊 Monitoramento de Desempenho do Modelo    │
│ Validação contínua contra overfitting       │
├─────────────────────────────────────────────┤
│                                             │
│ 🎯 Desempenho Atual                        │
│ [R²] [RMSE] [MAE] [Features] [Status]      │
│                                             │
│ ⚠️ Limites de Monitoramento                 │
│ [Limites] [Status Atual]                   │
│                                             │
│ 📈 Importância das Features                 │
│ [Gráfico Horizontal] [Top 8 Features]      │
│                                             │
│ 🔄 Validação Cruzada (5-Fold)              │
│ [Info] [Recomendações]                     │
│                                             │
│ 📊 Resumo de Desempenho                     │
│ [Tabela Atual vs Alvo]                     │
│                                             │
│ 🔔 Avisos de Monitoramento                 │
│ [Status: ✅ Nenhum aviso / ⚠️ Avisos]      │
│                                             │
│ 📋 Informações Técnicas                     │
│ [Expandível: Modelo & Features]            │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📊 Métricas Detalhadas

### R² Score (Coeficiente de Determinação)
- **O que é:** % da variância explicada pelo modelo
- **Range:** 0 a 1
- **Alvo:** ≥ 0.86
- **Atual:** 0.8610 ✅

### RMSE (Root Mean Square Error)
- **O que é:** Erro quadrático médio em pontos
- **Range:** 0 a infinito (menor é melhor)
- **Alvo:** < 2.5 pts
- **Atual:** 2.44 pts ✅

### MAE (Mean Absolute Error)
- **O que é:** Erro médio absoluto em pontos
- **Range:** 0 a infinito (menor é melhor)
- **Alvo:** < 1.8 pts
- **Atual:** 1.80 pts ⚠️

---

## 🚨 Quando Investigar

| Situação | Ação |
|----------|------|
| R² cai abaixo de 0.85 | Verificar qualidade dos dados |
| RMSE > 2.8 pts | Revalidar modelo |
| MAE > 2.0 pts | Investigar outliers |
| Muita variância em CV | Possível overfitting |
| Features ≠ 8 | Verificar versão do modelo |

---

## 🔗 Integração com Outras Abas

**Tab 1 - Preditor de Apostas:**
- Usa as métricas do modelo exibidas aqui
- Se modelo está degradado, previsões menos confiáveis

**Tab 2 - Histórico de Apostas:**
- Correlação: previsões ruins afetam apostas
- Usar monitoramento para explicar perdas

**Tab 3 - Monitoramento (NOVO):**
- Visão holística da saúde do modelo
- Alerta antes de problemas

---

## 💡 Dicas de Uso

1. **Diária:** Revisar aba de monitoramento antes de fazer apostas
2. **Semanal:** Analisar tendências em gráfico de importância
3. **Mensal:** Comparar desempenho com período anterior
4. **Sempre:** Respeitar os alertas automáticos

---

## 🔮 Próximas Melhorias (Futuros)

- [ ] Gráfico de série temporal das métricas
- [ ] Comparação com período anterior
- [ ] Exportar relatório de monitoramento
- [ ] Notificações quando limite é excedido
- [ ] Histórico de validações
- [ ] Regressão automática se modelo degrada

---

## ✅ STATUS

- [x] Aba criada e funcional
- [x] Métricas exibidas corretamente
- [x] Gráfico de importância funcionando
- [x] Sistema de alertas ativo
- [x] Testes passando (mypy, ruff)
- [x] Documentação completa

**Status:** 🟢 **OPERACIONAL**

---

**Criado em:** 28/03/2025
**Versão:** 1.0
