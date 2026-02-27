import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Skip if requested in CI
if os.environ.get("SKIP_GPU_TESTS") == "1":
    pytest.skip("Skipping debug tests in CI", allow_module_level=True)

@pytest.fixture
def debug_components():
    import numpy as np
    from PIL import Image
    from src.core.inference import InferenceOrchestrator
    from src.core.ai_models import AIEngine
    return {
        "np": np,
        "Image": Image,
        "InferenceOrchestrator": InferenceOrchestrator,
        "AIEngine": AIEngine
    }

@pytest.mark.ai_models
def test_batch_unpacking(debug_components):
    np = debug_components["np"]
    Image = debug_components["Image"]
    AIEngine = debug_components["AIEngine"]
    InferenceOrchestrator = debug_components["InferenceOrchestrator"]

    print("Initializing Engine...")
    engine = AIEngine() 
    orchestrator = InferenceOrchestrator(engine)
    
    # Create dummy images (Illustration style)
    print("Running process_batch with dummy images (Forced Illustration)...")
    
    # Create 3 dummy images
    images = [Image.new('RGB', (448, 448), color=(255, 0, 0)) for _ in range(3)]
    
    # MOCK extract_clip_features_batch to return style_mean (Illustration)
    def mock_clip_batch(imgs):
        print("MOCK: Returning illustration vectors")
        # Use style_mean from engine
        vec = engine.style_mean.cpu().numpy()
        return np.repeat(vec, len(imgs), axis=0)
        
    engine.extract_clip_features_batch = mock_clip_batch
    
    try:
        results = orchestrator.process_batch(images)
        print("Success! Results:", len(results))
        for res in results:
            print("Style:", res.get('style'))
            print("Tags:", res.get('char_tags'))
            
    except Exception as e:
        print("\nCRITICAL ERROR CAUGHT:")
        print(e)
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_batch_unpacking()
