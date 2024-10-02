import streamlit as st
import pandas as pd
from statsbombpy import sb
from mplsoccer import Pitch
import matplotlib.pyplot as plt
import seaborn as sns
import time
from PIL import Image

# Função de cache para otimizar o carregamento de dados
@st.cache_data
def get_competitions():
    competitions = sb.competitions().drop_duplicates(subset=['competition_id', 'competition_name'])
    return competitions[['competition_id', 'competition_name', 'season_name']]

@st.cache_data
def get_seasons(competition_id):
    competitions = sb.competitions()
    return competitions[competitions['competition_id'] == competition_id][['season_id', 'season_name']].drop_duplicates()

@st.cache_data
def get_matches(competition_id, season_id):
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    return matches[['match_id', 'home_team', 'away_team', 'home_score', 'away_score', 'kick_off']]

@st.cache_data
def get_players(events_df):
    return events_df['player'].dropna().unique()

@st.cache_data
def get_match_stats(match_id):
    events = sb.events(match_id=match_id)
    
    # Segregando eventos por clube
    home_team = events['team'].iloc[0]
    away_team = events['team'].iloc[1]

    stats_home = {
        'gols': len(events[(events['team'] == home_team) & (events['type'] == 'Shot') & (events['shot_outcome'] == 'Goal')]),
        'chutes': len(events[(events['team'] == home_team) & (events['type'] == 'Shot')]),
        'passes': len(events[(events['team'] == home_team) & (events['type'] == 'Pass')]),
        'desarmes': len(events[(events['team'] == home_team) & (events['type'] == 'Duel')]),
    }

    stats_away = {
        'gols': len(events[(events['team'] == away_team) & (events['type'] == 'Shot') & (events['shot_outcome'] == 'Goal')]),
        'chutes': len(events[(events['team'] == away_team) & (events['type'] == 'Shot')]),
        'passes': len(events[(events['team'] == away_team) & (events['type'] == 'Pass')]),
        'desarmes': len(events[(events['team'] == away_team) & (events['type'] == 'Duel')]),
    }

    return stats_home, stats_away, events

# Função para exibir o comparativo em forma de tabela
def display_comparison_table(stats_home, stats_away, home_team, away_team):
    comparison_df = pd.DataFrame({
        'Estatística': ['Gols', 'Chutes', 'Passes', 'Desarmes'],
        home_team: [stats_home['gols'], stats_home['chutes'], stats_home['passes'], stats_home['desarmes']],
        away_team: [stats_away['gols'], stats_away['chutes'], stats_away['passes'], stats_away['desarmes']]
    })
    
    st.write("### Comparativo de Estatísticas entre Clubes")
    st.table(comparison_df)

# Função para permitir o download de dados filtrados por clube
def download_data(events_df, team):
    team_events = events_df[events_df['team'] == team]
    csv = team_events.to_csv(index=False)
    st.download_button(label=f"Baixar Dados Filtrados do {team} (CSV)", data=csv, file_name=f'{team}_eventos.csv', mime='text/csv')

# Função para gerar o mapa de passes e exibir métricas detalhadas
def plot_pass_map(events_df, player_name):
    passes = events_df[(events_df['type'] == 'Pass') & (events_df['player'] == player_name)]
    
    pitch = Pitch(pitch_color='grass', line_color='white', stripe=True)
    fig, ax = pitch.draw(figsize=(10, 6))
    
    # Mapa de calor para localização dos passes
    pitch.kdeplot(passes['location'].apply(lambda x: x[0]),
                  passes['location'].apply(lambda x: x[1]),
                  ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=100)
    
    # Desenhando setas para os passes
    pitch.arrows(passes['location'].apply(lambda x: x[0]),
                 passes['location'].apply(lambda x: x[1]),
                 passes['pass_end_location'].apply(lambda x: x[0]),
                 passes['pass_end_location'].apply(lambda x: x[1]),
                 width=2, headwidth=3, color='blue', ax=ax, label='Passes', alpha=0.6)
    
    ax.set_title(f'Mapa de Passes - {player_name}', fontsize=18, color='white')
    st.pyplot(fig)
    
    # Exibir métricas de passes
    total_passes = len(passes)
    successful_passes = len(passes[passes['pass_outcome'].isna()])
    pass_success_rate = (successful_passes / total_passes) * 100 if total_passes > 0 else 0
    
    st.write("### Estatísticas de Passes")
    st.metric(label="Total de Passes", value=total_passes)
    st.metric(label="Passes Bem-Sucedidos", value=successful_passes)
    st.metric(label="Percentual de Passes Bem-Sucedidos", value=f"{pass_success_rate:.2f}%")

