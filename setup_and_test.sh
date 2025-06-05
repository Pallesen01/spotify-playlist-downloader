#!/bin/bash

echo "========================================"
echo "Spotify Playlist Downloader Setup"
echo "========================================"

# Set pafy to use internal backend
export PAFY_BACKEND=internal

# Install dependencies
echo "Installing Python dependencies..."
pip install -r "$(dirname "$0")/requirements.txt"

# Install optional providers
echo "Installing optional providers..."
pip install qobuz-dl

# Check if ffmpeg is installed
echo "Checking FFmpeg installation..."
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    # Try different package managers
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y ffmpeg
    elif command -v brew &> /dev/null; then
        brew install ffmpeg
    elif command -v yum &> /dev/null; then
        sudo yum install -y ffmpeg
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm ffmpeg
    else
        echo "Please install ffmpeg manually for your system"
        echo "Visit: https://ffmpeg.org/download.html"
    fi
else
    echo "FFmpeg is already installed."
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