import os
import json
import threading
import time
import subprocess
import sys
from flask import Flask, request, redirect, render_template, jsonify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import datetime

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAYLIST_FILE = os.path.join(PROJECT_ROOT, 'playlists.json')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.json')
INTERVAL = 3600  # 1 hour
next_sync_time = None  # Global for next sync time

app = Flask(__name__)

# Global variables for downloader state
downloader_thread = None
downloader_running = False
current_progress = {
    'status': 'idle',  # idle, running, completed, error
    'current_playlist': None,
    'current_song': None,
    'total_songs': 0,
    'downloaded_songs': 0,
    'error': None,
    'stage': 'Idle.'
}
# Add a global for the current subprocess
current_downloader_process = None

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

def downloader_loop():
    global downloader_running, current_progress, current_downloader_process, next_sync_time
    while downloader_running:
        try:
            playlists = load_playlists()
            for playlist in playlists:
                if not downloader_running:
                    break
                current_progress['current_playlist'] = playlist['name']
                current_progress['status'] = 'running'
                current_progress['downloaded_songs'] = 0
                current_progress['total_songs'] = 0
                current_progress['stage'] = 'Initializing...'

                sys.path.insert(0, PROJECT_ROOT)

                # Start the downloader subprocess and store it globally
                process = subprocess.Popen(
                    [sys.executable, '-m', 'src.core.playlist_downloader', playlist['url']],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env={**os.environ, 'PYTHONUNBUFFERED': '1'}
                )
                current_downloader_process = process

                # Read output line by line
                while True:
                    stdout_line = process.stdout.readline()
                    stderr_line = process.stderr.readline()

                    if not downloader_running:
                        # If stopped, terminate the process
                        if process.poll() is None:
                            process.terminate()
                        break

                    if process.poll() is not None:
                        remaining_stdout, remaining_stderr = process.communicate()
                        if remaining_stdout:
                            print(f"Debug - Remaining stdout: {remaining_stdout}")
                        if remaining_stderr:
                            print(f"Debug - Remaining stderr: {remaining_stderr}")
                        break

                    # Process stdout
                    if stdout_line:
                        line = stdout_line.strip()
                        print(f"Debug - Stdout: {line}")
                        if 'Found' in line and 'tracks in playlist:' in line:
                            try:
                                total = int(line.split('Found')[1].split('tracks')[0].strip())
                                current_progress['total_songs'] = total
                                current_progress['stage'] = 'Fetched playlist info'
                            except Exception as e:
                                print(f"Error parsing total tracks: {e}")
                        elif 'Checking already downloaded songs' in line:
                            current_progress['stage'] = 'Checking already downloaded songs...'
                        elif line.startswith('Finished:'):
                            song_info = line.replace('Finished:', '').strip()
                            current_progress['current_song'] = song_info
                            current_progress['stage'] = f"Last finished: {song_info}"
                        elif 'Downloading:' in line:
                            song_info = line.replace('Downloading:', '').strip()
                            if ' - ' in song_info:
                                title, artist = song_info.split(' - ', 1)
                                current_progress['current_song'] = f"{title} by {artist}"
                            else:
                                current_progress['current_song'] = song_info
                            current_progress['stage'] = f"Downloading: {current_progress['current_song']}"
                        elif 'Finished downloading playlist:' in line:
                            current_progress['stage'] = 'Finished downloading playlist.'
                        elif 'Error' in line:
                            current_progress['stage'] = line

                    # Process stderr
                    if stderr_line:
                        line = stderr_line.strip()
                        print(f"Debug - Stderr: {line}")
                        if 'Processing Songs:' in line:
                            try:
                                # Example: Processing Songs:   3%|3         | 1/29 [00:21<10:05]
                                if '|' in line:
                                    parts = line.split('|')
                                    if len(parts) >= 3:
                                        progress = parts[2].strip()
                                        if '/' in progress:
                                            current, total = progress.split('/')
                                            current = current.strip()
                                            total = total.split()[0].strip()
                                            current_progress['downloaded_songs'] = int(current)
                                            current_progress['total_songs'] = int(total)
                                            current_progress['stage'] = f"Downloading songs... ({current}/{total})"
                                            print(f"Debug - Progress: {current}/{total}")
                            except Exception as e:
                                print(f"Error parsing progress: {e}")
                        elif 'Finished downloading playlist:' in line:
                            current_progress['downloaded_songs'] = current_progress['total_songs']
                            current_progress['stage'] = 'Finished downloading playlist.'
                        elif 'Error' in line:
                            current_progress['error'] = line
                            current_progress['status'] = 'error'
                            current_progress['stage'] = line

                current_downloader_process = None

                if process.returncode not in (0, None):
                    error = current_progress.get('error', 'Unknown error')
                    current_progress['error'] = f"Error downloading {playlist['name']}: {error}"
                    current_progress['status'] = 'error'
                    current_progress['stage'] = f"Error downloading {playlist['name']}: {error}"
                    break

            if downloader_running:
                current_progress['status'] = 'completed'
                next_sync_time = datetime.datetime.now() + datetime.timedelta(seconds=INTERVAL)
                while downloader_running:
                    now = datetime.datetime.now()
                    seconds_left = int((next_sync_time - now).total_seconds())
                    if seconds_left <= 0:
                        break
                    minutes_left = (seconds_left + 59) // 60
                    current_progress['stage'] = f"Waiting for next sync in {minutes_left} minute{'s' if minutes_left != 1 else ''}..."
                    time.sleep(10)  # Update every 10 seconds for better accuracy
                # After waiting, loop will restart
        except Exception as e:
            current_progress['error'] = str(e)
            current_progress['status'] = 'error'
            current_progress['stage'] = f"Error: {str(e)}"
            break
    current_progress['status'] = 'idle'
    current_progress['current_playlist'] = None
    current_progress['current_song'] = None
    current_progress['total_songs'] = 0
    current_progress['downloaded_songs'] = 0
    current_progress['error'] = None
    current_progress['stage'] = 'Idle.'
    current_downloader_process = None
    next_sync_time = None

@app.route('/')
def index():
    playlists = load_playlists()
    config = load_config()
    has_credentials = bool(config.get('spotify', {}).get('client_id') and config.get('spotify', {}).get('client_secret'))
    return render_template('index.html', 
                         playlists=playlists, 
                         has_credentials=has_credentials,
                         downloader_running=downloader_running)

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
    global downloader_thread, downloader_running
    if downloader_thread and downloader_thread.is_alive():
        return redirect('/')
    downloader_running = True
    downloader_thread = threading.Thread(target=downloader_loop, daemon=True)
    downloader_thread.start()
    return redirect('/')

@app.route('/stop')
def stop_downloader():
    global downloader_running, current_downloader_process
    downloader_running = False
    # Terminate the subprocess if running
    if current_downloader_process and current_downloader_process.poll() is None:
        current_downloader_process.terminate()
    return redirect('/')

@app.route('/progress')
def get_progress():
    return jsonify(current_progress)

@app.route('/reorder', methods=['POST'])
def reorder_playlists():
    data = request.get_json()
    new_order = data.get('order', [])
    playlists = load_playlists()
    # Create a mapping from URL to playlist object
    playlist_map = {p['url']: p for p in playlists}
    # Reorder playlists based on the new order
    reordered = [playlist_map[url] for url in new_order if url in playlist_map]
    # If any playlists were not included (shouldn't happen), append them at the end
    for p in playlists:
        if p['url'] not in new_order:
            reordered.append(p)
    save_playlists(reordered)
    return ('', 204)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 