import pytest
import sys
import os

# Check if dependencies are missing or mocked
def is_dependency_missing_or_mocked(name):
    if name not in sys.modules:
        try:
            __import__(name)
        except ImportError:
            return True
    
    # Check if it's a MagicMock (common in this test suite's collection phase)
    module = sys.modules.get(name)
    if module and hasattr(module, "_mock_return_value"):
        return True
    if "MagicMock" in str(type(module)):
        return True
        
    return False

if is_dependency_missing_or_mocked("torch") or is_dependency_missing_or_mocked("transformers") or os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("VLM dependencies not installed, mocked, or CI skip requested", allow_module_level=True)

import torch
if not torch.cuda.is_available() or os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("VLM tests require GPU or CI skip requested", allow_module_level=True)

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
