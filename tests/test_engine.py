
import sys
import os
import numpy as np
from PIL import Image
import cv2

# Add src to path
sys.path.append(os.path.abspath("src"))

try:
    from core.ai_models import AIEngine
    from core.video_processor import VideoProcessor
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def create_dummy_video(filename="dummy_video.mp4", duration_sec=5, fps=30):
    print(f"Creating dummy video: {filename}...")
    height, width = 640, 640
    # fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    # Windows usually supports 'mp4v' effectively.
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
    print("Dummy video created.")

def test_engine():
    print("=== Starting AIEngine & VideoProcessor Test ===")
    
    # 1. Initialize Engine
    print("\n[Test 1] Initializing AIEngine...")
    try:
        engine = AIEngine()
        print("✅ AIEngine initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize AIEngine: {e}")
        return

    # 2. Test CLIP
    print("\n[Test 2] Testing CLIP Feature Extraction...")
    dummy_image = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    
    try:
        clip_vector = engine.extract_clip_feature(dummy_image)
        if clip_vector.shape == (768,):
            print("✅ CLIP extraction successful (Dimension: 768).")
        else:
            print(f"❌ CLIP vector dimension mismatch. Expected (768,), got {clip_vector.shape}")
    except Exception as e:
        print(f"❌ CLIP extraction failed: {e}")

    # 3. Test InsightFace
    print("\n[Test 3] Testing InsightFace Feature Extraction...")
    # Using a dummy BGR image
    dummy_face_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    try:
        faces = engine.extract_face_features(dummy_face_img)
        print(f"Faces detected: {len(faces)}")
        print("✅ InsightFace execution successful (No crash).")
    except Exception as e:
        print(f"❌ InsightFace execution failed: {e}")

    # 4. Test VideoProcessor
    print("\n[Test 4] Testing VideoProcessor...")
    dummy_vid_name = "dummy_video.mp4"
    create_dummy_video(dummy_vid_name)
    
    try:
        vp = VideoProcessor()
        # Ensure it shares the same AIEngine instance (Singleton check implicitly)
        
        print(f"Processing {dummy_vid_name}...")
        result = vp.process_video(dummy_vid_name)
        
        if result:
            print(f"✅ Video processing successful.")
            print(f"   Duration: {result['duration']:.2f}s")
            print(f"   FPS: {result['fps']:.2f}")
            print(f"   CLIP Vector Shape: {result['clip_embedding'].shape}")
            print(f"   Faces Detected: {len(result['faces'])}")
        else:
            print("❌ Video processing returned None.")
            
    except Exception as e:
        print(f"❌ Video processing failed: {e}")
    finally:
        # Cleanup
        if os.path.exists(dummy_vid_name):
            try:
                os.remove(dummy_vid_name)
            except:
                pass

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_engine()
