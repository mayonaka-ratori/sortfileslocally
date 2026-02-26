import sys
import os

def get_app_data_dir():
    """Get persistent data directory (works in both dev and packaged mode)."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        if sys.platform == 'win32':
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        elif sys.platform == 'darwin':
            base = os.path.expanduser('~/Library/Application Support')
        else:
            base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        return os.path.join(base, 'LocalCuratorPrime')
    else:
        # Development mode — use project root
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_DATA_DIR = get_app_data_dir()
os.makedirs(APP_DATA_DIR, exist_ok=True)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routers import gallery, media, scan, setup, dedup, albums, insights, scenes, demo, privacy
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LocalCurator Prime API", version="1.0.0")

# Scenes Thumbnails Static Mount
SCENES_THUMBNAILS_DIR = os.path.join(APP_DATA_DIR, ".thumbnails/scenes")
os.makedirs(SCENES_THUMBNAILS_DIR, exist_ok=True)
app.mount("/thumbnails/scenes", StaticFiles(directory=SCENES_THUMBNAILS_DIR), name="scene_thumbnails")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORS_ORIGIN", "http://localhost:3000")], # Secure by default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(gallery.router)
app.include_router(media.router)
app.include_router(scan.router)
app.include_router(setup.router)
app.include_router(dedup.router)
app.include_router(albums.router)
app.include_router(insights.router)
app.include_router(scenes.router)
app.include_router(demo.router)
app.include_router(privacy.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = 8000
    print(f"STARTING_PORT={port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
