@echo off
echo ============================================
echo   GiftScan - Development Environment
echo ============================================
echo.

REM Check if Docker containers are running
echo [1/4] Checking Docker containers...
docker ps | findstr giftscan-postgres >nul 2>&1
if errorlevel 1 (
    echo ERROR: PostgreSQL container not running!
    echo Please start it with: docker-compose up -d
    pause
    exit /b 1
)
docker ps | findstr giftscan-redis >nul 2>&1
if errorlevel 1 (
    echo ERROR: Redis container not running!
    echo Please start it with: docker-compose up -d
    pause
    exit /b 1
)
echo OK: Docker containers running

REM Start Backend
echo.
echo [2/4] Starting Backend (FastAPI)...
start "GiftScan Backend" cmd /k "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

REM Start Frontend
echo [3/4] Starting Frontend (Vite)...
start "GiftScan Frontend" cmd /k "cd frontend && npm run dev"
timeout /t 3 >nul

echo.
echo [4/4] Services started!
echo.
echo ============================================
echo   Services:
echo ============================================
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo.
echo   For Telegram Mini App:
echo   1. Install ngrok: https://ngrok.com/download
echo   2. Run: ngrok http 5173
echo   3. Copy HTTPS URL to @BotFather
echo.
echo   See TELEGRAM_SETUP.md for full instructions
echo ============================================
echo.
pause
