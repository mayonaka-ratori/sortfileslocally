
import os
import sys
import numpy as np
from PIL import Image

# Setup path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.core.inference import InferenceOrchestrator
from src.core.ai_models import AIEngine

def test_batch_unpacking():
    print("Initializing Engine...")
    engine = AIEngine() 
    orchestrator = InferenceOrchestrator(engine)
    
    # Create dummy images (Illustration style)
    # We need them to be classified as illustration to trigger the tagger.
    # We can force classification or just use random noise and hope?
    # Or strict mock?
    # Better: Mock AIEngine to return "illustration" vector.
    
    print("Running process_batch with dummy images (Forced Illustration)...")
    
    # Create 3 dummy images
    images = [Image.new('RGB', (448, 448), color=(255, 0, 0)) for _ in range(3)]
    
    # MOCK extract_clip_features_batch to return style_mean (Illustration)
    # We need to know shape. (N, 768)
    def mock_clip_batch(imgs):
        print("MOCK: Returning illustration vectors")
        # Use style_mean from engine
        # style_mean is tensor (1, 768). Convert to numpy.
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

if __name__ == "__main__":
    test_batch_unpacking()
