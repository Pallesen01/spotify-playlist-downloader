#!/usr/bin/env python3
"""
Debug version of the playlist downloader that shows which providers are being tried.
This patches the downloader functions to add logging.
"""

import spotipy, os, urllib, shelve, threading, sys, argparse
os.environ.setdefault('PAFY_BACKEND', 'internal')
import pafy
from tqdm import tqdm
from spotipy.oauth2 import SpotifyClientCredentials
from downloader_functions import *
from bs4 import BeautifulSoup
import time

# Patch the download functions to add logging
original_download_from_qobuz = download_from_qobuz
original_download_from_bandcamp = download_from_bandcamp  
original_download_from_soundcloud = download_from_soundcloud
original_download_from_jamendo = download_from_jamendo

def debug_download_from_qobuz(song, quiet=False):
    print(f"🎵 [{song.name}] Trying Qobuz...")
    start_time = time.time()
    result = original_download_from_qobuz(song, quiet=True)  # Always quiet to avoid double output
    elapsed = time.time() - start_time
    if result:
        print(f"✅ [{song.name}] Qobuz SUCCESS ({elapsed:.1f}s)")
    else:
        print(f"❌ [{song.name}] Qobuz failed ({elapsed:.1f}s)")
    return result

def debug_download_from_bandcamp(song, quiet=False):
    print(f"🎸 [{song.name}] Trying Bandcamp...")
    start_time = time.time()
    result = original_download_from_bandcamp(song, quiet=True)
    elapsed = time.time() - start_time
    if result:
        print(f"✅ [{song.name}] Bandcamp SUCCESS ({elapsed:.1f}s)")
    else:
        print(f"❌ [{song.name}] Bandcamp failed ({elapsed:.1f}s)")
    return result

def debug_download_from_soundcloud(song, quiet=False):
    print(f"☁️ [{song.name}] Trying SoundCloud...")
    start_time = time.time()
    result = original_download_from_soundcloud(song, quiet=True)
    elapsed = time.time() - start_time
    if result:
        print(f"✅ [{song.name}] SoundCloud SUCCESS ({elapsed:.1f}s)")
    else:
        print(f"❌ [{song.name}] SoundCloud failed ({elapsed:.1f}s)")
    return result

def debug_download_from_jamendo(song, quiet=False):
    print(f"🎼 [{song.name}] Trying Jamendo...")
    start_time = time.time()
    result = original_download_from_jamendo(song, quiet=True)
    elapsed = time.time() - start_time
    if result:
        print(f"✅ [{song.name}] Jamendo SUCCESS ({elapsed:.1f}s)")
    else:
        print(f"❌ [{song.name}] Jamendo failed ({elapsed:.1f}s)")
    return result

# Patch the Song class download method
original_song_download = Song.download

def debug_song_download(self, quiet=False):
    print(f"\n🎯 Starting download for: {self.name}")
    
    # Try high quality download sources in order
    if debug_download_from_qobuz(self, quiet=quiet):
        print(f"🎉 [{self.name}] Downloaded via Qobuz")
        return
    if debug_download_from_bandcamp(self, quiet=quiet):
        print(f"🎉 [{self.name}] Downloaded via Bandcamp")
        return
    if debug_download_from_soundcloud(self, quiet=quiet):
        print(f"🎉 [{self.name}] Downloaded via SoundCloud")
        return
    if debug_download_from_jamendo(self, quiet=quiet):
        print(f"🎉 [{self.name}] Downloaded via Jamendo")
        return

    # Fall back to YouTube
    print(f"📺 [{self.name}] Falling back to YouTube...")
    start_time = time.time()
    
    self.get_link(quiet=True)
    os.makedirs(self.folder_name, exist_ok=True)

    output_path = os.path.join(self.folder_name, self.name_file + ".%(ext)s")
    final_path = os.path.join(self.folder_name, self.name_file + ".mp3")
    
    try:
        # Use yt-dlp to download directly as mp3
        download_cmd = [
            'yt-dlp',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '0',  # best quality
            '--output', output_path,
            self.closesturl
        ]
        
        result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"⚠️ [{self.name}] Primary YouTube URL failed, trying backup...")
            # Try backup URL
            download_cmd[-1] = self.backupvid
            result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise Exception(f"Both downloads failed: {result.stderr}")
        
        # Find the actual downloaded file (yt-dlp might change the extension)
        for file in os.listdir(self.folder_name):
            if file.startswith(self.name_file) and file.endswith('.mp3'):
                self.file = os.path.join(self.folder_name, file)
                break
        else:
            # If no mp3 found, look for any file with our name and rename it
            for file in os.listdir(self.folder_name):
                if file.startswith(self.name_file):
                    old_path = os.path.join(self.folder_name, file)
                    os.rename(old_path, final_path)
                    self.file = final_path
                    break
            else:
                self.file = final_path
        
        elapsed = time.time() - start_time
        print(f"✅ [{self.name}] YouTube SUCCESS via yt-dlp ({elapsed:.1f}s)")
                
    except Exception as e:
        print(f"❌ [{self.name}] yt-dlp failed: {e}")
        # Fallback to old method
        try:
            if self.video and pafy:
                print(f"🔄 [{self.name}] Trying pafy fallback...")
                self.video.getbestaudio().download(filepath=os.path.join(self.folder_name, self.name_file))
                
                FNULL = open(os.devnull, 'w')
                subprocess.call("ffmpeg -i \"" + os.path.join(self.folder_name, self.name_file)+"\" " + "\""+ final_path +"\"", stdout=FNULL, stderr=subprocess.STDOUT)
                os.remove(os.path.join(self.folder_name, self.name_file))
                self.file = final_path
                elapsed = time.time() - start_time
                print(f"✅ [{self.name}] YouTube SUCCESS via pafy ({elapsed:.1f}s)")
            else:
                raise Exception("No pafy/video object available")
                
        except Exception as e2:
            elapsed = time.time() - start_time
            print(f"💥 [{self.name}] ALL METHODS FAILED ({elapsed:.1f}s): {e2}")
            self.file = None

