#!/bin/bash

# Set PYTHONPATH to include project root
export PYTHONPATH="$(dirname "$0")/..:$PYTHONPATH"

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

# Check if playlist URL is provided
if [ -z "$1" ]; then
    echo "Please provide a Spotify playlist URL"
    echo "Usage: ./download_playlist.sh 'https://open.spotify.com/playlist/...'"
    exit 1
fi

# Download the playlist
echo "Downloading Playlist..."
python "$(dirname "$0")/../src/core/playlist_downloader.py" "$1"

echo "Press any key to continue..."
read -n 1 -s 