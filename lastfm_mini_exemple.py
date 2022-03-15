import requests
import json

LASTFM_KEY = '105d6826d54097eaed281cbfb9930456'
LASTFM_URL = 'http://ws.audioscrobbler.com/2.0/'
LASTFM_USER = 'Duracell013'

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
    results = get_scrobbles(LASTFM_USER)
    jprint(results.json())
