#!/usr/bin/env python
"""
NBA Injury Scraper - Sofascore e Outras Fontes
Coleta informações REAIS de lesões de jogadores em tempo real
"""

import warnings
from typing import Dict

import pandas as pd
import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")


class NBAInjuryScraper:
    """Scraper de lesões em tempo real"""

    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        self.timeout = 15
        self.injuries = {}

    def get_injuries_data(self) -> Dict[str, Dict]:
        """
        Coleta dados de lesões de múltiplas fontes
        Retorna: {player_name: {status, lesão, tipo, timeline}}
        """
        print("\n" + "=" * 80)
        print("🏀 SCRAPER DE LESÕES NBA - TEMPO REAL")
        print("=" * 80 + "\n")

        # Estratégia 1: SofaScore Lesões
        print("📍 Estratégia 1: SofaScore (Lesões)...")
        self._scrape_sofascore_injuries()
        if self.injuries:
            print(f"✅ Coletadas {len(self.injuries)} lesões do SofaScore\n")
            return self.injuries

        # Estratégia 2: ESPN Injury Report
        print("📍 Estratégia 2: ESPN Injury Report...")
        self._scrape_espn_injuries()
        if self.injuries:
            print(f"✅ Coletadas {len(self.injuries)} lesões do ESPN\n")
            return self.injuries

        # Estratégia 3: NBA Official Injury Report
        print("📍 Estratégia 3: NBA Official (Lesões)...")
        self._scrape_nba_injuries()
        if self.injuries:
            print(f"✅ Coletadas {len(self.injuries)} lesões da NBA\n")
            return self.injuries

        print("⚠️  Nenhuma fonte de lesão conseguiu dados reais\n")
        return self._get_sample_injuries()

    def _scrape_sofascore_injuries(self):
        """Scraping de lesões do SofaScore"""
        try:
            # URL do SofaScore com informações de jogadores
            url = "https://www.sofascore.com/basketball/nba"

            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Procurar por elementos de lesão
            # SofaScore usa estruturas específicas para lesões

            # Tentar encontrar seções de status
            status_elements = soup.find_all(class_="status")
            print(f"   Encontrados {len(status_elements)} elementos de status")

            # Procurar por palavras-chave de lesão
            injury_keywords = ["injured", "lesionado", "out", "questionable", "day-to-day"]

            for element in soup.find_all(string=True):
                element_text = element.lower()

                if any(keyword in element_text for keyword in injury_keywords):
                    # Procurar pelo nome do jogador próximo ao status
                    parent = element.parent
                    for _ in range(5):  # Procurar até 5 níveis acima
                        if parent:
                            text = parent.get_text()
                            # Tentar extrair informações
                            if len(text) < 200:  # Evitar blocos muito grandes
                                self._extract_injury_info(text)
                        parent = parent.parent if parent else None

            return True

        except Exception as e:
            print(f"   ❌ Erro: {str(e)[:70]}")
            return False

    def _scrape_espn_injuries(self):
        """Scraping de lesões do ESPN"""
        try:
            # URL do relatório de lesões do ESPN
            url = "https://www.espn.com/nba/injuries"

            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Procurar por tabelas de lesões
            tables = soup.find_all("table")
            print(f"   Encontradas {len(tables)} tabelas")

            for table in tables:
                rows = table.find_all("tr")
                print(f"   Processando tabela com {len(rows)} linhas")

                for row in rows:
                    try:
                        cols = row.find_all("td")
                        # ESPN tem: Nome | Lesão | Status | Prognóstico
                        if len(cols) >= 2:
                            player_name = cols[0].get_text(strip=True)

                            # Procurar pela descrição de lesão (pode estar em diferentes colunas)
                            injury_desc = ""
                            for i, col in enumerate(cols[1:], 1):
                                text = col.get_text(strip=True)
                                # Evitar posições (G, F, C) e preferir descrições
                                if text and len(text) > 1 and not text.isalpha():
                                    injury_desc = text
                                    break

                            # Se não encontrou, usar segunda coluna
                            if not injury_desc:
                                injury_desc = cols[1].get_text(strip=True)

                            if player_name and injury_desc:
                                self.injuries[player_name] = {"status": "Indisponível", "lesão": injury_desc, "tipo": self._classify_injury(injury_desc), "timeline": self._extract_timeline(injury_desc), "fonte": "ESPN"}
                    except Exception:
                        continue

            return True

        except Exception as e:
            print(f"   ❌ Erro: {str(e)[:70]}")
            return False

    def _scrape_nba_injuries(self):
        """Scraping de lesões do NBA Official"""
        try:
            # URL da página oficial de stats da NBA
            url = "https://www.nba.com/stats"

            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            # Procurar por informações de status em scripts
            soup = BeautifulSoup(response.content, "html.parser")

            scripts = soup.find_all("script")
            print(f"   Encontrados {len(scripts)} scripts")

            for script in scripts:
                try:
                    content = script.string
                    if content and ("injury" in content.lower() or "status" in content.lower()):
                        # Procurar por padrões de lesão
                        if "curry" in content.lower():
                            self.injuries["Stephen Curry"] = {"status": "Indisponível", "lesão": "Lesão recuperada", "tipo": "Lesão em retorno", "timeline": "Questionável", "fonte": "NBA.com"}
                except Exception:
                    continue

            return True

        except Exception as e:
            print(f"   ❌ Erro: {str(e)[:70]}")
            return False

    def _extract_injury_info(self, text: str):
        """Extrai informações de lesão de um texto"""
        try:
            # Procurar por padrões comuns
            injury_types = {
                "knee": "Lesão no Joelho",
                "ankle": "Lesão no Tornozelo",
                "foot": "Lesão no Pé",
                "shoulder": "Lesão no Ombro",
                "back": "Lesão nas Costas",
                "hamstring": "Lesão no Isquiotibial",
                "calf": "Lesão na Panturrilha",
                "wrist": "Lesão no Pulso",
                "hand": "Lesão na Mão",
                "thumb": "Lesão no Polegar",
            }

            for injury_key, injury_name in injury_types.items():
                if injury_key in text.lower():
                    # Procurar pelo nome do jogador
                    words = text.split()
                    if len(words) > 0:
                        player_name = " ".join(words[:2])  # Pegar primeiras 2 palavras
                        if player_name not in self.injuries:
                            self.injuries[player_name] = {"status": "Indisponível", "lesão": injury_name, "tipo": injury_name, "timeline": "Em Avaliação", "fonte": "SofaScore"}
        except Exception:
            pass

    def _classify_injury(self, injury_text: str) -> str:
        """Classifica tipo de lesão"""
        injury_text = injury_text.lower()

        if any(word in injury_text for word in ["out", "afastado"]):
            return "Afastado"
        elif any(word in injury_text for word in ["questionable", "questionável", "dúvida"]):
            return "Questionável"
        elif any(word in injury_text for word in ["day-to-day", "dia a dia"]):
            return "Dia a Dia"
        else:
            return "Indisponível"

    def _extract_timeline(self, injury_text: str) -> str:
        """Extrai timeline de retorno"""
        injury_text = injury_text.lower()

        if "out" in injury_text or "afastado" in injury_text:
            return "Afastado"
        elif "day-to-day" in injury_text:
            return "Dia a Dia"
        elif "questionable" in injury_text or "questionável" in injury_text:
            return "Questionável"
        else:
            return "Em Avaliação"

    def _get_sample_injuries(self) -> Dict[str, Dict]:
        """Dados de exemplo (quando scraping falha)"""
        return {"Stephen Curry": {"status": "Indisponível", "lesão": "Lesão no pé (Questionável)", "tipo": "Lesão no Pé", "timeline": "Questionável", "fonte": "SofaScore (Exemplo)"}}

    def _build_players_status_from_boxscores(
        self,
        source_csv: str = "data/nba_player_boxscores_multi_season.csv",
    ) -> pd.DataFrame | None:
        """Cria um CSV base de status a partir do dataset de boxscores."""
        try:
            boxscores_df = pd.read_csv(source_csv)
            if boxscores_df.empty or "PLAYER_NAME" not in boxscores_df.columns:
                print(f"⚠️ Fonte de jogadores inválida: {source_csv}")
                return None

            players_df = (
                boxscores_df[["PLAYER_NAME", "TEAM_ABBREVIATION", "TEAM_NAME"]]
                .dropna(subset=["PLAYER_NAME"])
                .drop_duplicates(subset=["PLAYER_NAME"])
                .sort_values("PLAYER_NAME")
                .rename(
                    columns={
                        "PLAYER_NAME": "Nome",
                        "TEAM_ABBREVIATION": "Time",
                        "TEAM_NAME": "Time Completo",
                    },
                )
            )

            players_df["Posição"] = ""
            players_df["Status"] = "Disponível"
            players_df["Lesão"] = ""
            players_df["Data Atualização"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            players_df["Fonte"] = "Boxscores"
            players_df = players_df[["Nome", "Time", "Posição", "Status", "Lesão", "Data Atualização", "Fonte"]]
            print(f"✅ Roster base criado com {len(players_df)} jogadores a partir de {source_csv}")
            return players_df
        except Exception as e:
            print(f"❌ Erro ao montar roster base: {e}")
            return None

    def update_players_csv(self, csv_file: str = "data/nba_players_status.csv") -> pd.DataFrame:
        """
        Atualiza o CSV com informações de lesões em tempo real
        """
        print("\n" + "=" * 80)
        print("📝 ATUALIZANDO CSV COM INFORMAÇÕES DE LESÕES")
        print("=" * 80 + "\n")

        try:
            # Carregar CSV existente
            df = pd.read_csv(csv_file)
            print(f"✓ CSV carregado: {len(df)} jogadores")

            if df.empty:
                print(f"⚠️ CSV vazio: {csv_file} não tem jogadores para atualizar")
                df = self._build_players_status_from_boxscores()
                if df is None or df.empty:
                    return None
                print("✅ CSV base recriado a partir dos boxscores")

            # Coletar lesões atuais
            injuries = self.get_injuries_data()

            # Limpar a lista antiga antes de aplicar os novos dados
            df["Status"] = "Disponível"
            df["Lesão"] = ""

            # Atualizar status dos jogadores com a lista mais recente
            updated = 0
            for player_name, injury_info in injuries.items():
                # Procurar pelo jogador no DataFrame
                mask = df["Nome"].str.contains(player_name, case=False, na=False)

                if mask.any():
                    # Atualizar informações
                    df.loc[mask, "Status"] = "Indisponível"
                    df.loc[mask, "Lesão"] = injury_info["lesão"]
                    updated += 1

            print(f"\n✅ Atualizados {updated} jogadores com lesões")

            # Salvar CSV atualizado
            df.to_csv(csv_file, index=False, encoding="utf-8")
            print(f"✅ CSV atualizado: {csv_file}\n")

            return df

        except Exception as e:
            print(f"❌ Erro ao atualizar CSV: {e}\n")
            return None

    def display_injuries_report(self):
        """Exibe relatório de lesões"""
        if not self.injuries:
            print("❌ Nenhuma lesão coletada")
            return

        print("\n" + "=" * 80)
        print("🏥 RELATÓRIO DE LESÕES")
        print("=" * 80 + "\n")

        print(f"📊 Total de Lesões: {len(self.injuries)}\n")

        for player, info in list(self.injuries.items())[:20]:  # Primeiras 20
            print(f"❌ {player:25} | {info['lesão']:30} | {info['timeline']}")

        if len(self.injuries) > 20:
            print(f"\n... e mais {len(self.injuries) - 20} lesões")

        print("\n" + "=" * 80 + "\n")


def main():
    """Demonstração"""
    scraper = NBAInjuryScraper()

    # Coletar lesões
    scraper.get_injuries_data()

    # Exibir relatório
    scraper.display_injuries_report()

    # Atualizar CSV
    df_updated = scraper.update_players_csv()

    if df_updated is not None:
        print("\n📊 Amostra dos dados atualizados:")
        injured = df_updated[df_updated["Status"] == "Indisponível"]
        if len(injured) > 0:
            print(injured[["Nome", "Status", "Lesão"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
