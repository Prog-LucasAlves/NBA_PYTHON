"""
Processa dados de partidas e integra com o modelo de previsão.

Este script:
1. Coleta dados de jogadores por partida (web scraper)
2. Processa e normaliza os dados
3. Integra com dados históricos existentes
4. Prepara para treinamento de modelo
"""

import warnings
from pathlib import Path

import pandas as pd

from nba_game_stats_scraper import NBAGameStatsScraper

warnings.filterwarnings("ignore")


class GameStatsProcessor:
    """Processa e integra dados de partidas com sistema de previsão."""

    def __init__(self, base_path: str = "."):
        """
        Inicializa o processador.

        Args:
            base_path: Caminho base para arquivos
        """
        self.base_path = Path(base_path)
        self.scraper = NBAGameStatsScraper()
        self.raw_data = None
        self.processed_data = None

    def collect_game_stats(
        self,
        season: int = 2024,
        max_games: int = 500,
    ) -> pd.DataFrame:
        """
        Coleta estatísticas de partidas.

        Args:
            season: Temporada para coletar
            max_games: Limite de partidas

        Returns:
            DataFrame com dados coletados
        """
        print(f"\n🔄 Coletando dados da temporada {season}...")
        self.raw_data = self.scraper.scrape_game_stats(
            season=season,
            max_games=max_games,
            verbose=True,
        )
        return self.raw_data

    def process_game_stats(self) -> pd.DataFrame:
        """
        Processa e normaliza dados de partidas.

        Returns:
            DataFrame processado
        """
        if self.raw_data is None or self.raw_data.empty:
            print("❌ Nenhum dado para processar")
            return pd.DataFrame()

        print("\n⚙️ Processando dados...")

        df = self.raw_data.copy()

        # 1. Limpeza de dados
        print("  ✓ Limpando dados...")
        df = self._clean_data(df)

        # 2. Conversão de tipos
        print("  ✓ Convertendo tipos...")
        df = self._convert_types(df)

        # 3. Cálculo de estatísticas derivadas
        print("  ✓ Calculando stats derivadas...")
        df = self._calculate_derived_stats(df)

        # 4. Normalização de nomes
        print("  ✓ Normalizando nomes...")
        df = self._normalize_names(df)

        self.processed_data = df
        print(f"✅ Processamento concluído: {len(df)} registros")

        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicatas e valores inválidos."""
        # Remover duplicatas
        initial_count = len(df)
        df = df.drop_duplicates(
            subset=["game_id", "player_name", "team"],
            keep="last",
        )
        removed = initial_count - len(df)
        if removed > 0:
            print(f"    - {removed} duplicatas removidas")

        # Remover linhas com valores NaN críticos
        critical_cols = ["player_name", "team", "game_date"]
        df = df.dropna(subset=critical_cols)

        # Preencher NaNs em stats com 0
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
        df[stat_cols] = df[stat_cols].fillna(0)

        return df

    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converte tipos de dados."""
        # Converter stats para numérico
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

        for col in stat_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Converter datas
        df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")

        # Converter season e game_id
        df["season"] = df["season"].astype("int64")
        df["game_id"] = df["game_id"].astype("str")

        return df

    def _calculate_derived_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula estatísticas derivadas."""
        # Percentuais de acerto
        df["FG_PCT"] = 0.0
        df["3PT_PCT"] = 0.0
        df["FT_PCT"] = 0.0

        # Field Goal %
        fg_mask = df["FGA"] > 0
        df.loc[fg_mask, "FG_PCT"] = (df.loc[fg_mask, "FG"] / df.loc[fg_mask, "FGA"]) * 100

        # 3-Point %
        three_mask = df["3PA"] > 0
        df.loc[three_mask, "3PT_PCT"] = (df.loc[three_mask, "3PT"] / df.loc[three_mask, "3PA"]) * 100

        # Free Throw %
        ft_mask = df["FTA"] > 0
        df.loc[ft_mask, "FT_PCT"] = (df.loc[ft_mask, "FT"] / df.loc[ft_mask, "FTA"]) * 100

        # Substituir infinitos e NaNs por 0
        df = df.replace([float("inf"), float("-inf")], 0).fillna(0)

        return df

    def _normalize_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza nomes de jogadores e times."""
        # Normalizar nomes de jogadores (capitalize)
        df["player_name"] = df["player_name"].str.strip().str.title()

        # Normalizar times (uppercase)
        df["team"] = df["team"].str.strip().str.upper()
        df["opponent"] = df["opponent"].str.strip().str.upper()

        return df

    def aggregate_player_stats(self) -> pd.DataFrame:
        """
        Agrega stats por jogador e temporada.

        Returns:
            DataFrame com stats agregadas
        """
        if self.processed_data is None:
            return pd.DataFrame()

        print("\n📊 Agregando stats por jogador...")

        df = self.processed_data.copy()

        # Colunas para agregação
        numeric_cols = [
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

        # Agrupar por jogador e temporada
        agg_dict = {col: "mean" for col in numeric_cols}
        agg_dict["game_id"] = "count"  # Contador de partidas

        aggregated = df.groupby(["player_name", "team", "season"]).agg(agg_dict).reset_index()
        aggregated.rename(columns={"game_id": "GP"}, inplace=True)  # GP = Games Played

        print(f"✅ {len(aggregated)} registros agregados")

        return aggregated

    def merge_with_historical(self, csv_path: str = "training_data.csv") -> pd.DataFrame:
        """
        Mescla dados processados com histórico existente.

        Args:
            csv_path: Caminho do arquivo histórico

        Returns:
            DataFrame mesclado
        """
        print(f"\n🔗 Mesclando com histórico ({csv_path})...")

        filepath = self.base_path / csv_path
        aggregated = self.aggregate_player_stats()

        if not filepath.exists():
            print("  ℹ️ Arquivo não encontrado. Usando apenas dados novos.")
            merged = aggregated
        else:
            historical = pd.read_csv(filepath)
            print(f"  Histórico: {len(historical)} registros")
            print(f"  Novos: {len(aggregated)} registros")

            # Concatenar e remover duplicatas (keep newer)
            merged = pd.concat([historical, aggregated], ignore_index=True)
            merged = merged.sort_values("season", ascending=False)
            merged = merged.drop_duplicates(
                subset=["player_name", "team", "season"],
                keep="first",
            )

            print(f"  Total mesclado: {len(merged)} registros")

        return merged

    def save_processed_data(
        self,
        df: pd.DataFrame,
        filename: str = "game_stats_processed.csv",
    ) -> bool:
        """
        Salva dados processados.

        Args:
            df: DataFrame a salvar
            filename: Nome do arquivo

        Returns:
            True se salvo com sucesso
        """
        try:
            filepath = self.base_path / filename
            df.to_csv(filepath, index=False)
            print(f"\n✅ Dados salvos em: {filepath}")
            print(f"   Registros: {len(df)}")
            print(f"   Colunas: {len(df.columns)}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar: {str(e)}")
            return False

    def generate_processing_report(self) -> None:
        """Gera relatório do processamento."""
        if self.processed_data is None:
            print("❌ Nenhum dado processado")
            return

        print("\n" + "=" * 70)
        print("📋 RELATÓRIO DE PROCESSAMENTO DE DADOS")
        print("=" * 70)

        df = self.processed_data

        print("\n📊 Estatísticas Gerais:")
        print(f"  Total de registros: {len(df)}")
        print(f"  Jogadores únicos: {df['player_name'].nunique()}")
        print(f"  Partidas únicas: {df['game_id'].nunique()}")
        print(f"  Times: {df['team'].nunique()}")
        print(f"  Temporadas: {sorted(df['season'].unique())}")

        print("\n📅 Cobertura Temporal:")
        print(f"  Primeira partida: {df['game_date'].min()}")
        print(f"  Última partida: {df['game_date'].max()}")
        days_span = (df["game_date"].max() - df["game_date"].min()).days
        print(f"  Período: {days_span} dias")

        print("\n🎯 Top 20 Jogadores (por partidas):")
        top_players = df["player_name"].value_counts().head(20)
        for i, (player, count) in enumerate(top_players.items(), 1):
            print(f"  {i:2d}. {player}: {count:3d} partidas")

        print("\n📈 Distribuição por Time:")
        team_dist = df["team"].value_counts()
        for team, count in team_dist.items():
            print(f"  {team}: {count} registros")

        print("\n✅ Qualidade dos Dados:")
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
        null_percentages = (df[stat_cols].isna().sum() / len(df) * 100).sort_values()
        for col, pct in null_percentages[null_percentages > 0].items():
            print(f"  {col}: {pct:.2f}% valores ausentes")

        print("\n" + "=" * 70)


def main():
    """Exemplo de uso do processador."""
    processor = GameStatsProcessor()

    # 1. Coletar dados
    raw_df = processor.collect_game_stats(season=2024, max_games=100)

    if raw_df.empty:
        print("⚠️ Nenhum dado coletado")
        return

    # 2. Processar
    processed_df = processor.process_game_stats()

    # 3. Salvar dados processados
    processor.save_processed_data(processed_df, "nba_game_stats_2024_processed.csv")

    # 4. Relatório
    processor.generate_processing_report()

    # 5. Agregar e mesclar com histórico (opcional)
    # merged_df = processor.merge_with_historical("training_data.csv")
    # processor.save_processed_data(merged_df, "training_data_updated.csv")


if __name__ == "__main__":
    main()
