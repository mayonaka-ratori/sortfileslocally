import os

class Config:
    # Database
    DB_DIR = "data/db"
    DB_NAME = "local_curator.db"
    DB_PATH = os.path.join(DB_DIR, DB_NAME)
    
    # Input/Scanning
    DEFAULT_INPUT_DIR = "data/inputs"
    ALLOWED_EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.webp', '.bmp'],
        'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    }
    
    # AI Models
    # Thresholds
    CLUSTERING_EPS = 0.65
    CLUSTERING_MIN_SAMPLES = 4
    
    # Sorter
    SORT_LOG_DIR = "data/logs"
    
    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.DB_DIR, exist_ok=True)
        os.makedirs(cls.DEFAULT_INPUT_DIR, exist_ok=True)
        os.makedirs(cls.SORT_LOG_DIR, exist_ok=True)
