import pytest
import os
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_missing_deps():
    from importlib.machinery import ModuleSpec
    mocks = {}
    for mod_name in ["open_clip", "decord", "facenet_pytorch", "insightface", "onnxruntime", "pandas", "cv2", "src.core.ai_models", "src.core.vlm_engine", "src.core.processor"]:
        m = MagicMock()
        m.__spec__ = ModuleSpec(mod_name, None)
        mocks[mod_name] = m
    with patch.dict("sys.modules", mocks):
        yield mocks

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from server.main import app
    return TestClient(app)

@pytest.fixture
def mock_jm():
    from server.routers.scan import _get_job_manager
    from server.main import app
    jm = MagicMock()
    app.dependency_overrides[_get_job_manager] = lambda: jm
    yield jm
    app.dependency_overrides.pop(_get_job_manager, None)

@pytest.fixture
def mock_db():
    from server.dependencies import get_db_manager
    from server.main import app
    db = MagicMock()
    app.dependency_overrides[get_db_manager] = lambda: db
    yield db
    app.dependency_overrides.pop(get_db_manager, None)

def test_resume_scan_by_id_success(mock_jm, mock_db, client):
    # Setup mock job
    mock_job = MagicMock()
    mock_job.id = 123
    mock_job.target_path = "/tmp/test_path"
    mock_job.status = "failed"
    mock_job.force_reprocess = False
    mock_job.last_processed_path = "/tmp/test_path/last.jpg"
    
    # Add fields for _job_to_response
    for field in ["total_files", "processed_count", "skipped_count", "error_count", 
                  "started_at", "updated_at", "completed_at"]:
        setattr(mock_job, field, 0)
    mock_job.current_file = ""
    mock_job.progress_percent = 0.0
    mock_job.eta_seconds = 0.0
    
    mock_jm.get_job.return_value = mock_job
    
    with patch("os.path.exists", return_value=True):
        response = client.post("/scan/resume/123")
        assert response.status_code == 200
        assert response.json()["message"] == "Scan resumed"
        assert response.json()["job"]["id"] == 123

def test_resume_scan_by_id_not_found(mock_jm, client):
    mock_jm.get_job.return_value = None
    response = client.post("/scan/resume/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"

def test_resume_scan_by_id_invalid_status(mock_jm, client):
    mock_job = MagicMock()
    mock_job.status = "completed"
    mock_jm.get_job.return_value = mock_job
    
    response = client.post("/scan/resume/123")
    assert response.status_code == 422
    assert "cannot be resumed" in response.json()["detail"]
