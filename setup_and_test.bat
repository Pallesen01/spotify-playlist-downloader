@echo off
echo ========================================
echo Spotify Playlist Downloader Setup
echo ========================================

:: Set pafy to use internal backend
set PAFY_BACKEND=internal

:: Install dependencies
echo Installing Python dependencies...
pip install -r "%~dp0requirements.txt"

:: Install optional providers
echo Installing optional providers...
pip install qobuz-dl

:: Check if ffmpeg is installed
echo Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo Installing FFmpeg...
    winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    echo FFmpeg installed. Please restart your terminal and run this script again.
    pause
    exit /b
) else (
    echo FFmpeg is already installed.
)

echo.
echo ========================================
echo Running Provider Diagnostic Test...
echo ========================================
python "%~dp0test_providers.py"

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo You can now use:
echo - download_playlist.bat for quick downloads
echo - debug_downloader.py to see which providers are used
echo - test_providers.py to check provider status
echo.
pause 