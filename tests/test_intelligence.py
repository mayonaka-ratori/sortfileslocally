import os
import sys
import shutil
import pytest
from unittest.mock import MagicMock, patch

# Skip if requested in CI
if os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("Skipping intelligence tests in CI", allow_module_level=True)

@pytest.fixture
def intel_components():
    import numpy as np
    try:
        import faiss
    except ImportError:
        faiss = MagicMock()
    from PIL import Image
    
    # Internal core modules
    from src.core.ai_models import AIEngine
    from src.core.intelligence import AutoTagger, FaceClusterer
    from src.data.db_manager import DBManager
    from src.data.schemas import MediaItem, ProcessingResult, VectorData, FaceData
    
    return {
        "np": np,
        "faiss": faiss,
        "Image": Image,
        "AIEngine": AIEngine,
        "AutoTagger": AutoTagger,
        "FaceClusterer": FaceClusterer,
        "DBManager": DBManager,
        "MediaItem": MediaItem,
        "ProcessingResult": ProcessingResult,
        "VectorData": VectorData,
        "FaceData": FaceData
    }

@pytest.mark.ai_models
def test_auto_tagger(intel_components):
    AIEngine = intel_components["AIEngine"]
    AutoTagger = intel_components["AutoTagger"]
    np = intel_components["np"]
    
    # 1. Init Engine
    engine = AIEngine()
    tagger = AutoTagger(engine)
    
    # Simulate batch of 3 images (random vectors)
    vecs = np.random.rand(3, 768).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    
    tags = tagger.suggest_tags(vecs, top_k=3, threshold=-1.0) 
    
    assert len(tags) == 3
    assert len(tags[0]) == 3

@pytest.mark.ai_models
def test_face_clustering(tmp_path, intel_components):
    DBManager = intel_components["DBManager"]
    FaceClusterer = intel_components["FaceClusterer"]
    np = intel_components["np"]
    faiss = intel_components["faiss"]
    
    test_db_dir = str(tmp_path / "data" / "test_db_intel")
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
    
    db = DBManager(test_db_dir)
    clusterer = FaceClusterer(db)
    
    # 0 faces
    n = clusterer.run_clustering()
    assert n == 0
    
    # Add dummy faces
    vec_A = np.random.randn(512).astype(np.float32)
    vec_A /= np.linalg.norm(vec_A)
    
    vec_B = np.random.randn(512).astype(np.float32)
    vec_B /= np.linalg.norm(vec_B)
    # Ensure distinct
    if np.dot(vec_A, vec_B) > 0.8:
        vec_B = -vec_B
        
    faces = []
    for i in range(5):
        v = vec_A + np.random.normal(0, 0.005, 512)
        v /= np.linalg.norm(v)
        faces.append(v)
        
    for i in range(5):
        v = vec_B + np.random.normal(0, 0.005, 512)
        v /= np.linalg.norm(v)
        faces.append(v)
        
    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path) VALUES ('dummy_file')")
    fid = c.lastrowid
    
    for i, fvec in enumerate(faces):
        c.execute("INSERT INTO faces (file_id, face_index) VALUES (?, ?)", (fid, i))
        row_id = c.lastrowid
        
        fvec = fvec.astype(np.float32)
        faiss.normalize_L2(fvec[np.newaxis, :])
        db.face_index.add_with_ids(fvec[np.newaxis, :], np.array([row_id], dtype='int64'))
        
    conn.commit()
    conn.close()
    
    n_clusters = clusterer.run_clustering(eps=0.8, min_samples=2)
    assert n_clusters == 2
