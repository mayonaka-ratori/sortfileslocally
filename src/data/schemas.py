
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
import datetime
import json

@dataclass
class MediaItem:
    """Represents a single media file found in scanning."""
    file_path: str
    file_hash: str # MD5 or similar
    file_size: int
    media_type: str # 'image' or 'video'
    created_at: float # unix user_timestamp
    modified_at: float
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None # For video
    fps: Optional[float] = None # For video
    
    # Processing Status
    is_processed: bool = False
    tags: List[str] = field(default_factory=list)
    character_tags: List[str] = field(default_factory=list)
    series_tags: List[str] = field(default_factory=list)
    error_msg: Optional[str] = None
    audio_transcription: Optional[List[Dict[str, Any]]] = None
    frame_descriptions: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class VectorData:
    """Stores vector embeddings."""
    clip_vector: List[float] # 768 dim
    face_vectors: List[List[float]] # List of 512 dim vectors (multiple faces)
    
    def to_json(self):
        return json.dumps({
            'clip_vector': self.clip_vector,
            'face_vectors': self.face_vectors
        })
    
    @staticmethod
    def from_json(json_str: str):
        data = json.loads(json_str)
        return VectorData(
            clip_vector=data['clip_vector'],
            face_vectors=data['face_vectors']
        )

@dataclass
class FaceData:
    """Detailed face info for clustering (not just vector)."""
    embedding: List[float] # 512
    bbox: List[int]
    det_score: float
    kps: Optional[List[List[int]]] = None
    timestamp: float = 0.0 # For video frames
    
    def to_dict(self):
        return asdict(self)

@dataclass
class ProcessingResult:
    """Result returned from Processor."""
    file_path: str
    success: bool
    media_item: MediaItem
    vector_data: Optional[VectorData] = None
    faces: List[FaceData] = field(default_factory=list)
