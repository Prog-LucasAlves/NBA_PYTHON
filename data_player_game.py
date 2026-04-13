import time
from typing import Dict, List

import pandas as pd
import requests

# ===============================
# Configurações globais
# ===============================

BASE_URL = "https://stats.nba.com/stats/leaguegamelog"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com", "Connection": "keep-alive"}

SLEEP_SECONDS = 1.2


# ===============================
# Função para verificar total de registros
# ===============================


def get_total_records_count(season: str, season_type: str = "Regular Season") -> int:
    """
    Verifica quantos registros existem para uma temporada.
    """
    params = {"LeagueID": "00", "Season": season, "SeasonType": season_type, "PlayerOrTeam": "P", "Counter": 1, "Offset": 0, "Direction": "DESC", "Sorter": "DATE"}

    try:
        response = requests.get(BASE_URL, headers=HEADERS, params={k: str(v) for k, v in params.items()}, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Tenta encontrar o total nos metadados
        result_set = data["resultSets"][0]

        # Verifica se há um campo totalSets
        if "metadata" in data and "totalSets" in data["metadata"]:
            return int(data["metadata"]["totalSets"])

        # Alternativa: verifica o número de resultados na primeira página
        # e assume que é o total (se Counter=1, rowSet terá apenas 1 registro)
        return len(result_set.get("rowSet", []))

    except Exception as e:
        print(f"  - Erro ao verificar total: {e}")
        return -1


# ===============================
# Função principal de coleta CORRIGIDA
# ===============================


def get_player_game_logs(season: str, season_type: str = "Regular Season", show_progress: bool = True) -> pd.DataFrame:
    """
    Coleta o game log (box score por jogo) para todos os jogadores em uma temporada.
    Usa paginação baseada em data/sorter.
    """
    all_rows = []
    last_date = None
    page_size = 500
    page_num = 1
    max_pages = 100  # Limite de segurança para evitar loops infinitos

    if show_progress:
        print(f"  Iniciando coleta para {season}...")

    while page_num <= max_pages:
        params = {
            "LeagueID": "00",
            "Season": season,
            "SeasonType": season_type,
            "PlayerOrTeam": "P",
            "Counter": page_size,
            "Offset": 0,  # Mantém offset 0, usa DateFrom/DateTo para paginar
            "Direction": "DESC",
            "Sorter": "DATE",
        }

        # Se temos uma última data, usamos DateTo para pegar registros anteriores
        if last_date:
            params["DateTo"] = last_date

        if show_progress:
            if last_date:
                print(f"    Página {page_num}: buscando registros anteriores a {last_date}...", end=" ")
            else:
                print(f"    Página {page_num}: buscando registros mais recentes...", end=" ")

        try:
            response = requests.get(BASE_URL, headers=HEADERS, params={k: str(v) for k, v in params.items()}, timeout=30)
            response.raise_for_status()
            data = response.json()

            result_set = data["resultSets"][0]
            rows = result_set.get("rowSet", [])

            if not rows:
                if show_progress:
                    print("sem dados")
                break

            # Verifica se os registros são novos
            if show_progress:
                print(f"{len(rows)} registros encontrados")

            # Adiciona os registros
            all_rows.extend(rows)

            # Obtém a data mais antiga do lote atual
            # Assumindo que a data está na coluna 3 (índice pode variar)
            # Precisamos identificar a coluna de data corretamente
            date_column_index = None
            for i, header in enumerate(result_set["headers"]):
                if "GAME_DATE" in header or "DATE" in header:
                    date_column_index = i
                    break

            if date_column_index is not None and len(rows) > 0:
                # Pega a data mais antiga (último registro da lista)
                oldest_date = rows[-1][date_column_index]
                if oldest_date == last_date:
                    # Se a data não mudou, paramos para evitar loop
                    if show_progress:
                        print("    Data não mudou, encerrando coleta.")
                    break
                last_date = oldest_date
            else:
                # Se não encontrou coluna de data, usa o número de registros como critério
                if len(rows) < page_size:
                    if show_progress:
                        print(f"    Última página: {len(rows)} registros < {page_size}")
                    break

            page_num += 1

            # Se o número de registros for menor que o page_size, é a última página
            if len(rows) < page_size:
                if show_progress:
                    print(f"    Coleta concluída: última página com {len(rows)} registros")
                break

            time.sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"\n  ❌ Erro na página {page_num}: {e}")
            break

    if not all_rows:
        if show_progress:
            print(f"  ⚠️ Nenhum registro encontrado para {season}")
        return pd.DataFrame()

    # Cria DataFrame com os dados coletados
    df = pd.DataFrame(all_rows, columns=result_set["headers"])
    df["SEASON"] = season

    # Remove duplicatas baseadas em SEASON_ID e PLAYER_ID (ou outra combinação única)
    # Identifica colunas únicas
    unique_cols = []
    for col in ["GAME_ID", "PLAYER_ID", "SEASON_ID"]:
        if col in df.columns:
            unique_cols.append(col)

    if unique_cols:
        initial_count = len(df)
        df = df.drop_duplicates(subset=unique_cols)
        if show_progress and len(df) < initial_count:
            print(f"    Removidas {initial_count - len(df)} duplicatas")

    return df


