
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel, Field
import json
import logging

logger = logging.getLogger(__name__)

from ..dependencies import get_db_manager, get_ai_engine
from src.data.db_manager import DBManager
from src.core.ai_models import AIEngine
from .gallery import MediaItemResponse, safe_parse_json, HybridSearchRequest

router = APIRouter(prefix="/albums", tags=["albums"])

class AlbumResponse(BaseModel):
    id: int
    name: str
    is_dynamic: bool
    query_json: Optional[str] = None
    cover_file_id: Optional[int] = None
    item_count: int
    created_at: str
    updated_at: str

class AlbumCreateRequest(BaseModel):
    name: str
    is_dynamic: bool = False
    query_json: Optional[str] = None

class AlbumUpdateRequest(BaseModel):
    name: Optional[str] = None
    query_json: Optional[str] = None
    cover_file_id: Optional[int] = None

class AddItemsRequest(BaseModel):
    file_ids: List[int]

@router.get("/", response_model=List[AlbumResponse])
def list_albums(db: DBManager = Depends(get_db_manager)):
    return db.get_albums()

@router.post("/", response_model=int)
def create_album(request: AlbumCreateRequest, db: DBManager = Depends(get_db_manager)):
    if request.is_dynamic:
        if not request.query_json or not request.query_json.strip():
            raise HTTPException(status_code=422, detail="Dynamic albums require a valid search query")
        try:
            data = json.loads(request.query_json)
            HybridSearchRequest(**data)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid query format for dynamic album")
    return db.create_album(request.name, request.is_dynamic, request.query_json)

@router.get("/{id}", response_model=AlbumResponse)
def get_album(id: int, db: DBManager = Depends(get_db_manager)):
    album = db.get_album(id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return album

@router.put("/{id}")
def update_album(id: int, request: AlbumUpdateRequest, db: DBManager = Depends(get_db_manager)):
    album = db.get_album(id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # If it's a dynamic album and query_json is being updated (or we're checking its current state), validate it
    is_dynamic = album.get("is_dynamic", False)
    
    if is_dynamic and request.query_json is not None:
        if not request.query_json or not request.query_json.strip():
            raise HTTPException(status_code=422, detail="Dynamic albums require a valid search query")
        try:
            data = json.loads(request.query_json)
            HybridSearchRequest(**data)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid query format for dynamic album")

    db.update_album(id, name=request.name, query_json=request.query_json, cover_file_id=request.cover_file_id)
    return {"success": True}

@router.delete("/{id}")
def delete_album(id: int, db: DBManager = Depends(get_db_manager)):
    success = db.delete_album(id)
    if not success:
        raise HTTPException(status_code=404, detail="Album not found")
    return {"success": True}

@router.get("/{id}/media", response_model=List[MediaItemResponse])
def get_album_media(
    id: int, 
    db: DBManager = Depends(get_db_manager), 
    ai: AIEngine = Depends(get_ai_engine)
):
    media_items = db.get_album_media(id, ai_engine=ai)
    
    # Format results to match MediaItemResponse
    results = []
    for r in media_items:
        results.append(MediaItemResponse(
            id=r['id'],
            file_path=r['file_path'],
            media_type=r['media_type'],
            width=r.get('width'),
            height=r.get('height'),
            tags=safe_parse_json(r['tags']),
            character_tags=safe_parse_json(r['character_tags']),
            series_tags=safe_parse_json(r['series_tags']),
            caption=r.get('caption'),
            score=r.get('score')
        ))
    return results

@router.post("/{id}/items")
def add_to_album(id: int, request: AddItemsRequest, db: DBManager = Depends(get_db_manager)):
    db.add_to_album(id, request.file_ids)
    return {"success": True}

@router.delete("/{id}/items")
def remove_from_album(id: int, request: AddItemsRequest, db: DBManager = Depends(get_db_manager)):
    db.remove_from_album(id, request.file_ids)
    return {"success": True}
