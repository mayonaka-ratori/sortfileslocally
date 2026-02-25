
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os

from ..dependencies import get_processor, get_db_manager
from ..state import active_scans, ScanStatus
import time
from src.core.processor import Processor
from src.data.scan_job_manager import ScanJobManager, ScanJob

router = APIRouter(prefix="/scan", tags=["scan"])

class ScanRequest(BaseModel):
    target_path: str
    force_reprocess: bool = False

class ScanJobResponse(BaseModel):
    id: int
    target_path: str
    status: str
    total_files: int
    processed_count: int
    skipped_count: int
    error_count: int
    progress_percent: float
    current_file: str
    eta_seconds: float
    started_at: float
    updated_at: float
    completed_at: float

class ScanErrorResponse(BaseModel):
    id: int
    job_id: int
    file_path: str
    error_message: str
    occurred_at: float


def _job_to_response(job: ScanJob) -> ScanJobResponse:
    return ScanJobResponse(
        id=job.id,
        target_path=job.target_path,
        status=job.status,
        total_files=job.total_files,
        processed_count=job.processed_count,
        skipped_count=job.skipped_count,
        error_count=job.error_count,
        progress_percent=job.progress_percent,
        current_file=job.current_file,
        eta_seconds=job.eta_seconds,
        started_at=job.started_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


def _get_job_manager(processor: Processor = Depends(get_processor)) -> ScanJobManager:
    return ScanJobManager(processor.db_manager.sqlite_path)


async def run_scan_task(target_path: str, force_reprocess: bool,
                        processor: Processor, job_manager: ScanJobManager,
                        job_id: int, resume_after_path: str = None):
    """Background task to run the scan with persistent job tracking."""
    global active_scans
    current_status = ScanStatus()
    current_status.is_active = True
    current_status.error = None
    current_status.processed_count = 0
    current_status.total_files = 0
    current_status.progress_percent = 0.0
    current_status.last_updated = time.time()
    active_scans[job_id] = current_status

    print(f"Starting scan for: {target_path} (Job #{job_id})")
    
    try:
        import concurrent.futures
        loop = asyncio.get_running_loop()
        
        def _scan_loop():
            for status in processor.process_folder(
                target_path,
                force_reprocess=force_reprocess,
                job_manager=job_manager,
                job_id=job_id,
                resume_after_path=resume_after_path
            ):
                if 'error' in status:
                     current_status.error = status['error']
                     current_status.last_updated = time.time()
                     continue
                
                if 'status' in status and status['status'] == 'complete':
                    break
                    
                # Update in-memory status (for polling)
                current = status.get('current', 0)
                total = status.get('total', 1)
                
                current_status.processed_count = current
                current_status.total_files = total
                current_status.current_file = status.get('filename', '')
                current_status.eta_seconds = status.get('eta', 0.0)
                current_status.progress_percent = (current / total) * 100 if total > 0 else 0
                current_status.last_updated = time.time()
                
        await loop.run_in_executor(None, _scan_loop)
        
    except Exception as e:
        current_status.error = str(e)
        job_manager.mark_failed(job_id, str(e))
        print(f"Scan Error: {e}")
    finally:
        current_status.is_active = False
        current_status.last_updated = time.time()
        print("Scan finished.")


@router.post("/start")
async def start_scan(
    req: ScanRequest, 
    background_tasks: BackgroundTasks,
    processor: Processor = Depends(get_processor),
    job_manager: ScanJobManager = Depends(_get_job_manager),
):
    """Start scanning a directory."""
    if any(s.is_active for s in active_scans.values()):
        # (Optional) You can limit to 1 concurrent scan or modify according to requirements. 
        # For safety we can keep it single concurrent scan unless we add a queue.
        raise HTTPException(status_code=400, detail="Scan already in progress")
    
    if not os.path.exists(req.target_path):
        raise HTTPException(status_code=400, detail="Path does not exist")

    # Create a new persistent job
    job = job_manager.create_job(req.target_path, force_reprocess=req.force_reprocess)

    background_tasks.add_task(
        run_scan_task, req.target_path, req.force_reprocess,
        processor, job_manager, job.id
    )
    
    return {"message": "Scan started", "job": _job_to_response(job)}


class ResumeRequest(BaseModel):
    target_path: Optional[str] = None

@router.post("/resume")
async def resume_scan(
    req: Optional[ResumeRequest] = None,
    background_tasks: BackgroundTasks = None,
    processor: Processor = Depends(get_processor),
    job_manager: ScanJobManager = Depends(_get_job_manager),
):
    """Resume an incomplete scan job (auto-finds latest)."""
    if any(s.is_active for s in active_scans.values()):
        raise HTTPException(status_code=400, detail="Scan already in progress")

    job = None
    if req and req.target_path:
        job = job_manager.get_resumable_job(req.target_path)
    else:
        # Fallback to globally latest incomplete job
        latest = job_manager.get_latest_job()
        if latest and latest.status in ('running', 'paused', 'failed'):
            job = latest

    if not job:
        raise HTTPException(status_code=404, detail="No resumable scan job found")

    if not os.path.exists(job.target_path):
        raise HTTPException(status_code=400, detail=f"Original path no longer exists: {job.target_path}")

    resume_after = job.last_processed_path or None

    background_tasks.add_task(
        run_scan_task, job.target_path, job.force_reprocess,
        processor, job_manager, job.id, resume_after
    )
    
    return {"message": "Scan resumed", "job": _job_to_response(job)}


@router.post("/resume/{job_id}")
async def resume_scan_by_id(
    job_id: int,
    background_tasks: BackgroundTasks,
    processor: Processor = Depends(get_processor),
    job_manager: ScanJobManager = Depends(_get_job_manager),
):
    """Resume a specific scan job by ID."""
    if any(s.is_active for s in active_scans.values()):
        raise HTTPException(status_code=400, detail="Scan already in progress")

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Roadmap: return 422 if job status is not 'failed'/'interrupted'
    # Persistent status maps: running/paused/failed are 'interrupted' if not currently active
    if job.status not in ('failed', 'paused', 'running'):
        raise HTTPException(status_code=422, detail=f"Job {job_id} is in status '{job.status}' and cannot be resumed")

    if not os.path.exists(job.target_path):
        raise HTTPException(status_code=400, detail=f"Original path no longer exists: {job.target_path}")

    resume_after = job.last_processed_path or None

    background_tasks.add_task(
        run_scan_task, job.target_path, job.force_reprocess,
        processor, job_manager, job.id, resume_after
    )
    
    return {"message": "Scan resumed", "job": _job_to_response(job)}


def _cleanup_scans():
    now = time.time()
    to_remove = []
    for j_id, status in active_scans.items():
        if not status.is_active and (now - status.last_updated) > 600:
            to_remove.append(j_id)
    for j_id in to_remove:
        del active_scans[j_id]

@router.get("/status/{job_id}", response_model=ScanStatus)
def get_status(job_id: int):
    """Get current scan status (in-memory, for polling)."""
    _cleanup_scans()
    status = active_scans.get(job_id)
    if not status:
        return ScanStatus()
    return status


@router.get("/job/latest", response_model=ScanJobResponse)
def get_latest_job(
    job_manager: ScanJobManager = Depends(_get_job_manager),
):
    """Get the latest scan job from the database."""
    job = job_manager.get_latest_job()
    if not job:
        raise HTTPException(status_code=404, detail="No scan jobs found")
    return _job_to_response(job)


@router.get("/job/{job_id}", response_model=ScanJobResponse)
def get_job(
    job_id: int,
    job_manager: ScanJobManager = Depends(_get_job_manager),
):
    """Get a specific scan job by ID."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.get("/job/{job_id}/errors", response_model=List[ScanErrorResponse])
def get_job_errors(
    job_id: int,
    job_manager: ScanJobManager = Depends(_get_job_manager),
):
    """Get error log for a specific scan job."""
    errors = job_manager.get_errors(job_id)
    return [ScanErrorResponse(
        id=e.id, job_id=e.job_id, file_path=e.file_path,
        error_message=e.error_message, occurred_at=e.occurred_at
    ) for e in errors]


@router.get("/jobs", response_model=List[ScanJobResponse])
def list_jobs(
    limit: int = 20,
    job_manager: ScanJobManager = Depends(_get_job_manager),
):
    """List recent scan jobs."""
    jobs = job_manager.get_all_jobs(limit=limit)
    return [_job_to_response(j) for j in jobs]
