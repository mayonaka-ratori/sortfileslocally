
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import io
from PIL import Image

from ..dependencies import get_db_manager
from src.data.db_manager import DBManager

router = APIRouter(prefix="/media", tags=["media"])

@router.get("/{file_id}/original")
def get_original(file_id: int, db: DBManager = Depends(get_db_manager)):
    """Serve the original file."""
    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
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
    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
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

