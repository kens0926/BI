$ErrorActionPreference = "Stop"

if (-not $env:PRJ1_SECRET_KEY) {
    Write-Error "PRJ1_SECRET_KEY is required for production startup."
}

if (-not $env:PRJ1_DB_PATH) {
    $env:PRJ1_DB_PATH = Join-Path $PSScriptRoot "icp_system.db"
}

$hostName = if ($env:PRJ1_HOST) { $env:PRJ1_HOST } else { "0.0.0.0" }
$port = if ($env:PRJ1_PORT) { $env:PRJ1_PORT } else { "5000" }

waitress-serve --host=$hostName --port=$port wsgi:application
