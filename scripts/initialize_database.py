from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from app.database import data_summary, seed_from_raw_csv

if __name__ == "__main__":
    inserted = seed_from_raw_csv(force=False)
    summary = data_summary()
    print(f"Database ready. Inserted rows: {inserted}")
    print(summary)
