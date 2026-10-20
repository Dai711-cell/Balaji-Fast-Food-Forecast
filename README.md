# Balaji Fast Food Sales Forecast

Proyecto personal de análisis predictivo a partir de un dataset público de ventas de Balaji Fast Food; no se desarrolló por encargo del negocio. El proyecto recorre el flujo completo: limpieza, analisis exploratorio, modelado temporal, comparacion contra baseline y entrega mediante una aplicacion FastAPI utilizable por negocio.

## Producto final

La aplicacion incluye tres superficies:

- `/`: prevision diaria de ingresos con rangos de confianza del 50%, 60% y 70%.
- `/admin`: panel técnico de mantenimiento (no forma parte de la interfaz comercial; requiere protección antes de despliegue público).
- `/docs`: documentacion tecnica OpenAPI generada por FastAPI.

El frontend esta orientado a uso comercial: muestra una estimacion principal, sus bandas de incertidumbre y el camino previsto hasta una fecha futura.

## Resultado del modelo

El modelo final es un `ExtraTreesRegressor` con variables de calendario e historicos del objetivo calculados siempre con informacion pasada.

| Metrica | Extra Trees | Baseline rolling 30 dias | Mejora |
|---|---:|---:|---:|
| MAE | 437.41 | 463.52 | 5.63% |
| RMSE | 587.47 | 625.35 | 6.06% |

La validacion es temporal. Los lags y rolling windows se desplazan antes de construir las variables para evitar leakage.

## Funcionalidades

- Prediccion recursiva para cualquier fecha posterior al historico.
- Intervalos practicos calibrados con errores historicos.
- Comparacion del modelo frente a un baseline ingenuo.
- Limpieza automatica de fechas con `/` o `-`, nulos, categorias y tipos numericos.
- Previsualizacion del CSV limpio antes de insertarlo.
- Aviso cuando existen datos nuevos pendientes de reentrenamiento.
- Persistencia local con SQLite.
- Proteccion opcional de endpoints de escritura mediante `BALAJI_API_KEY`.
- Modelo serializado incluido para ejecutar la demo sin publicar los datos originales.

## Inicio rapido

```bash
git clone https://github.com/Dai711-cell/Balaji-Fast-Food-Forecast.git
cd Balaji-Fast-Food-Forecast
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Despues abre:

- Negocio: `http://127.0.0.1:8000/`
- Administracion: `http://127.0.0.1:8000/admin`
- API: `http://127.0.0.1:8000/docs`

En Windows tambien puedes ejecutar `run_balaji_production_like_api.bat`.

## Datos y reentrenamiento

Los datasets no se incluyen en GitHub, igual que en el proyecto DataCo. Para reconstruir la base y entrenar de nuevo:

1. Coloca `Balaji Fast Food Sales.csv` en la raiz.
2. Ejecuta:

```bash
python scripts/initialize_database.py
python scripts/train_model.py
```

El esquema esperado y la politica de datos estan documentados en `data/README.md`.

La demo de prediccion puede arrancar sin el CSV porque `models/sales_forecast_model.joblib` conserva el modelo y la serie diaria necesaria. Para cargar ventas nuevas o reentrenar se necesita proporcionar datos desde el panel interno o mediante el CSV original.

## Estructura

```text
.
|-- app/                         # FastAPI, persistencia, frontend y servicios
|   `-- services/forecasting.py  # features, entrenamiento y prediccion
|-- data/                        # documentacion; datos locales ignorados
|-- docs/                        # guia de despliegue
|-- models/                      # modelo entrenado y metadatos
|-- reports/                     # informes Rmd y figuras
|-- scripts/                     # inicializacion y entrenamiento
|-- src/                         # analisis y experimentos reproducibles
|-- PROJECT_LOG.md               # decisiones y trazabilidad
|-- requirements.txt
`-- README.md
```

## Interpretación del resultado

La mejora del 5,63 % en MAE frente al baseline es modesta. El R² de validación (aprox. 0,077) indica que el modelo explica una parte pequeña de la variación observada. Las bandas del 50 %, 60 % y 70 % son rangos orientativos derivados de los errores de validación, no intervalos de confianza estadística formalmente calibrados.

## Informes principales

- `reports/commercial_sales_forecast_slides.html`: presentacion comercial web de 10 diapositivas para abrir en navegador, sin PowerPoint ni licencia.
- `reports/commercial_sales_forecast_report.html`: informe local regenerable; no está incluido en GitHub.
- `reports/daily_sales_model_report.html`: informe local regenerable; no está incluido en GitHub.
- `reports/extra_trees_vs_baseline_sales_amount.html`: informe local regenerable; no está incluido en GitHub.
- Los archivos `.Rmd` y las figuras permanecen versionados; los HTML regenerables se excluyen, salvo la presentacion web final.

## Decisiones de modelado

- Objetivo: suma diaria de `transaction_amount` (`sales_amount`).
- `order_id` queda fuera del modelo.
- Todos los historicos usan solo valores anteriores al dia predicho.
- Lags principales: 1, 7 y 30 dias, ampliados durante la mejora del modelo.
- Rolling windows principales: 7 y 30 dias, con estadisticas adicionales.
- La calidad se compara siempre contra un baseline antes de recomendar ML.
- Cada semana y cada mes nuevo aportan mucho valor debido al historico disponible; el mantenimiento continuo es parte del producto.

## Seguridad y despliegue

Para proteger las operaciones de escritura:

```powershell
$env:BALAJI_API_KEY="una-clave-interna"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

La guia de evolucion desde demo gratuita hacia una implantacion real esta en `docs/deployment_free.md`.

## Politica del repositorio

- Los datos originales se mantienen intactos y fuera de Git.
- La base SQLite, PID, caches, secretos y datasets procesados no se publican.
- Los cambios importantes se registran en `PROJECT_LOG.md`.
- El modelo entrenado se versiona deliberadamente para que el portfolio sea ejecutable.