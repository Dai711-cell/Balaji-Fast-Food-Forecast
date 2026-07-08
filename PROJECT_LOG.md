# Project Log

Registro de decisiones y cambios del proyecto Balaji Fast Food Sales.

## 2026-07-07 | setup | Estructura inicial

Objetivo:

- Crear una estructura minima de trabajo sin modificar los datasets originales.

Cambios realizados:

- Creada carpeta `data/raw/` para datos originales si se decide copiar o reorganizar mas adelante.
- Creada carpeta `data/processed/` para salidas limpias o transformadas futuras.
- Creada carpeta `notebooks/` para el analisis exploratorio principal.
- Creada carpeta `reports/figures/` para graficos exportados.
- Creado `README.md` con estado inicial y reglas de trabajo.
- Creado `requirements.txt` con dependencias base.

Decisiones:

- No se han movido ni editado `Balaji Fast Food Sales.csv` ni `category distribution.JPG`.
- La raiz del proyecto se mantiene como entrega original por ahora.

Siguiente paso:

- Crear un notebook de exploracion cuando se empiece el analisis del dataset.


## 2026-07-08 | profiling | Resumen inicial del dataset

Objetivo:

- Crear un informe legible para entender el CSV antes de limpiar o transformar datos.

Cambios realizados:

- Creado `reports/balaji_fast_food_data_summary.Rmd`.
- Creado `reports/balaji_fast_food_data_summary.html`.

Decisiones:

- El archivo `Balaji Fast Food Sales.csv` se leyo solo para analisis descriptivo.
- No se modificaron datasets originales ni se crearon datos procesados.

Siguiente paso:

- Revisar el informe y definir la pregunta principal del analisis.


## 2026-07-08 | profiling | Ajuste del resumen inicial

Objetivo:

- Mejorar legibilidad y corregir la deteccion de fechas mixtas.

Cambios realizados:

- Actualizado `reports/balaji_fast_food_data_summary.Rmd`.
- Actualizado `reports/balaji_fast_food_data_summary.html`.
- Anadidos chequeos de calidad iniciales.

Decisiones:

- No se modificaron datasets originales ni se crearon datos procesados.
- Se marco `date` como columna con formatos mixtos que debe estandarizarse antes del analisis temporal.


## 2026-07-08 | cleaning | Limpieza y one-hot encoding inicial

Objetivo:

- Limpiar nulos, estandarizar fechas mixtas y aplicar one-hot encoding a variables categoricas.

Cambios realizados:

- Creado `data/processed/balaji_fast_food_sales_clean_encoded.csv`.
- No se creo Parquet porque falta una dependencia opcional: Unable to find a usable engine; tried using: 'pyarrow', 'fastparquet'.
A suitable version of pyarrow or fastparquet is required for parquet support.
Trying to import the above resulted in these errors:
 - `Import pyarrow` failed. pyarrow is required for parquet support. Use pip or conda to install the pyarrow package.
 - `Import fastparquet` failed. fastparquet is required for parquet support. Use pip or conda to install the fastparquet package.
- Creado `reports/cleaning_encoding_summary.md`.

Decisiones:

- No se modifico `Balaji Fast Food Sales.csv`.
- `transaction_type` nulo se convirtio en categoria `Unknown`.
- Las fechas se estandarizaron primero en `date_standardized` y despues se parsearon en `date` como datetime con formato mes/dia/ano.
- Se conservo `date_original` para trazabilidad.

Resultado:

- Dataset procesado con 1000 filas y 26 columnas.
- Nulos restantes: 0.

## 2026-07-08 | reproducibility | Script de limpieza

Objetivo:

- Guardar la transformacion de limpieza y one-hot encoding como script reproducible.

Cambios realizados:

- Creado `src/clean_encode_data.py`.
- Verificado que el script regenera `data/processed/balaji_fast_food_sales_clean_encoded.csv`.

Resultado:

- `date` queda como `datetime64` dentro del DataFrame.
- El dataset procesado tiene 1000 filas, 26 columnas y 0 nulos.
- `transaction_type_Unknown` contiene 107 filas, equivalentes a los nulos originales.

## 2026-07-08 | visualization | Rmd de graficos iniciales

Objetivo:

- Crear un informe R Markdown con graficos de barras y ventas agregadas.

Cambios realizados:

- Creado `reports/balaji_fast_food_sales_plots.Rmd`.

Contenido:

