import spotipy
import os
import urllib
import pafy
import shelve
import threading
import sys
import argparse
import webbrowser
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from tqdm import tqdm
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import json
import concurrent.futures
try:
    from .downloader_functions import *
except ImportError:
    from downloader_functions import *
from bs4 import BeautifulSoup

# Global variables
downloads_started = False
downloading_lock = threading.Lock()
currently_downloading = []

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def get_spotify_client():
    config = load_config()
    client_id = config.get('spotify', {}).get('client_id')
    client_secret = config.get('spotify', {}).get('client_secret')
    if not client_id or not client_secret:
        return None
    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_downloaded_songs(playlist_name):
    playlist_dir = os.path.join(PROJECT_ROOT, playlist_name)
    if not os.path.exists(playlist_dir):
        return set()
    
    downloaded = set()
    for file in os.listdir(playlist_dir):
        if file.endswith('.mp3'):
            # Remove .mp3 extension and add to set
            downloaded.add(os.path.splitext(file)[0])
    return downloaded

def download_song(track, playlist_name):
    try:
        # Get track info
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        song_id = f"{track_name} - {artist_name}"
        
        # Create playlist directory if it doesn't exist
        playlist_dir = os.path.join(PROJECT_ROOT, playlist_name)
        os.makedirs(playlist_dir, exist_ok=True)
        
        # Use spotdl command line
        import subprocess
        
        # Construct the search query
        search_query = f"{track_name} {artist_name}"
        
        # Run spotdl command
        result = subprocess.run(
            ['spotdl', '--output', playlist_dir, search_query],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"spotdl failed: {result.stderr}")
            
        return True
        
    except Exception as e:
        print(f"Error downloading {song_id}: {str(e)}", file=sys.stderr)
        return False

def thread_download(song, progress_bar, folder_name):
    global downloads_started
    
    with downloading_lock:
        currently_downloading.append(song.name)
        # Update progress bar description with current downloads
        current_desc = f"Downloading: {', '.join(currently_downloading[:3])}"
        if len(currently_downloading) > 3:
            current_desc += f" (+{len(currently_downloading)-3} more)"
        progress_bar.set_description(current_desc)
        progress_bar.refresh()  # Force refresh the progress bar
        
        # Start the timer on first actual download
        if not downloads_started:
            downloads_started = True
            progress_bar.start_t = time.time()
    
    try:
        downloadSong(song, folder_name)
    finally:
        with downloading_lock:
            currently_downloading.remove(song.name)
            # Update progress bar description
            if currently_downloading:
                current_desc = f"Downloading: {', '.join(currently_downloading[:3])}"
                if len(currently_downloading) > 3:
                    current_desc += f" (+{len(currently_downloading)-3} more)"
                progress_bar.set_description(current_desc)
            else:
                progress_bar.set_description("Processing Songs")
            progress_bar.refresh()  # Force refresh the progress bar
        
        progress_bar.update(1)
        progress_bar.refresh()  # Force refresh after update

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m src.core.playlist_downloader <playlist_url>")
        sys.exit(1)
    
    playlist_url = sys.argv[1]
    
    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    try:
        # Initialize Spotify client
        sp = get_spotify_client()
        if not sp:
            print("Error: Spotify credentials not configured")
            sys.exit(1)
        
        print("Fetching playlist metadata from Spotify...")
        # Get playlist ID from URL
        if 'https://open.spotify.com/playlist/' in playlist_url:
            playlist_id = playlist_url.split('playlist/')[1].split('?')[0]
            playlist = sp.playlist(playlist_id)
        else:
            playlist_user = playlist_url.split('user/')[1].split('/')[0]
            playlist_id = playlist_url.split('playlist/')[1].split('?')[0]
            playlist = sp.user_playlist(playlist_user, playlist_id)
        print(f"Fetched playlist metadata: {playlist['name']} (ID: {playlist['id']})")
        print("Fetching all tracks in playlist (this may take a while for large playlists)...")
        # Fetch all tracks with progress if paginated
        tracks = []
        results = playlist['tracks']
        total_tracks = results['total']
        fetched = 0
        while results:
            items = results['items']
            tracks.extend(items)
            fetched += len(items)
            print(f"  - Fetched {fetched}/{total_tracks} tracks...")
            if results.get('next'):
                results = sp.next(results)
            else:
                break
        print(f"All tracks fetched: {len(tracks)} total.")
        playlist_name = playlist['name']
        # Get total number of tracks (already set above)
        print(f"Found {total_tracks} tracks in playlist: {playlist_name}")
        print("Checking already downloaded songs...")
        downloaded_songs = get_downloaded_songs(playlist_name)
        
        # Download songs in parallel (up to 5 at a time)
        with tqdm(total=total_tracks, desc="Processing Songs", unit="song", 
                 bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                 mininterval=0.1, file=sys.stderr) as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for track in tracks:
                    if not track['track']:
                        pbar.update(1)
                        continue
                    track_name = track['track']['name']
                    artist_name = track['track']['artists'][0]['name']
                    song_id = f"{track_name} - {artist_name}"
                    if song_id in downloaded_songs:
                        pbar.update(1)
                        continue
                    # Submit download task
                    futures.append(executor.submit(download_song, track['track'], playlist_name))
                # As each download finishes, update the progress bar
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as e:
                        print(f"Error downloading song: {e}", file=sys.stderr)
                    pbar.update(1)
        print(f"Finished downloading playlist: {playlist_name}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
