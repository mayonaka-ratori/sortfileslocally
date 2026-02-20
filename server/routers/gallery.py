
from fastapi import APIRouter, Depends, Query, HTTPException
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

    # 1. Extract Text Feature
    text_vec = ai.extract_clip_text_feature(query)
    
    # 2. Search in FAISS
    # DBManager.search_similar_images returns [(path, score), ...]
    # We need to fetch metadata for them.
    
    search_results = db.search_similar_images(text_vec, top_k=top_k)
    
    paths = [r[0] for r in search_results]
    scores = {r[0]: r[1] for r in search_results}
    
    if not paths:
        return []
        
    # 3. Fetch Metadata
    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    placeholders = ','.join(['?'] * len(paths))
    c.execute(f"""
        SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags
        FROM files
        WHERE file_path IN ({placeholders})
    """, paths)
    
    rows = c.fetchall()
    conn.close()
    
    # Re-sort match search order
    results = []
    row_map = {r['file_path']: r for r in rows}
    
    for path in paths:
        if path in row_map:
            r = row_map[path]
            results.append(MediaItemResponse(
                id=r['id'],
                file_path=r['file_path'],
                media_type=r['media_type'],
                width=r['width'],
                height=r['height'],
                tags=json.loads(r['tags']) if r['tags'] else [],
                character_tags=json.loads(r['character_tags']) if r['character_tags'] else [],
                series_tags=json.loads(r['series_tags']) if r['series_tags'] else [],
                score=scores.get(path)
            ))
            
    return results

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
