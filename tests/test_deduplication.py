import os
import shutil
import pytest
from unittest.mock import MagicMock, patch

# Skip if requested in CI
if os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("Skipping deduplication tests in CI", allow_module_level=True)

@pytest.fixture
def dedup_components():
    import numpy as np
    try:
        import faiss
    except ImportError:
        faiss = MagicMock()
    from PIL import Image
    
    # Internal core modules
    from src.core.deduplication import Deduplicator
    from src.data.db_manager import DBManager
    from src.data.schemas import MediaItem, ProcessingResult, VectorData
    
    return {
        "np": np,
        "faiss": faiss,
        "Image": Image,
        "Deduplicator": Deduplicator,
        "DBManager": DBManager,
        "MediaItem": MediaItem,
        "ProcessingResult": ProcessingResult,
        "VectorData": VectorData
    }

@pytest.mark.ai_models
def test_deduplication_logic(tmp_path, dedup_components):
    np = dedup_components["np"]
    Image = dedup_components["Image"]
    DBManager = dedup_components["DBManager"]
    Deduplicator = dedup_components["Deduplicator"]
    MediaItem = dedup_components["MediaItem"]
    
    test_db_dir = str(tmp_path / "data" / "test_db_dedup")
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
        
    db = DBManager(test_db_dir)
    deduper = Deduplicator(db)
    
    import tempfile
    tdir = tempfile.mkdtemp()
    
    try:
        img_a_path = os.path.join(tdir, "img_a_big.jpg")
        img_b_path = os.path.join(tdir, "img_b_small.jpg")
        Image.new('RGB', (1920, 1080), color='red').save(img_a_path)
        Image.new('RGB', (640, 480), color='blue').save(img_b_path)
        
        # Pair 1: High Sim, A bigger resolution
        vec1 = np.random.randn(768).astype(np.float32)
        vec1 /= np.linalg.norm(vec1)
        
        # Item A (Big)
        item_a = MediaItem(img_a_path, "hash_a", 2000, "image", 1000, 1000, 1920, 1080)
        # Item B (Small, sim > 0.95)
        item_b = MediaItem(img_b_path, "hash_b", 500, "image", 2000, 2000, 640, 480)
        
        # Make vec2 close to vec1
        vec2 = vec1 + np.random.normal(0, 0.01, 768).astype(np.float32) 
        vec2 /= np.linalg.norm(vec2)
        
        # Store
        _inject_item(db, item_a, vec1, dedup_components)
        _inject_item(db, item_b, vec2, dedup_components)
        
        # Pair 2: Video, Different Duration
        vec3 = np.random.randn(768).astype(np.float32)
        vec3 /= np.linalg.norm(vec3)
        vec4 = vec3 + np.random.normal(0, 0.005, 768).astype(np.float32)
        vec4 /= np.linalg.norm(vec4)
        
        vid_a = MediaItem("vid_a.mp4", "h_va", 5000, "video", 100, 100, 1920, 1080, duration=60.0)
        vid_b = MediaItem("vid_b.mp4", "h_vb", 5000, "video", 100, 100, 1920, 1080, duration=120.0)
        
        _inject_item(db, vid_a, vec3, dedup_components)
        _inject_item(db, vid_b, vec4, dedup_components)
        
        # Run
        pairs = deduper.find_duplicates(threshold_img=0.90, threshold_vid=0.90)
        
        # Assertions
        img_pair = [p for p in pairs if "img_" in p.file_a.file_path]
        assert len(img_pair) == 1
        assert img_pair[0].recommended_action == 'keep_a' 
        
        vid_pair = [p for p in pairs if "vid_" in p.file_a.file_path]
        assert len(vid_pair) == 0
    finally:
        if os.path.exists(tdir):
            shutil.rmtree(tdir)

def _inject_item(db, item, vector, components):
    import sqlite3
    import json
    faiss = components["faiss"]
    np = components["np"]
    conn = sqlite3.connect(db.sqlite_path)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO files (file_path, file_hash, file_size, media_type, created_at, modified_at, width, height, duration, is_processed, error_msg, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (item.file_path, item.file_hash, item.file_size, item.media_type, item.created_at, item.modified_at, item.width, item.height, item.duration, 1, None, json.dumps([])))
    
    fid = c.lastrowid
    conn.commit()
    conn.close()
    
    faiss.normalize_L2(vector[np.newaxis, :])
    db.clip_index.add_with_ids(vector[np.newaxis, :], np.array([fid], dtype='int64'))
