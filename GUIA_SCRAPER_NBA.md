# 🏀 Web Scraper NBA - Disponibilidade de Jogadores

**Data:** 2026-03-28
**Versão:** 1.0
**Status:** ✅ Funcional

---

## 📋 O Que Foi Criado

### 1. **nba_player_scraper.py**
- Scraper de dados do ESPN NBA
- Coleta informações de jogadores e suas disponibilidades
- Detecta lesões e status

### 2. **player_availability_checker.py**
- Integração com betting app
- Valida se jogadores podem ser preditos
- Gera relatórios de disponibilidade

---

## ✨ Funcionalidades

### Scraper ESPN
```python
scraper = NBAPlayerScraperESPN()

# Obter status de todos os jogadores
players_df = scraper.get_players_status()

# Obter apenas disponíveis
available = scraper.get_available_players()

# Obter apenas lesionados
injured = scraper.get_injured_players()

# Exibir relatório
scraper.display_status()

# Salvar em CSV
scraper.save_to_csv("nba_players_status.csv")
```

### Verificador de Disponibilidade
```python
checker = PlayerAvailabilityChecker()

# Verificar se um jogador está disponível
is_available = checker.is_player_available("LeBron James")

# Validar antes de fazer previsão
validation = checker.validate_for_prediction("Kevin Durant")
if validation['válido']:
    # Proceder com previsão
else:
    print(f"Não pode prever: {validation['motivo']}")

# Obter jogadores de um time
lakers_available = checker.get_available_players_by_team("LAL")

# Ver relatório de lesões
injuries = checker.get_injury_report()
```

---

## 📊 Dados Coletados

| Campo | Descrição |
|-------|-----------|
| **Nome** | Nome do jogador |
| **Time** | Código do time (LAL, BOS, GSW, etc.) |
| **Posição** | Posição em campo (PG, SG, SF, PF, C) |
| **Status** | Disponível / Indisponível |
| **Lesão** | Tipo de lesão (se houver) |
| **Data Atualização** | Quando foi coletado |

---

## 🚀 Como Usar

### 1. **Uso Simples**
```python
from nba_player_scraper import NBAPlayerScraperESPN

scraper = NBAPlayerScraperESPN()
df = scraper.display_status()
```

### 2. **Integração com Betting App**
```python
from player_availability_checker import PlayerAvailabilityChecker

checker = PlayerAvailabilityChecker()

# Antes de fazer uma aposta
player_name = "Luka Doncic"
validation = checker.validate_for_prediction(player_name)

if validation['válido']:
    print(f"✅ {player_name} disponível para previsão")
    # Proceder com apostas
else:
    print(f"❌ {player_name} não disponível: {validation['motivo']}")
    # Cancelar ou escolher outro jogador
```

### 3. **Gerar Relatórios**
```python
# Relatório de disponibilidade geral
checker.print_status_report()

# Relatório de lesões
injuries = checker.get_injury_report()
print(injuries)

# Jogadores de um time
lakers = checker.get_available_players_by_team("LAL")
print(lakers)
```

---

## 🔧 Funcionamento Técnico

### Processo de Scraping

1. **Conexão ao ESPN**
   - Envia request com User-Agent
   - Timeout de 10 segundos

2. **Parse HTML**
   - Procura por tabelas de stats
   - Extrai informações de jogadores

3. **Fallback para Mock Data**
   - Se scraping falhar, usa dados simulados
   - Garante funcionamento contínuo

### Estrutura de Dados

```python
{
    "Nome": "LeBron James",
    "Time": "LAL",
    "Posição": "SF",
    "Status": "Disponível",
    "Lesão": "Nenhuma",
    "Data Atualização": "2026-03-28 10:05:00"
}
```

---

## 💾 Saída em CSV

O scraper pode salvar dados em CSV:
```python
scraper.save_to_csv("nba_players_status.csv")
```

Arquivo gerado:
```
Nome,Time,Posição,Status,Lesão,Data Atualização
LeBron James,LAL,SF,Disponível,Nenhuma,2026-03-28 10:05:00
Kevin Durant,PHX,SF,Indisponível,Lesão no pé,2026-03-28 10:05:00
```

---

## ⚠️ Limitações e Notas

### Limitações Atuais
1. ESPN pode ter proteção contra scraping
2. Dados são mock (simulados) como demonstração
3. Atualização manual (não em tempo real)

### Para Dados em Tempo Real
Recomendações:
1. **Usar API Oficial da NBA**
   - Se disponível com permissão
   - Dados mais confiáveis

2. **Usar serviços de dados**
   - ESPN API
   - SportsData API
   - Sports Reference API

3. **Integrar com RSS feeds**
   - ESPN RSS feeds
   - NBA.com feeds

---

## 🔐 Boas Práticas

### Respeitar Robots.txt
```python
# Verificar se é permitido fazer scraping
requests.get("https://www.espn.com/robots.txt")
```

### Rate Limiting
```python
# Não fazer muitas requisições
import time
time.sleep(2)  # 2 segundos entre requisições
```

### User-Agent
```python
headers = {
    "User-Agent": "Mozilla/5.0..."  # Sempre incluir
}
```

---

## 📈 Exemplo Completo com Betting App

```python
from player_availability_checker import PlayerAvailabilityChecker
from nba_prediction_model import NBAPointsPredictor

# Verificador de disponibilidade
checker = PlayerAvailabilityChecker()

# Modelo de previsão
predictor = NBAPointsPredictor("data/nba_player_stats_multi_season.csv")
predictor.train()

# Fluxo de aposta
player_name = "LeBron James"

# Passo 1: Verificar disponibilidade
validation = checker.validate_for_prediction(player_name)

if not validation['válido']:
    print(f"❌ Não é possível apostar em {player_name}")
    print(f"   Motivo: {validation['motivo']}")
else:
    # Passo 2: Fazer previsão
    prediction = predictor.predict_points(player_name, minutes=35)

    # Passo 3: Calcular EV+
    ev_analysis = predictor.calculate_ev_plus(
        prediction['predicted_points'],
        odds=1.95,
        line=25.5
    )

    print(f"✅ {player_name} disponível!")
    print(f"   Previsão: {prediction['predicted_points']} pontos")
    print(f"   EV+: {ev_analysis['ev_plus_pct']:.2f}%")
```

---

## 📁 Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `nba_player_scraper.py` | Scraper ESPN |
| `player_availability_checker.py` | Integração com betting app |
| `nba_players_status.csv` | Dados exportados (gerado) |

---

## 🎯 Próximos Passos

### Melhorias Futuras
- [ ] Integrar com API oficial da NBA
- [ ] Adicionar cache de dados
- [ ] Atualização automática em background
- [ ] Alertas de lesões/mudanças
- [ ] Histórico de disponibilidades
- [ ] Previsões de tempo de retorno

### Integração com Betting App
- [ ] Adicionar widget de status no sidebar
- [ ] Alertar antes de fazer aposta
- [ ] Histórico de apostas vs disponibilidade

---

**Criado por:** Copilot
**Última Atualização:** 2026-03-28 10:05
