from PIL import Image
import os
import sys
import pytest

sys.path.append(os.path.abspath("src"))

try:
    from core.vlm_engine import VLMEngine
except (ImportError, ValueError, Exception):
    pytest.skip("VLMEngine failed to import (likely missing transformers/torch)", allow_module_level=True)

def test_vlm_initialization():
    engine = VLMEngine()
    assert engine is not None

def test_vlm_inference():
    engine = VLMEngine()
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color='blue')
    
    caption = engine.generate_detailed_caption(img)
    assert isinstance(caption, str)

def test_vlm_vqa():
    engine = VLMEngine()
    img = Image.new('RGB', (100, 100), color='blue')
    
    answer = engine.ask_image(img, "What color is the image?")
    assert isinstance(answer, str)
