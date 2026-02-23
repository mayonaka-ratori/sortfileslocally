# Port and Dev Server Management

function Check-Port($port) {
    $netstat = netstat -ano | findstr ":$port" | findstr "LISTENING"
    if ($netstat) {
        $pid = ($netstat -split '\s+')[-1]
        Write-Host "⚠️ Port $port is occupied by PID $pid" -ForegroundColor Yellow
        return $pid
    }
    return $null
}

$backendPort = 8000
$frontendPort = 3000

$bPid = Check-Port $backendPort
$fPid = Check-Port $frontendPort

if ($bPid -or $fPid) {
    Write-Host "Ports are occupied. Use 'Stop-Process -Id <PID>' to clear them." -ForegroundColor Red
}

Write-Host "🚀 Starting Backend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python server/main.py"

Write-Host "🚀 Starting Frontend..." -ForegroundColor Green
if (Test-Path "web") {
    Push-Location web
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"
    Pop-Location
}
