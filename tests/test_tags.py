import os
import json
import sqlite3
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
def client(api_components):
    TestClient = api_components["TestClient"]
    app = api_components["app"]
    return TestClient(app)

@pytest.fixture
def db(request, api_components):
    DBManager = api_components["DBManager"]
    # Use a unique database per test to avoid interference
    test_name = request.node.name
    db_dir = f"data/test_{test_name}"
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)
    os.makedirs(db_dir, exist_ok=True)
    
    manager = DBManager(db_dir=db_dir)
    
    # Insert some test data
    conn = manager._connect()
    c = conn.cursor()
    # 1. Tagged image
    c.execute("""
        INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags, character_tags, series_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("tagged.jpg", "h1", 1024, "image", 1, '["landscape", "night"]', '["Airi"]', '["Original"]'))
    # 2. Another tagged image
    c.execute("""
        INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags, character_tags, series_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("tagged2.jpg", "h2", 1024, "image", 1, '["landscape"]', '[]', '["Original"]'))
    # 3. Untagged image
    c.execute("""
        INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags, character_tags, series_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("untagged.jpg", "h3", 1024, "image", 1, '[]', '[]', '[]'))
    # 4. Another untagged image (null tags)
    c.execute("""
        INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("untagged2.jpg", "h4", 1024, "image", 1, None))
    
    conn.commit()
    conn.close()
    
    yield manager
    
    # Cleanup
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)

def test_get_tag_stats(db):
    stats = db.get_tag_stats()
    # general: landscape (2), night (1)
    # character: Airi (1)
    # series: Original (2)
    # total_tags: unique (category, tag) pairs = 2 (gen) + 1 (char) + 1 (ser) = 4
    # untagged_count: files 3 and 4 = 2 (based on 'tags' column)
    
    assert stats["total_tags"] == 4
    assert stats["untagged_count"] == 2
    
    gen = {t["tag"]: t["count"] for t in stats["general"]}
    assert gen["landscape"] == 2
    assert gen["night"] == 1
    
    char = {t["tag"]: t["count"] for t in stats["character"]}
    assert char["Airi"] == 1
    
    ser = {t["tag"]: t["count"] for t in stats["series"]}
    assert ser["Original"] == 2

def test_get_untagged_files(db):
    res = db.get_untagged_files(page=1, per_page=10)
    assert res["total_count"] == 2
    paths = [f["file_path"] for f in res["files"]]
    assert "untagged.jpg" in paths
    assert "untagged2.jpg" in paths

def test_rename_tag_normal(db):
    # Rename landscape -> scenery
    res = db.rename_tag("landscape", "scenery", "general")
    assert res["renamed_count"] == 2
    assert res["merged_count"] == 0
    
    stats = db.get_tag_stats()
    gen = {t["tag"]: t["count"] for t in stats["general"]}
    assert "landscape" not in gen
    assert gen["scenery"] == 2

def test_rename_tag_merge(db):
    # Add 'scenery' to tagged.jpg first to trigger merge
    db.add_tags(1, ["scenery"], "general")
    # tagged.jpg now has ['landscape', 'night', 'scenery']
    # tagged2.jpg has ['landscape']
    
    # Rename landscape -> scenery
    res = db.rename_tag("landscape", "scenery", "general")
    # For tagged.jpg: scenery exists, so it's a merge (merged_count++)
    # For tagged2.jpg: scenery doesn't exist, so it's a rename (renamed_count++)
    
    assert res["renamed_count"] == 1
    assert res["merged_count"] == 1
    
    stats = db.get_tag_stats()
    gen = {t["tag"]: t["count"] for t in stats["general"]}
    assert "landscape" not in gen
    assert gen["scenery"] == 2

def test_rename_tag_not_found(db):
    res = db.rename_tag("nonexistent", "new", "general")
    assert res["renamed_count"] == 0
    assert res["merged_count"] == 0

def test_delete_tag(db):
    # Delete 'night'
    res = db.rename_tag("night", "", "general")
    assert res["renamed_count"] == 1
    
    stats = db.get_tag_stats()
    gen = {t["tag"]: t["count"] for t in stats["general"]}
    assert "night" not in gen

# Integration tests for FastAPI endpoints

def test_api_tag_stats(client, db, api_components):
    app = api_components["app"]
    get_db_manager = api_components["get_db_manager"]
    app.dependency_overrides[get_db_manager] = lambda: db
    response = client.get("/gallery/tags/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tags"] == 4
    app.dependency_overrides.clear()

def test_api_untagged(client, db, api_components):
    app = api_components["app"]
    get_db_manager = api_components["get_db_manager"]
    app.dependency_overrides[get_db_manager] = lambda: db
    response = client.get("/gallery/untagged")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    app.dependency_overrides.clear()

def test_api_rename(client, db, api_components):
    app = api_components["app"]
    get_db_manager = api_components["get_db_manager"]
    app.dependency_overrides[get_db_manager] = lambda: db
    response = client.post("/gallery/tags/rename", json={
        "old_tag": "landscape",
        "new_tag": "scenery",
        "category": "general"
    })
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["renamed_count"] == 2
    app.dependency_overrides.clear()
