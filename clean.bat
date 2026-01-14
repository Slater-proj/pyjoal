@echo off
REM Clean script for JOAL Modern project

echo Nettoyage du projet JOAL Modern...
echo.

REM Remove Python cache
echo   - Suppression des caches Python...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul

REM Remove Node modules and build
echo   - Suppression des builds Node.js...
if exist frontend\node_modules rd /s /q frontend\node_modules 2>nul
if exist frontend\dist rd /s /q frontend\dist 2>nul

REM Remove test torrents
echo   - Suppression des torrents de test...
del /q torrents\*.torrent 2>nul

REM Remove generated client files (keep base versions)
echo   - Suppression des clients generes...
del /q clients\*-5.*.client 2>nul
del /q clients\*-2.2.*.client 2>nul
del /q clients\*-4.0.6.client 2>nul

REM Remove logs
echo   - Suppression des logs...
del /s /q *.log 2>nul
if exist logs rd /s /q logs 2>nul

REM Remove pytest cache
echo   - Suppression des caches de test...
if exist .pytest_cache rd /s /q .pytest_cache 2>nul
if exist backend\.pytest_cache rd /s /q backend\.pytest_cache 2>nul
del /q .coverage 2>nul
if exist htmlcov rd /s /q htmlcov 2>nul

echo.
echo Projet nettoye avec succes!
echo.
echo Pour reinstaller les dependances :
echo    Backend:  cd backend ^&^& pip install -r requirements.txt
echo    Frontend: cd frontend ^&^& npm install
pause
