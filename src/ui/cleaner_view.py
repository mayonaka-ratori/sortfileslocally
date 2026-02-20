
import streamlit as st
import os
import shutil
from ..data.db_manager import DBManager
from ..core.deduplication import Deduplicator

def render_cleaner_view(db_manager: DBManager):
    st.header("🧹 Media Cleaner")
    st.info("Find and remove duplicate media. Recommended actions highlight the lower quality version.")
    
    # Initialize Deduplicator
    deduper = Deduplicator(db_manager)
    
    # State for scan results
    if 'duplicates' not in st.session_state:
        st.session_state['duplicates'] = []
    
    if st.button("Scan for Duplicates"):
        with st.spinner("Scanning... this may take a while"):
            pairs = deduper.find_duplicates(threshold_img=0.95, threshold_vid=0.98)
            st.session_state['duplicates'] = pairs
            if not pairs:
                st.success("No duplicates found!")
            else:
                st.success(f"Found {len(pairs)} duplicate pairs.")
    
    pairs = st.session_state['duplicates']
    
    if not pairs:
        return

    # Selection State: { index: 'A' or 'B' or None }
    if 'cleaner_selections' not in st.session_state:
        st.session_state['cleaner_selections'] = {}
        
    selections = st.session_state['cleaner_selections']

    # Bulk Action Bar
    c_bulk1, c_bulk2 = st.columns([3, 1])
    with c_bulk1:
        st.write(f"Showing top 50 pairs. Select items to delete below.")
    with c_bulk2:
        if st.button("🗑️ Delete Selected"):
            new_pairs = []
            deleted_count = 0
            
            for i, pair in enumerate(pairs):
                sel = selections.get(i)
                if sel == 'A':
                    _delete_file(pair.file_a.file_path, db_manager)
                    deleted_count += 1
                elif sel == 'B':
                    _delete_file(pair.file_b.file_path, db_manager)
                    deleted_count += 1
                else:
                    new_pairs.append(pair)
            
            st.session_state['duplicates'] = new_pairs
            st.session_state['cleaner_selections'] = {} # Reset
            st.success(f"Deleted {deleted_count} files.")
            st.rerun()

    st.divider()

    # List pairs (paginate 50)
    for i, pair in enumerate(pairs[:50]):
        c1, c2, c3 = st.columns([1, 0.2, 1])
        
        # Determine current selection
        current_sel = selections.get(i)
        
        # Left (A)
        with c1:
            bg_color = "rgba(255,0,0,0.1)" if current_sel == 'A' else "transparent"
            st.markdown(f'<div style="background-color:{bg_color}; padding:5px; border-radius:5px;">', unsafe_allow_html=True)
            
            st.caption(f"File A: {os.path.basename(pair.file_a.file_path)}")
            # Show media
            if os.path.exists(pair.file_a.file_path):
                if pair.file_a.media_type == 'image':
                    st.image(pair.file_a.file_path, width=200) # Smaller thumb
                elif pair.file_a.media_type == 'video':
                    st.video(pair.file_a.file_path)
            else:
                st.error("Missing")
            
            st.caption(f"{pair.file_a.width}x{pair.file_a.height} | {pair.file_a.file_size//1024}KB")
            
            # Checkbox equivalent (Button effectively)
            if st.button("Mark Delete A", key=f"del_a_{i}", type="primary" if current_sel=='A' else "secondary"):
                if current_sel == 'A':
                    del selections[i]
                else:
                    selections[i] = 'A'
                st.rerun()
                
            if pair.recommended_action == 'keep_b':
               st.caption("❌ Recommended to Delete")
               
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Center
        with c2:
            st.write(f"Sim: {pair.similarity:.3f}")
            st.write("⬅️ vs ➡️")

        # Right (B)
        with c3:
            bg_color = "rgba(255,0,0,0.1)" if current_sel == 'B' else "transparent"
            st.markdown(f'<div style="background-color:{bg_color}; padding:5px; border-radius:5px;">', unsafe_allow_html=True)

            st.caption(f"File B: {os.path.basename(pair.file_b.file_path)}")
            if os.path.exists(pair.file_b.file_path):
                if pair.file_b.media_type == 'image':
                    st.image(pair.file_b.file_path, width=200)
                elif pair.file_b.media_type == 'video':
                    st.video(pair.file_b.file_path)
            else:
                st.error("Missing")
                
            st.caption(f"{pair.file_b.width}x{pair.file_b.height} | {pair.file_b.file_size//1024}KB")

            if st.button("Mark Delete B", key=f"del_b_{i}", type="primary" if current_sel=='B' else "secondary"):
                if current_sel == 'B':
                    del selections[i]
                else:
                    selections[i] = 'B'
                st.rerun()

            if pair.recommended_action == 'keep_a':
               st.caption("❌ Recommended to Delete")
            st.markdown('</div>', unsafe_allow_html=True)
                
        st.divider()

def _delete_file(path: str, db_manager: DBManager):
    """
    Safe delete: Move to .trash folder
    Update DB to mark as deleted/remove.
    """
    if not os.path.exists(path):
        return

    trash_dir = os.path.join(os.path.dirname(path), ".trash")
    os.makedirs(trash_dir, exist_ok=True)
    
    try:
        fname = os.path.basename(path)
        dest = os.path.join(trash_dir, fname)
        # Handle collision
        if os.path.exists(dest):
            base, ext = os.path.splitext(fname)
            import time
            dest = os.path.join(trash_dir, f"{base}_{int(time.time())}{ext}")
            
        shutil.move(path, dest)
        
        # Remove from DB
        # Actually it's complex to remove from FAISS without rebuild or ID map meddling (remove_ids is slow).
        # Easiest: Mark as "processed=0" or delete row in SQLite.
        # But Vector persists. 
        # For now, just remove from SQLite 'files' table so it doesn't show up in search.
        conn = sqlite3.connect(db_manager.sqlite_path)
        c = conn.cursor()
        c.execute("DELETE FROM files WHERE file_path = ?", (path,))
        conn.commit()
        conn.close()
        
    except Exception as e:
        st.error(f"Failed to delete {path}: {e}")

def _remove_pair_by_index(index):
    if 'duplicates' in st.session_state:
        st.session_state['duplicates'].pop(index)
