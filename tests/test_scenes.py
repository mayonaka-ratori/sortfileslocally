
import os
import shutil
import json
import sqlite3
import pytest
import sys
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Mocking for environment-dependent imports
@pytest.fixture(autouse=True)
def mock_missing_deps():
    from importlib.machinery import ModuleSpec
    
    mocks = {}
    # Modules to mock with __spec__ for robust import behavior
    for mod_name in [
        "open_clip", "decord", "facenet_pytorch", "insightface", "onnxruntime", 
        "pandas", "cv2", "scenedetect", "sklearn", 
        "src.core.ai_models", "src.core.vlm_engine", "src.core.inference", 
        "src.core.intelligence", "src.core.video_processor", "src.core.exporter",
        "src.core.processor" # Added from instruction
    ]:
        m = MagicMock()
        m.__spec__ = ModuleSpec(mod_name, None)
        mocks[mod_name] = m
        
    # Mock AIEngine class specifically
    mock_ai_engine_cls = MagicMock()
    mock_ai_engine_inst = MagicMock()
    mock_ai_engine_inst.extract_clip_feature.return_value = np.zeros(768, dtype=np.float32)
    mock_ai_engine_inst.extract_clip_text_feature.return_value = np.zeros(768, dtype=np.float32)
    mock_ai_engine_cls.return_value = mock_ai_engine_inst
    mocks["src.core.ai_models"].AIEngine = mock_ai_engine_cls

    with patch.dict("sys.modules", mocks):
        yield mocks

@pytest.fixture
def api_components():
    # Import inside fixture to avoid top-level import issues
    from server.main import app
    from server.dependencies import get_db_manager, get_ai_engine, get_processor
    from src.data.db_manager import DBManager
    from src.data.schemas import MediaItem, ProcessingResult, VideoSceneData
    return {
        "app": app,
        "get_db_manager": get_db_manager,
        "get_ai_engine": get_ai_engine,
        "get_processor": get_processor,
        "DBManager": DBManager,
        "MediaItem": MediaItem,
        "ProcessingResult": ProcessingResult,
        "VideoSceneData": VideoSceneData
    }

@pytest.fixture
def test_db(tmp_path, api_components):
    test_db_dir = str(tmp_path / "data" / "test_db_scenes")
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir, ignore_errors=True)
    
    app = api_components["app"]
    DBManager = api_components["DBManager"]
    
    db = DBManager(test_db_dir)
    mock_ai_engine = MagicMock()
    mock_ai_engine.extract_clip_feature.return_value = np.zeros(768, dtype=np.float32)
    mock_ai_engine.extract_clip_text_feature.return_value = np.zeros(768, dtype=np.float32)
    db.ai_engine = mock_ai_engine
    db._migrate_schema() # Ensure schema is up to date

    # Patch dependencies
    app.dependency_overrides[api_components["get_db_manager"]] = lambda: db
    app.dependency_overrides[api_components["get_ai_engine"]] = lambda: mock_ai_engine
    app.dependency_overrides[api_components["get_processor"]] = lambda: MagicMock()
    
    yield db, test_db_dir
    
    app.dependency_overrides.clear()
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir, ignore_errors=True)

