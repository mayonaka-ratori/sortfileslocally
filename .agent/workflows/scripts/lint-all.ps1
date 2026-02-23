# Linting and Syntax Checks
Write-Host "--- Checking Python Syntax ---" -ForegroundColor Cyan
Get-ChildItem -Path . -Filter "*.py" -Recurse | Where-Object { $_.FullName -notmatch "venv" } | ForEach-Object {
    python -m py_compile $_.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Syntax Error in: $($_.FullName)" -ForegroundColor Red
    }
}

if (Get-Command "ruff" -ErrorAction SilentlyContinue) {
    Write-Host "--- Running Ruff ---" -ForegroundColor Cyan
    ruff check .
    ruff format .
} else {
    Write-Host "⚠️ Ruff not found. Skipping lint/format. Run 'pip install ruff' to enable." -ForegroundColor Yellow
}

Write-Host "--- Checking Web Linting ---" -ForegroundColor Cyan
if (Test-Path "web") {
    Push-Location web
    npm run lint
    Pop-Location
}
