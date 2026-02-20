
import os
import sys
import shutil
import numpy as np
import faiss
from PIL import Image

sys.path.append(os.path.abspath("src"))

from src.core.ai_models import AIEngine
from src.core.intelligence import AutoTagger, FaceClusterer
from src.data.db_manager import DBManager
from src.data.schemas import MediaItem, ProcessingResult, VectorData, FaceData

def test_auto_tagger():
    print("=== Testing AutoTagger ===")
    
    # 1. Init Engine
    engine = AIEngine()
    tagger = AutoTagger(engine)
    
    # 2. Create Dummy Images (One noise, one black, one white)
    # CLIP features for noise might be random.
    # Let's try to simulate a known distribution? Hard without real images.
    # Just check if it returns tags formatted correctly.
    
    print("Generating dummy features...")
    # Simulate batch of 3 images (random vectors)
    # Vectors must be normalized for dot product to be cosine sim
    vecs = np.random.rand(3, 768).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    
    tags = tagger.suggest_tags(vecs, top_k=3, threshold=-1.0) # threshold -1 to force output
    
    print(f"Tags output: {tags}")
    assert len(tags) == 3
    assert len(tags[0]) == 3
    print("AutoTagger Test Passed!")

def test_face_clustering():
    print("\n=== Testing FaceClusterer ===")
    
    test_db_dir = "data/test_db_intel"
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
    
    db = DBManager(test_db_dir)
    clusterer = FaceClusterer(db)
    
    # 0 faces
    n = clusterer.run_clustering()
    assert n == 0
    print("Empty clustering OK.")
    
    # Add dummy faces
    # Create 2 clusters: 0..4 (Cluster A), 5..9 (Cluster B)
    # Vectors[0-4] close to each other, [5-9] close to each other, far from A.
    
    print("Injecting dummy faces...")
    vec_A = np.random.randn(512).astype(np.float32)
    vec_A /= np.linalg.norm(vec_A)
    
    vec_B = np.random.randn(512).astype(np.float32)
    vec_B /= np.linalg.norm(vec_B)
    # Ensure distinct
    if np.dot(vec_A, vec_B) > 0.8:
        vec_B = -vec_B
        
    faces = []
    
    # Cluster A members (perturbation)
    for i in range(5):
        v = vec_A + np.random.normal(0, 0.005, 512)
        v /= np.linalg.norm(v)
        faces.append(v)
        
    # Cluster B members
    for i in range(5):
        v = vec_B + np.random.normal(0, 0.005, 512)
        v /= np.linalg.norm(v)
        faces.append(v)
        
    # Manual Insert
    fake_item = MediaItem("dummy", "hash", 0, "image", 0, 0)
    fake_vec = VectorData([], [])
    fake_res = ProcessingResult("dummy", True, fake_item, fake_vec, [])
    
    # We cheat and use internal FAISS add directly to simulate data
    # But need DB rows.
    # Insert 10 dummy files to satisfy FK? faces table refs files(id).
    import sqlite3
    conn = sqlite3.connect(db.sqlite_path)
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path) VALUES ('dummy_file')")
    fid = c.lastrowid
    
    # Insert faces
    for i, fvec in enumerate(faces):
        c.execute("INSERT INTO faces (file_id, face_index) VALUES (?, ?)", (fid, i))
        row_id = c.lastrowid
        
        # Add to FAISS
        fvec = fvec.astype(np.float32)
        faiss.normalize_L2(fvec[np.newaxis, :])
        db.face_index.add_with_ids(fvec[np.newaxis, :], np.array([row_id], dtype='int64'))
        
    conn.commit()
    conn.close()
    
    # Run Clustering
    print("Running DBSCAN...")
    n_clusters = clusterer.run_clustering(eps=0.8, min_samples=2)
    print(f"Clusters found: {n_clusters}")
    
    assert n_clusters == 2
    print("FaceClusterer Test Passed!")

if __name__ == "__main__":
    test_auto_tagger()
    test_face_clustering()
