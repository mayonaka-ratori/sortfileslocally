
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import numpy as np

from ..dependencies import get_db_manager, get_ai_engine
from src.data.db_manager import DBManager
from src.core.ai_models import AIEngine
from .shared_responses import DeleteResultResponse
# from src.core.deduplication import Deduplicator, DuplicatePair  # Moved to endpoints to avoid startup crash

router = APIRouter(prefix="/dedup", tags=["deduplication"])


# ------------------------------------------------------------------ #
# Response Models
# ------------------------------------------------------------------ #

class DuplicateItemResponse(BaseModel):
    file_path: str
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    media_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None

class DuplicatePairResponse(BaseModel):
    file_a: DuplicateItemResponse
    file_b: DuplicateItemResponse
    similarity: float
    recommended_action: str
    reason: str

class DeduplicationRequest(BaseModel):
    threshold_img: float = 0.95
    threshold_vid: float = 0.98

class DeleteRequest(BaseModel):
    file_paths: List[str]
    merge_into: Optional[Dict[str, str]] = None

class ReverseSearchResponse(BaseModel):
    id: int
    file_path: str
    media_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    similarity: float


# ------------------------------------------------------------------ #
# Deduplication Endpoints
# ------------------------------------------------------------------ #

@router.post("/candidates", response_model=List[DuplicatePairResponse])
def find_duplicate_candidates(
    req: DeduplicationRequest,
    db: DBManager = Depends(get_db_manager),
):
    """
    Run deduplication analysis and return candidate pairs.
    This may take a while for large libraries.
    """
    from src.core.deduplication import Deduplicator
    deduper = Deduplicator(db)

    try:
        pairs = deduper.find_duplicates(
            threshold_img=req.threshold_img,
            threshold_vid=req.threshold_vid
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deduplication failed: {str(e)}")

    results = []
    for p in pairs:
        results.append(DuplicatePairResponse(
            file_a=DuplicateItemResponse(
                file_path=p.file_a.file_path,
                file_hash=p.file_a.file_hash,
                file_size=p.file_a.file_size,
                media_type=p.file_a.media_type,
                width=p.file_a.width,
                height=p.file_a.height,
                duration=p.file_a.duration,
            ),
            file_b=DuplicateItemResponse(
                file_path=p.file_b.file_path,
                file_hash=p.file_b.file_hash,
                file_size=p.file_b.file_size,
                media_type=p.file_b.media_type,
                width=p.file_b.width,
                height=p.file_b.height,
                duration=p.file_b.duration,
            ),
            similarity=p.similarity,
            recommended_action=p.recommended_action,
            reason=p.reason,
        ))

    return results


@router.post("/apply", response_model=DeleteResultResponse)
def apply_deduplication(
    req: DeleteRequest,
    db: DBManager = Depends(get_db_manager),
):
    """
    Delete the specified files from disk.
    Only allows deleting files that are already indexed in the DB for safety.
    """
    deleted = []
    errors = []

    if not req.file_paths:
        return {"deleted_count": 0, "deleted": [], "errors": []}

    # Verify paths exist in DB first
    import sqlite3
    conn = db._connect()
    c = conn.cursor()
    
    placeholders = ','.join(['?'] * len(req.file_paths))
    c.execute(f"SELECT file_path FROM files WHERE file_path IN ({placeholders})", req.file_paths)
    allowed_paths = set(row[0] for row in c.fetchall())
    conn.close()

    merged_count = 0
    for path in req.file_paths:
        if path not in allowed_paths:
            errors.append({"path": path, "error": "Access denied: file not in library"})
            continue
            
        # Handle metadata merging
        if req.merge_into and path in req.merge_into:
            target_path = req.merge_into[path]
            if target_path in req.file_paths:
                errors.append({"path": path, "error": "Cannot merge into a file that is marked for deletion"})
            else:
                success = db.merge_metadata(path, target_path)
                if success:
                    merged_count += 1
                else:
                    errors.append({"path": path, "error": "Failed to merge metadata. Target may not exist."})

        try:
            if os.path.exists(path):
                os.remove(path)
                deleted.append(path)
                
                # Check and delete associated .xmp sidecar
                xmp_path = os.path.splitext(path)[0] + ".xmp"
                if os.path.exists(xmp_path):
                    try:
                        os.remove(xmp_path)
                        print(f"Deleted associated sidecar: {xmp_path}")
                    except Exception as e:
                        print(f"Failed to delete sidecar {xmp_path}: {e}")
            else:
                errors.append({"path": path, "error": "File not found on disk"})
        except Exception as e:
            errors.append({"path": path, "error": str(e)})

    return {
        "deleted_count": len(deleted),
        "merged_count": merged_count,
        "deleted": deleted,
        "errors": errors,
    }


# ------------------------------------------------------------------ #
# Reverse Image Search (Image-to-Image)
# ------------------------------------------------------------------ #

@router.post("/reverse-search", response_model=List[ReverseSearchResponse])
async def reverse_image_search(
    file: UploadFile = File(...),
    top_k: int = Query(default=30),
    ai: AIEngine = Depends(get_ai_engine),
    db: DBManager = Depends(get_db_manager),
):
    """
    Upload an image and find visually similar images in the library.
    Uses CLIP embedding for semantic similarity.
    """
    from PIL import Image
    import io

    # Check file size (approximate using headers or read first)
    MAX_SIZE = 20 * 1024 * 1024
    if file.size and file.size > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum upload size is 20MB.")
        
    try:
        # Read uploaded file
        contents = await file.read()
        if len(contents) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum upload size is 20MB.")
            
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")
    finally:
        await file.close()

    # Extract CLIP embedding
    query_vec = ai.extract_clip_feature(img)

    if query_vec is None or np.all(query_vec == 0):
        raise HTTPException(status_code=500, detail="Failed to extract image features")

    # Search FAISS
    similar = db.search_similar_images(query_vec, top_k=top_k)

    if not similar:
        return []

    # Fetch metadata
    import sqlite3
    conn = db._connect()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    paths = [r[0] for r in similar]
    scores = {r[0]: r[1] for r in similar}

    placeholders = ','.join(['?'] * len(paths))
    c.execute(f"""
        SELECT id, file_path, media_type, width, height
        FROM files
        WHERE file_path IN ({placeholders})
    """, paths)
    rows = {r['file_path']: dict(r) for r in c.fetchall()}
    conn.close()

    results = []
    for path, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if path in rows:
            r = rows[path]
            results.append(ReverseSearchResponse(
                id=r['id'],
                file_path=r['file_path'],
                media_type=r['media_type'],
                width=r['width'],
                height=r['height'],
                similarity=score,
            ))

    return results[:top_k]
