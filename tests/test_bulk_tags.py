import sys
import os
from unittest.mock import MagicMock

# Ensure project root is in path
sys.path.append(os.getcwd())

# Mock AI and system modules
for mod in ["open_clip", "decord", "PIL", "numpy", "facenet_pytorch", "insightface", "torch", "torchvision", "torchaudio", "onnxruntime", "pandas", "faiss", "cv2"]:
    sys.modules[mod] = MagicMock()

sys.modules["src.core.ai_models"] = MagicMock()
sys.modules["src.core.vlm_engine"] = MagicMock()
sys.modules["src.core.processor"] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from server.main import app
from src.data.db_manager import DBManager
from server.dependencies import get_db_manager

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db(request):
    test_name = request.node.name
    db_dir = f"data/test_bulk_{test_name}"
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)
    os.makedirs(db_dir, exist_ok=True)
    
    manager = DBManager(db_dir=db_dir)
    
    # Insert 3 test files
    conn = manager._connect()
    c = conn.cursor()
    for i in range(1, 4):
        c.execute("""
            INSERT INTO files (id, file_path, file_hash, file_size, media_type, is_processed, tags, character_tags, series_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, f"test_{i}.jpg", f"hash{i}", 1024, "image", 1, '["tagA"]', '[]', '[]'))
    conn.commit()
    conn.close()
    
    yield manager
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)

def test_bulk_add_tags(client, db):
    app.dependency_overrides[get_db_manager] = lambda: db
    payload = {
        "file_ids": [1, 2, 3],
        "action": "add",
        "tags": ["tagB", "tagC"],
        "category": "general"
    }
    response = client.post("/media/bulk-tags", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["affected_count"] == 3
    
    # Verify in DB
    for i in range(1, 4):
        tags = db.add_tags(i, [], "general")
        assert "tagA" in tags
        assert "tagB" in tags
        assert "tagC" in tags
        assert len(tags) == 3
    app.dependency_overrides.clear()

def test_bulk_remove_tags(client, db):
    app.dependency_overrides[get_db_manager] = lambda: db
    payload = {
        "file_ids": [1, 2],
        "action": "remove",
        "tags": ["tagA"],
        "category": "general"
    }
    response = client.post("/media/bulk-tags", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["affected_count"] == 2
    
    # Verify in DB
    assert len(db.add_tags(1, [], "general")) == 0
    assert len(db.add_tags(2, [], "general")) == 0
    assert "tagA" in db.add_tags(3, [], "general")
    app.dependency_overrides.clear()

def test_bulk_replace_tags(client, db):
    app.dependency_overrides[get_db_manager] = lambda: db
    payload = {
        "file_ids": [1, 2, 3],
        "action": "replace",
        "tags": ["new_tag"],
        "category": "general"
    }
    response = client.post("/media/bulk-tags", json=payload)
    assert response.status_code == 200
    
    # Verify in DB
    for i in range(1, 4):
        tags = db.add_tags(i, [], "general")
        assert tags == ["new_tag"]
    app.dependency_overrides.clear()

def test_bulk_limit_exceeded(client, db):
    app.dependency_overrides[get_db_manager] = lambda: db
    payload = {
        "file_ids": list(range(501)),
        "action": "add",
        "tags": ["tag"],
        "category": "general"
    }
    response = client.post("/media/bulk-tags", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Maximum 500 files per bulk operation"
    app.dependency_overrides.clear()

def test_bulk_mixed_results(client, db):
    app.dependency_overrides[get_db_manager] = lambda: db
    # 1 valid (ID 1), 1 invalid (ID 999)
    payload = {
        "file_ids": [1, 999],
        "action": "add",
        "tags": ["mixed_tag"],
        "category": "general"
    }
    response = client.post("/media/bulk-tags", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["affected_count"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["file_id"] == 999
    app.dependency_overrides.clear()

def test_bulk_empty_tags(client, db):
    app.dependency_overrides[get_db_manager] = lambda: db
    payload = {
        "file_ids": [1, 2],
        "action": "add",
        "tags": [],
        "category": "general"
    }
    response = client.post("/media/bulk-tags", json=payload)
    assert response.status_code == 422
    app.dependency_overrides.clear()

def test_bulk_add_tags_deduplication(client, db):
    app.dependency_overrides[get_db_manager] = lambda: db
    # Insert a file with no tags for clean test
    conn = db._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (id, file_path, tags) VALUES (10, 'dedup_test.jpg', '[]')")
    conn.commit()
    conn.close()

    payload = {
        "file_ids": [10],
        "action": "add",
        "tags": ["Apple", "apple", "APPLE"],
        "category": "general"
    }
    response = client.post("/media/bulk-tags", json=payload)
    assert response.status_code == 200
    
    # Verify in DB
    tags = db.add_tags(10, [], "general")
    assert tags == ["Apple"]
    app.dependency_overrides.clear()
