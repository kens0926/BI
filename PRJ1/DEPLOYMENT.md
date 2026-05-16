# PRJ1 Deployment Guide

This package is prepared for a small production deployment behind Waitress.

## Files

- `wsgi.py`: WSGI entry point.
- `start_production.ps1`: Windows startup script.
- `start_production.sh`: Linux/macOS startup script.
- `.env.example`: required environment variable examples.
- `icp_system.db`: current SQLite database snapshot.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure

Set these environment variables before startup:

```powershell
$env:PRJ1_SECRET_KEY = "use-a-long-random-secret"
$env:PRJ1_DB_PATH = "D:\PRJ1\data\icp_system.db"
$env:PRJ1_HOST = "0.0.0.0"
$env:PRJ1_PORT = "5000"
```

For a brand new empty database, set `PRJ1_DEFAULT_ADMIN_PASSWORD` before the first startup. Existing database users are preserved.

## Start

```powershell
.\start_production.ps1
```

Open:

```text
http://<server-ip>:5000/login
```

## Notes

- Keep `PRJ1_SECRET_KEY` stable across restarts.
- Back up `icp_system.db` regularly.
- Do not deploy the development `.venv`, `__pycache__`, or `server*.log` files.
