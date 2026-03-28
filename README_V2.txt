PREDITOR DE APOSTAS NBA PRO - Versao 2.0
=========================================

Sistema profissional de análise e registro de apostas esportivas em basquete NBA
com modelo de machine learning para previsão de pontos de jogadores.

NOVIDADE v2.0
=============

Sistema completo de rastreamento de apostas com:
✓ Interface com 2 abas (Preditor + Historico)
✓ Botão de registro de apostas
✓ Persistência de dados em CSV
✓ Estatísticas automáticas
✓ Exportação de dados

INICIO RAPIDO
=============

1. Instalar dependências:
   pip install -r requirements.txt

2. Executar o app:
   streamlit run betting_app.py

3. Abrir no navegador:
   http://localhost:8501

ESTRUTURA DO PROJETO
====================

betting_app.py
  └─ Aplicativo Streamlit principal com 2 abas:
     ├─ Tab 1: Preditor de Apostas
     │  └─ Análise completa com botão registrar
     └─ Tab 2: Historico de Apostas
        └─ Tabela, estatísticas e exportação

nba_prediction_model.py
  └─ Engine de previsão com ML:
     ├─ NBAPointsPredictor class
     ├─ Treinamento com ~3,400 registros
     ├─ R² = 0.8654 (86.54% acurácia)
     └─ Calculadora de EV+

data/nba_player_stats_multi_season.csv
  └─ Base de dados com 7 temporadas (2019-2026)
     └─ 969 jogadores únicos
     └─ 11 features estatísticas

historico_apostas.csv (gerado automaticamente)
  └─ Registro persistente de todas as apostas

COMO USAR
=========

PASSO 1: PREDITOR
- Selecione um jogador no sidebar
- Defina Linha (O/U), Odds e Minutos Esperados
- Revise a previsão de pontos
- Analise o EV+ (Expected Value Plus)

PASSO 2: REGISTRAR APOSTA
- Insira o valor que deseja apostar (R$)
- Escolha tipo: GREEN (Compra) ou RED (Evitar)
- Clique em "REGISTRAR APOSTA"
- Sucesso! A aposta foi salva em CSV

PASSO 3: HISTORICO
- Navegue para aba "Historico de Apostas"
- Veja todas as apostas registradas
- Consulte estatísticas gerais
- Resumo por jogador
- Exporte como CSV

COLUNAS DE DADOS
================

Ao registrar uma aposta, as seguintes informações são salvas:

| Campo          | Descrição                              |
|----------------|----------------------------------------|
| Data           | Timestamp do registro                  |
| Jogador        | Nome do jogador selecionado            |
| Linha          | Valor do over/under                    |
| Odd            | Odds decimais da casa                  |
| EV+%           | Valor esperado percentual              |
| Vitória%       | Probabilidade prevista pelo modelo     |
| Valor Aposta   | Quantia apostada em Reais              |
| Aposta         | GREEN (compra) ou RED (evitar)        |
| Resultado      | WIN/LOSS (preenchimento manual)        |
| Lucro/Prejuízo | Cálculo automático de ganho/perda     |

SINAIS DO MODELO
================

EV+ > 5%  →  FORTE COMPRA (Strong Buy)
EV+ > 0%  →  VALOR JUSTO (Fair Value)
EV+ > -5% →  MARGINAL (Marginal)
EV+ < -5% →  EVITAR (Avoid)

PERFORMANCE DO MODELO
====================

- R² Score: 0.8654 (explica 86.54% da variância)
- RMSE: 2.40 pontos
- MAE: 1.76 pontos
- Desvio padrão residual: 2.39

Features mais importantes:
1. Minutos (MIN) - 3.47
2. Turnovers (TOV) - 3.08
3. Defensive Rebounds (DREB) - 2.07

DADOS UTILIZADOS
================

- Período: 2019-20 a 2025-26 (7 temporadas)
- Jogadores: 969 únicos
- Registros: 3,409 (jogador-temporada)
- Critério: Mínimo 10 jogos por temporada
- Features: 11 estatísticas avançadas

REQUISITOS
==========

- Python 3.8+
- pandas >= 1.3.0
- streamlit >= 1.0.0
- scikit-learn >= 0.24.0
- numpy >= 1.21.0
- altair >= 4.1.0
- scipy >= 1.7.0

Instale tudo com:
  pip install -r requirements.txt

ARQUIVOS IMPORTANTES
====================

Documentação:
- RESUMO_ENTREGA.txt (este arquivo resumido)
- GUIA_COMPLETO_V2.txt (guia detalhado do usuário)
- ATUALIZACOES_V2.txt (mudanças técnicas)
- README_BETTING.md (documentação técnica original)
- QUICKSTART.md (início rápido em português)

Código:
- betting_app.py (aplicativo principal - 19KB)
- nba_prediction_model.py (modelo ML - 12KB)
- test_model.py (testes do modelo)
- demo_report.py (demonstração)

Dados:
- data/nba_player_stats_multi_season.csv (base histórica)
- requirements.txt (dependências)

BOAS PRATICAS
=============

1. BACKUP: Faça backup regular de historico_apostas.csv
2. RESPONSABILIDADE: Jogue apenas com dinheiro que pode perder
3. DIVERSIFICAÇÃO: Não aposte todo o bankroll em uma aposta
4. ANÁLISE: Sempre revise o EV+ antes de registrar
5. REGISTRO: Mantenha atualizados Resultado e Lucro/Prejuízo

TROUBLESHOOTING
===============

Problema: "App não inicia"
Solução: Verifique se está no diretório D:\Sports\NBA
         Execute: pip install -r requirements.txt

Problema: "Jogador não encontrado"
Solução: Aperte Ctrl+F na barra de seleção para buscar

Problema: "Erro ao salvar aposta"
Solução: Verifique se tem permissão de escrita no diretório
         Feche qualquer planilha aberta do historico_apostas.csv

Problema: "Caracteres estranhos no CSV"
Solução: Abra com encoding UTF-8 (Excel: Arquivo > Abrir > Opções)

ROADMAP FUTURO
==============

v2.1 (Próximo):
- Preenchimento de resultados na interface
- Cálculo automático de lucro/prejuízo
- Gráficos de performance

v2.2:
- Integração com APIs de odds em tempo real
- Alertas automáticos de oportunidades

v3.0:
- Backtesting histórico automático
- Dashboard de ROI
- Machine learning para otimizar seleções

SUPORTE
=======

Para dúvidas ou problemas:
1. Consulte GUIA_COMPLETO_V2.txt
2. Verifique ATUALIZACOES_V2.txt para mudanças técnicas
3. Revise os arquivos de documentação em português

RESPONSABILIDADE LEGAL
======================

AVISO: Este aplicativo é APENAS para fins educacionais e de entretenimento.

- Apostas esportivas envolvem risco
- Você pode perder todo o dinheiro apostado
- Não é garantia de lucro futuro
- Consulte as leis locais sobre apostas
- Jogue responsavelmente

CRÉDITOS
========

Desenvolvido com:
- Python 3.13
- Streamlit (interface)
- Scikit-learn (machine learning)
- Pandas (análise de dados)
- NumPy (computação numérica)
- SciPy (cálculos científicos)
- Altair (visualizações)

Dados: NBA Stats (2019-2026)

VERSÃO
======

v2.0 - Março 2026

Versão inicial com sistema de abas e persistência de dados.

---

Desenvolvido para apostadores sérios com análise profissional de dados.
