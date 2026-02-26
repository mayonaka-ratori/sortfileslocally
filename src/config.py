import os

class Config:
    # Use environment variable or default APP_DATA_DIR if possible
    # For now, we expect this file to be imported from main.py which sets the context or uses a fallback
    @staticmethod
    def get_base_dir():
        import sys
        import os
        if getattr(sys, 'frozen', False):
            if sys.platform == 'win32':
                base = os.environ.get('APPDATA', os.path.expanduser('~'))
            elif sys.platform == 'darwin':
                base = os.path.expanduser('~/Library/Application Support')
            else:
                base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
            return os.path.join(base, 'LocalCuratorPrime')
        else:
            return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    BASE_DIR = get_base_dir()

    # Database
    DB_DIR = os.path.join(BASE_DIR, "data/db")
    DB_NAME = "local_curator.db"
    DB_PATH = os.path.join(DB_DIR, DB_NAME)
    
    # Input/Scanning
    DEFAULT_INPUT_DIR = os.path.join(BASE_DIR, "data/inputs")
    ALLOWED_EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.webp', '.bmp'],
        'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    }
    
    # AI Models
    # Thresholds
    CLUSTERING_EPS = 0.65
    CLUSTERING_MIN_SAMPLES = 4
    
    # Sorter
    SORT_LOG_DIR = os.path.join(BASE_DIR, "data/logs")
    
    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.DB_DIR, exist_ok=True)
        os.makedirs(cls.DEFAULT_INPUT_DIR, exist_ok=True)
        os.makedirs(cls.SORT_LOG_DIR, exist_ok=True)
