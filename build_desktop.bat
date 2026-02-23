@echo off
echo ====================================================
echo Building LocalCuratorPrime Desktop Application
echo ====================================================

:: 1. Build the Python Backend (FastAPI) via PyInstaller
echo [1/3] Building Python Backend via PyInstaller...
cd server
pyinstaller --clean main.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed.
    exit /b %ERRORLEVEL%
)

:: Move the generated executable to Tauri binaries folder
echo Moving python backend executable to src-tauri/binaries...
if not exist "..\web\src-tauri\binaries" mkdir "..\web\src-tauri\binaries"
copy /Y "dist\backend-api.exe" "..\web\src-tauri\binaries\backend-api-x86_64-pc-windows-msvc.exe"
cd ..

:: 2. Build the Next.js Frontend
echo [2/3] Building Next.js Frontend (Static Export)...
cd web
call npm i
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Next.js frontend build failed.
    exit /b %ERRORLEVEL%
)

:: 3. Bundle with Tauri
echo [3/3] Packaging Desktop Executable via Tauri...
call npx tauri build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Tauri build failed.
    exit /b %ERRORLEVEL%
)

echo ====================================================
echo Build Complete!
echo The desktop installer can be found in web\src-tauri\target\release\bundle
echo ====================================================
pause
