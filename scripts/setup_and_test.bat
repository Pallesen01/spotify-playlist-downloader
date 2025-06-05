@echo off
setlocal enabledelayedexpansion

:: Set PYTHONPATH to include project root
set "PYTHONPATH=%~dp0..;%PYTHONPATH%"

:: Create Music directory if it doesn't exist
if not exist "%USERPROFILE%\Desktop\Music" mkdir "%USERPROFILE%\Desktop\Music"

:: Install required dependencies
echo Installing dependencies...
pip install -r "%~dp0..\requirements.txt" >nul 2>&1

:: Install optional high-quality providers (ignore errors if they fail)
echo Installing optional providers...
pip install qobuz-dl >nul 2>&1

:: Check if ffmpeg is installed
where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo FFmpeg not found. Please install FFmpeg and add it to your PATH.
    echo Visit: https://ffmpeg.org/download.html
    pause
    exit /b 1
)

:: Set pafy to use internal backend instead of youtube-dl
set PAFY_BACKEND=internal

:: Change file location to where you want the songs to be downloaded
cd "%USERPROFILE%\Desktop\Music"

:: Set to url for playlist to be downloaded
set playlistlink=https://open.spotify.com/playlist/6kVbhdK2ymPGUUXzXfZXvh?si=6cb919d48ea640bd

echo Downloading Playlist...
python "%~dp0..\src\core\playlist_downloader.py" %playlistlink%

echo.
echo Testing imports...
python "%~dp0..\tests\test_imports.py"

echo.
echo Starting web interface...
start http://localhost:5000
python "%~dp0..\src\main.py"

PAUSE 