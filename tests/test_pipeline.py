import os
import sys
import shutil
import pytest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath("src"))

# Skip if requested in CI or missing deps
def is_ai_deps_missing():
    try:
        import torch
        import open_clip
        return False
    except ImportError:
        return True

if os.environ.get("SKIP_GPU_TESTS") == "1" or is_ai_deps_missing():
    pytest.skip("Skipping pipeline tests (GPU omit or missing AI deps)", allow_module_level=True)

@pytest.fixture
def pipe_components():
    import numpy as np
    from PIL import Image
    from core.processor import Processor
    from data.db_manager import DBManager
    return {
        "np": np,
        "Image": Image,
        "Processor": Processor,
        "DBManager": DBManager
    }

def create_dummy_data(components):
    """Create a folder with some dummy files for testing."""
    np = components["np"]
    Image = components["Image"]
    test_dir = "data/inputs_test"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 1. Create a text file (should be ignored)
    with open(os.path.join(test_dir, "ignore.txt"), "w") as f:
        f.write("ignore me")
        
    # 2. Create dummy images (Noise)
    for i in range(3):
        # Generate random noise image
        img = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))
        img.save(os.path.join(test_dir, f"img_{i}.png"))
        
    print(f"Created dummy test data in {test_dir}")
    return test_dir

def clean_db():
    """Reset DB for testing."""
    db_dir = "data/db_test"
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)
    return db_dir

@pytest.mark.skipif(os.environ.get("SKIP_GPU_TESTS") == "1", reason="GPU not available")
@pytest.mark.ai_models
def test_pipeline_execution(pipe_components):
    Processor = pipe_components["Processor"]
    DBManager = pipe_components["DBManager"]
    print("=== Starting Phase 3 Pipeline Test ===")
    
    # Setup
    input_dir = create_dummy_data(pipe_components)
    db_dir = clean_db()
    
    try:
        # 1. Initialize Processor
        print("\n[Step 1] Initializing Processor...")
        processor = Processor(db_dir=db_dir)
        print("✅ Processor Initialized.")
        
        # 2. Run Processing
        print("\n[Step 2] Processing Folder...")
        processed_count = 0
        for status in processor.process_folder(input_dir):
            print(f"  > {status}")
            processed_count += 1
            
        print("\n[Step 3] Verifying Database...")
        db_mgr = DBManager(db_dir=db_dir)
        
        # Check SQLite
        import sqlite3
        conn = sqlite3.connect(os.path.join(db_dir, "metadata.db"))
        c = conn.cursor()
        c.execute("SELECT count(*) FROM files")
        count = c.fetchone()[0]
        c.execute("SELECT count(*) FROM files WHERE is_processed=1")
        processed = c.fetchone()[0]
        conn.close()
        
        print(f"  SQLite Total Files: {count}")
        print(f"  SQLite Processed: {processed}")
        
        # Check FAISS
        image_idx_count = db_mgr.clip_index.ntotal
        print(f"  FAISS CLIP Index Count: {image_idx_count}")
        
        if count == 3 and processed == 3 and image_idx_count == 3:
            print("✅ Pipeline Success: All 3 images processed and indexed.")
        else:
            print("❌ Pipeline Verification Failed.")
            raise ValueError("Pipeline verification failed")
            
    except Exception as e:
        print(f"❌ Pipeline Failed with Error: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_pipeline()
