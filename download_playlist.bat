@echo off
:: Create Music directory if it doesn't exist
if not exist "%USERPROFILE%\Desktop\Music" mkdir "%USERPROFILE%\Desktop\Music"

:: Install required dependencies
echo Installing dependencies...
pip install -r "%~dp0requirements.txt" >nul 2>&1

:: Install optional high-quality providers (ignore errors if they fail)
echo Installing optional providers...
pip install qobuz-dl >nul 2>&1

:: Check if ffmpeg is installed, install if not found
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo Installing ffmpeg...
    winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements >nul 2>&1
    echo FFmpeg installed. You may need to restart your terminal for it to work.
)

:: Set pafy to use internal backend instead of youtube-dl
set PAFY_BACKEND=internal

:: Change file location to where you want the songs to be downloaded
cd "%USERPROFILE%\Desktop\Music"

:: Set to url for playlist to be downloaded
set playlistlink=https://open.spotify.com/playlist/6kVbhdK2ymPGUUXzXfZXvh?si=6cb919d48ea640bd

echo Downloading Playlist...
python "%~dp0playlist_downloader.py" %playlistlink%
PAUSE