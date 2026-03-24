import os
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="NBA Player Stats Explorer", layout="wide")

DATA_PATH = os.path.join(os.path.dirname(__file__), "nba_player_stats_multi_season.csv")

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    # Normalize column names: strip whitespace and lower-case for robust matching
    df.columns = [c.strip() for c in df.columns]
    df.rename(columns={c: c.strip().lower() for c in df.columns}, inplace=True)

    # Map common dataset column names to canonical names used in the app
    col_mapping = {}
    # Player column
    for candidate in ['player_name', 'player', 'name', 'playername', 'player full name']:
        if candidate in df.columns:
            col_mapping['Player'] = candidate
            break
    # Team column
    for candidate in ['team_abbreviation', 'team', 'team_abbrev', 'team_name']:
        if candidate in df.columns:
            col_mapping['Team'] = candidate
            break
    # Season column
    for candidate in ['season', 'season_name', 'year']:
        if candidate in df.columns:
            col_mapping['Season'] = candidate
            break
    # Position column (optional)
    for candidate in ['pos', 'position']:
        if candidate in df.columns:
            col_mapping['Pos'] = candidate
            break

    # Create canonical columns if the underlying column exists
    for canon, col in col_mapping.items():
        df[canon] = df[col]

    return df


def main():
    st.title("NBA Player Stats — Multi-season Explorer")
    st.markdown("Carregando dados de: ``nba_player_stats_multi_season.csv``")

    if not os.path.exists(DATA_PATH):
        st.error(f"Arquivo não encontrado: {DATA_PATH}")
        return

    df = load_data(DATA_PATH)

    # Basic info
    with st.expander("Dados básicos e amostra", expanded=True):
        st.write(f"Linhas: {df.shape[0]}, Colunas: {df.shape[1]}")
        st.dataframe(df.head(50))

    # Sidebar filters
    st.sidebar.header("Filtros")
    seasons = sorted(df['Season'].unique().tolist()) if 'Season' in df.columns else []
    season = st.sidebar.selectbox("Season", options=["All"] + seasons, index=0)

    teams = sorted(df['Team'].dropna().unique().tolist()) if 'Team' in df.columns else []
    team = st.sidebar.selectbox("Team", options=["All"] + teams, index=0)

    positions = sorted(df['Pos'].dropna().unique().tolist()) if 'Pos' in df.columns else []
    pos = st.sidebar.multiselect("Position", options=positions, default=positions)

    player_query = st.sidebar.text_input("Buscar jogador (parte do nome)")

    # Apply filters
    filtered = df.copy()
    if season != "All":
        if 'Season' in filtered.columns:
            filtered = filtered[filtered['Season'] == season]
    if team != "All":
        if 'Team' in filtered.columns:
            filtered = filtered[filtered['Team'] == team]
    if pos and 'Pos' in filtered.columns:
        filtered = filtered[filtered['Pos'].isin(pos)]
    if player_query:
        if 'Player' in filtered.columns:
            filtered = filtered[filtered['Player'].str.contains(player_query, case=False, na=False)]

    st.sidebar.markdown(f"Resultados: {filtered.shape[0]} linhas")

    # Main layout: top metrics and charts
    st.header("Exploração")
    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("Top por estatística")
        stat = st.selectbox("Estatística", options=[c for c in df.columns if c not in ['Player', 'Team', 'Season', 'Pos']][:10])
        topn = st.slider("Top N", 5, 50, 10)
        if stat:
            top_players = filtered.groupby('Player', as_index=False)[stat].mean().sort_values(by=stat, ascending=False).head(topn)
            st.table(top_players.reset_index(drop=True))

    with col1:
        st.subheader("Distribuição")
        numeric_cols = filtered.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            hist_col = st.selectbox("Histograma de", options=numeric_cols)
            chart = alt.Chart(filtered).mark_bar().encode(
                alt.X(f"{hist_col}", bin=alt.Bin(maxbins=40)),
                y='count()'
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Nenhuma coluna numérica disponível para histogramas.")

    st.markdown("---")

    # Player time series
    st.subheader("Série temporal por jogador")
    players = sorted(df['Player'].unique().tolist()) if 'Player' in df.columns else []
    sel_player = st.selectbox("Selecionar jogador", options=players)
    if sel_player:
        player_df = df[df['Player'] == sel_player].sort_values('Season') if 'Season' in df.columns else df[df['Player'] == sel_player]
        if player_df.empty:
            st.warning("Nenhum dado disponível para o jogador selecionado.")
        else:
            metrics = [c for c in player_df.columns if player_df[c].dtype.kind in 'biuf' and c not in ['Age']]
            if metrics:
                sel_metrics = st.multiselect("Métricas para plotar", options=metrics, default=metrics[:3])
                if sel_metrics:
                    # Melt the dataframe in pandas to avoid transform_fold dtype issues
                    if 'Season' in player_df.columns:
                        melted = player_df.melt(id_vars=['Season'], value_vars=sel_metrics, var_name='metric', value_name='value')
                        melted['Season'] = melted['Season'].astype(str)
                    else:
                        # Fallback: use the dataframe index as a pseudo-season
                        temp = player_df.reset_index().rename(columns={'index': 'Season'})
                        melted = temp.melt(id_vars=['Season'], value_vars=sel_metrics, var_name='metric', value_name='value')
                        melted['Season'] = melted['Season'].astype(str)

                    lines = alt.Chart(melted).mark_line(point=True).encode(
                        x=alt.X('Season:N'),
                        y=alt.Y('value:Q'),
                        color=alt.Color('metric:N'),
                        tooltip=['Season', 'metric', 'value']
                    ).properties(height=400)
                    st.altair_chart(lines, use_container_width=True)
            else:
                st.info("Nenhuma métrica numérica disponível para plotar.")

    st.markdown("---")
    st.subheader("Tabela filtrada")
    st.dataframe(filtered.reset_index(drop=True))

    # Quick download
    st.sidebar.markdown("---")
    st.sidebar.download_button("Baixar CSV filtrado", data=filtered.to_csv(index=False).encode('utf-8'), file_name='nba_filtered.csv')

    st.info("Dica: rode 'streamlit run app.py' no diretório do projeto para executar.")


if __name__ == '__main__':
    main()
