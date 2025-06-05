import spotipy
import os
import urllib
import pafy
import shelve
import threading
import sys
import argparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from tqdm import tqdm
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from .downloader_functions import *
from bs4 import BeautifulSoup

parser = argparse.ArgumentParser(description="Download songs from a Spotify playlist")
parser.add_argument("playlist_url", help="Spotify playlist URL or URI")
parser.add_argument("--limit", "-l", type=int, help="Only download the first N songs", default=None)
parser.add_argument("--user-auth", action="store_true",
                    help="Authenticate via web browser instead of client credentials")
args = parser.parse_args()

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
shelveFile = shelve.open(os.path.join(PROJECT_ROOT, 'spotify_data'))

client_id = shelveFile.get('SPOTIPY_CLIENT_ID', os.environ.get('SPOTIPY_CLIENT_ID'))
client_secret = shelveFile.get('SPOTIPY_CLIENT_SECRET', os.environ.get('SPOTIPY_CLIENT_SECRET'))

if args.user_auth:
    if not client_id:
        client_id = input("Enter Client ID: ")
        shelveFile['SPOTIPY_CLIENT_ID'] = client_id
    if not client_secret:
        client_secret = input("Enter Client Secret: ")
        shelveFile['SPOTIPY_CLIENT_SECRET'] = client_secret

    oauth = SpotifyOAuth(client_id=client_id,
                         client_secret=client_secret,
                         redirect_uri='http://127.0.0.1:8888/callback',
                         scope='playlist-read-private playlist-read-collaborative',
                         cache_path=os.path.join(PROJECT_ROOT, 'spotify_token_cache'),
                         open_browser=True)
    token_info = oauth.get_cached_token()
    if not token_info:
        # Set up callback server
        auth_code = [None]  # Use list to avoid nonlocal issues
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urlparse(self.path)
                if parsed_url.path == '/callback':
                    query_params = parse_qs(parsed_url.query)
                    if 'code' in query_params:
                        auth_code[0] = query_params['code'][0]
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Authorization successful!</h1><p>You can close this window and return to the application.</p></body></html>')
                    else:
                        self.send_response(400)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'<html><body><h1>Authorization failed!</h1><p>No authorization code received.</p></body></html>')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress server logs
        
        # Start local server
        server = HTTPServer(('127.0.0.1', 8888), CallbackHandler)
        server.timeout = 60  # 60 second timeout
        
        print("Starting local server to handle Spotify callback...")
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.daemon = True
        server_thread.start()
        
        # Open browser for authorization
        auth_url = oauth.get_authorize_url()
        print(f"Opening browser for Spotify authorization...")
        webbrowser.open(auth_url)
        
        # Wait for callback
        print("Waiting for authorization... (will timeout in 60 seconds)")
        print("If you see an error page, make sure you've added 'http://127.0.0.1:8888/callback' to your Spotify app's redirect URIs")
        server_thread.join(timeout=60)
        server.server_close()
        
        if auth_code[0]:
            try:
                token_info = oauth.get_access_token(auth_code[0], as_dict=False)
                # Convert to dict format if it's a string
                if isinstance(token_info, str):
                    token_info = {'access_token': token_info}
                print("Authorization successful!")
            except Exception as e:
                print(f"Error getting access token: {e}")
                sys.exit(1)
        else:
            print("\nAuthorization timed out or failed.")
            print("This usually means the redirect URI isn't configured in your Spotify app.")
            print("Please add 'http://127.0.0.1:8888/callback' to your app's redirect URIs at:")
            print("https://developer.spotify.com/dashboard")
            print("\nAlternatively, you can run without --user-auth to use client credentials instead.")
            sys.exit(1)
    sp = spotipy.Spotify(auth=token_info['access_token'])
