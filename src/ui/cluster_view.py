
import streamlit as st
import sqlite3
import os
from ..data.db_manager import DBManager
from ..core.intelligence import FaceClusterer

def render_cluster_view(db_manager: DBManager):
    st.header("👥 Face Clusters")
    
    # Help Guide
    with st.expander("Clustering Settings & Help"):
        st.markdown("""
        **DBSCAN Clustering:** Groups faces based on similarity.
        - **Sensitivity (eps):** Lower is stricter (fewer false positives, but might split same person). Higher is loose.
        - **Min Samples:** Minimum faces required to form a cluster.
        """)
        
        c1, c2 = st.columns(2)
        eps = c1.slider("Sensitivity (eps)", 0.3, 0.9, 0.65, 0.05, help="Distance threshold. 0.6 is strict, 0.8 is loose.")
        min_samples = c2.slider("Min Samples", 2, 10, 3, help="Min faces to be considered a 'person'.")

    # 1. Run/Re-run Clustering Button
    if st.button("Run Face Clustering (DBSCAN)"):
        with st.spinner(f"Clustering faces (eps={eps}, min={min_samples})..."):
            clusterer = FaceClusterer(db_manager)
            n_clusters = clusterer.run_clustering(eps=eps, min_samples=min_samples)
            st.success(f"Clustering Complete! Found {n_clusters} person(s).")
            # Force reload to show results
            st.rerun()

    # 2. Fetch Clusters
    clusters = _fetch_clusters(db_manager)
    
    if not clusters:
        st.info("No clusters found. Try running clustering first.")
        return

    # 3. Display Clusters Grid
    st.subheader("Detected People")
    
    # Select a cluster to drill down
    cluster_ids = sorted(clusters.keys())
    
    cols = st.columns(6)
    for i, cid in enumerate(cluster_ids):
        count = clusters[cid]['count']
        thumb_path = clusters[cid]['thumbnail']
        
        with cols[i % 6]:
            if os.path.exists(thumb_path):
                st.image(thumb_path, width="stretch")
            else:
                st.write("📷")
            
            if st.button(f"Person #{cid}\n({count})", key=f"btn_cluster_{cid}"):
                st.session_state['selected_cluster'] = cid
                st.rerun()

    # 4. Drill Down View
    if 'selected_cluster' in st.session_state:
        cid = st.session_state['selected_cluster']
        st.divider()
        st.subheader(f"Photos of Person #{cid}")
        
        if st.button("Close View"):
            del st.session_state['selected_cluster']
            st.rerun()
            
        file_paths = _fetch_cluster_files(db_manager, cid)
        
        # Display Grid
        grid_cols = st.columns(5)
        for i, path in enumerate(file_paths):
            with grid_cols[i % 5]:
                if os.path.exists(path):
                    st.image(path, width="stretch")
                    st.caption(os.path.basename(path))

def _fetch_clusters(db_manager: DBManager):
    """
    Returns dict: {cluster_id: {'count': N, 'thumbnail': path}}
    """
    conn = sqlite3.connect(db_manager.sqlite_path)
    c = conn.cursor()
    
    # Get counts and one file_id per cluster (for thumbnail)
    # cluster_id -1 is noise (Unknown)
    query = '''
        SELECT f.cluster_id, COUNT(*), MIN(files.file_path)
        FROM faces f
        JOIN files ON f.file_id = files.id
        WHERE f.cluster_id != -1
        GROUP BY f.cluster_id
        ORDER BY COUNT(*) DESC
    '''
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    
    results = {}
    for r in rows:
        results[r[0]] = {
            'count': r[1],
            'thumbnail': r[2]
        }
    return results

def _fetch_cluster_files(db_manager: DBManager, cluster_id: int):
    conn = sqlite3.connect(db_manager.sqlite_path)
    c = conn.cursor()
    
    query = '''
        SELECT DISTINCT files.file_path
        FROM faces f
        JOIN files ON f.file_id = files.id
        WHERE f.cluster_id = ?
        LIMIT 100
    '''
    c.execute(query, (cluster_id,))
    paths = [r[0] for r in c.fetchall()]
    conn.close()
    return paths
