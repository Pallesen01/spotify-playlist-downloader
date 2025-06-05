#!/usr/bin/env python3
"""
Download Provider Diagnostic Tool
Tests each download provider to see which ones are working.
"""

import os
import sys
import subprocess
import requests
from urllib.parse import quote
import tempfile
import shutil

def test_command(cmd, name, timeout=30):
    """Test if a command exists and works"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"{name} timed out"
    except Exception as e:
        return False, "", str(e)

def test_python_import(module_name):
    """Test if a Python module can be imported"""
    try:
        __import__(module_name)
        return True, f"{module_name} imported successfully"
    except ImportError as e:
        return False, f"Failed to import {module_name}: {e}"

def test_qobuz():
    """Test Qobuz provider"""
    print("🎵 Testing Qobuz...")
    
    # Check environment variables
    required_vars = ['QOBUZ_EMAIL', 'QOBUZ_PASSWORD', 'QOBUZ_APP_ID', 'QOBUZ_SECRETS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"   ❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check qobuz_dl module
    success, msg = test_python_import('qobuz_dl.qopy')
    if not success:
        print(f"   ❌ {msg}")
        return False
    
    print("   ✅ Qobuz credentials and module available")
    return True

def test_bandcamp():
    """Test Bandcamp provider"""
    print("🎸 Testing Bandcamp...")
    
    # Test yt-dlp availability
    success, stdout, stderr = test_command('yt-dlp --version', 'yt-dlp')
    if not success:
        print(f"   ❌ yt-dlp not available: {stderr}")
        return False
    
    # Test basic web connectivity to Bandcamp
    try:
        response = requests.get('https://bandcamp.com', timeout=10)
        if response.status_code == 200:
            print("   ✅ Bandcamp accessible via yt-dlp")
            return True
        else:
            print(f"   ❌ Bandcamp returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot reach Bandcamp: {e}")
        return False

def test_soundcloud():
    """Test SoundCloud provider"""
    print("☁️ Testing SoundCloud...")
    
    # Test yt-dlp with SoundCloud search
    success, stdout, stderr = test_command('yt-dlp --version', 'yt-dlp')
    if not success:
        print(f"   ❌ yt-dlp not available: {stderr}")
        return False
    
    # Test SoundCloud search capability
    test_cmd = 'yt-dlp --dump-json --no-download "scsearch1:test"'
    success, stdout, stderr = test_command(test_cmd, 'SoundCloud search', timeout=15)
    
    if success and stdout.strip():
        print("   ✅ SoundCloud search working via yt-dlp")
        return True
    else:
        print(f"   ❌ SoundCloud search failed: {stderr}")
        return False

def test_jamendo():
    """Test Jamendo provider"""
    print("🎼 Testing Jamendo...")
    
    client_id = os.getenv('JAMENDO_CLIENT_ID')
    if not client_id:
        print("   ❌ Missing JAMENDO_CLIENT_ID environment variable")
        return False
    
    # Test Jamendo API
    try:
        api_url = f"https://api.jamendo.com/v3.0/tracks/?client_id={client_id}&format=json&limit=1&search=test"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                print("   ✅ Jamendo API accessible")
                return True
            else:
                print("   ❌ Jamendo API returned unexpected format")
                return False
        else:
            print(f"   ❌ Jamendo API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot reach Jamendo API: {e}")
        return False

def test_youtube():
    """Test YouTube provider (primary fallback)"""
    print("📺 Testing YouTube...")
    
    # Test yt-dlp
    success, stdout, stderr = test_command('yt-dlp --version', 'yt-dlp')
    if not success:
        print(f"   ❌ yt-dlp not available: {stderr}")
        yt_dlp_ok = False
    else:
        print(f"   ✅ yt-dlp version: {stdout.strip()}")
        yt_dlp_ok = True
    
    # Test YouTube search
    if yt_dlp_ok:
        test_cmd = 'yt-dlp --dump-json --no-download "ytsearch1:test song"'
        success, stdout, stderr = test_command(test_cmd, 'YouTube search', timeout=15)
        
        if success and stdout.strip():
            print("   ✅ YouTube search working")
        else:
            print(f"   ❌ YouTube search failed: {stderr}")
            yt_dlp_ok = False
    
    # Test pafy (legacy fallback)
    success, msg = test_python_import('pafy')
    if success:
        print("   ✅ pafy available (legacy fallback)")
    else:
        print(f"   ⚠️ pafy not available: {msg}")
    
    return yt_dlp_ok

def test_ffmpeg():
    """Test FFmpeg for audio conversion"""
    print("🔧 Testing FFmpeg...")
    
    success, stdout, stderr = test_command('ffmpeg -version', 'ffmpeg')
    if success:
        version_line = stdout.split('\n')[0]
        print(f"   ✅ {version_line}")
        return True
    else:
        print(f"   ❌ FFmpeg not available: {stderr}")
        return False

def test_actual_download():
    """Test an actual download with a short public domain track"""
    print("🧪 Testing actual download...")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "test.%(ext)s")
        
        # Try to download a very short public domain track
        test_cmd = f'yt-dlp --extract-audio --audio-format mp3 --audio-quality 9 --output "{output_path}" "https://www.youtube.com/watch?v=dQw4w9WgXcQ"'
        
        success, stdout, stderr = test_command(test_cmd, 'actual download test', timeout=60)
        
        if success:
            # Check if file was created
            files = os.listdir(temp_dir)
            mp3_files = [f for f in files if f.endswith('.mp3')]
            if mp3_files:
                print("   ✅ Download test successful")
                return True
            else:
                print("   ❌ Download completed but no MP3 file found")
                return False
        else:
            print(f"   ❌ Download test failed: {stderr}")
            return False

def main():
    print("🔍 Download Provider Diagnostic Tool")
    print("=" * 50)
    
    results = {}
    
    # Test each provider
    results['qobuz'] = test_qobuz()
    results['bandcamp'] = test_bandcamp()
    results['soundcloud'] = test_soundcloud()
    results['jamendo'] = test_jamendo()
    results['youtube'] = test_youtube()
    results['ffmpeg'] = test_ffmpeg()
    
    print("\n" + "=" * 50)
    print("🧪 Running actual download test...")
    results['download_test'] = test_actual_download()
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    working_providers = []
    broken_providers = []
    
    provider_names = {
        'qobuz': 'Qobuz (High Quality)',
        'bandcamp': 'Bandcamp',
        'soundcloud': 'SoundCloud', 
        'jamendo': 'Jamendo',
        'youtube': 'YouTube (Primary)',
        'ffmpeg': 'FFmpeg (Audio Processing)',
        'download_test': 'Actual Download Test'
    }
    
    for provider, status in results.items():
        name = provider_names.get(provider, provider)
        if status:
            working_providers.append(name)
            print(f"✅ {name}")
        else:
            broken_providers.append(name)
            print(f"❌ {name}")
    
    print(f"\n📈 Working: {len(working_providers)}/{len(results)}")
    print(f"📉 Broken: {len(broken_providers)}/{len(results)}")
    
    if not results['youtube']:
        print("\n⚠️  WARNING: YouTube provider is broken - this is the primary fallback!")
    
    if not results['ffmpeg']:
        print("\n⚠️  WARNING: FFmpeg is not available - audio conversion will fail!")
    
    if results['download_test']:
        print("\n🎉 Good news: Basic downloading is working!")
    else:
        print("\n💥 Bad news: Downloads are completely broken!")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if not results['youtube']:
        print("   • Install/update yt-dlp: pip install -U yt-dlp")
    if not results['ffmpeg']:
        print("   • Install FFmpeg from https://ffmpeg.org/")
    if not results['qobuz'] and any(os.getenv(var) for var in ['QOBUZ_EMAIL', 'QOBUZ_PASSWORD', 'QOBUZ_APP_ID', 'QOBUZ_SECRETS']):
        print("   • Install qobuz-dl: pip install qobuz-dl")
    if not results['jamendo'] and os.getenv('JAMENDO_CLIENT_ID'):
        print("   • Check your JAMENDO_CLIENT_ID is valid")

if __name__ == "__main__":
    main() 