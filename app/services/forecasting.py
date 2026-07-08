from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.config import MODEL_METADATA_PATH, MODEL_PATH, RANDOM_STATE
from app.database import get_sales_dataframe

TARGET = "sales_amount"
FEATURE_COLUMNS = [
    "day_of_week",
    "day_of_month",
    "month",
    "week_of_year",
    "is_weekend",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",
    "sales_amount_shift_1",
    "sales_amount_lag_1",
    "sales_amount_lag_2",
    "sales_amount_lag_3",
    "sales_amount_lag_7",
    "sales_amount_lag_14",
    "sales_amount_lag_30",
    "sales_amount_rolling_mean_7",
    "sales_amount_rolling_sum_7",
    "sales_amount_rolling_std_7",
    "sales_amount_rolling_min_7",
    "sales_amount_rolling_max_7",
    "sales_amount_rolling_mean_14",
    "sales_amount_rolling_sum_14",
    "sales_amount_rolling_std_14",
    "sales_amount_rolling_min_14",
    "sales_amount_rolling_max_14",
    "sales_amount_rolling_mean_30",
    "sales_amount_rolling_sum_30",
    "sales_amount_rolling_std_30",
    "sales_amount_rolling_min_30",
    "sales_amount_rolling_max_30",
    "sales_amount_ewm_7",
    "sales_amount_ewm_30",
    "sales_amount_expanding_mean",
]


@dataclass
class ForecastMetadata:
    model_name: str
    feature_set: str
    trained_at: str
    first_observed_date: str
    last_observed_date: str
    modeling_rows: int
    validation_rows: int
    validation_mae: float
    validation_rmse: float
    validation_r2: float
    validation_smape: float
    baseline_mae: float
    baseline_rmse: float
    residual_q50: float
    residual_q60: float
    residual_q70: float


def smape(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> float:
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true_arr) + np.abs(y_pred_arr)
    mask = denom != 0
    if not mask.any():
        return 0.0
    return float(np.mean(2 * np.abs(y_pred_arr[mask] - y_true_arr[mask]) / denom[mask]) * 100)


def build_daily_sales_series(sales_df: pd.DataFrame) -> pd.Series:
    daily = sales_df.groupby("date")["transaction_amount"].sum().sort_index()
    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq="D", name="date")
    return daily.reindex(full_index).fillna(0).astype(float)


def calendar_features(date: pd.Timestamp) -> dict[str, float]:
    day_of_week = int(date.dayofweek)
    month = int(date.month)
    return {
        "day_of_week": day_of_week,
        "day_of_month": int(date.day),
        "month": month,
        "week_of_year": int(date.isocalendar().week),
        "is_weekend": int(day_of_week in [5, 6]),
        "day_of_week_sin": float(np.sin(2 * np.pi * day_of_week / 7)),
        "day_of_week_cos": float(np.cos(2 * np.pi * day_of_week / 7)),
        "month_sin": float(np.sin(2 * np.pi * month / 12)),
        "month_cos": float(np.cos(2 * np.pi * month / 12)),
    }


def feature_row_from_history(history: pd.Series, date: pd.Timestamp) -> pd.DataFrame:
    history = history[history.index < date].astype(float)
    if len(history) < 30:
        raise ValueError("At least 30 historical daily observations are required for prediction.")
    values = calendar_features(date)
    values["sales_amount_shift_1"] = float(history.iloc[-1])
    for lag in [1, 2, 3, 7, 14, 30]:
        values[f"sales_amount_lag_{lag}"] = float(history.iloc[-lag])
    for window in [7, 14, 30]:
        window_values = history.iloc[-window:]
        values[f"sales_amount_rolling_mean_{window}"] = float(window_values.mean())
        values[f"sales_amount_rolling_sum_{window}"] = float(window_values.sum())
        values[f"sales_amount_rolling_std_{window}"] = float(window_values.std(ddof=1))
        values[f"sales_amount_rolling_min_{window}"] = float(window_values.min())
        values[f"sales_amount_rolling_max_{window}"] = float(window_values.max())
    values["sales_amount_ewm_7"] = float(history.ewm(span=7, adjust=False, min_periods=7).mean().iloc[-1])
    values["sales_amount_ewm_30"] = float(history.ewm(span=30, adjust=False, min_periods=30).mean().iloc[-1])
    values["sales_amount_expanding_mean"] = float(history.expanding(min_periods=30).mean().iloc[-1])
    return pd.DataFrame([{column: values[column] for column in FEATURE_COLUMNS}])


def build_modeling_dataset(sales_df: pd.DataFrame) -> pd.DataFrame:
    daily_sales = build_daily_sales_series(sales_df)
    rows = []
    for date in daily_sales.index[30:]:
        row = feature_row_from_history(daily_sales, date)
        row.insert(0, "date", date)
        row[TARGET] = float(daily_sales.loc[date])
        rows.append(row)
    if not rows:
        raise ValueError("Not enough daily history to build modeling dataset.")
    return pd.concat(rows, ignore_index=True)