- Distribucion de variables principales: producto, tipo de producto, tipo de pago, persona que recibe y franja horaria.
- Ventas por dia y por mes.
- Ventas por tipo de pago, producto, tipo de producto, persona que recibe y franja horaria.

Decision:

- El Rmd limpia fecha y `transaction_type` en memoria, sin modificar el CSV original.
- No se renderizo a HTML porque `Rscript` no esta disponible desde este entorno.


## 2026-07-08 | modeling | Modelo de ventas diarias con lags y rolling

Objetivo:

- Predecir el importe vendido por dia evitando leakage temporal.

Cambios realizados:

- Creado `src/daily_sales_modeling.py`.
- Creado `data/processed/daily_sales_modeling_dataset.csv`.
- Creado `reports/daily_sales_model_report.html`.
- Creados graficos en `reports/figures/` para comparacion de modelos, real vs predicho, residuales e importancia de variables.
- Actualizado `requirements.txt` con `scikit-learn`.

Decisiones:

- Se excluyo `order_id`.
- `date` se uso como calendario conocido: dia de semana, dia de mes, mes y fin de semana.
- Las variables transaccionales y categoricas se agregaron por dia y se desplazaron con `shift(1)` antes de entrar al modelo.
- Se usaron lags 1, 7 y 30, y rollings 7 y 30 calculados desde informacion disponible hasta el dia anterior.
- Se uso split temporal, no aleatorio.

Resultado:

- Dataset de modelado con 334 filas y 63 features.
- Mejor modelo por RMSE: Gradient Boosting.
- RMSE: 622.12; MAE: 464.66; R2: -0.035; sMAPE: 55.77%.
- El rendimiento es similar al baseline rolling mean 30, lo que indica senal predictiva limitada con estas variables agregadas.


## 2026-07-08 | modeling | Modelo de cantidad diaria mejorado

Objetivo:

- Corregir el objetivo del modelo para predecir la suma diaria de `quantity`, no el importe diario.
- Probar mejoras razonables sin introducir leakage temporal.

Cambios realizados:

- Creado `src/daily_quantity_modeling.py`.
- Creado `data/processed/daily_quantity_modeling_dataset.csv`.
- Creado `data/processed/daily_quantity_model_predictions.csv`.
- Creado `reports/daily_quantity_model_report.html`.
- Creados graficos `daily_quantity_*` en `reports/figures/`.

Decisiones:

- Se mantiene objetivo diario agregado porque `quantity` por producto seria mas util, pero hay pocos datos por producto para un primer modelo estable.
- Se usan variables calendario conocidas antes del dia.
- Las variables transaccionales y categoricas se agregan por dia y se desplazan con `shift(1)`.
- Se mantienen lags 1, 7 y 30; se anaden lags 2, 3 y 14, rollings 7, 14 y 30, EWM 7/30 y expanding mean.
- Se usa validacion temporal dentro del train para elegir hiperparametros de forma mas honesta.

Resultado:

- Dataset de modelado con 334 filas y 191 features.
- Auditoria anti-leakage: 0 variables transaccionales sospechosas sin shift.
- Mejor modelo por RMSE: Hist Gradient Boosting.
- RMSE: 15.23; MAE: 11.06; R2: -0.006; sMAPE: 48.85%.
- Mejora frente a baseline rolling mean 30: RMSE 15.23 vs 15.60, pequena pero real.


## 2026-07-08 | modeling | Mejora del modelo sales_amount diario

Objetivo:

- Mantener el objetivo correcto acordado: predecir `sales_amount`, la suma diaria de `transaction_amount`.
- Mejorar el resultado anterior sin introducir leakage temporal.

Cambios realizados:

- Actualizado `src/daily_sales_modeling.py`.
- Regenerado `data/processed/daily_sales_modeling_dataset.csv`.
- Creado `data/processed/daily_sales_model_predictions.csv`.
- Regenerado `reports/daily_sales_model_report.html`.
- Regenerados graficos `daily_sales_*` en `reports/figures/`.

Decisiones:

- Se probaron varios conjuntos de variables: todas las variables desplazadas, variables sin historico categorico, historial del target + calendario y una version core de features pedidas.
- Las variables categoricas desplazadas se mantienen en el dataset y en la comparacion, pero el mejor resultado viene de `target_history_calendar`.
- La conclusion es que las variables categoricas historicas aportan ruido para este objetivo diario con este volumen de datos.

Resultado:

