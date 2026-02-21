
import os
import sys
import traceback
from typing import List, Generator
from PIL import Image
from .scanner import Scanner
from .ai_models import AIEngine
from .video_processor import VideoProcessor
from ..data.db_manager import DBManager
from ..data.schemas import MediaItem, VectorData, ProcessingResult, FaceData
from .intelligence import AutoTagger
from .character_tagger import CharacterTagger
from ..config import Config
from .preprocessing import ImageProcessor
from .inference import InferenceOrchestrator
from .metadata import MetadataManager

class Processor:
    def __init__(self, db_dir=None):
        if db_dir is None:
            db_dir = Config.DB_DIR
            
        self.db_manager = DBManager(db_dir)
        self.scanner = Scanner()
        self.ai_engine = AIEngine()
        self.inference = InferenceOrchestrator(self.ai_engine)
        self.video_processor = VideoProcessor()
        self.auto_tagger = AutoTagger(self.ai_engine)
        # self.char_tagger removed (Migrated to InferenceOrchestrator)
        
    def process_folder(self, root_dir: str, force_reprocess: bool = False, exclude_dirs: List[str] = None) -> Generator[dict, None, None]:
        """
        Process all files in the directory.
        Yields status dictionaries.
        """
        import time
        start_time = time.time()
        
        # 1. Pre-scan for count
        all_files = list(self.scanner.scan_directory(root_dir, exclude_dirs=exclude_dirs))
        total_files = len(all_files)
        
        count = 0
        processed_new = 0
        
        for file_path in all_files:
            count += 1
            try:
                item = self.scanner.inspect_file(file_path)
                
                is_skip = not force_reprocess and self.db_manager.is_file_processed(item.file_path, item.file_hash)
                
                if not is_skip:
                    result = self._process_item(item)
                    self.db_manager.add_result(result)
                    processed_new += 1
                
                # Yield progress
                elapsed = time.time() - start_time
                avg = elapsed / count
                eta = (total_files - count) * avg
                
                yield {
                    'current': count,
                    'total': total_files,
                    'newly_processed': processed_new,
                    'filename': os.path.basename(file_path),
                    'eta': eta,
                    'elapsed': elapsed
                }
                
            except Exception as e:
                yield {'error': str(e), 'filename': os.path.basename(file_path)}
                item.error_msg = str(e)
                fail_result = ProcessingResult(item.file_path, False, item)
                self.db_manager.add_result(fail_result)

        yield {'status': 'complete', 'processed': processed_new, 'scanned': count}

    def _process_item(self, item: MediaItem) -> ProcessingResult:
        """Analyze a single item."""
        
        vec_data = None
        faces_data = []
        
        try:
            if item.media_type == 'image':
                # Open Image via ImageProcessor
                img = ImageProcessor.load_image(item.file_path)
                if img is None:
                     raise ValueError("Image load failed or invalid format")
                
                item.width, item.height = img.size
                
                # Orchestrated Inference
                res = self.inference.process_image(img)
                
                # Unpack Results
                clip_vec = res['clip']
                raw_faces = res['faces']
                # Update Metadata via Manager
                MetadataManager.update_item_tags(
                    item, 
                    char_tags=res['char_tags'], 
                    series_tags=res['series_tags'], 
                    style=res['style']
                )

                # Convert Faces
                faces_data = MetadataManager.create_face_data(raw_faces)
                face_vecs = [f.embedding for f in faces_data]

                vec_data = VectorData(
                    clip_vector=clip_vec,
                    face_vectors=face_vecs
                )
                
                item.is_processed = True

            elif item.media_type == 'video':
                # Use VideoProcessor
                # It returns dictionary
                res = self.video_processor.process_video(item.file_path)
                if not res:
                     raise ValueError("Video processing returned None")
                
                item.duration = res['duration']
                item.fps = res['fps']
                item.audio_transcription = res.get('audio_transcription', [])
                item.frame_descriptions = res.get('frame_descriptions', [])
                item.width = 0 # TODO: Get from decord if needed
                item.height = 0
                item.is_processed = True
                
                face_vecs = []
                for f in res['faces']:
                    face_vecs.append(f['embedding'].tolist())
                    faces_data.append(FaceData(
                        embedding=f['embedding'].tolist(),
                        bbox=f['bbox'],
                        det_score=f['det_score'],
                        kps=f['kps'],
                        timestamp=f.get('timestamp', 0)
                    ))

                vec_data = VectorData(
                    clip_vector=res['clip_embedding'].tolist(),
                    face_vectors=face_vecs
                )
                
                # Auto Tagging (Using video clip embedding)
                tags = self.auto_tagger.suggest_tags(np.array(res['clip_embedding']))[0]
                item.tags = tags

                # Character Tagging for Video (using representative frames or just avg?)
                # For now, let's tag the middle frame or a few? VideoProcessor doesn't return frames yet.
                # Simplest: Since we have the path, let's just do it again for video? 
                # Actually let's modify VideoProcessor to return a keyframe!
                # Or for now, skip video character tagging or do it simple.
                # I'll just skip video for a moment to be safe on memory, or just take first frame.
                try:
                    import decord
                    vr = decord.VideoReader(item.file_path)
                    mid_frame = vr[len(vr)//2].asnumpy()
                    res = self.inference.process_image(Image.fromarray(mid_frame))
                    item.character_tags = res['char_tags']
                    item.series_tags = res['series_tags']
                except:
                    pass

            return ProcessingResult(
                file_path=item.file_path,
                success=True,
                media_item=item,
                vector_data=vec_data,
                faces=faces_data
            )

        except Exception as e:
            item.error_msg = str(e)
            return ProcessingResult(
                file_path=item.file_path,
                success=False,
                media_item=item
            )

    def process_folder_batch(self, root_dir: str, force_reprocess: bool = False, batch_size: int = 32, exclude_dirs: List[str] = None) -> Generator[str, None, None]:
        """
        Batch processing version.
        Accumulates files in buffer and processes them in chunks.
        """
        print(f"Scanning directory (Batch Mode): {root_dir}")
        
        buffer: List[MediaItem] = []
        count = 0
        
        # Generator to yield items from scanner
        file_iter = self.scanner.scan_directory(root_dir, exclude_dirs=exclude_dirs)
        
        try:
            while True:
                # Fill Buffer
                try:
                    while len(buffer) < batch_size:
                        file_path = next(file_iter)
                        
                        # Inspection
                        item = self.scanner.inspect_file(file_path)
                        
                        # DB Check
                        if not force_reprocess and self.db_manager.is_file_processed(item.file_path, item.file_hash):
                            continue
                            
                        buffer.append(item)
                        
                except StopIteration:
                    # End of files
                    pass
                
                if not buffer:
                    break
                    
                # Process Buffer
                yield f"Batch Processing {len(buffer)} files..."
                
                results = self._process_batch(buffer)
                
                # Save Buffer
                self.db_manager.add_results_batch(results)
                
                count += len(buffer)
                buffer.clear()
        
        except Exception as e:
            yield f"Fatal Batch Error: {e}"
            traceback.print_exc()

        yield f"Completed! Processed {count} new files (Batch Mode)."

    def _process_batch(self, items: List[MediaItem]) -> List[ProcessingResult]:
        """Process a list of items using batch inference where possible."""
        
        results = []
        
        # Separate Images and Videos (Video processing is still sequential-ish inside)
        images_to_process = []
        indices_map = {} # map index in 'items' to index in 'images_to_process'
        
        for i, item in enumerate(items):
            if item.media_type == 'image':
                images_to_process.append((i, item))
        
        # 1. Process Images in Batch (CLIP)
        if images_to_process:
            try:
                # Load all PIL images in parallel using threads
                from concurrent.futures import ThreadPoolExecutor
                
                def load_img(idx_item):
                    idx, item = idx_item
                    try:
                        img = Image.open(item.file_path).convert('RGB')
                        item.width, item.height = img.size
                        return idx, img, None
                    except Exception as e:
                        return idx, None, str(e)

                pil_images = []
                loaded_indices = []
                
                # Using max_workers derived from CPU count or a sensible default
                with ThreadPoolExecutor(max_workers=8) as executor:
                    load_results = list(executor.map(load_img, images_to_process))
                
                for idx, img, error in load_results:
                    if error:
                        item = items[idx]
                        item.error_msg = f"Load Error: {error}"
                        results.append(ProcessingResult(item.file_path, False, item))
                    else:
                        pil_images.append(img)
                        loaded_indices.append(idx)

                if pil_images:
                    # Run Orchestrated Inference Batch (CLIP, Faces, Style, Char Tag)
                    batch_results = self.inference.process_batch(pil_images)
                    
                    # Auto Tagging Batch (needs clip vecs)
                    clip_vecs = np.array([res['clip'] for res in batch_results])
                    suggested_tags_list = self.auto_tagger.suggest_tags(clip_vecs)
                    
                    # Match results back
                    for j, real_idx in enumerate(loaded_indices):
                        item = items[real_idx]
                        item.tags = suggested_tags_list[j] # Assign tags
                        
                        res = batch_results[j]
                        
                        # Character Tags
                        item.character_tags = res['char_tags']
                        item.series_tags = res['series_tags']
                        
                        clip_v = res['clip'].tolist() if hasattr(res['clip'], 'tolist') else res['clip']
                        
                        faces_data = []
                        f_vecs = []
                        for f in res['faces']:
                             f_vecs.append(f['embedding'].tolist())
                             faces_data.append(FaceData(
                                embedding=f['embedding'].tolist(),
                                bbox=f['bbox'],
                                det_score=f['det_score'],
                                kps=f['kps']
                            ))
                            
                        vec_data = VectorData(clip_vector=clip_v, face_vectors=f_vecs)
                        item.is_processed = True
                        
                        results.append(ProcessingResult(
                            file_path=item.file_path,
                            success=True,
                            media_item=item,
                            vector_data=vec_data,
                            faces=faces_data
                        ))

            except Exception as e:
                print(f"Batch Logic Error: {e}")
                # Fallback for whole batch fail?
                pass

        # 2. Process Videos (Batch)
        video_indices = [i for i, x in enumerate(items) if x.media_type == 'video']
        if video_indices:
            try:
                # Parallel Load
                vid_paths = [items[i].file_path for i in video_indices]
                vid_results = self.video_processor.extract_frames_parallel(vid_paths, max_workers=4)
                
                # Now we have list of {frames: (N,H,W,C)}
                # We need to flatten ALL frames from ALL videos for Batch Inference?
                # Yes! That's the power of batching.
                # But we need to keep track of which output belongs to which video.
                
                all_frames = [] # List of numpy arrays (H,W,C)
                batch_mapping = [] # (video_idx_in_results, frame_idx) for reconstruction
                
                valid_vid_results = []
                
                current_base = 0
                for v_idx, res in enumerate(vid_results):
                    if not res:
                        item = items[video_indices[v_idx]]
                        item.error_msg = "Video Load Failed"
                        results.append(ProcessingResult(item.file_path, False, item))
                        valid_vid_results.append(None)
                        continue
                        
                    frames = res['frames'] # RGB numpy
                    valid_vid_results.append(res)
                    
                    # Convert to PIL for Taggers
                    for f_i in range(len(frames)):
                        all_frames.append(Image.fromarray(frames[f_i]))
                        batch_mapping.append((v_idx, f_i))
                
                if all_frames:
                    # Batch Inference via Orchestrator
                    batch_results = self.inference.process_batch(all_frames)
                    
                    # 4. Aggregate results back to videos
                    video_outputs = {v_idx: {'clips': [], 'faces': [], 'char_tags': [], 'series_tags': [], 'styles': []} for v_idx in range(len(vid_results))}
                    for global_idx, (v_idx, f_idx) in enumerate(batch_mapping):
                        res = batch_results[global_idx]
                        
                        video_outputs[v_idx]['clips'].append(res['clip'])
                        video_outputs[v_idx]['styles'].append(res['style'])
                        
                        # Add timestamp to faces
                        faces = res['faces']
                        vid_res = valid_vid_results[v_idx]
                        if vid_res:
                            fps = vid_res['fps']
                            ts = vid_res['indices'][f_idx] / fps if fps > 0 else 0
                            for f in faces:
                                f['timestamp'] = ts
                        video_outputs[v_idx]['faces'].extend(faces)
                        
                        # Tags
                        c_t = res['char_tags']
                        s_t = res['series_tags']
                        if c_t: video_outputs[v_idx]['char_tags'].extend(c_t)
                        if s_t: video_outputs[v_idx]['series_tags'].extend(s_t)
                        
                        # Add timestamp to faces
                    
                    # Finalize each video
                    for v_idx, res in enumerate(valid_vid_results):
                        if not res: continue
                        
                        item = items[video_indices[v_idx]]
                        item.duration = res['duration']
                        item.fps = res['fps']
                        item.width = 0 
                        item.height = 0
                        item.is_processed = True
                        
                        # Sequential fallback for Video Understanding in Batch Mode
                        from .video_processor import VideoProcessor
                        import tempfile
                        import subprocess
                        import os
                        audio_transcription = []
                        try:
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                                tmp_path = tmp_audio.name
                            cmd = ['ffmpeg', '-y', '-i', item.file_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', tmp_path]
                            if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                                audio_transcription = self.ai_engine.transcribe_audio(tmp_path)
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                        except:
                            pass
                        item.audio_transcription = audio_transcription
                        
                        frame_descriptions = []
                        if hasattr(self.video_processor, 'vlm_engine'):
                            try:
                                for f_idx, frame_np in enumerate(res['frames']):
                                    pil_img = Image.fromarray(frame_np)
                                    action_text = self.video_processor.vlm_engine.ask_image(pil_img, "Describe the main action or subject in this image in one short sentence.")
                                    if not action_text.startswith("Error"):
                                        ts = res['indices'][f_idx] / res['fps'] if res['fps'] > 0 else 0
                                        frame_descriptions.append({'timestamp': ts, 'text': action_text})
                            except Exception as e:
                                print(f"Batch VLM Error: {e}")
                        item.frame_descriptions = frame_descriptions
                        
                        outputs = video_outputs[v_idx]
                        
                        # Determine majority style for video
                        styles = outputs['styles']
                        if styles:
                            from collections import Counter
                            main_style = Counter(styles).most_common(1)[0][0]
                        else:
                            main_style = "illustration"

                        # Auto Tag (on avg clip)
                        clips = np.array(outputs['clips'])
                        if len(clips) > 0:
                            avg_clip = np.mean(clips, axis=0)
                            avg_clip /= np.linalg.norm(avg_clip)
                        else:
                            avg_clip = np.zeros(768)
                            
                        auto_tags = self.auto_tagger.suggest_tags(np.array([avg_clip]))[0]
                        
                        # Update Metadata
                        MetadataManager.update_item_tags(
                            item,
                            new_tags=auto_tags,
                            char_tags=outputs['char_tags'],
                            series_tags=outputs['series_tags'],
                            style=main_style
                        )
                        
                        # Faces
                        item_faces = MetadataManager.create_face_data(outputs['faces'])
                        f_vecs = [f.embedding for f in item_faces]
                            
                        vec_data = VectorData(clip_vector=avg_clip.tolist(), face_vectors=f_vecs)
                        
                        results.append(ProcessingResult(
                            file_path=item.file_path,
                            success=True,
                            media_item=item,
                            vector_data=vec_data,
                            faces=item_faces
                        ))

            except Exception as e:
                print(f"Video Batch Error: {e}")
                # Fallback?
                import traceback
                traceback.print_exc()
                pass
            
        return results
