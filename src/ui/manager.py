
import streamlit as st
from ..core.ai_models import AIEngine
from ..core.vlm_engine import VLMEngine
from ..data.db_manager import DBManager
from ..core.processor import Processor

from ..config import Config

class UIManager:
    """Wrapper to handle Streamlit Caching and State."""
    
    @staticmethod
    @st.cache_resource(show_spinner="Loading AI Core...")
    def get_ai_engine() -> AIEngine:
        """Cached singleton for AIEngine (Heavy Load)."""
        return AIEngine()

    @staticmethod
    @st.cache_resource(show_spinner="Loading VLM Engine...")
    def get_vlm_engine() -> VLMEngine:
        """Cached singleton for VLMEngine."""
        return VLMEngine()

    @staticmethod
    @st.cache_resource
    def get_db_manager() -> DBManager:
        """Cached singleton for DBManager."""
        return DBManager(Config.DB_DIR)
    
    @staticmethod
    @st.cache_resource(show_spinner="Loading Processing Pipeline...")
    def get_processor():
        """Cached singleton for Processor."""
        # Processor also defaults to data/db internally, but better to be explicit or let it use config too.
        # Ideally Processor should accept db_manager or db_dir.
        # Processor init arg is db_dir currently.
        return Processor(db_dir=Config.DB_DIR)
    
    @staticmethod
    def initialize_session_state():
        if "scan_active" not in st.session_state:
            st.session_state.scan_active = False
        if "target_dir" not in st.session_state:
            st.session_state.target_dir = ""
