from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image
import torch

from .ai_models import AIEngine
from .joytag_inference import JoyTagONNX
from .vlm_engine import VLMEngine

class InferenceOrchestrator:
    """
    Orchestrates AI Models (CLIP, InsightFace, JoyTag).
    Decides which models to run based on content type (Photo vs Illustration).
    """
    
    def __init__(self, ai_engine: AIEngine = None):
        self.ai_engine = ai_engine if ai_engine else AIEngine()
        self.char_tagger = JoyTagONNX()
        self.vlm_engine = VLMEngine()
        
    def classify_style(self, img: Image.Image) -> str:
        return self.ai_engine.classify_style(img)
        
    def process_image(self, img: Image.Image) -> Dict[str, Any]:
        """
        Process a single image.
        Returns dictionary with keys: 'clip', 'faces', 'general_tags', 'char_tags', 'series_tags', 'style'
        """
        result = {}
        
        # 1. Style Detection
        style = self.classify_style(img)
        result['style'] = style
        
        # 2. CLIP Embedding & Caption
        base_clip_vec = self.ai_engine.extract_clip_feature(img)
        
        caption = self.vlm_engine.generate_detailed_caption(img)
        if caption is not None:
            result['caption'] = caption
            text_vec = self.ai_engine.extract_clip_text_feature(caption)
            blended_vec = (base_clip_vec + text_vec) / 2.0
            blended_vec /= np.linalg.norm(blended_vec)
            result['clip'] = blended_vec.tolist()
        else:
            result['caption'] = ""
            result['clip'] = base_clip_vec.tolist()
        
        # 3. Face Detection
        # Needs BGR numpy
        img_np = np.array(img.convert('RGB'))
        img_bgr = img_np[:, :, ::-1]
        raw_faces = self.ai_engine.extract_face_features(img_bgr)
        # Convert to serializable format (list of dicts) if not already
        # extract_face_features returns list of dicts.
        # We might want to standardise schemas here or in Processor?
        # Let's return raw for now, caller maps to Schema.
        result['faces'] = raw_faces
        
        # 4. Character Tagging (Conditional)
        if style == "illustration":
            g_tags, c_tags, s_tags = self.char_tagger.tag_image(img)
            result['general_tags'] = g_tags
            result['char_tags'] = c_tags
            result['series_tags'] = s_tags
        else:
            result['general_tags'] = []
            result['char_tags'] = []
            result['series_tags'] = []
            
        return result

    def process_batch(self, images: List[Image.Image]) -> List[Dict[str, Any]]:
        """
        Process a batch of images.
        Used for video frames.
        """
        if not images:
            return []
            
        # 1. CLIP Batch
        base_clip_vecs = self.ai_engine.extract_clip_features_batch(images)
        
        # Add Captions and Blend
        clip_vecs = []
        captions = []
        for i, img in enumerate(images):
            caption = self.vlm_engine.generate_detailed_caption(img)
            if caption is not None:
                captions.append(caption)
                text_vec = self.ai_engine.extract_clip_text_feature(caption)
                blended_vec = (base_clip_vecs[i] + text_vec) / 2.0
                blended_vec /= np.linalg.norm(blended_vec)
                clip_vecs.append(blended_vec)
            else:
                captions.append("")
                clip_vecs.append(base_clip_vecs[i])
        
        # 2. Face Batch
        bgr_stack = [np.array(img.convert('RGB'))[:, :, ::-1] for img in images]
        faces_list = self.ai_engine.extract_face_features_batch(bgr_stack)
        
        # 3. Style Classification
        results = []
        
        # Tagging Batch Prep
        ill_indices = []
        style_list = []
        
        # Determine Style & Collect Illustration Indices
        for i, vec in enumerate(base_clip_vecs):
            # dot product with style means
            vec_tensor = torch.tensor(vec).to(self.ai_engine.device).unsqueeze(0).to(self.ai_engine.style_mean.dtype)
            score_anime = (vec_tensor @ self.ai_engine.style_mean.T).item()
            score_photo = (vec_tensor @ self.ai_engine.photo_mean.T).item()
            
            style = "photo" if score_photo > score_anime else "illustration"
            style_list.append(style)
            
            if style == "illustration":
                ill_indices.append(i)
        
        # Run Tagger on Illustrations Only
        batch_char_tags = [([], [], []) for _ in range(len(images))]
        
        if ill_indices:
            # Prepare batch for Tagger (List of PIL)
            ill_imgs = [images[i] for i in ill_indices]
            tag_results = self.char_tagger.tag_batch(ill_imgs)
            for local_i, global_i in enumerate(ill_indices):
                batch_char_tags[global_i] = tag_results[local_i]
                
        # Assemble
        for i in range(len(images)):
            res = {
                'style': style_list[i],
                'clip': clip_vecs[i].tolist() if isinstance(clip_vecs[i], np.ndarray) else clip_vecs[i],
                'caption': captions[i],
                'faces': faces_list[i],
                'general_tags': batch_char_tags[i][0],
                'char_tags': batch_char_tags[i][1],
                'series_tags': batch_char_tags[i][2]
            }
            results.append(res)
            
        return results
