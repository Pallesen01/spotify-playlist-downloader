import urllib, pafy, os, spotipy, subprocess, eyed3, requests, youtube_dl
from bs4 import BeautifulSoup
from pytube import YouTube

#download a song using song object
def downloadSong(song):
    print("Downloading", song.name)
    song.download()
    song.set_file_attributes()
    print(song.name, "Downloaded")

# returns a list of all track objects from a playlist
def getTracks(playlist_url, sp):
    allTracks = []
    if 'https://open.spotify.com/playlist/' in playlist_url:
        # New format: https://open.spotify.com/playlist/ID
        playlist_id = playlist_url.split('playlist/')[1].split('?')[0]
        playlist = sp.playlist(playlist_id)
    elif 'https://open.spotify.com/user/' in playlist_url:
        # Old format: https://open.spotify.com/user/USER/playlist/ID
        playlist_user = playlist_url.split('user/')[1].split('/')[0]
        playlist_id = playlist_url.split('playlist/')[1]
        playlist_id = playlist_id.split('?', 1)[0]
        playlist = sp.user_playlist(playlist_user, playlist_id)
    else:
        # Spotify URI format
        playlist_user = playlist_url.split(':')[0]
        playlist_id = playlist_url.split(':')[-1]
        playlist_id = playlist_id.split('?', 1)[0]
        playlist = sp.user_playlist(playlist_user, playlist_id)

    if 'https://open.spotify.com/playlist/' in playlist_url:
        # For new format, use playlist_tracks
        results = sp.playlist_tracks(playlist['id'])
        tracks = results
        for track in tracks['items']:
            allTracks.append(Song(track['track'], playlist['name']))

        while tracks['next']:
            tracks = sp.next(tracks)
            for track in tracks['items']:
                allTracks.append(Song(track['track'], playlist['name']))
    else:
        # For old format, use user_playlist
        results = sp.user_playlist(playlist_user, playlist['id'], fields="tracks,next")
        tracks = results['tracks']
        for track in tracks['items']:
            allTracks.append(Song(track['track'], playlist['name']))

        while tracks['next']:
            tracks = sp.next(tracks)
            for track in tracks['items']:
                allTracks.append(Song(track['track'], playlist['name']))

    return allTracks, playlist['name']

#delete all images in specified folder
def deleteAllImages(folder_name):
    for file in os.listdir(folder_name):
        if '.jpg' in file:
            os.remove(os.path.join(folder_name, file))

#Get URI from publisher attribute of mp3 file
def getUri(file):
    try:
        audiofile = eyed3.load(file)

    except TypeError as e:
        print("Error loading song for getting uri")
        print(e)

    try:
        return audiofile.tag.publisher

    except AttributeError as e:
        print("Error setting file attributes")
        print(e)

    except UnboundLocalError:
        pass

#Delete all songs from playlist folder that aren't in playlist
def delRemoved(playlistFolderURIs, songs, folder_name):
    playlistURIs=(song.uri for song in songs)
    songsToDel = list(set(playlistFolderURIs)-set(playlistURIs))
    for file in os.listdir(folder_name):
        if getUri(os.path.join(folder_name, file)) in songsToDel:
            os.remove(os.path.join(folder_name, file))



