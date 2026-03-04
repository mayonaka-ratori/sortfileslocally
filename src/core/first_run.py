import os
from pathlib import Path
from typing import Dict, Any, List, Callable
import time
import asyncio

# Hardcoded model information for the plan
MODELS = {
    "whisper-tiny": {
        "size_mb": 39,
        "path": "models/whisper/tiny.pt"
    },
    "whisper-base": {
        "size_mb": 74,
        "path": "models/whisper/base.pt"
    },
    "clip-vit-b-32": {
        "size_mb": 350,
        "path": "models/clip/ViT-B-32.pt"
    },
    "clip-vit-l-14": {
        "size_mb": 900,
        "path": "models/clip/ViT-L-14.pt"
    },
    "insightface-buffalo_l": {
        "size_mb": 400,
        "path": "models/insightface/buffalo_l"
    }
}

PROFILES = {
    "lightweight": ["whisper-tiny"],
    "balanced": ["clip-vit-b-32", "whisper-base"],
    "full": ["clip-vit-l-14", "whisper-base", "insightface-buffalo_l"]
}

def get_models_dir() -> Path:
    # Just a typical resolved path for models
    base_dir = os.getenv("LOCALCURATOR_MODELS_DIR", os.path.expanduser("~/.localcurator/models"))
    return Path(base_dir)

def check_model_status() -> Dict[str, Any]:
    """Check availability of predefined models."""
    status = {}
    base_dir = get_models_dir()
    for name, info in MODELS.items():
        model_path = base_dir / info["path"]
        available = model_path.exists()
        status[name] = {
            "available": available,
            "size_mb": info["size_mb"],
            "path": str(model_path)
        }
    return status

def get_download_plan(profile: str) -> List[str]:
    """Return models that need downloading based on profile."""
    return PROFILES.get(profile, [])

async def download_model_with_progress(model_name: str, callback: Callable[[float], None]):
    """Simulate downloading model with a progress callback for SSE."""
    if model_name not in MODELS:
        return
    
    # Simulate network download
    size_mb = MODELS[model_name]["size_mb"]
    # Fake speed ~50MB/s for simulation, minimum 1 second
    duration = max(1.0, size_mb / 50.0)
    steps = int(duration * 10)
    
    for i in range(1, steps + 1):
        progress = (i / steps) * 100
        callback(progress)
        await asyncio.sleep(duration / steps)
    
    # Pretend it saved successfully
    callback(100.0)
