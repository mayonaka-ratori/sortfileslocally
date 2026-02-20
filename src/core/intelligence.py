
import numpy as np
from sklearn.cluster import DBSCAN
import sqlite3
import faiss
from typing import List, Dict

from .ai_models import AIEngine
from ..data.db_manager import DBManager

DEFAULT_TAGS = [
    "portrait", "group photo", "landscape", "cityscape", "night view", 
    "sky", "sunset", "forest", "flower", "animal", "cat", "dog", "bird",
    "food", "drink", "indoor", "room", "building", "vehicle", "car",
    "document", "screenshot", "meme", "text", 
    "anime", "illustration", "sketch", "painting", "candid", "selfie"
]

class AutoTagger:
    def __init__(self, ai_engine: AIEngine, tags: List[str] = DEFAULT_TAGS):
        self.ai_engine = ai_engine
        self.tags = tags
        self.tag_vectors = self._precompute_tags()
        
    def _precompute_tags(self) -> np.ndarray:
        print("Precomputing Auto-Tagging vectors...")
        vecs = []
        for t in self.tags:
            # Use "a photo of {tag}" for better context
            text_emb = self.ai_engine.extract_clip_text_feature(f"a photo of {t}")
            vecs.append(text_emb)
        return np.array(vecs) # (N, 768)

    def suggest_tags(self, image_vectors: np.ndarray, top_k: int = 5, threshold: float = 0.20) -> List[List[str]]:
        """
        Batch suggestion.
        image_vectors: (B, 768)
        Returns: List of tag lists.
        """
        # Ensure 2D
        if image_vectors.ndim == 1:
            image_vectors = image_vectors[np.newaxis, :]
            
        # Calc similarity: (B, 768) @ (N, 768).T = (B, N)
        scores = image_vectors @ self.tag_vectors.T
        
        batch_tags = []
        for i in range(len(image_vectors)):
            # Get top K indices
            inds = np.argsort(scores[i])[::-1]
            
            suggested = []
            for idx in inds[:top_k]:
                score = scores[i][idx]
                if score >= threshold:
                    suggested.append(self.tags[idx])
            batch_tags.append(suggested)
            
        return batch_tags

class FaceClusterer:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        
    def run_clustering(self, eps: float = 0.75, min_samples: int = 3):
        """
        Run DBSCAN on all faces.
        eps: Distance threshold (Euclidean on normalized vectors)
             Cosine Sim s corresponds to Dist d = sqrt(2(1-s))
             s=0.7 -> d=0.77
             s=0.6 -> d=0.89
             eps=0.75 means similarity > ~0.72
        """
        print("Running Face Clustering (DBSCAN)...")
        index = self.db_manager.face_index
        ntotal = index.ntotal
        
        if ntotal == 0:
            print("No faces to cluster.")
            return 0

        vectors = None
        ids = None

        try:
            # Access underlying index (IndexFlat)
            # We iterate 0..ntotal-1 (offsets)
            sub_index = index.index
            
            vectors = []
            for i in range(ntotal):
                 vec = sub_index.reconstruct(i)
                 vectors.append(vec)
            vectors = np.array(vectors)
            
            # Retrieve IDs corresponding to these offsets
            ids = faiss.vector_to_array(index.id_map)
            
        except Exception as e:
            print(f"Failed to fetch vectors from FAISS: {e}")
            return 0

        # DBSCAN
        # n_jobs=-1 uses all cores
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean', n_jobs=-1)
        labels = clustering.fit_predict(vectors)
        
        # Update DB
        conn = sqlite3.connect(self.db_manager.sqlite_path)
        c = conn.cursor()
        
        updates = []
        for id_val, label in zip(ids, labels):
            # labels are numpy.int64, convert to int
            cluster_id = int(label)
            row_id = int(id_val)
            updates.append((cluster_id, row_id))
        
        c.executemany('UPDATE faces SET cluster_id = ? WHERE id = ?', updates)
        conn.commit()
        conn.close()
        
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"Clustering complete. Found {n_clusters} clusters (excluding noise).")
        return n_clusters
