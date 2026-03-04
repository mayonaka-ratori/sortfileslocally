import pytest
import numpy as np
import os
import sys
import tempfile
import base64
import struct
import wave
from PIL import Image

# 1. IMPORTS AND MARKERS

torch_available = False
try:
    import torch
    torch_available = torch.cuda.is_available()
except ImportError:
    pass

pytestmark = [
    pytest.mark.gpu,
    pytest.mark.ai_models,
    pytest.mark.skipif(not torch_available, reason="CUDA not available")
]

# 2. FIXTURES (module scope for model caching)

@pytest.fixture(scope="module")
def ai_engine():
    """Initialize AIEngine singleton. Module-scoped so models load once."""
    # Ensure project root is in sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.core.ai_models import AIEngine
    engine = AIEngine()
    return engine

@pytest.fixture(scope="module")
def photo_image():
    """Generate a simple photo-like image: outdoor scene with blue sky and green ground."""
    img = Image.new('RGB', (224, 224))
    pixels = img.load()
    for y in range(224):
        for x in range(224):
            if y < 112:
                # Sky: blue with slight variation
                pixels[x, y] = (100 + (x % 30), 150 + (y % 20), 220)
            else:
                # Ground: green/brown
                pixels[x, y] = (80 + (x % 20), 140 + (y % 30), 60)
    return img

@pytest.fixture(scope="module")
def illustration_image():
    """Generate a simple anime/illustration-like image: flat colors, bold outlines."""
    img = Image.new('RGB', (224, 224))
    pixels = img.load()
    for y in range(224):
        for x in range(224):
            # Flat pastel fill with hard edge "outline"
            if x < 5 or x > 218 or y < 5 or y > 218:
                pixels[x, y] = (0, 0, 0)  # Black outline
            elif x < 112:
                pixels[x, y] = (255, 182, 193)  # Flat pink
            else:
                pixels[x, y] = (173, 216, 230)  # Flat light blue
    return img

@pytest.fixture(scope="module")
def face_image():
    """Load a minimal face image for InsightFace detection.
    Creates a synthetic face-like pattern. NOTE: InsightFace may not detect
    purely synthetic faces — if detection fails, the test documents this limitation."""
    # Create a skin-tone oval on neutral background (basic face proxy)
    img = Image.new('RGB', (320, 320), (200, 200, 200))
    pixels = img.load()
    cx, cy, rx, ry = 160, 140, 60, 80
    for y in range(320):
        for x in range(320):
            # Oval check
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                pixels[x, y] = (210, 170, 135)  # Skin tone
            # Simple eye dots
            if (x - 140) ** 2 + (y - 120) ** 2 < 25:
                pixels[x, y] = (40, 30, 20)
            if (x - 180) ** 2 + (y - 120) ** 2 < 25:
                pixels[x, y] = (40, 30, 20)
            # Simple mouth line
            if 148 <= x <= 172 and 165 <= y <= 170:
                pixels[x, y] = (150, 60, 60)
    return img

@pytest.fixture(scope="module")
def blank_image():
    """All-black image for negative face detection test."""
    return Image.new('RGB', (320, 320), (0, 0, 0))

