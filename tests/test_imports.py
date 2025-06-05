"""
Test that all imports work with the new structure
"""
import os
import sys
import unittest

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class TestImports(unittest.TestCase):
    def test_core_imports(self):
        """Test that core modules can be imported"""
        from src.core.downloader_functions import Song, getTracks
        from src.core.playlist_downloader import main

    def test_web_imports(self):
        """Test that web modules can be imported"""
        from src.web.web_interface import app, load_config, load_playlists

if __name__ == '__main__':
    unittest.main() 