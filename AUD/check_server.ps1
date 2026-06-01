$ErrorActionPreference = "Continue"

Write-Host "Python processes:"
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Path, StartTime

Write-Host ""
Write-Host "Port 8000:"
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, State, OwningProcess

Write-Host ""
Write-Host "HTTP check:"
try {
    Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/ | Select-Object StatusCode, StatusDescription
} catch {
    Write-Host $_.Exception.Message
}

