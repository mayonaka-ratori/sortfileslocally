import sys
import os
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.getcwd())

# Mock AI and system modules only if missing
for mod in [
    "open_clip", "decord", "facenet_pytorch", "insightface", 
    "onnxruntime", "cv2", "sklearn", "sklearn.cluster"
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Mock internal components that would pull in heavy AI dependencies
sys.modules["src.core.ai_models"] = MagicMock()
sys.modules["src.core.vlm_engine"] = MagicMock()
sys.modules["src.core.inference"] = MagicMock()
sys.modules["src.core.video_processor"] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from server.main import app
from src.data.db_manager import DBManager
from server.dependencies import get_db_manager, get_processor

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db(request):
    test_name = request.node.name
    db_dir = f"data/test_rescan_{test_name}"
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)
    os.makedirs(db_dir, exist_ok=True)
    
    manager = DBManager(db_dir=db_dir)
    
    # Insert test files
    conn = manager._connect()
    c = conn.cursor()
    for i in range(1, 11):
        c.execute("""
            INSERT INTO files (id, file_path, file_hash, file_size, media_type, is_processed, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (i, f"test_{i}.jpg", f"hash{i}", 1024, "image", 1, '["existing_tag"]'))
    conn.commit()
    conn.close()
    
    yield manager
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)

@pytest.fixture
def mock_processor():
    proc = MagicMock()
    # Mock scanner.inspect_file
    proc.scanner.inspect_file.return_value = MagicMock()
    # Mock _process_item
    item_mock = MagicMock()
    item_mock.tags = ["ai_tag"]
    item_mock.character_tags = []
    item_mock.series_tags = []
    item_mock.caption = "ai caption"
    item_mock.error_msg = None
    
    result_mock = MagicMock()
    result_mock.success = True
    result_mock.media_item = item_mock
    
    proc._process_item.return_value = result_mock
    return proc

def test_single_rescan(client, db, mock_processor):
    app.dependency_overrides[get_db_manager] = lambda: db
    app.dependency_overrides[get_processor] = lambda: mock_processor
    
    payload = {"mode": "append"}
    response = client.post("/media/1/rescan", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["file_id"] == 1
    
    app.dependency_overrides.clear()

def test_bulk_rescan(client, db, mock_processor):
    app.dependency_overrides[get_db_manager] = lambda: db
    app.dependency_overrides[get_processor] = lambda: mock_processor
    
    payload = {
        "file_ids": [1, 2, 3],
        "mode": "append"
    }
    response = client.post("/media/bulk-rescan", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    assert data["file_count"] == 3
    
    app.dependency_overrides.clear()

def test_bulk_rescan_limit(client, db, mock_processor):
    app.dependency_overrides[get_db_manager] = lambda: db
    app.dependency_overrides[get_processor] = lambda: mock_processor
    
    # Generate 51 IDs
    file_ids = list(range(1, 52))
    payload = {
        "file_ids": file_ids,
        "mode": "append"
    }
    response = client.post("/media/bulk-rescan", json=payload)
    
    assert response.status_code == 422
    assert "Maximum 50 files" in response.json()["detail"]
    
    app.dependency_overrides.clear()

def test_rescan_invalid_file(client, db, mock_processor):
    app.dependency_overrides[get_db_manager] = lambda: db
    app.dependency_overrides[get_processor] = lambda: mock_processor
    
    payload = {"mode": "append"}
    response = client.post("/media/999/rescan", json=payload)
    
    assert response.status_code == 404
    
    app.dependency_overrides.clear()
