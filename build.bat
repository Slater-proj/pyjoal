@echo off
echo Building JOAL Modern Docker Image...

docker build -t joal-modern:latest .

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    echo.
    echo To run the container:
    echo docker-compose up -d
    echo.
    echo Or manually:
    echo docker run -d -p 8080:8080 -v ./config:/app/config -v ./torrents:/app/torrents -v ./clients:/app/clients -e SECRET_TOKEN=your_token -e UI_PATH_PREFIX=your_path joal-modern:latest
) else (
    echo Build failed!
    exit /b 1
)
