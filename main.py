import requests
import pandas as pd
import time
from typing import List

# ===============================
# Configurações globais
# ===============================

BASE_URL = "https://stats.nba.com/stats/leaguedashplayerstats"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Connection": "keep-alive"
}

SLEEP_SECONDS = 1.2   # importante para evitar bloqueio


# ===============================
# Função principal de coleta
# ===============================

def get_player_stats_by_season(
    season: str,
    season_type: str = "Regular Season",
    per_mode: str = "PerGame",
    measure_type: str = "Base"
) -> pd.DataFrame:
    """
    Coleta TODAS as estatísticas por jogador para uma temporada.
    """

    params = {
        "LeagueID": "00",
        "Season": season,
        "SeasonType": season_type,
        "PerMode": per_mode,
        "MeasureType": measure_type,
        "PlusMinus": "N",
        "PaceAdjust": "N",
        "Rank": "N",
        "Outcome": "",
        "Location": "",
        "Month": "0",
        "SeasonSegment": "",
        "DateFrom": "",
        "DateTo": "",
        "OpponentTeamID": "0",
        "VsConference": "",
        "VsDivision": "",
        "GameSegment": "",
        "Period": "0",
        "LastNGames": "0"
    }

    response = requests.get(
        BASE_URL,
        headers=HEADERS,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    json_data = response.json()

    result = json_data["resultSets"][0]
    df = pd.DataFrame(result["rowSet"], columns=result["headers"])

    df["SEASON"] = season

    if "PLAYER_ID" in df.columns:
        df["PLAYER_URL"] = df["PLAYER_ID"].apply(
            lambda x: f"https://www.nba.com/player/{x}"
        )

    return df


# ===============================
# Loop de múltiplas temporadas
# ===============================

def collect_multiple_seasons(
    seasons: List[str]
) -> pd.DataFrame:
    all_dfs = []

    for season in seasons:
        print(f"Coletando temporada: {season}")
        df = get_player_stats_by_season(season)
        all_dfs.append(df)
        time.sleep(SLEEP_SECONDS)

    return pd.concat(all_dfs, ignore_index=True)


# ===============================
# Execução
# ===============================

if __name__ == "__main__":

    seasons = [
        "2019-20",
        "2020-21",
        "2021-22",
        "2022-23",
        "2023-24"
    ]

    df_all = collect_multiple_seasons(seasons)

    print(df_all.head())
    print(f"\nTotal de registros: {len(df_all)}")

    df_all.to_csv("nba_player_stats_multi_season.csv", index=False)
    print("\nArquivo salvo: nba_player_stats_multi_season.csv")
