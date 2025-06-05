import os
import json
import threading
import time
import subprocess
import sys
from flask import Flask, request, redirect, render_template
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAYLIST_FILE = os.path.join(PROJECT_ROOT, 'playlists.json')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.json')
INTERVAL = 3600  # 1 hour

app = Flask(__name__)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def load_playlists():
    if os.path.exists(PLAYLIST_FILE):
        with open(PLAYLIST_FILE, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_playlists(playlists):
    with open(PLAYLIST_FILE, 'w') as f:
        json.dump(playlists, f)

def get_spotify_client():
    config = load_config()
    client_id = config.get('spotify', {}).get('client_id')
    client_secret = config.get('spotify', {}).get('client_secret')
    if not client_id or not client_secret:
        return None
    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_playlist_info(url):
    sp = get_spotify_client()
    if not sp:
        return None
    
    try:
        if 'https://open.spotify.com/playlist/' in url:
            playlist_id = url.split('playlist/')[1].split('?')[0]
            playlist = sp.playlist(playlist_id)
        else:
            playlist_user = url.split('user/')[1].split('/')[0]
            playlist_id = url.split('playlist/')[1].split('?')[0]
            playlist = sp.user_playlist(playlist_user, playlist_id)
        
        return {
            'name': playlist['name'],
            'track_count': playlist['tracks']['total'],
            'url': url
        }
    except Exception:
        return None

downloader_thread = None

def downloader_loop():
    while True:
        playlists = load_playlists()
        for playlist in playlists:
            # Add project root to Python path
            sys.path.insert(0, PROJECT_ROOT)
            # Run as module instead of script
            subprocess.run([sys.executable, '-m', 'src.core.playlist_downloader', playlist['url']])
        time.sleep(INTERVAL)

@app.route('/')
def index():
    playlists = load_playlists()
    config = load_config()
    has_credentials = bool(config.get('spotify', {}).get('client_id') and config.get('spotify', {}).get('client_secret'))
    return render_template('index.html', playlists=playlists, has_credentials=has_credentials)

@app.route('/add', methods=['POST'])
def add_playlist():
    url = request.form.get('url')
    if not url:
        return redirect('/')
    
    playlist_info = get_playlist_info(url)
    if not playlist_info:
        return redirect('/')
    
    playlists = load_playlists()
    # Check if playlist URL already exists
    if not any(p['url'] == url for p in playlists):
        playlists.append(playlist_info)
        save_playlists(playlists)
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete_playlist():
    url = request.form.get('url')
    playlists = load_playlists()
    playlists = [p for p in playlists if p['url'] != url]
    save_playlists(playlists)
    return redirect('/')

@app.route('/start')
def start_downloader():
    global downloader_thread
    if downloader_thread and downloader_thread.is_alive():
        return redirect('/')
    downloader_thread = threading.Thread(target=downloader_loop, daemon=True)
    downloader_thread.start()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 