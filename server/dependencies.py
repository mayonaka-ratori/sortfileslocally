
import sys
import os
from functools import lru_cache

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.ai_models import AIEngine
from src.data.db_manager import DBManager
from src.config import Config

@lru_cache()
def get_ai_engine() -> AIEngine:
    """Singleton for AI Engine."""
    print("Initializing AIEngine Singleton...")
    return AIEngine()

@lru_cache()
def get_db_manager() -> DBManager:
    """Singleton for DB Manager."""
    Config.ensure_dirs()
    return DBManager(Config.DB_DIR)

@lru_cache()
def get_processor() -> 'Processor':
    """Singleton for Processor."""
    from src.core.processor import Processor
    # Ensure AI engine is init first to avoid double load if possible (though singleton handles it)
    get_ai_engine()
    return Processor(db_dir=Config.DB_DIR)
