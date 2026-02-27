import os
import json
import pytest
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

@pytest.fixture
def api_components():
    from fastapi.testclient import TestClient
    from server.main import app
    from src.data.db_manager import DBManager
    from server.dependencies import get_db_manager
    return {
        "TestClient": TestClient,
        "app": app,
        "DBManager": DBManager,
        "get_db_manager": get_db_manager
    }

@pytest.fixture
def client(tmp_path, api_components):
    TestClient = api_components["TestClient"]
    app = api_components["app"]
    DBManager = api_components["DBManager"]
    get_db_manager = api_components["get_db_manager"]
    
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
