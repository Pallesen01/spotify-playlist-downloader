import spotipy, os, urllib, pafy, shelve, threading, sys, argparse
from tqdm import tqdm
from spotipy.oauth2 import SpotifyClientCredentials
from downloader_functions import *
from bs4 import BeautifulSoup

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

#TEMP Test Link
#test_link = "https://open.spotify.com/user/sparks_of_fire/playlist/4ScHDVxjzDpBFOyyKdWw6G?si=R_AFDhOJTYymeBpjs96jhw"

#set variables
threadList = []  # stores all threads
downloadQueue = []  # songs to be downloaded
album_counts = {}
album_lock = threading.Lock()

parser = argparse.ArgumentParser(description="Download songs from a Spotify playlist")
parser.add_argument("playlist_url", help="Spotify playlist URL or URI")
parser.add_argument("--limit", "-l", type=int, help="Only download the first N songs", default=None)
args = parser.parse_args()

playlist_url = args.playlist_url
limit = args.limit

songs, folder_name = getTracks(playlist_url, sp, limit=limit)
os.makedirs(folder_name, exist_ok=True)

print("Checking already downloaded songs...")
#get URIs of downloaded songs
URIs = []
playlistFolderURIs = []
for file in os.listdir(folder_name):
    file_path = os.path.join(folder_name, file)
    if os.path.isfile(file_path):
        playlistFolderURIs.append(getUri(file_path))


#Don't download dupe songs from other folders
URIs.extend(playlistFolderURIs)

for folder in os.listdir():
    if folder == folder_name or folder.startswith('.'):
        continue
    if not os.path.isdir(folder):
        continue
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        if os.path.isfile(file_path):
            URIs.append(getUri(file_path))

for song in songs:
    if song.uri in URIs:
        pass  # Skip already downloaded songs silently
    else:
        downloadQueue.append(song)

for song in downloadQueue:
    album_counts[song.album] = album_counts.get(song.album, 0) + 1

# Progress bar for all songs (downloaded + to download)
progress_bar = tqdm(total=len(songs), desc="Processing Songs", unit="song", 
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')

# Update progress for already downloaded songs (without affecting rate calculation)
already_downloaded = len(songs) - len(downloadQueue)
if already_downloaded > 0:
    # Set initial progress without starting the timer
    progress_bar.n = already_downloaded
    progress_bar.refresh()

# Flag to track when downloads actually start
downloads_started = False

# Track currently downloading songs
import threading
downloading_lock = threading.Lock()
currently_downloading = []

def thread_download(song):
    global downloads_started
    
    with downloading_lock:
        currently_downloading.append(song.name)
        # Update progress bar description with current downloads
        current_desc = f"Downloading: {', '.join(currently_downloading[:3])}"
        if len(currently_downloading) > 3:
            current_desc += f" (+{len(currently_downloading)-3} more)"
        progress_bar.set_description(current_desc)
        
        # Start the timer on first actual download
        if not downloads_started:
            downloads_started = True
            progress_bar.start_t = progress_bar._time()
    
    downloadSong(song, quiet=True)

    # Clean up album art when no longer needed
    with album_lock:
        album_counts[song.album] -= 1
        if album_counts[song.album] == 0:
            art_path = os.path.join(folder_name, song.album + '.jpg')
            if os.path.exists(art_path):
                try:
                    os.remove(art_path)
                except FileNotFoundError:
                    pass
    
    with downloading_lock:
        currently_downloading.remove(song.name)
        progress_bar.update(1)
        # Update description after completion
        if currently_downloading:
            current_desc = f"Downloading: {', '.join(currently_downloading[:3])}"
            if len(currently_downloading) > 3:
                current_desc += f" (+{len(currently_downloading)-3} more)"
            progress_bar.set_description(current_desc)
        else:
            progress_bar.set_description("Processing Songs")

#While there are songs in download queue download songs
while len(downloadQueue) > 0:
    if len(threadList) <= 4:
        threadObj = threading.Thread(target=thread_download, args=[downloadQueue.pop(0)])
        threadObj.handled = False
        threadList.append(threadObj)
        threadObj.start()

    for t in threadList:
        if not t.is_alive():
            #print("Thread Done")
            t.handled = True
    threadList = [t for t in threadList if not t.handled]

#Wait for all thread to finish
for t in threadList:
    t.join()

progress_bar.set_description("Finalizing...")
progress_bar.close()

print("Deleting images")
deleteAllImages(folder_name)
print("Deleting Removed Songs")
delRemoved(playlistFolderURIs, songs, folder_name)
print("Done")
