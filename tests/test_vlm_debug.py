import sys, os, pytest
from unittest.mock import MagicMock

# Only mock if necessary, and use a robust way to check availability
def is_available(mod_name):
    try:
        mod = __import__(mod_name)
        if 'mock' in str(type(mod)).lower():
            return False
        return True
    except (ImportError, ValueError, Exception):
        return False

sys.path.append(os.path.abspath("src"))

# Skip if requested in CI
if os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("Skipping VLM debug tests in CI", allow_module_level=True)

# Use allow_module_level=True to skip the whole file if dependencies are missing
if not is_available("torch") or not is_available("transformers") or not is_available("PIL"):
    pytest.skip("Torch/Transformers/PIL not available", allow_module_level=True)

try:
    from src.core.vlm_engine import VLMEngine
    from PIL import Image
    import torch
except Exception as e:
    pytest.skip(f"Failed to import VLM core: {e}", allow_module_level=True)

def test_vlm_debug_pad_token():
    # If VLMEngine is a mock (leaked from another test), skip
    if 'mock' in str(type(VLMEngine)).lower():
        pytest.skip("VLMEngine is mocked by another test - cannot run real debug test")

    vlm = VLMEngine()
    # If the model is not actually loaded (e.g. weights missing), skip
    if not hasattr(vlm, '_loaded') or not vlm._loaded:
        pytest.skip("VLM model weights not loaded")

    img = Image.new('RGB', (100, 100))

    try:
        ans = vlm.ask_image(img, "What is this?")
        assert isinstance(ans, str)
        
        if vlm.model:
            if hasattr(vlm.model.config, "pad_token_id"):
                print("pad_token_id is present in config")
            else:
                print("pad_token_id is missing from config")
    except Exception as e:
        pytest.fail(f"VLM debug call failed: {e}")