# Apply the patches
Song.download = debug_song_download

# Rest of the original script
shelveFile = shelve.open('spotify_data')

try:
    # spotify verification
    client_credentials_manager = SpotifyClientCredentials(client_id=shelveFile['SPOTIPY_CLIENT_ID'],
                                                        client_secret=shelveFile['SPOTIPY_CLIENT_SECRET'])

    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
except:
    shelveFile['SPOTIPY_CLIENT_ID'] = input("Enter Client ID: ")
    shelveFile['SPOTIPY_CLIENT_SECRET'] = input("Enter Client Secret: ")
    client_credentials_manager = SpotifyClientCredentials(client_id=shelveFile['SPOTIPY_CLIENT_ID'],
                                                        client_secret=shelveFile['SPOTIPY_CLIENT_SECRET'])

    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

shelveFile.close()

#set variables
threadList = []  # stores all threads
downloadQueue = []  # songs to be downloaded

parser = argparse.ArgumentParser(description="Download songs from a Spotify playlist (DEBUG VERSION)")
parser.add_argument("playlist_url", help="Spotify playlist URL or URI")
parser.add_argument("--limit", "-l", type=int, help="Only download the first N songs", default=None)
args = parser.parse_args()

playlist_url = args.playlist_url
limit = args.limit

songs, folder_name = getTracks(playlist_url, sp, limit=limit)
os.makedirs(folder_name, exist_ok=True)

print("Checking already downloaded songs...")
# get URIs of downloaded songs
URIs = []
playlistFolderURIs = []
for root, _, files in os.walk(folder_name):
    for file in files:
        file_path = os.path.join(root, file)
        if os.path.isfile(file_path):
            playlistFolderURIs.append(getUri(file_path))

#Don't download dupe songs from other folders
URIs.extend(playlistFolderURIs)

for folder in os.listdir():
    if folder == folder_name or folder.startswith('.'):
        continue
    if not os.path.isdir(folder):
        continue
    for root, _, files in os.walk(folder):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                URIs.append(getUri(file_path))

for song in songs:
    if song.uri in URIs:
        pass  # Skip already downloaded songs silently
    else:
        downloadQueue.append(song)

print(f"\n🎵 Found {len(songs)} total songs, {len(downloadQueue)} to download")
print("🔍 DEBUG MODE: Will show which providers are tried for each song\n")

# Progress bar for all songs (downloaded + to download)
progress_bar = tqdm(total=len(songs), desc="Processing Songs", unit="song", 
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')

# Update progress for already downloaded songs
already_downloaded = len(songs) - len(downloadQueue)
if already_downloaded > 0:
    progress_bar.n = already_downloaded
    progress_bar.refresh()

# Track download results
download_results = {
    'qobuz': 0,
    'bandcamp': 0, 
    'soundcloud': 0,
    'jamendo': 0,
    'youtube': 0,
    'failed': 0
}

def thread_download(song):
    downloadSong(song, quiet=True)
    progress_bar.update(1)

#While there are songs in download queue download songs
while len(downloadQueue) > 0:
    if len(threadList) <= 4:
        threadObj = threading.Thread(target=thread_download, args=[downloadQueue.pop(0)])
        threadObj.handled = False
        threadList.append(threadObj)
        threadObj.start()

    for t in threadList:
        if not t.is_alive():
            t.handled = True
    threadList = [t for t in threadList if not t.handled]

#Wait for all thread to finish
for t in threadList:
    t.join()

progress_bar.close()

print("Deleting Removed Songs")
delRemoved(playlistFolderURIs, songs, folder_name)
print("Done") 