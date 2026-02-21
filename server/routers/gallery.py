
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import json
import os

from ..dependencies import get_db_manager, get_ai_engine
from src.data.db_manager import DBManager
from src.core.ai_models import AIEngine

router = APIRouter(prefix="/gallery", tags=["gallery"])

class MediaItemResponse(BaseModel):
    id: int
    file_path: str
    media_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    tags: List[str]
    character_tags: List[str]
    series_tags: List[str]
    score: Optional[float] = None
    snippet: Optional[str] = None

@router.get("/", response_model=List[MediaItemResponse])
def list_media(
    limit: int = 50,
    offset: int = 0,
    character: Optional[str] = None,
    series: Optional[str] = None,
    tag: Optional[str] = None,
    media_type: Optional[str] = None,
    db: DBManager = Depends(get_db_manager)
):
    """
    List media files with optional filtering.
    """
    # Build Query
    where_clauses = ["is_processed=1"]
    params = []

    if character and character != "All":
        where_clauses.append("character_tags LIKE ?")
        params.append(f'%"{character}"%')
    
    if series and series != "All":
        where_clauses.append("series_tags LIKE ?")
        params.append(f'%"{series}"%')

    if tag:
        where_clauses.append("tags LIKE ?")
        params.append(f'%"{tag}"%')
        
    if media_type:
        where_clauses.append("media_type = ?")
        params.append(media_type.lower())

    query = f"""
        SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags
        FROM files
        WHERE {' AND '.join(where_clauses)}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        c.execute(query, params)
        rows = c.fetchall()
        
        results = []
        for r in rows:
            # Helper to safely parse JSON
            def parse_json(x):
                if not x: return []
                try:
                    return json.loads(x)
                except:
                    return []

            results.append(MediaItemResponse(
                id=r['id'],
                file_path=r['file_path'],
                media_type=r['media_type'],
                width=r['width'],
                height=r['height'],
                tags=parse_json(r['tags']),
                character_tags=parse_json(r['character_tags']),
                series_tags=parse_json(r['series_tags'])
            ))
        return results
    finally:
        conn.close()

@router.post("/search", response_model=List[MediaItemResponse])
def search_media(
    query: str,
    top_k: int = 50,
    ai: AIEngine = Depends(get_ai_engine),
    db: DBManager = Depends(get_db_manager)
):

    """
    Semantic search using CLIP.
    """
    if not query:
        return []

    # 1. Fetch from SQLite via Text Search
    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Text match search in audio_transcription and frame_descriptions
    escaped_query = query.replace("%", "\\%").replace("_", "\\_")
    text_search_query = f"%{escaped_query}%"
    c.execute("""
        SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags, audio_transcription, frame_descriptions
        FROM files
        WHERE media_type = 'video' AND 
              (audio_transcription LIKE ? OR frame_descriptions LIKE ?)
        LIMIT 20
    """, (text_search_query, text_search_query))
    text_rows = c.fetchall()
    
    text_match_paths = [r['file_path'] for r in text_rows]
    text_results_map = {r['file_path']: dict(r) for r in text_rows}

    # 2. Extract Text Feature
    text_vec = ai.extract_clip_text_feature(query)
    
    # 3. Search in FAISS
    search_results = db.search_similar_images(text_vec, top_k=top_k)
    
    paths = [r[0] for r in search_results]
    scores = {r[0]: r[1] for r in search_results}
    
    # Merge paths, prioritizing exact text matches for videos
    all_paths = list(text_match_paths)
    for p in paths:
        if p not in text_match_paths:
            all_paths.append(p)
    
    if not all_paths:
        conn.close()
        return []
        
    # 4. Fetch Metadata for vector matches
    paths_to_fetch = [p for p in all_paths if p not in text_results_map]
    row_map = {**text_results_map}
    
    if paths_to_fetch:
        placeholders = ','.join(['?'] * len(paths_to_fetch))
        c.execute(f"""
            SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags, audio_transcription, frame_descriptions
            FROM files
            WHERE file_path IN ({placeholders})
        """, paths_to_fetch)
        
        faiss_rows = c.fetchall()
        for r in faiss_rows:
            row_map[r['file_path']] = dict(r)
            
    conn.close()
    
    # Re-sort match search
    # Format results
    results = []
    
    def extract_snippet(row_dict, q):
        q_lower = q.lower()
        if row_dict.get('audio_transcription'):
            try:
                audio_data = json.loads(row_dict['audio_transcription'])
                for seg in audio_data:
                    if q_lower in seg.get('text', '').lower():
                        return f"[Audio @{seg['start']:.1f}s] {seg['text']}"
            except:
                pass
        if row_dict.get('frame_descriptions'):
            try:
                frame_data = json.loads(row_dict['frame_descriptions'])
                for seg in frame_data:
                    if q_lower in seg.get('text', '').lower():
                        return f"[Video @{seg['timestamp']:.1f}s] {seg['text']}"
            except:
                pass
        return None

    for path in all_paths:
        if path in row_map:
            r = row_map[path]
            snippet = extract_snippet(r, query)
            results.append(MediaItemResponse(
                id=r['id'],
                file_path=r['file_path'],
                media_type=r['media_type'],
                width=r['width'],
                height=r['height'],
                tags=json.loads(r['tags']) if r['tags'] else [],
                character_tags=json.loads(r['character_tags']) if r['character_tags'] else [],
                series_tags=json.loads(r['series_tags']) if r['series_tags'] else [],
                score=scores.get(path, 1.0), # Give text matches 1.0 score by default
                snippet=snippet
            ))
            
    return results[:top_k]

@router.get("/filters")
def get_filters(db: DBManager = Depends(get_db_manager)):
    """Get unique lists of characters and series for filtering."""
    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        c.execute("SELECT character_tags, series_tags FROM files WHERE is_processed=1")
        rows = c.fetchall()
        
        all_chars = set()
        all_series = set()
        
        for r in rows:
            try:
                if r['character_tags']:
                    all_chars.update(json.loads(r['character_tags']))
                if r['series_tags']:
                    all_series.update(json.loads(r['series_tags']))
            except:
                pass
                
        return {
            "characters": sorted(list(all_chars)),
            "series": sorted(list(all_series))
        }
    finally:
        conn.close()

class ChatRequest(BaseModel):
    file_path: str
    prompt: str

@router.post("/chat")
def chat_with_gallery(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    vlm: 'VLMEngine' = Depends(lambda: __import__('server.dependencies', fromlist=['get_vlm_engine']).get_vlm_engine())
):
    """
    Ask a question about a specific image using VLM.
    """
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        from PIL import Image
        img = None
        
        try:
            # Try opening as image first
            img = Image.open(request.file_path).convert("RGB")
        except Exception:
            # If it fails, assume it's a video and grab a frame
            try:
                import decord
                vr = decord.VideoReader(request.file_path)
                mid_frame = vr[len(vr)//2].asnumpy()
                img = Image.fromarray(mid_frame).convert("RGB")
            except ImportError:
                 raise HTTPException(status_code=400, detail="decord is required for video VQA")
            except Exception as e:
                 raise HTTPException(status_code=400, detail=f"Failed to extract frame from video: {e}")

        if img is not None:
             answer = vlm.ask_image(img, request.prompt)
             
             # Schedule VRAM release
             background_tasks.add_task(vlm.unload)
             
             return {"answer": answer}
        else:
             raise HTTPException(status_code=500, detail="Could not load media")
             
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
