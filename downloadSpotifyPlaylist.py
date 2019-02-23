# downloadSpotifyPlaylist Version 3.py - downloads all songs in a spotify playlist as mp3
# Daniel Pallesen
# 26/09/2018

# import modules
import spotipy, sys, os, urllib, requests, threading, subprocess, eyed3, time, pafy
from spotipy.oauth2 import SpotifyClientCredentials
from bs4 import BeautifulSoup
from pytube import YouTube
import moviepy as mp

# spotify verification
client_credentials_manager = SpotifyClientCredentials(client_id='2c712f6e44554be984e7239d06a4b1e5',
                                                      client_secret='d9fc9552db5b47aaae618c210c7b67a7')

sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
threadList = []
ffmpeg = 'C:\\Program Files\\ffmpeg-20180611-8c20ea8-win64-static\\bin\\ffmpeg.exe'
FNULL = open(os.devnull, 'w')

# returns a list of all track objects from a playlist
def getTracks(playlist_url):
    allTracks = []
    if 'https://open.spotify.com/user/' in playlist_url:

        playlist_user = playlist_url.split('user/')[1].split('/')[0]
        playlist_id = playlist_url.split('playlist/')[1]

    else:
        playlist_user = playlist_url.split(':')[0]
        playlist_id = playlist_url.split(':')[-1]
    
    playlist = sp.user_playlist(playlist_user, playlist_id)

    results = sp.user_playlist(playlist_user, playlist['id'], fields="tracks,next")
    tracks = results['tracks']
    for track in tracks['items']:
        allTracks.append(track['track'])

    while tracks['next']:
        tracks = sp.next(tracks)
        for track in tracks['items']:
            allTracks.append(track['track'])

    return allTracks

# gets a link to a youtube video for a track | returns link
def getTrackLink(track):
    videoList = []
    durLimit = 20
    textToSearch = track['artists'][0]['name']+ ' ' + track['name']+' track song'
    trackDuration = int(track['duration_ms']/1000)
    query = urllib.parse.quote(textToSearch)
    url = "https://www.youtube.com/results?search_query=" + query
    response = urllib.request.urlopen(url)
    html = response.read()
    soup = BeautifulSoup(html, 'html5lib')
    for vid in soup.findAll(attrs={'class':'yt-uix-tile-link'}):
        videoList.append('https://www.youtube.com' + vid['href'])

    for url in videoList:
        try:
            video = pafy.new(url)
        except ValueError:
            pass

        if video.length > trackDuration - durLimit and video.length < trackDuration + durLimit:
            return url  

# downloads youtube video from a link | returns file name
def downloadVideo(link, track):
    os.makedirs(folder_name, exist_ok=True)
    os.system("youtube-dl.exe --extract-audio --output \""+ folder_name + '\\' +removeInvalidCharacters(track['name'])+".%(ext)s"+"\" --audio-format mp3 --audio-quality 0 "+link)

    for file in os.listdir(folder_name):
        if removeInvalidCharacters(track['name']) in file or track['name'] in file:
            if not '.mp3' in file:
                pass
            else:
                return os.path.join(folder_name, file)

# download a file from a url | returns file location
def downloadFile(link, filename):
    print(filename)
    try:
        res = requests.get(link)
        res.raise_for_status()
            
        # Save the file to file location
        file = open(os.path.join(folder_name, os.path.basename(link)), 'wb')
        for chunk in res.iter_content(100000):
            file.write(chunk)
        file.close()
    except requests.exceptions.MissingSchema:
        print('Error requests.exceptions.MissingSchema')

    except FileExistsError:
        pass

    #find then rename file to filename specified
    for file in os.listdir(folder_name):
        if file == link.split('/')[-1]:
            os.rename(os.path.join(folder_name, file),filename)
            return filename

    return filename

# download album art | returns filename
def downloadAlbumArt(track):
    filenameOnly = removeInvalidCharacters(track['album']['name'])+'.jpg'
    filename = os.path.join(folder_name, filenameOnly)

    # check if file is already downloaded
    for file in os.listdir(folder_name):
        if filenameOnly == file:
            return filename

    downloadFile(track['album']['images'][0]['url'], filename)
    return filename

