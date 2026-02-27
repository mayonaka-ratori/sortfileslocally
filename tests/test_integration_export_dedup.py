import sys
import os
from unittest.mock import MagicMock

# Robust availability check
def is_available(mod_name):
    try:
        mod = __import__(mod_name)
        if 'mock' in str(type(mod)).lower(): return False
        return True
    except ImportError:
        return False

# Mock AI and system modules only if missing and not already real
for mod in ["open_clip", "decord", "facenet_pytorch", "insightface", "onnxruntime", "pandas", "cv2"]:
    if not is_available(mod):
        sys.modules[mod] = MagicMock()

# Models must be mocked
sys.modules["src.core.ai_models"] = MagicMock()
sys.modules["src.core.vlm_engine"] = MagicMock()
sys.modules["src.core.processor"] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from server.main import app
from src.data.schemas import MediaItem, ProcessingResult

# Handle PIL mock
if is_available("PIL"):
    from PIL import Image
else:
    Image = MagicMock()

client = TestClient(app)

def test_integration_export_dedup_deletes_xmp(tmp_path):
    # Setup test file - Use normalized absolute path
    test_img_path = (tmp_path / "test_dedup_export.jpg").resolve()
    if not isinstance(Image, MagicMock):
        img = Image.new('RGB', (100, 100))
        img.save(test_img_path, format='JPEG')
    else:
        with open(test_img_path, 'wb') as f: f.write(b"fake image")
    
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
    row = cursor.fetchone()
    assert row is not None, f"File {img_path_str} was not inserted into DB"
    file_id = row[0]
    conn.close()
    
    # 1. Export Metadata (creates .xmp)
    exp_res = client.post("/media/export-metadata", json={"file_ids": [file_id], "mode": "xmp"})
    assert exp_res.status_code == 200
    
    # Confirm .xmp sidecar exists
    xmp_path = os.path.splitext(img_path_str)[0] + ".xmp"
    assert os.path.exists(xmp_path), f"XMP sidecar {xmp_path} was not created"
    
    # 2. Dedup Apply (Delete media)
    dedup_res = client.post("/dedup/apply", json={"file_paths": [img_path_str]})
    assert dedup_res.status_code == 200
    
    data = dedup_res.json()
    if len(data["deleted"]) == 0:
        print(f"DEBUG: Dedup Apply Failed. Errors: {data.get('errors')}")
        # One last check: maybe the drive letter case changed?
        print(f"DEBUG: File exists on disk? {os.path.exists(img_path_str)}")
        
    assert len(data["deleted"]) == 1
    assert data["deleted"][0] == img_path_str
    
    # Confirm both .jpg and .xmp are deleted
    assert not os.path.exists(img_path_str), "Image file was not deleted"
    assert not os.path.exists(xmp_path), "XMP sidecar was not deleted during deduplication"
