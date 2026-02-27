import os
import shutil
import json
import io
import pytest
import sys
from unittest.mock import MagicMock, patch

# Robust availability check
def is_available(mod_name):
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
        if 'mock' in str(type(mod)).lower(): return False
        return True
    try:
        mod = __import__(mod_name)
        if 'mock' in str(type(mod)).lower(): return False
        return True
    except (ImportError, Exception):
        return False

# Negative test mock for PIL
def mock_open(fp, **kwargs):
    # Ensure fp is at start if it's a stream
    if hasattr(fp, 'seek'): fp.seek(0)
    content = fp.read()
    if b"Hello world" in content:
        raise OSError("cannot identify image file")
    mock_img = MagicMock()
    mock_img.convert.return_value = mock_img
    mock_img.width = 100
    mock_img.height = 100
    return mock_img

# Mock ONLY if missing and not already mocked or real
# Modules we want to test real logic for should not be mocked here
for mod in ["open_clip", "decord", "facenet_pytorch", "insightface", "onnxruntime", "pandas", "cv2"]:
    if not is_available(mod):
        m = MagicMock()
        sys.modules[mod] = m

# We want REAL PIL, numpy, faiss, torch, torchvision if available
# because the endpoint imports them and we might want to patch them specifically.
for mod in ["PIL", "numpy", "faiss", "torch", "torchvision"]:
    if not is_available(mod):
        # Even if missing, we'll let the individual tests handle mocking or skipping
        # to avoid polluting sys.modules for other tests that might have them.
        pass

# Models must be mocked
sys.modules["src.core.ai_models"] = MagicMock()

import numpy as np
from fastapi.testclient import TestClient
from server.main import app
from server.dependencies import get_db_manager, get_ai_engine
from src.data.db_manager import DBManager

# Mock AIEngine
class MockAIEngine:
    def extract_clip_feature(self, img):
        vec = np.ones(768, dtype=np.float32)
        return vec / np.linalg.norm(vec)
    def extract_clip_text_feature(self, text):
        pass

@pytest.fixture
def mock_db_rev_search(tmp_path):
    test_db_dir = str(tmp_path / "data" / "test_db_rev_search")
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
        
    db = DBManager(test_db_dir)
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
    
    yield db, test_db_dir, fids
    
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)

def test_reverse_search_endpoint(mock_db_rev_search):
    db, test_db_dir, fids = mock_db_rev_search
    
    db.search_similar_images = MagicMock(return_value=[("test1.jpg", 0.999), ("test2.png", 0.5)])
    
    def override_get_db_manager():
        return db
    def override_get_ai_engine():
        return MockAIEngine()

    app.dependency_overrides[get_db_manager] = override_get_db_manager
    app.dependency_overrides[get_ai_engine] = override_get_ai_engine
    
    # We MUST patch PIL.Image.open in the module where it's used if we want to be sure
    # But patching it globally for the duration of the test is easier.
    with patch("PIL.Image.open", side_effect=mock_open):
        with TestClient(app) as client:
            img_byte_arr = io.BytesIO()
            img_byte_arr.write(b"good image data")
            img_byte_arr.seek(0)
            
            response = client.post(
                "/dedup/reverse-search",
                files={"file": ("test.jpg", img_byte_arr, "image/jpeg")},
                params={"top_k": 5}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["file_path"] == "test1.jpg"
            
            # Negative Test 1: Non-image file
            response2 = client.post(
                "/dedup/reverse-search",
                files={"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")},
                params={"top_k": 5}
            )
            assert response2.status_code == 400

    app.dependency_overrides.clear()
