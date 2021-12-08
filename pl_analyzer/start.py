import itertools
import networkx as nx
import spotipy
import pandas as pd
import matplotlib.pyplot as plt
from spotipy.oauth2 import SpotifyClientCredentials


def get_spotify_handler():
    # run like this with SPOTIPY_CLIENT_ID=... and SPOTIPY_CLIENT_SECRET=... env variables
    auth_manager = SpotifyClientCredentials()

    # ...or like this with hardcoded id and secret
    # client_id = "..."
    # client_secret = "..."
    # auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)

    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp


def load_playlist(playlist_uri: str, sp: object):
    # retrieve all items (max 100 per request)
    playlist = sp.playlist(playlist_uri)
    playlist_blocks = [sp.playlist_items(playlist_uri, offset=0)]
    offset = len(playlist_blocks[0]['items'])
    while offset < playlist['tracks']['total']:
        playlist_blocks.append(sp.playlist_items(playlist_uri, offset=offset))
        offset = len(playlist_blocks) * 100

    # concat to one list
    all_tracks = []
    for block in playlist_blocks:
        all_tracks.extend(block['items'])
    return all_tracks


def convert_to_df(playlist_list: str):
    # create dataframe
    artist_dict = []
    title_dict = []
    added_by_id_dict = []
    for entry in playlist_list:
        artist_dict.append(entry['track']['artists'][0]['name'])
        title_dict.append(entry['track']['name'])
        added_by_id_dict.append(entry['added_by']['id'])
    playlist_df = pd.DataFrame({'artist': artist_dict,
                                'title': title_dict,
                                'added_by_id': added_by_id_dict},
                               columns=['artist', 'title', 'added_by_id'])
    return playlist_df


def draw_graph(df_to_draw):
    # create adjacency matrix
    df_as_dummies = pd.get_dummies(df_to_draw, columns=['artist']).groupby('added_by_id', as_index=False).max()
    df_as_dummies.set_index('added_by_id', inplace=True)
    user_list = df_as_dummies.index
    common_elements_matrix = pd.DataFrame(data=[[[] for _ in range(len(user_list))]
                                                for _ in range(len(user_list))], columns=user_list, index=user_list)
    for artist, column in df_as_dummies.iteritems():
        indices_to_add = column[column > 0].index.values.tolist()
        # cut dummy prefix
        artist = artist[len('artist_'):]

        permutations = itertools.permutations(indices_to_add, 2)
        for i1, i2 in permutations:
            common_elements_matrix.loc[i1, i2].append(artist)

    # get adjacency mat by selecting amount of common elements as adjacency weight
    adjacency_mat = common_elements_matrix.applymap(lambda l: len(l))

    # create ugly ass graph
    plt.figure(figsize=(10, 8), dpi=100)
    # -- generate graph obj
    G = nx.from_pandas_adjacency(adjacency_mat)
    # -- calc node positions by some alg
    pos = nx.spring_layout(G)
    # -- draw shit
    nx.draw_networkx(G, pos=pos, with_labels=True, font_weight='bold')
    # -- create edge labels and draw them
    # edge_labels_amount = {(f, t): int(adjacency_mat.loc[f, t]) for t in user_list for f in user_list if int(adjacency_mat.loc[f, t]) > 0}
    edge_labels_list = {(f, t): common_elements_matrix.loc[f, t] for t in user_list for f in user_list if
                        common_elements_matrix.loc[f, t]}
    edge_labels_concatenated = {idx: ','.join(l) for idx, l in edge_labels_list.items()}
    nx.draw_networkx_edge_labels(G, pos=pos, edge_labels=edge_labels_concatenated)

    plt.show()


def analyze_playlist():
    sp = get_spotify_handler()
    # the playlist link
    playlist_uri = "https://open.spotify.com/playlist/69ypGzKMvftTRFcs5uuyT6?si=a1d275f78af94b54"
    pl_list = load_playlist(playlist_uri, sp)
    playlist_dataframe = convert_to_df(pl_list)
    # get unique artists per user
    unique_artist_per_user = playlist_dataframe.drop_duplicates(['artist', 'added_by_id']) \
        .drop('title', axis=1).sort_values('artist')
    # filter to artists with multiple users
    artists_with_multiple_users = unique_artist_per_user[unique_artist_per_user.duplicated('artist', keep=False)]

    # df_dup_song = df[df.duplicated('title', keep=False)].sort_values('title')
    draw_graph(artists_with_multiple_users)
    return playlist_dataframe, artists_with_multiple_users


if __name__ == '__main__':
    df, dfa = analyze_playlist()

