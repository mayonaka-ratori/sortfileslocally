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
def api_components():
    from fastapi.testclient import TestClient
    from server.main import app
    return {
        "TestClient": TestClient,
        "app": app
    }

@pytest.fixture
def client(api_components):
    TestClient = api_components["TestClient"]
    app = api_components["app"]
    return TestClient(app)

@pytest.mark.ai_models
def test_get_setup_settings(client):
    response = client.get("/setup/settings")
    assert response.status_code == 200
    data = response.json()
    assert "custom_model_dir" in data

@pytest.mark.ai_models
def test_post_setup_settings_valid(tmp_path, client):
    valid_dir = str(tmp_path)
    response = client.post("/setup/settings", json={"key": "custom_model_dir", "value": valid_dir})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["key"] == "custom_model_dir"
    assert data["value"] == valid_dir
    assert data["requires_restart"] is True

@pytest.mark.ai_models
def test_post_setup_settings_invalid_not_exist(client):
    response = client.post("/setup/settings", json={"key": "custom_model_dir", "value": "/does/not/exist/ever123"})
    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"].lower()

@pytest.mark.ai_models
def test_post_setup_settings_invalid_not_dir(tmp_path, client):
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    response = client.post("/setup/settings", json={"key": "custom_model_dir", "value": str(test_file)})
    assert response.status_code == 422
    assert "not a directory" in response.json()["detail"].lower()

@pytest.mark.ai_models
def test_post_setup_backup(client):
    from server.dependencies import get_db_manager
    mock_db = MagicMock()
    mock_db.create_backup.return_value = "/mock/backup.db"
    
    # We need to override the dependency because the router uses it
    from server.main import app
    app.dependency_overrides[get_db_manager] = lambda: mock_db
    
    try:
        response = client.post("/setup/backup")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "backup_path" in response.json()
    finally:
        app.dependency_overrides.pop(get_db_manager, None)
