from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from sales_forecast_api import INDEX_HTML, SalesForecastService


app = FastAPI(
    title="Balaji Sales Forecast API",
    description=(
        "API para predecir ingresos diarios futuros usando el modelo Extra Trees. "
        "Devuelve estimacion central y rangos practicos 50%, 60% y 70%."
    ),
    version="1.0.0",
)

service = SalesForecastService()


class PredictionRequest(BaseModel):
    date: str = Field(..., description="Fecha futura en formato YYYY-MM-DD", examples=["2023-04-15"])


@app.get("/", response_class=HTMLResponse, tags=["frontend"])
def frontend() -> str:
    """Frontend visual para usuarios de negocio."""
    return INDEX_HTML


@app.get("/api/health", tags=["model"])
def health() -> dict[str, Any]:
    """Estado del modelo y ultimo dia real observado."""
    return service.health()


@app.get("/api/predict", tags=["prediction"])
def predict_get(
    date: str = Query(..., description="Fecha futura en formato YYYY-MM-DD", examples=["2023-04-15"])
) -> dict[str, Any]:
    """Predice ingresos para una fecha futura usando query parameter."""
    try:
        return service.predict(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/predict", tags=["prediction"])
def predict_post(payload: PredictionRequest) -> dict[str, Any]:
    """Predice ingresos para una fecha futura usando JSON."""
    try:
        return service.predict(payload.date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
