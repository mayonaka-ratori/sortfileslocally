
import os
import shutil
import time
from src.core.sorter import PhysicalSorter, SortLog
from src.data.schemas import MediaItem

def test_sorter_safety():
    print("=== Testing Physical Sorter ===")
    
    # Setup Dirs
    src_dir = "data/test_sort_src"
    dst_dir = "data/test_sort_dst"
    log_dir = "data/test_sort_logs"
    
    if os.path.exists(src_dir): shutil.rmtree(src_dir)
    if os.path.exists(dst_dir): shutil.rmtree(dst_dir)
    if os.path.exists(log_dir): shutil.rmtree(log_dir)
    
    os.makedirs(src_dir)
    
    # Create Dummy File
    src_file_path = os.path.join(src_dir, "test_img.jpg")
    with open(src_file_path, "w") as f:
        f.write("dummy content")
        
    ts = time.time()
    item = MediaItem(src_file_path, "hash", 10, "image", ts, ts, 100, 100)
    
    # Init Sorter
    logger = SortLog(log_dir)
    sorter = PhysicalSorter(logger)
    
    # 1. Dry Run
    print("Test 1: Dry Run")
    success = sorter.sort_file(item, dst_dir, "CategoryA", "dry_run")
    assert success
    assert os.path.exists(src_file_path) # Should still exist
    assert not os.path.exists(os.path.join(dst_dir, "CategoryA"))
    
    # 2. Copy
    print("Test 2: Copy")
    success = sorter.sort_file(item, dst_dir, "CategoryA", "copy")
    assert success
    assert os.path.exists(src_file_path) # Source exists
    
    year = os.path.join(dst_dir, "CategoryA", time.strftime("%Y"))
    dst_file = os.path.join(year, "test_img.jpg")
    assert os.path.exists(dst_file)
    print(f"Copied to: {dst_file}")
    
    # Check Undo Script
    with open(logger.undo_script, "r") as f:
        content = f.read()
        assert f'del "{dst_file}"' in content
        
    # 3. Move
    print("Test 3: Move")
    # Reset
    if os.path.exists(dst_file): os.remove(dst_file)
    
    success = sorter.sort_file(item, dst_dir, "CategoryB", "move")
    assert success
    assert not os.path.exists(src_file_path) # Source GONE
    
    dst_file_move = os.path.join(dst_dir, "CategoryB", time.strftime("%Y"), "test_img.jpg")
    assert os.path.exists(dst_file_move)
    print(f"Moved to: {dst_file_move}")
    
    # Check Undo (Move back)
    with open(logger.undo_script, "r") as f:
        content = f.readlines()[-1] # Last line
        # Should be: move "dst" "src"
        assert 'move "' in content and f'"{src_file_path}"' in content
        
    print("Sorter Safety Tests Passed!")

if __name__ == "__main__":
    test_sorter_safety()
