import pytest
import os
import shutil
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
def mock_db():
    from server.dependencies import get_db_manager
    from server.main import app
    db = MagicMock()
    app.dependency_overrides[get_db_manager] = lambda: db
    yield db
    app.dependency_overrides.pop(get_db_manager, None)

@pytest.fixture
def mock_processor():
    from server.dependencies import get_processor
    from server.main import app
    proc = MagicMock()
    app.dependency_overrides[get_processor] = lambda: proc
    yield proc
    app.dependency_overrides.pop(get_processor, None)

def test_get_demo_status(client, mock_db):
    # Case: demo mode OFF
    mock_db.get_setting.return_value = "0"
    response = client.get("/demo/status")
    assert response.status_code == 200
    assert response.json() == {"demo_mode": False}

    # Case: demo mode ON
    mock_db.get_setting.return_value = "1"
    response = client.get("/demo/status")
    assert response.status_code == 200
    assert response.json() == {"demo_mode": True}

@patch("os.path.exists")
@patch("os.makedirs")
@patch("os.listdir")
@patch("shutil.rmtree")
@patch("shutil.copy2")
def test_start_demo(mock_copy, mock_rmtree, mock_listdir, mock_makedirs, mock_exists, mock_db, mock_processor, client):
    from src.data.scan_job_manager import ScanJob
    from server.routers.scan import _get_job_manager
    from server.main import app
    
    # Setup mocks
    mock_exists.return_value = True
    mock_listdir.return_value = ["test1.jpg", "test2.jpg", "other.txt"]
    
    mock_jm = MagicMock()
    mock_job = MagicMock(spec=ScanJob)
    mock_job.id = 123
    mock_job.target_path = "data/demo_library"
    mock_job.status = "running"
    
    for field in ["total_files", "processed_count", "skipped_count", "error_count", 
                  "started_at", "updated_at", "completed_at"]:
        setattr(mock_job, field, 0)
    mock_job.current_file = ""
    mock_job.progress_percent = 0.0
    mock_job.eta_seconds = 0.0
    
    mock_jm.create_job.return_value = mock_job
    app.dependency_overrides[_get_job_manager] = lambda: mock_jm

    try:
        response = client.post("/demo/start")
        assert response.status_code == 200
        assert response.json()["message"] == "Demo started"
        assert response.json()["job"]["id"] == 123
        
        mock_db.set_setting.assert_any_call("demo_mode", "1")
        mock_copy.assert_called() 
    finally:
        app.dependency_overrides.pop(_get_job_manager, None)

@patch("os.path.exists")
@patch("shutil.rmtree")
def test_reset_demo(mock_rmtree, mock_exists, mock_db, client):
    mock_exists.return_value = True
    
    response = client.post("/demo/reset")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    mock_db.set_setting.assert_called_with("demo_mode", "0")
    mock_rmtree.assert_called()
