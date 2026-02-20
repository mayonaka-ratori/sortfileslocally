
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
import asyncio
import os

from ..dependencies import get_processor
from ..state import current_status, ScanStatus
from src.core.processor import Processor

router = APIRouter(prefix="/scan", tags=["scan"])

class ScanRequest(BaseModel):
    target_path: str
    force_reprocess: bool = False

async def run_scan_task(target_path: str, force_reprocess: bool, processor: Processor):
    """Background task to run the scan."""
    global current_status
    current_status.is_active = True
    current_status.error = None
    current_status.processed_count = 0
    current_status.total_files = 0
    current_status.progress_percent = 0.0

    print(f"Starting scan for: {target_path}")
    
    try:
        # Run synchronous generator in loop?
        # Since process_folder yields quickly, we can iterate in a threadpool executor 
        # but that blocks the thread for a long time.
        # Processor.process_folder is a generator. iterating over it blocks.
        # We can run the iteration in a separate thread.
        # Or just run it here if we don't mind blocking one thread of the pool.
        # BackgroundTasks run in the worker process. If async def, in main loop.
        # Wait, run_scan_task is `async def`. It runs in event loop!
        # Iterating `processor.process_folder` (sync generator) will BLOCK the event loop!
        # We MUST run this in a thread.
        
        # Helper to run blocking loop in thread
        import concurrent.futures
        loop = asyncio.get_running_loop()
        
        def _scan_loop():
            # Since we modify global state, and strings/ints are immutable (replaced), it should be fine?
            # Global variable assignment is atomic for reference update in CPython usually.
            # But better to be safe.
            # Actually, `current_status` is an object (Pydantic model). 
            # Updating its fields is thread-safe enough for simple status display.
            
            for status in processor.process_folder(target_path, force_reprocess=force_reprocess):
                if 'error' in status:
                     current_status.error = status['error']
                     # Don't break? Continue?
                     continue
                
                if 'status' in status and status['status'] == 'complete':
                    break
                    
                # Update status
                current = status.get('current', 0)
                total = status.get('total', 1)
                
                current_status.processed_count = status.get('newly_processed', 0)
                current_status.total_files = total
                current_status.current_file = status.get('filename', '')
                current_status.eta_seconds = status.get('eta', 0.0)
                current_status.progress_percent = (current / total) * 100 if total > 0 else 0
                
        # Run in default executor
        await loop.run_in_executor(None, _scan_loop)
        
    except Exception as e:
        current_status.error = str(e)
        print(f"Scan Error: {e}")
    finally:
        current_status.is_active = False
        print("Scan finished.")

@router.post("/start")
async def start_scan(
    req: ScanRequest, 
    background_tasks: BackgroundTasks,
    processor: Processor = Depends(get_processor)
):
    """Start scanning a directory."""
    if current_status.is_active:
        raise HTTPException(status_code=400, detail="Scan already in progress")
    
    if not os.path.exists(req.target_path):
        raise HTTPException(status_code=400, detail="Path does not exist")

    # Add task
    background_tasks.add_task(run_scan_task, req.target_path, req.force_reprocess, processor)
    
    return {"message": "Scan started", "status": current_status}

@router.get("/status", response_model=ScanStatus)
def get_status():
    """Get current scan status."""
    return current_status
