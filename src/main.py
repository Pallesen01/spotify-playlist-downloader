"""
Main entry point for the Spotify Playlist Downloader
"""
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.web_interface import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 