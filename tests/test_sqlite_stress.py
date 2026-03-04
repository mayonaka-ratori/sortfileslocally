import tempfile
import shutil
import pytest
import sqlite3
import threading
import numpy as np
import os
import time

from src.data.db_manager import DBManager
from src.data.schemas import MediaItem, VectorData, ProcessingResult

@pytest.fixture
def db_manager():
    """Create a DBManager in an isolated temporary directory."""
    temp_dir = tempfile.mkdtemp()
    db = DBManager(db_dir=temp_dir)
    yield db
    
    # Give threads a tiny moment to fully detach if any are lingering
    time.sleep(0.1)
    
    # Force close any lingering connections inside the manager's state
    # DBManager creates a new connection per query, but just in case:
    # Safely acquire lock during cleanup
    with db._faiss_lock:
        pass 
        
    # Attempt to remove directory (Windows might hold file locks if a connection leaked)
    shutil.rmtree(temp_dir, ignore_errors=True)

def _make_dummy_result(file_path: str, file_hash: str) -> ProcessingResult:
    """Helper to create a minimal ProcessingResult for testing."""
    item = MediaItem(
        file_path=file_path,
        file_hash=file_hash,
        file_size=1024,
        media_type='image',
        created_at=1000.0,
        modified_at=1000.0,
        is_processed=True
    )
    # 768-dim normalized random vector
    vec = np.random.rand(768).astype('float32')
    vec = vec / np.linalg.norm(vec)
    
    vector_data = VectorData(
        clip_vector=vec.tolist(),
        face_vectors=[]
    )
    
    return ProcessingResult(
        file_path=file_path,
        success=True,
        media_item=item,
        vector_data=vector_data,
        faces=[],
        scenes=[]
    )

@pytest.mark.slow
def test_concurrent_writes_no_busy_error(db_manager):
    """
    8スレッドがそれぞれ50件のユニークなレコードを同時に追加するテスト。
    SQLITE_BUSY エラーが発生せず、全400件が正しく保存されることを検証。
    """
    num_threads = 8
    writes_per_thread = 50
    exceptions = []

    def writer_worker(thread_id):
        try:
            for i in range(writes_per_thread):
                file_path = f"/fake/path/{thread_id}_{i}.jpg"
                file_hash = f"hash_{thread_id}_{i}"
                res = _make_dummy_result(file_path, file_hash)
                db_manager.add_result(res)
        except Exception as e:
            exceptions.append(e)

    threads = []
    for t_id in range(num_threads):
        t = threading.Thread(target=writer_worker, args=(t_id,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # SQLITE_BUSYやその他の例外が起きていないことを確認
    assert len(exceptions) == 0, f"Exceptions occurred during concurrent writes: {exceptions}"

    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM files")
    count = c.fetchone()[0]
    conn.close()

    assert count == num_threads * writes_per_thread

@pytest.mark.slow
def test_concurrent_read_write(db_manager):
    """
    100件の初期データがある状態で、4つの書き込みスレッドと4つの読み取りスレッドを同時に実行。
    読み込みと書き込みが干渉（ロック競合）せずに成功することを検証。
    """
    # 事前準備: 100件のデータを挿入
    initial_results = []
    for i in range(100):
        initial_results.append(_make_dummy_result(f"/init/{i}.jpg", f"hash_{i}"))
    db_manager.add_results_batch(initial_results)

    num_writers = 4
    num_readers = 4
    writes_per_thread = 25
    exceptions = []

    def writer_worker(thread_id):
        try:
            for i in range(writes_per_thread):
                file_path = f"/write/{thread_id}_{i}.jpg"
                file_hash = f"whash_{thread_id}_{i}"
                res = _make_dummy_result(file_path, file_hash)
                db_manager.add_result(res)
        except Exception as e:
            exceptions.append(e)

    def reader_worker():
        try:
            # 各リーダスレッドは50回の検索を実行
            for _ in range(50):
                query_vec = np.random.rand(768).astype('float32')
                results = db_manager.search_similar_images(query_vec, top_k=5)
                assert isinstance(results, list)
        except Exception as e:
            exceptions.append(e)

    threads = []
    # 書き込みスレッド開始
    for i in range(num_writers):
        t = threading.Thread(target=writer_worker, args=(i,))
        threads.append(t)
        t.start()
        
    # 読み取りスレッド開始
    for i in range(num_readers):
        t = threading.Thread(target=reader_worker)
        threads.append(t)
        t.start()

    # 全スレッドの終了を待機
    for t in threads:
        t.join()

    assert len(exceptions) == 0, f"Exceptions during read/write: {exceptions}"
    
    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM files")
    count = c.fetchone()[0]
    conn.close()

    # 初期100件 + (4スレッド × 25件) = 200件
    assert count == 100 + (num_writers * writes_per_thread)

@pytest.mark.slow
def test_concurrent_batch_writes(db_manager):
    """
    4スレッドがそれぞれ100件のバッチ挿入(add_results_batch)を同時に実行。
    全400件が正しく保存され、ファイルハッシュの一意性が保たれているか（データ破損の有無）を検証。
    """
    num_threads = 4
    batch_size = 100
    exceptions = []

    def batch_worker(thread_id):
        try:
            batch = []
            for i in range(batch_size):
                file_path = f"/batch/{thread_id}_{i}.jpg"
                file_hash = f"bhash_{thread_id}_{i}"
                batch.append(_make_dummy_result(file_path, file_hash))
            db_manager.add_results_batch(batch)
        except Exception as e:
            exceptions.append(e)

    threads = []
    for t_id in range(num_threads):
        t = threading.Thread(target=batch_worker, args=(t_id,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(exceptions) == 0, f"Exceptions during batch writes: {exceptions}"

    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM files")
    count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT file_hash) FROM files")
    unique_hashes = c.fetchone()[0]
    conn.close()

    assert count == num_threads * batch_size
    assert count == unique_hashes

def test_wal_mode_active(db_manager):
    """
    DBManagerの接続がWAL(Write-Ahead Logging)モードで動作していることを検証。
    """
    conn = db_manager._connect()
    c = conn.cursor()
    c.execute("PRAGMA journal_mode")
    mode = c.fetchone()[0]
    conn.close()
    
    assert mode.lower() == 'wal'