else:
    try:
        client_credentials_manager = SpotifyClientCredentials(client_id=client_id,
                                                             client_secret=client_secret)
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    except Exception:
        client_id = input("Enter Client ID: ")
        client_secret = input("Enter Client Secret: ")
        shelveFile['SPOTIPY_CLIENT_ID'] = client_id
        shelveFile['SPOTIPY_CLIENT_SECRET'] = client_secret
        client_credentials_manager = SpotifyClientCredentials(client_id=client_id,
                                                             client_secret=client_secret)
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

shelveFile.close()

#TEMP Test Link
#test_link = "https://open.spotify.com/user/sparks_of_fire/playlist/4ScHDVxjzDpBFOyyKdWw6G?si=R_AFDhOJTYymeBpjs96jhw"

#set variables
threadList = []  # stores all threads
downloadQueue = []  # songs to be downloaded

playlist_url = args.playlist_url
limit = args.limit

songs, folder_name = getTracks(playlist_url, sp, limit=limit)
os.makedirs(folder_name, exist_ok=True)

print("Checking already downloaded songs...")
#get URIs of downloaded songs
URIs = []
playlistFolderURIs = []
for file in os.listdir(folder_name):
    file_path = os.path.join(folder_name, file)
    if os.path.isfile(file_path):
        playlistFolderURIs.append(getUri(file_path))


#Don't download dupe songs from other folders
URIs.extend(playlistFolderURIs)

for folder in os.listdir():
    if folder == folder_name or folder.startswith('.'):
        continue
    if not os.path.isdir(folder):
        continue
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        if os.path.isfile(file_path):
            URIs.append(getUri(file_path))

for song in songs:
    if song.uri in URIs:
        pass  # Skip already downloaded songs silently
    else:
        downloadQueue.append(song)


# Progress bar for all songs (downloaded + to download)
progress_bar = tqdm(total=len(songs), desc="Processing Songs", unit="song", 
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')

# Update progress for already downloaded songs (without affecting rate calculation)
already_downloaded = len(songs) - len(downloadQueue)
if already_downloaded > 0:
    # Set initial progress without starting the timer
    progress_bar.n = already_downloaded
    progress_bar.refresh()

# Flag to track when downloads actually start
downloads_started = False

# Track currently downloading songs
import threading
downloading_lock = threading.Lock()
currently_downloading = []

def thread_download(song):
    global downloads_started
    
    with downloading_lock:
        currently_downloading.append(song.name)
        # Update progress bar description with current downloads
        current_desc = f"Downloading: {', '.join(currently_downloading[:3])}"
        if len(currently_downloading) > 3:
            current_desc += f" (+{len(currently_downloading)-3} more)"
        progress_bar.set_description(current_desc)
        
        # Start the timer on first actual download
        if not downloads_started:
            downloads_started = True
            progress_bar.start_t = progress_bar._time()
    
    downloadSong(song, quiet=True)


    
    with downloading_lock:
        currently_downloading.remove(song.name)
        progress_bar.update(1)
        # Update description after completion
        if currently_downloading:
            current_desc = f"Downloading: {', '.join(currently_downloading[:3])}"
            if len(currently_downloading) > 3:
                current_desc += f" (+{len(currently_downloading)-3} more)"
            progress_bar.set_description(current_desc)
        else:
            progress_bar.set_description("Processing Songs")

#While there are songs in download queue download songs
while len(downloadQueue) > 0:
    if len(threadList) <= 4:
        threadObj = threading.Thread(target=thread_download, args=[downloadQueue.pop(0)])
        threadObj.handled = False
        threadList.append(threadObj)
        threadObj.start()

    for t in threadList:
        if not t.is_alive():
            #print("Thread Done")
            t.handled = True
    threadList = [t for t in threadList if not t.handled]

#Wait for all thread to finish
for t in threadList:
    t.join()

progress_bar.set_description("Finalizing...")
progress_bar.close()

print("Deleting Removed Songs")
delRemoved(playlistFolderURIs, songs, folder_name)
print("Done")
