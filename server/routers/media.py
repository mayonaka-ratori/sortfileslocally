
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import io
import json
import sqlite3
import time
from PIL import Image

from ..dependencies import get_db_manager, get_processor
from ..state import active_scans, ScanStatus
from src.data.db_manager import DBManager
from src.core.exporter import MetadataExporter, ExportableMetadata
from src.core.processor import Processor
from src.data.scan_job_manager import ScanJobManager
from .shared_responses import (
    ExportResultResponse, TagUpdateResponse, BulkTagResponse,
    JobStartResponse, BulkRescanStartResponse
)

router = APIRouter(prefix="/media", tags=["media"])

@router.get("/{file_id}/original")
def get_original(file_id: int, db: DBManager = Depends(get_db_manager)):
    """Serve the original file."""
    conn = db._connect()
    c = conn.cursor()
    c.execute("SELECT file_path FROM files WHERE id = ?", (file_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
        
    path = row[0]
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File lost from disk")
        
    return FileResponse(path)

@router.get("/{file_id}/thumbnail")
def get_thumbnail(file_id: int, size: int = 300, db: DBManager = Depends(get_db_manager)):
    """Serve a resized thumbnail."""
    conn = db._connect()
    c = conn.cursor()
    c.execute("SELECT file_path, media_type FROM files WHERE id = ?", (file_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
        
    path, media_type = row
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File lost from disk")
        
    try:
        # Check if requested size is reasonable
        size = min(max(size, 100), 1080)
        
        # Check Cache Directory
        cache_dir = os.path.join(os.path.dirname(db.sqlite_path), ".thumbnails")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{file_id}_{size}.jpg")
        
        if os.path.exists(cache_path):
            return FileResponse(cache_path, media_type="image/jpeg")
        
        img = None
        
        if media_type == 'video':
            try:
                import decord
                # Attempt to extract the mid frame
                vr = decord.VideoReader(path)
                mid_frame = vr[len(vr)//2].asnumpy()
                img = Image.fromarray(mid_frame).convert("RGB")
            except Exception as e:
                print(f"Video Thumbnail Error for {path}: {e}")
                # Fallback to a black image if video decoding fails
                img = Image.new('RGB', (size, size), color=(20, 20, 20))
        else:
            try:
                img = Image.open(path)
                # Convert to RGB to ensure JPEG compatibility
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            except Exception as e:
                print(f"Image load Error for {path}: {e}")
                # Fallback to a black image
                img = Image.new('RGB', (size, size), color=(20, 20, 20))

        if img is not None:
             img.thumbnail((size, size)) # Preserves aspect ratio
             
             # Save to Cache and return it
             try:
                 rgb_img = img.convert('RGB')
                 temp_path = f"{cache_path}.{os.getpid()}.tmp"
                 rgb_img.save(temp_path, format="JPEG", quality=85)
                 os.replace(temp_path, cache_path)
                 return FileResponse(cache_path, media_type="image/jpeg")
             except Exception as e:
                 print(f"Failed to cache thumbnail: {e}")
                 # Fallback to streaming memory
                 buf = io.BytesIO()
                 img.save(buf, format="JPEG", quality=85)
                 buf.seek(0)
                 return StreamingResponse(buf, media_type="image/jpeg")
        else:
             raise HTTPException(status_code=500, detail="Could not generate thumbnail")
             
    except Exception as e:
        print(f"Thumbnail Error: {e}")
        raise HTTPException(status_code=500, detail="Thumbnail generation failed")

class SceneResponse(BaseModel):
    id: int
    scene_index: int = 0
    start_time: float
    end_time: float
    start_frame: int = 0
    end_frame: int = 0
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = None
    tags: List[str]
    character_tags: List[str]
    series_tags: List[str]
    duration: float = 0.0

@router.get("/{file_id}/scenes", response_model=List[SceneResponse])
def get_media_scenes(file_id: int, db: DBManager = Depends(get_db_manager)):
    """Get all scenes for a specific video file."""
    scenes = db.get_video_scenes(file_id)
    results = []
    for s in scenes:
        results.append(SceneResponse(
            id=s['id'],
            start_time=s['start_time'],
            end_time=s['end_time'],
            caption=s['caption'],
            tags=_safe_parse(s['tags']),
            character_tags=_safe_parse(s['character_tags']),
            series_tags=_safe_parse(s['series_tags'])
        ))
    return results


# ------------------------------------------------------------------ #
# Metadata Export Endpoints
# ------------------------------------------------------------------ #

class ExportRequest(BaseModel):
    file_ids: List[int]
    mode: str = "xmp"   # "xmp" or "exif"

class ExportAllRequest(BaseModel):
    mode: str = "xmp"

def _safe_parse(val) -> list:
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception as e:
        from src.data.db_manager import logger
        logger.warning(f"JSON parse failure for tags in media router: {e}")
        return []


@router.post("/export-metadata", response_model=ExportResultResponse)
def export_metadata(
    req: ExportRequest,
    db: DBManager = Depends(get_db_manager),
):
    """
    Export AI-generated metadata (tags, caption) to original files.
    Supports 'xmp' (sidecar) or 'exif' (JPEG only).
    """
    if req.mode not in ("xmp", "exif"):
        raise HTTPException(status_code=400, detail="Mode must be 'xmp' or 'exif'")

    if not req.file_ids:
        return {"success": 0, "failed": 0, "errors": []}

    conn = db._connect()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    placeholders = ','.join(['?'] * len(req.file_ids))
    c.execute(f"""
        SELECT id, file_path, tags, character_tags, series_tags, caption
        FROM files WHERE id IN ({placeholders}) AND is_processed=1
    """, req.file_ids)
    rows = c.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append(ExportableMetadata(
            file_path=r['file_path'],
            tags=_safe_parse(r['tags']),
            character_tags=_safe_parse(r['character_tags']),
            series_tags=_safe_parse(r['series_tags']),
            caption=r['caption'] or "",
        ))

    result = MetadataExporter.export_batch(items, mode=req.mode)
    return result


@router.post("/export-all", response_model=ExportResultResponse)
def export_all_metadata(
    req: ExportAllRequest,
    db: DBManager = Depends(get_db_manager),
):
    """
    Export metadata for ALL processed files in the library.
    This may take a while for large libraries.
    """
    if req.mode not in ("xmp", "exif"):
        raise HTTPException(status_code=400, detail="Mode must be 'xmp' or 'exif'")

    conn = db._connect()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, file_path, tags, character_tags, series_tags, caption
        FROM files WHERE is_processed=1
    """)
    rows = c.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append(ExportableMetadata(
            file_path=r['file_path'],
            tags=_safe_parse(r['tags']),
            character_tags=_safe_parse(r['character_tags']),
            series_tags=_safe_parse(r['series_tags']),
            caption=r['caption'] or "",
        ))

    result = MetadataExporter.export_batch(items, mode=req.mode)
    return result


# ------------------------------------------------------------------ #
# Tag Management Endpoints
# ------------------------------------------------------------------ #

class TagRequest(BaseModel):
    tags: List[str]
    category: str = "general" # "general" | "character" | "series"

@router.post("/{file_id}/tags", response_model=TagUpdateResponse)
def add_media_tags(file_id: int, req: TagRequest, db: DBManager = Depends(get_db_manager)):
    """Append tags to a specific media item."""
    try:
        updated_tags = db.add_tags(file_id, req.tags, req.category)
        return {
            "tags": updated_tags,
            "updated_count": len(req.tags)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{file_id}/tags", response_model=TagUpdateResponse)
def remove_media_tags(file_id: int, req: TagRequest, db: DBManager = Depends(get_db_manager)):
    """Remove tags from a specific media item."""
    try:
        updated_tags = db.remove_tags(file_id, req.tags, req.category)
        return {
            "tags": updated_tags,
            "removed_count": len(req.tags)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BulkTagRequest(BaseModel):
    file_ids: List[int]
    action: str # "add" | "remove" | "replace"
    tags: List[str]
    category: str = "general" # "general" | "character" | "series"

@router.post("/bulk-tags", response_model=BulkTagResponse)
def bulk_update_media_tags(req: BulkTagRequest, db: DBManager = Depends(get_db_manager)):
    """Bulk update tags for multiple media items."""
    if len(req.file_ids) > 500:
        raise HTTPException(status_code=422, detail="Maximum 500 files per bulk operation")
    
    if not req.tags:
        raise HTTPException(status_code=422, detail="Tags list cannot be empty")

    if req.action not in ("add", "remove", "replace"):
        raise HTTPException(status_code=400, detail="Invalid action")
    
    if req.category not in ("general", "character", "series"):
        raise HTTPException(status_code=400, detail="Invalid category")

    try:
        result = db.bulk_update_tags(req.file_ids, req.action, req.tags, req.category)
        return {
            "affected_count": result["affected_count"],
            "action": req.action,
            "tags": req.tags,
            "errors": result["errors"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
# AI Rescan Endpoints
# ------------------------------------------------------------------ #

class RescanRequest(BaseModel):
    mode: str = "append"  # "overwrite" | "append"

class BulkRescanRequest(BaseModel):
    file_ids: List[int]
    mode: str = "append"

def _rescan_file_worker(file_id: int, mode: str, db: DBManager, processor: Processor):
    """Background worker for single file rescan."""
    # Use active_scans for tracking, use file_id + 1000000 to avoid collisions
    job_key = 1000000 + file_id
    status = ScanStatus(is_active=True, total_files=1, last_updated=time.time())
    active_scans[job_key] = status
    
    try:
        conn = db._connect()
        c = conn.cursor()
        c.execute("SELECT file_path FROM files WHERE id = ?", (file_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            status.error = "File not found"
            return
            
        file_path = row[0]
        status.current_file = os.path.basename(file_path)
        
        # 1. Inspect
        item = processor.scanner.inspect_file(file_path)
        
        # Process with skip flags to ensure thread safety
        result = processor._process_item(item, skip_face=True, skip_whisper=True)
        
        if not result.success:
            status.error = result.media_item.error_msg
            return

        # Handle Merge (Append) vs Overwrite
        if mode == "append":
            # Fetch existing tags
            conn = db._connect()
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT tags, character_tags, series_tags, caption FROM files WHERE id = ?", (file_id,))
            old = c.fetchone()
            conn.close()
            
            if old:
                def safe_parse(v):
                    try: return json.loads(v) if v else []
                    except Exception as e: 
                        logger.warning(f"JSON parse failure for tags in rescan worker: {e}")
                        return []
                
                # Merge using DBManager helper
                result.media_item.tags = db._deduplicate_tags_ci(safe_parse(old['tags']) + result.media_item.tags)
                result.media_item.character_tags = db._deduplicate_tags_ci(safe_parse(old['character_tags']) + result.media_item.character_tags)
                result.media_item.series_tags = db._deduplicate_tags_ci(safe_parse(old['series_tags']) + result.media_item.series_tags)
                # If caption exists and not overwriting, keep it if new one is empty
                if old['caption'] and not result.media_item.caption:
                        result.media_item.caption = old['caption']
        
        # Save
        db.add_result(result)
        status.processed_count = 1
        status.progress_percent = 100.0

    except Exception as e:
        status.error = str(e)
    finally:
        status.is_active = False
        status.last_updated = time.time()

@router.post("/{file_id}/rescan", response_model=JobStartResponse)
def rescan_media_endpoint(
    file_id: int,
    req: RescanRequest,
    background_tasks: BackgroundTasks,
    db: DBManager = Depends(get_db_manager),
    processor: Processor = Depends(get_processor)
):
    """Trigger AI re-processing for a single file."""
    # Quick check if file exists
    conn = db._connect()
    c = conn.cursor()
    c.execute("SELECT id FROM files WHERE id = ?", (file_id,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="File not found")
    conn.close()

    background_tasks.add_task(_rescan_file_worker, file_id, req.mode, db, processor)
    return {"status": "processing", "file_id": file_id}


def _bulk_rescan_worker(file_ids: List[int], mode: str, db: DBManager, processor: Processor, job_id: int):
    """Background worker for bulk rescan."""
    job_manager = ScanJobManager(db.sqlite_path)
    job_manager.update_total(job_id, len(file_ids))
    job_manager.mark_running(job_id)

    status = ScanStatus(is_active=True, total_files=len(file_ids), last_updated=time.time())
    active_scans[job_id] = status

    try:
        def safe_parse(v):
            try: return json.loads(v) if v else []
            except Exception as e: 
                from src.data.db_manager import logger
                logger.warning(f"JSON parse failure for tags in bulk rescan worker for file {fid}: {e}")
                return []

        for i, fid in enumerate(file_ids):
            try:
                # Fetch path
                conn = db._connect()
                c = conn.cursor()
                c.execute("SELECT file_path FROM files WHERE id = ?", (fid,))
                row = c.fetchone()
                conn.close()
                if not row:
                    job_manager.log_error(job_id, f"ID:{fid}", "File not found in DB")
                    continue
                
                file_path = row[0]
                status.current_file = os.path.basename(file_path)
                
                # Inspect & Process
                item = processor.scanner.inspect_file(file_path)
                result = processor._process_item(item, skip_face=True, skip_whisper=True)
                
                if result.success:
                    if mode == "append":
                        conn = db._connect()
                        conn.row_factory = sqlite3.Row
                        c = conn.cursor()
                        c.execute("SELECT tags, character_tags, series_tags, caption FROM files WHERE id = ?", (fid,))
                        old = c.fetchone()
                        conn.close()
                        if old:
                            result.media_item.tags = db._deduplicate_tags_ci(safe_parse(old['tags']) + result.media_item.tags)
                            result.media_item.character_tags = db._deduplicate_tags_ci(safe_parse(old['character_tags']) + result.media_item.character_tags)
                            result.media_item.series_tags = db._deduplicate_tags_ci(safe_parse(old['series_tags']) + result.media_item.series_tags)
                            if old['caption'] and not result.media_item.caption:
                                result.media_item.caption = old['caption']
                    
                    db.add_result(result)
                    job_manager.increment_processed(job_id, file_path)
                else:
                    job_manager.log_error(job_id, file_path, result.media_item.error_msg or "Unknown error")

                # Update Status
                status.processed_count = i + 1
                status.progress_percent = ((i + 1) / len(file_ids)) * 100
                status.last_updated = time.time()

            except Exception as e:
                job_manager.log_error(job_id, f"ID:{fid}", str(e))

        job_manager.mark_completed(job_id)
    except Exception as e:
        job_manager.mark_failed(job_id, str(e))
        status.error = str(e)
    finally:
        status.is_active = False
        status.last_updated = time.time()


@router.post("/bulk-rescan", response_model=BulkRescanStartResponse)
def bulk_rescan_endpoint(
    req: BulkRescanRequest,
    background_tasks: BackgroundTasks,
    db: DBManager = Depends(get_db_manager),
    processor: Processor = Depends(get_processor)
):
    """Bulk rescan multiple files with AI."""
    if len(req.file_ids) > 50:
        raise HTTPException(status_code=422, detail="Maximum 50 files per rescan operation")

    job_manager = ScanJobManager(db.sqlite_path)
    # Use a dummy path for rescan jobs
    job = job_manager.create_job(f"Bulk Rescan ({len(req.file_ids)} files)")
    
    background_tasks.add_task(_bulk_rescan_worker, req.file_ids, req.mode, db, processor, job.id)
    
    return {
        "status": "processing",
        "job_id": job.id,
        "file_count": len(req.file_ids)
    }
