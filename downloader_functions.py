import urllib
import os
import spotipy
import eyed3
import asyncio
import aiohttp
from yt_dlp import YoutubeDL

# Set pafy backend before importing
import os as os_env
os_env.environ['PAFY_BACKEND'] = 'internal'

try:
    import pafy
except ImportError:
    pafy = None
    print("Warning: pafy not available, using yt-dlp only")

#download a song using song object
async def downloadSong(song, semaphore):
    async with semaphore:
        print("Downloading", song.name)
        await song.download()
        if song.file and os.path.exists(song.file):
            await song.set_file_attributes()
            print(song.name, "Downloaded")
        else:
            print(f"Failed to download {song.name}")

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
        self.name_file = track['name'].replace(':','').replace('?','').replace(';','').replace('<','').replace('>','').replace('*','').replace('|','').replace('/','').replace('\\','').replace('"','').replace("'","'").replace('á','a').replace('à','a').replace('ù','u').replace('Ä','A')
        self.artists = [artist['name'] for artist in track['artists']]
        self.duration = int(track['duration_ms']/1000)
        dur_mins = str(float(track['duration_ms']/1000/60)).split('.')
        self.duration_mins = dur_mins[0] + ':' + str(float('0.'+ dur_mins[1])*60).split('.')[0]
        self.album = track['album']['name']
        self.art_urls = [art['url'] for art in track['album']['images']]
        self.uri = track['uri']
        self.folder_name = folder_name

    async def get_link(self):
        import json
        textToSearch = self.name + ' ' + self.artists[0]

        async def extract():
            ydl_opts = {'quiet': True, 'skip_download': True}
            with YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(f'ytsearch15:{textToSearch}', download=False)

        try:
            info = await asyncio.to_thread(extract)
            videos = []
            for entry in info.get('entries', []):
                videos.append({
                    'url': entry.get('webpage_url'),
                    'duration': entry.get('duration', 0),
                    'title': entry.get('title', '')
                })

            if not videos:
                raise Exception("No videos found")

            import difflib
            query = (self.name + ' ' + self.artists[0]).lower()
            bestScore = None
            bestVideo = None
            backupVid = None

            for video in videos:
                title = video['title'].lower()
                ratio = difflib.SequenceMatcher(None, query, title).ratio()
                penalty = 0
                if video['duration']:
                    penalty = abs(video['duration'] - self.duration) / self.duration
                if any(word in title for word in ['cover', 'karaoke', 'live', 'remix', 'instrumental']):
                    ratio *= 0.8
                score = ratio - penalty * 0.1

                if bestScore is None or score > bestScore:
                    backupVid = bestVideo
                    bestScore = score
                    bestVideo = video['url']

            if bestVideo is None:
                bestVideo = videos[0]['url']
            if backupVid is None and len(videos) > 1:
                backupVid = videos[1]['url']
            elif backupVid is None:
                backupVid = bestVideo

            self.closesturl = bestVideo
            self.backupvid = backupVid

            try:
                if pafy:
                    self.video = pafy.new(bestVideo)
                else:
                    self.video = None
            except Exception:
                self.video = None

        except Exception as e:
            print(f"Error in get_link for {self.name}: {e}")
            query = urllib.parse.quote(textToSearch)
            self.closesturl = f"https://www.youtube.com/results?search_query={query}"
            self.backupvid = self.closesturl
            self.video = None



        

    async def download(self):
        await self.get_link()
        os.makedirs(self.folder_name, exist_ok=True)

        output_path = os.path.join(self.folder_name, self.name_file + ".%(ext)s")
        final_path = os.path.join(self.folder_name, self.name_file + ".mp3")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',
            }]
        }

        async def run_download(url):
            def _dl():
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            return await asyncio.to_thread(_dl)

        try:
            await run_download(self.closesturl)
        except Exception as e:
            print(f"Primary download failed for {self.name}, trying backup...")
            try:
                await run_download(self.backupvid)
            except Exception as e2:
                print(f"Both downloads failed: {e2}")
                self.file = None
                return

        found = False
        for file in os.listdir(self.folder_name):
            if file.startswith(self.name_file) and file.endswith('.mp3'):
                self.file = os.path.join(self.folder_name, file)
                found = True
                break
        if not found:
            for file in os.listdir(self.folder_name):
                if file.startswith(self.name_file):
                    old_path = os.path.join(self.folder_name, file)
                    os.rename(old_path, final_path)
                    self.file = final_path
                    found = True
                    break
        if not found:
            self.file = final_path


    # download a file from a url | returns file location
    async def download_art(self):
        filename = os.path.join(self.folder_name, self.album + '.jpg')

        # check if file is already downloaded
        for file in os.listdir(self.folder_name):
            if self.album + '.jpg' == file:
                return filename
                
        print("Downloading Album Art for", self.name)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.art_urls[0]) as res:
                    res.raise_for_status()
                    data = await res.read()

            with open(os.path.join(self.folder_name, os.path.basename(self.art_urls[0])), 'wb') as file:
                file.write(data)
        except Exception as e:
            print(f'Error downloading album art: {e}')

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
    async def set_file_attributes(self):
        #TEMP SET VAR
        self.file = os.path.join(self.folder_name, self.name_file)+".mp3"

        try:
            audiofile = await asyncio.to_thread(eyed3.load, self.file)

        except TypeError as e:
            print("Error loading song for setting attributes")
            print(e)

        try:
            try:
                self.art = await self.download_art()
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
            await asyncio.to_thread(audiofile.tag.save, self.file)

        except AttributeError as e:
            print("Error setting file attributes")
            print(e)

        except UnboundLocalError:
            pass