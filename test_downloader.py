import os
import sys
import tempfile
import types
from unittest import mock


def _start_dummy_modules():
    modules = {}
    for name in ["pafy", "spotipy", "youtube_dl", "pytube", "bs4", "requests", "eyed3"]:
        if name not in sys.modules:
            dummy = types.ModuleType(name)
            if name == "bs4":
                class DummySoup:
                    def __init__(self, *a, **k):
                        pass

                    def findAll(self, *a, **k):
                        return []

                dummy.BeautifulSoup = DummySoup
            if name == "pytube":
                dummy.YouTube = object
            if name == "eyed3":
                dummy.load = lambda f: types.SimpleNamespace(
                    tag=types.SimpleNamespace(publisher=None)
                )
            modules[name] = dummy
    patcher = mock.patch.dict(sys.modules, modules)
    patcher.start()
    return patcher


_PATCH = _start_dummy_modules()

import downloader_functions as df
from downloader_functions import Song, getTracks, deleteAllImages, getUri

PLAYLIST_URL = "https://open.spotify.com/playlist/37i9dQZF1FafeUudCnCplK?si=fa482ea6aa4a46a5"

class DummySpotify:
    def __init__(self):
        self.calls = []
    def user_playlist(self, user, playlist_id, fields=None):
        self.calls.append((user, playlist_id, fields))
        if fields is None:
            return {"name": "Test Playlist", "id": "playlist123"}
        else:
            track = {
                "name": "Song Name",
                "artists": [{"name": "Artist"}],
                "duration_ms": 180000,
                "album": {"name": "Album", "images": [{"url": "http://img"}]},
                "uri": "spotify:track:1",
            }
            return {"tracks": {"items": [{"track": track}], "next": None}}
    def next(self, tracks):
        return tracks

def test_getTracks_parses_playlist_and_returns_songs():
    sp = DummySpotify()
    songs, name = getTracks(PLAYLIST_URL, sp)
    assert name == "Test Playlist"
    assert len(songs) == 1
    assert isinstance(songs[0], Song)
    assert len(sp.calls) == 2
    user, playlist_id, _ = sp.calls[0]
    assert user == "https"
    assert playlist_id.startswith("//open.spotify.com/playlist/")

def test_deleteAllImages_removes_jpg_files():
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "image1.jpg"), "w").close()
        open(os.path.join(tmp, "image2.jpg"), "w").close()
        open(os.path.join(tmp, "audio.mp3"), "w").close()
        deleteAllImages(tmp)
        remaining = os.listdir(tmp)
        assert "audio.mp3" in remaining
        assert not any(f.endswith(".jpg") for f in remaining)

def test_getUri_returns_publisher():
    dummy_audio = types.SimpleNamespace(tag=types.SimpleNamespace(publisher="uriX"))
    with mock.patch.object(df.eyed3, "load", return_value=dummy_audio):
        assert getUri("dummy.mp3") == "uriX"


def teardown_module(module):
    _PATCH.stop()
