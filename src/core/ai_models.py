
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

import threading

class AIEngine:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AIEngine, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        from server.dependencies import get_db_manager
        db = get_db_manager()
        self.profile = db.get_setting("execution_profile", "balanced")
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Force CPU if lightweight profile is chosen? User said "CPU-friendly", but if CUDA is available, we can still use it.
        # User explicitly mentioned fp32 for lightweight.
        
        print(f"AIEngine initializing with profile: {self.profile} on device: {self.device}")
        
        if self.device == "cpu":
            print("WARNING: CUDA is not available. Performance will be significantly degraded.")

        self.use_fp16 = self.profile != "lightweight" and self.device == "cuda"

        # --- 1. Load CLIP Model ---
        print(f"Loading CLIP model (ViT-L-14 / laion2b_s32b_b82k) [FP16={self.use_fp16}]...")
        try:
            self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                'ViT-L-14', 
                pretrained='laion2b_s32b_b82k', 
                device=self.device,
                precision='fp16' if self.use_fp16 else 'fp32'
            )
            self.clip_tokenizer = open_clip.get_tokenizer('ViT-L-14')
            self.clip_model.eval() # Inference mode
            print("CLIP model loaded successfully.")
        except Exception as e:
            print(f"Failed to load CLIP model: {e}")
            raise e

        # --- 2. Load InsightFace Model (BuffaloL) ---
        if self.profile != "lightweight":
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
                # We can proceed without faces in some cases, but better to fail if profile expects them
                raise e
        else:
            print("Skipping InsightFace (lightweight profile)")
            self.face_app = None

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
        self._whisper_process = None
        self._whisper_task_queue = None
        self._whisper_result_queue = None
        self._whisper_lock = threading.Lock()

        self._initialized = True

    def _ensure_whisper_worker_running(self):
        with self._whisper_lock:
            if self._whisper_process is None or not self._whisper_process.is_alive():
                print("Starting persistent Whisper worker process...")
                import multiprocessing
                from .whisper_worker import whisper_worker_process
                
                self._whisper_task_queue = multiprocessing.Queue()
                self._whisper_result_queue = multiprocessing.Queue()
                self._whisper_process = multiprocessing.Process(
                    target=whisper_worker_process,
                    args=(self._whisper_task_queue, self._whisper_result_queue),
                    daemon=True
                )
                self._whisper_process.start()
                
                # Wait for initialization
                import queue
                try:
                    init_msg = self._whisper_result_queue.get(timeout=60)
                    if init_msg.get('status') == 'ready':
                        print("Whisper worker process started and initialized successfully.")
                    else:
                        print(f"Whisper worker initialization failed: {init_msg}")
                except queue.Empty:
                    print("Error: Whisper worker initialization timed out after 60s.")
                    if self._whisper_process.is_alive():
                        self._whisper_process.terminate()
                except Exception as e:
                    print(f"Error waiting for Whisper worker initialization: {e}")

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
            
            with torch.no_grad(), torch.amp.autocast("cuda") if self.device == "cuda" else torch.no_grad():
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
            text_tensor = self.clip_tokenizer([text]).to(self.device)

            with torch.no_grad(), torch.amp.autocast("cuda") if self.device == "cuda" else torch.no_grad():
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
            
            with torch.no_grad(), torch.amp.autocast("cuda") if self.device == "cuda" else torch.no_grad():
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
        Isolated to a persistent subprocess to prevent ctranslate2/onnxruntime DLL conflicts.
        Returns: [{'start': float, 'end': float, 'text': str}, ...]
        """
        if not HAS_WHISPER:
            print("faster-whisper not installed.")
            return []

        if not os.path.exists(audio_path):
            print(f"Audio file not found for transcription: {audio_path}")
            return []

        try:
            import uuid
            import queue
            
            self._ensure_whisper_worker_running()
            
            task_id = str(uuid.uuid4())
            abs_audio_path = os.path.abspath(audio_path).replace('\\', '/')
            
            with self._whisper_lock:
                self._whisper_task_queue.put({
                    'task_id': task_id,
                    'audio_path': abs_audio_path
                })
                
                try:
                    # Wait for result with 60s timeout
                    result_msg = self._whisper_result_queue.get(timeout=60)
                except queue.Empty:
                    print(f"WARNING: Whisper worker timed out waiting for {audio_path}")
                    # Consider worker dead if it times out
                    if self._whisper_process and self._whisper_process.is_alive():
                        self._whisper_process.terminate()
                    return []
                    
                if result_msg.get('task_id') != task_id:
                    print(f"WARNING: Whisper worker returned result for wrong task ID. Expected {task_id}, got {result_msg.get('task_id')}")
                    return []
                    
                if 'error' in result_msg:
                    print(f"Whisper Error for {audio_path}: {result_msg['error']}")
                    return []
                    
                return result_msg.get('result', [])
                
        except Exception as e:
            print(f"Error executing transcribe_audio: {e}")
            import traceback
            traceback.print_exc()
            return []
