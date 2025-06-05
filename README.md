# spotify-playlist-downloader
Downloads all songs in a Spotify playlist from YouTube.

# Required Modules
spotipy, sys, os, urllib, requests, threading, subprocess, eyed3, youtube_dl, pafy, bs4, pytube, tqdm, mutagen

## Improvements
The YouTube search logic now scores results using fuzzy title matching and
duration similarity which helps select the official or most accurate audio
track for each song.

Album artwork is now removed as soon as all tracks from that album have been
processed rather than waiting until the end of the run.

Downloads now attempt to grab the highest bitrate audio available. If the
bitrate is above 320kbps the track is stored as a FLAC file. 320kbps or lower
audio is converted to a high quality MP3. The previous MP3 approach is
retained as a fallback if the high fidelity method fails.

## Usage

Run `playlist_downloader.py` with the playlist URL:

```bash
python playlist_downloader.py <playlist_url>
```

To download only the first N songs, provide the `--limit` option:

```bash
python playlist_downloader.py <playlist_url> --limit N
```
