# Balaji Fast Food Forecast - despliegue sin coste inicial

Este proyecto queda preparado como una demo muy cercana a una venta real, pero pensada para no gastar dinero durante la fase de CV/presentacion.

## Que incluye

- API con FastAPI.
- Frontend de negocio en `/`.
- Panel interno de mantenimiento en `/admin`.
- Documentacion tecnica automatica en `/docs`.
- Base de datos SQLite local en `data/app/sales_forecast.sqlite`.
- Modelo guardado en `models/sales_forecast_model.joblib`.
- Metadatos del entrenamiento en `models/sales_forecast_metadata.json`.
- Carga de CSV, registro manual de ventas y reentrenamiento desde API.
- Rangos de confianza practicos de 50%, 60% y 70%.

## Uso local gratuito

1. Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

2. Inicializar base de datos:

```bash
python scripts/initialize_database.py
```

3. Entrenar modelo:

```bash
python scripts/train_model.py
```

4. Arrancar la aplicacion:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. Abrir:

- Negocio: http://127.0.0.1:8000/
- Panel interno: http://127.0.0.1:8000/admin
- API tecnica: http://127.0.0.1:8000/docs

## Como se actualizan los datos

Hay tres caminos:

1. Subir un CSV desde `/admin` con las mismas columnas que el dataset original.
2. Registrar una venta individual desde `/admin`.
3. Enviar datos desde otro sistema usando los endpoints de `/docs`.

Despues de cargar datos nuevos se debe pulsar `Reentrenar ahora`. En una implantacion real esto podria programarse cada noche o cada semana.

## Seguridad para escritura

Para proteger los endpoints de escritura, define una variable de entorno antes de arrancar:

```bash
set BALAJI_API_KEY=una_clave_interna
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Si la variable no existe, la prediccion sigue disponible, pero la carga de datos, el registro de ventas y el reentrenamiento desde HTTP permanecen deshabilitados (503). No desplegar el panel de administracion ni los endpoints de consulta de ventas en Internet sin autenticacion adicional y controles de acceso.

## Como llevarlo a algo real sin pagar aun

Para CV y demo, lo mejor es grabar o presentar la app corriendo localmente. Si se quiere compartir online sin coste inicial, opciones habituales son Render, Railway o Fly.io en sus capas gratuitas, aunque pueden dormir la app cuando no se usa.

Para una venta real convendria cambiar tres cosas:

- Usar PostgreSQL en lugar de SQLite.
- Guardar credenciales y claves en variables de entorno del servidor.
- Programar un job automatico para importar ventas y reentrenar el modelo.

## Mensaje comercial recomendado

La herramienta no sustituye la decision del negocio: reduce incertidumbre. Su mayor valor aparece cuando se mantiene viva, porque cada semana y cada mes de ventas nuevas ayudan al modelo a aprender tendencia, estacionalidad y cambios de comportamiento.

## Validacion privada antes de insertar datos

El panel `/admin` permite previsualizar un CSV antes de insertarlo. La app muestra:

- Primeras filas originales.
- Primeras filas despues de limpieza automatica.
- Resumen del historico actual frente al CSV limpio.
- Columnas extra ignoradas.
- Nulos detectados en el archivo original.
- Categorias nuevas frente al historico.
- Filas con fechas dentro del rango historico existente.

Esto sirve para revisar si el archivo nuevo concuerda con el dataset principal antes de contaminar la base de datos.

## Aviso de modelo pendiente de reentrenar

Cuando se insertan ventas manuales o CSV nuevos, `/admin` muestra un aviso si el modelo todavia no usa esos datos. Las predicciones solo incorporan esos cambios despues de pulsar `Reentrenar ahora`.
