import urllib, os, spotipy, subprocess, eyed3, requests
from bs4 import BeautifulSoup
from pytube import YouTube
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any

# Set pafy backend before importing
import os as os_env
os_env.environ['PAFY_BACKEND'] = 'internal'

try:
    import pafy
except ImportError:
    pafy = None
    print("Warning: pafy not available, using yt-dlp only")



def get_audio_bitrate(file_path):
    """Return the bitrate of the audio stream in bits per second or None."""
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error', '-select_streams', 'a:0',
                '-show_entries', 'stream=bit_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1', file_path
            ],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None

def adjust_audio_format(file_path, quiet=False):
    """Convert the downloaded file to flac or mp3 based on bitrate."""
    bitrate = get_audio_bitrate(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if bitrate and bitrate > 320000:
            if ext != '.flac':
                new_path = os.path.splitext(file_path)[0] + '.flac'
                FNULL = open(os.devnull, 'w')
                subprocess.call(['ffmpeg', '-y', '-i', file_path, new_path],
                                stdout=FNULL, stderr=subprocess.STDOUT)
                os.remove(file_path)
                return new_path
        else:
            if ext != '.mp3':
                new_path = os.path.splitext(file_path)[0] + '.mp3'
                FNULL = open(os.devnull, 'w')
                subprocess.call(['ffmpeg', '-y', '-i', file_path, new_path],
                                stdout=FNULL, stderr=subprocess.STDOUT)
                os.remove(file_path)
                return new_path
    except Exception:
        if not quiet:
            print(f"Format adjustment failed for {file_path}")
    return file_path

@dataclass
class DownloadProvider:
    """Configuration for a download provider"""
    name: str
    url_resolver: Callable[[str], Optional[str]]  # Function that takes query and returns download URL
    use_ytdlp: bool = True  # Whether to use yt-dlp for actual download
    direct_download: bool = False  # Whether to download directly without yt-dlp
    timeout: int = 300
    
def _ytdlp_download(song, url, quiet=False):
    """Common yt-dlp download logic"""
    os.makedirs(song.folder_name, exist_ok=True)
    output_path = os.path.join(song.folder_name, song.name_file + '.%(ext)s')
    cmd = [
        'yt-dlp', '--extract-audio', '--audio-format', 'best',
        '--audio-quality', '0', '--output', output_path, url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return False
    
    # Find downloaded file
    for f in os.listdir(song.folder_name):
        if f.startswith(song.name_file):
            song.file = os.path.join(song.folder_name, f)
            break
    
    if not song.file:
        return False
    
    song.file = adjust_audio_format(song.file, quiet=quiet)
    return True

def _direct_download(song, url, quiet=False):
    """Direct download without yt-dlp"""
    os.makedirs(song.folder_name, exist_ok=True)
    fname = os.path.join(song.folder_name, song.name_file + '.mp3')
    
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(fname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    
    song.file = adjust_audio_format(fname, quiet=quiet)
    return True

def _qobuz_download(song, url_data, quiet=False):
    """Special download function for Qobuz with quality selection"""
    if not url_data:
        return False
    
    url = url_data.get('url')
    if not url:
        return False

    bitrate = url_data.get('bitrate', 0)
    bit_depth = url_data.get('bit_depth')
    ext = '.flac' if (bit_depth and bitrate and bitrate > 320000) else '.mp3'

    os.makedirs(song.folder_name, exist_ok=True)
    fname = os.path.join(song.folder_name, song.name_file + ext)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(fname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    song.file = fname
    return True

def _generic_download(song, provider: DownloadProvider, quiet=False):
    """Generic download function that works with any provider"""
    try:
        query = f"{song.name} {song.artists[0]}"
        
        # Special handling for Qobuz
        if provider.name == 'Qobuz':
            url_data = provider.url_resolver(query)
            return _qobuz_download(song, url_data, quiet)
        
        url = provider.url_resolver(query)
        
        if not url:
            return False
        
        if provider.direct_download:
            return _direct_download(song, url, quiet)
        else:
            return _ytdlp_download(song, url, quiet)
            
    except Exception as e:
        if not quiet:
            print(f"{provider.name} download failed for {song.name}: {e}")
        return False

# URL resolver functions for each provider
def _resolve_bandcamp_url(query):
    """Find Bandcamp URL for a search query"""
    search_url = f"https://bandcamp.com/search?q={urllib.parse.quote(query)}"
    res = requests.get(search_url, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    link_tag = soup.select_one('li.searchresult a.itemurl')
    return link_tag['href'] if link_tag and link_tag.get('href') else None

def _resolve_soundcloud_url(query):
    """Generate SoundCloud search URL for yt-dlp"""
    return f'scsearch1:{query}'

def _resolve_jamendo_url(query):
    """Find Jamendo direct download URL"""
    client_id = os.getenv('JAMENDO_CLIENT_ID')
    if not client_id:
        return None
    
    api_url = (
        f"https://api.jamendo.com/v3.0/tracks/?client_id={client_id}&format=json"
        f"&limit=1&search={urllib.parse.quote(query)}"
    )
    res = requests.get(api_url, timeout=15)
    res.raise_for_status()
    data = res.json()
    tracks = data.get('results')
    if not tracks:
        return None
    return tracks[0].get('audiodownload') or tracks[0].get('audio')

def _resolve_qobuz_url(query):
    """Find Qobuz track and return download data"""
    q_email = os.getenv("QOBUZ_EMAIL")
    q_pass = os.getenv("QOBUZ_PASSWORD")
    q_app_id = os.getenv("QOBUZ_APP_ID")
    q_secrets = os.getenv("QOBUZ_SECRETS")

    if not all([q_email, q_pass, q_app_id, q_secrets]):
        return None

    try:
        from qobuz_dl.qopy import Client
    except Exception:
        return None

    try:
        secrets = [s for s in q_secrets.split(',') if s]
        client = Client(q_email, q_pass, q_app_id, secrets)
        res = client.search_tracks(query, limit=1)
        items = res.get('tracks', {}).get('items', [])
        if not items:
            return None

        track_id = items[0]['id']

        # Try hi-res >96kHz then <96kHz then lossless
        fmt_ids = [27, 7, 6]
        track_data = None
        for fmt in fmt_ids:
            try:
                track_data = client.get_track_url(track_id, fmt_id=fmt)
                if 'url' in track_data:
                    break
            except Exception:
                track_data = None
        if not track_data or 'url' not in track_data:
            # Fallback to 320k mp3
            track_data = client.get_track_url(track_id, fmt_id=5)

        return track_data
    except Exception:
        return None

# Provider configurations
PROVIDERS = {
    'qobuz': DownloadProvider(
        name='Qobuz',
        url_resolver=_resolve_qobuz_url,
        direct_download=True  # Uses special _qobuz_download function
    ),
    'bandcamp': DownloadProvider(
        name='Bandcamp',
        url_resolver=_resolve_bandcamp_url,
        use_ytdlp=True
    ),
    'soundcloud': DownloadProvider(
        name='SoundCloud', 
        url_resolver=_resolve_soundcloud_url,
        use_ytdlp=True
    ),
    'jamendo': DownloadProvider(
        name='Jamendo',
        url_resolver=_resolve_jamendo_url,
        direct_download=True
    )
}

def register_provider(key: str, provider: DownloadProvider):
    """Register a new download provider"""
    PROVIDERS[key] = provider

def create_provider_function(provider_key: str):
    """Create a download function for a provider"""
    def download_func(song, quiet=False):
        return _generic_download(song, PROVIDERS[provider_key], quiet)
    return download_func

# Simplified provider functions using the generic system
def download_from_qobuz(song, quiet=False):
    """Download a song from Qobuz if possible."""
    return _generic_download(song, PROVIDERS['qobuz'], quiet)

def download_from_bandcamp(song, quiet=False):
    """Attempt to download from Bandcamp using yt-dlp."""
    return _generic_download(song, PROVIDERS['bandcamp'], quiet)

def download_from_soundcloud(song, quiet=False):
    """Download audio from SoundCloud via yt-dlp search."""
    return _generic_download(song, PROVIDERS['soundcloud'], quiet)

def download_from_jamendo(song, quiet=False):
    """Download from Jamendo using its open API."""
    return _generic_download(song, PROVIDERS['jamendo'], quiet)

#download a song using song object
def downloadSong(song, quiet=False):
    if not quiet:
        print("Downloading", song.name)
    song.download(quiet=quiet)
    if song.file and os.path.exists(song.file):
        song.set_file_attributes(quiet=quiet)
        # Delete album art after metadata has been applied
        if getattr(song, 'art', None) and os.path.exists(song.art):
            try:
                os.remove(song.art)
            except FileNotFoundError:
                pass
            song.art = None
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

        # Try high quality download sources in order
        if download_from_qobuz(self, quiet=quiet):
            return
        if download_from_bandcamp(self, quiet=quiet):
            return
        if download_from_soundcloud(self, quiet=quiet):
            return
        if download_from_jamendo(self, quiet=quiet):
            return

        self.get_link(quiet=quiet)
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
                if not quiet:
                    print(f"Primary download failed for {self.name}, trying backup...")
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
                    
        except Exception as e:
            if not quiet:
                print(f"yt-dlp failed for {self.name}: {e}")
            # Fallback to old method
            try:
                if self.video and pafy:
                    self.video.getbestaudio().download(filepath=os.path.join(self.folder_name, self.name_file))
                    
                    FNULL = open(os.devnull, 'w')
                    if not quiet:
                        print("Converting", self.name)
                    subprocess.call("ffmpeg -i \"" + os.path.join(self.folder_name, self.name_file)+"\" " + "\""+ final_path +"\"", stdout=FNULL, stderr=subprocess.STDOUT)
                    os.remove(os.path.join(self.folder_name, self.name_file))
                    self.file = final_path
                else:
                    raise Exception("No pafy/video object available")
                    
            except Exception as e2:
                if not quiet:
                    print(f"All download methods failed for {self.name}: {e2}")
                self.file = None

    # download a file from a url | returns file location
    def download_art(self, quiet=False):
        # Clean album name for filename
        clean_album = self.album.replace(':','').replace('?','').replace(';','').replace('<','').replace('>','').replace('*','').replace('|','').replace('/','').replace('\\','').replace('"','').replace("'","'")
        filename = os.path.join(self.folder_name, clean_album + '.jpg')

        # check if file is already downloaded
        for file in os.listdir(self.folder_name):
            if clean_album + '.jpg' == file:
                return filename
                
        if not quiet:
            print("Downloading Album Art for", self.name)
        try:
            res = requests.get(self.art_urls[0])
            res.raise_for_status()
            
            # Create a safe temporary filename
            import tempfile
            temp_filename = os.path.join(self.folder_name, f"temp_art_{hash(self.art_urls[0]) % 10000}.jpg")
                
            # Save the file to temp location first
            with open(temp_filename, 'wb') as file:
                for chunk in res.iter_content(100000):
                    file.write(chunk)
            
            # Rename to final filename
            try:
                if os.path.exists(filename):
                    os.remove(filename)
                os.rename(temp_filename, filename)
            except Exception as e:
                if not quiet:
                    print(f"Error renaming art file: {e}")
                # If rename fails, just use the temp file
                filename = temp_filename
                
        except requests.exceptions.MissingSchema:
            if not quiet:
                print('Error requests.exceptions.MissingSchema')
        except Exception as e:
            if not quiet:
                print(f"Error downloading album art: {e}")

        return filename

    # assigns id3 attributes to mp3 file
    def set_file_attributes(self, quiet=False):
        # Ensure we have the downloaded file path
        if not self.file:
            self.file = os.path.join(self.folder_name, self.name_file + ".mp3")

        # Check if file exists first
        if not os.path.exists(self.file):
            if not quiet:
                print(f"Cannot set attributes: file {self.file} does not exist")
            return

        try:
            audiofile = eyed3.load(self.file)
            
            # Check if eyed3 successfully loaded the file
            if audiofile is None or audiofile.tag is None:
                if not quiet:
                    print(f"Cannot set attributes: {self.file} is not a valid audio file")
                return

        except TypeError as e:
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

# Example of how to add a new provider:
# def _resolve_newsite_url(query):
#     """Find NewSite URL for a search query"""
#     # Your search logic here
#     return url_or_none
# 
# register_provider('newsite', DownloadProvider(
#     name='NewSite',
#     url_resolver=_resolve_newsite_url,
#     use_ytdlp=True  # or direct_download=True
# ))
# 
# download_from_newsite = create_provider_function('newsite')

# Here's a real example - adding Freesound.org support:
def _resolve_freesound_url(query):
    """Find Freesound.org URL for a search query (requires API key)"""
    api_key = os.getenv('FREESOUND_API_KEY')
    if not api_key:
        return None
    
    try:
        # Freesound API search
        api_url = f"https://freesound.org/apiv2/search/text/?query={urllib.parse.quote(query)}&token={api_key}&format=json&fields=id,name,previews"
        res = requests.get(api_url, timeout=15)
        res.raise_for_status()
        data = res.json()
        
        if not data.get('results'):
            return None
            
        # Get the first result's preview URL
        sound = data['results'][0]
        preview_url = sound.get('previews', {}).get('preview-hq-mp3')
        return preview_url
    except Exception:
        return None

# Register the new provider (commented out since most users won't have API key)
# register_provider('freesound', DownloadProvider(
#     name='Freesound',
#     url_resolver=_resolve_freesound_url,
#     direct_download=True
# ))
# download_from_freesound = create_provider_function('freesound')