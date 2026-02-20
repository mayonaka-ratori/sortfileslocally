
import streamlit as st
import os
from .manager import UIManager
from ..config import Config

def render_sidebar():
    st.sidebar.title("LocalCurator Prime")
    st.sidebar.markdown("---")
    
    # 1. Target Directory Selection
    st.sidebar.header("📁 Control Panel")
    
    default_dir = os.path.abspath(Config.DEFAULT_INPUT_DIR) # Default
    target_dir = st.sidebar.text_input(
        "Target Folder", 
        value=default_dir,
        help="Path to the folder you want to organize."
    )
    st.session_state.target_dir = target_dir
    
    exclude_input = st.sidebar.text_input(
        "Exclude Folders (comma separated)",
        value="Sorted, .trash",
        help="Folder names or full paths to skip during scan."
    )
    
    # 2. Status Board
    db_mgr = UIManager.get_db_manager()
    try:
        # Quick stats from DB
        import sqlite3
        conn = sqlite3.connect(db_mgr.sqlite_path)
        c = conn.cursor()
        c.execute("SELECT count(*), sum(case when is_processed=1 then 1 else 0 end) FROM files")
        total, processed = c.fetchone()
        conn.close()
    except:
        total, processed = 0, 0

    st.sidebar.metric("Total Files", total)
    st.sidebar.metric("Processed", processed, delta=processed - total if total>0 else 0)

    # 3. Action Buttons
    st.sidebar.markdown("---")
    if st.sidebar.button("🚀 Start Scanning", type="primary", disabled=st.session_state.scan_active):
        excludes = [x.strip() for x in exclude_input.split(',')] if exclude_input else []
        perform_scan(target_dir, excludes)

    if st.sidebar.button("🧹 Cleanup Database", help="Remove entries for files that no longer exist on disk"):
        cleanup_database(db_mgr)

def cleanup_database(db_mgr):
    with st.status("Cleaning up database...") as status:
        import sqlite3
        conn = sqlite3.connect(db_mgr.sqlite_path)
        c = conn.cursor()
        c.execute("SELECT id, file_path FROM files")
        rows = c.fetchall()
        
        to_delete = []
        for fid, path in rows:
            if not os.path.exists(path):
                to_delete.append(fid)
        
        if to_delete:
            # Delete in chunks
            for i in range(0, len(to_delete), 500):
                chunk = to_delete[i:i+500]
                c.execute(f"DELETE FROM files WHERE id IN ({','.join(['?']*len(chunk))})", chunk)
                # Note: This doesn't remove from FAISS but prevents display.
            conn.commit()
            status.update(label=f"Done! Removed {len(to_delete)} stale entries.", state="complete")
        else:
            status.update(label="Database is already clean.", state="complete")
        conn.close()
    st.rerun()

def perform_scan(root_dir, exclude_dirs=None):
    if not os.path.exists(root_dir):
        st.sidebar.error("❌ Directory not found!")
        return

    st.session_state.scan_active = True
    processor = UIManager.get_processor()
    
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()
    
    # Run Sync for now (Streamlit is single threaded usually unless handled)
    # Ideally should be async, but for MVP sync is okay with yield.
    try:
        with st.status("🔍 Initializing Scan...", expanded=True) as status:
            # If exclude dirs are relative names (e.g. "Sorted"), resolve them against root?
            # Or pass as raw strings to scanner (which does startsWith check on abs path)
            # Better to resolve relative names to absolute paths IF they are just names in root.
            resolved_excludes = []
            if exclude_dirs:
                for ex in exclude_dirs:
                    if os.path.isabs(ex):
                        resolved_excludes.append(ex)
                    else:
                        # Assume relative to root AND general name match? 
                        # Scanner logic implemented startsWith absolute check.
                        # So we should append absolute path of root/ex
                        resolved_excludes.append(os.path.abspath(os.path.join(root_dir, ex)))
            
            for data in processor.process_folder(root_dir, exclude_dirs=resolved_excludes):
                if 'status' in data and data['status'] == 'complete':
                    status.update(label=f"✅ Scan Complete! ({data['processed']} new files)", state="complete", expanded=False)
                elif 'error' in data:
                    status.write(f"❌ Error ({data['filename']}): {data['error']}")
                else:
                    # Progress Update
                    curr = data['current']
                    total = data['total']
                    eta = data['eta']
                    
                    # Update Progress Bar
                    progress_bar.progress(curr / total)
                    
                    # Format ETA
                    mins, secs = divmod(int(eta), 60)
                    eta_str = f"{mins:02d}:{secs:02d}"
                    
                    status_text.markdown(f"""
                    **Progress:** `{curr}/{total}` files  
                    **Newly Processed:** `{data['newly_processed']}`  
                    **Estim. Time Remaining:** `{eta_str}`  
                    *Current: {data['filename']}*
                    """)
            
        st.sidebar.success("Done!")
        st.rerun() 
        
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
    finally:
        st.session_state.scan_active = False
        progress_bar.empty()
