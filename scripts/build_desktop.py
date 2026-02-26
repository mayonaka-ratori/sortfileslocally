"""
Unified desktop build script for LocalCurator Prime.
Runs: Next.js export → PyInstaller → Tauri bundle

Usage:
    python scripts/build_desktop.py [--cpu-only] [--skip-frontend] [--skip-backend]
"""
import subprocess
import sys
import os
import time

def run(cmd, cwd=None, label=""):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    start = time.time()
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"FAILED: {label} (exit code {result.returncode})")
        sys.exit(1)
    print(f"  Completed in {elapsed:.1f}s")
    return result

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build LocalCurator Prime desktop app")
    parser.add_argument('--cpu-only', action='store_true')
    parser.add_argument('--skip-frontend', action='store_true')
    parser.add_argument('--skip-backend', action='store_true')
    parser.add_argument('--skip-tauri', action='store_true')
    args = parser.parse_args()
    
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    
    # Version Consistency Note:
    # Always ensure web/package.json version matches src-tauri/tauri.conf.json version.
    
    # Step 1: Frontend static export
    if not args.skip_frontend:
        run("npm run build", cwd="web", label="Step 1/3: Next.js Static Export")
        if not os.path.exists("web/out/index.html"):
            print("ERROR: web/out/index.html not found after build")
            sys.exit(1)
    
    # Step 2: Backend PyInstaller
    if not args.skip_backend:
        cmd = f"{sys.executable} scripts/build_backend.py"
        if args.cpu_only:
            cmd += " --cpu-only"
        run(cmd, label="Step 2/3: PyInstaller Backend Bundle")
    
    # Step 3: Tauri bundle
    if not args.skip_tauri:
        run("npm run tauri:build", label="Step 3/3: Tauri Desktop Bundle")
    
    print(f"\n{'='*60}")
    print("  BUILD COMPLETE")
    print(f"{'='*60}")
    
    # Report output locations
    if sys.platform == 'win32':
        installer_dir = "src-tauri/target/release/bundle/msi"
    elif sys.platform == 'darwin':
        installer_dir = "src-tauri/target/release/bundle/dmg"
    else:
        installer_dir = "src-tauri/target/release/bundle/appimage"
    
    if os.path.exists(installer_dir):
        for f in os.listdir(installer_dir):
            path = os.path.join(installer_dir, f)
            size_mb = os.path.getsize(path) / (1024*1024)
            print(f"  Installer: {path} ({size_mb:.1f} MB)")

if __name__ == '__main__':
    main()
