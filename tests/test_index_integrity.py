import pytest
import os
import shutil
import numpy as np
import faiss

from src.data.db_manager import DBManager
from src.data.schemas import MediaItem, VectorData, ProcessingResult

@pytest.fixture
def temp_db_dir(tmp_path):
    db_dir = os.path.join(tmp_path, "db")
    yield db_dir
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)

@pytest.fixture
def db_manager(temp_db_dir):
    manager = DBManager(db_dir=temp_db_dir)
    yield manager

def create_dummy_result(file_path: str, success: bool = True) -> ProcessingResult:
    item = MediaItem(
        file_path=file_path,
        file_hash=f"hash_{file_path}",
        file_size=1024,
        media_type="image",
        created_at=0.0,
        modified_at=0.0,
        width=800,
        height=600,
        duration=0.0
    )
    vec = VectorData(
        clip_vector=np.random.rand(768).astype('float32').tolist(),
        face_vectors=[]
    )
    return ProcessingResult(
        file_path=file_path,
        success=success,
        media_item=item,
        vector_data=vec,
        faces=[],
        scenes=[]
    )

def test_clean_state(db_manager):
    # Add one item
    res = create_dummy_result("test1.jpg")
    db_manager.add_result(res)
    
    # Run integrity verify
    db_manager.verify_index_integrity()
    
    # Fetch counts
    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM vector_mapping")
    sqlite_count = c.fetchone()[0]
    conn.close()
    
    faiss_count = db_manager.clip_index.ntotal
    assert sqlite_count == 1
    assert faiss_count == 1

def test_orphan_vectors(db_manager):
    # Add one item
    res = create_dummy_result("test_orphan.jpg")
    db_manager.add_result(res)
    
    # Verify pre-condition
    assert db_manager.clip_index.ntotal == 1
    
    # 1. Create an orphan by deleting from SQLite vector_mapping
    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("DELETE FROM vector_mapping")
    conn.commit()
    conn.close()
    
    # 2. Run integrity verify
    db_manager.verify_index_integrity()
    
    # 3. Verify post-condition (FAISS vector should be removed)
    assert db_manager.clip_index.ntotal == 0

def test_dangling_refs(db_manager):
    # Add one item
    res = create_dummy_result("test_dangling.jpg")
    db_manager.add_result(res)
    
    # 1. Create a dangling ref by removing from FAISS
    # We find the faiss id first
    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("SELECT faiss_id, entity_id FROM vector_mapping LIMIT 1")
    row = c.fetchone()
    faiss_id = row[0]
    file_id = row[1]
    
    # Check pre-condition: is_processed is 1
    c.execute("SELECT is_processed FROM files WHERE id = ?", (file_id,))
    assert c.fetchone()[0] == 1
    conn.close()
    
    with db_manager._faiss_lock:
        db_manager.clip_index.remove_ids(np.array([faiss_id], dtype='int64'))
        
    assert db_manager.clip_index.ntotal == 0
    
    # 2. Run integrity verify
    db_manager.verify_index_integrity()
    
    # 3. Verify post-condition (SQLite mapping should be removed, is_processed should be 0)
    conn = db_manager._connect()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM vector_mapping")
    assert c.fetchone()[0] == 0
    
    c.execute("SELECT is_processed FROM files WHERE id = ?", (file_id,))
    assert c.fetchone()[0] == 0
    
    conn.close()
