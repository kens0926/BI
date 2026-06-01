@echo off
setlocal
cd /d "%~dp0"

echo Starting Internal Audit Management System...
echo URL: http://127.0.0.1:8000
echo Login: admin / admin123
echo.
echo Checking Python dependencies...
python -c "import fastapi, uvicorn, sqlalchemy; print('Dependencies OK')"
if errorlevel 1 (
  echo.
  echo Dependency check failed. Installing requirements...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Install failed. Please keep this window open and share the error message.
    pause
    exit /b 1
  )
)

echo.
echo Server is starting. Keep this window open while using the system.
echo Press Ctrl+C to stop.
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Server stopped or failed to start. Please keep this window open and share the message above.
pause
