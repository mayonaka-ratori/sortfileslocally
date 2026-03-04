import argparse
import uvicorn
from fastapi import FastAPI, Response
import json

app = FastAPI()

CURRENT_VERSION = "99.0.0"
CURRENT_NOTES = "This is a dry run update test."

@app.get("/latest.json")
def get_latest():
    return {
        "version": CURRENT_VERSION,
        "notes": CURRENT_NOTES,
        "pub_date": "2026-03-04T00:00:00Z",
        "platforms": {
            "windows-x86_64": {
                "signature": "mock_signature_for_windows",
                "url": "http://localhost:9999/download"
            },
            "darwin-aarch64": {
                "signature": "mock_signature_for_macos",
                "url": "http://localhost:9999/download"
            }
        }
    }

@app.get("/download")
def download_update():
    return Response(content=b"dummy update data", media_type="application/octet-stream")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="99.0.0", help="Version to broadcast")
    parser.add_argument("--notes", default="This is a dry run update test.", help="Release notes")
    args = parser.parse_args()
    
    CURRENT_VERSION = args.version
    CURRENT_NOTES = args.notes
    
    print(f"Starting mock update server on port 9999")
    print(f"Broadcasting version: {CURRENT_VERSION}")
    uvicorn.run(app, host="0.0.0.0", port=9999)
