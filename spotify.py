# Spotify wrapper

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def create_api():
    '''Connect to Spotify API'''
    print('Connecting to spotipy...', end=' ')
    api = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(),
                          requests_timeout=10, retries=10)
    print('[OK]')
    return api

def find_uri(api, artist, album, title):
    '''Find Spotify track and artists URI'''
    if '(feat.' in title:
        title = title[:title.find('(feat.')]
    artist = sanitize(artist)
    album = sanitize(album)
    title = sanitize(title)
    query = f'track:{title} artist:{artist} album:{album}'
    if len(query) > 100:
        query = f'track:{title} artist:{artist}'
    if len(query) > 100:
        query = f'track:{title}'
    results = api.search(q=query, type='track')
    if results['tracks']['total'] == 0:
        results = api.search(q=f'track:{title} artist:{artist}', type='track')
    if results['tracks']['total'] == 0:
        return None, None
    else:
        track_uri = results['tracks']['items'][0]['uri']
        artist_uris = []
        for a in results['tracks']['items'][0]['artists']:
            artist_uris.append(a['uri'])
        return track_uri, artist_uris

def features(api, uri):
    '''Get track features from Spotify'''
    r = api.audio_features(uri)
    r = r[0]
    if r:
        features = {k: r[k] for k in FEATURES if k in r}
    else:
        features = None
    return features


def genres(api, artist_uris):
    '''Get artists genres from Spotify'''
    genres = []
    for uri in artist_uris:
        results = api.artist(uri)
        genres.extend(results['genres'])
    return genres