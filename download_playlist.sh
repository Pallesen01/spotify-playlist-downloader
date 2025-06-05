#!/bin/bash

# Set pafy to use internal backend instead of youtube-dl (must be set before installing)
export PAFY_BACKEND=internal

# Install required dependencies
echo "Installing dependencies..."
pip install -r "$(dirname "$0")/requirements.txt" > /dev/null 2>&1

# Install optional high-quality providers (ignore errors if they fail)
echo "Installing optional providers..."
pip install qobuz-dl > /dev/null 2>&1

# Check if ffmpeg is installed, install if not found
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing ffmpeg..."
    # Try different package managers
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y ffmpeg > /dev/null 2>&1
    elif command -v brew &> /dev/null; then
        brew install ffmpeg > /dev/null 2>&1
    elif command -v yum &> /dev/null; then
        sudo yum install -y ffmpeg > /dev/null 2>&1
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm ffmpeg > /dev/null 2>&1
    else
        echo "Please install ffmpeg manually for your system"
    fi
fi

# Set playlist URL
playlistlink="https://open.spotify.com/playlist/6kVbhdK2ymPGUUXzXfZXvh?si=6cb919d48ea640bd"

echo "Downloading Playlist..."
python "$(dirname "$0")/playlist_downloader.py" "$playlistlink"

echo "Press any key to continue..."
read -n 1 -s 