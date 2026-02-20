
import os
import sys
from PIL import Image
import numpy as np

sys.path.append(os.path.join(os.getcwd(), 'src'))
from src.core.character_tagger import CharacterTagger

def test_model_load():
    print("Initializing CharacterTagger with WD ViT v3...")
    try:
        tagger = CharacterTagger() # Should trigger download
        print("Model loaded successfully!")
        
        # Print input shape
        print(f"Model Input Name: {tagger.input_name}")
        print(f"Model Input Shape: {tagger.input_shape}")
        
        # Dummy Inference
        print("Running dummy inference...")
        dummy_img = Image.new("RGB", (512, 512), (255, 255, 255))
        chars, series = tagger.tag_image(dummy_img)
        print("Inference successful!")
        print(f"Detected Tags (White Image): {chars}, {series}")
        
    except Exception as e:
        print(f"\nFAILED to load/run model: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_model_load()
