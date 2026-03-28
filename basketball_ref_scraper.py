"""
NBA Game Statistics Scraper - Basketball-Reference.com

Coleta dados de performance de jogadores da NBA de Basketball-Reference.com,
uma das fontes mais confiáveis e completas para estatísticas históricas.

Exemplo de uso:
    scraper = BasketballRefScraper()
    df = scraper.scrape_2025_season()
    scraper.save_to_csv(df, "nba_stats_2025.csv")
"""

import warnings
from typing import Optional

import pandas as pd
import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

warnings.filterwarnings("ignore")


class BasketballRefScraper:
    """
    Scraper de dados do Basketball-Reference.com.

    Coleta estatísticas detalhadas de jogadores da temporada em andamento.
    """

    BASE_URL = "https://www.basketball-reference.com"
    HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")}

    def __init__(self) -> None:
        """Inicializa o scraper."""
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.data: list = []

    def scrape_2025_season(self, max_players: Optional[int] = None) -> pd.DataFrame:
        """
        Scrapa dados da temporada 2025-2026.

        Args:
            max_players: Limite de jogadores a coletar

        Returns:
            DataFrame com dados de jogadores
        """
        print("\n🏀 Coletando dados de Basketball-Reference.com...")
        print("   Temporada: 2025-2026")

        try:
            # URL para 2024-2025 season (mais recente com dados completos)
            url = f"{self.BASE_URL}/leagues/NBA_2025_per_game.html"

            print(f"\n📡 Requisitando: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            df = self._parse_player_stats(response.text, max_players)

            if df.empty:
                print("⚠️  Tentando página alternativa...")
                # Fallback: tentar página de totals
                url_alt = f"{self.BASE_URL}/leagues/NBA_2024_per_game.html"
                response = self.session.get(url_alt, timeout=10)
                response.raise_for_status()
                df = self._parse_player_stats(response.text, max_players)

            if not df.empty:
                print(f"✅ {len(df)} jogadores coletados com sucesso!")
                return df

            return pd.DataFrame()

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ Erro ao processar: {str(e)}")
            return pd.DataFrame()

    def _parse_player_stats(self, html: str, max_players: Optional[int]) -> pd.DataFrame:
        """
        Extrai dados de jogadores do HTML.

        Args:
            html: Conteúdo HTML da página
            max_players: Limite de jogadores

        Returns:
            DataFrame com dados de jogadores
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Encontrar tabela de stats
            table = soup.find("table", {"id": "per_game_stats"})

            if not table:
                print("⚠️  Tabela não encontrada")
                return pd.DataFrame()

            # Extrair headers
            headers = []
            thead = table.find("thead")  # type: ignore
            if thead:
                for th in thead.find_all("th"):  # type: ignore
                    headers.append(th.get_text().strip())

            # Extrair dados
            rows_data = []
            tbody = table.find("tbody")  # type: ignore

            if not tbody:
                return pd.DataFrame()

            for i, tr in enumerate(tbody.find_all("tr")):  # type: ignore
                if max_players and i >= max_players:
                    break

                # Pular linhas de separação
                if tr.get("class") and "thead" in tr.get("class"):
                    continue

                cells = tr.find_all("td")
                if not cells:
                    continue

                row = {}
                for j, cell in enumerate(cells):
                    if j < len(headers):
                        row[headers[j]] = cell.get_text().strip()

                if row:
                    rows_data.append(row)

            if rows_data:
                df = pd.DataFrame(rows_data)
                print(f"   ✓ {len(df)} registros extraídos")
                return df

            return pd.DataFrame()

        except Exception as e:
            print(f"⚠️  Erro ao fazer parse: {str(e)}")
            return pd.DataFrame()

    def scrape_all_seasons(self, start_year: int = 2020, end_year: int = 2025) -> pd.DataFrame:
        """
        Scrapa dados de múltiplas temporadas.

        Args:
            start_year: Ano inicial
            end_year: Ano final

        Returns:
            DataFrame consolidado com dados de todas as temporadas
        """
        print(f"\n🏀 Coletando dados de {start_year}-{end_year}...")

        all_data = []

        for year in range(start_year, end_year + 1):
            print(f"\n  📥 Temporada {year}-{year + 1}...")
            url = f"{self.BASE_URL}/leagues/NBA_{year}_per_game.html"

            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()

                df = self._parse_player_stats(response.text, None)

                if not df.empty:
                    df["Season"] = f"{year}-{year + 1}"
                    all_data.append(df)
                    print(f"    ✓ {len(df)} jogadores")

            except Exception as e:
                print(f"    ⚠️  Erro: {str(e)}")
                continue

        if all_data:
            consolidated = pd.concat(all_data, ignore_index=True)
            print(f"\n✅ Total: {len(consolidated)} registros consolidados")
            return consolidated

        return pd.DataFrame()

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
            print(f"\n✅ Dados salvos em: {filename}")
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

        if "Season" in df.columns:
            print(f"  Temporadas: {sorted(df['Season'].unique())}")

        if "Player" in df.columns:
            print(f"  Jogadores únicos: {df['Player'].nunique()}")

        if "Tm" in df.columns:
            print(f"  Times: {df['Tm'].nunique()}")

        print("\n📊 Colunas disponíveis:")
        cols = list(df.columns)
        for i in range(0, len(cols), 5):
            print(f"  {', '.join(cols[i : i + 5])}")

        print("\n✅ Status: Dados prontos para processamento")
        print("=" * 70)


def main() -> None:
    """Exemplo de uso do scraper."""
    scraper = BasketballRefScraper()

    # Opção 1: Coletar temporada atual
    print("\n🔍 Opção 1: Temporada Atual")
    df_current = scraper.scrape_2025_season(max_players=50)

    if not df_current.empty:
        scraper.save_to_csv(df_current, "nba_stats_2025_current.csv")
        scraper.generate_report(df_current)

    # Opção 2: Coletar múltiplas temporadas
    print("\n" + "=" * 70)
    print("\n🔍 Opção 2: Histórico (2020-2025)")
    df_history = scraper.scrape_all_seasons(start_year=2020, end_year=2024)

    if not df_history.empty:
        scraper.save_to_csv(df_history, "nba_stats_history.csv")
        scraper.generate_report(df_history)

    print("\n✅ Coleta concluída!")


if __name__ == "__main__":
    main()