# Função para gerar o mapa de chutes e exibir métricas detalhadas
def plot_shot_map(events_df, player_name):
    shots = events_df[(events_df['type'] == 'Shot') & (events_df['player'] == player_name)]
    
    pitch = Pitch(pitch_color='grass', line_color='white', stripe=True)
    fig, ax = pitch.draw(figsize=(10, 6))
    
    # Desenhando localização dos chutes
    pitch.scatter(shots['location'].apply(lambda x: x[0]),
                  shots['location'].apply(lambda x: x[1]),
                  c='red', s=100, ax=ax, label='Chutes', alpha=0.7)
    
    ax.set_title(f'Mapa de Chutes - {player_name}', fontsize=18, color='white')
    st.pyplot(fig)

    # Calcular e exibir métricas de chutes
    total_shots = len(shots)
    goals = len(shots[shots['shot_outcome'] == 'Goal'])
    conversion_rate = (goals / total_shots) * 100 if total_shots > 0 else 0
    
    st.write("### Estatísticas de Chutes")
    st.metric(label="Total de Chutes", value=total_shots)
    st.metric(label="Gols", value=goals)
    st.metric(label="Percentual de Conversão de Chutes em Gols", value=f"{conversion_rate:.2f}%")

# Título do dashboard
st.title('Análise de Partidas com StatsBombPy')

# Menu para navegar entre as seções
menu = st.sidebar.selectbox('Selecione uma Seção', ['Visão Geral', 'Análise da Partida', 'Análise do Jogador', 'Comparativo de Jogador'])

# Se a seção for "Visão Geral", exiba a imagem e o objetivo, sem filtros
if menu == 'Visão Geral':
    st.write("### Bem-vindo ao Dashboard de Análise de Partidas")
    
    image = Image.open("img/corner.png")
    st.image(image, caption='Corner Kick Analysis', use_column_width=True)
    
    # Definir o objetivo do dashboard
    st.write("""
    **Objetivo**: Este dashboard foi desenvolvido para fornecer insights detalhados sobre partidas de futebol, utilizando dados fornecidos pela biblioteca StatsBombPy.

    **Perguntas que o dashboard responde:**
    1. Qual é o comparativo das estatísticas entre os times?
    2. Como foram os desempenhos individuais dos jogadores em termos de passes e chutes?
    3. Como os jogadores de um time se comparam em termos de eventos, como passes, chutes, e desarmes, em uma partida?
    4. Quais são as estatísticas detalhadas de eventos dentro de um intervalo de tempo específico na partida?

    **Exploração Visual**: Use as opções no menu lateral para navegar por diferentes análises.
    """)

