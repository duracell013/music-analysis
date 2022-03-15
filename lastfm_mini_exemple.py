import requests
import json
import pandas as pd
import os

LASTFM_KEY = os.environ.get('LASTFM_KEY')
LASTFM_URL = 'http://ws.audioscrobbler.com/2.0/'
LASTFM_USER = 'Duracell013'

EXPORT_FILE = 'scrobbles.pkl'

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
        raise ValueError(r.json()['error'])
    return r


def jprint(obj):
    # create a formatted string of the Python JSON object
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)


if __name__ == '__main__':
    df = pd.read_pickle(EXPORT_FILE)
    print(df.head())
    
    #results = get_scrobbles(LASTFM_USER)
    #jprint(results.json())
