import argparse
import uvicorn
import os
import sys

# Ensure this script runs from the project root and can import 'server'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Local Curator Prime Backend Launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    print(f"Starting backend on http://{args.host}:{args.port}")

    # For PyInstaller/cx_Freeze: programmatic uvicorn running
    uvicorn.run("server.main:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
