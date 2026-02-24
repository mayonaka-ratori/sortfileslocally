
import os
import sys
import json
import requests
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE_URL = "http://localhost:8000"

def test_scenes_api():
    # 1. Search for a video with scenes (assuming one exists or we used the previous verification data)
    # Actually, we should probably just check if the endpoints exist.
    
    print("Checking /gallery/search...")
    try:
        resp = requests.get(f"{BASE_URL}/gallery/search?query=test&top_k=5")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Search Success: Found {len(data['results'])} results")
            for r in data['results']:
                if r.get('matched_scene'):
                    print(f"Matched Scene found in result: {r['matched_scene']}")
        else:
            print(f"Search Failed: {resp.status_code}")
    except Exception as e:
        print(f"Search Request Error: {e}")

    # 2. Check /media/{id}/scenes
    # We need a valid file id. Let's try to get the first one from /gallery/
    print("\nChecking /media/{id}/scenes...")
    try:
        resp = requests.get(f"{BASE_URL}/gallery/")
        if resp.status_code == 200:
            files = resp.json()
            if files:
                file_id = files[0]['id']
                print(f"Testing for File ID: {file_id}")
                s_resp = requests.get(f"{BASE_URL}/media/{file_id}/scenes")
                if s_resp.status_code == 200:
                    scenes = s_resp.json()
                    print(f"Scenes API Success: Found {len(scenes)} scenes")
                    if scenes:
                        print(f"First Scene: {scenes[0]}")
                else:
                    print(f"Scenes API Failed: {s_resp.status_code}")
            else:
                print("No files found in library to test.")
        else:
            print(f"Gallery API Failed: {resp.status_code}")
    except Exception as e:
        print(f"API Request Error: {e}")

if __name__ == "__main__":
    # Start the server in a separate terminal OR assume it's running.
    # For verification in this environment, it's easier to verify via mock if server isn't guaranteed.
    # But since the user might want a real check, I'll just provide the script.
    test_scenes_api()
