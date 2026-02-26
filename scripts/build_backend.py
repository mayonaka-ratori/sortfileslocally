"""
Build script for PyInstaller backend bundling.
Requires Python 3.11 with all dependencies installed.

Usage:
    python scripts/build_backend.py [--cpu-only] [--output-dir PATH]
"""
import subprocess
import sys
import os
import shutil
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpu-only', action='store_true', help='Build CPU-only version (smaller)')
    parser.add_argument('--output-dir', default='src-tauri/binaries', help='Output directory')
    args = parser.parse_args()

    # Check Python version
    if sys.version_info[:2] not in [(3, 10), (3, 11), (3, 12)]:
        print(f"WARNING: Python {sys.version} detected. Recommended: 3.11")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller not installed. Run: pip install pyinstaller")
        sys.exit(1)
    
    # Determine target triple
    import platform
    if platform.system() == 'Windows':
        triple = 'x86_64-pc-windows-msvc'
        ext = '.exe'
    elif platform.system() == 'Darwin':
        triple = 'aarch64-apple-darwin' if platform.machine() == 'arm64' else 'x86_64-apple-darwin'
        ext = ''
    else:
        triple = 'x86_64-unknown-linux-gnu'
        ext = ''
    
    output_name = f"localcurator-backend-{triple}{ext}"
    
    # Run PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        'localcurator-backend.spec',
        '--noconfirm',
        '--clean',
        '--distpath', 'dist',
    ]
    
    print(f"Building backend for {triple}...")
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print("ERROR: PyInstaller build failed")
        sys.exit(1)
    
    # Copy to Tauri binaries directory
    src = os.path.join('dist', f'localcurator-backend{ext}')
    dst = os.path.join(args.output_dir, output_name)
    os.makedirs(args.output_dir, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Backend binary copied to: {dst}")
    print(f"Size: {os.path.getsize(dst) / (1024*1024):.1f} MB")

if __name__ == '__main__':
    main()
