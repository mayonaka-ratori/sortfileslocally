
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import os

from src.core.model_manager import ModelManager

router = APIRouter(prefix="/setup", tags=["setup"])


# Singleton
_model_manager: Optional[ModelManager] = None

def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        from server.dependencies import get_db_manager
        db = get_db_manager()
        custom_dir = db.get_setting("custom_model_dir")
        _model_manager = ModelManager(custom_model_dir=custom_dir)
    return _model_manager


# ------------------------------------------------------------------ #
# Response Models
# ------------------------------------------------------------------ #

class ModelStatusResponse(BaseModel):
    key: str
    name: str
    source: str
    repo_id: str
    is_downloaded: bool
    local_size_mb: float
    estimated_size_mb: int
    local_dir: str

class DownloadProgressResponse(BaseModel):
    model_key: str
    filename: str
    downloaded_bytes: int
    total_bytes: int
    percent: float
    status: str
    error: str

class DownloadRequest(BaseModel):
    model_key: str

class SettingItem(BaseModel):
    key: str
    value: str

class AppSettingsResponse(BaseModel):
    custom_model_dir: Optional[str] = None
    # Future settings can be added here

class SettingUpdateResponse(BaseModel):
    status: str
    key: str
    value: str
    requires_restart: Optional[bool] = False


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #

@router.get("/models", response_model=List[ModelStatusResponse])
def list_models(mm: ModelManager = Depends(get_model_manager)):
    """Return status for all registered AI models."""
    return mm.get_all_status()


@router.get("/models/{key}", response_model=ModelStatusResponse)
def get_model(key: str, mm: ModelManager = Depends(get_model_manager)):
    """Get status for a single model."""
    status = mm.get_model_status(key)
    if not status:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found")
    return status


@router.post("/models/download")
async def download_model(
    req: DownloadRequest,
    background_tasks: BackgroundTasks,
    mm: ModelManager = Depends(get_model_manager),
):
    """Trigger download for a model that is missing."""
    status = mm.get_model_status(req.model_key)
    if not status:
        raise HTTPException(status_code=404, detail=f"Model '{req.model_key}' not found")
    if status["is_downloaded"]:
        return {"message": "Model already downloaded", "status": status}

    def _do_download():
        mm.ensure_model(req.model_key)

    background_tasks.add_task(_do_download)

    return {"message": f"Download started for {req.model_key}"}


@router.get("/models/{key}/progress", response_model=Optional[DownloadProgressResponse])
def get_download_progress(key: str, mm: ModelManager = Depends(get_model_manager)):
    """Check download progress for a model."""
    prog = mm.get_download_progress(key)
    if not prog:
        return None
    return prog


@router.get("/settings", response_model=AppSettingsResponse)
def get_settings():
    """Retrieve all application settings."""
    from server.dependencies import get_db_manager
    db = get_db_manager()
    return {
        "custom_model_dir": db.get_setting("custom_model_dir")
    }


@router.post("/settings", response_model=SettingUpdateResponse)
def update_setting(req: SettingItem):
    """Update a specific application setting."""
    from server.dependencies import get_db_manager
    db = get_db_manager()

    # Input Validation
    if req.key == "custom_model_dir":
        path = req.value.strip()
        if not path:
            # Handle empty as reset to default
            db.set_setting(req.key, "")
        else:
            if not os.path.exists(path):
                raise HTTPException(status_code=422, detail=f"Directory does not exist: {path}")
            if not os.path.isdir(path):
                raise HTTPException(status_code=422, detail=f"Path is not a directory: {path}")
            
            # Check writability
            try:
                test_file = os.path.join(path, ".lcp_write_test")
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Directory is not writable: {str(e)}")
            
            db.set_setting(req.key, path)
            
            # Reset the singleton so next call reloads with new path
            global _model_manager
            _model_manager = None 
            
        return {"status": "success", "key": req.key, "value": req.value, "requires_restart": True}
    else:
        # Generic setting update
        db.set_setting(req.key, req.value)

    return {"status": "success", "key": req.key, "value": req.value, "requires_restart": False}
