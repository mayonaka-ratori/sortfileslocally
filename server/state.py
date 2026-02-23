from pydantic import BaseModel
from typing import Optional, Dict
import time

class ScanStatus(BaseModel):
    is_active: bool = False
    progress_percent: float = 0.0
    current_file: str = ""
    processed_count: int = 0
    total_files: int = 0
    eta_seconds: float = 0.0
    error: Optional[str] = None
    last_updated: float = 0.0

active_scans: Dict[int, ScanStatus] = {}
