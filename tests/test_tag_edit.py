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
    db_path = f"{db_dir}/media_curator.db"
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)
    os.makedirs(db_dir, exist_ok=True)
    
    manager = DBManager(db_dir=db_dir)
    
    # Insert a test file with all necessary fields to satisfy constraints
    conn = manager._connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags, character_tags, series_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("test_file.jpg", "hash123", 1024, "image", 1, '["old_tag"]', '[]', '[]'))
    conn.commit()
    conn.close()
    
    yield manager
    
    # Cleanup
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)

def test_add_tags(db):
    updated = db.add_tags(1, ["new_tag1", "new_tag2"], "general")
    assert "old_tag" in updated
    assert "new_tag1" in updated
    assert "new_tag2" in updated
    assert len(updated) == 3

def test_add_duplicate_tag(db):
    updated = db.add_tags(1, ["old_tag", "NEW_TAG"], "general")
    # "old_tag" already exists, so it shouldn't be added again.
    # "NEW_TAG" is new (case-insensitive check).
    assert len(updated) == 2
    assert "old_tag" in updated
    assert "NEW_TAG" in updated
    
    # Add same tag again with different case
    updated2 = db.add_tags(1, ["new_tag"], "general")
    assert len(updated2) == 2 # "NEW_TAG" matches "new_tag"

def test_remove_tag(db):
    db.add_tags(1, ["tag_to_remove"], "general")
    updated = db.remove_tags(1, ["tag_to_remove"], "general")
    assert "tag_to_remove" not in updated
    assert "old_tag" in updated

def test_remove_nonexistent_tag(db):
    current = db.add_tags(1, [], "general")
    updated = db.remove_tags(1, ["nonexistent"], "general")
    assert updated == current

def test_suggest_tags(db):
    db.add_tags(1, ["landscape", "lantern"], "general")
    
    # Add another file with landscape to test count
    conn = db._connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("test2.jpg", "hash456", 2048, "image", 1, '["landscape"]'))
    conn.commit()
    conn.close()
    
    suggestions = db.suggest_tags("lan", "general")
    assert len(suggestions) >= 2
    # "landscape" should be first as it has 2 count, "lantern" has 1
    # Check by searching for the tag name in suggestions
    s_map = {s["tag"]: s["count"] for s in suggestions}
    assert s_map["landscape"] == 2
    assert s_map["lantern"] == 1
    assert suggestions[0]["count"] == 2 # Top one should have count 2

def test_category_separation(db):
    db.add_tags(1, ["char1"], "character")
    
    general = db.add_tags(1, [], "general")
    characters = db.add_tags(1, [], "character")
    
    assert "char1" in characters
    assert "char1" not in general

def test_invalid_file_id(db):
    with pytest.raises(ValueError):
        db.add_tags(999, ["tag"], "general")

# Integration tests for FastAPI endpoints

def test_api_add_tags(client, db, api_components):
    app = api_components["app"]
    get_db_manager = api_components["get_db_manager"]
    app.dependency_overrides[get_db_manager] = lambda: db
    response = client.post("/media/1/tags", json={"tags": ["api_tag"], "category": "general"})
    assert response.status_code == 200
    data = response.json()
    assert "api_tag" in data["tags"]
    app.dependency_overrides.clear()

def test_api_suggest_tags(client, db, api_components):
    app = api_components["app"]
    get_db_manager = api_components["get_db_manager"]
    app.dependency_overrides[get_db_manager] = lambda: db
    db.add_tags(1, ["apple", "apricot"], "general")
    response = client.get("/gallery/tags/suggest?q=ap")
    assert response.status_code == 200
    data = response.json()
    assert any(s["tag"] == "apple" for s in data)
    assert any(s["tag"] == "apricot" for s in data)
    app.dependency_overrides.clear()

def test_api_404(client, db, api_components):
    app = api_components["app"]
    get_db_manager = api_components["get_db_manager"]
    app.dependency_overrides[get_db_manager] = lambda: db
    response = client.post("/media/999/tags", json={"tags": ["tag"], "category": "general"})
    assert response.status_code == 404
    app.dependency_overrides.clear()
