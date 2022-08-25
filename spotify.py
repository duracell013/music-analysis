# Spotify class

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd


class Spotify:

    def __init__(self):
        '''Connect to Spotify API'''
        print('Connecting to spotipy...', end=' ')
        self.api = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(),
                                   requests_timeout=10, retries=10)
        print('[OK]')

    def find_uri(self, artist, album, title):
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
        results = self.api.search(q=query, type='track')
        if results['tracks']['total'] == 0:
            results = self.api.search(q=f'track:{title} artist:{artist}',
                                      type='track')
        if results['tracks']['total'] == 0:
            return None, None
        else:
            track_uri = results['tracks']['items'][0]['uri']
            artist_uris = []
            for a in results['tracks']['items'][0]['artists']:
                artist_uris.append(a['uri'])
            return track_uri, artist_uris

    def features(self, uri):
        '''Get track features from Spotify'''
        r = self.api.audio_features(uri)
        r = r[0]
        if r:
            features = {k: r[k] for k in FEATURES if k in r}
        else:
            features = None
        return features

    def genres(self, artist_uris):
        '''Get artists genres from Spotify'''
        genres = []
        for uri in artist_uris:
            results = self.api.artist(uri)
            genres.extend(results['genres'])
        return genres

    def playlist_tracks(self, playlist_id):
        df = pd.DataFrame(columns=['artist', 'album', 'track'])
        limit = 100
        offset = 0
        tracks = self.api.playlist_tracks(playlist_id, offset=offset, limit=limit)
        total = tracks['total']
        while offset < total:
            tracks = self.api.playlist_tracks(playlist_id,
                                              offset=offset, limit=limit)
            for i, t in enumerate(tracks['items']):
                df.loc[i+offset] = track_info(t)
            offset += limit
        return df


def sanitize(string):
    '''Remove special characters from string to make HTTP query'''
    string = unidecode(string)
    chars = ['.', '&', '  ']
    for i in chars:
        string = string.replace(i, ' ')
    return string.strip()


def track_info(track):
    '''Format and return dictionnary with artists, track, and album'''
    artist = ', '.join([a['name'] for a in track['track']['artists']])
    dic = {'artist': artist,
           'track': track['track']['name'],
           'album': track['track']['album']['name']}
    return dic


if __name__ == '__main__':

    playlist_id = '0k5hJzzAvLllBUJYEJddJT'  # Gilles Peterson Worldwide Radio

    sp = Spotify()
    tracks = sp.playlist_tracks(playlist_id)
    print(tracks)
