@echo off
:: Change file location to where you want the songs to be downloaded
G:
cd G:\Music

:: Set to url for playlist to be downloaded
set playlistlink="ENTER PLAYLIST URL"

echo Downloading Playlist...
python "C:\Users\Daniel\Desktop\Python\Scripts\Spotify\Spotify Playlist Downloader V3\downloadSpotifyPlaylist.py" %playlistlink%
PAUSE
