
import os
import sys
import shutil
import numpy as np
from PIL import Image
import sqlite3
import faiss

sys.path.append(os.path.abspath("src"))

from src.core.deduplication import Deduplicator
from src.data.db_manager import DBManager
from src.data.schemas import MediaItem, ProcessingResult, VectorData

def test_deduplication_logic():
    print("=== Testing Deduplication Logic ===")
    
    test_db_dir = "data/test_db_dedup"
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
        
    db = DBManager(test_db_dir)
    deduper = Deduplicator(db)
    
    # Needs to inject dummy data into DB (SQLite and FAISS)
    print("Injecting dummy pairs...")
    
    # Pair 1: High Sim, A bigger resolution
    vec1 = np.random.randn(768).astype(np.float32)
    vec1 /= np.linalg.norm(vec1)
    
    # Item A (Big)
    item_a = MediaItem("path/to/img_a_big.jpg", "hash_a", 2000, "image", 1000, 1000, 1920, 1080)
    # Item B (Small, sim > 0.95)
    item_b = MediaItem("path/to/img_b_small.jpg", "hash_b", 500, "image", 2000, 2000, 640, 480)
    
    # Make vec2 close to vec1
    vec2 = vec1 + np.random.normal(0, 0.01, 768).astype(np.float32) # Very small noise
    vec2 /= np.linalg.norm(vec2)
    
    # Store
    _inject_item(db, item_a, vec1)
    _inject_item(db, item_b, vec2)
    
    # Pair 2: Video, Different Duration (Should NOT match even if vectors close)
    # Clip vectors for video often similar if content similar
    vec3 = np.random.randn(768).astype(np.float32)
    vec3 /= np.linalg.norm(vec3)
    vec4 = vec3 + np.random.normal(0, 0.005, 768).astype(np.float32)
    vec4 /= np.linalg.norm(vec4)
    
    vid_a = MediaItem("vid_a.mp4", "h_va", 5000, "video", 100, 100, 1920, 1080, duration=60.0)
    vid_b = MediaItem("vid_b.mp4", "h_vb", 5000, "video", 100, 100, 1920, 1080, duration=120.0) # Diff duration
    
    _inject_item(db, vid_a, vec3)
    _inject_item(db, vid_b, vec4)
    
    try:
        # Run
        pairs = deduper.find_duplicates(threshold_img=0.90, threshold_vid=0.90)
        
        print(f"Found pairs: {len(pairs)}")
        for p in pairs:
            print(f"Match: {p.file_a.file_path} <-> {p.file_b.file_path} | Sim: {p.similarity:.4f} | Rec: {p.recommended_action}")
    except Exception as e:
        print(f"Error caught in test: {e}")
        import traceback
        traceback.print_exc()
        raise e
    
    # Assertions
    # 1. Image pair should be found
    img_pair = [p for p in pairs if "img_" in p.file_a.file_path]
    assert len(img_pair) == 1
    assert img_pair[0].recommended_action == 'keep_a' # Because A is bigger resoluton
    
    # 2. Video pair should NOT be found (duration mismatch)
    vid_pair = [p for p in pairs if "vid_" in p.file_a.file_path]
    assert len(vid_pair) == 0
    
    print("Deduplication Test Passed!")
    
def _inject_item(db, item, vector):
    conn = sqlite3.connect(db.sqlite_path)
    c = conn.cursor()
    
    import json
    c.execute('''
        INSERT INTO files (file_path, file_hash, file_size, media_type, created_at, modified_at, width, height, duration, is_processed, error_msg, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (item.file_path, item.file_hash, item.file_size, item.media_type, item.created_at, item.modified_at, item.width, item.height, item.duration, 1, None, json.dumps([])))
    
    fid = c.lastrowid
    conn.commit()
    conn.close()
    
    faiss.normalize_L2(vector[np.newaxis, :])
    db.clip_index.add_with_ids(vector[np.newaxis, :], np.array([fid], dtype='int64'))

if __name__ == "__main__":
    test_deduplication_logic()
