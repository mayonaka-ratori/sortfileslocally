import os
import sys
import shutil
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
import io
import json

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("src"))

from server.main import app
from server.dependencies import get_db_manager, get_ai_engine
from src.data.db_manager import DBManager

# Mock AIEngine
class MockAIEngine:
    def extract_clip_feature(self, img):
        # Return a dummy vector
        vec = np.ones(768, dtype=np.float32)
        return vec / np.linalg.norm(vec)
        
    def extract_clip_text_feature(self, text):
        pass

def setup_mock_db():
    test_db_dir = "data/test_db_rev_search"
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
        
    db = DBManager(test_db_dir)
    
    import sqlite3
    import faiss
    
    conn = db._connect()
    c = conn.cursor()
    
    items = [
        ("test1.jpg", "image", 1920, 1080),
        ("test2.png", "image", 800, 600)
    ]
    
    fids = []
    for path, mtype, w, h in items:
        c.execute('''
            INSERT INTO files (file_path, file_hash, file_size, media_type, created_at, modified_at, width, height, duration, is_processed, error_msg, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (path, "hash", 1000, mtype, 1, 1, w, h, None, 1, None, json.dumps([])))
        fids.append(c.lastrowid)
        
    conn.commit()
    conn.close()
    
    vec1 = np.ones(768, dtype=np.float32)
    vec1 /= np.linalg.norm(vec1)
    
    vec2 = np.random.randn(768).astype(np.float32)
    vec2 /= np.linalg.norm(vec2)
    
    faiss.normalize_L2(vec1[np.newaxis, :])
    faiss.normalize_L2(vec2[np.newaxis, :])
    
    db.clip_index.add_with_ids(vec1[np.newaxis, :], np.array([fids[0]], dtype='int64'))
    db.clip_index.add_with_ids(vec2[np.newaxis, :], np.array([fids[1]], dtype='int64'))
    
    return db, test_db_dir

def run_test():
    print("=== Testing Reverse Search Endpoint ===")
    db, test_db_dir = setup_mock_db()
    
    def override_get_db_manager():
        return db
        
    def override_get_ai_engine():
        return MockAIEngine()

    app.dependency_overrides[get_db_manager] = override_get_db_manager
    app.dependency_overrides[get_ai_engine] = override_get_ai_engine
    
    with TestClient(app) as client:
        img = Image.new('RGB', (100, 100), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        response = client.post(
            "/dedup/reverse-search", # Fixed endpoint path based on dedup router
            files={"file": ("test.jpg", img_byte_arr, "image/jpeg")},
            params={"top_k": 5}
        )
        
        if response.status_code != 200:
            print(f"FAILED: Status code {response.status_code}")
            print(response.text)
            assert False
            
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["file_path"] == "test1.jpg"
        assert data[0]["similarity"] > 0.99
        print(f"Top Result: {data[0]['file_path']} with similarity {data[0]['similarity']:.4f}")
        
        # Negative Test 1: Non-image file
        response2 = client.post(
            "/dedup/reverse-search",
            files={"file": ("test.txt", io.BytesIO(b"Hello world, not an image"), "text/plain")},
            params={"top_k": 5}
        )
        assert response2.status_code == 400
        print("Negative Test 1 (Non-image) Passed!")
        
        # Negative Test 2: File too large
        large_bytes = io.BytesIO(b"0" * (20 * 1024 * 1024 + 1))
        response3 = client.post(
            "/dedup/reverse-search",
            files={"file": ("large.jpg", large_bytes, "image/jpeg")},
            params={"top_k": 5}
        )
        assert response3.status_code == 413
        print("Negative Test 2 (Size Limit) Passed!")

        print("Reverse Search Test Passed!")

    app.dependency_overrides.clear()
    
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)

if __name__ == "__main__":
    run_test()
