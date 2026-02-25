
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import shutil
import time
from typing import Optional

from ..dependencies import get_db_manager, get_processor
from .scan import run_scan_task, _get_job_manager, _job_to_response
from src.core.processor import Processor
from src.data.scan_job_manager import ScanJobManager

router = APIRouter(prefix="/demo", tags=["demo"])

class DemoStatusResponse(BaseModel):
    demo_mode: bool

@router.get("/status", response_model=DemoStatusResponse)
def get_demo_status(db = Depends(get_db_manager)):
    """Check if the app is currently in demo mode."""
    mode = db.get_setting("demo_mode") == "1"
    return {"demo_mode": mode}

@router.post("/start")
async def start_demo(
    background_tasks: BackgroundTasks,
    db = Depends(get_db_manager),
    processor: Processor = Depends(get_processor),
    job_manager: ScanJobManager = Depends(_get_job_manager)
):
    """Initialize demo mode by copying assets to a temp folder and starting a scan."""
    # 1. Setup paths
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    demo_assets_dir = os.path.join(base_dir, "web/public/demo")
    temp_demo_dir = os.path.join(base_dir, "data/demo_library")
    
    if not os.path.exists(demo_assets_dir):
        raise HTTPException(status_code=404, detail="Demo assets not found")
        
    # 2. Prepare temp folder (reset if exists)
    if os.path.exists(temp_demo_dir):
        shutil.rmtree(temp_demo_dir)
    os.makedirs(temp_demo_dir, exist_ok=True)
    
    # 3. Copy assets
    for item in os.listdir(demo_assets_dir):
        if item.endswith(".jpg"):
            shutil.copy2(os.path.join(demo_assets_dir, item), os.path.join(temp_demo_dir, item))
            
    # 4. Update settings
    db.set_setting("demo_mode", "1")
    
    # 5. Trigger scan
    job = job_manager.create_job(temp_demo_dir)
    background_tasks.add_task(run_scan_task, temp_demo_dir, False, processor, job_manager, job.id)
    
    return {"message": "Demo started", "job": _job_to_response(job)}

@router.post("/reset")
def reset_demo(db = Depends(get_db_manager)):
    """Exit demo mode and clear demo data."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    temp_demo_dir = os.path.join(base_dir, "data/demo_library")
    
    if os.path.exists(temp_demo_dir):
        shutil.rmtree(temp_demo_dir)
        
    db.set_setting("demo_mode", "0")
    
    # Note: We don't automatically delete the records from the DB here 
    # as the scanner logic usually handles missing files during re-scans.
    # But for a true "reset", one might want to purge records pointing to temp_demo_dir.
    
    return {"status": "success"}
