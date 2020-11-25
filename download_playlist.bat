@echo off
:: Change file location to where you want the songs to be downloaded
G:
cd G:\Music

:: Set to url for playlist to be downloaded
set playlistlink=https://open.spotify.com/user/sparks_of_fire/playlist/5PKXk1rI16nqb0TALQmdqj?si=DId6N6wWQY28D72RUY0tlA

echo Downloading Playlist...
python playlist_downloader.py %playlistlink%
PAUSE