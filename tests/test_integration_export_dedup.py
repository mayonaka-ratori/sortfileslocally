import pytest
from fastapi.testclient import TestClient
import os
from server.main import app
from src.data.schemas import MediaItem, ProcessingResult
from PIL import Image

client = TestClient(app)

def test_integration_export_dedup_deletes_xmp(tmp_path):
    # Setup test file
    test_img_path = tmp_path / "test_dedup_export.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(test_img_path, format='JPEG')
    
    img_path_str = str(test_img_path)
    
    # Needs db
    from server.dependencies import get_db_manager
    db = get_db_manager()
    
    import time
    item = MediaItem(file_path=img_path_str, media_type="image", file_size=100, file_hash="dummyhash", created_at=time.time(), modified_at=time.time(), tags=["tag1"], character_tags=[], series_tags=[], caption="")
    res = ProcessingResult(file_path=img_path_str, success=True, media_item=item)
    db.add_results_batch([res])
    
    # Need to find the ID
    conn = db._connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM files WHERE file_path=?", (img_path_str,))
    file_id = cursor.fetchone()[0]
    conn.close()
    
    # 1. Export Metadata (creates .xmp)
    exp_res = client.post("/media/export-metadata", json={"file_ids": [file_id], "mode": "xmp"})
    assert exp_res.status_code == 200
    
    # Confirm .xmp sidecar exists
    xmp_path = os.path.splitext(img_path_str)[0] + ".xmp"
    assert os.path.exists(xmp_path), "XMP sidecar was not created"
    
    # 2. Dedup Apply (Delete media)
    dedup_res = client.post("/dedup/apply", json={"file_paths": [img_path_str]})
    assert dedup_res.status_code == 200
    
    data = dedup_res.json()
    assert len(data["deleted"]) == 1
    assert data["deleted"][0] == img_path_str
    
    # Confirm both .jpg and .xmp are deleted
    assert not os.path.exists(img_path_str), "Image file was not deleted"
    assert not os.path.exists(xmp_path), "XMP sidecar was not deleted during deduplication"
