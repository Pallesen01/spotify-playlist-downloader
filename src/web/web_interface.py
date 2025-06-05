import os
import json
import threading
import time
import subprocess
import sys
from flask import Flask, request, redirect, render_template

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

downloader_thread = None

def downloader_loop():
    while True:
        playlists = load_playlists()
        for url in playlists:
            # Add project root to Python path
            sys.path.insert(0, PROJECT_ROOT)
            # Run as module instead of script
            subprocess.run([sys.executable, '-m', 'src.core.playlist_downloader', url])
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
    playlists = load_playlists()
    if url and url not in playlists:
        playlists.append(url)
        save_playlists(playlists)
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete_playlist():
    url = request.form.get('url')
    playlists = load_playlists()
    if url in playlists:
        playlists.remove(url)
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