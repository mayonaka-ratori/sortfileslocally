import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image
import threading

class VLMEngine:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VLMEngine, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        with self._lock:
            if self._initialized:
                return

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"VLMEngine initializing on device: {self.device}")
            
            self.model_id = "vikhyatk/moondream2"
            self.revision = "2024-05-20" # Explicit revision for stability
            
            self.model = None
            self.tokenizer = None
            self._loaded = False
            self._initialized = True

    def _load_model(self):
        """Lazy load the model to save VRAM until needed."""
        with self._lock:
            if self._loaded:
                return
                
            print(f"Loading VLM model ({self.model_id})...")
        try:
            # Load with trust_remote_code=True for moondream
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, 
                trust_remote_code=True,
                revision=self.revision,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map={"": self.device}
            )
            self.model.eval()
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
            self._loaded = True
            print("VLM model loaded successfully.")
        except Exception as e:
            print(f"Failed to load VLM model: {e}")
            self._loaded = False
            raise e

    def _load_model_unlocked(self):
        """Helper to load model when lock is already acquired by caller."""
        if self._loaded:
            return
            
        print(f"Loading VLM model ({self.model_id})...")
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, 
                trust_remote_code=True,
                revision=self.revision,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map={"": self.device}
            )
            self.model.eval()
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
            self._loaded = True
            print("VLM model loaded successfully.")
        except Exception as e:
            print(f"Failed to load VLM model: {e}")
            self._loaded = False
            raise e

    def ask_image(self, image: Image.Image, prompt: str) -> str:
        """
        Ask a question about a single image.
        """
        with self._lock:
            if not self._loaded:
                self._load_model_unlocked()
                
            if not self._loaded or self.model is None:
                return "Error: VLM model is not loaded."

            try:
                with torch.no_grad():
                    # Workaround for huggingface transformers missing tokens in some Phi configs
                    # PhiConfig overrides __getattribute__ and throws AttributeError, so we use try/except
                    try:
                        _ = self.model.config.pad_token_id
                    except AttributeError:
                        self.model.config.pad_token_id = self.tokenizer.eos_token_id
                        
                    try:
                        _ = self.model.config.bos_token_id
                    except AttributeError:
                        self.model.config.bos_token_id = self.tokenizer.bos_token_id or self.tokenizer.eos_token_id
                    
                    if hasattr(self.model, "generation_config"):
                        try:
                            _ = self.model.generation_config.pad_token_id
                        except AttributeError:
                            self.model.generation_config.pad_token_id = self.tokenizer.eos_token_id
                            
                        try:
                            _ = self.model.generation_config.bos_token_id
                        except AttributeError:
                            self.model.generation_config.bos_token_id = self.tokenizer.bos_token_id or self.tokenizer.eos_token_id

                    # moondream2 API
                    encoded_image = self.model.encode_image(image)
                    answer = self.model.answer_question(encoded_image, prompt, self.tokenizer)
                    return answer
            except Exception as e:
                 print(f"Error during VLM inference: {e}")
                 return f"Error: {str(e)}"

    def unload(self):
        """Free VRAM when not in use."""
        with self._lock:
            if self._loaded:
                 print("Unloading VLM model to free VRAM...")
                 del self.model
                 del self.tokenizer
                 self.model = None
                 self.tokenizer = None
                 self._loaded = False
                 
                 if torch.cuda.is_available():
                     torch.cuda.empty_cache()
                 
    def __del__(self):
        self.unload()
