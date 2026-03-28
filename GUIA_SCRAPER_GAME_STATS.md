# 🏀 Web Scraper de Estatísticas de Jogadores por Partida

**Data:** 2026-03-28
**Versão:** 1.0
**Status:** ✅ Funcional

---

## 📋 Resumo

Sistema completo para coleta, processamento e integração de dados de performance de jogadores da NBA por partida. Ideal para:

- 🎯 Treinamento de modelos preditivos
- 📊 Análise histórica de performance
- 📈 Comparação de estatísticas
- 🤖 Machine Learning e análise avançada

---

## 📁 Arquivos Criados

### 1. **nba_game_stats_scraper.py** (380 linhas)
Scraper principal que coleta dados diretamente do ESPN.

```python
from nba_game_stats_scraper import NBAGameStatsScraper

# Inicializar
scraper = NBAGameStatsScraper()

# Coletar dados da temporada 2024
df = scraper.scrape_game_stats(season=2024, max_games=100)

# Salvar em CSV
scraper.save_to_csv(df, "nba_game_stats_2024.csv")

# Gerar relatório
scraper.generate_report(df)

# Obter stats agregadas de um jogador
stats = scraper.get_player_season_stats("LeBron", df)
```

**Classe: `NBAGameStatsScraper`**

| Método | Descrição |
|--------|-----------|
| `scrape_game_stats(season, max_games)` | Coleta dados de partidas da temporada |
| `scrape_recent_games(days)` | Coleta partidas dos últimos N dias |
| `save_to_csv(df, filename)` | Salva DataFrame em CSV |
| `get_player_season_stats(player_name, df)` | Retorna stats agregadas de um jogador |
| `generate_report(df)` | Gera relatório dos dados coletados |

**Estatísticas Coletadas:**

| Abreviação | Significado |
|------------|-------------|
| FG | Field Goals (acertos) |
| FGA | Field Goals Attempted (tentativas) |
| 3PT | 3-Pointers (3-pontos acertos) |
| 3PA | 3-Pointers Attempted (3-pontos tentativas) |
| FT | Free Throws (lances livres) |
| FTA | Free Throws Attempted (lances tentativas) |
| OREB | Offensive Rebounds (rebotes ofensivos) |
| DREB | Defensive Rebounds (rebotes defensivos) |
| REB | Total Rebounds (rebotes totais) |
| AST | Assists (assistências) |
| TOV | Turnovers (erros) |
| STL | Steals (roubos) |
| BLK | Blocks (bloqueios) |
| PF | Personal Fouls (faltas pessoais) |
| PTS | Points (pontos) |

---

### 2. **process_game_stats.py** (280 linhas)
Processa e integra dados de partidas com o sistema de previsão.

```python
from process_game_stats import GameStatsProcessor

processor = GameStatsProcessor()

# 1. Coletar
raw_df = processor.collect_game_stats(season=2024)

# 2. Processar
processed_df = processor.process_game_stats()

# 3. Salvar
processor.save_processed_data(processed_df, "processed.csv")

# 4. Agregar
aggregated = processor.aggregate_player_stats()

# 5. Mesclar com histórico
merged = processor.merge_with_historical("training_data.csv")
```

**Classe: `GameStatsProcessor`**

| Método | Descrição |
|--------|-----------|
| `collect_game_stats(season, max_games)` | Coleta dados brutos |
| `process_game_stats()` | Processa e normaliza dados |
| `aggregate_player_stats()` | Agrega por jogador e temporada |
| `merge_with_historical(csv_path)` | Mescla com dados históricos |
| `save_processed_data(df, filename)` | Salva dados processados |

**Pipeline de Processamento:**

```
Dados Brutos (ESPN)
        ↓
   Limpeza (remove duplicatas, NaNs)
        ↓
   Conversão de Tipos (numérico, datetime)
        ↓
   Stats Derivadas (percentuais: FG%, 3P%, FT%)
        ↓
   Normalização de Nomes
        ↓
   Dados Processados ✅
```

---

## 💡 Exemplos de Uso

### Exemplo 1: Coletar Dados Simples