# Se a seção não for "Visão Geral", exiba os filtros apropriados
else:
    # Lógica combinada para filtrar por competição, temporada e partida
    competitions_df = get_competitions()
    competition_name = st.sidebar.selectbox('Selecione uma Competição', competitions_df['competition_name'])
    competition_id = competitions_df[competitions_df['competition_name'] == competition_name]['competition_id'].values[0]

    seasons_df = get_seasons(competition_id)
    season_name = st.sidebar.selectbox('Selecione uma Temporada', seasons_df['season_name'])
    season_id = seasons_df[seasons_df['season_name'] == season_name]['season_id'].values[0]

    matches_df = get_matches(competition_id, season_id)
    match_selection = st.sidebar.selectbox('Selecione uma Partida', matches_df.apply(lambda x: f"{x['home_team']} vs {x['away_team']} - {x['kick_off']}", axis=1))
    match_id = matches_df[matches_df.apply(lambda x: f"{x['home_team']} vs {x['away_team']} - {x['kick_off']}", axis=1) == match_selection]['match_id'].values[0]
    home_team = matches_df[matches_df['match_id'] == match_id]['home_team'].values[0]
    away_team = matches_df[matches_df['match_id'] == match_id]['away_team'].values[0]
    home_score = matches_df[matches_df['match_id'] == match_id]['home_score'].values[0]
    away_score = matches_df[matches_df['match_id'] == match_id]['away_score'].values[0]

    stats_home, stats_away, events_df = get_match_stats(match_id)

    if menu == 'Análise da Partida':
        # Exibir placar da partida
        st.write(f"### Placar: {home_team} {home_score} - {away_score} {away_team}")

        # Exibir comparativo de estatísticas por clube em forma de tabela
        display_comparison_table(stats_home, stats_away, home_team, away_team)

        # Exibir DataFrame com os eventos da partida logo abaixo da tabela
        st.write("### Eventos da Partida")
        st.dataframe(events_df[['type', 'team', 'player', 'minute', 'location']])

        # Download dos dados filtrados por clube
        st.write("### Download dos Dados Filtrados por Clube")
        download_data(events_df, home_team)
        download_data(events_df, away_team)

    elif menu == 'Análise do Jogador':
        # Exibir placar da partida na seção de visualizações
        st.write(f"### Placar: {home_team} {home_score} - {away_score} {away_team}")

        # Filtro adicional de jogador apenas na opção "Análise do Jogador"
        player_name = st.sidebar.selectbox('Selecione um Jogador', get_players(events_df))

        # Mapa de Passes com mapa de calor e seleção de jogador
        st.write("### Mapa de Passes")
        plot_pass_map(events_df, player_name)

        # Mapa de Chutes com seleção de jogador
        st.write("### Mapa de Chutes")
        plot_shot_map(events_df, player_name)

    elif menu == 'Comparativo de Jogador':
        # Seção de comparação de jogadores
        st.write("### Comparativo de Jogador")

        # Selecionar a quantidade de eventos a serem exibidos
        event_count = st.slider("Quantidade de Eventos a Exibir", min_value=1, max_value=50, value=10)

        # Escolher o intervalo de tempo de uma partida
        start_time = st.number_input("Minuto Inicial", min_value=0, max_value=90, value=0)
        end_time = st.number_input("Minuto Final", min_value=0, max_value=90, value=90)

        # Escolher dois jogadores para comparação
        player1 = st.selectbox("Selecione o Primeiro Jogador para Comparação", get_players(events_df))
        player2 = st.selectbox("Selecione o Segundo Jogador para Comparação", get_players(events_df))

        if st.button("Comparar Jogadores"):
            st.write(f"Comparando {player1} com {player2} de {start_time}' a {end_time}'")
            filtered_events_player1 = events_df[(events_df['player'] == player1) & (events_df['minute'] >= start_time) & (events_df['minute'] <= end_time)]
            filtered_events_player2 = events_df[(events_df['player'] == player2) & (events_df['minute'] >= start_time) & (events_df['minute'] <= end_time)]
            
            st.write(f"Eventos de {player1}:")
            st.dataframe(filtered_events_player1.head(event_count)[['type', 'minute', 'location']])
            
            st.write(f"Eventos de {player2}:")
            st.dataframe(filtered_events_player2.head(event_count)[['type', 'minute', 'location']])
