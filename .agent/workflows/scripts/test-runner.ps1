# Test Runner with Summary Table

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
$testDir = "tests"
$results = @()
$logDir = "tests/logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir }

Write-Host "🧪 Discovering tests in $testDir..." -ForegroundColor Cyan

$testFiles = Get-ChildItem -Path $testDir -Filter "test_*.py"

foreach ($file in $testFiles) {
    Write-Host "Running $($file.Name)..." -NoNewline
    $start = Get-Date
    $pythonPath = if (Test-Path "venv/Scripts/python.exe") { "venv/Scripts/python.exe" } else { "python" }
    $output = & $pythonPath $file.FullName 2>&1
    $end = Get-Date
    $duration = ($end - $start).TotalSeconds
    $status = if ($LASTEXITCODE -eq 0) { "✅ PASS" } else { "❌ FAIL" }
    
    $results += [PSCustomObject]@{
        Name     = $file.Name
        Result   = $status
        Duration = "{0:N2}s" -f $duration
    }
    
    $file.Name + " Output:`n" + $output | Out-File "$logDir/$($file.Name).log"
    Write-Host " $status ($($results[-1].Duration))"
}

Write-Host "`n--- Test Summary ---" -ForegroundColor Cyan
$results | Format-Table -AutoSize

# Generate Markdown table for agent to pick up
$md = "| Test Name | Result | Duration |`n| :--- | :--- | :--- |`n"
foreach ($r in $results) {
    $md += "| $($r.Name) | $($r.Result) | $($r.Duration) |`n"
}
$md | Out-File "tests/summary.md" -Encoding utf8
