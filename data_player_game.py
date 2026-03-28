#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coleta dados de desempenho de cada jogador por partida da temporada.

Implementa:
- LeagueGameFinder para coleta eficiente (evita rate limiting)
- Verificação de ROSTERSTATUS em commonplayerinfo
- Cache de dados
- Rate limiting seguro
- Tratamento robusto de erros
"""

import json
import logging
import os
import time
from typing import Dict, Optional

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

STATS_API_BASE = "https://stats.nba.com/stats"

# User-Agents para rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


class PlayerGameDataCollector:
    """Coleta dados de partidas por jogador usando LeagueGameFinder."""

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
            status_forcelist=[429, 500, 502, 503, 504],  # Status codes para retry
            allowed_methods=["GET", "HEAD"],
            backoff_factor=1.5,  # Espera 1.5, 3, 4.5 segundos entre tentativas
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(HEADERS)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.rate_limit_delay = 1.5  # Delay entre requisições (aumentado)
        self.user_agent_index = 0  # Para rotation de User-Agent

    def _get_cache_path(self, endpoint: str, params: Dict) -> str:
        """Gera caminho de cache para uma requisição."""
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_file = f"{endpoint}_{param_str}.json"
        return os.path.join(self.cache_dir, cache_file)

    def _load_from_cache(self, cache_path: str) -> Optional[Dict]:
        """Carrega dados do cache se existirem."""
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
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

    def _make_request(self, endpoint: str, params: Dict, use_cache: bool = True) -> Optional[Dict]:
        """
        Faz requisição à API com cache, retry e rate limiting.

        Args:
            endpoint: Nome do endpoint (ex: 'leaguegamefinder')
            params: Parâmetros da requisição
            use_cache: Se True, usa cache quando disponível

        Returns:
            Dados JSON ou None se falhar
        """
        cache_path = self._get_cache_path(endpoint, params)

        # Tenta carregar do cache
        if use_cache:
            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                logger.debug(f"📦 Usando cache para {endpoint}")
                return cached_data

        try:
            url = f"{STATS_API_BASE}/{endpoint}"
            logger.debug(f"📡 Requisitando {endpoint} com params: {params}")

            # Rotaciona User-Agent
            headers = HEADERS.copy()
            headers["User-Agent"] = USER_AGENTS[self.user_agent_index % len(USER_AGENTS)]
            self.user_agent_index += 1

            # Timeout aumentado para 30s (API pode ser lenta)
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Salva em cache
            self._save_to_cache(cache_path, data)

            # Respeita rate limit
            time.sleep(self.rate_limit_delay)

            return data

        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout na requisição a {endpoint} (30s)")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Erro HTTP ({e.response.status_code}): {endpoint}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro na requisição: {str(e)}")
            return None

    def get_active_players(self, season: str = "2025-26") -> Optional[pd.DataFrame]:
        """
        Obtém lista de jogadores ativos com status de roster.

        Args:
            season: Temporada no formato "YYYY-YY"

        Returns:
            DataFrame com jogadores ativos
        """
        try:
            logger.info(f"👥 Obtendo jogadores ativos da temporada {season}...")

            params = {"LeagueID": "00", "Season": season, "SeasonType": "Regular Season", "PerMode": "PerGame"}

            data = self._make_request("leaguedashplayerstats", params)

            if not data or "resultSets" not in data:
                logger.warning(f"⚠️  Sem dados de jogadores para {season}")
                return None

            headers = data["resultSets"][0]["headers"]
            rows = data["resultSets"][0]["rowSet"]

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=headers)

            # Mantém apenas PLAYER_ID e PLAYER_NAME para referência
            if "PLAYER_ID" in df.columns and "PLAYER_NAME" in df.columns:
                df = df[["PLAYER_ID", "PLAYER_NAME"]].copy()
                df.drop_duplicates(subset=["PLAYER_ID"], inplace=True)
                logger.info(f"✅ Encontrados {len(df)} jogadores ativos")
                return df

            return None

        except Exception as e:
            logger.error(f"❌ Erro ao obter jogadores ativos: {str(e)}")
            return None

    def verify_roster_status(self, player_id: int) -> Optional[str]:
        """
        Verifica o status de roster do jogador (mais preciso que is_active).

        Args:
            player_id: ID do jogador

        Returns:
            Status do roster ou None se não disponível
        """
        try:
            params = {"PlayerID": player_id}
            data = self._make_request("commonplayerinfo", params)

            if not data or "resultSets" not in data or len(data["resultSets"]) < 1:
                return None

            headers = data["resultSets"][0]["headers"]
            rows = data["resultSets"][0]["rowSet"]

            if not rows:
                return None

            if "ROSTERSTATUS" in headers:
                idx = headers.index("ROSTERSTATUS")
                return rows[0][idx]

            return None

        except Exception as e:
            logger.debug(f"⚠️  Erro ao verificar status de {player_id}: {str(e)}")
            return None

    def get_league_game_finder(self, season: str = "2025-26", season_type: str = "Regular Season") -> Optional[pd.DataFrame]:
        """
        Coleta dados de todos os jogos usando LeagueGameFinder.

        Muito mais eficiente do que fazer chamadas individuais por jogador.

        Args:
            season: Temporada no formato "YYYY-YY"
            season_type: Tipo de temporada ('Regular Season', 'Playoffs', 'All-Star')

        Returns:
            DataFrame com dados de cada jogador em cada partida
        """
        try:
            logger.info(f"\n🎮 Coletando dados de partidas com LeagueGameFinder ({season})...")
            logger.info(f"   Tipo: {season_type}")
            logger.info("   ⏳ Isso pode levar alguns minutos...")

            params = {"LeagueID": "00", "Season": season, "SeasonType": season_type, "PerMode": "PerGame"}

            data = self._make_request("leaguegamefinder", params, use_cache=True)

            if not data or "resultSets" not in data:
                logger.warning(f"⚠️  Sem dados de partidas para {season}")
                return None

            if len(data["resultSets"]) < 1:
                logger.warning("⚠️  Nenhuma linha de dados retornada")
                return None

            headers = data["resultSets"][0]["headers"]
            rows = data["resultSets"][0]["rowSet"]

            if not rows:
                logger.warning("⚠️  Nenhuma partida encontrada")
                return None

            df = pd.DataFrame(rows, columns=headers)

            logger.info(f"✅ Coletadas {len(df)} linhas de dados de partidas")
            logger.info(f"   Jogadores únicos: {df['PLAYER_ID'].nunique() if 'PLAYER_ID' in df.columns else 'N/A'}")
            logger.info(f"   Partidas únicas: {df['Game_ID'].nunique() if 'Game_ID' in df.columns else 'N/A'}")

            return df

        except Exception as e:
            logger.error(f"❌ Erro ao coletar dados de partidas: {str(e)}")
            return None

    def get_player_game_logs(self, player_id: int, season: str = "2025-26") -> Optional[pd.DataFrame]:
        """
        Coleta histórico de jogos de um jogador específico.

        Use apenas para jogadores individuais após coleta em massa com LeagueGameFinder.

        Args:
            player_id: ID do jogador
            season: Temporada

        Returns:
            DataFrame com logs de jogo do jogador
        """
        try:
            params = {"PlayerID": player_id, "Season": season, "SeasonType": "Regular Season"}

            data = self._make_request("playergamelog", params)

            if not data or "resultSets" not in data:
                return None

            headers = data["resultSets"][0]["headers"]
            rows = data["resultSets"][0]["rowSet"]

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=headers)
            return df

        except Exception as e:
            logger.warning(f"⚠️  Erro ao coletar logs de {player_id}: {str(e)}")
            return None

    def enrich_with_roster_status(self, df: pd.DataFrame, sample_size: int = 50) -> pd.DataFrame:
        """
        Enriquece dados com status de roster de uma amostra de jogadores.

        Não verifica TODOS os jogadores para economizar rate limits.

        Args:
            df: DataFrame com dados de partidas
            sample_size: Quantos jogadores únicos verificar

        Returns:
            DataFrame com coluna ROSTERSTATUS_VERIFIED
        """
        try:
            if "PLAYER_ID" not in df.columns:
                logger.warning("⚠️  Coluna PLAYER_ID não encontrada")
                return df

            unique_players = df["PLAYER_ID"].unique()[:sample_size]

            logger.info(f"🔍 Verificando status de roster de {len(unique_players)} jogadores...")

            roster_statuses = {}
            for i, player_id in enumerate(unique_players):
                status = self.verify_roster_status(int(player_id))
                roster_statuses[player_id] = status

                if (i + 1) % 10 == 0:
                    logger.debug(f"   ✓ {i + 1}/{len(unique_players)}")

            df["ROSTERSTATUS_VERIFIED"] = df["PLAYER_ID"].map(roster_statuses)
            logger.info("✅ Status de roster verificado")

            return df

        except Exception as e:
            logger.error(f"❌ Erro ao enriquecer com status de roster: {str(e)}")
            return df

    def save_game_data(self, df: pd.DataFrame, filename: str = "nba_player_game_data.csv") -> bool:
        """
        Salva dados de partidas em CSV.

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
            logger.info(f"💾 Salvo: {filename} ({size_kb:.1f} KB)")

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao salvar {filename}: {str(e)}")
            return False

    def get_data_summary(self, df: pd.DataFrame) -> None:
        """Exibe resumo dos dados coletados."""
        if df is None or df.empty:
            logger.warning("⚠️  Nenhum dado para resumir")
            return

        logger.info("\n" + "=" * 70)
        logger.info("📊 RESUMO DOS DADOS COLETADOS")
        logger.info("=" * 70)

        if "PLAYER_ID" in df.columns:
            logger.info(f"  👥 Jogadores únicos: {df['PLAYER_ID'].nunique()}")

        if "Game_ID" in df.columns:
            logger.info(f"  🎮 Partidas únicas: {df['Game_ID'].nunique()}")

        if "GAME_DATE" in df.columns:
            logger.info(f"  📅 Período: {df['GAME_DATE'].min()} a {df['GAME_DATE'].max()}")

        if "PTS" in df.columns:
            logger.info(f"  📈 Pontos por jogo: {df['PTS'].mean():.1f} ± {df['PTS'].std():.1f}")

        if "FGA" in df.columns:
            logger.info(f"  🎯 Taxa de arremesso: {(df['FGM'] / df['FGA'].replace(0, np.nan)).mean() * 100:.1f}%")

        logger.info(f"  📌 Total de linhas: {len(df)}")
        logger.info("=" * 70 + "\n")


def main():
    """Função principal para coleta de dados de partidas."""
    collector = PlayerGameDataCollector()

    season = "2025-26"

    logger.info("\n" + "🚀 " * 20)
    logger.info("COLETA DE DADOS DE PARTIDAS POR JOGADOR")
    logger.info("🚀 " * 20 + "\n")

    # 1. Coleta dados de jogadores ativos
    df_players = collector.get_active_players(season)
    if df_players is not None:
        logger.info(f"✅ Carregados {len(df_players)} jogadores")

    # 2. Coleta dados de TODAS as partidas (muito mais eficiente)
    df_games = collector.get_league_game_finder(season, "Regular Season")

    if df_games is not None:
        # 3. Enriquece com verificação de status de roster
        df_games = collector.enrich_with_roster_status(df_games, sample_size=100)

        # 4. Exibe resumo
        collector.get_data_summary(df_games)

        # 5. Salva em CSV
        collector.save_game_data(df_games, f"nba_player_game_data_{season}.csv")

    logger.info("\n✅ Coleta de dados concluída!")
    logger.info("💡 Dica: Esses dados estão prontos para treinar o modelo de predição.")


if __name__ == "__main__":
    main()