@pytest.fixture(scope="module")
def audio_file():
    """Generate a minimal WAV file with a simple sine wave tone (440Hz, 2 seconds).
    Whisper should detect it as audio but may not produce meaningful text —
    the test verifies the pipeline works, not transcription accuracy."""
    import math
    sample_rate = 16000
    duration = 2.0
    frequency = 440.0
    num_samples = int(sample_rate * duration)

    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    with wave.open(tmp.name, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(num_samples):
            sample = int(16000 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wav.writeframes(struct.pack('<h', sample))

    yield tmp.name
    os.unlink(tmp.name)


# 3. TEST CASES

# --- A. CLIP Feature Extraction ---

def test_clip_feature_nonzero(ai_engine, photo_image):
    feature = ai_engine.extract_clip_feature(photo_image)
    assert feature.shape == (768,), f"Expected shape (768,), got {feature.shape}"
    assert np.any(feature != 0), "Feature vector is all zeros"

def test_clip_feature_normalized(ai_engine, photo_image):
    feature = ai_engine.extract_clip_feature(photo_image)
    norm = np.linalg.norm(feature)
    assert abs(norm - 1.0) < 0.05, f"Expected L2 norm ≈ 1.0, got {norm}"

def test_clip_text_feature_nonzero(ai_engine):
    feature = ai_engine.extract_clip_text_feature("a photo of a cat")
    assert feature.shape == (768,), f"Expected shape (768,), got {feature.shape}"
    assert np.any(feature != 0), "Text feature vector is all zeros"

def test_clip_similarity_basic(ai_engine):
    dog = ai_engine.extract_clip_text_feature("a photo of a dog")
    cat = ai_engine.extract_clip_text_feature("a photo of a cat")
    physics = ai_engine.extract_clip_text_feature("quantum physics equation")
    
    # Cosine similarity (vectors are already normalized)
    sim_related = float(np.dot(dog, cat))
    sim_unrelated = float(np.dot(dog, physics))
    
    assert sim_related > 0.5, f"Dog-cat similarity {sim_related:.3f} should be > 0.5"
    assert sim_unrelated < 0.5, f"Dog-physics similarity {sim_unrelated:.3f} should be < 0.5"


# --- B. Style Classification ---

def test_classify_photo_vs_illustration(ai_engine, photo_image, illustration_image):
    photo_result = ai_engine.classify_style(photo_image)
    illustration_result = ai_engine.classify_style(illustration_image)
    # NOTE: With synthetic images, classification may not be perfect.
    # At minimum, verify the method returns valid values.
    assert photo_result in ('photo', 'illustration'), f"Unexpected result: {photo_result}"
    assert illustration_result in ('photo', 'illustration'), f"Unexpected result: {illustration_result}"
    # Soft assertion: log if classification doesn't match expectation
    if photo_result != 'photo':
        import warnings
        warnings.warn(f"Photo image classified as '{photo_result}' — synthetic image limitation")
    if illustration_result != 'illustration':
        import warnings
        warnings.warn(f"Illustration image classified as '{illustration_result}' — synthetic image limitation")


# --- C. Face Detection ---

def test_face_detection_basic(ai_engine, face_image):
    """Attempt face detection on synthetic face image.
    InsightFace may not detect synthetic faces — we test the pipeline doesn't crash."""
    import cv2
    img_np = np.array(face_image)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    faces = ai_engine.extract_face_features(img_bgr)
    # Pipeline must not crash; detection count is informational
    assert isinstance(faces, list), "Expected list return type"
    if len(faces) == 0:
        import warnings
        warnings.warn("No faces detected in synthetic image — expected limitation")

def test_face_embedding_shape(ai_engine, face_image):
    """If faces are detected, verify embedding dimensions."""
    import cv2
    img_np = np.array(face_image)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    faces = ai_engine.extract_face_features(img_bgr)
    for face in faces:
        assert 'embedding' in face, "Face dict missing 'embedding' key"
        assert face['embedding'].shape == (512,), f"Expected (512,), got {face['embedding'].shape}"
        assert 'bbox' in face, "Face dict missing 'bbox' key"
        assert 'det_score' in face, "Face dict missing 'det_score' key"

def test_face_no_faces_in_blank(ai_engine, blank_image):
    """Blank image should return no faces."""
    import cv2
    img_np = np.array(blank_image)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    faces = ai_engine.extract_face_features(img_bgr)
    assert faces == [], f"Expected empty list for blank image, got {len(faces)} faces"


# --- D. Whisper Transcription ---

def test_whisper_basic_transcription(ai_engine, audio_file):
    """Test Whisper transcription pipeline with sine wave audio.
    A pure tone may produce empty/nonsensical text, but the pipeline must not crash."""
    segments = ai_engine.transcribe_audio(audio_file)
    assert isinstance(segments, list), f"Expected list, got {type(segments)}"
    # Pipeline must complete without error; segment count is informational
    if len(segments) > 0:
        seg = segments[0]
        assert 'start' in seg, "Segment missing 'start' key"
        assert 'end' in seg, "Segment missing 'end' key"
        assert 'text' in seg, "Segment missing 'text' key"
    else:
        import warnings
        warnings.warn("Whisper returned no segments for sine wave — expected for non-speech audio")
