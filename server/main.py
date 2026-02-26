
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routers import gallery, media, scan, setup, dedup, albums, insights, scenes, demo, privacy
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LocalCurator Prime API", version="1.0.0")

# Scenes Thumbnails Static Mount
os.makedirs(".thumbnails/scenes", exist_ok=True)
app.mount("/thumbnails/scenes", StaticFiles(directory=".thumbnails/scenes"), name="scene_thumbnails")

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
