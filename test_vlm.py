from PIL import Image
import os
import sys

# Ensure src in path
sys.path.append(os.path.abspath("src"))
from core.vlm_engine import VLMEngine

def main():
    print("Testing VLM Engine Initialization...")
    engine = VLMEngine()
    
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color = 'red')
    
    print("Testing VQA inference...")
    answer = engine.ask_image(img, "What color is this image?")
    print(f"Answer: {answer}")
    
    print("Test Complete.")

if __name__ == "__main__":
    main()
