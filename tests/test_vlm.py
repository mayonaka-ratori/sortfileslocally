from PIL import Image
import os
import sys

sys.path.append(os.path.abspath("src"))
from core.vlm_engine import VLMEngine

def main():
    print("Testing Florence-2 Initialization...")
    engine = VLMEngine()
    
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color='blue')
    
    print("Testing generate_detailed_caption inference...")
    caption = engine.generate_detailed_caption(img)
    print(f"Caption: {caption}")

    print("Testing VQA fallback...")
    answer = engine.ask_image(img, "What color is the image?")
    print(f"Answer: {answer}")
    
    print("Test Complete.")

if __name__ == "__main__":
    main()
