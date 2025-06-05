#!/usr/bin/env python3
"""
Setup script for the Spotify Playlist Downloader
"""
import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is 3.7 or higher"""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        sys.exit(1)

def install_requirements():
    """Install required Python packages"""
    print("Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def install_ffmpeg():
    """Install FFmpeg based on the operating system"""
    system = platform.system().lower()
    print(f"Checking FFmpeg installation on {system}...")
    
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("FFmpeg is already installed")
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    if system == "windows":
        print("Installing FFmpeg using winget...")
        subprocess.run(["winget", "install", "--id=Gyan.FFmpeg", "-e", "--accept-source-agreements", "--accept-package-agreements"])
    elif system == "darwin":
        print("Installing FFmpeg using Homebrew...")
        subprocess.run(["brew", "install", "ffmpeg"])
    elif system == "linux":
        if os.path.exists("/usr/bin/apt"):
            print("Installing FFmpeg using apt...")
            subprocess.run(["sudo", "apt", "update"])
            subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"])
        elif os.path.exists("/usr/bin/yum"):
            print("Installing FFmpeg using yum...")
            subprocess.run(["sudo", "yum", "install", "-y", "ffmpeg"])
        elif os.path.exists("/usr/bin/pacman"):
            print("Installing FFmpeg using pacman...")
            subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])
        else:
            print("Error: Could not determine package manager for FFmpeg installation")
            print("Please install FFmpeg manually for your system")
            sys.exit(1)

def create_config():
    """Create config.json if it doesn't exist"""
    if not os.path.exists("config.json"):
        print("Creating config.json...")
        with open("config.json", "w") as f:
            f.write("""{
    "spotify": {
        "client_id": "",
        "client_secret": ""
    }
}""")
        print("Please add your Spotify client ID and secret to config.json")

def main():
    """Main setup function"""
    print("Setting up Spotify Playlist Downloader...")
    
    check_python_version()
    install_requirements()
    install_ffmpeg()
    create_config()
    
    print("\nSetup complete!")
    print("\nTo start the web interface:")
    print("python src/main.py")
    print("\nTo download a playlist directly:")
    print("python src/core/playlist_downloader.py <playlist_url>")

if __name__ == "__main__":
    main() 