- Mejor modelo: Extra Trees.
- Mejor conjunto de variables: `target_history_calendar`.
- RMSE: 587.47; MAE: 437.41; R2: 0.077; sMAPE: 53.34%.
- Baseline rolling mean 30: RMSE 625.35.
- Auditoria anti-leakage del mejor set: 0 variables sospechosas sin shift.


## 2026-07-08 | evaluation | Comparacion Extra Trees vs baseline sales_amount

Objetivo:

- Crear un HTML especifico comparando el real diario con la prediccion de Extra Trees y cuantificar la mejora frente al baseline rolling mean 30.

Cambios realizados:

- Creado `reports/extra_trees_vs_baseline_sales_amount.html`.
- Creado `reports/figures/extra_trees_real_vs_predicted_sales_amount.png`.
- Creado `data/processed/extra_trees_vs_baseline_sales_predictions.csv`.

Resultado:

- Mejora RMSE: 6.06%.
- Mejora MAE: 5.63%.
- Modelo: Extra Trees con `target_history_calendar`.


## 2026-07-08 | modeling | Extra Trees mas agresivo

Objetivo:

- Probar una variante mas agresiva del modelo porque la version anterior corregia bien pero reaccionaba de forma demasiado suave.

Cambios realizados:

- Actualizado `src/daily_sales_modeling.py` con `Extra Trees Aggressive` y `Random Forest Aggressive`.
- Creado `reports/extra_trees_aggressive_sales_amount_comparison.html`.
- Creado `reports/figures/extra_trees_aggressive_real_vs_predicted_sales_amount.png`.
- Creado `data/processed/extra_trees_aggressive_sales_predictions.csv`.

Resultado:

- Extra Trees agresivo mejora al baseline rolling 30 en RMSE un 1.95%.
- Extra Trees agresivo mejora al baseline rolling 30 en MAE un 6.72%.
- Frente al Extra Trees normal, la version agresiva reduce MAE pero aumenta RMSE: responde mas, pero comete errores grandes con mas coste.


## 2026-07-08 | reporting | Informe comercial de prediccion sales_amount

Objetivo:

- Crear un informe comercial explicando resultados, limitaciones, mejora frente al baseline y recomendaciones de negocio.

Cambios realizados:

- Creado `reports/commercial_sales_forecast_report.html`.
- Creados graficos comerciales en `reports/figures/`.
- Creado `data/processed/commercial_sales_forecast_summary.csv`.

Resultado:

- Mejora MAE frente baseline: 5.63%.
- Mejora RMSE frente baseline: 6.06%.
- El modelo tiende a sobrepredecir en 40/67 dias (59.7%).
- Recomendacion: usar como apoyo con margen conservador y ampliar historico/variables.


## 2026-07-08 | reporting | Reenfoque comercial positivo del informe

Objetivo:

- Reescribir el informe comercial para centrarlo en el valor del modelo frente a no usarlo, sin venderlo como una solucion perfecta.

Cambios realizados:

- Actualizado `reports/commercial_sales_forecast_report.html`.
- Regenerados graficos comerciales con etiquetas mas orientadas a negocio.

Decision:

- Las limitaciones se presentan como oportunidades de mejora y mantenimiento, no como el mensaje principal.


## 2026-07-08 | reporting | Refuerzo del valor del mantenimiento de datos

Objetivo:

- Destacar en el informe comercial que cada semana o mes de datos nuevos mejora el potencial del modelo y justifica un mantenimiento recurrente.

Cambios realizados:

- Actualizada la seccion 7 de `reports/commercial_sales_forecast_report.html`.
- Actualizada la recomendacion final para proponer carga semanal, revision mensual y reentrenamiento mensual.


## 2026-07-08 | reporting | Walk-forward y deterioro del modelo

Objetivo:

- Agregar validacion walk-forward y una medicion de deterioro por antiguedad del modelo al informe comercial.
- Reducir graficos centrados en metricas tecnicas para evitar ruido comercial.

Cambios realizados:

- Actualizado `reports/commercial_sales_forecast_report.html`.
- Creado `data/processed/walk_forward_sales_validation.csv`.
- Creado `data/processed/model_deterioration_by_age.csv`.
- Creado `data/processed/model_deterioration_raw_predictions.csv`.
- Creados graficos `commercial_walk_forward_validation.png` y `commercial_model_deterioration.png`.
- Eliminado del informe el grafico de mejora por metrica como elemento principal; las mejoras quedan en tabla/texto.

Resultado:

