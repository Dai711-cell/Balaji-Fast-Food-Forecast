
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_DIR / "Balaji Fast Food Sales.csv"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
REPORTS_DIR = PROJECT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
REPORT_PATH = REPORTS_DIR / "daily_quantity_model_report.html"
DATASET_PATH = PROCESSED_DIR / "daily_quantity_modeling_dataset.csv"
PREDICTIONS_PATH = PROCESSED_DIR / "daily_quantity_model_predictions.csv"

RANDOM_STATE = 42
TEST_SIZE = 0.20
TARGET = "quantity_sum"

CATEGORICAL_COLUMNS = [
    "item_name",
    "item_type",
    "transaction_type",
    "received_by",
    "time_of_sale",
]
SHIFTED_BASE_COLUMNS = [
    "quantity_sum",
    "sales_amount",
    "item_price_mean",
    "item_price_sum",
    "order_count",
]
CORE_LAGS = [1, 7, 30]
EXTRA_LAGS = [2, 3, 14]
ALL_LAGS = sorted(set(CORE_LAGS + EXTRA_LAGS))
CORE_ROLLING_WINDOWS = [7, 30]
EXTRA_ROLLING_WINDOWS = [14]
ALL_ROLLING_WINDOWS = sorted(set(CORE_ROLLING_WINDOWS + EXTRA_ROLLING_WINDOWS))


@dataclass
class ModelResult:
    name: str
    estimator: object | None
    predictions: np.ndarray
    mae: float
    rmse: float
    r2: float
    smape: float
    cv_rmse: float | None = None


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
            quantity_sum=("quantity", "sum"),
            sales_amount=("transaction_amount", "sum"),
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
        daily_counts = dummies.groupby("date").sum().sort_index()
        dummy_frames.append(daily_counts)

    daily = pd.concat([numeric_daily] + dummy_frames, axis=1).sort_index()
    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq="D", name="date")
    daily = daily.reindex(full_index)

    count_or_sum_cols = [col for col in daily.columns if col != "item_price_mean"]
    daily[count_or_sum_cols] = daily[count_or_sum_cols].fillna(0)
    daily["item_price_mean"] = daily["item_price_mean"].fillna(0)

    feature_table = pd.DataFrame(index=daily.index)
    feature_table[TARGET] = daily[TARGET]

    # Calendar features are known before the sales day starts, so they do not leak.
    feature_table["day_of_week"] = feature_table.index.dayofweek
    feature_table["day_of_month"] = feature_table.index.day
    feature_table["month"] = feature_table.index.month
    feature_table["week_of_year"] = feature_table.index.isocalendar().week.astype(int)
    feature_table["is_weekend"] = feature_table["day_of_week"].isin([5, 6]).astype(int)
    feature_table["day_of_week_sin"] = np.sin(2 * np.pi * feature_table["day_of_week"] / 7)
    feature_table["day_of_week_cos"] = np.cos(2 * np.pi * feature_table["day_of_week"] / 7)
    feature_table["month_sin"] = np.sin(2 * np.pi * feature_table["month"] / 12)
    feature_table["month_cos"] = np.cos(2 * np.pi * feature_table["month"] / 12)

    for column in SHIFTED_BASE_COLUMNS:
        shifted = daily[column].shift(1)
        feature_table[f"{column}_shift_1"] = shifted
        for lag in ALL_LAGS:
            feature_table[f"{column}_lag_{lag}"] = daily[column].shift(lag)
        for window in ALL_ROLLING_WINDOWS:
            rolling = shifted.rolling(window=window, min_periods=window)
            feature_table[f"{column}_rolling_mean_{window}"] = rolling.mean()
            feature_table[f"{column}_rolling_sum_{window}"] = rolling.sum()
            feature_table[f"{column}_rolling_std_{window}"] = rolling.std()
            feature_table[f"{column}_rolling_min_{window}"] = rolling.min()
            feature_table[f"{column}_rolling_max_{window}"] = rolling.max()
        feature_table[f"{column}_ewm_7"] = shifted.ewm(span=7, adjust=False, min_periods=7).mean()
        feature_table[f"{column}_ewm_30"] = shifted.ewm(span=30, adjust=False, min_periods=30).mean()
        feature_table[f"{column}_expanding_mean"] = shifted.expanding(min_periods=30).mean()

    category_daily_columns = [
        col for col in daily.columns
        if any(col.startswith(f"{base}_") for base in CATEGORICAL_COLUMNS)
    ]
    for column in category_daily_columns:
        shifted = daily[column].shift(1)
        feature_table[f"{column}_shift_1"] = shifted
        feature_table[f"{column}_rolling_sum_7"] = shifted.rolling(window=7, min_periods=7).sum()
        feature_table[f"{column}_rolling_sum_30"] = shifted.rolling(window=30, min_periods=30).sum()

    feature_table = feature_table.dropna().reset_index().rename(columns={"index": "date"})
    return feature_table


