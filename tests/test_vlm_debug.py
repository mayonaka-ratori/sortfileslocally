from src.core.vlm_engine import VLMEngine
from PIL import Image
import torch

vlm = VLMEngine()
img = Image.new('RGB', (100, 100))

try:
    # This will trigger the internal load
    ans = vlm.ask_image(img, "What is this?")
    print("Answer:", ans)
    
    if vlm.model:
        print("Model config dir:", dir(vlm.model.config))
        if hasattr(vlm.model.config, "pad_token_id"):
            print("pad_token_id is present in config")
        else:
            print("pad_token_id is missing from config")
except Exception as e:
    print("Error:", e)
