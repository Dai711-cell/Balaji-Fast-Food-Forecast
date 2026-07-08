from __future__ import annotations

import sqlite3
from datetime import datetime

import pandas as pd

from app.config import DATABASE_PATH, RAW_CSV_PATH

REQUIRED_COLUMNS = [
    "order_id",
    "date",
    "item_name",
    "item_type",
    "item_price",
    "quantity",
    "transaction_amount",
    "transaction_type",
    "received_by",
    "time_of_sale",
]

CATEGORY_COLUMNS = ["item_name", "item_type", "transaction_type", "received_by", "time_of_sale"]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                date TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_price REAL NOT NULL,
                quantity REAL NOT NULL,
                transaction_amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                received_by TEXT NOT NULL,
                time_of_sale TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_raw_date ON sales_raw(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_raw_source ON sales_raw(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_raw_created_at ON sales_raw(created_at)")


def normalize_sales_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df[REQUIRED_COLUMNS].copy()
    out["date"] = out["date"].astype(str).str.strip().str.replace("-", "/", regex=False)
    parsed_date = pd.to_datetime(out["date"], format="%m/%d/%Y", errors="coerce")
    fallback = pd.to_datetime(out.loc[parsed_date.isna(), "date"], errors="coerce", format="mixed")
    parsed_date.loc[parsed_date.isna()] = fallback
    if parsed_date.isna().any():
        bad_values = out.loc[parsed_date.isna(), "date"].head(10).tolist()
        raise ValueError(f"Could not parse date values: {bad_values}")
    out["date"] = parsed_date.dt.strftime("%Y-%m-%d")

    for column in CATEGORY_COLUMNS:
        out[column] = out[column].astype("string").str.strip().fillna("Unknown")
        out[column] = out[column].replace({"": "Unknown"}).fillna("Unknown")

    numeric_columns = ["order_id", "item_price", "quantity", "transaction_amount"]
    for column in numeric_columns:
        out[column] = pd.to_numeric(out[column], errors="coerce")
        if out[column].isna().any():
            raise ValueError(f"Column {column} contains non-numeric values")

    out["order_id"] = out["order_id"].astype(int)
    return out


def dataframe_business_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "rows": 0,
            "first_date": None,
            "last_date": None,
            "distinct_days": 0,
            "total_sales": 0,
            "total_quantity": 0,
            "avg_transaction_amount": 0,
        }
    dates = pd.to_datetime(df["date"])
    return {
        "rows": int(len(df)),
        "first_date": dates.min().strftime("%Y-%m-%d"),
        "last_date": dates.max().strftime("%Y-%m-%d"),
        "distinct_days": int(dates.nunique()),
        "total_sales": float(df["transaction_amount"].sum()),
        "total_quantity": float(df["quantity"].sum()),
        "avg_transaction_amount": float(df["transaction_amount"].mean()),
    }


def category_values() -> dict[str, list[str]]:
    init_db()
    values: dict[str, list[str]] = {}
    with connect() as conn:
        for column in CATEGORY_COLUMNS:
            rows = conn.execute(
                f"SELECT DISTINCT {column} AS value FROM sales_raw ORDER BY {column}"
            ).fetchall()
            values[column] = [row["value"] for row in rows]
    return values


def preview_sales_upload(df: pd.DataFrame, sample_size: int = 10) -> dict:
    raw_columns = list(df.columns)
    raw_nulls = {column: int(df[column].isna().sum()) for column in raw_columns}
    normalized = normalize_sales_dataframe(df)
    historical_summary = data_summary()
    upload_summary = dataframe_business_summary(normalized)
    historical_categories = category_values()
    uploaded_categories = {
        column: sorted(normalized[column].dropna().astype(str).unique().tolist()) for column in CATEGORY_COLUMNS
    }
    new_categories = {
        column: sorted(set(uploaded_categories[column]) - set(historical_categories.get(column, [])))
        for column in CATEGORY_COLUMNS
    }
    overlap_days = 0
    if historical_summary.get("first_date") and historical_summary.get("last_date"):
        upload_dates = pd.to_datetime(normalized["date"])
        start = pd.to_datetime(historical_summary["first_date"])
        end = pd.to_datetime(historical_summary["last_date"])
        overlap_days = int(((upload_dates >= start) & (upload_dates <= end)).sum())

    return {
        "status": "ok",
        "required_columns": REQUIRED_COLUMNS,
        "raw_columns": raw_columns,
        "raw_missing_required": [col for col in REQUIRED_COLUMNS if col not in raw_columns],
        "raw_extra_columns": [col for col in raw_columns if col not in REQUIRED_COLUMNS],
        "raw_nulls": raw_nulls,
        "historical_summary": historical_summary,
        "upload_summary": upload_summary,
        "uploaded_categories": uploaded_categories,
        "new_categories": new_categories,
        "overlap_rows_with_existing_date_range": overlap_days,
        "raw_preview": df.head(sample_size).fillna("").astype(str).to_dict(orient="records"),
        "clean_preview": normalized.head(sample_size).to_dict(orient="records"),
    }


def insert_sales(df: pd.DataFrame, source: str = "manual") -> int:
    normalized = normalize_sales_dataframe(df)
    now = datetime.utcnow().isoformat(timespec="seconds")
    rows = []
    for record in normalized.to_dict(orient="records"):
        rows.append(
            (
                int(record["order_id"]),
                record["date"],
                record["item_name"],
                record["item_type"],
                float(record["item_price"]),
                float(record["quantity"]),
                float(record["transaction_amount"]),
                record["transaction_type"],
                record["received_by"],
                record["time_of_sale"],
                source,
                now,
            )
        )
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO sales_raw (
                order_id, date, item_name, item_type, item_price, quantity,
                transaction_amount, transaction_type, received_by, time_of_sale,
                source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def seed_from_raw_csv(force: bool = False) -> int:
    init_db()
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM sales_raw").fetchone()["n"]
    if count and not force:
        return 0
    if not RAW_CSV_PATH.exists():
        return 0
    if force:
        with connect() as conn:
            conn.execute("DELETE FROM sales_raw")
    df = pd.read_csv(RAW_CSV_PATH)
    return insert_sales(df, source="seed_csv")


def get_sales_dataframe() -> pd.DataFrame:
    init_db()
    with connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT order_id, date, item_name, item_type, item_price, quantity,
                   transaction_amount, transaction_type, received_by, time_of_sale
            FROM sales_raw
            ORDER BY date, id
            """,
            conn,
        )
    if df.empty:
        raise ValueError("No sales data available. Seed or upload data first.")
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    return df


def recent_sales(limit: int = 25) -> list[dict]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT order_id, date, item_name, item_type, item_price, quantity,
                   transaction_amount, transaction_type, received_by, time_of_sale, source, created_at
            FROM sales_raw
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def data_summary() -> dict:
    init_db()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS rows,
                   MIN(date) AS first_date,
                   MAX(date) AS last_date,
                   COUNT(DISTINCT date) AS distinct_days,
                   SUM(transaction_amount) AS total_sales,
                   MAX(created_at) AS last_inserted_at
            FROM sales_raw
            """
        ).fetchone()
    return dict(row)


def pending_model_updates(trained_at: str, model_last_observed_date: str) -> dict:
    init_db()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS rows_inserted_after_training,
                   MIN(date) AS first_pending_date,
                   MAX(date) AS last_pending_date
            FROM sales_raw
            WHERE created_at > ?
            """,
            (trained_at,),
        ).fetchone()
        later_row = conn.execute(
            """
            SELECT COUNT(*) AS rows_after_model_last_date,
                   MIN(date) AS first_date_after_model,
                   MAX(date) AS last_date_after_model
            FROM sales_raw
            WHERE date > ?
            """,
            (model_last_observed_date,),
        ).fetchone()
    pending = dict(row)
    pending.update(dict(later_row))
    pending["needs_retraining"] = bool(
        pending.get("rows_inserted_after_training", 0) or pending.get("rows_after_model_last_date", 0)
    )
    return pending
