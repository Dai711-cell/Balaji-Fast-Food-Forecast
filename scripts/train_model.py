from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from app.database import seed_from_raw_csv
from app.services.forecasting import train_and_save_model

if __name__ == "__main__":
    seed_from_raw_csv(force=False)
    metadata = train_and_save_model()
    print("Model trained and saved.")
    print(asdict(metadata))
