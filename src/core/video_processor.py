
import os
import numpy as np
from PIL import Image
import decord
from decord import VideoReader, cpu, gpu
from typing import List, Dict, Any, Union
from .ai_models import AIEngine

class VideoProcessor:
    def __init__(self):
        self.ai_engine = AIEngine()
        # Determine device for decord
        # Try to use GPU if available
        try:
            # Test if GPU context works
            _ = decord.gpu(0)
            self.ctx = decord.gpu(0)
            print("VideoProcessor: Using GPU for decoding.")
        except Exception:
            self.ctx = decord.cpu(0)
            print("VideoProcessor: GPU decoding not available, using CPU.")

    def _get_frame_indices(self, vr: VideoReader) -> List[int]:
        """
        Calculate indices for Start+10s, 25%, Middle, 75%, End-10s.
        """
        frame_count = len(vr)
        fps = vr.get_avg_fps()
        
        indices = []
        
        # Points: Start+10s, 25%, 50%, 75%, End-10s
        ten_seconds = int(10 * fps)
        
        candidates = [
            ten_seconds if frame_count > ten_seconds else 0,
            frame_count * 1 // 4,
            frame_count * 2 // 4,
            frame_count * 3 // 4,
            frame_count - ten_seconds if frame_count > ten_seconds else frame_count - 1
        ]
        
        # Ensure unique and sorted, and within bounds
        raw_indices = sorted(list(set(candidates)))
        valid_indices = [max(0, min(int(i), frame_count - 1)) for i in raw_indices]
        
        return valid_indices
        
    def extract_frames_parallel(self, video_paths: List[str], max_workers=4) -> List[Dict[str, Any]]:
        """
        Extract frames from multiple videos in parallel.
        Returns list of results: [{'path': p, 'frames': np_array(N,H,W,C), 'indices': [], 'fps': f}, ...]
        Result can be None if failed.
        """
        from concurrent.futures import ThreadPoolExecutor
        
        results = [None] * len(video_paths)
        
        def _process_one(idx_path):
            i, path = idx_path
            try:
                if not os.path.exists(path):
                    return i, None
                
                # Use CPU context for parallel readers to avoid GPU contention/OOM in threads?
                # Actually Decord is efficient. Let's try self.ctx (GPU) but handle OOM.
                # Just use CPU for safety in threads if GPU is small.
                # Let's enforce CPU for parallel extraction to be safe, or just self.ctx.
                # Safe bet: separate context per thread if using GPU? No, allow shared.
                
                vr = VideoReader(path, ctx=self.ctx)
                
                # Metadata
                fps = vr.get_avg_fps()
                frame_count = len(vr)
                
                # Indices
                idx_list = self._get_frame_indices(vr)
                frames = vr.get_batch(idx_list).asnumpy() # (N,H,W,C)
                
                return i, {
                    'path': path,
                    'frames': frames, # RGB
                    'indices': idx_list,
                    'fps': fps,
                    'duration': frame_count / fps if fps > 0 else 0
                }
            except Exception as e:
                print(f"Parallel Load Error {path}: {e}")
                return i, None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map returns iterator in order? No, map does.
            # But we want to populate results list by index.
            futures = executor.map(_process_one, enumerate(video_paths))
            
            for idx, res in futures:
                results[idx] = res
                
        return results

    def process_video(self, video_path: str) -> Dict[str, Any]:
        """
        Process a video file: extract keyframes, compute averaged CLIP embedding, and pool face detections.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        try:
            vr = VideoReader(video_path, ctx=self.ctx)
        except Exception as e:
            print(f"Failed to open video {video_path}: {e}")
            return None

        # Metadata
        fps = vr.get_avg_fps()
        frame_count = len(vr)
        duration = frame_count / fps if fps > 0 else 0
        
        # Extract Frames
        indices = self._get_frame_indices(vr)
        frames = vr.get_batch(indices).asnumpy() # (N, H, W, C)
        
        clip_embeddings = []
        all_faces = []
        
        for i, frame_np in enumerate(frames):
            # frame_np is numpy array (RGB or BGR depending on decord?)
            # Decord returns RGB by default.
            
            # 1. CLIP Embedding (Needs PIL RGB)
            pil_img = Image.fromarray(frame_np)
            clip_vec = self.ai_engine.extract_clip_feature(pil_img)
            clip_embeddings.append(clip_vec)
            
            # 2. Face Detection (Needs BGR for InsightFace)
            # Convert RGB to BGR
            frame_bgr = frame_np[:, :, ::-1] 
            faces = self.ai_engine.extract_face_features(frame_bgr)
            
            # Add timestamp info to face
            timestamp = indices[i] / fps if fps > 0 else 0
            for face in faces:
                face['timestamp'] = timestamp
                all_faces.append(face)

        # Average CLIP embeddings
        if clip_embeddings:
            avg_clip_embedding = np.mean(clip_embeddings, axis=0)
            avg_clip_embedding /= np.linalg.norm(avg_clip_embedding) # Re-normalize
        else:
            avg_clip_embedding = np.zeros(768, dtype=np.float32)

        return {
            'file_path': video_path,
            'duration': duration,
            'fps': fps,
            'frame_count': frame_count,
            'clip_embedding': avg_clip_embedding, # (768,)
            'faces': all_faces # List of dicts
        }
