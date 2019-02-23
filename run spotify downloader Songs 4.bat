@echo off
:: Change file location to where you want the songs to be downloaded
G:
cd G:\Music

:: Set to url for playlist to be downloaded
set playlistlink=https://open.spotify.com/user/sparks_of_fire/playlist/4bsNBniLyy3R2CprhcSRA0?si=XdFZLTMuTVau7tk3_WP-3g

echo Downloading Playlist...
python "C:\Users\Daniel\Desktop\Python\Scripts\Spotify\Spotify Playlist Downloader V3\downloadSpotifyPlaylist.py" %playlistlink%
PAUSE
