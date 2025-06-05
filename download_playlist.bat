@echo off
:: Create Music directory if it doesn't exist
if not exist "%USERPROFILE%\Desktop\Music" mkdir "%USERPROFILE%\Desktop\Music"

:: Change file location to where you want the songs to be downloaded
cd "%USERPROFILE%\Desktop\Music"

:: Set to url for playlist to be downloaded
set playlistlink=https://open.spotify.com/playlist/6kVbhdK2ymPGUUXzXfZXvh?si=6cb919d48ea640bd

echo Downloading Playlist...
python "%~dp0playlist_downloader.py" %playlistlink%
PAUSE