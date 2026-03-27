# 🏀 Preditor de Apostas NBA PRO

**Sistema profissional de previsão de pontos de jogadores baseado em IA com análise de Valor Esperado (EV+) para apostas esportivas**

---

## 📊 Visão Geral

**Preditor de Apostas NBA Pro** é uma aplicação sofisticada de aprendizado de máquina que prevê o desempenho de pontos de jogadores individuais da NBA nos próximos jogos. Combina modelagem preditiva com análise profissional de apostas esportivas para ajudar apostadores a identificar oportunidades valiosas.

### Recursos Principais

✅ **Modelo de Previsão com ML Avançado**
- Regressão linear treinada em 3.900+ registros de desempenho de jogadores multi-temporada
- **Score R²: 0.8654** (86,54% da variância explicada)
- **RMSE: 2,40 pontos** (previsões altamente precisas)
- **MAE: 1,76 pontos** (margem média de erro)
- Features: Minutos, FG%, 3P%, FT%, AST, REB, bloqueios, roubos, turnovers

✅ **Análise EV+ (Valor Esperado Plus)**
- Compara previsões do modelo contra odds do mercado
- Identifica oportunidades de apostas +EV (lucrativas)
- Inclui cálculos do Critério de Kelly para dimensionamento ótimo de apostas
- Calibração de probabilidade usando scipy.stats

✅ **Painel de Controle Profissional**
- Previsões de pontos em tempo real com intervalos de confiança
- Classificação de sinais EV+ (FORTE COMPRA / VALOR JUSTO / MARGINAL / EVITAR)
- Análise de tendências (desempenho recente vs histórico)
- Revisão dos últimos 10 jogos
- Gráficos de desempenho multi-temporada
- Comparação com pares (vs jogadores da mesma posição)
- Visualização de importância das features

✅ **Insights Orientados por Dados**
- 7 temporadas de dados de jogadores da NBA (2019-20 até 2025-26)
- Médias de jogadores, métricas de consistência, análise baseada em posição
- Análise de correlação entre minutos e pontos
- Gráficos de distribuição histórica

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.8+
- Gerenciador pip

### Instalação

```bash
# Clone/navegue até o diretório do projeto
cd D:\Sports\NBA

# Instale as dependências
pip install -r requirements.txt

# Ou instale manualmente
pip install pandas numpy scikit-learn scipy streamlit altair plotly
```

### Executando a Aplicação

```bash
# Inicie a aplicação Streamlit
streamlit run betting_app.py

# A aplicação abre em http://localhost:8501
```

---

## 📈 Arquitetura do Modelo

### Pipeline de Processamento de Dados

```
Dados CSV Brutos
    ↓
Validação e Limpeza de Dados
    ↓
Engenharia de Features (11 features)
    ↓
Ponderação por Recência (temporadas recentes → peso maior)
    ↓
Normalização com StandardScaler
    ↓
Treinamento com LinearRegression
    ↓
Avaliação e Métricas do Modelo
```

### Features Utilizadas

| Feature | Descrição |
|---------|-----------|
| `MIN` | Minutos Por Jogo |
| `FG_PCT` | Percentual de Arremessos |
| `FG3_PCT` | Percentual de 3-Pontos |
| `FT_PCT` | Percentual de Lances Livres |
| `AST` | Assistências Por Jogo |
| `REB` | Rebotes Por Jogo |
| `OREB` | Rebotes Ofensivos |
| `DREB` | Rebotes Defensivos |
| `STL` | Roubos Por Jogo |
| `BLK` | Bloqueios Por Jogo |
| `TOV` | Turnovers Por Jogo |

### Variável Alvo
- **PTS**: Pontos Por Jogo (contínua, intervalo 0-70+)

---

## 💰 Cálculo e Estratégia de Apostas EV+

### O que é EV+?

EV+ (Valor Esperado Plus) mede se uma aposta tem retorno esperado positivo:

```
EV+ = (Probabilidade do Modelo × Odds) - 1
```

**Interpretação:**
- **EV+ > 5%**: Expectativa positiva forte (FORTE COMPRA)
- **EV+ 0% a 5%**: Valor justo (VALOR JUSTO)
- **EV+ -5% a 0%**: Margem marginal (MARGINAL)
- **EV+ < -5%**: Expectativa negativa (EVITAR)