# assigns id3 attributes to mp3 file
def audioFileAttributes(file, track, art):
    try:
        audiofile = eyed3.load(file)

    except TypeError as e:
        print("Could not download song")
        print(e)

    try:
        audiofile.tag.artist = track['artists'][0]['name']
        audiofile.tag.album = track['album']['name']
        audiofile.title = removeInvalidCharacters(track['name'])
        audiofile.tag.images.set(3, open(art,'rb').read(), 'image/jpeg')
        audiofile.tag.save()
    except AttributeError as e:
        print("error setting file attributes")
        print(e)

    except UnboundLocalError:
        pass
    

def removeInvalidCharacters(string):
    return string.replace(':','').replace('?','').replace(';','').replace('<','').replace('>','').replace('*','').replace('|','').replace('/','').replace('\\','').replace('"','').replace('‘','\'')

def removeInvalidCharactersVid(string):
    return string.replace(':','').replace('?','').replace(';','').replace('<','').replace('>','').replace('*','').replace('|','').replace('/','').replace('\\','').replace('.','').replace('"','').replace('\'','').replace(',','')

def deleteAllImages():
    for file in os.listdir(folder_name):
        if '.jpg' in file:
            os.remove(os.path.join(folder_name, file))

def deleteFile(file):
    os.remove(os.path.join(folder_name, file))

def getPlaylistName(playlist_url):
    #allTracks = [] Like 90% sure this isn't needed lol
    if 'https://open.spotify.com/user/' in playlist_url:

        playlist_user = playlist_url.split('user/')[1].split('/')[0]
        playlist_id = playlist_url.split('playlist/')[1]

    else:
        playlist_user = playlist_url.split(':')[0]
        playlist_id = playlist_url.split(':')[-1]
    
    playlist = sp.user_playlist(playlist_user, playlist_id)
    return playlist['name']

#test vars
#folder_name = 'Songs 3'
#playlist_url = 'https://open.spotify.com/user/sparks_of_fire/playlist/1uBMmG5EyrC5Od5A4fBdR9?si=Vjv4si7pSQCKQaDp5rPVuQ'

try:
    playlist_url = sys.argv[1]

except IndexError:
    playlist_url = 'https://open.spotify.com/user/sparks_of_fire/playlist/1uBMmG5EyrC5Od5A4fBdR9?si=Vjv4si7pSQCKQaDp5rPVuQ'

folder_name = getPlaylistName(playlist_url)
allTracks = []

for track in getTracks(playlist_url):
    allTracks.append(removeInvalidCharacters(track['name']))
    validTrack = True
    os.makedirs(folder_name, exist_ok=True)

    try:
        x = track['album']['images'][0]['url']
    
    except IndexError:
        validTrack = False

    if validTrack:

        # check if file already exists
        fileExists = False
        for file in os.listdir(folder_name):
            if removeInvalidCharacters(track['name']) + '.mp3' == str(file):
                if '.jpg' in file:
                    pass
                else:
                    fileExists = True
                    break

        if not fileExists:
            print("Finding URL for", track['name'])
            videoLink = getTrackLink(track)
            print('Downloading', track['name'])
            audioFile = downloadVideo(videoLink, track)
            print("Downloading Album Cover for", track['name'])
            albumCover = downloadAlbumArt(track)
            print("Setting File Attributes for", track['name'])
            audioFileAttributes(audioFile, track, albumCover)

        else:
            print(track['name'],"Already Downloaded")
            #downloadAlbumArt(track)

    else:
        pass

#Delete songs that have been removed from the playlist
for file in os.listdir(folder_name):
    if not '.jpg' in file:
        if not file.replace('.mp3', '') in allTracks:
            print(file, "No Longer in Playlist")
            deleteFile(file)

print("Deleting Cover Images")
deleteAllImages()

print("Finished Downloading Playlist")