def temporal_split(modeling_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series, pd.Series]:
    split_idx = int(len(modeling_df) * (1 - TEST_SIZE))
    train = modeling_df.iloc[:split_idx].copy()
    test = modeling_df.iloc[split_idx:].copy()
    feature_columns = [col for col in modeling_df.columns if col not in ["date", TARGET]]
    return train[feature_columns], test[feature_columns], train[TARGET], test[TARGET], train["date"], test["date"]


def smape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true_arr) + np.abs(y_pred_arr)
    mask = denom != 0
    if not mask.any():
        return 0.0
    return float(np.mean(2 * np.abs(y_pred_arr[mask] - y_true_arr[mask]) / denom[mask]) * 100)


def evaluate_predictions(name: str, estimator: object | None, y_test: pd.Series, predictions: np.ndarray, cv_rmse: float | None = None) -> ModelResult:
    predictions = np.clip(np.asarray(predictions, dtype=float), 0, None)
    return ModelResult(
        name=name,
        estimator=estimator,
        predictions=predictions,
        mae=float(mean_absolute_error(y_test, predictions)),
        rmse=float(np.sqrt(mean_squared_error(y_test, predictions))),
        r2=float(r2_score(y_test, predictions)),
        smape=smape(y_test, predictions),
        cv_rmse=cv_rmse,
    )


