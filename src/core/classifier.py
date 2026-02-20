
import os
import numpy as np
import pickle
import faiss
from typing import List, Dict, Optional
from PIL import Image
from .ai_models import AIEngine
from ..data.schemas import MediaItem

class CustomClassifier:
    """
    Few-shot learner using Nearest Class Mean (Centroid) classifier on CLIP embeddings.
    """
    def __init__(self, ai_engine: AIEngine, model_path: str = "data/classifier_model.pkl"):
        self.ai_engine = ai_engine
        self.model_path = model_path
        self.centroids: Dict[str, np.ndarray] = {} # {'category_name': centroid_vector}
        self.load_model()
        
    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.centroids = pickle.load(f)
                print(f"Loaded classifier with {len(self.centroids)} categories.")
            except Exception as e:
                print(f"Failed to load classifier: {e}")
                self.centroids = {}

    def save_model(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.centroids, f)
            
    def train(self, training_dir: str):
        """
        Scan subdirectories in training_dir. Each subdir name is a category.
        Computes average CLIP vector for images in each subdir.
        """
        print(f"Training from: {training_dir}")
        new_centroids = {}
        
        if not os.path.exists(training_dir):
            print("Training directory not found.")
            return

        cam_subdirs = [d for d in os.listdir(training_dir) if os.path.isdir(os.path.join(training_dir, d))]
        
        for cat in cam_subdirs:
            cat_dir = os.path.join(training_dir, cat)
            vectors = []
            
            # Scan images
            files = [f for f in os.listdir(cat_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            
            if not files:
                continue
                
            print(f"Processing category '{cat}' ({len(files)} images)...")
            
            for f in files:
                path = os.path.join(cat_dir, f)
                try:
                    img = Image.open(path).convert('RGB')
                    vec = self.ai_engine.extract_clip_feature(img)
                    vectors.append(vec)
                except Exception as e:
                    print(f"Error loading {f}: {e}")
            
            if vectors:
                # Compute Centroid
                # Stack: (N, 768)
                mat = np.stack(vectors)
                # Mean
                centroid = np.mean(mat, axis=0) # (768,)
                # Normalize Centroid (Cosine similarity requires normalized vectors)
                centroid /= np.linalg.norm(centroid)
                new_centroids[cat] = centroid.astype(np.float32)
                
        self.centroids.update(new_centroids)
        self.save_model()
        print("Training complete.")
        
    def classify_vector(self, clip_vector: np.ndarray, threshold: float = 0.25) -> Optional[str]:
        """
        Classify a single vector. Returns category name or None if below threshold.
        """
        if not self.centroids:
            return None
            
        best_cat = None
        best_sim = -1.0
        
        # Ensure input is normalized
        vec = clip_vector / np.linalg.norm(clip_vector)
        
        for cat, centroid in self.centroids.items():
            sim = np.dot(vec, centroid)
            if sim > best_sim:
                best_sim = sim
                best_cat = cat
                
        if best_sim >= threshold:
            return best_cat
        return None

    def get_categories(self) -> List[str]:
        return list(self.centroids.keys())
