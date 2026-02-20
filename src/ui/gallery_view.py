
import streamlit as st
import os
import sqlite3
from .manager import UIManager
import textwrap
import json

def render_gallery():
    st.header("🔍 Intelligent Gallery")
    
    db_mgr = UIManager.get_db_manager()
    ai_engine = UIManager.get_ai_engine()
    
    # --- Sidebar Filters ---
    st.sidebar.markdown("### 🎭 AI Filters")
    
    # Fetch top characters and series for filters
    conn = sqlite3.connect(db_mgr.sqlite_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get unique characters
    c.execute("SELECT character_tags FROM files WHERE character_tags IS NOT NULL AND character_tags != '[]'")
    char_rows = c.fetchall()
    all_chars = set()
    for r in char_rows:
        all_chars.update(json.loads(r['character_tags']))
    
    selected_char = st.sidebar.selectbox("Filter by Character", ["All"] + sorted(list(all_chars)))
    
    # Get unique series
    c.execute("SELECT series_tags FROM files WHERE series_tags IS NOT NULL AND series_tags != '[]'")
    series_rows = c.fetchall()
    all_series = set()
    for r in series_rows:
        all_series.update(json.loads(r['series_tags']))
    
    selected_series = st.sidebar.selectbox("Filter by Series", ["All"] + sorted(list(all_series)))
    
    selected_media = st.sidebar.selectbox("Media Type", ["All", "Image", "Video"])
    
    # Style Filter (New)
    selected_style = st.sidebar.selectbox("Filter by Style", ["All", "Illustration", "Photo"])
    
    st.sidebar.markdown("---")
    
    # --- Search Bar ---
    search_mode = st.radio("Search Mode", ["Semantic (CLIP)", "Tag Match"], horizontal=True)
    query = st.text_input("Search Collection", placeholder="e.g. 'sunset at beach' (Semantic) or 'hatsune miku' (Tag)")
    
    results = []
    
    # Toggle for untagged
    if st.checkbox("Show Untagged Only"):
        where_clauses = ["is_processed=1", "(character_tags IS NULL OR character_tags = '[]' OR character_tags = '')"]
        # Reset search if conflict? No, combine.
        search_mode = "Tag Match"
        selected_char = "All"
        selected_series = "All"
    
    # Apply Filters and Search
    if search_mode == "Semantic (CLIP)" and query:
        with st.spinner(f"Analyzing search vector..."):
            text_vec = ai_engine.extract_clip_text_feature(query)
            # Fetch all for re-filtering or add to search? DB search is by path.
            # Easiest: get more results and filter in python.
            raw_results = db_mgr.search_similar_images(text_vec, top_k=200) 
            
            # Enrich results with tags
            for path, score in raw_results:
                c.execute("SELECT id, character_tags, series_tags, media_type, tags FROM files WHERE file_path = ?", (path,))
                row = c.fetchone()
                if row:
                    # Filter by media type if needed
                    m_type = row['media_type']
                    if selected_media != "All" and m_type.lower() != selected_media.lower():
                        continue
                        
                    # Filter by Style
                    tags_json = row['tags']
                    tags_list = json.loads(tags_json) if tags_json else []
                    if selected_style != "All":
                        if selected_style.lower() not in tags_list:
                             continue
                        
                    file_id = row['id']
                    chars = json.loads(row['character_tags']) if row['character_tags'] else []
                    series = json.loads(row['series_tags']) if row['series_tags'] else []
                    results.append((file_id, path, score, chars, series))
                    
                    if len(results) >= 60: break
    else:
        # DB Query based search or browse
        if 'where_clauses' not in locals():
            where_clauses = ["is_processed=1"]
            
        params = []
        
        if search_mode == "Tag Match" and query:
            where_clauses.append("(character_tags LIKE ? OR series_tags LIKE ? OR tags LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q])
            
        if selected_char != "All":
            where_clauses.append("character_tags LIKE ?")
            params.append(f'%"{selected_char}"%')
            
        if selected_series != "All":
            where_clauses.append("series_tags LIKE ?")
            params.append(f'%"{selected_series}"%')
            
        if selected_media != "All":
            where_clauses.append("media_type = ?")
            params.append(selected_media.lower())
            
        if selected_style != "All":
            where_clauses.append("tags LIKE ?")
            params.append(f'%"{selected_style.lower()}"%')
            
        query_str = f"SELECT id, file_path, character_tags, series_tags FROM files WHERE {' AND '.join(where_clauses)} ORDER BY created_at DESC LIMIT 60"
        c.execute(query_str, params)
        rows = c.fetchall()
        for r in rows:
            chars = json.loads(r['character_tags']) if r['character_tags'] else []
            series = json.loads(r['series_tags']) if r['series_tags'] else []
            results.append((r['id'], r['file_path'], 0.0, chars, series))
            
    conn.close()

    # --- VLM Chat Panel (Sidebar) ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Chat with Gallery")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Render chat history
    chat_container = st.sidebar.container(height=300)
    with chat_container:
        for msg in st.session_state.chat_history:
            st.chat_message(msg["role"]).write(msg["content"])
            
    # Chat Input
    chat_prompt = st.sidebar.chat_input("Ask about the gallery or a specific image...")
    if chat_prompt:
        st.session_state.chat_history.append({"role": "user", "content": chat_prompt})
        st.sidebar.chat_message("user").write(chat_prompt)
        
        # Decide if asking about a specific image or the whole gallery
        with st.sidebar.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if st.session_state.get('editing_id'):
                    # Context is the selected image
                    try:
                        conn = sqlite3.connect(db_mgr.sqlite_path)
                        conn.row_factory = sqlite3.Row
                        c = conn.cursor()
                        c.execute("SELECT file_path FROM files WHERE id = ?", (st.session_state['editing_id'],))
                        row = c.fetchone()
                        conn.close()
                        
                        if row and os.path.exists(row['file_path']):
                            from PIL import Image
                            vlm_engine = UIManager.get_vlm_engine()
                            
                            file_path = row['file_path']
                            try:
                                # Try opening as image first
                                img = Image.open(file_path).convert("RGB")
                            except Exception:
                                # If it fails, assume it's a video and grab a frame
                                try:
                                    import decord
                                    vr = decord.VideoReader(file_path)
                                    mid_frame = vr[len(vr)//2].asnumpy()
                                    img = Image.fromarray(mid_frame).convert("RGB")
                                except ImportError:
                                    st.error("decord is required for video VQA")
                                    img = None
                                except Exception as e:
                                    st.error(f"Failed to extract frame from video: {e}")
                                    img = None

                            if img is not None:
                                answer = vlm_engine.ask_image(img, chat_prompt)
                                st.write(answer)
                                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        else:
                            st.write("Could not load the selected media for analysis.")
                    except Exception as e:
                        st.error(f"Error analyzing media: {e}")
                else:
                    st.write("Please select an image/video (click 'Edit Tags') to ask a question about it, or use the main search bar to filter the gallery.")
                    st.session_state.chat_history.append({"role": "assistant", "content": "Please select an image/video (click 'Edit Tags') to ask a question about it..."})
    
    # Add a button to clear chat
    if len(st.session_state.chat_history) > 0 and st.sidebar.button("Clear Chat"):
         st.session_state.chat_history = []
         st.rerun()

    if not results:
        st.info("No images found. Try running a scan or changing your query.")
        return

    # 2. Grid Display
    # To handle selection, we need unique keys.
    if 'editing_id' not in st.session_state:
        st.session_state['editing_id'] = None

    cols_per_row = 4
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        batch = results[i:i+cols_per_row]
        
        for col, (fid, path, score, chars, series) in zip(cols, batch):
            with col:
                try:
                    fname = textwrap.shorten(os.path.basename(path), width=20)
                    
                    if os.path.exists(path):
                        # Make image clickable-ish by using button below or styled container?
                        # Streamlit images aren't clickable. We use a button below.
                        st.image(path, width="stretch")
                        
                        btn_label = "✏️ Edit Tags"
                        if not chars and not series:
                            btn_label = "➕ Add Tags"
                            
                        if st.button(btn_label, key=f"edit_{fid}"):
                            st.session_state['editing_id'] = fid
                            st.rerun()
                            
                        # Display tags
                        tag_str = ""
                        if series:
                            tag_str += f"🎬 `{series[0]}`\n"
                        if chars:
                            tag_str += f"👤 `{', '.join(chars[:2])}`"
                        if tag_str:
                            st.caption(tag_str)
                    else:
                        st.warning(f"Missing: {fname}")
                except Exception as e:
                    st.error(f"Error: {fname}")

    # Editor Modal (Expander or just area at top, or Sidebar?)
    # Sidebar is good for editing.
    if st.session_state['editing_id']:
        _render_tag_editor(st.session_state['editing_id'], db_mgr, all_chars, all_series)

def _render_tag_editor(file_id, db_mgr, existing_chars, existing_series):
    conn = sqlite3.connect(db_mgr.sqlite_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT file_path, character_tags, series_tags FROM files WHERE id = ?", (file_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        st.error("File not found in DB.")
        return

    path = row['file_path']
    curr_chars = json.loads(row['character_tags']) if row['character_tags'] else []
    curr_series = json.loads(row['series_tags']) if row['series_tags'] else []

    with st.sidebar:
        st.markdown("### ✏️ Tag Editor")
        st.image(path, caption="Editing...")
        st.caption(os.path.basename(path))
        
        new_chars = st.multiselect("Character Tags", sorted(list(existing_chars)), default=[c for c in curr_chars if c in existing_chars])
        # Allow adding new? Multiselect doesn't support "create" easily in pure Streamlit unless utilizing a combo box logic or just separate text input.
        # Simple fix: Add text input for "New Character".
        add_char = st.text_input("Add New Character")
        
        new_series = st.multiselect("Series Tags", sorted(list(existing_series)), default=[s for s in curr_series if s in existing_series])
        add_series = st.text_input("Add New Series")
        
        if st.button("💾 Save Changes", type="primary"):
            final_chars = new_chars
            if add_char and add_char not in final_chars:
                final_chars.append(add_char)
                
            final_series = new_series
            if add_series and add_series not in final_series:
                final_series.append(add_series)
            
            _update_tags_in_db(file_id, final_chars, final_series, db_mgr)
            st.toast("Tags Saved!")
            st.session_state['editing_id'] = None
            st.rerun()
            
        if st.button("Cancel"):
             st.session_state['editing_id'] = None
             st.rerun()

def _update_tags_in_db(fid, chars, series, db_mgr):
    conn = sqlite3.connect(db_mgr.sqlite_path)
    c = conn.cursor()
    c.execute("UPDATE files SET character_tags = ?, series_tags = ? WHERE id = ?", 
              (json.dumps(chars), json.dumps(series), fid))
    conn.commit()
    conn.close()