def test_detect_scenes_endpoint(test_db, api_components):
    db, _ = test_db
    app = api_components["app"]
    get_processor = api_components["get_processor"]
    
    # 1. Setup a video file in DB
    conn = db._connect()
    c = conn.cursor()
    c.execute('''
        INSERT INTO files (file_path, file_hash, file_size, media_type, duration, is_processed)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ("test_video.mp4", "hash1", 1024, "video", 100.0, 1))
    file_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Mock processor.process_video_scenes
    mock_processor = MagicMock()
    app.dependency_overrides[get_processor] = lambda: mock_processor
    
    with TestClient(app) as client:
        response = client.post(f"/scenes/{file_id}/detect")
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        mock_processor.process_video_scenes.assert_called_once_with(file_id)

def test_delete_scenes_endpoint(test_db, api_components):
    db, _ = test_db
    app = api_components["app"]
    
    # 1. Setup video and scenes
    conn = db._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed) VALUES (?, ?, ?, ?, ?)", ("v1.mp4", "h1", 1, "video", 1))
    fid = c.lastrowid
    
    # Insert a scene with a fake FAISS mapping
    c.execute("INSERT INTO vector_mapping (entity_type, entity_id) VALUES (?, ?)", ("scene", 1))
    faiss_id = c.lastrowid
    c.execute("INSERT INTO video_scenes (file_id, start_time, end_time, scene_index, clip_vector_id) VALUES (?, ?, ?, ?, ?)", (fid, 0, 10, 0, faiss_id))
    conn.commit()
    conn.close()
    
    # Mock FAISS remove_ids
    db.clip_index = MagicMock()
    
    with TestClient(app) as client:
        response = client.delete(f"/scenes/{fid}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        
        # Verify DB is clean
        conn = db._connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM video_scenes WHERE file_id = ?", (fid,))
        assert c.fetchone()[0] == 0
        c.execute("SELECT COUNT(*) FROM vector_mapping WHERE faiss_id = ?", (faiss_id,))
        assert c.fetchone()[0] == 0
        conn.close()

def test_scene_search_endpoint(test_db, api_components):
    db, _ = test_db
    app = api_components["app"]
    
    # Mock db.search_scenes
    db.search_scenes = MagicMock(return_value=[
        {
            'scene_id': 1, 'file_id': 10, 'file_path': 'vid.mp4',
            'scene_index': 2, 'start_time': 5.0, 'end_time': 10.0,
            'thumbnail_path': 't.jpg', 'caption': 'test scene',
            'tags': '["nature"]', 'character_tags': '[]', 'series_tags': '[]',
            'score': 0.85, 'faiss_id': 100
        }
    ])
    
    with TestClient(app) as client:
        response = client.get("/scenes/search", params={"query": "forest", "top_k": 1})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["caption"] == "test scene"
        assert "nature" in data[0]["tags"]

def test_db_manager_new_columns(test_db, api_components):
    db, _ = test_db
    MediaItem = api_components["MediaItem"]
    VideoSceneData = api_components["VideoSceneData"]
    ProcessingResult = api_components["ProcessingResult"]
    
    # Verify add_result populates new columns
    item = MediaItem("v2.mp4", "h2", 100, "video", 1, 1)
    scene = VideoSceneData(
        start_time=0.0, end_time=5.0, scene_index=1, 
        thumbnail_path="thumb.jpg", start_frame=0, end_frame=150,
        caption="test cap", tags=["tag1"], clip_vector=[0.1]*768
    )
    res = ProcessingResult("v2.mp4", True, item, scenes=[scene])
    
    db.add_result(res)
    
    conn = db._connect()
    conn.row_factory = sqlite3.Row # Use Row for easier access
    c = conn.cursor()
    c.execute("SELECT * FROM video_scenes WHERE file_id = (SELECT id FROM files WHERE file_path = 'v2.mp4')")
    row = c.fetchone()
    
    if not row:
        conn.close()
        pytest.fail("No scene found in DB")
        
    row_dict = dict(row)
    print(f"DEBUG: Row keys: {list(row_dict.keys())}")
    
    assert "scene_index" in row_dict, f"scene_index missing. Keys: {list(row_dict.keys())}"
    assert row_dict["scene_index"] == 1
    assert row_dict["thumbnail_path"] == "thumb.jpg"
    assert row_dict["start_frame"] == 0
    assert row_dict["end_frame"] == 150
    assert row_dict["caption"] == "test cap"
    assert "tag1" in row_dict["tags"]
    assert row_dict["clip_vector_id"] is not None
    conn.close()

def test_detect_scenes_not_found(test_db, api_components):
    app = api_components["app"]
    with TestClient(app) as client:
        response = client.post("/scenes/99999/detect")
        assert response.status_code == 404

def test_detect_scenes_not_video(test_db, api_components):
    db, _ = test_db
    app = api_components["app"]
    conn = db._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, media_type) VALUES (?, ?)", ("img.jpg", "image"))
    fid = c.lastrowid
    conn.commit()
    conn.close()
    
    with TestClient(app) as client:
        response = client.post(f"/scenes/{fid}/detect")
        assert response.status_code == 422

def test_detect_scenes_duration_limit(test_db, api_components):
    db, _ = test_db
    app = api_components["app"]
    conn = db._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, media_type, duration) VALUES (?, ?, ?)", ("long.mp4", "video", 8000))
    fid = c.lastrowid
    conn.commit()
    conn.close()
    
    with TestClient(app) as client:
        response = client.post(f"/scenes/{fid}/detect")
        assert response.status_code == 422
        assert "exceeds maximum duration" in response.json()["detail"]

def test_detect_scenes_force_override(test_db, api_components):
    db, _ = test_db
    app = api_components["app"]
    conn = db._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, media_type, duration) VALUES (?, ?, ?)", ("long_force.mp4", "video", 8000))
    fid = c.lastrowid
    conn.commit()
    conn.close()
    
    with TestClient(app) as client:
        response = client.post(f"/scenes/{fid}/detect", json={"force": True})
        assert response.status_code == 200
        assert response.json()["status"] == "processing"

def test_get_scenes_empty(test_db, api_components):
    db, _ = test_db
    app = api_components["app"]
    conn = db._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, media_type) VALUES (?, ?)", ("empty.mp4", "video"))
    fid = c.lastrowid
    conn.commit()
    conn.close()
    
    with TestClient(app) as client:
        response = client.get(f"/media/{fid}/scenes")
        # Ensure media prefix is handled correctly (media router)
        assert response.status_code == 200
        assert response.json() == []

def test_delete_scenes_cleans_thumbnails(test_db, tmp_path, api_components):
    db, _ = test_db
    app = api_components["app"]
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    t1 = thumb_dir / "t1.jpg"
    t1.write_text("fake image")
    t1_path = str(t1)
    
    conn = db._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, media_type) VALUES (?, ?)", ("v_thumb.mp4", "video"))
    fid = c.lastrowid
    c.execute("INSERT INTO video_scenes (file_id, start_time, end_time, thumbnail_path) VALUES (?, ?, ?, ?)", (fid, 0, 5, t1_path))
    conn.commit()
    conn.close()
    
    assert os.path.exists(t1_path)
    
    with TestClient(app) as client:
        response = client.delete(f"/scenes/{fid}")
        assert response.status_code == 200
        assert not os.path.exists(t1_path)
