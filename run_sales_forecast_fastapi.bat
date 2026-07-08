@echo off
cd /d "%~dp0"
python -m uvicorn sales_forecast_fastapi:app --host 127.0.0.1 --port 8000 --app-dir src
pause