### Critério de Kelly

Para dimensionamento ótimo de apostas:
```
Percentual Kelly = (probabilidade × odds - 1) / (odds - 1)
```

*Recomendado: Use Kelly fracionário (25-50% do Kelly completo) para segurança*

### Exemplo

```
Previsão do Jogador: 24,5 pontos
Linha de Mercado: 25,5 (Over/Under)
Odds: 1,95 (típico)

Percentual de Vitória do Modelo (Over da linha): 48%
EV+: -2,35% → Sinal: MARGINAL (pular ou aposta pequena)
```

---

## 📁 Estrutura do Projeto

```
D:\Sports\NBA/
├── betting_app.py                      # Aplicação principal Streamlit
├── nba_prediction_model.py             # Mecanismo de previsão & ML
├── test_model.py                       # Script de validação do modelo
├── data/
│   └── nba_player_stats_multi_season.csv  # Dataset (3900+ linhas)
├── requirements.txt                    # Dependências Python
└── README_BETTING.md                   # Este arquivo
```

---

## 🔧 Configuração

### Controles da Barra Lateral

**Seleção de Jogador**
- Buscar/selecionar entre 900+ jogadores da NBA
- Carrega automaticamente estatísticas do jogador

**Parâmetros de Apostas**
- `Linha de Mercado (O/U)`: Linha Over/Under da casa de apostas
- `Odds Decimais`: Odds para a aposta (1,95 = -105 US)
- `Minutos Esperados`: Tempo de jogo previsto

**Exibição de Desempenho do Modelo**
- Score R²
- RMSE (erro de previsão)
- MAE (erro absoluto médio)

---

## 📊 Seções do Painel de Controle

### 1. Linha de Métricas Principais
- **Pontos Previstos**: Previsão do modelo com confiança ±desvio padrão
- **Tendência**: Comparação recente vs histórica com mudança percentual
- **Minutos Médios**: Tempo de jogo esperado
- **R² do Modelo**: Métrica de precisão do modelo e MAE

### 2. Análise EV+
- **Valor EV+**: Percentual de ROI esperado
- **Sinal**: Classificação COMPRA/JUSTO/MARGINAL/EVITAR
- **Recomendação**: Over ou Under
- **Métricas Detalhadas**: Probabilidades, Critério de Kelly, odds implícitas

### 3. Análise de Desempenho do Jogador
- Médias de temporada (PPG, MPG, Posição, Time, Tempo de atuação)
- Comparação recente vs histórica
- Análise dos últimos 10 jogos

### 4. Gráficos de Desempenho Histórico
- **Tendência de Pontos**: PPG ao longo de todas as temporadas com linha média
- **Tendência de Minutos**: Evolução do tempo de jogo
- **Distribuição de Pontos**: Histograma do intervalo de pontuação do jogador
- **Scatter Minutos vs Pontos**: Análise de correlação com linha de tendência

### 5. Comparação com Pares
- Top 15 jogadores da mesma posição (por PPG)
- Comparação em PTS, MIN, FG%, AST, REB
- Destaque da classificação do jogador selecionado

### 6. Importância das Features
- Gráfico de barras mostrando quais estatísticas impactam mais a previsão
- Magnitudes dos coeficientes

---

## 🎯 Casos de Uso

### Para Apostadores Casuais
1. Selecione um jogador que deseja apostar
2. Configure a linha de mercado e odds
3. Verifique o sinal EV+
4. Revise as tendências históricas e comparação com pares
5. Decida COMPRAR ou PULAR a aposta

### Para Traders Profissionais
1. Use EV+ como critério de seleção sistemática
2. Aplique o Critério de Kelly para dimensionamento de posição
3. Acompanhe a precisão do modelo ao longo do tempo (R², MAE)
4. Construa estratégias de apostas usando filtros de sinal

### Para Cientistas de Dados
1. Analise a importância das features na previsão de pontos de jogadores
2. Estude resíduos e distribuição de erros
3. Explore dados em diferentes posições/times
4. Estenda o modelo com features adicionais (casa/visitante, adversário, jogos consecutivos, etc)

---

## 📚 Desempenho do Modelo

### Métricas Gerais (Dados de Validação)