# ===============================
# Função para verificar todas as temporadas
# ===============================


def check_all_seasons(seasons: List[str]) -> Dict[str, int]:
    """
    Verifica quantos registros existem em cada temporada.
    """
    print("=" * 60)
    print("VERIFICANDO VOLUME DE DADOS POR TEMPORADA")
    print("=" * 60)

    records_count = {}

    for season in seasons:
        print(f"\nVerificando temporada {season}...", end=" ")
        count = get_total_records_count(season)

        if count > 0:
            print(f"{count:,} registros encontrados")
            records_count[season] = count
        elif count == 0:
            print("0 registros encontrados")
            records_count[season] = 0
        else:
            print("ERRO - não foi possível verificar")
            records_count[season] = -1

    print("\n" + "=" * 60)
    print("RESUMO POR TEMPORADA:")
    print("-" * 60)

    total_estimated = 0
    for season, count in records_count.items():
        if count > 0:
            print(f"  {season}: {count:,} registros")
            total_estimated += count
        elif count == 0:
            print(f"  {season}: NENHUM registro")
        else:
            print(f"  {season}: ❌ Erro na verificação")

    print("-" * 60)
    print(f"  TOTAL ESTIMADO: {total_estimated:,} registros")
    print("=" * 60)

    return records_count


# ===============================
# Loop de múltiplas temporadas
# ===============================


def collect_multiple_seasons(seasons: List[str], check_first: bool = True) -> pd.DataFrame:
    """
    Coleta dados de múltiplas temporadas.
    """
    # Verificação prévia
    if check_first:
        check_all_seasons(seasons)

        print("\nDeseja prosseguir com a coleta? (s/n): ", end="")
        resposta = input().strip().lower()

        if resposta != "s":
            print("Coleta cancelada pelo usuário.")
            return pd.DataFrame()

    # Coleta efetiva
    print("\n" + "=" * 60)
    print("INICIANDO COLETA DE DADOS")
    print("=" * 60)

    all_dfs = []

    for i, season in enumerate(seasons, 1):
        print(f"\n[{i}/{len(seasons)}] Coletando temporada: {season}")

        try:
            df = get_player_game_logs(season, show_progress=True)

            if len(df) > 0:
                print(f"  ✅ Coletados {len(df):,} registros únicos para {season}")
                all_dfs.append(df)
            else:
                print(f"  ⚠️ Nenhum registro encontrado para {season}")

        except Exception as e:
            print(f"  ❌ Erro: {e}")

        if i < len(seasons):
            time.sleep(SLEEP_SECONDS)

    # Concatena todos os DataFrames
    if all_dfs:
        df_final = pd.concat(all_dfs, ignore_index=True)
        print("\n" + "=" * 60)
        print("✅ COLETA CONCLUÍDA!")
        print(f"Total de registros coletados: {len(df_final):,}")
        print("=" * 60)
        return df_final
    else:
        print("\n⚠️ Nenhum dado foi coletado.")
        return pd.DataFrame()


# ===============================
# Execução
# ===============================

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    seasons = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

    # Opção 1: Apenas verificar
    # Opção 2: Verificar e coletar
    # Opção 3: Coletar diretamente

    print("Opção 1: Verificar dados disponíveis")
    print("Opção 2: Verificar e coletar")
    print("Opção 3: Coletar diretamente (sem verificação)")

    opcao = input("\nEscolha uma opção (1/2/3): ").strip()

    if opcao == "1":
        # Apenas verifica
        check_all_seasons(seasons)

    elif opcao == "2":
        # Verifica e coleta
        df_all = collect_multiple_seasons(seasons, check_first=True)
        if len(df_all) > 0:
            filename = "../NBA/data/nba_player_boxscores_multi_season.csv"
            df_all.to_csv(filename, index=False)
            print(f"\n✅ Arquivo salvo em: {filename}")
            print("📊 Primeiras 5 linhas:")
            print(df_all.head())

    elif opcao == "3":
        # Coleta direta
        df_all = collect_multiple_seasons(seasons, check_first=False)
        if len(df_all) > 0:
            filename = "../NBA/data/nba_player_boxscores_multi_season.csv"
            df_all.to_csv(filename, index=False)
            print(f"\n✅ Arquivo salvo em: {filename}")
    else:
        print("Opção inválida!")
