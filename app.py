
import streamlit as st
import os
import sys

# Ensure src is in path
sys.path.append(os.path.abspath("src"))

from src.ui.manager import UIManager
from src.ui.sidebar import render_sidebar
from src.ui.gallery_view import render_gallery
from src.ui.cluster_view import render_cluster_view
from src.ui.cleaner_view import render_cleaner_view
from src.ui.sorter_view import render_sorter_view
from src.config import Config

# Ensure directories
Config.ensure_dirs()

# --- Page Config ---
st.set_page_config(
    page_title="LocalCurator Prime",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Init ---
UIManager.initialize_session_state()

# --- Main Layout ---
def main():
    # Sidebar
    render_sidebar()
    
    # Navigation
    with st.sidebar:
        st.divider()
        view_mode = st.radio(
            "View Mode", 
            ["Gallery", "Face Clusters", "Cleaner", "Auto Organizer"],
            index=0
        )
    
    # Get DB Manager (Cached)
    db_manager = UIManager.get_db_manager()

    # Main Content
    if view_mode == "Gallery":
        render_gallery()
    elif view_mode == "Face Clusters":
        render_cluster_view(db_manager)
    elif view_mode == "Cleaner":
        render_cleaner_view(db_manager)
    elif view_mode == "Auto Organizer":
        render_sorter_view(db_manager)

if __name__ == "__main__":
    main()
