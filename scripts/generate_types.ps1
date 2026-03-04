# Generates TypeScript types from the FastAPI OpenAPI spec.
# Run from project root: pwsh -File scripts/generate_types.ps1
# Or via npm: npm run generate-types (from web/)

$ErrorActionPreference = "Stop"

$Port = 8765
$OpenApiUrl = "http://localhost:$Port/openapi.json"
$Output = "web/src/generated/api-types.ts"

Write-Host "[1/4] Starting FastAPI server temporarily on port $Port..."
$env:CORS_ORIGINS = "http://localhost:3000"
$ServerProcess = Start-Process -FilePath "python" `
  -ArgumentList "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", "$Port", "--no-access-log" `
  -PassThru -NoNewWindow

# Wait for server to be ready (up to 20 seconds)
Write-Host "[2/4] Waiting for server to be ready..."
$Ready = $false
for ($i = 1; $i -le 20; $i++) {
    try {
        $null = Invoke-WebRequest -Uri $OpenApiUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  Server ready after ${i}s."
        $Ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $Ready) {
    Write-Error "ERROR: Server did not start in 20 seconds."
    Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

# Generate TypeScript types
Write-Host "[3/4] Running openapi-typescript..."
npx openapi-typescript@latest $OpenApiUrl -o $Output

# Stop server
Write-Host "[4/4] Stopping temporary server (PID=$($ServerProcess.Id))..."
Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✅ TypeScript types generated at: $Output"
