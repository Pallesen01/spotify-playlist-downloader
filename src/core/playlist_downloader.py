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

def get_download_directory():
    config = load_config()
    return config.get('download_directory', PROJECT_ROOT)

def get_downloaded_songs(playlist_name):
    download_dir = get_download_directory()
    playlist_dir = os.path.join(download_dir, playlist_name)
    if not os.path.exists(playlist_dir):
        return set()
    downloaded = set()
    for file in os.listdir(playlist_dir):
        if file.endswith('.mp3'):
            downloaded.add(os.path.splitext(file)[0])
    return downloaded

def download_song(track, playlist_name):
    try:
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        song_id = f"{track_name} - {artist_name}"
        download_dir = get_download_directory()
        playlist_dir = os.path.join(download_dir, playlist_name)
        os.makedirs(playlist_dir, exist_ok=True)
        song_obj = Song(track, playlist_name)
        # Patch the Song object to use the correct folder
        song_obj.folder_name = os.path.join(download_dir, playlist_name, song_obj.artist_folder, song_obj.album_folder_with_year)
        downloadSong(song_obj, quiet=False)
        if song_obj.file and os.path.exists(song_obj.file):
            print(f"Finished: {song_id}")
            return True
        else:
            print(f"Error downloading {song_id} with custom logic", flush=True)
            return False
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

def write_m3u8_playlist(playlist_name, download_dir):
    playlists_dir = os.path.join(download_dir, '1 - Playlists')
    os.makedirs(playlists_dir, exist_ok=True)
    m3u8_path = os.path.join(playlists_dir, f'{playlist_name}.m3u8')
    playlist_folder = os.path.join(download_dir, playlist_name)
    mp3_files = []
    for root, _, files in os.walk(playlist_folder):
        for file in files:
            if file.endswith('.mp3'):
                mp3_files.append(os.path.relpath(os.path.join(root, file), playlists_dir))
    with open(m3u8_path, 'w', encoding='utf-8') as f:
        for rel_path in sorted(mp3_files):
            f.write(rel_path + '\n')

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m src.core.playlist_downloader <playlist_url>")
        sys.exit(1)
    
    playlist_url = sys.argv[1]
    
    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    print("[DEBUG] Starting download process", flush=True)
    print("[DEBUG] Starting download process", file=sys.stderr, flush=True)
    
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
        print(f"Found {total_tracks} tracks in playlist: {playlist_name}")
        print("Checking already downloaded songs...")
        downloaded_songs = get_downloaded_songs(playlist_name)
        download_dir = get_download_directory()
        # Download songs in parallel (up to 8 at a time)
        with tqdm(total=total_tracks, desc="Processing Songs", unit="song", 
                 bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                 mininterval=0.1, file=sys.stderr) as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
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
                    futures.append(executor.submit(download_song, track['track'], playlist_name))
                for future in concurrent.futures.as_completed(futures):
                    pbar.update(1)
        # Always update the m3u8 playlist after downloads
        write_m3u8_playlist(playlist_name, download_dir)
        print(f"Updated m3u8 playlist for {playlist_name}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
