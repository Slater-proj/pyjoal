@echo off
REM Update BitTorrent client definitions with latest versions

cd /d "%~dp0"

echo Updating BitTorrent clients to latest versions...
echo.

python update_clients.py

echo.
echo Done! Check the clients\ folder for new .client files
pause
