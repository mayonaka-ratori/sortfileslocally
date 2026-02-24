
import os
import numpy as np
import json
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.db_manager import DBManager
from src.data.schemas import MediaItem, VectorData, ProcessingResult, VideoSceneData, FaceData

def test_db_manager_mapping():
    db_dir = os.path.join("data", "test_db")
    db = DBManager(db_dir)
    
    # 1. Create a dummy ProcessingResult for a video with a scene
    item = MediaItem(
        file_path="test_video_1.mp4",
        file_hash="hash1",
        file_size=1000,
        media_type="video",
        created_at=0.0,
        modified_at=0.0,
        duration=10.0
    )
    
    vec_data = VectorData(
        clip_vector=[0.1] * 768,
        face_vectors=[]
    )
    
    scene = VideoSceneData(
        start_time=0.0,
        end_time=5.0,
        caption="A scene",
        clip_vector=[0.25] * 768 # Use higher value to distinguish
    )
    
    result = ProcessingResult(
        file_path="test_video_1.mp4",
        success=True,
        media_item=item,
        vector_data=vec_data,
        scenes=[scene]
    )
    
    # 2. Add Result
    print("Adding result...")
    db.add_result(result)
    
    # 3. Verify Tables
    conn = db._connect()
    c = conn.cursor()
    
    c.execute("SELECT * FROM files WHERE file_path = 'test_video_1.mp4'")
    file_row = c.fetchone()
    print(f"File Row: {file_row}")
    file_id = file_row[0]
    
    c.execute("SELECT * FROM video_scenes WHERE file_id = ?", (file_id,))
    scene_row = c.fetchone()
    print(f"Scene Row: {scene_row}")
    scene_id = scene_row[0]
    
    c.execute("SELECT * FROM vector_mapping")
    mappings = c.fetchall()
    print(f"Mappings: {mappings}")
    # Expected: 2 mappings (one for file, one for scene)
    assert len(mappings) == 2
    
    # 4. Test Search
    print("Testing Search...")
    # Search with vector close to file [0.1...]
    query_vec = np.array([0.1] * 768, dtype='float32')
    # search_similar_images uses clip_index
    results = db.search_similar_images(query_vec, top_k=5)
    print(f"Search Similar Results: {results}")
    assert len(results) > 0
    assert results[0][0] == "test_video_1.mp4"
    
    # Test Hybrid Search
    print("Testing Hybrid Search...")
    h_results = db.hybrid_search(query_vec, filters={}, top_k=5)
    print(f"Hybrid Search Results: {h_results['results']}")
    assert len(h_results['results']) > 0
    
    # Test Scene Match
    query_scene_vec = np.array([0.25] * 768, dtype='float32')
    h_results_scene = db.hybrid_search(query_scene_vec, filters={}, top_k=5)
    print(f"Hybrid Search (Scene) Results: {h_results_scene['results']}")
    assert len(h_results_scene['results']) > 0
    assert 'matched_scene' in h_results_scene['results'][0]
    assert h_results_scene['results'][0]['matched_scene']['scene_id'] == scene_id
    
    print("Verification Successful!")
    conn.close()

if __name__ == "__main__":
    test_db_dir = os.path.join("data", "test_db")
    # Cleanup test DB if exists
    if os.path.exists(test_db_dir):
        import shutil
        shutil.rmtree(test_db_dir)
        
    try:
        test_db_manager_mapping()
    finally:
        # Cleanup
        if os.path.exists(test_db_dir):
            import shutil
            shutil.rmtree(test_db_dir)
