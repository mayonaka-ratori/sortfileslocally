"""
Minimal step-by-step test for VideoProcessor init crash diagnosis.
"""
import sys, os, tempfile, subprocess, traceback
sys.path.insert(0, '.')

# Create test video
tmp = tempfile.mktemp(suffix='.mp4')
r = subprocess.run(
    ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x240:rate=10',
     '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
     '-c:v', 'libx264', '-c:a', 'aac', '-shortest', tmp],
    capture_output=True
)
print('video created:', os.path.exists(tmp), 'ffmpeg rc:', r.returncode, flush=True)

print('--- Importing VideoProcessor ---', flush=True)
from src.core.video_processor import VideoProcessor
print('--- Creating VideoProcessor() ---', flush=True)

try:
    vp = VideoProcessor()
    print('VP init OK', flush=True)
    print('whisper:', type(vp.ai_engine.whisper_model).__name__, flush=True)
    print('--- Calling process_video() ---', flush=True)
    res = vp.process_video(tmp)
    if res:
        print('audio_segments:', len(res.get('audio_transcription', [])), flush=True)
        print('frame_descriptions:', len(res.get('frame_descriptions', [])), flush=True)
        for d in res.get('frame_descriptions', []):
            print('  [@%.1fs]' % d['timestamp'], d['text'], flush=True)
    else:
        print('result was None', flush=True)
except Exception as e:
    traceback.print_exc()

try:
    os.remove(tmp)
except:
    pass

print('DONE', flush=True)
