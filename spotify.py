# Spotify wrapper

def create_api():
    '''Connect to Spotify API'''
    print('Connecting to spotipy...', end=' ')
    api = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(),
                          requests_timeout=10, retries=10)
    print('[OK]')
    return api
