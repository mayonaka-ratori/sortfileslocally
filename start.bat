@echo off
SETLOCAL EnableDelayedExpansion

echo ===========================================
echo   Starting Local Curator Prime Launcher
echo ===========================================

REM Ensure we are in the project root
cd /d "%~dp0"

REM 1. Check Python VENV
IF NOT EXIST "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please ensure you have created it and installed requirements.txt
    pause
    exit /b 1
)

REM 2. Start FastAPI Server in background
echo [INFO] Starting Backend Server...
start "Local Curator Prime - Backend" cmd /c "venv\Scripts\activate && python -m uvicorn server.main:app --host 127.0.0.1 --port 8000"

REM 3. Wait a moment for backend
timeout /t 3 /nobreak >nul

REM 4. Start Next.js Frontend
echo [INFO] Starting Next.js Frontend...
IF NOT EXIST "web\node_modules" (
    echo [ERROR] Node modules not found in 'web/'. Did you run 'npm install'?
    pause
    exit /b 1
)

start "Local Curator Prime - Frontend" cmd /c "cd web && npm run dev"

REM 5. Wait for frontend to compile, then open browser
echo [INFO] Waiting for Frontend to initialize...
timeout /t 5 /nobreak >nul
echo [INFO] Launching Browser!
start http://localhost:3000

echo ===========================================
echo   Local Curator Prime is running! 
echo   Close the two pop-up terminal windows 
echo   to completely stop the application.
echo ===========================================
