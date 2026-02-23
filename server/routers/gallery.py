
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import json
import os
import logging

logger = logging.getLogger(__name__)

from ..dependencies import get_db_manager, get_ai_engine
from src.data.db_manager import DBManager
from src.core.ai_models import AIEngine

router = APIRouter(prefix="/gallery", tags=["gallery"])

def safe_parse_json(x):
    """Helper to safely parse JSON strings from SQLite."""
    if not x: return []
    try:
        return json.loads(x)
    except Exception:
        return []

class MediaItemResponse(BaseModel):
    id: int
    file_path: str
    media_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    tags: List[str]
    character_tags: List[str]
    series_tags: List[str]
    caption: Optional[str] = None
    score: Optional[float] = None
    snippet: Optional[str] = None

class SearchFilters(BaseModel):
    tags: Optional[List[str]] = None
    character_tags: Optional[List[str]] = None
    series_tags: Optional[List[str]] = None
    media_type: Optional[str] = None
    extension: Optional[List[str]] = None

class HybridSearchRequest(BaseModel):
    query: Optional[str] = None
    filters: Optional[SearchFilters] = None
    top_k: int = 50

class HybridSearchResponse(BaseModel):
    results: List[MediaItemResponse]
    total_candidates: int
    filters_applied: SearchFilters

class SearchHistoryResponse(BaseModel):
    id: int
    query_text: str
    filters_json: Optional[str] = None
    result_count: int
    executed_at: str

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
        SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags, caption
        FROM files
        WHERE {' AND '.join(where_clauses)}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    import sqlite3
    conn = db._connect()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        c.execute(query, params)
        rows = c.fetchall()
        
        results = []
        for r in rows:
            results.append(MediaItemResponse(
                id=r['id'],
                file_path=r['file_path'],
                media_type=r['media_type'],
                width=r['width'],
                height=r['height'],
                tags=safe_parse_json(r['tags']),
                character_tags=safe_parse_json(r['character_tags']),
                series_tags=safe_parse_json(r['series_tags']),
                caption=r['caption']
            ))
        return results
    finally:
        conn.close()

@router.post("/search", response_model=HybridSearchResponse)
def search_media(
    request: Optional[HybridSearchRequest] = None,
    query: Optional[str] = Query(None),
    top_k: int = Query(default=50),
    ai: AIEngine = Depends(get_ai_engine),
    db: DBManager = Depends(get_db_manager)
):
    """
    Hybrid semantic search using CLIP + SQLite filtering.
    """
    # 1. Handle Backward Compatibility & Param Extraction
    final_query = query
    final_top_k = top_k
    final_filters = {}

    if request:
        if request.query:
            final_query = request.query
        if request.top_k != 50:
            final_top_k = request.top_k
        if request.filters:
            final_filters = request.filters.dict(exclude_none=True)

    if not final_query:
        return HybridSearchResponse(
            results=[],
            total_candidates=0,
            filters_applied=SearchFilters()
        )

    # 2. Extract Text Feature
    text_vec = ai.extract_clip_text_feature(final_query)
    
    # 3. Perform Hybrid Search
    hybrid_res = db.hybrid_search(text_vec, final_filters, top_k=final_top_k)
    
    # 4. Format Results
    # We still want to extract snippets for the results if applicable
    def extract_snippet(row_dict, q):
        q_lower = q.lower()
        if row_dict.get('caption') and q_lower in row_dict['caption'].lower():
             return f"[Caption] {row_dict['caption']}"
        if row_dict.get('audio_transcription'):
            try:
                audio_data = json.loads(row_dict['audio_transcription'])
                for seg in audio_data:
                    if q_lower in seg.get('text', '').lower():
                        return f"[Audio @{seg['start']:.1f}s] {seg['text']}"
            except Exception as e:
                logger.error(f"Error parsing audio_transcription JSON: {e}")
        if row_dict.get('frame_descriptions'):
            try:
                frame_data = json.loads(row_dict['frame_descriptions'])
                for seg in frame_data:
                    if q_lower in seg.get('text', '').lower():
                        return f"[Video @{seg['timestamp']:.1f}s] {seg['text']}"
            except Exception as e:
                logger.error(f"Error parsing frame_descriptions JSON: {e}")
        return None

    results = []
    for r in hybrid_res['results']:
        snippet = extract_snippet(r, final_query)
        results.append(MediaItemResponse(
            id=r['id'],
            file_path=r['file_path'],
            media_type=r['media_type'],
            width=r['width'],
            height=r['height'],
            tags=safe_parse_json(r['tags']),
            character_tags=safe_parse_json(r['character_tags']),
            series_tags=safe_parse_json(r['series_tags']),
            caption=r.get('caption'),
            score=r.get('score', 0.0),
            snippet=snippet
        ))
        
    # Auto-save search history (excluding empty query)
    if final_query:
        filters_str = json.dumps(final_filters) if final_filters else None
        db.save_search_history(final_query, filters_str, hybrid_res['total_candidates'])

    return HybridSearchResponse(
        results=results,
        total_candidates=hybrid_res['total_candidates'],
        filters_applied=SearchFilters(**final_filters)
    )

