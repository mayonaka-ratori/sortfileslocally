import os
import sys
import tempfile
import subprocess
import time
import pytest
from src.core.ai_models import AIEngine, HAS_WHISPER

try:
    if os.environ.get("SKIP_GPU_TESTS") == "1":
        pytest.skip("CI skip requested for GPU/heavy models", allow_module_level=True)
    import faster_whisper
except ImportError:
    pytest.skip("faster_whisper not installed", allow_module_level=True)

@pytest.fixture(scope="module")
def sample_audio_file():
    tmp = tempfile.mktemp(suffix='.wav')
    has_ffmpeg = False
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        has_ffmpeg = True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    if not has_ffmpeg:
        pytest.skip("ffmpeg not found, required to generate test audio")

    # Generate 1-second 440Hz sine wave
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-ar', '16000', '-ac', '1', tmp], capture_output=True, check=True)
    yield tmp
    if os.path.exists(tmp):
        os.remove(tmp)

@pytest.mark.ai_models
@pytest.mark.slow
def test_whisper_worker_batch(sample_audio_file, monkeypatch):
    # AIEngine is a singleton, reset it for clean testing
    AIEngine._instance = None
    engine = AIEngine()
    
    # Send 5 paths
    results = []
    for _ in range(5):
        res = engine.transcribe_audio(sample_audio_file)
        results.append(res)
        
    assert len(results) == 5
    for r in results:
        assert isinstance(r, list)

@pytest.mark.ai_models
@pytest.mark.slow
def test_whisper_worker_invalid():
    # AIEngine is a singleton, reset it
    AIEngine._instance = None
    engine = AIEngine()
    
    # Invalid file handled gracefully
    res = engine.transcribe_audio("nonexistent_fake_audio.wav")
    assert res == []

@pytest.mark.ai_models
@pytest.mark.slow
def test_whisper_worker_shutdown_and_restart(sample_audio_file):
    # AIEngine is a singleton, reset it
    AIEngine._instance = None
    engine = AIEngine()
    
    # Ensure worker is up
    engine.transcribe_audio(sample_audio_file)
    assert engine._whisper_process is not None
    assert engine._whisper_process.is_alive()
    
    pid_before = engine._whisper_process.pid
    
    # Send shutdown signal manually
    engine._whisper_task_queue.put(None)
    
    # Wait for process to die
    engine._whisper_process.join(timeout=5)
    assert not engine._whisper_process.is_alive()
    
    # Restart by requesting transcription again
    res = engine.transcribe_audio(sample_audio_file)
    assert isinstance(res, list)
    
    # Check that a new process spawned
    assert engine._whisper_process.is_alive()
    assert engine._whisper_process.pid != pid_before
