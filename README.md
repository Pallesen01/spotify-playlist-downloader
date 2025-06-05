# spotify-playlist-downloader
Downloads all songs in a Spotify playlist from YouTube.

# Required Modules
spotipy, sys, os, urllib, requests, threading, subprocess, eyed3, youtube_dl, pafy, bs4, pytube, tqdm

## Improvements
The YouTube search logic now scores results using fuzzy title matching and
duration similarity which helps select the official or most accurate audio
track for each song.

Album artwork is deleted immediately after each song is downloaded and tagged
so that images are not left behind after the metadata is applied. Because the
cleanup happens per track, there is no longer a final image deletion step.

## Usage

Run `playlist_downloader.py` with the playlist URL:

```bash
python playlist_downloader.py <playlist_url>
```

To download only the first N songs, provide the `--limit` option:

```bash
python playlist_downloader.py <playlist_url> --limit N
```

## Graphical Interface

A basic Tkinter GUI is provided in `gui.py` for users who prefer not to use the command line. Run it with:

```bash
python gui.py
```

Enter the playlist URL and an optional limit, choose a destination folder, then click **Start Download**. Console output from the downloader will be shown in the window.
