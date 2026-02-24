import pytest
import os
import json
import sqlite3
import numpy as np

try:
    import faiss
except Exception:
    pytest.skip("faiss not installed", allow_module_level=True)

from src.data.db_manager import DBManager
from unittest.mock import MagicMock

@pytest.fixture
def db_manager(tmp_path):
    db_dir = tmp_path / "db"
    db_manager = DBManager(db_dir=str(db_dir))
    yield db_manager
    # Teardown
    db_manager.save_indices()

def test_create_static_album(db_manager):
    album_id = db_manager.create_album("Static Album", is_dynamic=False)
    assert album_id > 0
    
    album = db_manager.get_album(album_id)
    assert album["name"] == "Static Album"
    assert album["is_dynamic"] == 0
    assert album["item_count"] == 0

def test_create_dynamic_album(db_manager):
    query_json = json.dumps({"query": "mountain", "filters": {"media_type": "image"}})
    album_id = db_manager.create_album("Dynamic Album", is_dynamic=True, query_json=query_json)
    assert album_id > 0
    
    album = db_manager.get_album(album_id)
    assert album["name"] == "Dynamic Album"
    assert album["is_dynamic"] == 1
    assert album["query_json"] == query_json

def test_add_remove_items_static(db_manager):
    # Setup: Create file and album
    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, is_processed) VALUES (?, ?)", ("test1.jpg", 1))
    file_id = c.lastrowid
    conn.commit()
    conn.close()

    album_id = db_manager.create_album("Static", is_dynamic=False)
    
    # Add item
    db_manager.add_to_album(album_id, [file_id])
    media = db_manager.get_album_media(album_id)
    assert len(media) == 1
    assert media[0]["id"] == file_id
    
    album = db_manager.get_album(album_id)
    assert album["item_count"] == 1

    # Remove item
    db_manager.remove_from_album(album_id, [file_id])
    media = db_manager.get_album_media(album_id)
    assert len(media) == 0
    
    album = db_manager.get_album(album_id)
    assert album["item_count"] == 0

def test_dynamic_album_results(db_manager):
    # Mock AI Engine
    ai_engine = MagicMock()
    # CLIP dimension is 768 as seen in db_manager.py
    ai_engine.extract_clip_text_feature.return_value = np.zeros(768, dtype='float32')
    
    # Setup dynamic album
    query_json = json.dumps({"query": "test", "top_k": 10})
    album_id = db_manager.create_album("Dynamic", is_dynamic=True, query_json=query_json)
    
    # Call get_album_media
    # This will call hybrid_search internally
    # Since DB is empty, should return empty list but call ai_engine
    media = db_manager.get_album_media(album_id, ai_engine=ai_engine)
    
    assert isinstance(media, list)
    ai_engine.extract_clip_text_feature.assert_called_once_with("test")

def test_delete_album(db_manager):
    album_id = db_manager.create_album("To Delete", is_dynamic=False)
    assert db_manager.delete_album(album_id) is True
    assert db_manager.get_album(album_id) is None

def test_update_album(db_manager):
    album_id = db_manager.create_album("Old Name", is_dynamic=False)
    db_manager.update_album(album_id, name="New Name")
    
    album = db_manager.get_album(album_id)
    assert album["name"] == "New Name"
