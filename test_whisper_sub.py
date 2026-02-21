import sys, os, tempfile, subprocess, json

tmp = tempfile.mktemp(suffix='.wav')
subprocess.run(['ffmpeg','-y','-f','lavfi','-i','sine=frequency=440:duration=1','-ar','16000','-ac','1',tmp], capture_output=True)

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

script_path = 'worker_whisper.py'
with open(script_path, 'w', encoding='utf-8') as f:
    f.write(script)

cmd = [sys.executable, script_path, tmp]
res = subprocess.run(cmd, capture_output=True, text=True)
print('STDOUT:', res.stdout)
print('STDERR:', res.stderr)

os.remove(tmp)
os.remove(script_path)
