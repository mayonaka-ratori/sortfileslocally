import os
import shutil
import json
import io
import pytest
import sys
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_missing_deps():
    from importlib.machinery import ModuleSpec
    
    mocks = {}
    for mod_name in ["open_clip", "decord", "facenet_pytorch", "insightface", "onnxruntime", "pandas", "cv2", "src.core.ai_models", "src.core.vlm_engine", "src.core.processor"]:
        m = MagicMock()
        m.__spec__ = ModuleSpec(mod_name, None)
        mocks[mod_name] = m
        
    with patch.dict("sys.modules", mocks):
        yield mocks

# Negative test mock for PIL
def mock_open(fp, **kwargs):
    # Ensure fp is at start if it's a stream
    if hasattr(fp, 'seek'): fp.seek(0)
    if hasattr(fp, 'read'):
        content = fp.read()
    else:
        content = b""
    if b"Hello world" in content:
        raise OSError("cannot identify image file")
    mock_img = MagicMock()
    mock_img.convert.return_value = mock_img
    mock_img.width = 100
    mock_img.height = 100
    return mock_img

@pytest.fixture
def api_components():
    import numpy as np
    from server.main import app
    from server.dependencies import get_db_manager, get_ai_engine
    from src.data.db_manager import DBManager
    return {
        "np": np,
        "app": app,
        "get_db_manager": get_db_manager,
        "get_ai_engine": get_ai_engine,
        "DBManager": DBManager
    }

# Mock AIEngine
class MockAIEngine:
    def __init__(self, np_mod):
        self.np = np_mod
    def extract_clip_feature(self, img):
        vec = self.np.ones(768, dtype=self.np.float32)
        return vec / self.np.linalg.norm(vec)
    def extract_clip_text_feature(self, text):
        pass

@pytest.fixture
def mock_db_rev_search(tmp_path, api_components):
    DBManager = api_components["DBManager"]
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

def test_reverse_search_endpoint(mock_db_rev_search, api_components):
    db, test_db_dir, fids = mock_db_rev_search
    app = api_components["app"]
    get_db_manager = api_components["get_db_manager"]
    get_ai_engine = api_components["get_ai_engine"]
    np = api_components["np"]
    from fastapi.testclient import TestClient
    
    db.search_similar_images = MagicMock(return_value=[("test1.jpg", 0.999), ("test2.png", 0.5)])
    
    def override_get_db_manager():
        return db
    def override_get_ai_engine():
        return MockAIEngine(np)

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