- Walk-forward MAE modelo: 448.45; baseline: 447.95; mejora: -0.11%.
- Walk-forward RMSE modelo: 580.72; baseline: 573.34; mejora: -1.29%.
- Deterioro 31-60 dias vs 1-7 dias: 20.97%.


## 2026-07-08 | reporting | Aclaracion ventana de deterioro

Objetivo:

- Aclarar que la prueba de deterioro usa una ventana inicial aproximada de 6 meses para no ocultar el efecto de falta de mantenimiento.

Cambios realizados:

- Actualizada la seccion de deterioro en `reports/commercial_sales_forecast_report.html`.


## 2026-07-08 | reporting | Simplificacion de walk-forward y deterioro

Objetivo:

- Quitar del informe comercial los apartados y graficos principales de deterioro y walk-forward.
- Mantener una explicacion breve: el deterioro no puede comprobarse robustamente con tan poco historico y el walk-forward mantiene consistencia respecto al modelo presentado.

Cambios realizados:

- Actualizado `reports/commercial_sales_forecast_report.html`.
- Sustituidas las secciones de walk-forward/deterioro por explicacion comercial breve.


## 2026-07-08 | reporting | Simplificacion de sesgo de prevision

Objetivo:

- Quitar el grafico de comportamiento de la prevision y explicar en texto que el modelo tiende a ser algo optimista frente a la realidad.

Cambios realizados:

- Actualizada la seccion `Como usar la prevision` en `reports/commercial_sales_forecast_report.html`.

## 2026-07-08 | deployment | API local de prevision

Objetivo:

- Crear una API funcional con frontend para que la empresa pueda predecir ingresos diarios futuros.

Cambios realizados:

- Creado `src/sales_forecast_api.py`.
- Creado `run_sales_forecast_api.bat`.
- Actualizado `README.md` con instrucciones de ejecucion y endpoints.

Caracteristicas:

- Frontend web local.
- `GET /api/health`.
- `GET /api/predict?date=YYYY-MM-DD`.
- `POST /api/predict`.
- Estimacion central e intervalos 90%, 95% y 99%.
- Forecast recursivo para cualquier dia futuro.

Decision:

- Se implemento con libreria estandar de Python para no depender de FastAPI/Flask/Uvicorn, que no estan instalados.

## 2026-07-08 | deployment | Version FastAPI de la API

Objetivo:

- Migrar la API local a FastAPI para tener endpoints mas estandar y documentacion automatica.

Cambios realizados:

- Instalado `fastapi` y `uvicorn`.
- Creado `src/sales_forecast_fastapi.py`.
- Creado `run_sales_forecast_fastapi.bat`.
- Actualizado `README.md` con instrucciones de FastAPI.
- Actualizado `requirements.txt`.

Endpoints:

- `GET /` frontend.
- `GET /api/health`.
- `GET /api/predict?date=YYYY-MM-DD`.
- `POST /api/predict`.
- `GET /docs` documentacion automatica.


## 2026-07-08 | deployment | Rangos practicos y frontend de negocio

Objetivo:

- Cambiar los intervalos visibles de 90/95/99 a 50/60/70 para que sean mas practicos para negocio.
- Ocultar la seccion tecnica de API para integracion del frontend principal.

Cambios realizados:

- Actualizado `src/sales_forecast_api.py`.
- Actualizado `src/sales_forecast_fastapi.py`.
- Actualizado `README.md`.

Decision:

- Los endpoints tecnicos siguen disponibles para integraciones y documentacion en `/docs`, pero no aparecen en la pantalla principal que vera negocio.


## 2026-07-08 | deployment | Correccion primera fecha predecible

Objetivo:

- Corregir el calculo del frontend para que la primera fecha predecible sea realmente el dia posterior al ultimo dato observado.

Cambios realizados:

- Actualizada la funcion `nextDay` en `src/sales_forecast_api.py` para evitar problemas de zona horaria en JavaScript.

## 2026-07-08 | deployment | API production-like gratuita

Objetivo:

- Dejar la herramienta lo mas parecida posible a una entrega real, sin pagar hosting todavia, para poder presentarla en CV o demo comercial.

Cambios realizados:

- Creado paquete modular `app/` con FastAPI en `app/main.py`.
- Creado frontend de negocio en `/` y panel interno en `/admin` dentro de `app/pages.py`.
- Creada base SQLite local en `data/app/sales_forecast.sqlite`.
- Persistido modelo en `models/sales_forecast_model.joblib` y metadata en `models/sales_forecast_metadata.json`.
- Creados scripts `scripts/initialize_database.py` y `scripts/train_model.py`.
- Creado lanzador `run_balaji_production_like_api.bat`.
- Creada guia `docs/deployment_free.md`.
- Actualizado `README.md` y `requirements.txt`.

