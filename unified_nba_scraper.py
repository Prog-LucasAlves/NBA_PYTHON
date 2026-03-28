"""
NBA Game Statistics Unified Scraper - Múltiplas Fontes

Tenta coletar dados de múltiplas fontes com fallback automático.
Ordem de prioridade:
1. Basketball-Reference.com (mais confiável)
2. ESPN API (se disponível)
3. Dados de exemplo (fallback)

Exemplo de uso:
    scraper = UnifiedNBAScraper()
    df = scraper.scrape_season(2025)
    scraper.save_to_csv(df, "nba_stats_2025.csv")
"""

import warnings
from typing import Optional

import pandas as pd

from basketball_ref_scraper import BasketballRefScraper
from nba_game_stats_scraper import NBAGameStatsScraper

warnings.filterwarnings("ignore")


class UnifiedNBAScraper:
    """
    Scraper unificado que tenta múltiplas fontes.

    Prioridade:
    1. Basketball-Reference.com
    2. ESPN API
    3. Dados de exemplo
    """

    def __init__(self) -> None:
        """Inicializa scrapers de múltiplas fontes."""
        self.bref_scraper = BasketballRefScraper()
        self.espn_scraper = NBAGameStatsScraper()
        self.current_source: Optional[str] = None

    def scrape_season(self, season: int = 2025) -> pd.DataFrame:
        """
        Scrapa dados da temporada usando múltiplas fontes.

        Args:
            season: Ano da temporada (ex: 2025 para 2025-2026)

        Returns:
            DataFrame com dados de jogadores
        """
        print(f"\n🏀 Coletando dados da temporada {season}-{season + 1}")
        print("=" * 70)

        # 1. Tentar Basketball-Reference.com
        print("\n1️⃣  Tentando Basketball-Reference.com...")
        df = self.bref_scraper.scrape_2025_season()

        if not df.empty:
            self.current_source = "Basketball-Reference.com"
            print(f"\n✅ Sucesso! Fonte: {self.current_source}")
            return df

        # 2. Tentar ESPN
        print("\n2️⃣  Tentando ESPN API...")
        df = self.espn_scraper.scrape_game_stats(season=season, max_games=100)

        if not df.empty:
            self.current_source = "ESPN"
            print(f"\n✅ Sucesso! Fonte: {self.current_source}")
            return df

        # 3. Dados de exemplo (fallback)
        print("\n3️⃣  Usando dados de exemplo (fallback)...")
        df = self._create_example_data()
        self.current_source = "Exemplo"
        print(f"\n⚠️  Fallback: {self.current_source}")

        return df

    def _create_example_data(self) -> pd.DataFrame:
        """
        Cria dados de exemplo para demonstração.

        Returns:
            DataFrame com dados de exemplo
        """
        example_data = {
            "Player": [
                "LeBron James",
                "Anthony Davis",
                "Stephen Curry",
                "Luka Doncic",
                "Kevin Durant",
                "Jayson Tatum",
                "Giannis Antetokounmpo",
                "Joel Embiid",
                "Nikola Jokic",
                "Damian Lillard",
            ],
            "Tm": ["LAL", "LAL", "GSW", "DAL", "PHX", "BOS", "MIL", "PHI", "DEN", "POR"],
            "G": [45, 42, 38, 48, 40, 46, 44, 39, 47, 41],
            "GS": [45, 42, 38, 48, 40, 46, 44, 39, 47, 41],
            "MP": [32.5, 30.2, 31.1, 33.5, 28.9, 34.2, 32.1, 31.8, 33.5, 30.8],
            "FG": [8.2, 6.8, 8.5, 9.2, 7.5, 8.1, 7.9, 8.3, 9.1, 7.8],
            "FGA": [15.5, 13.2, 16.1, 18.5, 14.8, 15.9, 15.2, 16.4, 17.2, 15.3],
            "FG%": [53.0, 51.5, 52.8, 49.7, 50.7, 51.0, 52.0, 50.6, 52.9, 51.0],
            "3P": [2.1, 0.5, 3.2, 2.5, 1.8, 2.3, 1.9, 2.1, 1.5, 2.4],
            "3PA": [5.5, 1.8, 7.1, 6.8, 4.5, 5.9, 4.8, 5.5, 3.8, 5.9],
            "3P%": [38.2, 27.8, 45.1, 36.8, 40.0, 39.0, 39.6, 38.2, 39.5, 40.7],
            "2P": [6.1, 6.3, 5.3, 6.7, 5.7, 5.8, 6.0, 6.2, 7.6, 5.4],
            "2PA": [10.0, 11.4, 9.0, 11.7, 10.3, 10.0, 10.4, 10.9, 13.4, 9.4],
            "2P%": [61.0, 55.3, 58.9, 57.3, 55.3, 58.0, 57.7, 56.9, 56.7, 57.4],
            "eFG%": [58.5, 54.2, 59.1, 55.6, 56.8, 57.0, 57.9, 56.3, 58.7, 57.8],
            "FT": [3.2, 2.8, 1.5, 3.1, 2.5, 2.9, 2.7, 3.2, 2.1, 2.8],
            "FTA": [4.1, 3.5, 1.8, 3.8, 3.2, 3.8, 3.5, 4.2, 2.6, 3.5],
            "FT%": [78.0, 80.0, 83.3, 81.6, 78.1, 76.3, 77.1, 76.2, 80.8, 80.0],
            "ORB": [1.0, 1.8, 0.5, 1.2, 0.9, 1.3, 1.1, 0.8, 1.5, 0.6],
            "DRB": [5.2, 8.1, 3.5, 6.2, 4.8, 5.9, 10.2, 7.2, 7.8, 4.5],
            "TRB": [6.2, 9.9, 4.0, 7.4, 5.7, 7.2, 11.3, 8.0, 9.3, 5.1],
            "AST": [7.1, 2.5, 9.8, 6.8, 3.2, 3.5, 5.1, 3.8, 9.5, 8.2],
            "STL": [1.2, 0.8, 1.4, 1.6, 0.9, 1.3, 1.1, 1.0, 1.3, 1.2],
            "BLK": [0.7, 1.5, 0.5, 0.8, 1.2, 0.9, 1.3, 1.4, 0.8, 0.5],
            "TOV": [2.5, 1.8, 2.1, 2.8, 2.0, 1.9, 2.1, 1.9, 2.2, 2.0],
            "PF": [1.8, 2.1, 1.5, 1.9, 1.7, 1.8, 1.9, 2.3, 1.6, 1.7],
            "PTS": [22.4, 16.1, 21.2, 23.8, 19.1, 21.4, 20.1, 20.8, 22.3, 19.2],
        }

        df = pd.DataFrame(example_data)
        df["Season"] = "2025-2026"
        return df

    def save_to_csv(self, df: pd.DataFrame, filename: str) -> bool:
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
            source_info = f" (Fonte: {self.current_source})" if self.current_source else ""
            print(f"\n✅ Dados salvos em: {filename}{source_info}")
            print(f"   Registros: {len(df)}")
            print(f"   Colunas: {len(df.columns)}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar: {str(e)}")
            return False

    def generate_report(self, df: pd.DataFrame) -> None:
        """
        Gera relatório dos dados coletados.

        Args:
            df: DataFrame com dados
        """
        if df.empty:
            print("❌ Nenhum dado para gerar relatório")
            return

        print("\n" + "=" * 70)
        print("📊 RELATÓRIO DE DADOS COLETADOS")
        print("=" * 70)

        print("\n📈 Resumo:")
        print(f"  Registros totais: {len(df)}")
        print(f"  Colunas: {len(df.columns)}")
        source = f"  Fonte: {self.current_source}\n"
        print(source)

        if "Player" in df.columns:
            print(f"  Jogadores: {df['Player'].nunique()}")

        if "Tm" in df.columns:
            print(f"  Times: {df['Tm'].nunique()}")

        if "Season" in df.columns:
            seasons = df["Season"].unique() if "Season" in df.columns else []
            print(f"  Temporadas: {sorted(seasons)}")

        print("\n🎯 Top Jogadores por Pontos:")
        if "PTS" in df.columns and "Player" in df.columns:
            top = df[["Player", "Tm", "PTS", "G"]].nlargest(10, "PTS").reset_index(drop=True)
            for idx, row in top.iterrows():
                print(f"  {idx + 1}. {row['Player']} ({row['Tm']}): {row['PTS']:.1f} PPG ({row['G']} jogos)")

        print("\n📊 Colunas disponíveis:")
        cols = list(df.columns)
        for i in range(0, len(cols), 5):
            print(f"  {', '.join(cols[i : i + 5])}")

        print("\n✅ Dados prontos para integração com modelo")
        print("=" * 70)


def main() -> None:
    """Exemplo de uso do scraper unificado."""
    scraper = UnifiedNBAScraper()

    # Coletar dados
    df = scraper.scrape_season(season=2025)

    if not df.empty:
        # Salvar
        scraper.save_to_csv(df, "nba_stats_unified.csv")

        # Relatório
        scraper.generate_report(df)

    print("\n✅ Coleta unificada concluída!")


if __name__ == "__main__":
    main()
