from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from daily_sales_modeling import (
    RANDOM_STATE,
    build_daily_dataset,
    feature_sets,
    load_raw_data,
    smape,
    temporal_split,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass
class ModelDiagnostics:
    model_name: str
    feature_set: str
    train_rows: int
    validation_rows: int
    mae: float
    rmse: float
    r2: float
    smape: float
    baseline_mae: float
    baseline_rmse: float
    residual_q50: float
    residual_q60: float
    residual_q70: float


class SalesForecastService:
    """Train and serve daily sales_amount forecasts."""

    def __init__(self) -> None:
        self.raw = load_raw_data()
        self.modeling_df = build_daily_dataset(self.raw)
        all_features = [col for col in self.modeling_df.columns if col not in ["date", "sales_amount"]]
        self.feature_columns = feature_sets(all_features)["target_history_calendar"]
        self.daily_sales = self._daily_sales_series()
        self.last_observed_date = self.daily_sales.index.max()
        self.model = ExtraTreesRegressor(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=3,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        self.diagnostics = self._fit_and_calibrate()

    def _daily_sales_series(self) -> pd.Series:
        daily = self.raw.groupby("date")["transaction_amount"].sum().sort_index()
        full_index = pd.date_range(daily.index.min(), daily.index.max(), freq="D", name="date")
        return daily.reindex(full_index).fillna(0).astype(float)

    def _fit_and_calibrate(self) -> ModelDiagnostics:
        train, test, _ = temporal_split(self.modeling_df)
        validation_model = ExtraTreesRegressor(
            n_estimators=500,
            max_depth=8,
            min_samples_leaf=3,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        validation_model.fit(train[self.feature_columns], train["sales_amount"])
        validation_pred = np.clip(validation_model.predict(test[self.feature_columns]), 0, None)
        baseline_pred = test["sales_amount_rolling_mean_30"].to_numpy()
        residual_abs = np.abs(test["sales_amount"].to_numpy() - validation_pred)

        self.model.fit(self.modeling_df[self.feature_columns], self.modeling_df["sales_amount"])

        return ModelDiagnostics(
            model_name="Extra Trees Regressor",
            feature_set="target_history_calendar",
            train_rows=len(self.modeling_df),
            validation_rows=len(test),
            mae=float(mean_absolute_error(test["sales_amount"], validation_pred)),
            rmse=float(np.sqrt(mean_squared_error(test["sales_amount"], validation_pred))),
            r2=float(r2_score(test["sales_amount"], validation_pred)),
            smape=float(smape(test["sales_amount"], validation_pred)),
            baseline_mae=float(mean_absolute_error(test["sales_amount"], baseline_pred)),
            baseline_rmse=float(np.sqrt(mean_squared_error(test["sales_amount"], baseline_pred))),
            residual_q50=float(np.quantile(residual_abs, 0.50)),
            residual_q60=float(np.quantile(residual_abs, 0.60)),
            residual_q70=float(np.quantile(residual_abs, 0.70)),
        )

    def _calendar_features(self, date: pd.Timestamp) -> dict[str, float]:
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

    def _feature_row(self, sales_history: pd.Series, date: pd.Timestamp) -> pd.DataFrame:
        history = sales_history[sales_history.index < date].astype(float)
        if len(history) < 30:
            raise ValueError("At least 30 historical daily observations are required for this model.")

        values: dict[str, float] = self._calendar_features(date)
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

        return pd.DataFrame([{col: values[col] for col in self.feature_columns}])

    def predict(self, requested_date: str) -> dict:
        try:
            target_date = pd.to_datetime(requested_date, format="%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Date must use YYYY-MM-DD format.") from exc

        if target_date <= self.last_observed_date:
            raise ValueError(f"Date must be after the last observed date: {self.last_observed_date.date()}.")

        forecast_dates = pd.date_range(self.last_observed_date + pd.Timedelta(days=1), target_date, freq="D")
        sales_history = self.daily_sales.copy()
        daily_predictions: list[dict] = []

        for current_date in forecast_dates:
            row = self._feature_row(sales_history, current_date)
            prediction = float(np.clip(self.model.predict(row)[0], 0, None))
            sales_history.loc[current_date] = prediction
            daily_predictions.append({"date": current_date.strftime("%Y-%m-%d"), "prediction": round(prediction, 2)})

        point = daily_predictions[-1]["prediction"]
        days_ahead = len(forecast_dates)
        horizon_multiplier = math.sqrt(1 + max(days_ahead - 1, 0) / 30)
        intervals = {}
        for label, residual in [("50", self.diagnostics.residual_q50), ("60", self.diagnostics.residual_q60), ("70", self.diagnostics.residual_q70)]:
            margin = float(residual * horizon_multiplier)
            intervals[label] = {
                "lower": round(max(point - margin, 0), 2),
                "upper": round(point + margin, 2),
                "margin": round(margin, 2),
            }

        warnings = ["Intervals are calibrated from historical test residuals and widened with forecast horizon."]
        if days_ahead > 60:
            warnings.insert(0, "Long-horizon recursive forecast: uncertainty is higher beyond 60 days.")

        return {
            "requested_date": target_date.strftime("%Y-%m-%d"),
            "last_observed_date": self.last_observed_date.strftime("%Y-%m-%d"),
            "days_ahead": days_ahead,
            "prediction": round(point, 2),
            "currency_note": "Same monetary unit as transaction_amount in the source dataset.",
            "intervals": intervals,
            "model": {
                "name": self.diagnostics.model_name,
                "feature_set": self.diagnostics.feature_set,
                "training_rows": self.diagnostics.train_rows,
                "validation_mae": round(self.diagnostics.mae, 2),
                "validation_rmse": round(self.diagnostics.rmse, 2),
                "baseline_mae": round(self.diagnostics.baseline_mae, 2),
                "baseline_rmse": round(self.diagnostics.baseline_rmse, 2),
            },
            "forecast_path": daily_predictions,
            "warnings": warnings,
        }

    def health(self) -> dict:
        return {
            "status": "ok",
            "model": self.diagnostics.model_name,
            "feature_set": self.diagnostics.feature_set,
            "last_observed_date": self.last_observed_date.strftime("%Y-%m-%d"),
            "training_rows": self.diagnostics.train_rows,
            "validation_mae": round(self.diagnostics.mae, 2),
            "validation_rmse": round(self.diagnostics.rmse, 2),
        }


INDEX_HTML = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Balaji Sales Forecast API</title>
<style>
:root { --bg:#f4f6f8; --ink:#18202a; --muted:#627084; --line:#d8dee8; --green:#2f7d4f; --green-soft:#e7f4ec; --blue:#2f5f9f; --white:#ffffff; }
* { box-sizing: border-box; }
body { margin:0; font-family: Segoe UI, Arial, sans-serif; color:var(--ink); background:var(--bg); }
header { background:#17212f; color:white; padding:22px 32px; }
header h1 { margin:0 0 4px; font-size:24px; }
header p { margin:0; color:#c7d0dd; }
main { max-width:1160px; margin:0 auto; padding:28px; }
.panel { background:var(--white); border:1px solid var(--line); border-radius:8px; padding:20px; margin-bottom:18px; }
.grid { display:grid; grid-template-columns:360px 1fr; gap:18px; align-items:start; }
label { display:block; font-weight:650; margin-bottom:8px; }
input[type="date"] { width:100%; padding:12px; border:1px solid var(--line); border-radius:6px; font-size:16px; }
button { width:100%; margin-top:12px; padding:12px 14px; border:0; border-radius:6px; background:var(--green); color:white; font-size:16px; font-weight:700; cursor:pointer; }
button:hover { filter:brightness(0.95); }
button:disabled { opacity:0.55; cursor:wait; }
.hint { color:var(--muted); font-size:14px; margin-top:10px; }
.cards { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.card { border:1px solid var(--line); border-radius:8px; background:white; padding:14px; min-height:92px; }
.card span { display:block; color:var(--muted); font-size:13px; }
.card strong { display:block; font-size:24px; margin-top:8px; }
.prediction { background:var(--green-soft); border-color:#b8d9c2; }
.prediction strong { color:var(--green); }
.interval-list { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:14px; }
.interval { border:1px solid var(--line); border-radius:8px; padding:14px; background:#fbfcfd; }
.interval h3 { margin:0 0 8px; font-size:16px; }
.range { font-size:19px; font-weight:750; color:var(--blue); }
.margin { color:var(--muted); font-size:13px; margin-top:4px; }
.note { padding:12px 14px; border-radius:6px; background:#fff7df; border:1px solid #ead58a; color:#4c3a13; }
.api-box { background:#0d1520; color:#dbe7f5; border-radius:8px; padding:14px; overflow-x:auto; font-family:Consolas, monospace; font-size:13px; }
.path-table { width:100%; border-collapse:collapse; font-size:14px; }
.path-table th, .path-table td { padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; }
.path-table th { background:#eef2f7; }
.hidden { display:none; }
.error { color:#9b1c1c; background:#fff1f0; border:1px solid #f1b4ae; padding:12px 14px; border-radius:6px; }
@media (max-width:900px) { .grid, .cards, .interval-list { grid-template-columns:1fr; } main { padding:16px; } }
</style>
</head>
<body>
<header><h1>Balaji Sales Forecast</h1><p>Prediccion diaria de ingresos con rangos practicos 50%, 60% y 70%.</p></header>
<main>
<section class="grid">
<div class="panel">
<label for="dateInput">Dia futuro a predecir</label>
<input id="dateInput" type="date">
<button id="predictBtn">Predecir ingresos</button>
<p class="hint" id="dateHint">Cargando informacion del modelo...</p>
<p class="hint">La API predice fechas futuras a partir del ultimo dia observado. Para fechas lejanas, la incertidumbre aumenta.</p>
</div>
<div class="panel">
<div id="error" class="error hidden"></div>
<div id="results" class="hidden">
<div class="cards">
<div class="card prediction"><span>Estimacion central</span><strong id="prediction">-</strong></div>
<div class="card"><span>Fecha solicitada</span><strong id="requestedDate">-</strong></div>
<div class="card"><span>Dias hacia delante</span><strong id="daysAhead">-</strong></div>
<div class="card"><span>Ultimo dato real</span><strong id="lastDate">-</strong></div>
</div>
<h2>Rangos esperados</h2>
<div class="interval-list">
<div class="interval"><h3>50% confianza</h3><div class="range" id="i50">-</div><div class="margin" id="m50"></div></div>
<div class="interval"><h3>60% confianza</h3><div class="range" id="i60">-</div><div class="margin" id="m60"></div></div>
<div class="interval"><h3>70% confianza</h3><div class="range" id="i70">-</div><div class="margin" id="m70"></div></div>
</div>
<p class="note" id="warningText"></p>
</div>
</div>
</section>
<section class="panel"><h2>Como interpretar la prediccion</h2><p>La estimacion central es el ingreso diario esperado. Los rangos 50%, 60% y 70% son bandas practicas basadas en errores historicos del modelo: mas estrechas y faciles de usar para planificacion diaria.</p><p>La herramienta es mas util si se actualiza con nuevos datos cada semana o cada mes. Cada bloque nuevo de ventas ayuda al modelo a reconocer mejor la tendencia reciente.</p></section>
<section class="panel hidden" id="pathSection"><h2>Camino recursivo de prediccion</h2><p class="hint">Si la fecha esta a varios dias, la API predice cada dia intermedio y usa esas estimaciones para llegar al dia solicitado.</p><table class="path-table"><thead><tr><th>Fecha</th><th>Prediccion</th></tr></thead><tbody id="pathBody"></tbody></table></section>
</main>
<script>
const dateInput=document.getElementById('dateInput'); const button=document.getElementById('predictBtn'); const errorBox=document.getElementById('error'); const results=document.getElementById('results'); const dateHint=document.getElementById('dateHint'); const pathSection=document.getElementById('pathSection'); const pathBody=document.getElementById('pathBody');
function money(value){return Number(value).toLocaleString('es-ES',{maximumFractionDigits:2,minimumFractionDigits:2});}
function nextDay(dateStr){const parts=dateStr.split('-').map(Number); const d=new Date(Date.UTC(parts[0],parts[1]-1,parts[2]+1)); return d.toISOString().slice(0,10);}
async function loadHealth(){const res=await fetch('/api/health'); const data=await res.json(); const minDate=nextDay(data.last_observed_date); dateInput.min=minDate; dateInput.value=minDate; dateHint.textContent=`Ultimo dato real: ${data.last_observed_date}. Primera fecha predecible: ${minDate}.`;}
async function predict(){errorBox.classList.add('hidden'); results.classList.add('hidden'); pathSection.classList.add('hidden'); button.disabled=true; button.textContent='Calculando...'; try{const res=await fetch(`/api/predict?date=${encodeURIComponent(dateInput.value)}`); const data=await res.json(); if(!res.ok) throw new Error(data.error||'No se pudo calcular la prediccion.'); document.getElementById('prediction').textContent=money(data.prediction); document.getElementById('requestedDate').textContent=data.requested_date; document.getElementById('daysAhead').textContent=data.days_ahead; document.getElementById('lastDate').textContent=data.last_observed_date; for(const key of ['50','60','70']){const interval=data.intervals[key]; document.getElementById(`i${key}`).textContent=`${money(interval.lower)} - ${money(interval.upper)}`; document.getElementById(`m${key}`).textContent=`margen: +/- ${money(interval.margin)}`;} document.getElementById('warningText').textContent=data.warnings.join(' '); pathBody.innerHTML=''; data.forecast_path.slice(-20).forEach(row=>{const tr=document.createElement('tr'); tr.innerHTML=`<td>${row.date}</td><td>${money(row.prediction)}</td>`; pathBody.appendChild(tr);}); if(data.forecast_path.length>1) pathSection.classList.remove('hidden'); results.classList.remove('hidden');}catch(err){errorBox.textContent=err.message; errorBox.classList.remove('hidden');}finally{button.disabled=false; button.textContent='Predecir ingresos';}}
button.addEventListener('click',predict); loadHealth().then(predict).catch(()=>{dateHint.textContent='No se pudo cargar el modelo.';});
</script>
</body>
</html>'''


SERVICE = SalesForecastService()


class ForecastHandler(BaseHTTPRequestHandler):
    server_version = "BalajiForecastAPI/1.0"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(INDEX_HTML)
            return
        if parsed.path == "/api/health":
            self._send_json(SERVICE.health())
            return
        if parsed.path == "/api/predict":
            query = parse_qs(parsed.query)
            date = query.get("date", [None])[0]
            if not date:
                self._send_json({"error": "Missing required query parameter: date=YYYY-MM-DD"}, 400)
                return
            try:
                self._send_json(SERVICE.predict(date))
            except ValueError as exc:
                self._send_json({"error": str(exc)}, 400)
            except Exception as exc:
                self._send_json({"error": f"Unexpected prediction error: {exc}"}, 500)
            return
        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/predict":
            self._send_json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            date = payload.get("date")
            if not date:
                self._send_json({"error": "Missing required JSON field: date"}, 400)
                return
            self._send_json(SERVICE.predict(date))
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
        except Exception as exc:
            self._send_json({"error": f"Unexpected prediction error: {exc}"}, 500)

    def log_message(self, format: str, *args) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} {format % args}")


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    httpd = ThreadingHTTPServer((host, port), ForecastHandler)
    print(f"Balaji Sales Forecast API running at http://{host}:{port}")
    print(f"Last observed date: {SERVICE.last_observed_date.date()}")
    httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Balaji Sales Forecast API")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--check", action="store_true", help="Run a smoke prediction and exit")
    args = parser.parse_args()
    if args.check:
        next_date = (SERVICE.last_observed_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        result = SERVICE.predict(next_date)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    run(args.host, args.port)


if __name__ == "__main__":
    main()
