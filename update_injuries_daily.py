#!/usr/bin/env python
"""
Script para atualizar lesões diariamente
Integração com nba_injury_scraper.py e betting_app.py
"""

from datetime import datetime

from nba_injury_scraper import NBAInjuryScraper


def update_player_status_csv():
    """
    Atualiza o CSV de status de jogadores com lesões em tempo real
    Pode ser executado:
    - Manualmente: python update_injuries_daily.py
    - Automaticamente: via scheduler (cron, Windows Task Scheduler, etc)
    """

    print("\n" + "=" * 80)
    print("🔄 ATUALIZANDO STATUS DE LESÕES")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    # Criar scraper
    scraper = NBAInjuryScraper()

    # Atualizar CSV
    df_updated = scraper.update_players_csv("nba_players_status.csv")

    if df_updated is not None:
        # Estatísticas
        total_players = len(df_updated)
        injured_count = len(df_updated[df_updated["Status"] == "Indisponível"])
        available_count = len(df_updated[df_updated["Status"] == "Disponível"])

        print("\n" + "=" * 80)
        print("📊 RESUMO DA ATUALIZAÇÃO")
        print("=" * 80)
        print(f"✓ Total de Jogadores:      {total_players}")
        print(f"❌ Indisponíveis:           {injured_count} ({injured_count * 100 / total_players:.1f}%)")
        print(f"✅ Disponíveis:             {available_count} ({available_count * 100 / total_players:.1f}%)")
        print("=" * 80 + "\n")

        return True

    return False


if __name__ == "__main__":
    success = update_player_status_csv()
    exit(0 if success else 1)
