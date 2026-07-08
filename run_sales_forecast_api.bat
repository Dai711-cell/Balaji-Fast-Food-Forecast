@echo off
cd /d "%~dp0"
python src\sales_forecast_api.py --host 127.0.0.1 --port 8000
pause
