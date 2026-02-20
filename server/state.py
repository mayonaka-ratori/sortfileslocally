
from pydantic import BaseModel
from typing import Optional

class ScanStatus(BaseModel):
    is_active: bool = False
    progress_percent: float = 0.0
    current_file: str = ""
    processed_count: int = 0
    total_files: int = 0
    eta_seconds: float = 0.0
    error: Optional[str] = None

# Global state
# In production, use Redis or DB for persistence across workers.
# For single worker Uvicorn, this global variable is fine.
current_status = ScanStatus()
