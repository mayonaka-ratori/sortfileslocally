
import os
import torch
import open_clip
import numpy as np
from PIL import Image
from insightface.app import FaceAnalysis
from typing import List, Optional, Tuple, Union, Dict, Any

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

class AIEngine:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AIEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"AIEngine initializing on device: {self.device}")
        
        if self.device == "cpu":
            print("WARNING: CUDA is not available. Performance will be significantly degraded.")

        # --- 1. Load CLIP Model ---
        print("Loading CLIP model (ViT-L-14 / laion2b_s32b_b82k)...")
        try:
            self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                'ViT-L-14', 
                pretrained='laion2b_s32b_b82k', 
                device=self.device
            )
            self.clip_model.eval() # Inference mode
            print("CLIP model loaded successfully.")
        except Exception as e:
            print(f"Failed to load CLIP model: {e}")
            raise e

        # --- 2. Load InsightFace Model ---
        print("Loading InsightFace model (buffalo_l)...")
        try:
            # providers: CUDAExecutionProvider if available, else CPUExecutionProvider
            providers = ['CUDAExecutionProvider'] if self.device == "cuda" else ['CPUExecutionProvider']
            
            self.face_app = FaceAnalysis(name='buffalo_l', providers=providers)
            # ctx_id=0 for GPU 0, det_size=(640, 640) can be adjusted if needed
            self.face_app.prepare(ctx_id=0, det_size=(640, 640))
            print("InsightFace model loaded successfully.")
        except Exception as e:
            print(f"Failed to load InsightFace model: {e}")
            raise e

        # --- 3. Pre-compute Text Features for Style Classification ---
        # "Anime" vs "Photo"
        self.style_prompts = ["anime illustration", "digital art", "sketch", "manga", "comic", "monochrome illustration", "lineart", "japanese comic"]
        self.photo_prompts = ["photo", "realistic", "live action", "color photograph", "real world photo", "realistic photo", "live action movie frame"]
        
        with torch.no_grad():
             style_tokens = open_clip.tokenize(self.style_prompts).to(self.device)
             photo_tokens = open_clip.tokenize(self.photo_prompts).to(self.device)
             
             self.style_embs = self.clip_model.encode_text(style_tokens)
             self.style_embs /= self.style_embs.norm(dim=-1, keepdim=True)
             self.style_mean = self.style_embs.mean(dim=0, keepdim=True)
             self.style_mean /= self.style_mean.norm(dim=-1, keepdim=True)

             self.photo_embs = self.clip_model.encode_text(photo_tokens)
             self.photo_embs /= self.photo_embs.norm(dim=-1, keepdim=True)
             self.photo_mean = self.photo_embs.mean(dim=0, keepdim=True)
             self.photo_mean /= self.photo_mean.norm(dim=-1, keepdim=True)

        # --- 4. Whisper Model ---
        # NOTE: Whisper (ctranslate2) is run in a subprocess to avoid DLL conflicts
        # with onnxruntime-gpu. No model is loaded here.

        self._initialized = True

    def classify_style(self, image: Image.Image) -> str:
        """
        Returns 'illustration' or 'photo' using zero-shot classification.
        """
        img_features = self.extract_clip_feature(image) # Returns numpy (1, dim)
        img_vec = torch.from_numpy(img_features).to(self.device).to(self.style_mean.dtype)
        
        # Compare cosine similarity with mean vectors
        # Shape: (1, dim) @ (dim, 1) -> (1, 1)
        score_anime = (img_vec @ self.style_mean.T).item()
        score_photo = (img_vec @ self.photo_mean.T).item()
        
        if score_photo > score_anime:
            return "photo"
        return "illustration"

    def extract_clip_feature(self, image: Image.Image) -> np.ndarray:
        """
        Extract CLIP image embedding.
        Returns a normalized numpy array of shape (768,).
        """
        try:
            # Preprocess and move to device
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad(), torch.cuda.amp.autocast():
                image_features = self.clip_model.encode_image(image_tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True) # Normalize

            return image_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Error in extract_clip_feature: {e}")
            return np.zeros(768, dtype=np.float32) # Return zero vector on error

    def extract_clip_text_feature(self, text: str) -> np.ndarray:
        """
        Extract CLIP text embedding for search queries.
        Returns a normalized numpy array of shape (768,).
        """
        try:
            tokenizer = open_clip.get_tokenizer('ViT-L-14')
            text_tensor = tokenizer([text]).to(self.device)

            with torch.no_grad(), torch.cuda.amp.autocast():
                text_features = self.clip_model.encode_text(text_tensor)
                text_features /= text_features.norm(dim=-1, keepdim=True)
            
            return text_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Error in extract_clip_text_feature: {e}")
            return np.zeros(768, dtype=np.float32)

    def extract_face_features(self, image_np: np.ndarray) -> List[dict]:
        """
        Extract face features using InsightFace.
        Input: numpy array (OpenCV format: BGR). If RGB, convert before calling or wrapper will handle if PIL provided?
        InsightFace expects BGR usually if read by cv2. 
        Note: If passing PIL image converted to np array, it is RGB. InsightFace expects BGR/RGB? 
        The FaceAnalysis.get() method typically expects BGR numpy array (cv2.imread style).
        
        Returns: List of dicts containing 'bbox', 'kps', 'det_score', 'embedding' (512,).
        """
        try:
            # InsightFace expects BGR images.
            # If the input appears to be RGB (e.g. from PIL), we might need to swap channels if strictly required.
            # However, typically simple detection works, but embeddings might be affected if color space is wrong.
            # Assuming the caller provides BGR or we handle conversion if we standardized on PIL elsewhere.
            # For this method, let's assume input is BGR numpy array as per standard cv2.
            
            faces = self.face_app.get(image_np)
            results = []
            for face in faces:
                results.append({
                    'bbox': face.bbox.astype(int).tolist(),
                    'det_score': float(face.det_score),
                    'embedding': face.embedding, # 512D numpy array
                    'kps': face.kps.astype(int).tolist() # Landmarks
                })
            return results
        except Exception as e:
            print(f"Error in extract_face_features: {e}")
            return []

    def extract_clip_features_batch(self, images: List[Image.Image]) -> np.ndarray:
        """
        Extract CLIP embeddings for a batch of images efficiently.
        Returns: numpy array of shape (N, 768)
        """
        if not images:
            return np.empty((0, 768), dtype=np.float32)

        try:
            # Preprocess all images and stack into a tensor
            # self.clip_preprocess returns (3, 224, 224)
            # torch.stack will make it (N, 3, 224, 224)
            tensors = [self.clip_preprocess(img) for img in images]
            batch_tensor = torch.stack(tensors).to(self.device)
            
            with torch.no_grad(), torch.cuda.amp.autocast():
                image_features = self.clip_model.encode_image(batch_tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True) # Normalize

            return image_features.cpu().numpy() # (N, 768)
        except Exception as e:
            print(f"Error in extract_clip_features_batch: {e}")
            return np.zeros((len(images), 768), dtype=np.float32)

    def extract_face_features_batch(self, images_np: List[np.ndarray]) -> List[List[dict]]:
        """
        InsightFace doesn't natively support batch inference in the same way (detection size varies).
        We simulate batching by processing sequentially but minimizing overhead.
        
        Input: List of BGR numpy arrays.
        Returns: List of Lists of face dicts.
        """
        batch_results = []
        for img in images_np:
            batch_results.append(self.extract_face_features(img))
        return batch_results

    def transcribe_audio(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Transcribe audio file using Whisper.
        Isolated to a subprocess to prevent ctranslate2/onnxruntime DLL conflicts.
        Returns: [{'start': float, 'end': float, 'text': str}, ...]
        """
        if not HAS_WHISPER:
            print("faster-whisper not installed.")
            return []

        if not os.path.exists(audio_path):
            print(f"Audio file not found for transcription: {audio_path}")
            return []

        try:
            import tempfile, subprocess, json, sys
            
            # Create a tiny Python script to run Whisper isolated from the main process
            script_code = '''
import sys, json
try:
    from faster_whisper import WhisperModel
    model = WhisperModel('base', device='cpu', compute_type='int8')
    segs, info = model.transcribe(sys.argv[1], beam_size=5)
    out = [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in segs]
    print(json.dumps(out))
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(json.dumps({'error': str(e)}))
'''
            # Windows requires the absolute audio path and correct escaping
            abs_audio_path = os.path.abspath(audio_path).replace('\\', '/')
            
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8') as f:
                f.write(script_code)
                script_path = f.name
                
            cmd = [sys.executable, script_path, abs_audio_path]
            # Suppress console window on windows
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NO_WINDOW
                
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
            
            if os.path.exists(script_path):
                os.remove(script_path)
                
            if res.returncode != 0:
                print(f"Whisper subprocess failed: {res.stderr}")
                return []
                
            try:
                # Find the JSON array line as ctranslate2 might print warnings
                lines = res.stdout.strip().splitlines()
                json_str = lines[-1] if lines else "[]"
                
                # Check if it returned an error dictionary
                result_data = json.loads(json_str)
                if isinstance(result_data, dict) and 'error' in result_data:
                    print(f"Whisper Error: {result_data['error']}")
                    return []
                    
                return result_data
            except Exception as e:
                print(f"Failed to parse Whisper output: {e}\nSTDOUT: {res.stdout}")
                return []
                
        except Exception as e:
            print(f"Error executing transcribe_audio: {e}")
            return []
