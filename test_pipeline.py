
import os
import sys
import shutil

# Add src to path
sys.path.append(os.path.abspath("src"))

from src.core.processor import Processor
from src.data.db_manager import DBManager

def create_dummy_data():
    """Create a folder with some dummy files for testing."""
    test_dir = "data/inputs_test"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 1. Create a text file (should be ignored)
    with open(os.path.join(test_dir, "ignore.txt"), "w") as f:
        f.write("ignore me")
        
    # 2. Create dummy images (Noise)
    import numpy as np
    from PIL import Image
    
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

def test_pipeline():
    print("=== Starting Phase 3 Pipeline Test ===")
    
    # Setup
    input_dir = create_dummy_data()
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
        conn = db_mgr._init_sqlite() # Re-connect manually or check via new method
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
            
    except Exception as e:
        print(f"❌ Pipeline Failed with Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline()
