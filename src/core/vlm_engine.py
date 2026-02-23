import torch
from transformers import AutoProcessor, AutoModelForCausalLM
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
            
            self.model_id = "microsoft/Florence-2-base"
            
            self.model = None
            self.processor = None
            self._loaded = False
            self._load_failures = 0
            self._initialized = True

    def _load_model_unlocked(self):
        """Helper to load model when lock is already acquired by caller."""
        if self._loaded or self._load_failures >= 3:
            return
            
        print(f"Loading VLM model ({self.model_id})...")
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, 
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).eval().to(self.device)
            self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
            self._loaded = True
            self._load_failures = 0
            print("VLM model loaded successfully.")
        except Exception as e:
            self._load_failures += 1
            print(f"Failed to load VLM model (attempt {self._load_failures}/3): {e}")
            self._loaded = False
            if self._load_failures >= 3:
                 print("Max VLM load failures reached. Skipping subsequent attempts.")
            raise e

    def _run_inference(self, image: Image.Image, task_prompt: str, input_text: str = None, max_new_tokens: int = 256) -> str:
        with self._lock:
            if not self._loaded:
                try:
                    self._load_model_unlocked()
                except Exception:
                    pass
                
            if not self._loaded or self.model is None:
                return None

            if input_text is None:
                input_text = task_prompt

            try:
                # Note: keeping single inference as it's safe for 7B models.
                inputs = self.processor(text=input_text, images=image, return_tensors="pt")
                if self.device == "cuda":
                     inputs = {k: v.to(self.device, torch.float16 if v.is_floating_point() and v.dtype == torch.float32 else None) for k, v in inputs.items()}
                else:
                     inputs = {k: v.to(self.device) for k, v in inputs.items()}

                with torch.no_grad():
                    generated_ids = self.model.generate(
                        input_ids=inputs["input_ids"],
                        pixel_values=inputs["pixel_values"],
                        max_new_tokens=max_new_tokens,
                        early_stopping=False,
                        do_sample=False,
                        num_beams=3,
                    )
                generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
                parsed_answer = self.processor.post_process_generation(
                    generated_text, 
                    task=task_prompt, 
                    image_size=(image.width, image.height)
                )
                return str(parsed_answer.get(task_prompt, "No answer"))
            except Exception as e:
                 print(f"Error during VLM inference: {e}")
                 return None

    def ask_image(self, image: Image.Image, prompt: str) -> str:
        """
        Ask a question about a single image.
        """
        task_prompt = "<VQA>"
        full_prompt = task_prompt + prompt
        return self._run_inference(image, task_prompt, full_prompt, max_new_tokens=1024)

    def generate_detailed_caption(self, image: Image.Image) -> str:
        """
        Generate a detailed caption for the image using Florence-2.
        """
        task_prompt = "<MORE_DETAILED_CAPTION>"
        return self._run_inference(image, task_prompt, task_prompt, max_new_tokens=256)

    def unload(self):
        """Free VRAM when not in use."""
        with self._lock:
            if self._loaded:
                 print("Unloading VLM model to free VRAM...")
                 del self.model
                 del self.processor
                 self.model = None
                 self.processor = None
                 self._loaded = False
                 
                 if torch.cuda.is_available():
                     torch.cuda.empty_cache()
                 
    def __del__(self):
        self.unload()
