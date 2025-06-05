import spotipy, os, urllib, pafy, shelve, threading, sys
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
threadList = [] # stores all threads
downloadQueue = [] #songs to be downloaded

try:
    playlist_url = sys.argv[1]
except IndexError:
    print("Error - no playlist link found")
    print("Usage: python playlist_downloader.py <playlist_url>")
    sys.exit(1)

songs, folder_name = getTracks(playlist_url, sp)
os.makedirs(folder_name, exist_ok=True)

print("Checking already downloaded songs...")
#get URIs of downloaded songs
URIs = []
playlistFolderURIs = []
for file in os.listdir(folder_name):
    playlistFolderURIs.append(getUri(os.path.join(folder_name, file)))


#Don't download dupe songs from other folders
URIs.extend(playlistFolderURIs)

for folder in os.listdir():
    if folder == folder_name:
        pass
    try:
        for file in os.listdir(folder):
            URIs.append(getUri(os.path.join(folder, file)))
    except NotADirectoryError:
        pass

for song in songs:
    if song.uri in URIs:
        pass  # Skip already downloaded songs silently
    else:
        downloadQueue.append(song)

# Progress bar for all songs (downloaded + to download)
progress_bar = tqdm(total=len(songs), desc="Processing Songs", unit="song", 
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')

# Update progress for already downloaded songs
already_downloaded = len(songs) - len(downloadQueue)
progress_bar.update(already_downloaded)

# Track currently downloading songs
import threading
downloading_lock = threading.Lock()
currently_downloading = []

def thread_download(song):
    with downloading_lock:
        currently_downloading.append(song.name)
        # Update progress bar description with current downloads
        current_desc = f"Downloading: {', '.join(currently_downloading[:3])}"
        if len(currently_downloading) > 3:
            current_desc += f" (+{len(currently_downloading)-3} more)"
        progress_bar.set_description(current_desc)
    
    downloadSong(song, quiet=True)
    
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