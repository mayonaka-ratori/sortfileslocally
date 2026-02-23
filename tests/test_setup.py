import pytest
from fastapi.testclient import TestClient
import os
from server.main import app

client = TestClient(app)

def test_get_setup_settings():
    response = client.get("/setup/settings")
    assert response.status_code == 200
    data = response.json()
    assert "custom_model_dir" in data

def test_post_setup_settings_valid(tmp_path):
    valid_dir = str(tmp_path)
    response = client.post("/setup/settings", json={"key": "custom_model_dir", "value": valid_dir})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["key"] == "custom_model_dir"
    assert data["value"] == valid_dir
    assert data["requires_restart"] is True

def test_post_setup_settings_invalid_not_exist():
    response = client.post("/setup/settings", json={"key": "custom_model_dir", "value": "/does/not/exist/ever123"})
    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"].lower()

def test_post_setup_settings_invalid_not_dir(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    response = client.post("/setup/settings", json={"key": "custom_model_dir", "value": str(test_file)})
    assert response.status_code == 422
    assert "not a directory" in response.json()["detail"].lower()
