"""
Shared Pydantic response models used across multiple routers.
Import from here to keep response schemas consistent and DRY.
"""
from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class SuccessResponse(BaseModel):
    success: bool = True


class JobStartResponse(BaseModel):
    status: str
    file_id: Optional[int] = None
    job_id: Optional[int] = None
    file_count: Optional[int] = None
    message: Optional[str] = None


class BulkRescanStartResponse(BaseModel):
    status: str
    job_id: int
    file_count: int


class ExportResultResponse(BaseModel):
    success: int
    failed: int
    errors: List[str]


class TagUpdateResponse(BaseModel):
    tags: List[str]
    updated_count: Optional[int] = None
    removed_count: Optional[int] = None


class BulkTagResponse(BaseModel):
    affected_count: int
    action: str
    tags: List[str]
    errors: List[Dict[str, Any]]


class DeleteResultResponse(BaseModel):
    deleted_count: int
    merged_count: Optional[int] = None
    deleted: List[str]
    errors: List[Any]


class SceneDeleteResponse(BaseModel):
    status: str
    count: int


class ChatResponse(BaseModel):
    answer: str


class FiltersResponse(BaseModel):
    characters: List[str]
    series: List[str]


class TagSuggestion(BaseModel):
    tag: str
    count: int


class RenameTagResponse(BaseModel):
    renamed_count: int
    merged_count: int


class DownloadStartResponse(BaseModel):
    message: str


class BackupResponse(BaseModel):
    status: str
    backup_path: str


class ScanStartResponse(BaseModel):
    message: str
    job: Any  # ScanJobResponse — imported in scan.py to avoid circular
