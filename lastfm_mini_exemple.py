import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

LASTFM_KEY = os.environ.get('LASTFM_KEY')
LASTFM_URL = 'http://ws.audioscrobbler.com/2.0/'
LASTFM_USER = 'Duracell013'
FEATURES = ['acousticness', 'danceability', 'energy', 'instrumentalness',
            'key', 'liveness', 'loudness', 'mode', 'speechiness', 'tempo',
            'time_signature', 'valence']

EXPORT_FILE = 'scrobbles.pkl'

REFRESH = True

def get_scrobbles(user, limit=200, page=1, extended=0):
    params = {'method': 'user.getRecentTracks',
              'limit': limit,
              'user': user,
              'page': page,
              'extended': extended,
              'api_key': LASTFM_KEY,
              'format': 'json'}
    r = requests.post(LASTFM_URL, params=params)
    if not r.ok:
        raise ValueError(r.json()['error'], r.json()['message'])
    return r


def jprint(obj):
    # create a formatted string of the Python JSON object
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
        #track_uri, artist_uris = find_uri(artist, album, track)
        tags = get_tags(track, artist)
        dic = {'artist': artist,
               'album': album,
               'track': track,
               #'uri': track_uri,
               'tags': tags}
##        if track_uri:
##            f = features(track_uri)
##            if f:
##                dic.update(f)
##            g = genres(artist_uris)
##            if g:
##                dic.update({'genres': g})
        df.loc[date] = dic
    return df, break_flag

if __name__ == '__main__':
    
    if not REFRESH:
        print('Reading pickle file...', end='')
        df = pd.read_pickle(EXPORT_FILE)
        last_date = df.index.max()
        print(f' done (last entry = {last_date})')
    else:
        cols = ['artist', 'album', 'track', 'uri', 'tags', 'genres']
        cols.extend(FEATURES)
        df = pd.DataFrame(columns=cols)
        last_date = datetime.min
    page = 1
    n_pages = np.Inf
    break_flag = False
    print(f'Fetching scrobbles (n_pages = {n_pages})...', end=' ')
    while (page <= n_pages) and not break_flag:
        r = get_scrobbles(LASTFM_USER, page=page, limit=50)
        n_pages = int(r.json()['recenttracks']['@attr']['totalPages'])
        df, break_flag = fill_data(df, r, last_date)
        page += 1
        print(f'{page}', end=',')
    df.sort_index(inplace=True)
    df.to_pickle(EXPORT_FILE, protocol=4)
    print(' done')
