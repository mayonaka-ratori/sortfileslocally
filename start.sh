#!/bin/bash
echo "==========================================="
echo "  Starting Local Curator Prime Launcher"
echo "==========================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 1. Check Python VENV
if [ ! -d "venv" ]; then
    echo "[ERROR] Virtual environment 'venv' not found."
    echo "Please ensure you have created it and installed requirements.txt"
    exit 1
fi

# 2. Start FastAPI Server in background
echo "[INFO] Starting Backend Server..."
source venv/bin/activate
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

sleep 3

# 3. Start Next.js Frontend
echo "[INFO] Starting Next.js Frontend..."
if [ ! -d "web/node_modules" ]; then
    echo "[ERROR] Node modules not found in 'web/'. Did you run 'npm install'?"
    kill $BACKEND_PID
    exit 1
fi

cd web
npm run dev &
FRONTEND_PID=$!

# Move back to root
cd "$DIR"

# Wait for frontend starting up
echo "[INFO] Waiting for Frontend to initialize..."
sleep 5

# 4. Open Browser
echo "[INFO] Launching Browser!"
if which xdg-open > /dev/null
then
  xdg-open http://localhost:3000
elif which gnome-open > /dev/null
then
  gnome-open http://localhost:3000
elif which open > /dev/null
then
  open http://localhost:3000
else
  echo "Could not open browser automatically. Please visit http://localhost:3000"
fi

echo "==========================================="
echo "  Local Curator Prime is running!"
echo "  Press Ctrl+C to terminate both servers."
echo "==========================================="

# Wait until script is terminated
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
wait $BACKEND_PID $FRONTEND_PID