```python
from nba_game_stats_scraper import NBAGameStatsScraper

scraper = NBAGameStatsScraper()

# Coletar últimas 10 partidas
df = scraper.scrape_game_stats(season=2024, max_games=10)

# Salvar
scraper.save_to_csv(df, "recent_games.csv")

# Exibir resumo
scraper.generate_report(df)
```

**Saída esperada:**
```
🏀 Coletando dados da temporada 2024-2025...
  ✓ 50 linhas coletadas...
  ✓ 100 linhas coletadas...
✅ 250 registros coletados com sucesso!

✅ Dados salvos em: recent_games.csv
   Total: 250 registros
   Colunas: game_id, game_date, season, player_name, ...
```

### Exemplo 2: Processar e Normalizar

```python
from process_game_stats import GameStatsProcessor

processor = GameStatsProcessor()

# Coletar
raw = processor.collect_game_stats(season=2024, max_games=500)

# Processar (limpeza, normalização, cálculos)
processed = processor.process_game_stats()

# Salvar
processor.save_processed_data(processed, "game_stats_2024.csv")

# Relatório
processor.generate_processing_report()
```

### Exemplo 3: Agregar por Jogador

```python
processor = GameStatsProcessor()
processor.collect_game_stats(season=2024, max_games=500)
processor.process_game_stats()

# Obter média de stats por jogador
aggregated = processor.aggregate_player_stats()

# aggregated agora tem:
# player_name, team, season, FG, FGA, FG_PCT, 3PT, ...
```

### Exemplo 4: Mesclar com Histórico

```python
# Supondo que você tenha um arquivo "training_data.csv" existente

processor = GameStatsProcessor(base_path=".")

# Coletar e processar novos dados
processor.collect_game_stats(season=2024)
processor.process_game_stats()

# Mesclar com histórico e salvar
merged = processor.merge_with_historical("training_data.csv")
processor.save_processed_data(merged, "training_data_updated.csv")
```

---

## 📊 Estrutura dos Dados

### Dados Brutos (antes de processar):

```
game_id        game_date    season    player_name      team    opponent   home_away   FG   FGA   FG_PCT   ...
g123456        2024-03-20   2024      LeBron James     LAL     GSW        Home        8    15    NULL     ...
g123456        2024-03-20   2024      Stephen Curry   GSW     LAL        Away        9    18    NULL     ...
g123457        2024-03-21   2024      Luka Doncic     DAL     MIA        Home        10   22    NULL     ...
```

### Dados Processados (depois de processar):

```
game_id        game_date    season    player_name      team    opponent   home_away   FG   FGA   FG_PCT    3PT   3PA   3PT_PCT   ...
g123456        2024-03-20   2024      Lebron James     LAL     GSW        Home        8    15    53.33    2     6     33.33     ...
g123456        2024-03-20   2024      Stephen Curry   GSW     LAL        Away        9    18    50.00    5     11    45.45     ...
g123457        2024-03-21   2024      Luka Doncic     DAL     MIA        Home        10   22    45.45    3     8     37.50     ...
```

### Dados Agregados (por temporada):

```
player_name      team    season    GP    FG        FGA       FG_PCT      3PT       3PA       3PT_PCT    REB       AST    ...
LeBron James     LAL     2024      42    7.21      15.19     47.42       1.81      4.76      38.05      5.29      2.76   ...
Stephen Curry    GSW     2024      38    8.18      16.24     50.37       5.32      11.45     46.40      3.18      7.42   ...
```

---

## ⚠️ Avisos e Limitações

### 1. Taxa de Requisições
- ESPN pode bloquear requisições muito frequentes
- **Recomendação**: Máximo 1 request a cada 2 segundos
- Use `max_games` para limitar coleta inicial

### 2. Dados Incompletos
- Histórico antes de 2019 pode ter dados limitados
- Algumas stats podem ser NULL ou 0
- Processador preenche automaticamente com 0

### 3. Formato de Nomes
- Nomes são normalizados (capitalizados)
- Variações (ex: "Luka Doncic" vs "DONCIC, Luka") são unificadas
- Nomes com caracteres especiais podem ser truncados

### 4. Performance
- Coletar 500+ partidas pode levar 2-5 minutos
- Usar `max_games` menor para testes

