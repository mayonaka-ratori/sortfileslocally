import sys
import os
import pytest

try:
    import numpy as np
    import cv2
    from PIL import Image
except Exception:
    pytest.skip("Dependencies missing for engine test (cv2, numpy, PIL)", allow_module_level=True)

# Add src to path
sys.path.append(os.path.abspath("src"))

try:
    from core.ai_models import AIEngine
    from core.video_processor import VideoProcessor
except Exception:
    pytest.skip("Core modules failed to import (likely missing torch/faiss)", allow_module_level=True)

def create_dummy_video(filename="dummy_video.mp4", duration_sec=5, fps=30):
    height, width = 640, 640
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    frames = int(duration_sec * fps)
    for i in range(frames):
        # Create a changing color frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (i % 255, (i*2) % 255, (i*3) % 255) # BGR
        
        # Draw a moving rectangle (simulating a "face" or object)
        cv2.rectangle(frame, (i%500, 100), ((i%500)+100, 200), (255, 255, 255), -1)
        
        out.write(frame)
    
    out.release()

@pytest.mark.ai_models
def test_engine_initialization():
    try:
        engine = AIEngine()
        assert engine is not None
    except Exception as e:
        pytest.fail(f"AIEngine failed to initialize: {e}")

@pytest.mark.ai_models
def test_clip_extraction():
    engine = AIEngine()
    dummy_image = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    
    try:
        clip_vector = engine.extract_clip_feature(dummy_image)
        assert clip_vector.shape == (768,)
    except Exception as e:
        pytest.fail(f"CLIP extraction failed: {e}")

@pytest.mark.ai_models
def test_insightface_execution():
    engine = AIEngine()
    dummy_face_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    try:
        faces = engine.extract_face_features(dummy_face_img)
        assert isinstance(faces, list)
    except Exception as e:
        pytest.fail(f"InsightFace execution failed: {e}")

@pytest.mark.ai_models
@pytest.mark.slow
def test_video_processor():
    dummy_vid_name = "dummy_video_test.mp4"
    create_dummy_video(dummy_vid_name)
    
    try:
        vp = VideoProcessor()
        result = vp.process_video(dummy_vid_name)
        
        if result:
            assert result['duration'] > 0
            assert result['fps'] > 0
            assert result['clip_embedding'].shape == (768,)
            assert isinstance(result['faces'], list)
        else:
            pytest.fail("Video processing returned None")
            
    except Exception as e:
        pytest.fail(f"Video processing failed: {e}")
    finally:
        if os.path.exists(dummy_vid_name):
            try: os.remove(dummy_vid_name)
            except: pass
