import urllib, os, spotipy, subprocess, eyed3, requests, json
from bs4 import BeautifulSoup
from pytube import YouTube
from mutagen.flac import FLAC

# Set pafy backend before importing
import os as os_env
os_env.environ['PAFY_BACKEND'] = 'internal'

try:
    import pafy
except ImportError:
    pafy = None
    print("Warning: pafy not available, using yt-dlp only")

#download a song using song object
def downloadSong(song, quiet=False):
    if not quiet:
        print("Downloading", song.name)
    song.download(quiet=quiet)
    if song.file and os.path.exists(song.file):
        song.set_file_attributes(quiet=quiet)
        if not quiet:
            print(song.name, "Downloaded")
    else:
        if not quiet:
            print(f"Failed to download {song.name}")

# returns a list of all track objects from a playlist
def getTracks(playlist_url, sp, limit=None):
    """Return a list of Song objects from a playlist.

    Parameters
    ----------
    playlist_url : str
        Spotify playlist URL or URI.
    sp : spotipy.Spotify
        Authenticated Spotipy client.
    limit : int, optional
        Maximum number of tracks to return. If None, return all tracks.
    """
    from tqdm import tqdm

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

    # Get total track count for progress bar
    total_tracks = playlist['tracks']['total']
    if limit is not None:
        progress_total = min(limit, total_tracks)
    else:
        progress_total = total_tracks
    progress_bar = tqdm(total=progress_total, desc="Getting playlist tracks", unit="track",
                       bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')

    if 'https://open.spotify.com/playlist/' in playlist_url:
        # For new format, use playlist_tracks
        results = sp.playlist_tracks(playlist['id'])
        tracks = results
        for track in tracks['items']:
            allTracks.append(Song(track['track'], playlist['name']))
            progress_bar.update(1)
            if limit is not None and len(allTracks) >= limit:
                progress_bar.close()
                return allTracks, playlist['name']

        while tracks['next'] and (limit is None or len(allTracks) < limit):
            tracks = sp.next(tracks)
            for track in tracks['items']:
                allTracks.append(Song(track['track'], playlist['name']))
                progress_bar.update(1)
                if limit is not None and len(allTracks) >= limit:
                    progress_bar.close()
                    return allTracks, playlist['name']
    else:
        # For old format, use user_playlist
        results = sp.user_playlist(playlist_user, playlist['id'], fields="tracks,next")
        tracks = results['tracks']
        for track in tracks['items']:
            allTracks.append(Song(track['track'], playlist['name']))
            progress_bar.update(1)
            if limit is not None and len(allTracks) >= limit:
                progress_bar.close()
                return allTracks, playlist['name']

        while tracks['next'] and (limit is None or len(allTracks) < limit):
            tracks = sp.next(tracks)
            for track in tracks['items']:
                allTracks.append(Song(track['track'], playlist['name']))
                progress_bar.update(1)
                if limit is not None and len(allTracks) >= limit:
                    progress_bar.close()
                    return allTracks, playlist['name']

    progress_bar.close()
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
        
        # Check if eyed3 successfully loaded the file
        if audiofile is None or audiofile.tag is None:
            return None

        return audiofile.tag.publisher

    except (TypeError, AttributeError) as e:
        print("Error loading song for getting uri")
        print(e)
        return None

    except UnboundLocalError:
        return None

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

    def get_link(self, quiet=False):
        import json
        import subprocess
        
        textToSearch = self.name + ' ' + self.artists[0]
        
        try:
            # Use yt-dlp to search YouTube
            search_cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                '--flat-playlist',
                f'ytsearch15:{textToSearch}'
            ]
            
            result = subprocess.run(search_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"yt-dlp search failed: {result.stderr}")
            
            videos = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        video_info = json.loads(line)
                        videos.append({
                            'url': f"https://www.youtube.com/watch?v={video_info['id']}",
                            'duration': video_info.get('duration', 0),
                            'title': video_info.get('title', '')
                        })
                    except json.JSONDecodeError:
                        continue
            
            if not videos:
                raise Exception("No videos found")
            
            # Score videos based on title similarity and duration difference
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

            closestVideo = bestVideo
                
            self.closesturl = closestVideo
            self.backupvid = backupVid
            
            # Try to create pafy object for compatibility
            try:
                if pafy:
                    self.video = pafy.new(closestVideo)
                else:
                    self.video = None
            except:
                self.video = None
                
        except Exception as e:
            if not quiet:
                print(f"Error in get_link for {self.name}: {e}")
            # Fallback: create a simple search URL
            query = urllib.parse.quote(textToSearch)
            self.closesturl = f"https://www.youtube.com/results?search_query={query}"
            self.backupvid = self.closesturl
            self.video = None



        

    def download(self, quiet=False):
        import subprocess

        self.get_link(quiet=quiet)
        os.makedirs(self.folder_name, exist_ok=True)

        output_path = os.path.join(self.folder_name, self.name_file + ".%(ext)s")
        flac_path = os.path.join(self.folder_name, self.name_file + ".flac")
        mp3_path = os.path.join(self.folder_name, self.name_file + ".mp3")

        try:
            # Attempt high fidelity download first
            info_cmd = [
                'yt-dlp', '-f', 'bestaudio', '--no-warnings', '--skip-download', '--print-json',
                self.closesturl
            ]
            info_res = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
            abr = 0
            ext = None
            if info_res.returncode == 0 and info_res.stdout:
                try:
                    info = json.loads(info_res.stdout.splitlines()[0])
                    abr = info.get('abr', 0)
                    ext = info.get('ext')
                except json.JSONDecodeError:
                    pass

            dl_cmd = ['yt-dlp', '-f', 'bestaudio', '-o', output_path, self.closesturl]
            result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise Exception(result.stderr)

            if ext:
                downloaded_file = output_path.replace('%(ext)s', ext)
            else:
                downloaded_file = None

            if not downloaded_file or not os.path.exists(downloaded_file):
                for f in os.listdir(self.folder_name):
                    if f.startswith(self.name_file):
                        downloaded_file = os.path.join(self.folder_name, f)
                        break

            if not downloaded_file or not os.path.exists(downloaded_file):
                raise Exception('Downloaded file not found')

            FNULL = open(os.devnull, 'w')
            if abr and abr > 320:
                convert_cmd = ['ffmpeg', '-y', '-i', downloaded_file, '-vn', '-acodec', 'flac', flac_path]
                subprocess.run(convert_cmd, stdout=FNULL, stderr=FNULL)
                os.remove(downloaded_file)
                self.file = flac_path
            else:
                convert_cmd = ['ffmpeg', '-y', '-i', downloaded_file, '-vn', '-acodec', 'libmp3lame', '-ab', '320k', mp3_path]
                subprocess.run(convert_cmd, stdout=FNULL, stderr=FNULL)
                os.remove(downloaded_file)
                self.file = mp3_path

        except Exception as e:
            if not quiet:
                print(f"High fidelity method failed for {self.name}: {e}")
            # Fallback to previous implementation
            try:
                download_cmd = [
                    'yt-dlp',
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',
                    '--output', output_path,
                    self.closesturl
                ]

                result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    if not quiet:
                        print(f"Primary download failed for {self.name}, trying backup...")
                    download_cmd[-1] = self.backupvid
                    result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode != 0:
                        raise Exception(result.stderr)

                for file in os.listdir(self.folder_name):
                    if file.startswith(self.name_file) and file.endswith('.mp3'):
                        self.file = os.path.join(self.folder_name, file)
                        break
                else:
                    self.file = mp3_path

            except Exception as e2:
                if not quiet:
                    print(f"All download methods failed for {self.name}: {e2}")
                try:
                    if self.video and pafy:
                        self.video.getbestaudio().download(filepath=os.path.join(self.folder_name, self.name_file))
                        FNULL = open(os.devnull, 'w')
                        if not quiet:
                            print("Converting", self.name)
                        subprocess.call("ffmpeg -i \"" + os.path.join(self.folder_name, self.name_file)+"\" \""+ mp3_path +"\"", stdout=FNULL, stderr=subprocess.STDOUT)
                        os.remove(os.path.join(self.folder_name, self.name_file))
                        self.file = mp3_path
                    else:
                        raise Exception("No pafy/video object available")
                except Exception as e3:
                    if not quiet:
                        print(f"All download methods failed for {self.name}: {e3}")
                    self.file = None

    # download a file from a url | returns file location
    def download_art(self, quiet=False):
        filename = os.path.join(self.folder_name, self.album + '.jpg')

        # check if file is already downloaded
        for file in os.listdir(self.folder_name):
            if self.album + '.jpg' == file:
                return filename
                
        if not quiet:
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
    def set_file_attributes(self, quiet=False):
        ext = os.path.splitext(self.file)[1].lower()

        # Check if file exists first
        if not os.path.exists(self.file):
            if not quiet:
                print(f"Cannot set attributes: file {self.file} does not exist")
            return

        try:
            if ext == '.flac':
                audiofile = FLAC(self.file)
            else:
                audiofile = eyed3.load(self.file)
                if audiofile is None or audiofile.tag is None:
                    if not quiet:
                        print(f"Cannot set attributes: {self.file} is not a valid audio file")
                    return
        except Exception as e:
            if not quiet:
                print("Error loading song for setting attributes")
                print(e)
            return

        try:
            try:
                self.art = self.download_art(quiet=quiet)
            except FileNotFoundError:
                if not quiet:
                    print("Error setting art for", self.name)
                    print(Exception)
            if ext == '.flac':
                from mutagen.flac import Picture
                audiofile['artist'] = ', '.join(self.artists)
                audiofile['album'] = self.album
                audiofile['title'] = self.name
                audiofile['publisher'] = self.uri
                try:
                    pic = Picture()
                    pic.type = 3
                    pic.mime = 'image/jpeg'
                    pic.data = open(self.art, 'rb').read()
                    audiofile.add_picture(pic)
                except Exception:
                    pass
                audiofile.save()
            else:
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
            if not quiet:
                print("Error setting file attributes")
                print(e)

        except UnboundLocalError:
            pass
