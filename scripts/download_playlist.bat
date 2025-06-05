@echo off
setlocal enabledelayedexpansion

:: Set PYTHONPATH to include project root
set "PYTHONPATH=%~dp0..;%PYTHONPATH%"

:: Create Music directory on desktop if it doesn't exist
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

:: Set download location to Music directory on desktop
set "DOWNLOAD_LOCATION=%USERPROFILE%\Desktop\Music"

:: Check if playlist URL is provided
if "%~1"=="" (
    echo Please provide a Spotify playlist URL
    echo Usage: download_playlist.bat "https://open.spotify.com/playlist/..."
    pause
    exit /b 1
)

:: Download the playlist
echo Downloading Playlist...
python "%~dp0..\src\core\playlist_downloader.py" "%~1"

pause