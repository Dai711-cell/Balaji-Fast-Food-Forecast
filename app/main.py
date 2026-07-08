from __future__ import annotations

import io
from datetime import timedelta
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.config import APP_API_KEY
from app.database import (
    data_summary,
    insert_sales,
    pending_model_updates,
    preview_sales_upload,
    recent_sales,
    seed_from_raw_csv,
)
from app.pages import ADMIN_HTML, BUSINESS_HTML
from app.services.forecasting import ForecastMetadata, ensure_model, predict_future, train_and_save_model

app = FastAPI(
    title="Balaji Fast Food Sales Forecast",
    description="API y panel interno para predecir ingresos diarios futuros con actualizacion de datos y reentrenamiento local.",
    version="1.0.0",
)


class PredictRequest(BaseModel):
    date: str = Field(..., examples=["2023-04-15"])


class SaleRecord(BaseModel):
    order_id: int
    date: str = Field(..., examples=["2023-04-15"])
    item_name: str
    item_type: str
    item_price: float
    quantity: float
    transaction_amount: float
    transaction_type: str = "Unknown"
    received_by: str
    time_of_sale: str


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if APP_API_KEY and x_api_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def metadata_to_public(metadata: ForecastMetadata) -> dict[str, Any]:
    first_predictable = (pd.to_datetime(metadata.last_observed_date) + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "name": metadata.model_name,
        "feature_set": metadata.feature_set,
        "trained_at": metadata.trained_at,
        "first_observed_date": metadata.first_observed_date,
        "last_observed_date": metadata.last_observed_date,
        "first_predictable_date": first_predictable,
        "training_rows": metadata.modeling_rows,
        "validation_rows": metadata.validation_rows,
        "validation_mae": round(metadata.validation_mae, 2),
        "validation_rmse": round(metadata.validation_rmse, 2),
        "baseline_mae": round(metadata.baseline_mae, 2),
        "baseline_rmse": round(metadata.baseline_rmse, 2),
    }


@app.on_event("startup")
def startup() -> None:
    seed_from_raw_csv(force=False)
    ensure_model()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def business_page() -> str:
    return BUSINESS_HTML


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_page() -> str:
    return ADMIN_HTML


@app.get("/api/health")
def health() -> dict[str, Any]:
    metadata = ensure_model()
    public_model = metadata_to_public(metadata)
    pending = pending_model_updates(metadata.trained_at, metadata.last_observed_date)
    return {
        "status": "ok",
        "data": data_summary(),
        "model": public_model,
        "first_predictable_date": public_model["first_predictable_date"],
        "admin_protected": bool(APP_API_KEY),
        "pending_retraining": pending,
    }


@app.get("/api/predict")
def predict_get(date: str) -> dict[str, Any]:
    try:
        return predict_future(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/predict")
def predict_post(payload: PredictRequest) -> dict[str, Any]:
    return predict_get(payload.date)


@app.get("/api/sales/recent")
def sales_recent(limit: int = 25) -> dict[str, Any]:
    return {"items": recent_sales(limit=max(1, min(limit, 100)))}


@app.post("/api/sales", dependencies=[Depends(require_api_key)])
def sales_create(payload: SaleRecord) -> dict[str, Any]:
    try:
        payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        inserted = insert_sales(pd.DataFrame([payload_dict]), source="manual_api")
        return {"inserted_rows": inserted, "message": "Sale inserted. Retrain the model to include it in future predictions."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/data/preview-csv", dependencies=[Depends(require_api_key)])
async def preview_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
        preview = preview_sales_upload(df)
        preview["filename"] = file.filename
        return preview
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/data/upload-csv", dependencies=[Depends(require_api_key)])
async def upload_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
        inserted = insert_sales(df, source=f"upload:{file.filename}")
        return {"inserted_rows": inserted, "filename": file.filename, "message": "CSV inserted. Retrain the model to use the new data."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/model/retrain", dependencies=[Depends(require_api_key)])
def retrain_model() -> dict[str, Any]:
    try:
        metadata = train_and_save_model()
        public = metadata_to_public(metadata)
        public["pending_retraining"] = pending_model_updates(metadata.trained_at, metadata.last_observed_date)
        return public
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