| Métrica | Valor | Interpretação |
|--------|-------|-----------------|
| **Score R²** | 0,8654 | Modelo explica 86,54% da variância de pontos |
| **RMSE** | 2,40 pts | Erro quadrático médio da raiz |
| **MAE** | 1,76 pts | Erro absoluto médio de previsão |
| **Desvio Padrão Residual** | 2,39 pts | Intervalo de confiança (±1σ) |

### Distribuição

- **Resíduos**: Aproximadamente distribuídos normalmente ao redor de 0
- **Outliers**: ~5% das previsões desviadas por >±5 pontos (provavelmente devido a lesões, descanso, fatores de combinação importantes)

---

## ⚠️ Limitações e Avisos

### Limitações do Modelo
1. **NÃO considera**:
   - Lesões de jogadores ou dias de descanso
   - Mudanças de escalação de última hora
   - Jogos em casa vs visitante
   - Força da oposição
   - Fadiga de jogos consecutivos
   - Trades ou mudanças de elenco no meio da temporada

2. **Qualidade dos Dados**:
   - Dados históricos datam de 2019-20 em diante
   - Jogadores com < 10 jogos por temporada são filtrados
   - Algumas estatísticas podem ter valores ausentes (preenchidas com 0)

3. **Risco de Apostas**:
   - Todas as previsões são estimativas estatísticas, NÃO garantias
   - Apostas esportivas envolvem risco de perda financeira
   - Até apostas +EV podem perder no curto prazo (variância)
   - Casas de apostas têm ajustes rápidos e movimentos de linha

### Jogo Responsável

🚨 **Por favor, jogue de forma responsável:**
- Aposte apenas dinheiro que pode perder
- Nunca persiga perdas
- Estabeleça limites de apostas
- Evite apostar sob influência
- Se lutar contra o vício em jogos, procure ajuda: [NCPG Helpline](https://www.ncpgambling.org/)

---

## 🔄 Melhorias Futuras

- [ ] Integração com API de relatórios de lesões
- [ ] Distinção entre jogos em casa/visitante
- [ ] Classificações de força do adversário
- [ ] Detecção de dias de descanso
- [ ] Comparação de modelos XGBoost/LightGBM
- [ ] Sistema de votação por ensemble
- [ ] Atualização de odds em tempo real
- [ ] Simulador de ticket de apostas
- [ ] Rastreamento de desempenho/backtesting
- [ ] Mercados de adereços de jogador (rebotes, assistências)

---

## 📝 Detalhes Técnicos

### Dependências

```
pandas>=1.3.0          # Processamento de dados
numpy>=1.21.0          # Computação numérica
scikit-learn>=1.0.0    # Aprendizado de máquina
scipy>=1.7.0           # Computação científica
streamlit>=1.20.0      # Aplicação web
altair>=4.2.0          # Gráficos interativos
plotly>=5.0.0          # Visualização avançada
```

### Arquivos

**betting_app.py** (14.5 KB)
- UI Streamlit e painel de controle
- Seleção de jogador e filtragem
- Gráficos e visualizações
- Exibição e análise de EV+

**nba_prediction_model.py** (11.7 KB)
- Classe `NBAPointsPredictor`
- Carregamento e pré-processamento de dados
- Treinamento do modelo (com ponderação por recência)
- Previsão e intervalos de confiança
- Cálculo de EV+
- Geração de comparação com pares

**test_model.py** (1.4 KB)
- Script de validação rápido
- Testa funcionalidade básica
- Previsões e cálculos de EV+ de amostra

---

## 🤝 Suporte e Contribuição

### Problemas
Se encontrar bugs ou tiver sugestões:
1. Verifique a documentação existente
2. Verifique se o caminho do arquivo de dados está correto
3. Verifique se todas as dependências estão instaladas

### Perguntas
Consulte a documentação inline e docstrings no código em:
- Classe `NBAPointsPredictor`
- Método `predict_points()`
- Método `calculate_ev_plus()`

---

## 📜 Licença

Este projeto é fornecido como está para fins educacionais e de entretenimento.

---

## 🙏 Agradecimentos

- Dados de estatísticas de jogadores da NBA
- Scikit-learn para framework de ML
- Streamlit para bela UI web
- Altair para visualização

---

**Construído com ❤️ para apostadores sérios e entusiastas de dados**

*Última Atualização: Março 2026*
*Versão: 1.0*
