import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
import os
import sys
from unittest.mock import MagicMock

# Mock out AI-heavy routers before importing server.main
# Prevents open_clip / torch from being required in the test environment
_ROUTER_NAMES = ["gallery", "media", "scan", "setup", "dedup", "albums", "insights", "scenes", "demo", "privacy"]
for _r in _ROUTER_NAMES:
    sys.modules.setdefault(f"server.routers.{_r}", MagicMock())
sys.modules.setdefault("server.routers", MagicMock())
# Also mock heavy AI dep used by dependencies.py
sys.modules.setdefault("src.core.ai_models", MagicMock())

from server.main import get_cors_origins

@pytest.fixture
def create_test_app():
    """Creates a fresh FastAPI app with CORS configured using current get_cors_origins()."""
    def _create():
        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=get_cors_origins(),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        @app.get("/health")
        def health():
            return {"status": "ok"}
        return app
    return _create

def test_cors_tauri_origins_always_allowed(monkeypatch, create_test_app):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    
    client = TestClient(create_test_app())
    
    response = client.options("/health", headers={"Origin": "tauri://localhost", "Access-Control-Request-Method": "GET"})
    assert response.headers.get("access-control-allow-origin") == "tauri://localhost"
    
    response = client.options("/health", headers={"Origin": "https://tauri.localhost", "Access-Control-Request-Method": "GET"})
    assert response.headers.get("access-control-allow-origin") == "https://tauri.localhost"

def test_cors_random_origins_rejected(monkeypatch, create_test_app):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    
    client = TestClient(create_test_app())
    
    response = client.options("/health", headers={"Origin": "https://malicious.com", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in response.headers

def test_cors_dev_origin_auto_allowed_in_dev_mode(monkeypatch, create_test_app):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    
    client = TestClient(create_test_app())
    
    response = client.options("/health", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_cors_dev_origin_allowed_via_env_var(monkeypatch, create_test_app):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:8080")
    
    client = TestClient(create_test_app())
    
    response = client.options("/health", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    
    response = client.options("/health", headers={"Origin": "http://127.0.0.1:8080", "Access-Control-Request-Method": "GET"})
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:8080"
    
    response = client.options("/health", headers={"Origin": "https://random.com", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in response.headers