def train_and_save_model() -> ForecastMetadata:
    sales_df = get_sales_dataframe()
    daily_sales = build_daily_sales_series(sales_df)
    modeling_df = build_modeling_dataset(sales_df)
    split_idx = int(len(modeling_df) * 0.80)
    train = modeling_df.iloc[:split_idx].copy()
    test = modeling_df.iloc[split_idx:].copy()

    validation_model = ExtraTreesRegressor(
        n_estimators=500,
        max_depth=8,
        min_samples_leaf=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    validation_model.fit(train[FEATURE_COLUMNS], train[TARGET])
    validation_pred = np.clip(validation_model.predict(test[FEATURE_COLUMNS]), 0, None)
    baseline_pred = test["sales_amount_rolling_mean_30"].to_numpy()
    residual_abs = np.abs(test[TARGET].to_numpy() - validation_pred)

    model = ExtraTreesRegressor(
        n_estimators=500,
        max_depth=8,
        min_samples_leaf=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(modeling_df[FEATURE_COLUMNS], modeling_df[TARGET])

    metadata = ForecastMetadata(
        model_name="Extra Trees Regressor",
        feature_set="target_history_calendar",
        trained_at=datetime.utcnow().isoformat(timespec="seconds"),
        first_observed_date=daily_sales.index.min().strftime("%Y-%m-%d"),
        last_observed_date=daily_sales.index.max().strftime("%Y-%m-%d"),
        modeling_rows=len(modeling_df),
        validation_rows=len(test),
        validation_mae=float(mean_absolute_error(test[TARGET], validation_pred)),
        validation_rmse=float(np.sqrt(mean_squared_error(test[TARGET], validation_pred))),
        validation_r2=float(r2_score(test[TARGET], validation_pred)),
        validation_smape=float(smape(test[TARGET], validation_pred)),
        baseline_mae=float(mean_absolute_error(test[TARGET], baseline_pred)),
        baseline_rmse=float(np.sqrt(mean_squared_error(test[TARGET], baseline_pred))),
        residual_q50=float(np.quantile(residual_abs, 0.50)),
        residual_q60=float(np.quantile(residual_abs, 0.60)),
        residual_q70=float(np.quantile(residual_abs, 0.70)),
    )

    bundle = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "daily_sales": daily_sales,
        "metadata": asdict(metadata),
    }
    joblib.dump(bundle, MODEL_PATH)
    MODEL_METADATA_PATH.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
    return metadata


def ensure_model() -> ForecastMetadata:
    if not MODEL_PATH.exists() or not MODEL_METADATA_PATH.exists():
        return train_and_save_model()
    return ForecastMetadata(**json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8")))


def load_bundle() -> dict[str, Any]:
    ensure_model()
    return joblib.load(MODEL_PATH)


def predict_future(date_text: str) -> dict[str, Any]:
    bundle = load_bundle()
    model = bundle["model"]
    daily_sales: pd.Series = bundle["daily_sales"].copy()
    metadata = ForecastMetadata(**bundle["metadata"])

    try:
        target_date = pd.to_datetime(date_text, format="%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Date must use YYYY-MM-DD format.") from exc

    last_observed = pd.to_datetime(metadata.last_observed_date)
    if target_date <= last_observed:
        raise ValueError(f"Date must be after the last observed date: {metadata.last_observed_date}.")

    forecast_dates = pd.date_range(last_observed + pd.Timedelta(days=1), target_date, freq="D")
    forecast_path = []
    for current_date in forecast_dates:
        row = feature_row_from_history(daily_sales, current_date)
        prediction = float(np.clip(model.predict(row)[0], 0, None))
        daily_sales.loc[current_date] = prediction
        forecast_path.append({"date": current_date.strftime("%Y-%m-%d"), "prediction": round(prediction, 2)})

    point = forecast_path[-1]["prediction"]
    days_ahead = len(forecast_dates)
    horizon_multiplier = math.sqrt(1 + max(days_ahead - 1, 0) / 30)
    intervals = {}
    for label, residual in [("50", metadata.residual_q50), ("60", metadata.residual_q60), ("70", metadata.residual_q70)]:
        margin = float(residual * horizon_multiplier)
        intervals[label] = {
            "lower": round(max(point - margin, 0), 2),
            "upper": round(point + margin, 2),
            "margin": round(margin, 2),
        }

    warnings = ["Ranges are calibrated from historical model errors and widened with forecast horizon."]
    if days_ahead > 60:
        warnings.insert(0, "Long-horizon recursive forecast: uncertainty is higher beyond 60 days.")

    return {
        "requested_date": target_date.strftime("%Y-%m-%d"),
        "last_observed_date": metadata.last_observed_date,
        "days_ahead": days_ahead,
        "prediction": round(point, 2),
        "currency_note": "Same monetary unit as transaction_amount in the source data.",
        "intervals": intervals,
        "model": {
            "name": metadata.model_name,
            "feature_set": metadata.feature_set,
            "trained_at": metadata.trained_at,
            "training_rows": metadata.modeling_rows,
            "validation_mae": round(metadata.validation_mae, 2),
            "validation_rmse": round(metadata.validation_rmse, 2),
            "baseline_mae": round(metadata.baseline_mae, 2),
            "baseline_rmse": round(metadata.baseline_rmse, 2),
        },
        "forecast_path": forecast_path,
        "warnings": warnings,
    }
