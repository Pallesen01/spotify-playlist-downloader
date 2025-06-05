# spotify-playlist-downloader
Downloads all songs in a Spotify playlist from YouTube.

# Required Modules
spotipy, sys, os, urllib, requests, subprocess, eyed3, youtube_dl, pafy, bs4, pytube, asyncio (builtin)

The downloader now uses Python's `asyncio` library to fetch up to four songs concurrently.
