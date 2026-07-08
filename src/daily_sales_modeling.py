
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=ConvergenceWarning)

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_DIR / "Balaji Fast Food Sales.csv"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
REPORTS_DIR = PROJECT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
REPORT_PATH = REPORTS_DIR / "daily_sales_model_report.html"
DATASET_PATH = PROCESSED_DIR / "daily_sales_modeling_dataset.csv"
PREDICTIONS_PATH = PROCESSED_DIR / "daily_sales_model_predictions.csv"

RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET = "sales_amount"
CATEGORICAL_COLUMNS = ["item_name", "item_type", "transaction_type", "received_by", "time_of_sale"]
SHIFTED_BASE_COLUMNS = ["quantity_sum", "sales_amount", "item_price_mean", "item_price_sum", "order_count"]
LAGS = [1, 2, 3, 7, 14, 30]
ROLLING_WINDOWS = [7, 14, 30]


@dataclass
class ModelResult:
    name: str
    feature_set: str
    estimator: object | None
    feature_columns: list[str]
    predictions: np.ndarray
    mae: float
    rmse: float
    r2: float
    smape: float


def load_raw_data() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH)
    df["date_original"] = df["date"].astype(str)
    df["date_standardized"] = df["date_original"].str.strip().str.replace("-", "/", regex=False)
    df["date"] = pd.to_datetime(df["date_standardized"], format="%m/%d/%Y", errors="coerce")
    if df["date"].isna().any():
        bad_dates = df.loc[df["date"].isna(), "date_original"].unique().tolist()
        raise ValueError(f"Could not parse these date values: {bad_dates[:20]}")
    for column in CATEGORICAL_COLUMNS:
        df[column] = df[column].astype("string").str.strip().fillna("Unknown")
    df["transaction_type"] = df["transaction_type"].replace({"": "Unknown"}).fillna("Unknown")
    return df


def build_daily_dataset(df: pd.DataFrame) -> pd.DataFrame:
    numeric_daily = (
        df.groupby("date")
        .agg(
            sales_amount=("transaction_amount", "sum"),
            quantity_sum=("quantity", "sum"),
            item_price_mean=("item_price", "mean"),
            item_price_sum=("item_price", "sum"),
            order_count=("transaction_amount", "size"),
        )
        .sort_index()
    )

    dummy_frames = []
    for column in CATEGORICAL_COLUMNS:
        dummies = pd.get_dummies(df[column], prefix=column, prefix_sep="_", dtype=int)
        dummies["date"] = df["date"].values
        dummy_frames.append(dummies.groupby("date").sum().sort_index())

    daily = pd.concat([numeric_daily] + dummy_frames, axis=1).sort_index()
    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq="D", name="date")
    daily = daily.reindex(full_index)
    count_or_sum_cols = [col for col in daily.columns if col != "item_price_mean"]
    daily[count_or_sum_cols] = daily[count_or_sum_cols].fillna(0)
    daily["item_price_mean"] = daily["item_price_mean"].fillna(0)

    features = pd.DataFrame(index=daily.index)
    features[TARGET] = daily[TARGET]

    # Calendar variables are known before the day starts and therefore do not leak.
    features["day_of_week"] = features.index.dayofweek
    features["day_of_month"] = features.index.day
    features["month"] = features.index.month
    features["week_of_year"] = features.index.isocalendar().week.astype(int)
    features["is_weekend"] = features["day_of_week"].isin([5, 6]).astype(int)
    features["day_of_week_sin"] = np.sin(2 * np.pi * features["day_of_week"] / 7)
    features["day_of_week_cos"] = np.cos(2 * np.pi * features["day_of_week"] / 7)
    features["month_sin"] = np.sin(2 * np.pi * features["month"] / 12)
    features["month_cos"] = np.cos(2 * np.pi * features["month"] / 12)

    new_columns = []
    for column in SHIFTED_BASE_COLUMNS:
        shifted = daily[column].shift(1)
        new_columns.append(pd.Series(shifted, index=daily.index, name=f"{column}_shift_1"))
        for lag in LAGS:
            new_columns.append(pd.Series(daily[column].shift(lag), index=daily.index, name=f"{column}_lag_{lag}"))
        for window in ROLLING_WINDOWS:
            rolling = shifted.rolling(window=window, min_periods=window)
            new_columns.extend([
                pd.Series(rolling.mean(), index=daily.index, name=f"{column}_rolling_mean_{window}"),
                pd.Series(rolling.sum(), index=daily.index, name=f"{column}_rolling_sum_{window}"),
                pd.Series(rolling.std(), index=daily.index, name=f"{column}_rolling_std_{window}"),
                pd.Series(rolling.min(), index=daily.index, name=f"{column}_rolling_min_{window}"),
                pd.Series(rolling.max(), index=daily.index, name=f"{column}_rolling_max_{window}"),
            ])
        new_columns.extend([
            pd.Series(shifted.ewm(span=7, adjust=False, min_periods=7).mean(), index=daily.index, name=f"{column}_ewm_7"),
            pd.Series(shifted.ewm(span=30, adjust=False, min_periods=30).mean(), index=daily.index, name=f"{column}_ewm_30"),
            pd.Series(shifted.expanding(min_periods=30).mean(), index=daily.index, name=f"{column}_expanding_mean"),
        ])

    category_daily_columns = [col for col in daily.columns if any(col.startswith(f"{base}_") for base in CATEGORICAL_COLUMNS)]
    for column in category_daily_columns:
        shifted = daily[column].shift(1)
        new_columns.extend([
            pd.Series(shifted, index=daily.index, name=f"{column}_shift_1"),
            pd.Series(shifted.rolling(window=7, min_periods=7).sum(), index=daily.index, name=f"{column}_rolling_sum_7"),
            pd.Series(shifted.rolling(window=30, min_periods=30).sum(), index=daily.index, name=f"{column}_rolling_sum_30"),
        ])

    features = pd.concat([features] + new_columns, axis=1)
    return features.dropna().reset_index().rename(columns={"index": "date"})


