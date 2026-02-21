@echo off
chcp 65001 >nul
echo ============================================================
echo   GiftScan -- Dev Launcher
echo ============================================================
echo.
echo   [1] DEV MODE   -- hot reload (Vite + uvicorn --reload)
echo   [2] FULL STACK -- everything in Docker (prod-like)
echo   [3] STOP       -- stop all containers
echo.
set /p MODE="Choose mode (1/2/3): "

if "%MODE%"=="3" goto STOP
if "%MODE%"=="2" goto DOCKER
goto DEV

:: -----------------------------------------------------------------------
:DEV
echo.
echo [DEV] Starting postgres + redis via Docker...
docker-compose up -d postgres redis
if errorlevel 1 (
    echo ERROR: Docker not running. Open Docker Desktop first.
    pause & exit /b 1
)
echo Waiting for postgres to be ready...
timeout /t 6 >nul

echo [DEV] Starting Backend (FastAPI hot-reload)...
start "GiftScan Backend" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

echo [DEV] Starting Frontend (Vite)...
start "GiftScan Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 >nul

echo.
echo ============================================================
echo   DEV MODE running:
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo.
echo   Telegram Mini App (needs HTTPS):
echo   1. Run: ngrok http 5173
echo   2. Copy https://xxxx.ngrok-free.app URL
echo   3. BotFather: /mybots -- your bot -- Menu Button -- set URL
echo ============================================================
echo.
pause & exit /b 0

:: -----------------------------------------------------------------------
:DOCKER
echo.
echo [DOCKER] Building and starting all services...
echo (First run takes a few minutes: npm install + pip install)
echo.
docker-compose up --build -d
if errorlevel 1 (
    echo ERROR: docker-compose failed. Is Docker Desktop running?
    pause & exit /b 1
)
echo.
echo Waiting for services to start...
timeout /t 10 >nul

echo.
echo Seeding gift catalog (safe to run multiple times)...
curl -s http://localhost:8000/seed > nul 2>&1

echo.
echo ============================================================
echo   FULL STACK running:
echo   App:      http://localhost          (Telegram Mini App)
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   pgAdmin:  http://localhost:5050
echo.
echo   Telegram Mini App (needs HTTPS):
echo   1. Run: ngrok http 80
echo   2. Copy https://xxxx.ngrok-free.app URL
echo   3. BotFather: /mybots -- your bot -- Menu Button -- set URL
echo ============================================================
echo.
start http://localhost
pause & exit /b 0

:: -----------------------------------------------------------------------
:STOP
echo.
echo Stopping all GiftScan containers...
docker-compose down
echo Done.
pause & exit /b 0
