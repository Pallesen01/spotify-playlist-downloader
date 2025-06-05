import os
import json
import threading
import time
import subprocess
import sys
from flask import Flask, request, redirect, render_template_string

PLAYLIST_FILE = 'playlists.json'
INTERVAL = 3600  # 1 hour

app = Flask(__name__)

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


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Spotify Playlist Downloader</title>
</head>
<body>
    <h1>Spotify Playlist Downloader</h1>
    <form action="/add" method="post">
        <input type="text" name="url" placeholder="Playlist URL" required>
        <button type="submit">Add Playlist</button>
    </form>
    <h2>Tracked Playlists</h2>
    <ul>
    {% for p in playlists %}
        <li>{{ p }}</li>
    {% endfor %}
    </ul>
    <a href="/start">Start Downloader</a>
</body>
</html>
"""


downloader_thread = None


def downloader_loop():
    while True:
        playlists = load_playlists()
        for url in playlists:
            subprocess.run([sys.executable, 'playlist_downloader.py', url])
        time.sleep(INTERVAL)


@app.route('/')
def index():
    playlists = load_playlists()
    return render_template_string(HTML_TEMPLATE, playlists=playlists)


@app.route('/add', methods=['POST'])
def add_playlist():
    url = request.form.get('url')
    playlists = load_playlists()
    if url and url not in playlists:
        playlists.append(url)
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

