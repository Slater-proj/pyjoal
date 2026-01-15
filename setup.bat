@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   PyJOAL - Setup ^& Installation Script
echo ================================================
echo.

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found. Creating from template...
    copy .env.example .env
    
    echo Please edit .env file and set:
    echo   - SECRET_TOKEN ^(required^)
    echo   - UI_PATH_PREFIX ^(required^)
    echo.
    pause
    notepad .env
)

REM Check Docker installation
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not installed!
    echo Please install Docker: https://docs.docker.com/get-docker/
    exit /b 1
)

docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker Compose is not installed!
    echo Please install Docker Compose: https://docs.docker.com/compose/install/
    exit /b 1
)

echo [OK] Docker and Docker Compose found
echo.

REM Ask what to do
echo What would you like to do?
echo 1^) Build and start with Docker ^(recommended^)
echo 2^) Development setup ^(Python + Node.js^)
echo 3^) Just build Docker image
echo 4^) Exit
echo.
set /p choice="Choose option [1-4]: "

if "%choice%"=="1" goto docker_start
if "%choice%"=="2" goto dev_setup
if "%choice%"=="3" goto docker_build
if "%choice%"=="4" goto end
echo Invalid option!
exit /b 1

:docker_start
echo.
echo [BUILD] Building Docker image...
docker-compose build

if %ERRORLEVEL% EQU 0 (
    echo [OK] Build successful!
    echo.
    echo [START] Starting PyJOAL...
    docker-compose up -d
    
    timeout /t 3 /nobreak >nul
    
    REM Get UI path from .env
    for /f "tokens=2 delims==" %%a in ('findstr UI_PATH_PREFIX .env') do set UI_PATH=%%a
    for /f "tokens=2 delims==" %%a in ('findstr PORT .env') do set PORT=%%a
    if "!PORT!"=="" set PORT=8080
    
    echo.
    echo ================================================
    echo   PyJOAL is now running! 🎉
    echo ================================================
    echo.
    echo Access the web UI at:
    echo http://localhost:!PORT!/!UI_PATH!/ui/
    echo.
    echo API Documentation:
    echo http://localhost:!PORT!/docs
    echo.
    echo To view logs:
    echo docker-compose logs -f pyjoal
    echo.
    echo To stop:
    echo docker-compose down
    echo.
) else (
    echo [ERROR] Build failed!
    exit /b 1
)
goto end

:dev_setup
echo.
echo [SETUP] Setting up development environment...

echo.
echo [BACKEND] Setting up backend...
cd backend

if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt

echo [OK] Backend ready
echo.
echo To run backend:
echo   cd backend
echo   venv\Scripts\activate
echo   python -m uvicorn app.main:app --reload
echo.

cd ..

echo [FRONTEND] Setting up frontend...
cd frontend

if not exist node_modules (
    call npm install
)

echo [OK] Frontend ready
echo.
echo To run frontend:
echo   cd frontend
echo   npm run dev
echo.

cd ..

echo ================================================
echo   Development environment ready! 🎉
echo ================================================
goto end

:docker_build
echo.
echo [BUILD] Building Docker image only...
docker build -t pyjoal:latest .

if %ERRORLEVEL% EQU 0 (
    echo [OK] Build successful!
) else (
    echo [ERROR] Build failed!
    exit /b 1
)
goto end

:end
pause
