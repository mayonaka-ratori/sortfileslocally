
import os
import cv2
import numpy as np
import pandas as pd
import onnxruntime as ort
from PIL import Image
from typing import List, Tuple, Dict
import requests
from tqdm import tqdm

class CharacterTagger:
    MODEL_URL = "https://huggingface.co/SmilingWolf/wd-vit-tagger-v3/resolve/main/model.onnx"
    CSV_URL = "https://huggingface.co/SmilingWolf/wd-vit-tagger-v3/resolve/main/selected_tags.csv"
    
    def __init__(self, model_dir: str = "data/models/wd-vit-v3"):
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "model.onnx")
        self.csv_path = os.path.join(model_dir, "selected_tags.csv")
        
        self._ensure_model_exists()
        
        # Initialize ONNX
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.session = ort.InferenceSession(self.model_path, providers=providers)
        
        # Load Tags
        self.tags_df = pd.read_csv(self.csv_path)
        # Categories: 0: general, 4: character, 3: copyright, 1: rating
        self.char_indices = self.tags_df[self.tags_df['category'] == 4].index.tolist()
        self.series_indices = self.tags_df[self.tags_df['category'] == 3].index.tolist()
        self.all_tag_names = self.tags_df['name'].tolist()

        # Input shape (WD14 ConvNext is usually 448x448)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape[1:3] # H, W

    def _ensure_model_exists(self):
        os.makedirs(self.model_dir, exist_ok=True)
        if not os.path.exists(self.model_path):
            self._download(self.MODEL_URL, self.model_path)
        if not os.path.exists(self.csv_path):
            self._download(self.CSV_URL, self.csv_path)

    def _download(self, url: str, dest: str):
        print(f"Downloading {os.path.basename(dest)}...")
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        with open(dest, 'wb') as f, tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
            for data in response.iter_content(chunk_size=1024):
                f.write(data)
                pbar.update(len(data))

    def preprocess(self, pil_img: Image.Image) -> np.ndarray:
        """Preprocess for ConvNext Tagger. Returns (448, 448, 3) BGR float32."""
        # Resize to 448x448 with padding to keep aspect ratio
        w, h = pil_img.size
        # WD14 models expect RGB
        img = pil_img.convert("RGB")
        
        # Pad to square
        size = max(w, h)
        new_img = Image.new("RGB", (size, size), (255, 255, 255))
        new_img.paste(img, ((size - w) // 2, (size - h) // 2))
        
        # Resize
        new_img = new_img.resize((self.input_shape[1], self.input_shape[0]), Image.Resampling.LANCZOS)
        
        # To Numpy BGR (OpenCV Style as the model often expects BGR if using cv2, but check)
        # Usually WD14 Taggers use BGR
        img_np = np.array(new_img).astype(np.float32)
        img_np = img_np[:, :, ::-1] # RGB -> BGR
        
        # img_np = np.expand_dims(img_np, axis=0) # Removed: do expected dims in caller
        return img_np

    def tag_image(self, pil_img: Image.Image, threshold: float = 0.35) -> Tuple[List[str], List[str]]:
        """
        Predict character and series tags.
        Returns: (character_tags, series_tags)
        """
        blob = self.preprocess(pil_img)
        blob = np.expand_dims(blob, axis=0) # Add batch dim (1, 448, 448, 3)
        preds = self.session.run(None, {self.input_name: blob})[0][0]
        
        return self._decode_preds(preds, threshold)

    from typing import Union, List, Tuple
    
    def tag_batch(self, images: Union[List[Image.Image], np.ndarray], threshold: float = 0.35) -> List[Tuple[List[str], List[str]]]:
        """Process multiple images. Handles fixed-batch models by looping."""
        if isinstance(images, list):
             if not images: return []
             pil_images = images
        elif isinstance(images, np.ndarray):
             if images.size == 0: return []
             # Expect (N, H, W, 3)
             pil_images = [Image.fromarray(img) for img in images]
        else:
             return []
            
        # Parallel Preprocessing (CPU bound)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(pil_images), 8)) as executor:
            blobs = list(executor.map(self.preprocess, pil_images))
            
        # Check if model supports batching
        input_shape = self.session.get_inputs()[0].shape
        supports_batching = input_shape[0] not in [1, '1']
        
        results = []
        if supports_batching:
            try:
                batch_blob = np.stack(blobs, axis=0)
                batch_preds = self.session.run(None, {self.input_name: batch_blob})[0]
                for preds in batch_preds:
                    results.append(self._decode_preds(preds, threshold))
                return results
            except:
                pass

        # Sequential / Fixed Batch 1 Fallback
        for blob in blobs:
            # Need to add batch dim for session.run
            blob_batch = np.expand_dims(blob, axis=0)
            preds = self.session.run(None, {self.input_name: blob_batch})[0][0]
            results.append(self._decode_preds(preds, threshold))
            
        return results

    def _decode_preds(self, preds: np.ndarray, threshold: float) -> Tuple[List[str], List[str]]:
        """Decode probability vector to tags."""
        chars = []
        for i in self.char_indices:
            if preds[i] > threshold:
                name = self.all_tag_names[i].replace('_', ' ')
                chars.append(name)
        
        series = []
        for i in self.series_indices:
            if preds[i] > threshold:
                name = self.all_tag_names[i].replace('_', ' ')
                series.append(name)
                
        return chars, series
