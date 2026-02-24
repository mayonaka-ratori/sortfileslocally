import sys, os, tempfile, subprocess, json, pytest

try:
    import faster_whisper
except ImportError:
    pytest.skip("faster_whisper not installed", allow_module_level=True)

def test_whisper_transcription():
    tmp = tempfile.mktemp(suffix='.wav')
    has_ffmpeg = False
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        has_ffmpeg = True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("ffmpeg not found")

    try:
        subprocess.run(['ffmpeg','-y','-f','lavfi','-i','sine=frequency=440:duration=1','-ar','16000','-ac','1',tmp], capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail("ffmpeg subprocess timed out")

    script = """
import sys, json
try:
    from faster_whisper import WhisperModel
    model = WhisperModel('base', device='cpu', compute_type='int8')
    segs, _ = model.transcribe(sys.argv[1], beam_size=5)
    out = [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in segs]
    print(json.dumps(out))
except Exception as e:
    print(json.dumps({'error': str(e)}))
"""

    script_path = 'worker_whisper_test.py'
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)

    try:
        cmd = [sys.executable, script_path, tmp]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            pytest.fail("Whisper subprocess timed out")
        
        print('STDOUT:', res.stdout)
        print('STDERR:', res.stderr)

        if res.returncode != 0 or 'error' in res.stdout:
            pytest.fail(f"Test failed: Error in worker script output: {res.stdout}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
        if os.path.exists(script_path):
            os.remove(script_path)
