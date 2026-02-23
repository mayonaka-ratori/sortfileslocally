
import pytest
import json
from fastapi.testclient import TestClient
from server.main import app
from src.data.db_manager import DBManager
from server.dependencies import get_db_manager

# Mock DBManager for API tests
@pytest.fixture
def client(tmp_path):
    db_dir = tmp_path / "db"
    db = DBManager(db_dir=str(db_dir))
    
    # Override dependency
    app.dependency_overrides[get_db_manager] = lambda: db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

def test_create_dynamic_album_validation(client):
    # 1. Valid dynamic album
    query_json = json.dumps({"query": "mountain", "top_k": 10})
    response = client.post("/albums/", json={
        "name": "Dynamic OK",
        "is_dynamic": True,
        "query_json": query_json
    })
    assert response.status_code == 200
    
    # 2. Missing query_json for dynamic album
    response = client.post("/albums/", json={
        "name": "Dynamic No Query",
        "is_dynamic": True,
        "query_json": None
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "Dynamic albums require a valid search query"
    
    # 3. Invalid JSON format
    response = client.post("/albums/", json={
        "name": "Dynamic Bad JSON",
        "is_dynamic": True,
        "query_json": "{invalid json}"
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid query format for dynamic album"
    
    # 4. Valid JSON but not matching HybridSearchRequest (e.g. unknown field? No, Pydantic often ignores unknown fields unless Config.extra='forbid')
    # Let's try something that fails type validation if possible, though HybridSearchRequest is quite flexible.
    # Actually, HybridSearchRequest has top_k: int. Let's try top_k: "abc"
    response = client.post("/albums/", json={
        "name": "Dynamic Bad Types",
        "is_dynamic": True,
        "query_json": json.dumps({"top_k": "not an int"})
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid query format for dynamic album"

def test_update_dynamic_album_validation(client):
    # Setup: Create a dynamic album
    query_json = json.dumps({"query": "test"})
    album_id = client.post("/albums/", json={
        "name": "Dynamic",
        "is_dynamic": True,
        "query_json": query_json
    }).json()
    
    # 1. Update with valid query
    new_query = json.dumps({"query": "new"})
    response = client.put(f"/albums/{album_id}", json={"query_json": new_query})
    assert response.status_code == 200
    
    # 2. Update with invalid query
    response = client.put(f"/albums/{album_id}", json={"query_json": "{}"}) # Should be valid technically as query is Optional
    # Wait, HybridSearchRequest accepts {} because everything is Optional.
    
    # Let's try invalid JSON
    response = client.put(f"/albums/{album_id}", json={"query_json": "!!"})
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid query format for dynamic album"
    
    # 3. Update with empty string (should fail as per requirement)
    response = client.put(f"/albums/{album_id}", json={"query_json": ""})
    assert response.status_code == 422
    assert response.json()["detail"] == "Dynamic albums require a valid search query"
