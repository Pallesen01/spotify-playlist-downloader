import spotipy
import os
import shelve
import sys
from datetime import timedelta
from collections import defaultdict
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

def get_spotify_client():
    """Initialize Spotify client with existing auth setup"""
    shelveFile = shelve.open('spotify_data')
    
    client_id = shelveFile.get('SPOTIPY_CLIENT_ID', os.environ.get('SPOTIPY_CLIENT_ID'))
    client_secret = shelveFile.get('SPOTIPY_CLIENT_SECRET', os.environ.get('SPOTIPY_CLIENT_SECRET'))
    
    if not client_id or not client_secret:
        print("Spotify credentials not found. Please run the main downloader first to set them up.")
        sys.exit(1)
    
    # Use OAuth for user-specific data (required to see who added tracks)
    oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri='http://127.0.0.1:8888/callback',
        scope='playlist-read-private playlist-read-collaborative',
        cache_path='spotify_token_cache',
        open_browser=False
    )
    
    token_info = oauth.get_cached_token()
    if not token_info:
        print("Need to authenticate first. Please run the main downloader with --user-auth flag first.")
        sys.exit(1)
    
    shelveFile.close()
    return spotipy.Spotify(auth=token_info['access_token'])

def extract_playlist_id(url):
    """Extract playlist ID from Spotify URL"""
    if 'playlist/' in url:
        return url.split('playlist/')[1].split('?')[0]
    elif 'spotify:playlist:' in url:
        return url.split('spotify:playlist:')[1]
    else:
        print("Invalid Spotify playlist URL")
        sys.exit(1)

def format_duration(ms):
    """Convert milliseconds to readable format"""
    seconds = ms // 1000
    return str(timedelta(seconds=seconds))

def get_user_display_name(sp, user_id):
    """Get display name for a user ID"""
    try:
        if not user_id or user_id == 'Unknown':
            return user_id
        
        # If it already looks like a display name (has spaces, not all lowercase), keep it
        if ' ' in user_id or (user_id[0].isupper() and not user_id.islower()):
            return user_id
            
        user = sp.user(user_id)
        return user.get('display_name') or user.get('id') or user_id
    except:
        return user_id

def analyze_collaborator_contributions(playlist_url):
    """Analyze who added what to a collaborative playlist"""
    sp = get_spotify_client()
    playlist_id = extract_playlist_id(playlist_url)
    
    try:
        # Get playlist info
        playlist = sp.playlist(playlist_id)
        print(f"\nAnalyzing playlist: {playlist['name']}")
        print(f"Total tracks: {playlist['tracks']['total']}")
        print("-" * 50)
        
        # Get all tracks with pagination
        tracks = []
        results = sp.playlist_tracks(playlist_id)
        tracks.extend(results['items'])
        
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        # Analyze contributions and collect user IDs
        contributor_stats = defaultdict(lambda: {'count': 0, 'duration': 0, 'songs': []})
        user_ids_to_resolve = set()
        
        for track_item in tracks:
            if track_item['track'] and track_item['track']['duration_ms']:
                # Handle different ways added_by info might be structured
                added_by = 'Unknown'
                if track_item.get('added_by'):
                    if isinstance(track_item['added_by'], dict):
                        added_by = track_item['added_by'].get('display_name') or track_item['added_by'].get('id') or 'Unknown'
                    else:
                        added_by = str(track_item['added_by'])
                
                # If it looks like a username/ID (not a display name), add to resolution list
                if (added_by != 'Unknown' and 
                    not (' ' in added_by or (added_by[0].isupper() and not added_by.islower()))):
                    user_ids_to_resolve.add(added_by)
                
                duration_ms = track_item['track']['duration_ms']
                song_name = track_item['track']['name']
                artist_names = ', '.join([artist['name'] for artist in track_item['track']['artists']])
                
                contributor_stats[added_by]['count'] += 1
                contributor_stats[added_by]['duration'] += duration_ms
                contributor_stats[added_by]['songs'].append(f"{song_name} - {artist_names}")
        
        # Resolve user IDs to display names
        id_to_name = {}
        for user_id in user_ids_to_resolve:
            display_name = get_user_display_name(sp, user_id)
            if display_name != user_id:
                id_to_name[user_id] = display_name
        
        # Update contributor stats with resolved names
        if id_to_name:
            updated_stats = defaultdict(lambda: {'count': 0, 'duration': 0, 'songs': []})
            for contributor, stats in contributor_stats.items():
                final_name = id_to_name.get(contributor, contributor)
                updated_stats[final_name]['count'] += stats['count']
                updated_stats[final_name]['duration'] += stats['duration']
                updated_stats[final_name]['songs'].extend(stats['songs'])
            contributor_stats = updated_stats
        
        # Sort contributors by total duration
        sorted_contributors = sorted(contributor_stats.items(), 
                                   key=lambda x: x[1]['duration'], 
                                   reverse=True)
        
        # Display results
        total_duration = sum(stats['duration'] for stats in contributor_stats.values())
        
        for contributor, stats in sorted_contributors:
            percentage = (stats['duration'] / total_duration) * 100 if total_duration > 0 else 0
            print(f"\n{contributor}:")
            print(f"  Songs added: {stats['count']}")
            print(f"  Total duration: {format_duration(stats['duration'])} ({percentage:.1f}%)")
            
            # Show first few songs as examples
            if len(stats['songs']) <= 3:
                print(f"  Songs: {', '.join(stats['songs'])}")
            else:
                print(f"  Sample songs: {', '.join(stats['songs'][:3])} ... (+{len(stats['songs'])-3} more)")
        
        print(f"\nPlaylist totals:")
        print(f"  Total duration: {format_duration(total_duration)}")
        print(f"  Total contributors: {len(contributor_stats)}")
        
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 403:
            print("Access denied. This playlist might be private or you don't have permission to view it.")
        else:
            print(f"Spotify API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Spotify Playlist Collaborator Analysis")
    print("=" * 40)
    
    playlist_url = input("Enter Spotify playlist URL: ").strip()
    if not playlist_url:
        print("No URL provided!")
        sys.exit(1)
    
    analyze_collaborator_contributions(playlist_url) 