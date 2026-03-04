# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Paths
project_root = os.path.abspath('.')
server_dir = os.path.join(project_root, 'server')
src_dir = os.path.join(project_root, 'src')

a = Analysis(
    [os.path.join(server_dir, 'main.py')],
    pathex=[project_root, server_dir, src_dir],
    binaries=[],
    datas=[
        (os.path.join(src_dir, 'core'), 'src/core'),
        (os.path.join(src_dir, 'data'), 'src/data'),
    ],
    hiddenimports=[
        # FastAPI & Uvicorn
        'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
        'uvicorn.protocols', 'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto', 'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # SQLite
        'sqlite3',
        # AI Libraries
        'torch', 'torch._C', 'torch.distributions', 'torchvision', 'torchvision.transforms',
        'open_clip', 'open_clip_torch',
        'PIL', 'PIL.Image',
        'numpy', 'scipy',
        'sklearn', 'sklearn.preprocessing',
        # FAISS
        'faiss',
        # InsightFace + ONNX
        'insightface', 'insightface.app', 'insightface.app.common',
        'onnxruntime',
        # Whisper
        'faster_whisper', 'ctranslate2',
        # Scene Detection
        'scenedetect', 'cv2',
        # JoyTag
        'safetensors',
        # Other
        'pydantic', 'fastapi', 'starlette',
        'multipart', 'python_multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'jupyter',
        'IPython', 'notebook', 'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='localcurator-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for STARTING_PORT output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='localcurator-backend',
)
