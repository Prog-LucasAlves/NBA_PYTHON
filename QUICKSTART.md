# 🚀 Guia de Início Rápido — Preditor de Apostas NBA Pro

## Configuração em 5 Minutos

### Passo 1: Instale Dependências
```bash
cd D:\Sports\NBA
pip install -r requirements.txt
```

### Passo 2: Execute a Aplicação
```bash
streamlit run betting_app.py
```

A aplicação abre automaticamente em **http://localhost:8501**

---

## Usando a Aplicação

### 1. **Selecione um Jogador**
   - Use o dropdown da barra lateral para escolher um jogador da NBA
   - ~969 jogadores disponíveis de 7 temporadas (2019-2026)

### 2. **Configure Parâmetros de Apostas**
   - **Linha de Mercado**: Digite a linha Over/Under (ex: 25,5)
   - **Odds Decimais**: Típico é 1,95 (-105 US)
   - **Minutos Esperados**: Tempo de jogo provável do jogador

### 3. **Revise Previsões**
   - **Pontos Previstos**: Estimativa do modelo ± intervalo de confiança
   - **Sinal EV+**: VERDE (COMPRA) → VERMELHO (EVITAR)
   - **Recomendação**: OVER ou UNDER

### 4. **Analise Tendências**
   - Desempenho recente vs histórico
   - Comparação do jogador com pares similares
   - Gráficos históricos e distribuições

---

## Significados de Sinais EV+

| Sinal | Intervalo EV+ | Ação |
|--------|-----------|--------|
| ✓ **FORTE COMPRA** | > 5% | OVER (bom valor) |
| → **VALOR JUSTO** | 0-5% | OVER (sem vantagem) |
| ⚠ **MARGINAL** | -5% a 0% | Considere contexto |
| ✗ **EVITAR** | < -5% | Pule ou UNDER |

---

## Exemplo

```
Jogador: LeBron James
Linha de Mercado: 25,5 pontos @ 1,95 odds

Previsão do Modelo: 24,8 ± 2,4 pontos
• Confiança: [22,4, 27,2]
• Tendência: UP (+3,2% vs histórico)

Análise EV+:
• Percentual de Vitória do Modelo: 45,2%
• EV+: -1,23% → Sinal MARGINAL
• Recomendação: Aguarde melhor linha
```

---

## Informações do Dataset

- **3.409 registros de jogador-temporada**
- **969 jogadores únicos da NBA**
- **7 temporadas**: 2019-20 até 2025-26
- **Filtro**: Jogadores com 10+ jogos por temporada

---

## Precisão do Modelo

✅ **Score R²: 0,8654** (explica 86,54% da variância de pontos)
✅ **MAE: 1,76 pontos** (erro médio de previsão)
✅ **RMSE: 2,40 pontos** (raiz do erro quadrático médio)

---

## Arquivos

| Arquivo | Propósito |
|------|---------|
| `betting_app.py` | Aplicação Streamlit principal |
| `nba_prediction_model.py` | Mecanismo de previsão & ML |
| `demo_report.py` | Demonstração com cenários de amostra |
| `test_model.py` | Script de validação |
| `requirements.txt` | Dependências Python |

---

## O que o Modelo NÃO Consegue Prever

❌ Lesões ou dias de descanso
❌ Trades/mudanças de elenco
❌ Diferenças casa vs visitante
❌ Fadiga de jogos consecutivos
❌ Força do adversário
❌ Mudanças de escalação de última hora

---

## Dicas de Apostas

1. **Use o Critério de Kelly** para dimensionamento de posição
   - Kelly completo = `kelly_criterion` (frequentemente muito agressivo)
   - Recomendado: 25-50% do valor de Kelly
   - Exemplo: Kelly = 0,05 (5%) → Aposte 1-2,5%

2. **Estabeleça Seus Limites**
   - Aposte apenas 1-3% do seu bankroll por jogo
   - Nunca persiga perdas
   - Acompanhe suas apostas para análise de ROI

3. **Filtre por Qualidade**
   - Aposte apenas em EV+ > 2%
   - Prefira FORTE COMPRA em vez de MARGINAL
   - Verifique forma recente (Tendência UP é bom)

4. **Compare Linhas**
   - Compare odds entre casas de apostas
   - Às vezes mover meio ponto muda significativamente EV+
   - Use a aplicação para encontrar linhas perspicazes

---

## Solução de Problemas

**"Jogador não encontrado"**
- Verifique a ortografia (sensível a maiúsculas/minúsculas)
- Use o nome completo do jogador (primeiro e sobrenome)
- Tente um jogador famoso como "LeBron James"

**"ModuleNotFoundError"**
```bash
# Reinstale dependências
pip install -r requirements.txt --force-reinstall
```

**A aplicação não iniciará**
```bash
# Limpe cache Streamlit
rm -r ~/.streamlit/cache
streamlit run betting_app.py
```

---

## Próximos Passos

1. ✅ Execute a aplicação e selecione um jogador
2. 📊 Revise a previsão vs linha de mercado
3. 💰 Verifique o sinal EV+
4. 🎯 Coloque uma aposta pequena se EV+ > 2%
5. 📈 Acompanhe seus resultados ao longo do tempo

---

## Recursos

- **Jogo Responsável**: https://www.ncpgambling.org/
- **Critério de Kelly**: https://en.wikipedia.org/wiki/Kelly_criterion
- **Valor Esperado**: https://www.investopedia.com/terms/e/expected-value.asp

---

**Dúvidas?** Consulte README_BETTING.md para documentação detalhada.

**Boa sorte! 🏀🍀**