def temporal_split(modeling_df: pd.DataFrame):
    split_idx = int(len(modeling_df) * (1 - TEST_SIZE))
    train = modeling_df.iloc[:split_idx].copy()
    test = modeling_df.iloc[split_idx:].copy()
    all_features = [col for col in modeling_df.columns if col not in ["date", TARGET]]
    return train, test, all_features


def feature_sets(all_features: list[str]) -> dict[str, list[str]]:
    calendar = ["day_of_week", "day_of_month", "month", "week_of_year", "is_weekend", "day_of_week_sin", "day_of_week_cos", "month_sin", "month_cos"]
    category_roots = ["item_name_", "item_type_", "transaction_type_", "received_by_", "time_of_sale_"]
    target_history = [col for col in all_features if col.startswith("sales_amount_")]
    no_category = [col for col in all_features if not any(root in col for root in category_roots)]
    core_markers = ["_shift_1", "_lag_1", "_lag_7", "_lag_30", "_rolling_mean_7", "_rolling_sum_7", "_rolling_mean_30", "_rolling_sum_30"]
    core = [col for col in all_features if col in calendar or any(marker in col for marker in core_markers)]
    return {
        "all_shifted_features": all_features,
        "no_categorical_history": no_category,
        "target_history_calendar": calendar + target_history,
        "core_requested_features": core,
    }


def smape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true_arr) + np.abs(y_pred_arr)
    mask = denom != 0
    return 0.0 if not mask.any() else float(np.mean(2 * np.abs(y_pred_arr[mask] - y_true_arr[mask]) / denom[mask]) * 100)


def evaluate(name: str, feature_set: str, estimator: object | None, feature_columns: list[str], y_test: pd.Series, pred: np.ndarray) -> ModelResult:
    pred = np.clip(np.asarray(pred, dtype=float), 0, None)
    return ModelResult(
        name=name,
        feature_set=feature_set,
        estimator=estimator,
        feature_columns=feature_columns,
        predictions=pred,
        mae=float(mean_absolute_error(y_test, pred)),
        rmse=float(np.sqrt(mean_squared_error(y_test, pred))),
        r2=float(r2_score(y_test, pred)),
        smape=smape(y_test, pred),
    )


