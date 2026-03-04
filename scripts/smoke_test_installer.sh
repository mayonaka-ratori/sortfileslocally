#!/bin/bash

INSTALLER_PATH=$1

if [ -z "$INSTALLER_PATH" ]; then
    echo "Usage: ./smoke_test_installer.sh <installer_path>"
    exit 1
fi

APP_NAME="LocalCurator Prime"
EXE_NAME="localcurator-prime"

cleanup() {
    echo "Cleaning up processes..."
    kill -9 $APP_PID 2>/dev/null || true
    pkill -9 localcurator-backend 2>/dev/null || true

    if [[ "$INSTALLER_PATH" == *.dmg ]] && [ -n "$MOUNT_POINT" ]; then
        echo "Unmounting DMG..."
        hdiutil detach "$MOUNT_POINT" -quiet -force || true
    fi
}
trap cleanup EXIT

if [[ "$INSTALLER_PATH" == *.dmg ]]; then
    echo "Mounting DMG: $INSTALLER_PATH"
    MOUNT_POINT="/Volumes/$APP_NAME"
    hdiutil attach "$INSTALLER_PATH" -mountpoint "$MOUNT_POINT" -quiet
    LAUNCH_PATH="$MOUNT_POINT/$APP_NAME.app/Contents/MacOS/$EXE_NAME"
elif [[ "$INSTALLER_PATH" == *.AppImage ]]; then
    echo "Running AppImage: $INSTALLER_PATH"
    chmod +x "$INSTALLER_PATH"
    LAUNCH_PATH="$INSTALLER_PATH"
else
    echo "Unsupported installer format for shell script."
    exit 1
fi

echo "Launching: $LAUNCH_PATH"
if [[ "$INSTALLER_PATH" == *.AppImage ]]; then
    "$LAUNCH_PATH" --appimage-extract-and-run &
else
    "$LAUNCH_PATH" &
fi
APP_PID=$!

TIMEOUT=60
INTERVAL=2
ELAPSED=0
HEALTH_OK=false

echo "Polling backend /health for $TIMEOUT seconds..."

while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s http://localhost:8000/health | grep -q 'ok'; then
        HEALTH_OK=true
        echo "Backend is healthy!"
        break
    fi
    echo "Backend not ready yet... (${ELAPSED}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ "$HEALTH_OK" = true ]; then
    echo "Smoke test PASSED."
    exit 0
else
    echo "Smoke test FAILED: Backend did not respond within $TIMEOUT seconds."
    exit 1
fi
