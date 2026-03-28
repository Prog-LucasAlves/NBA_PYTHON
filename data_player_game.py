#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coleta dados de boxscores de jogadores da NBA.

Coleta dados de: https://www.nba.com/stats/players/boxscores

Implementações:
- Retry strategy com backoff exponencial (evita rate limiting)
- User-Agent rotation (evita detecção de bot)
- Cache em JSON (recuperação instantânea)
- Timeout aumentado (API pode ser lenta)
- Logging detalhado
- Tratamento robusto de erros
"""

import json
import logging
import os
import time
from typing import Dict, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://stats.nba.com/stats/leaguedashplayerstats"

# User-Agents para rotation (evita bloqueios)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/stats/players/boxscores",
}

SLEEP_SECONDS = 1.2  # Delay entre requisições


class BoxscoresCollector:
    """Coleta dados de boxscores de jogadores."""

    def __init__(self, cache_dir: str = "data/.cache"):
        """
        Inicializa o coletor.

        Args:
            cache_dir: Diretório para cache de dados
        """
        self.session = requests.Session()

        # Configura retry strategy com backoff exponencial
        retry_strategy = Retry(
            total=3,  # Total de tentativas
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            backoff_factor=1.5,  # Espera 1.5s, 3s, 4.5s entre tentativas
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(HEADERS)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.user_agent_index = 0

    def _get_cache_path(self, params: Dict) -> str:
        """Gera caminho de cache para uma requisição."""
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_file = f"boxscores_{param_str}.json"
        return os.path.join(self.cache_dir, cache_file)

    def _load_from_cache(self, cache_path: str) -> Optional[Dict]:
        """Carrega dados do cache se existirem."""
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    logger.debug(f"📦 Usando cache: {os.path.basename(cache_path)}")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️  Erro ao ler cache: {str(e)}")
        return None

    def _save_to_cache(self, cache_path: str, data: Dict) -> None:
        """Salva dados em cache."""
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"⚠️  Erro ao salvar cache: {str(e)}")

    def _make_request(self, params: Dict, use_cache: bool = True) -> Optional[Dict]:
        """
        Faz requisição com cache, retry e rate limiting.

        Args:
            params: Parâmetros da requisição
            use_cache: Se True, usa cache quando disponível

        Returns:
            Dados JSON ou None se falhar
        """
        cache_path = self._get_cache_path(params)

        # Tenta carregar do cache
        if use_cache:
            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                return cached_data

        try:
            logger.debug(f"📡 Requisitando: {BASE_URL}")
            logger.debug(f"   Params: {params}")

            # Rotaciona User-Agent
            headers = HEADERS.copy()
            headers["User-Agent"] = USER_AGENTS[self.user_agent_index % len(USER_AGENTS)]
            self.user_agent_index += 1

            # Timeout aumentado para 60s (API pode ser muito lenta)
            response = self.session.get(BASE_URL, params=params, headers=headers, timeout=60)
            response.raise_for_status()

            # Valida que é JSON
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                logger.warning(f"⚠️  Content-Type não é JSON: {content_type}")
                logger.debug(f"   Corpo: {response.text[:200]}")
                return None

            data = response.json()

            # Salva em cache
            self._save_to_cache(cache_path, data)

            # Respeita rate limit
            time.sleep(SLEEP_SECONDS)

            return data

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout na requisição (60s) - API muito lenta")
            logger.info("💡 Dica: Tente novamente mais tarde ou use dados em cache")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Erro HTTP ({e.response.status_code}): {str(e)[:100]}")
            logger.debug(f"   Resposta: {e.response.text[:200]}")
            return None
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON: {str(e)[:100]}")
            logger.debug("   ℹ️  A página pode estar em HTML, não JSON")
            logger.debug(f"   URL: {BASE_URL}")
            logger.debug(f"   Params: {params}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro na requisição: {str(e)[:100]}")
            return None

    def get_player_stats_by_game(self, season: str = "2025-26", season_type: str = "Regular Season", measure_type: str = "Base") -> Optional[pd.DataFrame]:
        """
        Coleta estatísticas de jogadores por jogo.

        Args:
            season: Temporada (ex: "2025-26")
            season_type: Tipo de temporada ('Regular Season', 'Playoffs')
            measure_type: Tipo de medida ('Base', 'Advanced')

        Returns:
            DataFrame com estatísticas ou None se falhar
        """
        try:
            logger.info(f"🏀 Coletando boxscores da temporada {season}...")

            params = {
                "Season": season,
                "SeasonType": season_type,
                "MeasureType": measure_type,
                "PerMode": "PerGame",
                "LeagueID": "00",
                "PageSize": 1000,
                "PageNum": 1,
            }

            data = self._make_request(params, use_cache=True)

            if not data:
                logger.warning(f"⚠️  Nenhum dado retornado para {season}")
                return None

            # Extrair dados de jogadores
            player_stats = data.get("resultSet", {}).get("rowSet", [])
            headers = data.get("resultSet", {}).get("headers", [])

            if not player_stats or not headers:
                logger.warning("⚠️  Nenhum dado de jogador encontrado")
                return None

            df = pd.DataFrame(player_stats, columns=headers)

            # Adicionar coluna de temporada
            df["SEASON"] = season

            logger.info(f"✅ Coletados {len(df)} registros para {season}")
            logger.info(f"   Colunas: {len(df.columns)}")
            logger.info(f"   Período: {df.get('GAME_DATE', pd.Series()).min() if 'GAME_DATE' in df.columns else 'N/A'} a {df.get('GAME_DATE', pd.Series()).max() if 'GAME_DATE' in df.columns else 'N/A'}")

            return df

        except Exception as e:
            logger.error(f"❌ Erro ao coletar dados: {str(e)[:100]}")
            return None

    def save_to_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """
        Salva dados em CSV.

        Args:
            df: DataFrame para salvar
            filename: Nome do arquivo

        Returns:
            True se salvo com sucesso
        """
        try:
            filepath = os.path.join("data", filename)
            os.makedirs("data", exist_ok=True)

            df.to_csv(filepath, index=False, encoding="utf-8")

            size_kb = os.path.getsize(filepath) / 1024
            logger.info(f"💾 Salvo: {filename} ({size_kb:.1f} KB, {len(df)} linhas)")

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao salvar {filename}: {str(e)}")
            return False

    def get_summary(self, df: pd.DataFrame) -> None:
        """Exibe resumo dos dados."""
        if df is None or df.empty:
            logger.warning("⚠️  Nenhum dado para resumir")
            return

        logger.info("\n" + "=" * 70)
        logger.info("📊 RESUMO DOS DADOS")
        logger.info("=" * 70)

        logger.info(f"  📌 Total de linhas: {len(df)}")
        logger.info(f"  📋 Total de colunas: {len(df.columns)}")

        if "PLAYER_ID" in df.columns:
            logger.info(f"  👥 Jogadores únicos: {df['PLAYER_ID'].nunique()}")

        if "GAME_ID" in df.columns:
            logger.info(f"  🎮 Jogos únicos: {df['GAME_ID'].nunique()}")

        if "GAME_DATE" in df.columns:
            dates = pd.to_datetime(df["GAME_DATE"], errors="coerce")
            logger.info(f"  📅 Período: {dates.min()} a {dates.max()}")

        if "PTS" in df.columns:
            pts_mean = df["PTS"].mean()
            pts_std = df["PTS"].std()
            logger.info(f"  📈 Pontos: {pts_mean:.1f} ± {pts_std:.1f}")

        logger.info("=" * 70 + "\n")


def main() -> None:
    """Função principal."""
    collector = BoxscoresCollector()

    season = "2025-26"
    season_type = "Regular Season"

    logger.info("\n" + "🚀 " * 20)
    logger.info("COLETA DE BOXSCORES")
    logger.info("🚀 " * 20 + "\n")

    # Coleta dados
    df = collector.get_player_stats_by_game(season, season_type)

    if df is not None and not df.empty:
        # Exibe resumo
        collector.get_summary(df)

        # Salva em CSV
        collector.save_to_csv(df, f"nba_boxscores_{season}.csv")

        logger.info("✅ Coleta concluída com sucesso!")
    else:
        logger.warning("⚠️  Nenhum dado foi coletado")


if __name__ == "__main__":
    main()
