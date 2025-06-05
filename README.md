# spotify-playlist-downloader
Downloads all songs in a Spotify playlist from YouTube.

# Required Modules
spotipy, sys, os, urllib, requests, threading, subprocess, eyed3, mutagen, youtube_dl, pafy, bs4, pytube, tqdm

## Improvements
The YouTube search logic now scores results using fuzzy title matching and
duration similarity which helps select the official or most accurate audio
track for each song.

### High Fidelity Downloads
The downloader first attempts to retrieve audio as lossless FLAC from
SoundCloud using `yt-dlp`. If that fails, it falls back to the previous FLAC
method that downloads from YouTube, and finally to the original mp3 workflow.
Album art and metadata continue to be embedded in the resulting files.
