import os
import sys
import shutil
import time
import pytest
from unittest.mock import MagicMock, patch

# Skip if requested in CI
if os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("Skipping optimization tests in CI", allow_module_level=True)

@pytest.fixture
def opt_components():
    from PIL import Image
    import numpy as np
    from src.core.processor import Processor
    from src.data.db_manager import DBManager
    return {
        "Image": Image,
        "np": np,
        "Processor": Processor,
        "DBManager": DBManager
    }

def setup_benchmark_data(num_images=50, components=None):
    """Create a folder with N dummy images."""
    Image = components["Image"]
    np = components["np"]
    bench_dir = "data/bench_inputs"
    if os.path.exists(bench_dir):
        shutil.rmtree(bench_dir)
    os.makedirs(bench_dir)
    
    print(f"Generating {num_images} dummy images...")
    for i in range(num_images):
        # 640x640 random noise
        img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
        img.save(os.path.join(bench_dir, f"img_{i}.jpg"), quality=80)
        
    return bench_dir

def clean_db(suffix):
    db_dir = f"data/db_bench_{suffix}"
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)
    return db_dir

def benchmark(components):
    Processor = components["Processor"]
    DBManager = components["DBManager"]
    print("=== Starting Performance Benchmark ===")
    
    # Setup
    num_images = 32 # Match expected batch size for fair single comparison
    input_dir = setup_benchmark_data(num_images, components=components)
    
    processor = Processor() # Init once to load models (exclude model load time)
    # Force initialize models
    _ = processor.ai_engine.clip_model
    
    # --- Case 1: Sequential Processing ---
    print("\n--- Testing Sequential Processing ---")
    db_seq = clean_db("seq")
    processor.db_manager = DBManager(db_seq) # Switch DB
    
    start_time = time.time()
    for _ in processor.process_folder(input_dir, force_reprocess=True):
        pass
    seq_time = time.time() - start_time
    print(f"Sequential Time ({num_images} items): {seq_time:.2f}s")
    print(f"TPS (Transaction Per Second): {num_images/seq_time:.2f}")

    # --- Case 2: Batch Processing ---
    print("\n--- Testing Batch Processing ---")
    db_batch = clean_db("batch")
    processor.db_manager = DBManager(db_batch) # Switch DB
    
    start_time = time.time()
    for _ in processor.process_folder_batch(input_dir, force_reprocess=True, batch_size=32):
        pass
    batch_time = time.time() - start_time
    print(f"Batch Time ({num_images} items): {batch_time:.2f}s")
    print(f"TPS (Transaction Per Second): {num_images/batch_time:.2f}")
    
    # --- Conclusion ---
    if batch_time < seq_time:
        speedup = seq_time / batch_time
        print(f"\n✅ Optimization SUCCESS! Speedup: {speedup:.2f}x")
    else:
        print("\n⚠️ Optimization FAILED. Batch processing was slower.")

@pytest.mark.ai_models
@pytest.mark.slow
def test_benchmark(opt_components):
    benchmark(opt_components)

if __name__ == "__main__":
    benchmark()