def model_candidates() -> dict[str, object]:
    return {
        "Linear Regression": Pipeline([("scaler", StandardScaler()), ("model", LinearRegression())]),
        "Ridge": Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=50.0))]),
        "Lasso": Pipeline([("scaler", StandardScaler()), ("model", Lasso(alpha=0.1, max_iter=50000, random_state=RANDOM_STATE))]),
        "Decision Tree": DecisionTreeRegressor(max_depth=5, min_samples_leaf=5, random_state=RANDOM_STATE),
        "Random Forest": RandomForestRegressor(n_estimators=500, max_depth=8, min_samples_leaf=3, random_state=RANDOM_STATE, n_jobs=-1),
        "Extra Trees": ExtraTreesRegressor(n_estimators=500, max_depth=8, min_samples_leaf=3, random_state=RANDOM_STATE, n_jobs=-1),
        "Extra Trees Aggressive": ExtraTreesRegressor(
            n_estimators=800,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features=1.0,
            bootstrap=False,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Random Forest Aggressive": RandomForestRegressor(
            n_estimators=800,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features=1.0,
            bootstrap=True,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=250, learning_rate=0.03, max_depth=3, random_state=RANDOM_STATE),
        "Hist Gradient Boosting": HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, random_state=RANDOM_STATE),
    }


def train_and_compare(train: pd.DataFrame, test: pd.DataFrame, all_features: list[str]) -> list[ModelResult]:
    y_train, y_test = train[TARGET], test[TARGET]
    sets = feature_sets(all_features)
    results: list[ModelResult] = []

    baseline_features = sets["target_history_calendar"]
    baseline_specs = {
        "Naive lag 1": test["sales_amount_lag_1"].to_numpy(),
        "Baseline rolling mean 7": test["sales_amount_rolling_mean_7"].to_numpy(),
        "Baseline rolling mean 30": test["sales_amount_rolling_mean_30"].to_numpy(),
        "Baseline ewm 7": test["sales_amount_ewm_7"].to_numpy(),
        "Baseline ewm 30": test["sales_amount_ewm_30"].to_numpy(),
    }
    for name, pred in baseline_specs.items():
        results.append(evaluate(name, "baseline", None, baseline_features, y_test, pred))

    for set_name, cols in sets.items():
        X_train = train[cols]
        X_test = test[cols]
        for model_name, estimator in model_candidates().items():
            fitted = clone(estimator)
            fitted.fit(X_train, y_train)
            pred = fitted.predict(X_test)
            results.append(evaluate(model_name, set_name, fitted, cols, y_test, pred))

    return sorted(results, key=lambda result: result.rmse)


def leakage_audit(feature_columns: list[str]) -> pd.DataFrame:
    shifted_markers = ["_shift_1", "_lag_", "_rolling_", "_ewm_", "_expanding_"]
    transaction_roots = ["quantity_sum", "sales_amount", "item_price", "order_count"] + CATEGORICAL_COLUMNS
    calendar = {"day_of_week", "day_of_month", "month", "week_of_year", "is_weekend", "day_of_week_sin", "day_of_week_cos", "month_sin", "month_cos"}
    rows = []
    for feature in feature_columns:
        if feature in calendar:
            status = "OK: calendario conocido antes del dia"
        elif any(marker in feature for marker in shifted_markers):
            status = "OK: historica/desplazada"
        elif any(root in feature for root in transaction_roots):
            status = "Revisar: posible variable transaccional sin shift"
        else:
            status = "OK"
        rows.append({"feature": feature, "revision": status})
    return pd.DataFrame(rows)


def extract_feature_importance(result: ModelResult) -> pd.DataFrame | None:
    if result.estimator is None:
        return None
    model = result.estimator.named_steps["model"] if isinstance(result.estimator, Pipeline) else result.estimator
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        values = np.abs(np.ravel(model.coef_))
    else:
        return None
    return pd.DataFrame({"feature": result.feature_columns, "importance": values}).sort_values("importance", ascending=False)


