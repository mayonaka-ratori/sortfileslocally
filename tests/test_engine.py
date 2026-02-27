import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Skip if requested in CI
if os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("Skipping engine tests in CI", allow_module_level=True)

@pytest.fixture
def engine_components():
    import numpy as np
    try:
        import cv2
    except ImportError:
        cv2 = MagicMock()
    from PIL import Image
    
    # Internal core modules
    from core.ai_models import AIEngine
    from core.video_processor import VideoProcessor
    
    return {
        "np": np,
        "cv2": cv2,
        "Image": Image,
        "AIEngine": AIEngine,
        "VideoProcessor": VideoProcessor
    }

def create_dummy_video(filename="dummy_video.mp4", duration_sec=5, fps=30, components=None):
    cv2 = components["cv2"]
    np = components["np"]
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
def test_engine_initialization(engine_components):
    AIEngine = engine_components["AIEngine"]
    try:
        engine = AIEngine()
        assert engine is not None
    except Exception as e:
        pytest.fail(f"AIEngine failed to initialize: {e}")

@pytest.mark.ai_models
def test_clip_extraction(engine_components):
    AIEngine = engine_components["AIEngine"]
    np = engine_components["np"]
    Image = engine_components["Image"]
    engine = AIEngine()
    dummy_image = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    
    try:
        clip_vector = engine.extract_clip_feature(dummy_image)
        assert clip_vector.shape == (768,)
    except Exception as e:
        pytest.fail(f"CLIP extraction failed: {e}")

@pytest.mark.ai_models
def test_insightface_execution(engine_components):
    AIEngine = engine_components["AIEngine"]
    np = engine_components["np"]
    engine = AIEngine()
    dummy_face_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    try:
        faces = engine.extract_face_features(dummy_face_img)
        assert isinstance(faces, list)
    except Exception as e:
        pytest.fail(f"InsightFace execution failed: {e}")

@pytest.mark.ai_models
@pytest.mark.slow
def test_video_processor(engine_components):
    VideoProcessor = engine_components["VideoProcessor"]
    dummy_vid_name = "dummy_video_test.mp4"
    create_dummy_video(dummy_vid_name, components=engine_components)
    
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
