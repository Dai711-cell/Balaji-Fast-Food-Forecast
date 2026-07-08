@echo off
cd /d %~dp0
python scripts\initialize_database.py
python scripts\train_model.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
