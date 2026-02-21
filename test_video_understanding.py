"""
Video Understanding Pipeline Test
Tests audio transcription and frame-description storage.
"""
import os
import sys
import json
import sqlite3
import subprocess
import shutil
import tempfile

sys.path.insert(0, os.path.abspath("."))

DB_PATH = "data/db/metadata.db"


def check_db_columns():
    """Verify that new columns exist in the DB."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(files)")
    cols = [r[1] for r in cur.fetchall()]
    conn.close()
    has_audio = "audio_transcription" in cols
    has_frames = "frame_descriptions" in cols
    print(f"  [DB columns] audio_transcription: {has_audio}, frame_descriptions: {has_frames}")
    return has_audio and has_frames


def create_test_video(out_path: str, duration: int = 5):
    """Generate a tiny test video (silent, color bars) via ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size=320x240:rate=10",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest", out_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def test_pipeline_with_video(video_path: str):
    """Run the video through VideoProcessor and check results."""
    from src.core.video_processor import VideoProcessor
    print(f"  Loading VideoProcessor...")
    vp = VideoProcessor()
    print(f"  Processing: {video_path}")
    result = vp.process_video(video_path)
    if result is None:
        print("  [FAIL] process_video returned None")
        return False

    print(f"  Duration: {result['duration']:.1f}s, FPS: {result['fps']:.1f}")
    print(f"  Faces detected: {len(result['faces'])}")
    print(f"  Audio segments: {len(result['audio_transcription'])}")
    print(f"  Frame descriptions: {len(result['frame_descriptions'])}")

    for seg in result['audio_transcription']:
        print(f"    [Audio] {seg['start']:.1f}s-{seg['end']:.1f}s: {seg['text']}")
    for desc in result['frame_descriptions']:
        print(f"    [Frame] @{desc['timestamp']:.1f}s: {desc['text']}")

    return True


def test_db_roundtrip(video_path: str):
    """Process a video, save to a fresh test DB, then confirm columns are populated."""
    import shutil
    db_dir = "data/db_test_video_understanding"
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)

    from src.core.processor import Processor
    print(f"  Initializing Processor with test DB: {db_dir}")
    proc = Processor(db_dir=db_dir)

    # Put the video in a temp scan directory
    scan_dir = "data/test_video_scan_dir"
    os.makedirs(scan_dir, exist_ok=True)
    dest = os.path.join(scan_dir, os.path.basename(video_path))
    shutil.copy(video_path, dest)

    print(f"  Scanning {scan_dir} ...")
    for status in proc.process_folder(scan_dir, force_reprocess=True):
        print(f"    {status}")

    # Check DB
    db_file = os.path.join(db_dir, "metadata.db")
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT file_path, audio_transcription, frame_descriptions FROM files WHERE media_type='video'")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("  [FAIL] No video rows in DB after scan")
        return False

    for path, audio_json, frames_json in rows:
        audio = json.loads(audio_json) if audio_json else []
        frames = json.loads(frames_json) if frames_json else []
        print(f"  [DB] {os.path.basename(path)}: {len(audio)} audio segments, {len(frames)} frame descriptions STORED")

    # Cleanup
    shutil.rmtree(scan_dir, ignore_errors=True)
    shutil.rmtree(db_dir, ignore_errors=True)
    return True


if __name__ == "__main__":
    print("=== Video Understanding Pipeline Test ===\n")

    print("[1] Verifying DB column migration...")
    if check_db_columns():
        print("  PASS: New columns exist\n")
    else:
        print("  FAIL: Columns missing - restart the server to trigger migration\n")

    print("[2] Generating test video via ffmpeg...")
    tmp_dir = tempfile.mkdtemp()
    test_vid = os.path.join(tmp_dir, "test_video.mp4")
    if create_test_video(test_vid):
        print(f"  PASS: Created {test_vid}\n")
    else:
        print("  FAIL: ffmpeg not found or error. Aborting video tests.")
        print("  (Install ffmpeg and add to PATH to enable audio extraction)")
        sys.exit(1)

    print("[3] Testing VideoProcessor (audio + frame descriptions)...")
    ok = test_pipeline_with_video(test_vid)
    print(f"  {'PASS' if ok else 'FAIL'}: VideoProcessor pipeline\n")

    if ok:
        print("[4] Testing DB roundtrip (scan -> store -> check)...")
        ok2 = test_db_roundtrip(test_vid)
        print(f"  {'PASS' if ok2 else 'FAIL'}: DB roundtrip\n")
    
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("=== Test Complete ===")
