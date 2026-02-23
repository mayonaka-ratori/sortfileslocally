
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import io
import json
import sqlite3
from PIL import Image

from ..dependencies import get_db_manager
from src.data.db_manager import DBManager
from src.core.exporter import MetadataExporter, ExportableMetadata

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
    except Exception:
        return []


@router.post("/export-metadata")
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


@router.post("/export-all")
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
