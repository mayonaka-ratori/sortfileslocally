import os
import onnxruntime as ort
from PIL import Image
import numpy as np
from typing import List, Tuple
from huggingface_hub import hf_hub_download
import pandas as pd
import logging

class JoyTagONNX:
    # Extracted normalization constants for WD14/JoyTag
    MEAN_ARR = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
    STD_ARR = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

    def __init__(self, model_dir="data/models/joytag"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "model.onnx")
        self.tags_path = os.path.join(self.model_dir, "top_tags.txt")
        self.wd14_csv_path = os.path.join(self.model_dir, "wd14_selected_tags.csv")
        self._ensure_models()
        self._init_session()

    def _ensure_models(self):
        if not os.path.exists(self.model_path):
            print("Downloading JoyTag ONNX (model.onnx). This may take a minute...")
            hf_hub_download(repo_id="fancyfeast/joytag", filename="model.onnx", local_dir=self.model_dir)

        if not os.path.exists(self.tags_path):
            print("Downloading JoyTag tags (top_tags.txt)...")
            hf_hub_download(repo_id="fancyfeast/joytag", filename="top_tags.txt", local_dir=self.model_dir)
            
        if not os.path.exists(self.wd14_csv_path):
            print("Downloading WD14 tag categories for mapping...")
            hf_hub_download(
                repo_id="SmilingWolf/wd-vit-tagger-v3",
                filename="selected_tags.csv",
                local_dir=self.model_dir
            )
            # rename it
            dl_path = os.path.join(self.model_dir, "selected_tags.csv")
            if os.path.exists(dl_path):
                os.rename(dl_path, self.wd14_csv_path)

    def _init_session(self):
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        self.session = ort.InferenceSession(self.model_path, providers=providers)
        
        with open(self.tags_path, 'r', encoding='utf-8') as f:
            self.joytag_tags = [x.strip() for x in f.readlines()]
            
        df = pd.read_csv(self.wd14_csv_path)
        self.tag_category_map = {str(k).replace(' ', '_'): v for k, v in df.set_index('name')['category'].to_dict().items()}
        
        self.input_name = self.session.get_inputs()[0].name
        shape = self.session.get_inputs()[0].shape
        self.input_size = 448 if len(shape) < 3 or isinstance(shape[2], str) else shape[2]

    def _prepare_image(self, pil_img: Image.Image) -> np.ndarray:
        w, h = pil_img.size
        img = pil_img.convert("RGB")
        
        # Pad to square
        size = max(w, h)
        new_img = Image.new("RGB", (size, size), (255, 255, 255))
        new_img.paste(img, ((size - w) // 2, (size - h) // 2))
        
        # Resize
        new_img = new_img.resize((self.input_size, self.input_size), Image.Resampling.LANCZOS)
        
        # To Numpy RGB
        img_np = np.array(new_img).astype(np.float32)
        # Standard subset normalization
        img_np /= 255.0
        img_np = (img_np - self.MEAN_ARR) / self.STD_ARR
        
        # HWC to CHW
        img_np = np.transpose(img_np, (2, 0, 1))
        return img_np

    def _classify_tags(self, preds: np.ndarray, threshold: float) -> Tuple[List[str], List[str], List[str]]:
        general_tags = []
        char_tags = []
        series_tags = []
        
        for i, score in enumerate(preds):
            if score > threshold:
                tag_name = self.joytag_tags[i]
                clean_name = tag_name.replace(' ', '_')
                display_name = tag_name.replace('_', ' ')
                
                cat = self.tag_category_map.get(clean_name)
                if cat == 4:
                    char_tags.append(display_name)
                elif cat == 3:
                    series_tags.append(display_name)
                else:
                    if cat is None:
                        logging.warning(f"Tag mapping not found for JoyTag: {clean_name}, treating as general")
                    general_tags.append(display_name)
                    
        return general_tags, char_tags, series_tags

    def tag_image(self, pil_img: Image.Image, threshold: float = 0.4) -> Tuple[List[str], List[str], List[str]]:
        blob = self._prepare_image(pil_img)
        blob = np.expand_dims(blob, axis=0) # Add batch dim
        preds = self.session.run(None, {self.input_name: blob})[0][0]
        preds = 1 / (1 + np.exp(-preds))
        return self._classify_tags(preds, threshold)

    def tag_batch(self, images: List[Image.Image], threshold: float = 0.4) -> List[Tuple[List[str], List[str], List[str]]]:
        if not images: return []
        
        blobs = [self._prepare_image(img) for img in images]
        
        try:
            batch_blob = np.stack(blobs, axis=0)
            batch_preds = self.session.run(None, {self.input_name: batch_blob})[0]
            batch_preds = 1 / (1 + np.exp(-batch_preds))
            return [self._classify_tags(preds, threshold) for preds in batch_preds]
        except Exception:
            # Fallback to sequential if batching fails or model fixed batch size
            results = []
            for blob in blobs:
                blob_batch = np.expand_dims(blob, axis=0)
                preds = self.session.run(None, {self.input_name: blob_batch})[0][0]
                preds = 1 / (1 + np.exp(-preds))
                results.append(self._classify_tags(preds, threshold))
            return results
