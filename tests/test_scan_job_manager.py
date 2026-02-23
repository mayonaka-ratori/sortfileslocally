"""
Verify ScanJobManager: create, update, resume, and error logging.
"""
import os
import sys
import shutil
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.db_manager import DBManager
from src.data.scan_job_manager import ScanJobManager, ScanJob


def test_scan_job_lifecycle():
    print("=== ScanJobManager Lifecycle Test ===")

    test_db_dir = "data/test_db_sjm"
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)

    # DBManager creates the tables (including new scan_jobs / scan_errors)
    db = DBManager(test_db_dir)
    manager = ScanJobManager(db.sqlite_path)

    # 1. Create a job
    job = manager.create_job("/test/path", total_files=100)
    assert job.id > 0, "Job should have been assigned an ID"
    assert job.status == "pending"
    assert job.total_files == 100
    print(f"  [PASS] Created job #{job.id} (status={job.status})")

    # 2. Mark running
    manager.mark_running(job.id)
    job = manager.get_job(job.id)
    assert job.status == "running"
    print(f"  [PASS] Job marked running")

    # 3. Increment processed
    manager.increment_processed(job.id, "/test/path/file_01.jpg")
    manager.increment_processed(job.id, "/test/path/file_02.jpg")
    manager.increment_skipped(job.id)
    job = manager.get_job(job.id)
    assert job.processed_count == 2
    assert job.skipped_count == 1
    assert job.last_processed_path == "/test/path/file_02.jpg"
    print(f"  [PASS] Progress: processed={job.processed_count}, skipped={job.skipped_count}")

    # 4. Log an error
    manager.log_error(job.id, "/test/path/bad.png", "Corrupt file", "Traceback...")
    job = manager.get_job(job.id)
    assert job.error_count == 1
    errors = manager.get_errors(job.id)
    assert len(errors) == 1
    assert errors[0].file_path == "/test/path/bad.png"
    print(f"  [PASS] Error logged: {errors[0].error_message}")

    # 5. Progress percent and ETA
    print(f"  [INFO] Progress: {job.progress_percent:.1f}%  ETA: {job.eta_seconds:.1f}s")
    assert job.progress_percent > 0

    # 6. Simulate crash → resume
    manager.mark_failed(job.id, "Server crashed")
    job = manager.get_job(job.id)
    assert job.status == "failed"
    print(f"  [PASS] Job marked as failed")

    # 7. Find resumable
    resumable = manager.get_resumable_job("/test/path")
    assert resumable is not None
    assert resumable.id == job.id
    assert resumable.last_processed_path == "/test/path/file_02.jpg"
    print(f"  [PASS] Found resumable job #{resumable.id} (resume after: {resumable.last_processed_path})")

    # 8. Complete
    manager.mark_running(job.id)
    manager.mark_completed(job.id)
    job = manager.get_job(job.id)
    assert job.status == "completed"
    assert job.completed_at > 0
    print(f"  [PASS] Job completed")

    # 9. List all
    all_jobs = manager.get_all_jobs()
    assert len(all_jobs) == 1
    print(f"  [PASS] Listed {len(all_jobs)} job(s)")

    # Cleanup
    shutil.rmtree(test_db_dir)
    print("=== All ScanJobManager Tests Passed! ===")


if __name__ == "__main__":
    test_scan_job_lifecycle()
