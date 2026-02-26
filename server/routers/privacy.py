from fastapi import APIRouter, HTTPException, Depends
import subprocess
import json
import os
from typing import Dict, Any

from src.config import Config
from server.routers.setup import get_model_manager
from src.core.model_manager import ModelManager

router = APIRouter(prefix="/privacy", tags=["privacy"])

@router.get("/audit")
async def run_privacy_audit():
    """Runs the static analysis script to check for external network calls."""
    try:
        # Resolve script path
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        script_path = os.path.join(project_root, "scripts", "privacy_audit.py")
        
        if not os.path.exists(script_path):
            raise HTTPException(status_code=404, detail="Audit script not found")

        # Run script via subprocess
        # Using sys.executable to ensure we use the same python environment
        import sys
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Parse JSON output
        try:
            audit_data = json.loads(result.stdout)
            return audit_data
        except json.JSONDecodeError:
            return {
                "verdict": "FAIL",
                "error": "Failed to parse audit results",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Privacy audit timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")

@router.get("/storage")
async def get_storage_locations(mm: ModelManager = Depends(get_model_manager)) -> Dict[str, str]:
    """Returns absolute paths for data storage used by the application."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    # DB path
    db_path = os.path.abspath(os.path.join(project_root, Config.DB_PATH))
    
    # Thumbnail path (from main.py mount)
    thumb_path = os.path.abspath(os.path.join(project_root, ".thumbnails", "scenes"))
    
    # Model path - get first model's local_dir as a proxy or custom dir
    models = mm.get_all_status()
    model_path = "Default (System Cache)"
    if models:
        # Check if they are in a custom dir or default
        sample = models[0]
        model_path = sample["local_dir"]

    return {
        "db": db_path,
        "thumbnails": thumb_path,
        "models": model_path
    }
