from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_CSV_PATH = PROJECT_DIR / "Balaji Fast Food Sales.csv"
DATA_DIR = PROJECT_DIR / "data"
APP_DATA_DIR = DATA_DIR / "app"
MODELS_DIR = PROJECT_DIR / "models"
DATABASE_PATH = APP_DATA_DIR / "sales_forecast.sqlite"
MODEL_PATH = MODELS_DIR / "sales_forecast_model.joblib"
MODEL_METADATA_PATH = MODELS_DIR / "sales_forecast_metadata.json"

APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

APP_API_KEY = os.getenv("BALAJI_API_KEY", "")
RANDOM_STATE = 42
TARGET = "sales_amount"
