
import pytest
import os
import json
import time
from src.data.db_manager import DBManager

@pytest.fixture
def db_manager(tmp_path):
    db_dir = tmp_path / "db"
    db_manager = DBManager(db_dir=str(db_dir))
    yield db_manager
    # Teardown
    db_manager.save_indices()

def test_save_and_retrieve_history(db_manager):
    query = "beautiful sunset"
    filters = json.dumps({"media_type": "image"})
    result_count = 10
    
    db_manager.save_search_history(query, filters, result_count)
    
    history = db_manager.get_search_history()
    assert len(history) == 1
    assert history[0]["query_text"] == query
    assert history[0]["filters_json"] == filters
    assert history[0]["result_count"] == result_count
    assert "executed_at" in history[0]

def test_upsert_history(db_manager):
    query = "cat"
    filters = json.dumps({})
    
    # First save
    db_manager.save_search_history(query, filters, 5)
    history1 = db_manager.get_search_history()
    assert len(history1) == 1
    
    # Second save (same query/filters)
    db_manager.save_search_history(query, filters, 15)
    history2 = db_manager.get_search_history()
    
    assert len(history2) == 1 # Still 1 entry
    assert history2[0]["result_count"] == 15

def test_auto_delete_oldest(db_manager):
    # Insert 105 entries. Since they are rapid, ID will be the primary tie-breaker for ordering.
    for i in range(105):
        db_manager.save_search_history(f"query {i}", json.dumps({}), i)
        
    history = db_manager.get_search_history(limit=200)
    assert len(history) == 100
    
    # With ID tie-breaker, the highest IDs (most recent) should be kept.
    # Entries 0, 1, 2, 3, 4 should be deleted.
    queries = [h["query_text"] for h in history]
    assert "query 0" not in queries
    assert "query 4" not in queries
    assert "query 5" in queries
    assert "query 104" in queries

def test_delete_single_entry(db_manager):
    db_manager.save_search_history("to delete", None, 0)
    db_manager.save_search_history("keep", None, 1)
    
    history = db_manager.get_search_history()
    assert len(history) == 2
    
    id_to_delete = [h["id"] for h in history if h["query_text"] == "to delete"][0]
    db_manager.delete_search_history(id_to_delete)
    
    history_after = db_manager.get_search_history()
    assert len(history_after) == 1
    assert history_after[0]["query_text"] == "keep"

def test_clear_all_history(db_manager):
    db_manager.save_search_history("q1", None, 1)
    db_manager.save_search_history("q2", None, 2)
    
    assert len(db_manager.get_search_history()) == 2
    
    db_manager.clear_search_history()
    
    assert len(db_manager.get_search_history()) == 0
