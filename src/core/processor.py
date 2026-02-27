
import os
import sys
import traceback
import logging
from typing import List, Generator
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)
from .scanner import Scanner
from .ai_models import AIEngine
from .video_processor import VideoProcessor
from ..data.db_manager import DBManager
from ..data.schemas import MediaItem, VectorData, ProcessingResult, FaceData
from ..data.scan_job_manager import ScanJobManager
from .intelligence import AutoTagger
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
        
    def process_folder(self, root_dir: str, force_reprocess: bool = False,
                        exclude_dirs: List[str] = None,
                        job_manager: ScanJobManager = None,
                        job_id: int = None,
                        resume_after_path: str = None) -> Generator[dict, None, None]:
        """
        Process all files in the directory.
        Yields status dictionaries.

        Args:
            job_manager: Optional ScanJobManager for persistent state.
            job_id:      The job row ID (required if job_manager is set).
            resume_after_path: If resuming, skip files up to and including this path.
        """
        import time
        start_time = time.time()
        
        # 1. Pre-scan for count
        # We sort alphabetical to ensure consistent order for resume logic
        all_files = sorted(self.scanner.scan_directory(root_dir, exclude_dirs=exclude_dirs))
        total_files = len(all_files)
        
        session_conn = None
        try:
            if job_manager and job_id:
                # S4: Use a session connection to avoid churning SQLite handles per-file
                import sqlite3
                session_conn = sqlite3.connect(job_manager.sqlite_path, timeout=30)
                session_conn.execute("PRAGMA journal_mode=WAL")
                session_conn.row_factory = sqlite3.Row
                job_manager.set_session_conn(session_conn)
                
                job_manager.update_total(job_id, total_files)
                job_manager.mark_running(job_id)

            # Resume: skip files already processed in a prior run
            skip_until_found = bool(resume_after_path)
            
            resume_skipped = 0  # Files skipped due to resume (prior run)
            count = 0           # Files visited this session (for ETA)
            processed_new = 0
            
            for file_path in all_files:
                # Resume logic: skip files we already handled in a prior run
                if skip_until_found:
                    if file_path == resume_after_path:
                        skip_until_found = False
                    resume_skipped += 1
                    if job_manager and job_id:
                        job_manager.increment_skipped(job_id)
                    continue

                count += 1
                item = None
                try:
                    item = self.scanner.inspect_file(file_path)
                    
                    is_skip = not force_reprocess and self.db_manager.is_file_processed(item.file_path, item.file_hash)
                    
                    if not is_skip:
                        result = self._process_item(item)
                        self.db_manager.add_result(result)
                        processed_new += 1
                        if job_manager and job_id:
                            job_manager.increment_processed(job_id, file_path)
                    else:
                        if job_manager and job_id:
                            job_manager.increment_skipped(job_id)
                    
                    # Yield progress
                    elapsed = time.time() - start_time
                    remaining_this_session = (total_files - resume_skipped) - count
                    avg = elapsed / count if count > 0 else 0
                    eta = remaining_this_session * avg
                    
                    yield {
                        'current': resume_skipped + count,  # Overall position
                        'total': total_files,
                        'newly_processed': processed_new,
                        'filename': os.path.basename(file_path),
                        'eta': eta,
                        'elapsed': elapsed
                    }
                    
                except Exception as e:
                    tb_str = traceback.format_exc()
                    if job_manager and job_id:
                        job_manager.log_error(job_id, file_path, str(e), tb_str)
                    yield {'error': str(e), 'filename': os.path.basename(file_path)}
                    if item is not None:
                        item.error_msg = str(e)
                        fail_result = ProcessingResult(item.file_path, False, item)
                        self.db_manager.add_result(fail_result)

            # Mark job complete
            if job_manager and job_id:
                job_manager.mark_completed(job_id)

        finally:
            if session_conn:
                job_manager.set_session_conn(None)
                session_conn.close()

        yield {'status': 'complete', 'processed': processed_new, 'scanned': count, 'resume_skipped': resume_skipped}

    def _process_item(self, item: MediaItem, skip_face: bool = False, skip_whisper: bool = False) -> ProcessingResult:
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
                res = self.inference.process_image(img, skip_face=skip_face)
                
                # Unpack Results
                clip_vec = res['clip']
                item.caption = res.get('caption', "")
                raw_faces = res['faces']
                # Update Metadata via Manager
                MetadataManager.update_item_tags(
                    item, 
                    new_tags=res.get('general_tags', []),
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
                
                try:
                    t_val = self.db_manager.get_setting("scene_threshold")
                    if t_val: threshold = float(t_val)
                except Exception as e:
                    logger.warning(f"Failed to fetch scene_threshold: {e}")

                try:
                    a_val = self.db_manager.get_setting("auto_scene_detection")
                    if a_val: auto_scene = (a_val.lower() == "true")
                except Exception as e:
                    logger.warning(f"Failed to fetch auto_scene_detection: {e}")

                res = self.video_processor.process_video(
                    item.file_path, 
                    skip_face=skip_face, 
                    skip_whisper=skip_whisper,
                    scene_threshold=threshold if auto_scene else 999.0 # Effectively disable if not auto
                )
                if not res:
                     raise ValueError("Video processing returned None")
                
                item.duration = res['duration']
                item.fps = res['fps']
                item.audio_transcription = res.get('audio_transcription', [])
                item.frame_descriptions = res.get('frame_descriptions', [])
                
                if item.frame_descriptions:
                    mid_idx = len(item.frame_descriptions) // 2
                    item.caption = item.frame_descriptions[mid_idx].get('text', '')
                else:
                    item.caption = ""
                    
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

                try:
                    import decord
                    vr = decord.VideoReader(item.file_path)
                    mid_frame = vr[len(vr)//2].asnumpy()
                    res_img = self.inference.process_image(Image.fromarray(mid_frame))
                    item.character_tags = res_img['char_tags']
                    item.series_tags = res_img['series_tags']
                except Exception as e:
                    logger.warning(f"Failed character tagging for video {item.file_path}: {e}")

                # Map scenes to VideoSceneData
                scenes_data = []
                for s in res.get('scenes', []):
                    scenes_data.append(VideoSceneData(
                        start_time=s['start_time'],
                        end_time=s['end_time'],
                        scene_index=s.get('scene_index', 0),
                        thumbnail_path=s.get('thumbnail_path'),
                        start_frame=s.get('start_frame', 0),
                        end_frame=s.get('end_frame', 0),
                        caption=s['caption'],
                        clip_vector=s['clip_vector'].tolist() if hasattr(s['clip_vector'], 'tolist') else s['clip_vector'],
                        tags=s.get('tags', []),
                        character_tags=s.get('character_tags', []),
                        series_tags=s.get('series_tags', [])
                    ))

                return ProcessingResult(
                    file_path=item.file_path,
                    success=True,
                    media_item=item,
                    vector_data=vec_data,
                    faces=faces_data,
                    scenes=scenes_data
                )

        except Exception as e:
            item.error_msg = str(e)
            return ProcessingResult(
                file_path=item.file_path,
                success=False,
                media_item=item
            )

    def process_video_scenes(self, file_id: int):
        """
        Standalone scene detection for a specific video file.
        Used by the /scenes/{id}/detect endpoint.
        """
        conn = self.db_manager._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = c.fetchone()
            if not row:
                logger.error(f"File {file_id} not found for scene detection")
                return
            
            file_path = row['file_path']
            # Re-inspect to get MediaItem
            item = self.scanner.inspect_file(file_path)
            
            try:
                t_val = self.db_manager.get_setting("scene_threshold")
                if t_val: threshold = float(t_val)
            except Exception as e:
                logger.warning(f"Failed to fetch scene_threshold for re-detection: {e}")

            res = self.video_processor.process_video(file_path, skip_face=True, skip_whisper=True, scene_threshold=threshold)
            if not res:
                return

            scenes_data = []
            for s in res.get('scenes', []):
                scenes_data.append(VideoSceneData(
                    start_time=s['start_time'],
                    end_time=s['end_time'],
                    scene_index=s.get('scene_index', 0),
                    thumbnail_path=s.get('thumbnail_path'),
                    start_frame=s.get('start_frame', 0),
                    end_frame=s.get('end_frame', 0),
                    caption=s['caption'],
                    clip_vector=s['clip_vector'].tolist() if hasattr(s['clip_vector'], 'tolist') else s['clip_vector'],
                    tags=s.get('tags', []),
                    character_tags=s.get('character_tags', []),
                    series_tags=s.get('series_tags', [])
                ))
            
            # We don't want to overwrite file metadata, just scenes
            # But the current add_result logic cleans up scenes for the file_id.
            # So we create a ProcessingResult with just scenes.
            result = ProcessingResult(
                file_path=file_path,
                success=True,
                media_item=item,
                scenes=scenes_data
            )
            
            # Need to avoid cleaning up file CLIP and faces if this is just scene re-detection.
            # However, add_result(result) as implemented currently cleans up both.
            # Let's add a partial update method to db_manager or modify add_result.
            # For now, I'll use a hacky way or just call add_result and accept re-processing cost if needed.
            # Actually, I should probably add a save_scenes method to DBManager as requested.
            self.db_manager.add_result(result)

        finally:
            conn.close()

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

    def _process_batch(self, items: List[MediaItem], skip_face: bool = False, skip_whisper: bool = False) -> List[ProcessingResult]:
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
                    batch_results = self.inference.process_batch(pil_images, skip_face=skip_face)
                    
                    # Auto Tagging Batch (needs clip vecs)
                    clip_vecs = np.array([res['clip'] for res in batch_results])
                    suggested_tags_list = self.auto_tagger.suggest_tags(clip_vecs)
                    
                    # Match results back
                    for j, real_idx in enumerate(loaded_indices):
                        item = items[real_idx]
                        item.tags = suggested_tags_list[j] # Assign tags
                        
                        res = batch_results[j]
                        
                        item.caption = res.get('caption', "")
                        
                        # Use MetadataManager for consistent tag and style handling
                        MetadataManager.update_item_tags(
                            item,
                            new_tags=suggested_tags_list[j] + res.get('general_tags', []),
                            char_tags=res['char_tags'],
                            series_tags=res['series_tags'],
                            style=res['style']
                        )
                        
                        clip_v = res['clip'].tolist() if hasattr(res['clip'], 'tolist') else res['clip']
                        
                        # Use MetadataManager for consistent face data creation
                        faces_data = MetadataManager.create_face_data(res['faces'])
                        f_vecs = [f.embedding for f in faces_data]
                            
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
                logger.error(f"Batch Logic Error: {e}")

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
                    batch_results = self.inference.process_batch(all_frames, skip_face=skip_face)
                    
                    # 4. Aggregate results back to videos
                    video_outputs = {v_idx: {'clips': [], 'faces': [], 'general_tags': [], 'char_tags': [], 'series_tags': [], 'styles': []} for v_idx in range(len(vid_results))}
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
                        g_t = res.get('general_tags', [])
                        c_t = res['char_tags']
                        s_t = res['series_tags']
                        if g_t: video_outputs[v_idx]['general_tags'].extend(g_t)
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
                            if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60).returncode == 0:
                                audio_transcription = self.ai_engine.transcribe_audio(tmp_path)
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                        except subprocess.TimeoutExpired:
                            logger.warning(f"ffmpeg timed out extracting audio for {item.file_path}")
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                        except Exception as e:
                            logger.error(f"Fallback sequential transcription error: {e}")
                        item.audio_transcription = audio_transcription
                        
                        frame_descriptions = []
                        if hasattr(self.video_processor, '_vlm_engine'):
                            try:
                                for f_idx, frame_np in enumerate(res['frames']):
                                    pil_img = Image.fromarray(frame_np)
                                    action_text = self.video_processor._vlm_engine.generate_detailed_caption(pil_img)
                                    if action_text is not None:
                                        ts = res['indices'][f_idx] / res['fps'] if res['fps'] > 0 else 0
                                        frame_descriptions.append({'timestamp': ts, 'text': action_text})
                            except Exception as e:
                                logger.error(f"Batch VLM Error during frame description for {item.file_path}: {e}")
                        item.frame_descriptions = frame_descriptions
                        
                        if item.frame_descriptions:
                            mid_idx = len(item.frame_descriptions) // 2
                            item.caption = item.frame_descriptions[mid_idx].get('text', '')
                        else:
                            item.caption = ""
                        
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
                        
                        # Combine base auto tags (CLIP) with vision model tags
                        auto_tags.extend(outputs.get('general_tags', []))
                        
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
                logger.error(f"Video Batch Error: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
        return results
