import sys
import os
from unittest.mock import MagicMock

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

# Mock ONLY if missing
for mod in ["open_clip", "decord", "PIL", "facenet_pytorch", "insightface", "torch", "torchvision", "torchaudio", "onnxruntime", "pandas", "faiss", "cv2"]:
    if not is_available(mod):
        sys.modules[mod] = MagicMock()

# Models must be mocked to avoid model loading during test collection
sys.modules["src.core.ai_models"] = MagicMock()
sys.modules["src.core.vlm_engine"] = MagicMock()
sys.modules["src.core.processor"] = MagicMock()

import pytest
import json
from fastapi.testclient import TestClient
from server.main import app
from server.dependencies import get_db_manager
from src.data.db_manager import DBManager

@pytest.fixture
def client(tmp_path):
    db_dir = tmp_path / "db"
    db = DBManager(db_dir=str(db_dir))
    
    # Override dependency
    app.dependency_overrides[get_db_manager] = lambda: db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

def test_create_dynamic_album_validation(client):
    # Missing query_json
    payload = {
        "name": "Dynamic Trip",
        "is_dynamic": True,
        "query_json": None
    }
    response = client.post("/albums/", json=payload)
    assert response.status_code == 422
    # Match the actual error message in albums.py
    assert "Dynamic albums require a valid search query" in response.json()["detail"]

def test_update_dynamic_album_validation(client):
    # Create static first
    payload = {"name": "Test", "is_dynamic": False}
    resp = client.post("/albums/", json=payload)
    # create_album returns int directly!
    album_id = resp.json()
    
    # Create it as dynamic from start to test update on dynamic album
    payload_dyn = {"name": "TestDyn", "is_dynamic": True, "query_json": '{"text": "cats"}'}
    resp_dyn = client.post("/albums/", json=payload_dyn)
    assert resp_dyn.status_code == 200
    dyn_id = resp_dyn.json()
    
    # Try updating dynamic with invalid JSON
    update = {
        "query_json": "invalid-json{"
    }
    response = client.put(f"/albums/{dyn_id}", json=update)
    assert response.status_code == 422
    assert "Invalid query format" in response.json()["detail"]
