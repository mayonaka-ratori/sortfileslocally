import pytest
import sys
import os

import torch

if os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("CI skip requested for GPU tests", allow_module_level=True)

try:
    if not torch.cuda.is_available():
        pytest.skip("VLM tests require CUDA", allow_module_level=True)
except Exception:
     pytest.skip("Torch not installed or working", allow_module_level=True)

from PIL import Image

sys.path.append(os.path.abspath("src"))

try:
    from core.vlm_engine import VLMEngine
except (ImportError, ValueError):
    pytest.skip("VLMEngine failed to import (likely missing transformers/torch)", allow_module_level=True)

@pytest.mark.gpu
@pytest.mark.ai_models
def test_vlm_initialization():
    engine = VLMEngine()
    assert engine is not None

@pytest.mark.gpu
@pytest.mark.ai_models
def test_vlm_inference():
    engine = VLMEngine()
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color='blue')
    
    caption = engine.generate_detailed_caption(img)
    assert isinstance(caption, str)

@pytest.mark.gpu
@pytest.mark.ai_models
def test_vlm_vqa():
    engine = VLMEngine()
    img = Image.new('RGB', (100, 100), color='blue')
    
    answer = engine.ask_image(img, "What color is the image?")
    assert isinstance(answer, str)
