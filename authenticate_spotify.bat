@echo off
echo Authenticating with Spotify...
echo This will open your browser for login.
echo.
python "%~dp0playlist_downloader.py" --user-auth https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
echo.
echo Authentication complete! You can now run the collaborator analysis.
pause 