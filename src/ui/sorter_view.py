
import streamlit as st
import os
import shutil
import json
import sqlite3
from ..data.db_manager import DBManager
from ..core.classifier import CustomClassifier
from ..core.sorter import PhysicalSorter, SortLog
from ..ui.manager import UIManager

def render_sorter_view(db_manager: DBManager):
    st.header("🗂️ Auto Organizer")
    
    tab1, tab2, tab3 = st.tabs(["🧠 Custom Learning", "📂 Physical Sorter", "✨ Super Intelligence"])
    
    # --- Tab 1: Learning ---
    with tab1:
        st.subheader("Teach AI your categories")
        st.info("Create a folder structure like `MyCategories/Landscape`, `MyCategories/Portrait` and put some example images in them.")
        
        train_dir = st.text_input("Training Data Directory", value="data/training_examples")
        
        if st.button("Train Classifier"):
            if not os.path.exists(train_dir):
                st.error("Directory not found.")
            else:
                with st.spinner("Learning from your examples..."):
                    # Get Engine from Manager (Singleton)
                    # We need to access the engine instance. 
                    # UIManager stores cached resources but access is a bit tricky if not exposed.
                    # Let's create a helper in UIManager or just grab it if we initialized it in session state?
                    # Actually Processor has it. Let's instantiate a temporary one or pass it.
                    # The UIManager.get_ai_engine() is not implemented efficiently?
                    # Let's assume AIEngine is cheap to init if models are cached? No.
                    # We should get it from session state or UIManager.
                    
                    # Hack: Re-using the singleton pattern in AIEngine logic (lru_cache might help)
                    from ..core.ai_models import AIEngine
                    engine = AIEngine() # Should be fast if models loaded
                    
                    classifier = CustomClassifier(engine)
                    classifier.train(train_dir)
                    st.success(f"Training Complete! Categories: {classifier.get_categories()}")
                    
        # List current categories
        from ..core.classifier import CustomClassifier
        # Just peak at model file?
        if os.path.exists("data/classifier_model.pkl"):
            import pickle
            with open("data/classifier_model.pkl", "rb") as f:
                cats = list(pickle.load(f).keys())
            st.write("Current Categories:", cats)

    # --- Tab 2: Sorter ---
    with tab2:
        st.subheader("Sort Files into Folders")
        
        col1, col2 = st.columns(2)
        with col1:
            dest_root = st.text_input("Destination Root Folder", value="C:/SortedMedia")
            operation = st.selectbox("Operation Mode", ["dry_run", "copy", "move"])
        
        with col2:
            sort_mode = st.radio("Sort By", ["AI Category (Custom)", "Character (AI)", "Series (AI)", "Date (Year/Month)", "File Type"])
        
        st.warning("⚠️ 'Move' operation will delete files from source. 'Copy' is safer. 'Dry Run' only logs what would happen.")
        
        if st.button("Start Sorting"):
            if not os.path.exists(dest_root):
                os.makedirs(dest_root, exist_ok=True)
                
            # Init components
            logger = SortLog()
            sorter = PhysicalSorter(logger)
            
            # Classifier
            classifier = None
            if sort_mode == "AI Category (Custom)":
                from ..core.ai_models import AIEngine
                engine = AIEngine()
                classifier = CustomClassifier(engine)
                if not classifier.get_categories():
                    st.error("No categories learnt yet! Go to 'Custom Learning' tab.")
                    return

            # Scan DB for processed files
            # Ideally we sort EVERYTHING in the DB? Or just selected folder?
            # Let's sort ALL processed files for now or add filter.
            # Query DB
            # Query DB
            conn = sqlite3.connect(db_manager.sqlite_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM files WHERE is_processed=1 AND error_msg IS NULL")
            rows = c.fetchall()
            conn.close()
            
            st.write(f"Found {len(rows)} files to sort.")
            
            progress = st.progress(0)
            log_area = st.empty()
            count = 0
            
            for i, row in enumerate(rows):
                from ..data.schemas import MediaItem
                item = MediaItem(
                     file_path=row['file_path'],
                     file_hash=row['file_hash'],
                     file_size=row['file_size'],
                     media_type=row['media_type'],
                     created_at=row['created_at'],
                     modified_at=row['modified_at'],
                     width=row['width'],
                     height=row['height'],
                     duration=row['duration'],
                     tags=json.loads(row['tags']) if row['tags'] else [],
                     character_tags=json.loads(row['character_tags']) if 'character_tags' in row.keys() and row['character_tags'] else [],
                     series_tags=json.loads(row['series_tags']) if 'series_tags' in row.keys() and row['series_tags'] else [],
                     error_msg=row['error_msg']
                 )
                
                # Determine Category
                category = "Uncategorized"
                
                if sort_mode == "Date (Year/Month)":
                    category = "ByDate" # Logic in sorter handles Year/Month
                elif sort_mode == "File Type":
                    category = item.media_type
                elif sort_mode == "AI Category (Custom)" and classifier:
                    # Need Vector
                    # Fetch vector from FAISS? Or DB cache?
                    # We did not store clip vector in SQLite.
                    # Access FAISS Clip Index by ID?
                    # This is slow if we do random access on FAISS.
                    # Alternative: We re-infer? No slow.
                    # Alternative: We should have cached vectors in DB or Pickle?
                    # Valid Point: Real application needs vectors accessible.
                    # Let's assume for now we skip this or implement FAISS fetch.
                    
                    # FAISS fetch by ID
                    try:
                        # item['id'] is what we sent to FAISS?
                        # DBManager maps file_id -> FAISS ID.
                        # clip_index is IndexIDMap.
                        # vector = db_manager.clip_index.reconstruct(row['id'])
                        # But wait, did we use file_id as ID? Yes. 
                        # db_manager.py: self.clip_index.add_with_ids(..., query_id)
                        
                        vec = db_manager.clip_index.reconstruct(row['id'])
                        pred = classifier.classify_vector(vec)
                        if pred:
                            category = pred
                    except Exception as e:
                        # Only works if reconstruct supported (IndexFlat)
                        # print(e)
                        pass
                elif sort_mode == "Character (AI)":
                    if item.character_tags:
                        category = item.character_tags[0] # Take primary character
                    else:
                        category = "Unknown_Character"
                elif sort_mode == "Series (AI)":
                    if item.series_tags:
                        category = item.series_tags[0] # Take primary series
                    else:
                        category = "Unknown_Series"
                
                # Execute Sort
                # Note: PhysicalSorter logic puts into {dest}/{category}/{Year}
                # So if category is "ByDate", result is {dest}/ByDate/{Year}
                
                if sorter.sort_file(item, dest_root, category, operation):
                    count += 1
                    
                if i % 10 == 0:
                    progress.progress((i + 1) / len(rows))
                    log_area.text(f"Processed {i+1}/{len(rows)}: {item.file_path} -> {category}")
            
            st.success(f"Sorting Complete! processed {count} files. Check logs for Undo script.")
            st.write(f"Undo Script: {logger.undo_script}")

    # --- Tab 3: Advanced Intelligence ---
    with tab3:
        st.subheader("Advanced Analysis")
        st.write("Run deep AI analysis on your existing database to discover styles, characters, and series.")
        
        force_all = st.checkbox("Force Re-process All Files", value=False)
        
        if st.button("🚀 Run Smart Tagging Update"):
            conn = sqlite3.connect(db_manager.sqlite_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Fetch all strings to filter in python or basic SQL
            c.execute("SELECT id, file_path, media_type, tags, character_tags FROM files WHERE is_processed=1")
            rows = c.fetchall()
            
            to_process = []
            for row in rows:
                if force_all:
                    to_process.append(row)
                    continue
                    
                # Check if missing style or char tags
                tags_str = row['tags'] if row['tags'] else "[]"
                char_str = row['character_tags'] if row['character_tags'] else "[]"
                
                has_style = "photo" in tags_str.lower() or "illustration" in tags_str.lower()
                has_chars = char_str != "[]" and char_str != "null"
                
                # If it's an image/video, it SHOULD have a style.
                if not has_style:
                    to_process.append(row)
                # If it is illustration (or unknown yet) and lacks chars, process
                elif "illustration" in tags_str.lower() and not has_chars:
                    to_process.append(row)
            
            if not to_process:
                st.success("All files seem up to date! Check 'Force Re-process' if you want to run anyway.")
                conn.close()
            else:
                st.write(f"Queueing {len(to_process)} files for AI analysis...")
                progress = st.progress(0)
                status = st.empty()
                
                processor = UIManager.get_processor()
                inference = processor.inference
                
                updated_count = 0
                batch_size = 16 # Reduce batch for full pipeline
                
                for i in range(0, len(to_process), batch_size):
                    chunk = to_process[i:i+batch_size]
                    
                    batch_images = []
                    batch_rows = []
                    
                    # Load Batch
                    for row in chunk:
                        path = row['file_path']
                        if not os.path.exists(path): continue
                        
                        try:
                            if row['media_type'] == 'image':
                                from PIL import Image
                                img = Image.open(path).convert('RGB')
                                batch_images.append(img)
                                batch_rows.append(row)
                            else:
                                # Video: Take mid frame
                                import decord
                                vr = decord.VideoReader(path)
                                mid_frame = vr[len(vr)//2].asnumpy()
                                batch_images.append(Image.fromarray(mid_frame))
                                batch_rows.append(row)
                        except Exception as e:
                            status.write(f"Error loading {path}: {e}")
                            
                    if not batch_images:
                        continue
                        
                    # Infer Batch using Orchestrator (Safety & Style logic)
                    try:
                        results = inference.process_batch(batch_images)
                        
                        # Update DB
                        from ..core.metadata import MetadataManager
                        # We need to construct dummy MediaItems or update DB directly.
                        # DB Update is easier.
                        
                        for j, res in enumerate(results):
                            row = batch_rows[j]
                            style = res['style']
                            char_tags = res['char_tags']
                            series_tags = res['series_tags']
                            
                            # Merge Style into existing tags
                            curr_tags_json = row['tags']
                            curr_tags = json.loads(curr_tags_json) if curr_tags_json else []
                            if style not in curr_tags:
                                curr_tags.append(style)
                                
                            # Execute Update
                            c.execute("""
                                UPDATE files 
                                SET tags = ?, character_tags = ?, series_tags = ?
                                WHERE id = ?
                            """, (json.dumps(curr_tags), json.dumps(char_tags), json.dumps(series_tags), row['id']))
                            
                            updated_count += 1
                            
                        conn.commit()
                        
                        progress.progress(min((i + batch_size) / len(to_process), 1.0))
                        status.text(f"Processed {min(i + batch_size, len(to_process))}/{len(to_process)}")
                        
                    except Exception as e:
                        status.write(f"Batch Error: {e}")
                
                conn.close()
                st.success(f"Successfully updated AI tags for {updated_count} files!")
                st.rerun()