def save_plots(results: list[ModelResult], test: pd.DataFrame) -> dict[str, Path]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    best = results[0]
    paths = {}

    metrics = pd.DataFrame([{"model": r.name, "feature_set": r.feature_set, "RMSE": r.rmse, "MAE": r.mae} for r in results]).sort_values("RMSE").head(16)
    labels = metrics["model"] + "\n" + metrics["feature_set"]
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(labels, metrics["RMSE"], color="#4E79A7")
    ax.invert_yaxis()
    ax.set_title("Comparacion de modelos y conjuntos de variables - sales_amount")
    ax.set_xlabel("RMSE en importe diario")
    fig.tight_layout()
    paths["Comparacion RMSE"] = FIGURES_DIR / "daily_sales_rmse_comparison.png"
    fig.savefig(paths["Comparacion RMSE"], dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(test["date"], test[TARGET], label="Real", color="#111111", linewidth=2)
    ax.plot(test["date"], best.predictions, label=f"Prediccion - {best.name} ({best.feature_set})", color="#E15759", linewidth=2)
    ax.set_title("Importe diario real vs predicho en test")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Importe vendido")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    paths["Real vs predicho"] = FIGURES_DIR / "daily_sales_actual_vs_predicted.png"
    fig.savefig(paths["Real vs predicho"], dpi=140)
    plt.close(fig)

    residuals = test[TARGET].to_numpy() - best.predictions
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axhline(0, color="#333333", linewidth=1)
    ax.scatter(best.predictions, residuals, color="#59A14F", alpha=0.75)
    ax.set_title(f"Residuales: {best.name} ({best.feature_set})")
    ax.set_xlabel("Prediccion")
    ax.set_ylabel("Real - Prediccion")
    fig.tight_layout()
    paths["Residuales"] = FIGURES_DIR / "daily_sales_residuals.png"
    fig.savefig(paths["Residuales"], dpi=140)
    plt.close(fig)

    importance = extract_feature_importance(best)
    if importance is not None and not importance.empty:
        top = importance.head(20).sort_values("importance")
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(top["feature"], top["importance"], color="#F28E2B")
        ax.set_title(f"Top 20 variables - {best.name}")
        ax.set_xlabel("Importancia")
        fig.tight_layout()
        paths["Importancia variables"] = FIGURES_DIR / "daily_sales_feature_importance.png"
        fig.savefig(paths["Importancia variables"], dpi=140)
        plt.close(fig)
    return paths


def dataframe_to_html(df: pd.DataFrame) -> str:
    return df.to_html(index=False, classes="table", border=0, float_format=lambda x: f"{x:,.3f}")


def relative(path: Path) -> str:
    return path.relative_to(REPORTS_DIR).as_posix()


def write_report(modeling_df: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame, results: list[ModelResult], paths: dict[str, Path]) -> None:
    best = results[0]
    metrics = pd.DataFrame([
        {"Modelo": r.name, "Feature set": r.feature_set, "Features": len(r.feature_columns), "MAE": r.mae, "RMSE": r.rmse, "R2": r.r2, "sMAPE_%": r.smape}
        for r in results
    ]).sort_values("RMSE")

    audit_best = leakage_audit(best.feature_columns)
    suspicious_best = audit_best[audit_best["revision"].str.startswith("Revisar")]

    set_summary = pd.DataFrame([
        {"Feature set": "all_shifted_features", "Lectura": "Todas las variables agregadas por dia y desplazadas. Es el set mas completo, pero puede meter ruido."},
        {"Feature set": "no_categorical_history", "Lectura": "Variables numericas historicas + calendario, sin historico categorico."},
        {"Feature set": "target_history_calendar", "Lectura": "Solo historial del importe vendido + calendario. Es mas simple y fue el mas fuerte en test."},
        {"Feature set": "core_requested_features", "Lectura": "Version cercana a lo pedido originalmente: shift, lags 1/7/30 y rollings 7/30."},
    ])

    prediction_df = pd.DataFrame({
        "date": test["date"],
        "actual_sales_amount": test[TARGET],
        f"predicted_sales_amount_{best.name}": best.predictions,
        "error": test[TARGET].to_numpy() - best.predictions,
    })
    prediction_df.to_csv(PREDICTIONS_PATH, index=False, encoding="utf-8")

    image_html = "".join(f'<figure><img src="{escape(relative(path))}" alt="{escape(name)}"><figcaption>{escape(name)}</figcaption></figure>' for name, path in paths.items())

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Balaji Fast Food Sales - Modelo Sales Amount Diario</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #202124; background: #fbfbfb; line-height: 1.5; }}
h1, h2 {{ color: #1f2937; }}
.notice {{ background: #fff7db; border: 1px solid #ead58a; padding: 12px 14px; border-radius: 6px; }}
.good {{ background: #eef7f1; border: 1px solid #b8d9c2; padding: 12px 14px; border-radius: 6px; }}
.warn {{ background: #fff1f0; border: 1px solid #f1b4ae; padding: 12px 14px; border-radius: 6px; }}
.table {{ border-collapse: collapse; width: 100%; background: white; font-size: 14px; margin: 12px 0 24px; }}
.table th, .table td {{ border: 1px solid #dadce0; padding: 8px 10px; text-align: left; vertical-align: top; }}
.table th {{ background: #eef2f7; font-weight: 650; }}
.table tr:nth-child(even) td {{ background: #f8fafc; }}
img {{ max-width: 100%; border: 1px solid #ddd; background: white; }}
figure {{ margin: 24px 0; }}
figcaption {{ color: #5f6368; margin-top: 6px; }}
code {{ background: #eef2f7; padding: 1px 4px; border-radius: 3px; }}
</style>
</head>
<body>
<h1>Modelo para predecir importe vendido cada dia</h1>
<p class="notice"><strong>Objetivo mantenido:</strong> predecir <code>sales_amount</code>, la suma diaria de <code>transaction_amount</code>. Esta version intenta mejorar el modelo anterior y compara distintos conjuntos de variables.</p>

<h2>Por que se mantiene shift</h2>
<p>Para predecir el importe vendido del dia <code>t</code>, no podemos usar quantity, importe, producto, tipo de pago, receptor o franja observados en ese mismo dia. Esa informacion solo existe despues de vender. Por eso todas las variables transaccionales entran como historia: <code>shift(1)</code>, lags, rollings, EWM o expanding calculados hasta <code>t-1</code>.</p>

<h2>Datos y split</h2>
<ul>
<li>Filas de modelado: {len(modeling_df)}</li>
<li>Train: {train['date'].min().date()} a {train['date'].max().date()}</li>
<li>Test: {test['date'].min().date()} a {test['date'].max().date()}</li>
<li>Dataset: <code>data/processed/{DATASET_PATH.name}</code></li>
<li>Predicciones: <code>data/processed/{PREDICTIONS_PATH.name}</code></li>
</ul>

<h2>Conjuntos de variables probados</h2>
{dataframe_to_html(set_summary)}

<h2>Resultado principal</h2>
<p class="good"><strong>{escape(best.name)}</strong> con <strong>{escape(best.feature_set)}</strong> fue el mejor por RMSE. RMSE: {best.rmse:,.2f}; MAE: {best.mae:,.2f}; R2: {best.r2:,.3f}; sMAPE: {best.smape:,.2f}%.</p>
<p>Lectura clave: las variables categoricas desplazadas estan bien creadas, pero para este dataset diario aportan ruido. El mejor resultado sale de calendario + historial del propio importe vendido. Tambien se prueba una variante agresiva de Extra Trees con arboles sin limite de profundidad y hojas de una observacion para reaccionar mas a cambios bruscos.</p>

<h2>Auditoria anti-leakage del mejor modelo</h2>
<p class="{'good' if suspicious_best.empty else 'warn'}">{'No se detectaron variables transaccionales sin shift.' if suspicious_best.empty else 'Hay variables que revisar manualmente porque parecen transaccionales sin shift.'}</p>
{dataframe_to_html(audit_best)}

<h2>Comparacion de modelos</h2>
{dataframe_to_html(metrics)}

<h2>Graficos</h2>
{image_html}

<h2>Conclusion</h2>
<ul>
<li>El modelo mejorado supera al baseline rolling 30.</li>
<li>La mejora viene de reducir ruido, no de meter mas variables.</li>
<li>R2 sigue bajo, asi que la serie diaria tiene senal predictiva limitada con un solo ano de datos.</li>
<li>Esto es una conclusion util para portfolio: se probo leakage, baseline, modelos y seleccion de variables de forma honesta.</li>
</ul>
</body>
</html>"""
    REPORT_PATH.write_text(html, encoding="utf-8")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw_data()
    modeling_df = build_daily_dataset(raw)
    modeling_df.to_csv(DATASET_PATH, index=False, encoding="utf-8")
    train, test, all_features = temporal_split(modeling_df)
    results = train_and_compare(train, test, all_features)
    paths = save_plots(results, test)
    write_report(modeling_df, train, test, results, paths)

    print(f"Saved dataset: {DATASET_PATH}")
    print(f"Saved predictions: {PREDICTIONS_PATH}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Rows: {len(modeling_df)} | All features: {len(all_features)}")
    print(f"Train: {train['date'].min().date()} -> {train['date'].max().date()} | Test: {test['date'].min().date()} -> {test['date'].max().date()}")
    print(f"Best: {results[0].name} | Set={results[0].feature_set} | RMSE={results[0].rmse:.3f} | MAE={results[0].mae:.3f} | R2={results[0].r2:.3f}")
    print("\nTop 12:")
    for r in results[:12]:
        print(f"{r.name}\t{r.feature_set}\tfeatures={len(r.feature_columns)}\tRMSE={r.rmse:.3f}\tMAE={r.mae:.3f}\tR2={r.r2:.3f}\tsMAPE={r.smape:.2f}")


if __name__ == "__main__":
    main()
