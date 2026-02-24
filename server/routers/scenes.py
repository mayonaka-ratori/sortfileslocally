
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from src.core.processor import Processor
from src.data.db_manager import DBManager
from src.config import Config
import os

router = APIRouter(prefix="/scenes", tags=["scenes"])

from server.dependencies import get_db_manager, get_processor

router = APIRouter(prefix="/scenes", tags=["scenes"])

class SceneSearchResponse(BaseModel):
    scene_id: int
    file_id: int
    file_path: str
    scene_index: int
    start_time: float
    end_time: float
    thumbnail_path: Optional[str]
    caption: Optional[str]
    tags: List[str]
    character_tags: List[str]
    series_tags: List[str]
    score: float

class DetectRequest(BaseModel):
    force: bool = False

@router.post("/{file_id}/detect")
async def detect_scenes(
    file_id: int, 
    background_tasks: BackgroundTasks,
    req: DetectRequest = DetectRequest(),
    db: DBManager = Depends(get_db_manager),
    processor: Processor = Depends(get_processor)
):
    """Trigger background scene detection for a video."""
    conn = db._connect()
    c = conn.cursor()
    c.execute("SELECT file_path, media_type, duration FROM files WHERE id = ?", (file_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path, media_type, duration = row
    if media_type != "video":
        raise HTTPException(status_code=422, detail="Only videos support scene detection")

    # Check max duration from settings
    if not req.force:
        max_duration = 7200
        try:
            m_val = db.get_setting("max_video_duration")
            if m_val: max_duration = int(m_val)
        except: pass
        
        if duration and duration > max_duration:
            raise HTTPException(status_code=422, detail=f"Video exceeds maximum duration ({duration}s > {max_duration}s). Use force=true to override.")

    # Launch background task
    background_tasks.add_task(processor.process_video_scenes, file_id)
    
    return {"status": "processing", "message": "Scene detection started in background"}

@router.delete("/{file_id}")
async def delete_scenes(file_id: int, db: DBManager = Depends(get_db_manager)):
    """Delete all scenes and thumbnails for a video."""
    conn = db._connect()
    c = conn.cursor()
    
    try:
        # Get thumbnails to delete
        c.execute("SELECT thumbnail_path FROM video_scenes WHERE file_id = ?", (file_id,))
        thumbnails = [r[0] for r in c.fetchall() if r[0]]
        
        # 1. FAISS Cleanup
        c.execute("SELECT clip_vector_id FROM video_scenes WHERE file_id = ? AND clip_vector_id IS NOT NULL", (file_id,))
        faiss_ids = [r[0] for r in c.fetchall()]
        
        if faiss_ids:
            import numpy as np
            with db._faiss_lock:
                db.clip_index.remove_ids(np.array(faiss_ids, dtype='int64'))
            
            # Delete mappings
            placeholders = ','.join(['?'] * len(faiss_ids))
            c.execute(f"DELETE FROM vector_mapping WHERE faiss_id IN ({placeholders})", faiss_ids)

        # 2. DB Cleanup
        c.execute("DELETE FROM video_scenes WHERE file_id = ?", (file_id,))
        conn.commit()
        
        # 3. Disk Cleanup (Thumbnails)
        for tp in thumbnails:
            if os.path.exists(tp):
                try: os.remove(tp)
                except: pass
                
        return {"status": "deleted", "count": len(thumbnails)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/search", response_model=List[SceneSearchResponse])
async def search_scenes(
    query: str, 
    top_k: int = 20, 
    db: DBManager = Depends(get_db_manager)
):
    """Standalone scene search using semantic query."""
    if not query:
        raise HTTPException(status_code=400, detail="Query string is required")
        
    # 1. Encode query
    query_vec = db.ai_engine.extract_clip_text_feature(query)
    
    # 2. Search DB
    results = db.search_scenes(query_vec, top_k=top_k)
    
    # 3. Format response
    import json
    formatted = []
    for r in results:
        formatted.append(SceneSearchResponse(
            scene_id=r['scene_id'],
            file_id=r['file_id'],
            file_path=r['file_path'],
            scene_index=r['scene_index'],
            start_time=r['start_time'],
            end_time=r['end_time'],
            thumbnail_path=r['thumbnail_path'],
            caption=r['caption'],
            tags=json.loads(r['tags']) if isinstance(r['tags'], str) else (r['tags'] or []),
            character_tags=json.loads(r['character_tags']) if isinstance(r['character_tags'], str) else (r['character_tags'] or []),
            series_tags=json.loads(r['series_tags']) if isinstance(r['series_tags'], str) else (r['series_tags'] or []),
            score=r['score']
        ))
        
    return formatted
