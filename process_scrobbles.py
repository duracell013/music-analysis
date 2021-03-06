import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from time import sleep

LASTFM_KEY = os.environ.get('LASTFM_KEY')
LASTFM_URL = 'http://ws.audioscrobbler.com/2.0/'
LASTFM_USER = 'Duracell013'
FEATURES = ['acousticness', 'danceability', 'energy', 'instrumentalness',
            'key', 'liveness', 'loudness', 'mode', 'speechiness', 'tempo',
            'time_signature', 'valence']

EXPORT_FILE = 'scrobbles.pkl'

REFRESH = False

def connect_spotipy():
    '''Connect to Spotify API'''
    print('Connecting to spotipy...', end=' ')
    api = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(),
                          requests_timeout=10, retries=10)
    print('[OK]')
    return api

def find_uri(artist, album, title):
    '''Find Spotify track and artists URI'''
    artist = artist.replace('.', ' ').replace('&', ' ')
    album = album.replace('.', ' ').replace('&', ' ')
    title = title.replace('.', ' ').replace('&', ' ')
    if '(feat.' in title:
        title = title[:title.find('(feat.')]
    results = sp.search(q=f'track:{title} artist:{artist} album:{album}',
                        type='track')
    if results['tracks']['total'] == 0:
        results = sp.search(q=f'track:{title} artist:{artist}', type='track')
    if results['tracks']['total'] == 0:
        return None, None
    else:
        track_uri = results['tracks']['items'][0]['uri']
        artist_uris = []
        for a in results['tracks']['items'][0]['artists']:
            artist_uris.append(a['uri'])
        return track_uri, artist_uris

def features(uri):
    '''Get track features from Spotify'''
    r = sp.audio_features(uri)
    r = r[0]
    if r:
        features = {k: r[k] for k in FEATURES if k in r}
    else:
        features = None
    return features


def genres(artist_uris):
    '''Get artists genres from Spotify'''
    genres = []
    for uri in artist_uris:
        results = sp.artist(uri)
        genres.extend(results['genres'])
    return genres

def get_scrobbles(limit=200, page=1, extended=0):
    '''Get Last.fm scrobbles'''
    params = {'method': 'user.getRecentTracks',
              'limit': limit,
              'user': LASTFM_USER,
              'page': page,
              'extended': extended,
              'api_key': LASTFM_KEY,
              'format': 'json'}
    tries = 5
    while tries > 0:
        r = requests.post(LASTFM_URL, params=params)
        if r.ok:
            return r
        else:
            print(f'Try {6-tries} - ERROR',r.json()['error'], r.json()['message'])
            tries -= 1
            sleep(2)
    raise ValueError(r.json()['error'], r.json()['message'])


def jprint(obj):
    '''Create a formatted string of the Python JSON object'''
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)


def get_tags(track, artist):
    params = {'method': 'track.getTopTags',
              'artist': artist,
              'track': track,
              'user': LASTFM_USER,
              'api_key': LASTFM_KEY,
              'format': 'json'}
    r = requests.post(LASTFM_URL, params=params)
    tags = []
    if 'toptags' in r.json():
        for i, tag in enumerate(r.json()['toptags']['tag']):
            # TODO: find a better way to handle this
            if i > 4:
                break
            #if tag['count'] > 10:
            tags.append(tag['name'])
    return tags


def fill_data(df, results, last_date):
    break_flag = False
    for t in results.json()['recenttracks']['track']:

        # Skip if date doesn't exist (currently playing)
        if 'date' not in t:
            continue

        # Fill data
        date = pd.to_datetime(t['date']['uts'], unit='s')
        if date <= last_date:
            break_flag = True
            break
        artist = t['artist']['#text']
        album = t['album']['#text']
        track = t['name']
        track_uri, artist_uris = find_uri(artist, album, track)
        tags = get_tags(track, artist)
        dic = {'artist': artist,
               'album': album,
               'track': track,
               'uri': track_uri,
               'tags': tags}
        if track_uri:
            f = features(track_uri)
            if f:
                dic.update(f)
            g = genres(artist_uris)
            if g:
                dic.update({'genres': g})
        df.loc[date] = dic
    return df, break_flag

if __name__ == '__main__':
            
    # Connect to spotify
    sp = connect_spotipy()

    if not REFRESH:
        print('Reading pickle file...', end=' ')
        df = pd.read_pickle(EXPORT_FILE)
        last_date = df.index.max()
        print(f'[OK] (last entry = {last_date})')
    else:
        cols = ['artist', 'album', 'track', 'uri', 'tags', 'genres']
        cols.extend(FEATURES)
        df = pd.DataFrame(columns=cols)
        last_date = datetime.min
    page = 1
    n_pages = np.Inf
    break_flag = False
    print('Fetching scrobbles...', end=' ')
    while (page <= n_pages) and not break_flag:
        r = get_scrobbles(page=page, limit=50)
        n_pages = int(r.json()['recenttracks']['@attr']['totalPages'])
        if page == 1:
             print(f'{n_pages} pages in total -', end=' ')
        df, break_flag = fill_data(df, r, last_date)
        print(f'{page}', end=',')
        page += 1
    df.sort_index(inplace=True)
    df.to_pickle(EXPORT_FILE, protocol=4)
    print(' done')