#class for spotify track
class Song():
    def __init__(self, track, folder_name):
        self.track = track
        self.name = track['name']
        self.name_file = track['name'].replace(':','').replace('?','').replace(';','').replace('<','').replace('>','').replace('*','').replace('|','').replace('/','').replace('\\','').replace('"','').replace('‘','\'').replace('á','a').replace('à','a').replace('ù','u').replace('Ä','A').replace("’","'")
        self.artists = [artist['name'] for artist in track['artists']]
        self.duration = int(track['duration_ms']/1000)
        dur_mins = str(float(track['duration_ms']/1000/60)).split('.')
        self.duration_mins = dur_mins[0] + ':' + str(float('0.'+ dur_mins[1])*60).split('.')[0]
        self.album = track['album']['name']
        self.art_urls = [art['url'] for art in track['album']['images']]
        self.uri = track['uri']
        self.folder_name = folder_name

    def get_link(self):
        videoList = []
        closestVideo = None
        closestDur = None
        durDiff = None
        textToSearch = self.name + ' ' + self.artists[0]
        query = urllib.parse.quote(textToSearch)
        url = "https://www.youtube.com/results?search_query=" + query
        response = urllib.request.urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html, 'html.parser')
        backupVid = None
        for vid in soup.findAll(attrs={'class':'yt-uix-tile-link'}):
            videoList.append('https://www.youtube.com' + vid['href'])

        for url in videoList[:3]:
            try:
                video = pafy.new(url)

            except ValueError:
                pass

            except Exception as e:
                print("Error using pafy: ", e)
                continue

            durDiff = abs(video.length - self.duration)
            if closestDur == None:
                closestDur = durDiff
                closestVideo = url

            elif durDiff < closestDur:
                backupVid = closestVideo
                closestDur = durDiff
                closestVideo = url

        if backupVid == None:
            backupVid = videoList[1]

        self.backupvid = backupVid
        self.closesturl = closestVideo
        self.video = pafy.new(closestVideo)



        

    def download(self):
        self.get_link()
        os.makedirs(self.folder_name, exist_ok=True)
        try:
            self.video.getbestaudio().download(filepath=os.path.join(self.folder_name, self.name_file))

        except:
            try:
                print("Error Downloading with Pafy...\nTrying pytube...")
                yt = YouTube(self.closesturl)
                stream = yt.streams.first()
                stream.download(os.path.join(self.folder_name, self.name_file))

            except:
                try:
                    print("Error with first url")
                    self.video = pafy.new(self.backupvid)
                    self.video.getbestaudio().download(filepath=os.path.join(self.folder_name, self.name_file))

                except:
                    print(self.closesturl)
                    print(self.backupvid)
                    yt = YouTube(self.backupvid)
                    stream = yt.streams.first()
                    stream.download(os.path.join(self.folder_name, self.name_file))



        FNULL = open(os.devnull, 'w')
        print("Converting", self.name)
        subprocess.call("ffmpeg -i \"" + os.path.join(self.folder_name, self.name_file)+"\" " + "\""+ os.path.join(self.folder_name, self.name_file)+".mp3\"", stdout=FNULL, stderr=subprocess.STDOUT)
        os.remove(os.path.join(self.folder_name, self.name_file))
        self.file = os.path.join(self.folder_name, self.name_file)+".mp3"

    # download a file from a url | returns file location
    def download_art(self):
        filename = os.path.join(self.folder_name, self.album + '.jpg')

        # check if file is already downloaded
        for file in os.listdir(self.folder_name):
            if self.album + '.jpg' == file:
                return filename
                
        print("Downloading Album Art for", self.name)
        try:
            res = requests.get(self.art_urls[0])
            res.raise_for_status()
                
            # Save the file to file location
            file = open(os.path.join(self.folder_name, os.path.basename(self.art_urls[0])), 'wb')
            for chunk in res.iter_content(100000):
                file.write(chunk)
            file.close()
        except requests.exceptions.MissingSchema:
            print('Error requests.exceptions.MissingSchema')

        except FileExistsError:
            pass

        #find then rename file to filename specified
        for file in os.listdir(self.folder_name):
            if file == self.art_urls[0].split('/')[-1]:
                try:
                    #print(file)
                    #print(os.path.join(self.folder_name, file))
                    #print(filename)
                    try:
                        os.rename(os.path.join(self.folder_name, file),filename)
                    except:
                        pass

                except FileExistsError:
                    pass

                return filename

        return filename

    # assigns id3 attributes to mp3 file
    def set_file_attributes(self):
        #TEMP SET VAR
        self.file = os.path.join(self.folder_name, self.name_file)+".mp3"

        try:
            audiofile = eyed3.load(self.file)

        except TypeError as e:
            print("Error loading song for setting attributes")
            print(e)

        try:
            try:
                self.art = self.download_art()
            except FileNotFoundError:
                print("Error setting art for", self.name)
                print(Exception)
            audiofile.tag.artist = ', '.join(self.artists)
            audiofile.tag.album = self.album
            audiofile.tag.title = self.name
            audiofile.tag.publisher = self.uri
            try:
                audiofile.tag.images.set(3, open(self.art,'rb').read(), 'image/jpeg')
            except:
                pass
            audiofile.tag.save(self.file)

        except AttributeError as e:
            print("Error setting file attributes")
            print(e)

        except UnboundLocalError:
            pass