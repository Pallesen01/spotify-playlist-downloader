# Spotify Playlist Downloader

Downloads songs in a Spotify playlist. The downloader attempts to grab lossless audio from Qobuz when credentials are provided and falls back to YouTube otherwise.

## Project Structure

```
spotify-playlist-downloader/
├── src/
│   ├── core/                 # Core downloader functionality
│   │   ├── __init__.py
│   │   ├── downloader_functions.py
│   │   └── playlist_downloader.py
│   ├── web/                  # Web interface
│   │   ├── __init__.py
│   │   └── web_interface.py
│   └── main.py              # Main entry point
├── static/
│   └── css/
│       └── style.css        # Web interface styles
├── templates/
│   └── index.html          # Web interface template
├── tests/                   # Test files
├── scripts/                 # Shell/batch scripts
├── requirements.txt
└── README.md
```

## Required Modules
spotipy, sys, os, urllib, requests, threading, subprocess, eyed3, youtube_dl,
pafy, bs4, pytube, tqdm, qobuz-dl

## Improvements
The YouTube search logic now scores results using fuzzy title matching and
duration similarity which helps select the official or most accurate audio
track for each song.

Album artwork is deleted immediately after each song is downloaded and tagged
so that images are not left behind after the metadata is applied. Because the
cleanup happens per track, there is no longer a final image deletion step.

## Usage

### Command Line
Run `playlist_downloader.py` with the playlist URL:

```bash
python src/core/playlist_downloader.py <playlist_url>
```

### Web Interface
Start the web interface:

```bash
python src/main.py
```

Open `http://localhost:5000` in your browser to manage playlists and start the
automatic downloader.

## Configuration

If you have a Qobuz account and wish to download lossless audio, set the
following environment variables before running the script:

```
export QOBUZ_EMAIL="your-email"
export QOBUZ_PASSWORD="your-password"
export QOBUZ_APP_ID="your-app-id"
export QOBUZ_SECRETS="secret1,secret2,..."
```

When these are provided the downloader will attempt to fetch FLAC files from
Qobuz. You can optionally set a Jamendo API client ID to enable downloads from
Jamendo as well:

```
export JAMENDO_CLIENT_ID="your-client-id"
```

The downloader attempts the following sources in order of quality:
1. Qobuz (lossless when available)
2. Bandcamp
3. SoundCloud
4. Jamendo
5. YouTube

If all high quality sources fail, it falls back to YouTube as before.

To download only the first N songs, provide the `--limit` option:

```bash
python src/core/playlist_downloader.py <playlist_url> --limit N
```

If you prefer to authenticate through your web browser instead of providing a
client ID and secret, add the `--user-auth` flag. A browser window will open so
you can log into Spotify:

```bash
python src/core/playlist_downloader.py <playlist_url> --user-auth
```
