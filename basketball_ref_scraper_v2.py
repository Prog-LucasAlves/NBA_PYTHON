"""
Adicionar suporte a Scrapy com retry inteligente para Basketball-Reference.
Melhora robustez do scraper original.
"""

import time
import warnings

import pandas as pd
import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

warnings.filterwarnings("ignore")


class BasketballRefScraperV2:
    """
    Scraper melhorado de Basketball-Reference.com com retry inteligente.

    Técnicas de mitigação de 403:
    1. Múltiplos User-Agents
    2. Delays entre requisições
    3. Session persistente
    4. Retry automático
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
    ]

    BASE_URL = "https://www.basketball-reference.com"

    def __init__(self) -> None:
        """Inicializa scraper com session persistente."""
        self.session = requests.Session()
        self.current_ua_index = 0
        self._rotate_user_agent()

    def _rotate_user_agent(self) -> None:
        """Rotaciona User-Agent a cada requisição."""
        ua = self.USER_AGENTS[self.current_ua_index % len(self.USER_AGENTS)]
        self.session.headers.update(
            {
                "User-Agent": ua,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        self.current_ua_index += 1

    def scrape_with_retry(
        self,
        season: int = 2025,
        max_retries: int = 3,
        delay: float = 2.0,
    ) -> pd.DataFrame:
        """
        Scrapa com retry automático e delay.

        Args:
            season: Ano da temporada
            max_retries: Número de tentativas
            delay: Delay entre tentativas (segundos)

        Returns:
            DataFrame com dados ou vazio se falhar
        """
        print("\n🏀 Coletando dados de Basketball-Reference.com...")
        print(f"   Temporada: {season}-{season + 1}")
        print(f"   Tentativas: {max_retries} | Delay: {delay}s")

        for attempt in range(max_retries):
            try:
                self._rotate_user_agent()
                url = f"{self.BASE_URL}/leagues/NBA_{season}_per_game.html"

                print(f"\n   Tentativa {attempt + 1}/{max_retries}...")
                print(f"   📡 Requisitando com User-Agent #{self.current_ua_index}")

                response = self.session.get(url, timeout=10)
                response.raise_for_status()

                df = self._parse_player_stats(response.text)

                if not df.empty:
                    print(f"   ✅ Sucesso! {len(df)} jogadores")
                    return df

                # Se parse retornar vazio, tenta novamente
                if attempt < max_retries - 1:
                    print(f"   ⏳ Esperando {delay}s antes de nova tentativa...")
                    time.sleep(delay)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print("   ⚠️  403 Forbidden - Site está bloqueando")
                    if attempt < max_retries - 1:
                        print(f"   ⏳ Esperando {delay}s antes de nova tentativa...")
                        time.sleep(delay)
                else:
                    print(f"   ❌ HTTP {e.response.status_code}: {str(e)}")
                    break

            except requests.exceptions.RequestException as e:
                print(f"   ⚠️  Erro de conexão: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"   ⏳ Esperando {delay}s antes de nova tentativa...")
                    time.sleep(delay)

            except Exception as e:
                print(f"   ❌ Erro inesperado: {str(e)}")
                break

        print(f"\n❌ Falhou após {max_retries} tentativas")
        return pd.DataFrame()

    def _parse_player_stats(self, html: str) -> pd.DataFrame:
        """
        Extrai dados de jogadores do HTML.

        Args:
            html: Conteúdo HTML da página

        Returns:
            DataFrame com dados
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", {"id": "per_game_stats"})

            if not table:
                print("   ⚠️  Tabela não encontrada no HTML")
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
                print("   ⚠️  Corpo da tabela não encontrado")
                return pd.DataFrame()

            for tr in tbody.find_all("tr"):  # type: ignore
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

            print("   ⚠️  Nenhum registro encontrado")
            return pd.DataFrame()

        except Exception as e:
            print(f"   ❌ Erro ao fazer parse: {str(e)}")
            return pd.DataFrame()

    def save_to_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """Salva dados em CSV."""
        try:
            df.to_csv(filename, index=False)
            print(f"\n✅ Dados salvos em: {filename}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar: {str(e)}")
            return False


def main() -> None:
    """Exemplo de uso com retry."""
    scraper = BasketballRefScraperV2()

    # Tentar com retry e delay
    df = scraper.scrape_with_retry(season=2024, max_retries=3, delay=2.0)

    if not df.empty:
        scraper.save_to_csv(df, "nba_stats_retry.csv")
        print(f"\n✅ Sucesso! {len(df)} registros coletados")
    else:
        print("\n⚠️  Não foi possível coletar dados")
        print("   Dica: Use unified_nba_scraper.py para fallback automático")


if __name__ == "__main__":
    main()
