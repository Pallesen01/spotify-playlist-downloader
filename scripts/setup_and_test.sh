#!/bin/bash

# Set PYTHONPATH to include project root
export PYTHONPATH="$(dirname "$0")/..:$PYTHONPATH"

echo "========================================"
echo "Spotify Playlist Downloader Setup"
echo "========================================"

# Set pafy to use internal backend instead of youtube-dl (must be set before installing)
export PAFY_BACKEND=internal

# Install required dependencies
echo "Installing dependencies..."
pip install -r "$(dirname "$0")/../requirements.txt" > /dev/null 2>&1

# Install optional high-quality providers (ignore errors if they fail)
echo "Installing optional providers..."
pip install qobuz-dl > /dev/null 2>&1

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found. Please install FFmpeg and add it to your PATH."
    echo "Visit: https://ffmpeg.org/download.html"
    exit 1
fi

echo ""
echo "========================================"
echo "Running Provider Diagnostic Test..."
echo "========================================"
python "$(dirname "$0")/test_providers.py"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo "You can now use:"
echo "- ./download_playlist.sh for quick downloads"
echo "- python debug_downloader.py to see which providers are used"
echo "- python test_providers.py to check provider status"
echo ""
echo "Press any key to continue..."
read -n 1 -s

# Set playlist URL
playlistlink="https://open.spotify.com/playlist/6kVbhdK2ymPGUUXzXfZXvh?si=6cb919d48ea640bd"

echo "Downloading Playlist..."
python "$(dirname "$0")/../src/core/playlist_downloader.py" "$playlistlink"

echo
echo "Testing imports..."
python "$(dirname "$0")/../tests/test_imports.py"

echo
echo "Starting web interface..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5000 &
elif command -v open &> /dev/null; then
    open http://localhost:5000 &
fi
python "$(dirname "$0")/../src/main.py"

echo "Press any key to continue..."
read -n 1 -s 