import pytest
from unittest.mock import MagicMock, patch
import json

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
def mock_mm():
    from server.routers.setup import get_model_manager
    from server.main import app
    mm = MagicMock()
    app.dependency_overrides[get_model_manager] = lambda: mm
    yield mm
    app.dependency_overrides.pop(get_model_manager, None)

@patch("subprocess.run")
@patch("os.path.exists")
def test_run_privacy_audit_success(mock_exists, mock_run, client):
    mock_exists.return_value = True
    
    # Mock subprocess success
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({"verdict": "PASS", "details": []})
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    
    response = client.get("/privacy/audit")
    assert response.status_code == 200
    assert response.json()["verdict"] == "PASS"

@patch("subprocess.run")
@patch("os.path.exists")
def test_run_privacy_audit_parse_fail(mock_exists, mock_run, client):
    mock_exists.return_value = True
    
    # Mock subprocess output that isn't JSON
    mock_result = MagicMock()
    mock_result.stdout = "Not a JSON"
    mock_result.stderr = "Some error"
    mock_run.return_value = mock_result
    
    response = client.get("/privacy/audit")
    assert response.status_code == 200
    assert response.json()["verdict"] == "FAIL"
    assert "error" in response.json()

def test_get_storage_locations(mock_mm, client):
    # Mock models status
    mock_mm.get_all_status.return_value = [
        {"key": "test", "local_dir": "/mock/path/to/models"}
    ]
    
    response = client.get("/privacy/storage")
    assert response.status_code == 200
    data = response.json()
    assert "db" in data
    assert "thumbnails" in data
    assert data["models"] == "/mock/path/to/models"

def test_get_storage_locations_no_models(mock_mm, client):
    mock_mm.get_all_status.return_value = []
    
    response = client.get("/privacy/storage")
    assert response.status_code == 200
    data = response.json()
    assert data["models"] == "Default (System Cache)"
