# Datos

Los datos originales y derivados no se publican en GitHub, siguiendo el mismo criterio usado en DataCo.

## Datos originales

Coloca en la raiz del proyecto:

- `Balaji Fast Food Sales.csv`
- `category distribution.JPG` (opcional, solo como referencia visual)

El CSV debe conservar estas columnas:

```text
order_id,date,item_name,item_type,item_price,quantity,transaction_amount,transaction_type,received_by,time_of_sale
```

La aplicacion admite fechas con `/` o `-` y las normaliza antes de insertarlas.

## Carpetas

- `data/app/`: base SQLite creada localmente por la aplicacion.
- `data/processed/`: tablas derivadas y predicciones regenerables.
- `data/raw/`: espacio reservado para nuevas fuentes sin versionar.

El modelo entrenado de `models/` si se incluye para que la prediccion de portfolio pueda ejecutarse sin publicar el dataset.