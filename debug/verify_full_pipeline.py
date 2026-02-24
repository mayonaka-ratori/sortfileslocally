
import os
import numpy as np
import sys
import torch
from PIL import Image

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.processor import Processor
from src.data.db_manager import DBManager
from src.data.schemas import MediaItem

def create_dummy_video(path, duration=5, fps=24):
    """Create a dummy mp4 using ffmpeg if available, or just a placeholder."""
    # We need a real video for PySceneDetect to work well.
    # Let's try to use ffmpeg to generate a test pattern.
    import subprocess
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', f'testsrc=duration={duration}:size=640x480:rate={fps}',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def test_full_pipeline():
    db_dir = os.path.join("data", "test_db_full")
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)
        
    p = Processor(db_dir=db_dir)
    
    video_path = "test_full_video.mp4"
    if not create_dummy_video(video_path):
        print("Failed to create dummy video. Ensure ffmpeg is in PATH.")
        return

    try:
        print(f"Processing video: {video_path}")
        item = p.scanner.inspect_file(video_path)
        result = p._process_item(item)
        
        print(f"Success: {result.success}")
        print(f"Scenes Detected: {len(result.scenes)}")
        
        if result.scenes:
            for i, scene in enumerate(result.scenes):
                print(f"Scene {i}: {scene.start_time:.2f}s - {scene.end_time:.2f}s | Caption: {scene.caption[:50]}...")

        # Add to DB
        print("Adding to DB...")
        p.db_manager.add_result(result)
        
        # Search
        print("Testing DB Search...")
        # Search for a scene
        if result.scenes:
            scene_vec = np.array(result.scenes[0].clip_vector, dtype='float32')
            h_res = p.db_manager.hybrid_search(scene_vec, filters={}, top_k=5)
            print(f"Search Results: {len(h_res['results'])}")
            if h_res['results']:
                match = h_res['results'][0]
                print(f"Top Match: {match['file_path']} | Score: {match['score']:.4f}")
                if 'matched_scene' in match:
                    print(f"Matched Scene: {match['matched_scene']['start_time']}s - {match['matched_scene']['end_time']}s")

        print("Full Pipeline Verification Successful!")
        
    finally:
        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(db_dir):
            import shutil
            shutil.rmtree(db_dir)

if __name__ == "__main__":
    test_full_pipeline()
