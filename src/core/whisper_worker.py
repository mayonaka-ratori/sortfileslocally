import os
import sys
import json
import traceback
import queue

def whisper_worker_process(task_queue, result_queue):
    """
    Long-lived worker process for Whisper transcription.
    Loads the model once and processes audio paths from task_queue.
    """
    # Attempt to import faster_whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        # If faster_whisper is not available, we shouldn't be here, but just in case
        print("faster_whisper not installed. Worker exiting.", file=sys.stderr)
        return

    print("Whisper worker initializing model...", file=sys.stderr)
    try:
        # Initialize model once
        model = WhisperModel('base', device='cpu', compute_type='int8')
        print("Whisper worker initialized successfully.", file=sys.stderr)
    except Exception as e:
        print(f"Whisper worker failed to initialize model: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return

    # Signal that initialization is complete
    result_queue.put({"type": "init", "status": "ready"})

    # Process tasks
    while True:
        try:
            # Block until a task is available
            task = task_queue.get()
            
            # Sentinel value for shutdown
            if task is None:
                print("Whisper worker received shutdown signal.", file=sys.stderr)
                break
                
            task_id = task.get('task_id')
            audio_path = task.get('audio_path')

            if not audio_path or not os.path.exists(audio_path):
                result_queue.put({
                    "task_id": task_id,
                    "error": f"Audio file not found: {audio_path}"
                })
                continue

            try:
                # Transcribe
                segs, info = model.transcribe(audio_path, beam_size=5)
                # Parse segments to standard format
                out = [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in segs]
                
                # Send success result
                result_queue.put({
                    "task_id": task_id,
                    "result": out
                })
            except Exception as e:
                print(f"Whisper worker transcription error for {audio_path}: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                # Send error result
                result_queue.put({
                    "task_id": task_id,
                    "error": str(e)
                })
                
        except KeyboardInterrupt:
            print("Whisper worker received KeyboardInterrupt.", file=sys.stderr)
            break
        except Exception as e:
            print(f"Whisper worker loop error: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # Try to inform the main process if we have a task_id
            try:
                if 'task_id' in locals() and task_id is not None:
                    result_queue.put({
                        "task_id": task_id,
                        "error": f"Worker loop error: {str(e)}"
                    })
            except:
                pass

    print("Whisper worker process exiting.", file=sys.stderr)
