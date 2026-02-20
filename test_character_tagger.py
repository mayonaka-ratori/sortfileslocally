
import os
import sys
from PIL import Image
# Add current dir to path
sys.path.append(os.getcwd())

from src.core.character_tagger import CharacterTagger

def test_tagging():
    tagger = CharacterTagger()
    
    # Use a dummy image if no real one provided
    test_img_path = "test_character.jpg"
    if not os.path.exists(test_img_path):
        # Create a white dummy image
        img = Image.new('RGB', (512, 512), color=(255, 255, 255))
        img.save(test_img_path)
        print("Created dummy test image.")
    
    img = Image.open(test_img_path)
    chars, series = tagger.tag_image(img)
    
    print(f"Results for {test_img_path}:")
    print(f"Characters: {chars}")
    print(f"Series: {series}")

if __name__ == "__main__":
    test_tagging()