@router.get("/search-history", response_model=List[SearchHistoryResponse])
def get_search_history(limit: int = 20, db: DBManager = Depends(get_db_manager)):
    """Get recent search history."""
    history = db.get_search_history(limit=limit)
    return history

@router.delete("/search-history/{id}", status_code=204)
def delete_search_history_entry(id: int, db: DBManager = Depends(get_db_manager)):
    """Delete a single search history entry."""
    db.delete_search_history(id)
    return

@router.delete("/search-history", status_code=204)
def clear_search_history(db: DBManager = Depends(get_db_manager)):
    """Clear all search history."""
    db.clear_search_history()
    return

@router.get("/filters")
def get_filters(db: DBManager = Depends(get_db_manager)):
    """Get unique lists of characters and series for filtering."""
    import sqlite3
    conn = db._connect()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # Use SQLite json_each for efficient flattening
        try:
            c.execute("SELECT DISTINCT value FROM files, json_each(character_tags) WHERE is_processed=1 AND character_tags IS NOT NULL")
            all_chars = [row[0] for row in c.fetchall() if row[0]]
        except Exception:
            all_chars = []
            
        try:
            c.execute("SELECT DISTINCT value FROM files, json_each(series_tags) WHERE is_processed=1 AND series_tags IS NOT NULL")
            all_series = [row[0] for row in c.fetchall() if row[0]]
        except Exception:
            all_series = []
                
        return {
            "characters": sorted(all_chars),
            "series": sorted(all_series)
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
                if len(vr) == 0:
                    raise HTTPException(status_code=422, detail="Video has no readable frames")
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


class FaceResponse(BaseModel):
    id: int
    file_id: int
    face_index: int
    timestamp: float
    bbox: List[float]
    person_name: Optional[str] = None
    
class NameFaceRequest(BaseModel):
    person_name: str

@router.get("/{id}/faces", response_model=List[FaceResponse])
def get_file_faces(id: int, db: DBManager = Depends(get_db_manager)):
    """Get all detected faces for a specific media file."""
    faces = db.get_faces_for_file(id)
    results = []
    for f in faces:
        try:
            bbox = json.loads(f['bbox']) if f['bbox'] else []
        except:
            bbox = []
        results.append(FaceResponse(
            id=f['id'],
            file_id=f['file_id'],
            face_index=f['face_index'],
            timestamp=f['timestamp'],
            bbox=bbox,
            person_name=f['person_name']
        ))
    return results

@router.post("/faces/{face_id}/search", response_model=List[MediaItemResponse])
def search_by_face(face_id: int, top_k: int = Query(default=50), db: DBManager = Depends(get_db_manager)):
    """Search for media containing the same face."""
    face_vec = db.get_face_vector(face_id)
    if face_vec is None:
        raise HTTPException(status_code=404, detail="Face vector not found")
        
    search_results = db.search_similar_faces(face_vec, top_k=top_k)
    if not search_results:
        return []
        
    face_ids = [r[0] for r in search_results]
    face_details = db.get_face_details(face_ids)
    
    file_ids = list(set([f['file_id'] for f in face_details]))
    
    if not file_ids:
        return []
        
    rows = db.get_files_by_ids(file_ids)
    
    # Map scores by file_id taking maximum score for that file
    file_scores = {}
    face_scores = {r[0]: r[1] for r in search_results}
    for fd in face_details:
        fid = fd['file_id']
        f_score = face_scores.get(fd['face_id'], 0.0)
        file_scores[fid] = max(file_scores.get(fid, 0.0), f_score)

    results = []
    for r in rows:
        results.append(MediaItemResponse(
            id=r['id'],
            file_path=r['file_path'],
            media_type=r['media_type'],
            width=r['width'],
            height=r['height'],
            tags=safe_parse_json(r['tags']),
            character_tags=safe_parse_json(r['character_tags']),
            series_tags=safe_parse_json(r['series_tags']),
            caption=r['caption'],
            score=file_scores.get(r['id'], 0.0)
        ))
        
    results.sort(key=lambda x: x.score or 0.0, reverse=True)
    return results

@router.post("/faces/{face_id}/name")
def name_face(face_id: int, request: NameFaceRequest, db: DBManager = Depends(get_db_manager)):
    """Give a name to a specific face."""
    success = db.update_face_person(face_id, request.person_name)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to update name")
    return {"success": True}

