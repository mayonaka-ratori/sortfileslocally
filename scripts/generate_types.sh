#!/usr/bin/env bash
# Generates TypeScript types from the FastAPI OpenAPI spec.
# Run from project root: bash scripts/generate_types.sh
# Or via npm: npm run generate-types (from web/)

set -e

PORT=8765
OPENAPI_URL="http://localhost:${PORT}/openapi.json"
OUTPUT="web/src/generated/api-types.ts"

echo "[1/4] Starting FastAPI server temporarily on port ${PORT}..."
CORS_ORIGINS="http://localhost:3000" python -m uvicorn server.main:app \
  --host 127.0.0.1 --port ${PORT} --no-access-log &
SERVER_PID=$!

# Wait for server to be ready (up to 20 seconds)
echo "[2/4] Waiting for server to be ready..."
for i in $(seq 1 20); do
  if curl -s "${OPENAPI_URL}" > /dev/null 2>&1; then
    echo "  Server ready after ${i}s."
    break
  fi
  if [ "${i}" -eq 20 ]; then
    echo "  ERROR: Server did not start in time."
    kill "${SERVER_PID}" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

# Generate TypeScript types
echo "[3/4] Running openapi-typescript..."
npx openapi-typescript@latest "${OPENAPI_URL}" -o "${OUTPUT}"

# Stop server
echo "[4/4] Stopping temporary server (PID=${SERVER_PID})..."
kill "${SERVER_PID}" 2>/dev/null || true

echo ""
echo "✅ TypeScript types generated at: ${OUTPUT}"