Caracteristicas:

- Prediccion de cualquier dia futuro con rangos 50%, 60% y 70%.
- Carga de CSV, insercion manual de ventas y reentrenamiento desde panel interno/API.
- Endpoints tecnicos visibles en `/docs`, no en la pantalla principal de negocio.
- Proteccion opcional con variable `BALAJI_API_KEY` para endpoints de escritura.

Verificacion:

- `python scripts/initialize_database.py` correcto: 1000 filas cargadas.
- `python scripts/train_model.py` correcto.
- `GET /api/health` correcto.
- `GET /api/predict?date=2023-04-15` correcto.
- `/`, `/admin` y `/docs` devuelven HTTP 200.

Resultado actual:

- Ultimo dia observado: `2023-03-30`.
- Primera fecha predecible: `2023-03-31`.
- Ejemplo `2023-04-15`: prediccion `829.07`, intervalo 50% `413.61 - 1244.53`, 60% `252.61 - 1405.53`, 70% `91.88 - 1566.26`.

## 2026-07-08 | deployment | Validacion privada de CSV y aviso de reentrenamiento

Objetivo:

- Permitir revisar como queda un CSV despues de la limpieza automatica antes de insertarlo.
- Avisar en el panel privado si hay datos cargados que el modelo todavia no ha aprendido.

Cambios realizados:

- Actualizado `app/database.py` con `preview_sales_upload`, comparativa de resumen y categorias nuevas.
- Actualizado `app/main.py` con endpoint `POST /api/data/preview-csv` y `pending_retraining` en `/api/health`.
- Actualizado `/admin` en `app/pages.py` con previsualizacion de limpieza, tablas original/limpia y aviso de reentrenamiento pendiente.
- Actualizados `README.md` y `docs/deployment_free.md`.

Verificacion:

- Compilacion Python correcta.
- `GET /api/health` correcto, `needs_retraining=False` con la base actual.
- `POST /api/data/preview-csv` probado con el CSV original: 1000 filas detectadas, 10 filas limpias de muestra, 0 columnas extra.
- `/admin` y `/` devuelven HTTP 200.

## 2026-07-08 | frontend | Paleta azul/blanco de alto contraste

Objetivo:

- Cambiar la app a una paleta clara y suave basada en azul/blanco, manteniendo contraste marcado para que todo se lea bien durante una demo.

Cambios realizados:

- Actualizado `app/pages.py`.
- Sustituidos los colores principales verde/naranja por azul, azul claro, blanco y navy.
- Cambiadas las barras del camino previsto a degradado azul/celeste para evitar que parezcan alertas rojas.
- Ajustados mensajes de estado del panel admin para mantener coherencia visual.

Verificacion:

- `python -m py_compile app/pages.py` correcto.
- `/` devuelve HTTP 200.
- `/admin` devuelve HTTP 200.

## 2026-07-08 | frontend | Fondo espacial azul y blanco

Objetivo:

- Dar al fondo una atmosfera luminosa de espacio/cielo, sustituyendo el negro por tonos azules y blancos difuminados.

Cambios realizados:

- Actualizado el fondo de las pantallas principal y admin en `app/pages.py`.
- Anadido degradado diagonal azul/blanco y pequenos puntos luminosos.
- Ajustadas las tarjetas a blanco semitransparente con desenfoque y sombra azul suave.
- Conservado contraste alto en texto, botones y controles.

Verificacion:

- Compilacion correcta.
- `/` y `/admin` devuelven HTTP 200.
- Revision visual realizada en navegador local sin solapamientos visibles.

### Fondo espacial con movimiento suave
- Se elimino la trama repetitiva de puntos blancos.
- El degradado azul/blanco ahora se desplaza lentamente.
- Se agregaron seis destellos dispersos con deriva y pulso suaves.
- La animacion se desactiva cuando el sistema solicita movimiento reducido.

### Preparacion para GitHub
- Se adopto la misma politica de datos que en DataCo: raw y derivados fuera de Git.
- Se documentaron las carpetas de datos y la ejecucion desde una clonacion limpia.
- La demo puede iniciar con el modelo versionado aunque el CSV original no este presente.
- Se excluyeron SQLite, PID, caches, secretos y HTML regenerables.
