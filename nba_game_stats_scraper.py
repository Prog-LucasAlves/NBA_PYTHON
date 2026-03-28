"""
NBA Game Statistics Scraper - Coleta dados de jogadores por partida

Coleta dados de performance de jogadores da NBA do ESPN, organizando
por partida com estatísticas detalhadas. Útil para análise histórica
e treinamento de modelos.

Exemplo de uso:
    scraper = NBAGameStatsScraper()
    df = scraper.scrape_game_stats(season=2024, max_games=100)
    scraper.save_to_csv(df, "nba_game_stats_2024.csv")
"""

import warnings
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests  # type: ignore

warnings.filterwarnings("ignore")


class NBAGameStatsScraper:
    """
    Scraper de dados de jogadores por partida do ESPN.

    Coleta statistics detalhadas de cada jogador em cada partida,
    incluindo pontos, rebotes, assistências, etc.
    """

    BASE_URL = "https://www.espn.com/nba"
    HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")}

    # Mapeamento de estatísticas do ESPN
    STATS_MAP = {
        "FG": "FG",  # Field Goals
        "FGA": "FGA",  # Field Goals Attempted
        "3PT": "3PT",  # 3-Pointers
        "3PA": "3PA",  # 3-Pointers Attempted
        "FT": "FT",  # Free Throws
        "FTA": "FTA",  # Free Throws Attempted
        "OFF": "OREB",  # Offensive Rebounds
        "DEF": "DREB",  # Defensive Rebounds
        "REB": "REB",  # Total Rebounds
        "AST": "AST",  # Assists
        "TO": "TOV",  # Turnovers
        "STL": "STL",  # Steals
        "BLK": "BLK",  # Blocks
        "PF": "PF",  # Personal Fouls
        "PTS": "PTS",  # Points
    }

    def __init__(self) -> None:
        """Inicializa o scraper."""
        self.games_data: list = []
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def scrape_game_stats(
        self,
        season: int = 2025,
        max_games: Optional[int] = None,
        verbose: bool = True,
    ) -> pd.DataFrame:
        """
        Scrapa estatísticas de jogadores por partida.

        Args:
            season: Ano da temporada (ex: 2024 para 2023-2024)
            max_games: Limite de partidas a coletar (None = todas)
            verbose: Exibir progresso

        Returns:
            DataFrame com dados de jogadores por partida
        """
        if verbose:
            print(f"\n🏀 Coletando dados da temporada {season}-{season + 1}...")

        try:
            # Usar API do ESPN para obter dados
            game_stats_df = self._scrape_espn_game_stats(season, max_games, verbose)

            if game_stats_df is None or game_stats_df.empty:
                return self._get_fallback_data(season)

            return game_stats_df

        except Exception as e:
            print(f"❌ Erro ao fazer scrape: {str(e)}")
            return self._get_fallback_data(season)

    def _scrape_espn_game_stats(
        self,
        season: int,
        max_games: Optional[int],
        verbose: bool,
    ) -> Optional[pd.DataFrame]:
        """
        Scrapa dados do ESPN usando a API interna.

        Args:
            season: Ano da temporada
            max_games: Limite de partidas
            verbose: Exibir progresso

        Returns:
            DataFrame ou None se falhar
        """
        try:
            # ESPN API para stats de jogadores por temporada
            url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/statistics"

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extrair dados de partidas
            games_list = []

            if "events" in data:
                for event in data.get("events", [])[: max_games or 999]:
                    game_info = self._parse_game_data(event, season)
                    if game_info:
                        games_list.extend(game_info)
                        if verbose and len(games_list) % 50 == 0:
                            print(f"  ✓ {len(games_list)} linhas coletadas...")

            if games_list:
                df = pd.DataFrame(games_list)
                if verbose:
                    print(f"✅ {len(df)} registros coletados com sucesso!")
                return df

            return None

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erro na requisição: {str(e)}")
            return None
        except Exception as e:
            print(f"⚠️ Erro ao processar dados: {str(e)}")
            return None

    def _parse_game_data(self, event: dict, season: int) -> list:  # type: ignore
        """
        Extrai dados de uma partida.

        Args:
            event: Dados da partida do ESPN
            season: Temporada

        Returns:
            Lista de dicionários com dados de cada jogador
        """
        try:
            game_records = []

            # Extrair informações gerais da partida
            game_id = event.get("id")
            game_date = event.get("date", "")
            home_team = event.get("competitions", [{}])[0].get("home", {}).get("team", {}).get("abbreviation", "")
            away_team = event.get("competitions", [{}])[0].get("away", {}).get("team", {}).get("abbreviation", "")

            # Extrair stats de cada time
            competitions = event.get("competitions", [])
            if competitions:
                comp = competitions[0]

                # Home team
                home_competitors = comp.get("home", {}).get("competitors", [])
                for competitor in home_competitors:
                    player_name = competitor.get("athlete", {}).get("displayName", "")
                    stats = competitor.get("stats", {})

                    if player_name and stats:
                        record = {
                            "game_id": game_id,
                            "game_date": game_date,
                            "season": season,
                            "player_name": player_name,
                            "team": home_team,
                            "opponent": away_team,
                            "home_away": "Home",
                        }

                        # Adicionar estatísticas
                        for stat_key, stat_name in self.STATS_MAP.items():
                            record[stat_name] = stats.get(stat_key, 0)

                        game_records.append(record)

                # Away team
                away_competitors = comp.get("away", {}).get("competitors", [])
                for competitor in away_competitors:
                    player_name = competitor.get("athlete", {}).get("displayName", "")
                    stats = competitor.get("stats", {})

                    if player_name and stats:
                        record = {
                            "game_id": game_id,
                            "game_date": game_date,
                            "season": season,
                            "player_name": player_name,
                            "team": away_team,
                            "opponent": home_team,
                            "home_away": "Away",
                        }

                        # Adicionar estatísticas
                        for stat_key, stat_name in self.STATS_MAP.items():
                            record[stat_name] = stats.get(stat_key, 0)

                        game_records.append(record)

            return game_records

        except Exception:
            return []

    def _get_fallback_data(self, season: int) -> pd.DataFrame:
        """
        Retorna dados de fallback (template vazio para estrutura).

        Args:
            season: Temporada

        Returns:
            DataFrame com estrutura correta mas sem dados
        """
        columns = [
            "game_id",
            "game_date",
            "season",
            "player_name",
            "team",
            "opponent",
            "home_away",
        ] + list(self.STATS_MAP.values())

        df = pd.DataFrame(columns=columns)
        print(f"⚠️ Sem dados para {season}. Retornando estrutura vazia.\n💡 Dica: Verifique sua conexão ou tente uma temporada mais recente.")
        return df

    def scrape_recent_games(self, days: int = 7) -> pd.DataFrame:
        """
        Scrapa partidas recentes (últimos N dias).

        Args:
            days: Número de dias para retroceder

        Returns:
            DataFrame com dados de partidas recentes
        """
        print(f"\n🏀 Coletando partidas dos últimos {days} dias...")

        try:
            url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/statistics"

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            games_list = []

            cutoff_date = datetime.now() - timedelta(days=days)

            for event in data.get("events", []):
                try:
                    game_date = datetime.fromisoformat(event.get("date", "").replace("Z", "+00:00"))
                    if game_date >= cutoff_date:
                        game_info = self._parse_game_data(event, 2024)
                        games_list.extend(game_info)
                except (ValueError, TypeError):
                    continue

            if games_list:
                df = pd.DataFrame(games_list)
                print(f"✅ {len(df)} registros dos últimos {days} dias!")
                return df

            return pd.DataFrame()

        except Exception as e:
            print(f"❌ Erro: {str(e)}")
            return pd.DataFrame()

    def save_to_csv(
        self,
        df: pd.DataFrame,
        filename: str = "nba_game_stats.csv",
    ) -> bool:
        """
        Salva dados em CSV.

        Args:
            df: DataFrame a salvar
            filename: Nome do arquivo

        Returns:
            True se salvo com sucesso
        """
        try:
            df.to_csv(filename, index=False)
            print(f"✅ Dados salvos em: {filename}")
            print(f"   Total: {len(df)} registros")
            print(f"   Colunas: {', '.join(df.columns)}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar: {str(e)}")
            return False

    def get_player_season_stats(
        self,
        player_name: str,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Retorna estatísticas agregadas de um jogador na temporada.

        Args:
            player_name: Nome do jogador
            df: DataFrame com dados

        Returns:
            DataFrame com stats agregadas
        """
        player_games = df[df["player_name"].str.contains(player_name, case=False, na=False)]

        if player_games.empty:
            return pd.DataFrame()

        # Colunas numéricas para agregação
        numeric_cols = [
            col
            for col in player_games.columns
            if col
            not in [
                "game_id",
                "game_date",
                "season",
                "player_name",
                "team",
                "opponent",
                "home_away",
            ]
        ]

        stats = player_games[numeric_cols].agg(["mean", "std", "min", "max"])
        stats["games_played"] = len(player_games)

        return stats

    def generate_report(self, df: pd.DataFrame) -> None:
        """
        Gera relatório dos dados coletados.

        Args:
            df: DataFrame com dados
        """
        if df.empty:
            print("❌ Nenhum dado para gerar relatório")
            return

        print("\n" + "=" * 60)
        print("📊 RELATÓRIO DE DADOS COLETADOS")
        print("=" * 60)

        print("\n📈 Resumo:")
        print(f"  Partidas únicas: {df['game_id'].nunique()}")
        print(f"  Registros totais: {len(df)}")
        print(f"  Jogadores únicos: {df['player_name'].nunique()}")
        print(f"  Temporadas: {', '.join(map(str, sorted(df['season'].unique())))}")

        print("\n📅 Período:")
        print(f"  Data mínima: {df['game_date'].min()}")
        print(f"  Data máxima: {df['game_date'].max()}")

        print("\n🏀 Times representados:")
        teams = sorted(df["team"].unique())
        for i in range(0, len(teams), 5):
            print(f"  {', '.join(teams[i : i + 5])}")

        print("\n🎯 Top 10 jogadores por partidas:")
        top_players = df["player_name"].value_counts().head(10)
        for player, count in top_players.items():
            print(f"  {player}: {count} partidas")

        print("\n📊 Estatísticas disponíveis:")
        stat_cols = [
            col
            for col in df.columns
            if col
            not in [
                "game_id",
                "game_date",
                "season",
                "player_name",
                "team",
                "opponent",
                "home_away",
            ]
        ]
        for i in range(0, len(stat_cols), 5):
            print(f"  {', '.join(stat_cols[i : i + 5])}")

        print("\n" + "=" * 60)


def main() -> None:
    """Exemplo de uso do scraper."""
    scraper = NBAGameStatsScraper()

    # Coletar dados da temporada 2025-2026 (atual)
    df = scraper.scrape_game_stats(season=2025, max_games=100)

    if not df.empty:
        # Salvar em CSV
        scraper.save_to_csv(df, "nba_game_stats_2025.csv")

        # Gerar relatório
        scraper.generate_report(df)

        # Exemplo: Stats de um jogador
        print("\n🔍 Exemplo - Stats de Luka Doncic:")
        luka_stats = scraper.get_player_season_stats("Luka", df)
        if not luka_stats.empty:
            print(luka_stats)


if __name__ == "__main__":
    main()
