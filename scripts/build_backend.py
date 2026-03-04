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
    
    # Copy to Tauri binaries directory (onedir builds create a directory, not a single file)
    src_dir = os.path.join('dist', 'localcurator-backend')
    
    # Target directory structure:
    # src-tauri/binaries/
    #   localcurator-backend-<triple>.cmd    (Wrapper for Windows)
    #   localcurator-backend-<triple>        (Wrapper for Mac/Linux)
    #   localcurator-backend-dir/            (The actual onedir build)
    
    bin_dir = args.output_dir
    target_bundle_dir = os.path.join(bin_dir, 'localcurator-backend-dir')
    
    if os.path.exists(target_bundle_dir):
        shutil.rmtree(target_bundle_dir)
        
    os.makedirs(target_bundle_dir, exist_ok=True)
    
    print(f"Copying onedir output to: {target_bundle_dir}")
    shutil.copytree(src_dir, target_bundle_dir, dirs_exist_ok=True)
    
    # Generate thin wrapper scripts for Tauri externalBin
    wrapper_path_sh = os.path.join(bin_dir, f"localcurator-backend-{triple}")
    wrapper_path_cmd = os.path.join(bin_dir, f"localcurator-backend-{triple}.cmd")
    
    # Linux/Mac bash wrapper
    with open(wrapper_path_sh, 'w', encoding='utf-8') as f:
        f.write("#!/bin/sh\n")
        f.write('exec "$(dirname "$0")/localcurator-backend-dir/localcurator-backend" "$@"\n')
    
    # Windows cmd wrapper
    with open(wrapper_path_cmd, 'w', encoding='utf-8') as f:
        f.write("@echo off\r\n")
        f.write('"%~dp0localcurator-backend-dir\\localcurator-backend.exe" %*\r\n')
    
    # Make shell script executable
    if platform.system() != 'Windows':
        os.chmod(wrapper_path_sh, 0o755)

    print(f"Wrapper scripts generated: {wrapper_path_cmd} and {wrapper_path_sh}")

if __name__ == '__main__':
    main()
