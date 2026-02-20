from typing import List, Dict, Any, Optional
import json
from ..data.schemas import MediaItem, FaceData

class MetadataManager:
    """
    Handles metadata operations: merging tags, updating schemas, 
    and preparing data for DB storage.
    Abstracts direct object manipulation from Processor.
    """
    
    @staticmethod
    def update_item_tags(item: MediaItem, new_tags: List[str] = None, char_tags: List[str] = None, series_tags: List[str] = None, style: str = None):
        """
        Update tags on a MediaItem.
        """
        # Generic Tags
        if not item.tags:
            item.tags = []
        if new_tags:
            # Add unique
            current_set = set(item.tags)
            for t in new_tags:
                if t not in current_set:
                    item.tags.append(t)
        
        # Style Tag
        if style:
            if style not in item.tags:
                item.tags.append(style)
                
        # Character & Series (Overwrite or Append? Usually overwrite during full re-scan, but append if partial?)
        # For now, overwrite is what Processor did.
        if char_tags is not None:
             item.character_tags = char_tags
             
        if series_tags is not None:
             item.series_tags = series_tags
             
    @staticmethod
    def create_face_data(raw_faces: List[Dict[str, Any]]) -> List[FaceData]:
        """Convert raw face dicts to FaceData schema."""
        face_vecs = []
        for f in raw_faces:
            face_vecs.append(FaceData(
                embedding=f['embedding'].tolist(),
                bbox=f['bbox'],
                det_score=f['det_score'],
                kps=f['kps'],
                timestamp=f.get('timestamp', 0.0)
            ))
        return face_vecs
