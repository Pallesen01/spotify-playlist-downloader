import spotipy
import os
import shelve
import sys
import asyncio
from spotipy.oauth2 import SpotifyClientCredentials
from downloader_functions import *

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
downloadQueue = []  # songs to be downloaded

try:
    playlist_url = sys.argv[1]
except IndexError:
    print("Error - no playlist link found")
    print("Usage: python playlist_downloader.py <playlist_url>")
    sys.exit(1)

print("Getting all songs from playlist...")
songs, folder_name = getTracks(playlist_url, sp)
os.makedirs(folder_name, exist_ok=True)

print("Getting already downloaded songs...")
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
        print(song.name, "already downloaded")
    else:
        downloadQueue.append(song)


async def main():
    semaphore = asyncio.Semaphore(4)
    tasks = [downloadSong(song, semaphore) for song in downloadQueue]
    if tasks:
        await asyncio.gather(*tasks)

    print("Deleting images")
    deleteAllImages(folder_name)
    print("Deleting Removed Songs")
    delRemoved(playlistFolderURIs, songs, folder_name)
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
