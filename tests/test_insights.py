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
import json

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db(request):
    test_name = request.node.name
    db_dir = f"data/test_{test_name}"
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)
    os.makedirs(db_dir, exist_ok=True)
    
    manager = DBManager(db_dir=db_dir)
    yield manager
    
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)

def test_empty_library_insights(db):
    insights = db.get_insights()
    # Should be empty except for maybe things that don't depend on file count > 0 if any
    # Current implementation: all insights require count > 0 or > 10 etc.
    assert len(insights) == 0

def test_untagged_files_insight(db):
    conn = db._connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("untagged.jpg", "h1", 100, "image", 1, "[]"))
    conn.commit()
    conn.close()
    
    insights = db.get_insights()
    untagged = [i for i in insights if i["type"] == "untagged_files"]
    assert len(untagged) == 1
    assert untagged[0]["count"] == 1
    assert untagged[0]["priority"] == "medium"

def test_untagged_files_high_priority(db):
    conn = db._connect()
    c = conn.cursor()
    for i in range(51):
        c.execute("""
            INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"untagged_{i}.jpg", f"h{i}", 100, "image", 1, "[]"))
    conn.commit()
    conn.close()
    
    insights = db.get_insights()
    untagged = [i for i in insights if i["type"] == "untagged_files"]
    assert untagged[0]["count"] == 51
    assert untagged[0]["priority"] == "high"

def test_album_suggestion_insight(db):
    conn = db._connect()
    c = conn.cursor()
    # 20 files with tag "nature"
    for i in range(20):
        c.execute("""
            INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"nature_{i}.jpg", f"hn{i}", 100, "image", 1, '["nature"]'))
    conn.commit()
    conn.close()
    
    insights = db.get_insights()
    suggestions = [i for i in insights if i["type"] == "album_suggestion"]
    assert len(suggestions) == 1
    assert suggestions[0]["tag"] == "nature"
    assert "query_json" in suggestions[0]

def test_album_suggestion_already_exists(db):
    conn = db._connect()
    c = conn.cursor()
    # 20 files with tag "nature"
    for i in range(20):
        c.execute("""
            INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"nature_{i}.jpg", f"hn{i}", 100, "image", 1, '["nature"]'))
    # Existing album named "nature"
    c.execute("INSERT INTO albums (name, is_dynamic) VALUES (?, ?)", ("Nature", 1))
    conn.commit()
    conn.close()
    
    insights = db.get_insights()
    suggestions = [i for i in insights if i["type"] == "album_suggestion"]
    # Should not suggest nature because album exists (case-insensitive check in DBManager)
    assert len(suggestions) == 0

def test_low_quality_tags_insight(db):
    conn = db._connect()
    c = conn.cursor()
    # 11 files with only 1 tag
    for i in range(11):
        c.execute("""
            INSERT INTO files (file_path, file_hash, file_size, media_type, is_processed, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"sparse_{i}.jpg", f"hs{i}", 100, "image", 1, '["one"]'))
    conn.commit()
    conn.close()
    
    insights = db.get_insights()
    low_qual = [i for i in insights if i["type"] == "low_quality_tags"]
    assert len(low_qual) == 1
    assert low_qual[0]["count"] == 11

def test_api_insights_endpoint(client, db):
    from server.dependencies import get_db_manager
    app.dependency_overrides[get_db_manager] = lambda: db
    
    response = client.get("/insights")
    assert response.status_code == 200
    data = response.json()
    assert "insights" in data
    assert "generated_at" in data
    
    app.dependency_overrides.clear()