def candidate_models() -> dict[str, list[object]]:
    return {
        "Linear Regression": [Pipeline([("scaler", StandardScaler()), ("model", LinearRegression())])],
        "Ridge": [
            Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=alpha))])
            for alpha in [10.0, 50.0]
        ],
        "Lasso": [
            Pipeline([("scaler", StandardScaler()), ("model", Lasso(alpha=alpha, max_iter=30000, random_state=RANDOM_STATE))])
            for alpha in [0.05, 0.1]
        ],
        "ElasticNet": [
            Pipeline([("scaler", StandardScaler()), ("model", ElasticNet(alpha=alpha, l1_ratio=ratio, max_iter=30000, random_state=RANDOM_STATE))])
            for alpha in [0.05, 0.1]
            for ratio in [0.5]
        ],
        "Decision Tree": [
            DecisionTreeRegressor(max_depth=depth, min_samples_leaf=leaf, random_state=RANDOM_STATE)
            for depth in [3, 5]
            for leaf in [5, 10]
        ],
        "Random Forest": [
            RandomForestRegressor(
                n_estimators=200,
                max_depth=depth,
                min_samples_leaf=leaf,
                max_features=max_features,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            for depth in [4, 8]
            for leaf in [5, 10]
            for max_features in ["sqrt"]
        ],
        "Extra Trees": [
            ExtraTreesRegressor(
                n_estimators=200,
                max_depth=depth,
                min_samples_leaf=leaf,
                max_features=max_features,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            for depth in [4, 8]
            for leaf in [5, 10]
            for max_features in ["sqrt"]
        ],
        "Gradient Boosting": [
            GradientBoostingRegressor(
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=depth,
                min_samples_leaf=leaf,
                random_state=RANDOM_STATE,
            )
            for n_estimators in [100, 250]
            for learning_rate in [0.03, 0.05]
            for depth in [2, 3]
            for leaf in [5]
        ],
        "Hist Gradient Boosting": [
            HistGradientBoostingRegressor(
                max_iter=max_iter,
                learning_rate=learning_rate,
                max_leaf_nodes=max_leaf_nodes,
                l2_regularization=l2,
                random_state=RANDOM_STATE,
            )
            for max_iter in [100, 200]
            for learning_rate in [0.05, 0.08]
            for max_leaf_nodes in [7, 15]
            for l2 in [0.0, 0.1]
        ],
    }


def cv_rmse(estimator: object, X: pd.DataFrame, y: pd.Series, n_splits: int = 3) -> float:
    splitter = TimeSeriesSplit(n_splits=n_splits)
    rmses = []
    for train_idx, valid_idx in splitter.split(X):
        X_tr, X_val = X.iloc[train_idx], X.iloc[valid_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[valid_idx]
        model = clone(estimator)
        model.fit(X_tr, y_tr)
        pred = np.clip(model.predict(X_val), 0, None)
        rmses.append(np.sqrt(mean_squared_error(y_val, pred)))
    return float(np.mean(rmses))


def fit_best_models(X_train: pd.DataFrame, X_test: pd.DataFrame, y_train: pd.Series, y_test: pd.Series) -> list[ModelResult]:
    results: list[ModelResult] = []

    baseline_specs = {
        "Naive lag 1": X_test["quantity_sum_lag_1"].to_numpy(),
        "Baseline rolling mean 7": X_test["quantity_sum_rolling_mean_7"].to_numpy(),
        "Baseline rolling mean 30": X_test["quantity_sum_rolling_mean_30"].to_numpy(),
        "Baseline ewm 7": X_test["quantity_sum_ewm_7"].to_numpy(),
        "Baseline ewm 30": X_test["quantity_sum_ewm_30"].to_numpy(),
    }
    for name, pred in baseline_specs.items():
        results.append(evaluate_predictions(name, None, y_test, pred))

    for family, candidates in candidate_models().items():
        best_candidate = None
        best_cv = np.inf
        for estimator in candidates:
            score = cv_rmse(estimator, X_train, y_train)
            if score < best_cv:
                best_cv = score
                best_candidate = estimator
        fitted = clone(best_candidate)
        fitted.fit(X_train, y_train)
        pred = fitted.predict(X_test)
        results.append(evaluate_predictions(family, fitted, y_test, pred, cv_rmse=best_cv))

    return sorted(results, key=lambda result: result.rmse)


def extract_feature_importance(result: ModelResult, feature_names: list[str]) -> pd.DataFrame | None:
    estimator = result.estimator
    if estimator is None:
        return None
    model = estimator.named_steps["model"] if isinstance(estimator, Pipeline) else estimator
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        values = np.abs(np.ravel(model.coef_))
    else:
        return None
    importance = pd.DataFrame({"feature": feature_names, "importance": values})
    return importance.sort_values("importance", ascending=False)


def save_plots(results: list[ModelResult], y_test: pd.Series, test_dates: pd.Series, X_train: pd.DataFrame) -> dict[str, Path]:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    best = results[0]
    paths: dict[str, Path] = {}

    metrics_df = pd.DataFrame([{"model": r.name, "RMSE": r.rmse, "MAE": r.mae} for r in results]).sort_values("RMSE")
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(metrics_df["model"], metrics_df["RMSE"], color="#4E79A7")
    ax.invert_yaxis()
    ax.set_title("Comparacion de modelos por RMSE - quantity diaria")
    ax.set_xlabel("RMSE en unidades diarias")
    fig.tight_layout()
    paths["Comparacion RMSE"] = FIGURES_DIR / "daily_quantity_rmse_comparison.png"
    fig.savefig(paths["Comparacion RMSE"], dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(test_dates, y_test, label="Real", color="#111111", linewidth=2)
    ax.plot(test_dates, best.predictions, label=f"Prediccion - {best.name}", color="#E15759", linewidth=2)
    ax.set_title("Cantidad diaria real vs predicha en test")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Unidades vendidas")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    paths["Real vs predicho"] = FIGURES_DIR / "daily_quantity_actual_vs_predicted.png"
    fig.savefig(paths["Real vs predicho"], dpi=140)
    plt.close(fig)

    residuals = y_test.to_numpy() - best.predictions
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axhline(0, color="#333333", linewidth=1)
    ax.scatter(best.predictions, residuals, color="#59A14F", alpha=0.75)
    ax.set_title(f"Residuales del mejor modelo: {best.name}")
    ax.set_xlabel("Prediccion")
    ax.set_ylabel("Real - Prediccion")
    fig.tight_layout()
    paths["Residuales"] = FIGURES_DIR / "daily_quantity_residuals.png"
    fig.savefig(paths["Residuales"], dpi=140)
    plt.close(fig)

    importance = extract_feature_importance(best, X_train.columns.tolist())
    if importance is not None and not importance.empty:
        top = importance.head(20).sort_values("importance")
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(top["feature"], top["importance"], color="#F28E2B")
        ax.set_title(f"Top 20 variables - {best.name}")
        ax.set_xlabel("Importancia")
        fig.tight_layout()
        paths["Importancia variables"] = FIGURES_DIR / "daily_quantity_feature_importance.png"
        fig.savefig(paths["Importancia variables"], dpi=140)
        plt.close(fig)

    return paths


def dataframe_to_html(df: pd.DataFrame) -> str:
    return df.to_html(index=False, classes="table", border=0, float_format=lambda x: f"{x:,.3f}")


def relative(path: Path) -> str:
    return path.relative_to(REPORTS_DIR).as_posix()


def leakage_audit(feature_columns: Iterable[str]) -> pd.DataFrame:
    shifted_markers = ["_shift_1", "_lag_", "_rolling_", "_ewm_", "_expanding_"]
    transaction_roots = ["quantity_sum", "sales_amount", "item_price", "order_count"] + CATEGORICAL_COLUMNS
    rows = []
    for feature in feature_columns:
        if feature in ["day_of_week", "day_of_month", "month", "week_of_year", "is_weekend", "day_of_week_sin", "day_of_week_cos", "month_sin", "month_cos"]:
            status = "OK: calendario conocido antes del dia"
        elif any(marker in feature for marker in shifted_markers):
            status = "OK: historica/desplazada"
        elif any(root in feature for root in transaction_roots):
            status = "Revisar: posible variable transaccional sin shift"
        else:
            status = "OK"
        rows.append({"feature": feature, "revision": status})
    return pd.DataFrame(rows)


def write_html_report(
    modeling_df: pd.DataFrame,
    results: list[ModelResult],
    paths: dict[str, Path],
    train_dates: pd.Series,
    test_dates: pd.Series,
    X_train: pd.DataFrame,
    y_test: pd.Series,
) -> None:
    best = results[0]
    metrics_df = pd.DataFrame([
        {
            "Modelo": r.name,
            "CV_RMSE_train": r.cv_rmse,
            "MAE_test": r.mae,
            "RMSE_test": r.rmse,
            "R2_test": r.r2,
            "sMAPE_test_%": r.smape,
        }
        for r in results
    ]).sort_values("RMSE_test")

    audit_df = leakage_audit(X_train.columns)
    suspicious = audit_df[audit_df["revision"].str.startswith("Revisar")]

    feature_groups = pd.DataFrame([
        {"Grupo": "Target", "Columnas": "quantity_sum = suma diaria de quantity"},
        {"Grupo": "Calendario", "Columnas": "dia de semana, dia de mes, mes, semana, fin de semana y versiones sin/cos"},
        {"Grupo": "Core lags", "Columnas": "lags 1, 7 y 30 como pidio el objetivo original"},
        {"Grupo": "Lags extra", "Columnas": "lags 2, 3 y 14 para capturar continuidad corta y patron quincenal"},
        {"Grupo": "Rollings", "Columnas": "7, 14 y 30 dias: mean, sum, std, min, max"},
        {"Grupo": "EWM/expanding", "Columnas": "medias exponenciales 7/30 y media historica acumulada"},
        {"Grupo": "Categorias", "Columnas": "producto, tipo, pago, receptor y franja agregados por dia y siempre desplazados"},
    ])

    predictions_df = pd.DataFrame({
        "date": test_dates.values,
        "actual_quantity": y_test.values,
        f"predicted_{best.name}": best.predictions,
        "error": y_test.values - best.predictions,
    })
    predictions_df.to_csv(PREDICTIONS_PATH, index=False, encoding="utf-8")

    image_html = "".join(
        f'<figure><img src="{escape(relative(path))}" alt="{escape(name)}"><figcaption>{escape(name)}</figcaption></figure>'
        for name, path in paths.items()
    )

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Balaji Fast Food Sales - Modelo de Cantidad Diaria</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #202124; background: #fbfbfb; line-height: 1.5; }}
h1, h2, h3 {{ color: #1f2937; }}
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
<h1>Modelo para predecir cantidad diaria vendida</h1>
<p class="notice"><strong>Objetivo corregido:</strong> predecir <code>quantity_sum</code>, la suma diaria de <code>quantity</code>. No se modela importe vendido en este informe.</p>

<h2>Decision sobre granularidad</h2>
<p>Predecir cantidad por producto seria mas util para inventario, pero con este dataset la muestra diaria por producto es pequena y muchas combinaciones dia-producto quedan con poco soporte. Por eso esta version se queda en el objetivo diario agregado, que es mas estable para una primera iteracion.</p>

<h2>Por que se necesita shift</h2>
<p>Para predecir las unidades del dia <code>t</code>, no podemos usar cantidad, importe, producto, tipo de pago, receptor o franja horaria observados en ese mismo dia. Esa informacion solo existe despues de vender. Usarla en entrenamiento seria leakage temporal.</p>
<p>La regla aplicada es: calendario de <code>t</code> si se conoce antes, y variables de ventas solo hasta <code>t-1</code>. Por eso se usan <code>shift(1)</code>, lags y rollings calculados desde series desplazadas.</p>

<h2>Datos y split</h2>
<ul>
<li>Filas de modelado: {len(modeling_df)}</li>
<li>Features: {X_train.shape[1]}</li>
<li>Train: {train_dates.min().date()} a {train_dates.max().date()}</li>
<li>Test: {test_dates.min().date()} a {test_dates.max().date()}</li>
<li>Dataset generado: <code>data/processed/{DATASET_PATH.name}</code></li>
<li>Predicciones test: <code>data/processed/{PREDICTIONS_PATH.name}</code></li>
</ul>

<h2>Mejoras probadas</h2>
{dataframe_to_html(feature_groups)}

<h2>Auditoria anti-leakage</h2>
<p class="{'good' if suspicious.empty else 'warn'}">{'No se detectaron variables transaccionales sin shift.' if suspicious.empty else 'Hay variables que revisar manualmente porque parecen transaccionales sin shift.'}</p>
{dataframe_to_html(audit_df)}

<h2>Comparacion de modelos</h2>
<p>Los modelos se comparan contra baselines naive y se seleccionan con validacion temporal dentro del train cuando tienen hiperparametros.</p>
{dataframe_to_html(metrics_df)}

<h2>Resultado principal</h2>
<p class="good"><strong>{escape(best.name)}</strong> fue el mejor por RMSE en test. RMSE: {best.rmse:,.2f}; MAE: {best.mae:,.2f}; R2: {best.r2:,.3f}; sMAPE: {best.smape:,.2f}%.</p>

<h2>Graficos</h2>
{image_html}

<h2>Lectura honesta</h2>
<ul>
<li>Si el mejor modelo queda cerca de un baseline rolling, significa que la serie diaria tiene poca senal adicional estable.</li>
<li>La mejora valida debe superar baselines sin usar variables del mismo dia.</li>
<li>El siguiente salto util seria tener mas historial o pasar a producto-dia solo si hay suficientes observaciones por producto.</li>
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

    X_train, X_test, y_train, y_test, train_dates, test_dates = temporal_split(modeling_df)
    results = fit_best_models(X_train, X_test, y_train, y_test)
    paths = save_plots(results, y_test, test_dates, X_train)
    write_html_report(modeling_df, results, paths, train_dates, test_dates, X_train, y_test)

    print(f"Saved dataset: {DATASET_PATH}")
    print(f"Saved predictions: {PREDICTIONS_PATH}")
    print(f"Saved report: {REPORT_PATH}")
    print(f"Rows: {len(modeling_df)} | Features: {X_train.shape[1]}")
    print(f"Train: {train_dates.min().date()} -> {train_dates.max().date()} | Test: {test_dates.min().date()} -> {test_dates.max().date()}")
    print(f"Best model: {results[0].name} | RMSE={results[0].rmse:.3f} | MAE={results[0].mae:.3f} | R2={results[0].r2:.3f}")
    print("\nRanking:")
    for result in results:
        print(f"{result.name}\tRMSE={result.rmse:.3f}\tMAE={result.mae:.3f}\tR2={result.r2:.3f}\tsMAPE={result.smape:.2f}\tCV={result.cv_rmse}")


if __name__ == "__main__":
    main()
