from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_DIR / "Balaji Fast Food Sales.csv"
PROCESSED_PATH = PROJECT_DIR / "data" / "processed" / "balaji_fast_food_sales_clean_encoded.csv"

CATEGORICAL_COLUMNS = [
    "item_name",
    "item_type",
    "transaction_type",
    "received_by",
    "time_of_sale",
]


def clean_and_encode(raw_path: Path = RAW_PATH) -> pd.DataFrame:
    """Clean the Balaji Fast Food dataset and one-hot encode categorical columns."""
    df = pd.read_csv(raw_path)

    df.insert(df.columns.get_loc("date"), "date_original", df["date"].astype(str))
    df["date_standardized"] = (
        df["date_original"]
        .str.strip()
        .str.replace("-", "/", regex=False)
    )
    df["date"] = pd.to_datetime(df["date_standardized"], format="%m/%d/%Y", errors="coerce")

    if df["date"].isna().any():
        bad_dates = df.loc[df["date"].isna(), "date_original"].unique().tolist()
        raise ValueError(f"Could not parse these date values: {bad_dates[:20]}")

    for column in CATEGORICAL_COLUMNS:
        df[column] = df[column].astype("string").str.strip().fillna("Unknown")

    df["transaction_type"] = df["transaction_type"].replace({"": "Unknown"}).fillna("Unknown")

    encoded = pd.get_dummies(
        df,
        columns=CATEGORICAL_COLUMNS,
        prefix=CATEGORICAL_COLUMNS,
        prefix_sep="_",
        dtype=int,
    )

    return encoded


def main() -> None:
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    encoded = clean_and_encode()
    encoded.to_csv(PROCESSED_PATH, index=False, encoding="utf-8")
    print(f"Saved {PROCESSED_PATH}")
    print(f"Shape: {encoded.shape[0]} rows x {encoded.shape[1]} columns")
    print(f"Remaining nulls: {int(encoded.isna().sum().sum())}")


if __name__ == "__main__":
    main()
