import asyncio
import os
import shelve
import sys
import urllib

import pafy
import spotipy
from bs4 import BeautifulSoup
from spotipy.oauth2 import SpotifyClientCredentials

from downloader_functions import downloadSong, getTracks, getUri, deleteAllImages, delRemoved


async def download_worker(song, semaphore, loop):
    """Asynchronously download a single song using a thread executor."""
    async with semaphore:
        await loop.run_in_executor(None, downloadSong, song)


async def main():
    shelveFile = shelve.open('spotify_data')
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=shelveFile['SPOTIPY_CLIENT_ID'],
            client_secret=shelveFile['SPOTIPY_CLIENT_SECRET'],
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    except Exception:
        shelveFile['SPOTIPY_CLIENT_ID'] = input("Enter Client ID: ")
        shelveFile['SPOTIPY_CLIENT_SECRET'] = input("Enter Client Secret: ")
        client_credentials_manager = SpotifyClientCredentials(
            client_id=shelveFile['SPOTIPY_CLIENT_ID'],
            client_secret=shelveFile['SPOTIPY_CLIENT_SECRET'],
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    shelveFile.close()

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
    URIs = []
    playlistFolderURIs = []
    for file in os.listdir(folder_name):
        playlistFolderURIs.append(getUri(os.path.join(folder_name, file)))

    URIs.extend(playlistFolderURIs)

    for folder in os.listdir():
        if folder == folder_name:
            continue
        try:
            for file in os.listdir(folder):
                URIs.append(getUri(os.path.join(folder, file)))
        except NotADirectoryError:
            pass

    downloadQueue = []
    for song in songs:
        if song.uri in URIs:
            print(song.name, "already downloaded")
        else:
            downloadQueue.append(song)

    semaphore = asyncio.Semaphore(4)
    loop = asyncio.get_event_loop()
    tasks = [download_worker(song, semaphore, loop) for song in downloadQueue]
    if tasks:
        await asyncio.gather(*tasks)

    print("Deleting images")
    deleteAllImages(folder_name)
    print("Deleting Removed Songs")
    delRemoved(playlistFolderURIs, songs, folder_name)
    print("Done")


if __name__ == '__main__':
    asyncio.run(main())
