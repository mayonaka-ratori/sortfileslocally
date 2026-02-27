
import os
import numpy as np
from PIL import Image
import decord
from decord import VideoReader, cpu, gpu
from typing import List, Dict, Any, Union, Tuple
import tempfile
import subprocess
import logging
from .vlm_engine import VLMEngine

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.ai_engine = AIEngine()
        self._vlm_engine = None  # lazy-loaded on first use
        # Determine device for decord
        # Use CPU by default as decord GPU requires custom builds on windows
        self.ctx = decord.cpu(0)

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
                logger.error(f"Parallel Load Error for {path}: {e}")
                return i, None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map returns iterator in order? No, map does.
            # But we want to populate results list by index.
            futures = executor.map(_process_one, enumerate(video_paths))
            
            for idx, res in futures:
                results[idx] = res
                
        return results

    def _detect_scenes(self, video_path: str, threshold: float = 27.0) -> List[Tuple[float, float]]:
        """Detect scenes in video using PySceneDetect."""
        try:
            # Using ContentDetector with configurable threshold.
            scene_list = detect(video_path, ContentDetector(threshold=threshold))
            # scene_list is a list of (start_time, end_time) as FrameTimecode objects
            return [(s[0].get_seconds(), s[1].get_seconds()) for s in scene_list]
        except Exception as e:
            logger.error(f"Scene detection failed for {video_path}: {e}")
            return []

    def process_video(self, video_path: str, skip_face: bool = False, skip_whisper: bool = False, scene_threshold: float = 27.0) -> Dict[str, Any]:
        """
        Process a video file: extract keyframes, compute averaged CLIP embedding, and pool face detections.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        try:
            vr = VideoReader(video_path, ctx=self.ctx)
        except Exception as e:
            logger.error(f"Failed to open video {video_path} with decord: {e}")
            return None

        # Metadata
        fps = vr.get_avg_fps()
        frame_count = len(vr)
        duration = frame_count / fps if fps > 0 else 0
        
        # Extract Audio and Transcribe
        audio_transcription = []
        if not skip_whisper:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                    tmp_audio_path = tmp_audio.name
                
                # Extract audio at 16kHz for whisper
                cmd = ['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', tmp_audio_path]
                # Use subprocess to run ffmpeg, supressing output
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
                if result.returncode == 0:
                    audio_transcription = self.ai_engine.transcribe_audio(tmp_audio_path)
                
                if os.path.exists(tmp_audio_path):
                    os.remove(tmp_audio_path)
            except Exception as e:
                logger.error(f"Failed to process audio for {video_path}: {e}")
                if 'tmp_audio_path' in locals() and os.path.exists(tmp_audio_path):
                    os.remove(tmp_audio_path)
        
        # Extract Frames
        indices = self._get_frame_indices(vr)
        frames = vr.get_batch(indices).asnumpy() # (N, H, W, C)
        
        clip_embeddings = []
        all_faces = []
        frame_descriptions = []
        
        for i, frame_np in enumerate(frames):
            # frame_np is numpy array (RGB or BGR depending on decord?)
            # Decord returns RGB by default.
            
            # 1. CLIP Embedding (Needs PIL RGB)
            pil_img = Image.fromarray(frame_np)
            clip_vec = self.ai_engine.extract_clip_feature(pil_img)
            clip_embeddings.append(clip_vec)
            
            # 2. Face Detection (Needs BGR for InsightFace)
            if not skip_face:
                # Convert RGB to BGR
                frame_bgr = frame_np[:, :, ::-1] 
                faces = self.ai_engine.extract_face_features(frame_bgr)
                
                # Add timestamp info to face
                timestamp = indices[i] / fps if fps > 0 else 0
                for face in faces:
                    face['timestamp'] = timestamp
                    all_faces.append(face)

            # 3. Action Recognition (Florence-2 VLM) - lazy-load VLMEngine
            try:
                if self._vlm_engine is None:
                    from .vlm_engine import VLMEngine as _VLMEngine
                    self._vlm_engine = _VLMEngine()
                action_text = self._vlm_engine.generate_detailed_caption(pil_img)
                if action_text is not None:
                    frame_descriptions.append({
                        'timestamp': timestamp if not skip_face else (indices[i] / fps if fps > 0 else 0),
                        'text': action_text
                    })
            except Exception as e:
                logger.error(f"VLM prediction failed for frame from {video_path}: {e}")

        # Average CLIP embeddings
        if clip_embeddings:
            avg_clip_embedding = np.mean(clip_embeddings, axis=0)
            avg_clip_embedding /= np.linalg.norm(avg_clip_embedding) # Re-normalize
        else:
            avg_clip_embedding = np.zeros(768, dtype=np.float32)

        # --- NEW: Scene Segmentation & Per-Scene Analysis ---
        scenes_data = []
        try:
             scene_boundaries = self._detect_scenes(video_path, threshold=scene_threshold)
             if scene_boundaries:
                 # Limit to reasonable number of scenes to prevent processing indefinitely
                 # e.g. Max 50 scenes per video
                 processed_scenes = scene_boundaries[:50]
                 
                 for idx, (start_s, end_s) in enumerate(processed_scenes):
                     # Calculate middle frame of scene
                     mid_s = (start_s + end_s) / 2
                     mid_frame_idx = int(mid_s * fps)
                     mid_frame_idx = max(0, min(mid_frame_idx, frame_count - 1))
                     
                     # Extract middle frame
                     scene_frame_np = vr[mid_frame_idx].asnumpy()
                     pil_scene = Image.fromarray(scene_frame_np)
                     
                     # 1. CLIP Embedding
                     scene_clip_vec = self.ai_engine.extract_clip_feature(pil_scene)
                     
                     # 2. Caption
                     scene_caption = ""
                     try:
                         if self._vlm_engine is None:
                             from .vlm_engine import VLMEngine as _VLMEngine
                             self._vlm_engine = _VLMEngine()
                         scene_caption = self._vlm_engine.generate_detailed_caption(pil_scene) or ""
                     except Exception as ve:
                         logger.error(f"Scene captioning failed: {ve}")

                     scenes_data.append({
                         'start_time': start_s,
                         'end_time': end_s,
                         'scene_index': idx,
                         'start_frame': int(start_s * fps),
                         'end_frame': int(end_s * fps),
                         'clip_vector': scene_clip_vec,
                         'caption': scene_caption,
                         'tags': [], # For now
                         'character_tags': [],
                         'series_tags': []
                     })
                     
                     # Explicitly delete frame data to free memory
                     del scene_frame_np
                     del pil_scene
                 
                 # Final memory cleanup after all scenes
                 import gc
                 gc.collect()
        except Exception as se:
            logger.error(f"Scene analysis/segmentation failed for {video_path}: {se}")

        return {
            'file_path': video_path,
            'duration': duration,
            'fps': fps,
            'frame_count': frame_count,
            'clip_embedding': avg_clip_embedding, # (768,)
            'faces': all_faces, # List of dicts
            'audio_transcription': audio_transcription,
            'frame_descriptions': frame_descriptions,
            'scenes': scenes_data
        }