### 5. Dados Ausentes
- Se ESPN estiver indisponível, retorna estrutura vazia
- Verifique sua conexão de internet

---

## 🔧 Integração com Modelo de Previsão

```python
import pandas as pd
from process_game_stats import GameStatsProcessor
from nba_prediction_model import NBAPointsPredictor

# 1. Processar dados de partidas
processor = GameStatsProcessor()
processor.collect_game_stats(season=2024, max_games=1000)
processor.process_game_stats()
processor.save_processed_data(processor.processed_data, "games_2024.csv")

# 2. Carregar dados agregados no modelo
predictor = NBAPointsPredictor()
predictor.load_data("games_2024.csv")
predictor.train()

# 3. Fazer previsões
prediction = predictor.predict_points(
    player_name="LeBron James",
    season=2024,
    min_games=10
)
print(f"Previsão: {prediction:.1f} pontos")
```

---

## 📈 Fluxo Completo de Uso

```
1. Coletar Dados
   ├─ ESPN Web Scraper
   ├─ ~250-500 registros por 50 partidas
   └─ Salvar: game_stats_raw.csv

2. Processar Dados
   ├─ Limpeza (remove duplicatas)
   ├─ Normalização (tipos, nomes)
   ├─ Stats derivadas (%, etc)
   └─ Salvar: game_stats_processed.csv

3. Agregar por Jogador
   ├─ Média de stats por temporada
   ├─ Adicionar GP (games played)
   └─ Salvar: game_stats_aggregated.csv

4. Integrar com Histórico
   ├─ Mesclar com training_data.csv existente
   ├─ Remover duplicatas
   └─ Salvar: training_data_updated.csv

5. Treinar/Revalidar Modelo
   ├─ NBAPointsPredictor.load_data()
   ├─ NBAPointsPredictor.train()
   └─ Métricas (R², RMSE, MAE)
```

---

## 🎯 Casos de Uso

### Caso 1: Manter Dados Sempre Atualizados
```python
# Executar diariamente
processor = GameStatsProcessor()
processor.collect_game_stats(season=2024, max_games=50)
processor.process_game_stats()
merged = processor.merge_with_historical("training_data.csv")
processor.save_processed_data(merged, "training_data.csv")
```

### Caso 2: Análise de Desempenho Histórico
```python
# Coletar histórico completo
scraper = NBAGameStatsScraper()
df = scraper.scrape_game_stats(season=2024, max_games=2000)

# Filtrar por time
lakers = df[df["team"] == "LAL"]
print(f"Partidas Lakers: {lakers['game_id'].nunique()}")

# Stats de um jogador
luka_stats = scraper.get_player_season_stats("Luka", df)
```

### Caso 3: Detecção de Anomalias
```python
processor = GameStatsProcessor()
processor.collect_game_stats(season=2024)
processed = processor.process_game_stats()

# Outliers (performances extremas)
high_scorers = processed[processed["PTS"] > processed["PTS"].quantile(0.95)]
print(f"Top 5% performances: {len(high_scorers)} registros")
```

---

## 📋 Checklist de Implementação

- ✅ Scraper implementado (ESPN)
- ✅ Processamento de dados
- ✅ Agregação por jogador
- ✅ Integração com histórico
- ✅ Validação de sintaxe
- ✅ Documentação completa
- ⏳ Integração com betting_app.py (próximo passo)

---

## 🚀 Próximos Passos

1. **Integrar com Betting App**
   - Adicionar botão para atualizar dados de partidas
   - Exibir últimos dados coletados no sidebar
   - Dashboard com estatísticas por jogador

2. **Automação**
   - Script de atualização diária
   - Agendador (cron/task scheduler)
   - Alertas quando dados desatualizam

3. **Análise**
   - Trends de performance
   - Comparação home vs away
   - Impacto de opponent na performance

4. **Qualidade**
   - Validação de dados
   - Detecção de outliers
   - Versionamento de datasets

---

## 📞 Suporte

Se encontrar erros:

1. Verifique sua conexão de internet
2. Tente limitar `max_games` (ex: 10 em vez de 1000)
3. Verifique se ESPN está acessível
4. Valide dados com `generate_report()`

---

**Status:** ✅ Pronto para Uso
**Última Atualização:** 2026-03-28
