
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
        # For simplicity, open with PIL and resize
        # Note: This is synchronous, handled in threadpool by FastAPI (def)
        # Large files might be slow.
        # Ideally: generate thumbnail once and cache it on disk.
        # But for now, on-the-fly.
        
        # If video, maybe extract frame?
        # VideoProcessor.extract_frames is heavy.
        # Provide placeholder for video or implement frame extraction later.
        
        if media_type == 'video':
            # For now return placeholder or try to extract ONE frame if possible
            # Just return a generic icon or fail gracefully?
            # Or try to open with cv2?
            # Let's try simple frame extraction if `decord` is available.
            # But that's heavy.
            # Let's return local placeholder logic if possible, or just fail for now.
            # Actually, let's just create a blank image with text "VIDEO"
            img = Image.new('RGB', (size, size), color='black')
            # Text drawing requires font, let's just make it colored.
            pass # TODO: Video thumbnail
            
        else:
            img = Image.open(path)
            img.thumbnail((size, size)) # Preserves aspect ratio
            
        # Save to BytesIO
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)
        
        return StreamingResponse(buf, media_type="image/jpeg")
        
    except Exception as e:
        print(f"Thumbnail Error: {e}")
        # Return 404 or a placeholder image?
        # Let's return 500 or 404
        raise HTTPException(status_code=500, detail="Thumbnail generation failed")

