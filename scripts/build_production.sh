#!/bin/bash
# === LocalCurator Prime Production Build Script (macOS/Linux) ===
# Usage: ./scripts/build_production.sh [--cpu-only]

set -e
CPU_ONLY=false
for arg in "$@"; do
  if [ "$arg" == "--cpu-only" ]; then
    CPU_ONLY=true
  fi
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."

BUILD_FLAG=""
if [ "$CPU_ONLY" = true ]; then
  BUILD_FLAG="--cpu-only"
fi

echo "=== [1/5] Building Backend ($BUILD_FLAG) ==="
python3 scripts/build_backend.py $BUILD_FLAG

echo "=== [2/5] Verifying Sidecar Binary ==="
ARCH=$(uname -m)
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
if [ "$OS" == "darwin" ]; then
  TRIPLE="$ARCH-apple-darwin"
else
  TRIPLE="x86_64-unknown-linux-gnu"
fi

SIDECAR_WRAPPER="src-tauri/binaries/localcurator-backend-$TRIPLE"
SIDECAR_DIR="src-tauri/binaries/localcurator-backend-dir"

if [ ! -f "$SIDECAR_WRAPPER" ]; then
  echo "ERROR: Sidecar wrapper not found: $SIDECAR_WRAPPER"
  exit 1
fi
if [ ! -d "$SIDECAR_DIR" ]; then
  echo "ERROR: Sidecar directory not found: $SIDECAR_DIR"
  exit 1
fi
echo "  ✅ Sidecar verified."

echo "=== [3/5] Building Frontend ==="
cd web && npm run build
cd ..

echo "=== [4/5] Building Tauri App ==="
npm run tauri build

echo "=== [5/5] Artifact Verification ==="
# Check for .app, .dmg, .deb, .rpm etc
find src-tauri/target/release/bundle -maxdepth 2 -type f \( -name "*.dmg" -o -name "*.deb" -o -name "*.app" -o -name "*.rpm" \) | while read -r file; do
  echo "  Artifact: $(basename "$file")"
  if command -v sha256sum >/dev/null; then
    sha256sum "$file"
  elif command -v shasum >/dev/null; then
    shasum -a 256 "$file"
  fi
done

echo -e "\n=== BUILD COMPLETE ==="
