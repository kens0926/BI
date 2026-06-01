$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Starting Internal Audit Management System..."
Write-Host "URL: http://127.0.0.1:8000"
Write-Host "Login: admin / admin123"
Write-Host ""
Write-Host "Keep this window open while using the system."
Write-Host "Press Ctrl+C to stop."
Write-Host ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

