# Cleaning and Encoding Summary

## Objetivo

Limpiar nulos, estandarizar fechas y codificar variables categoricas del dataset Balaji Fast Food Sales sin modificar el CSV original.

## Archivos generados

- `data/processed/balaji_fast_food_sales_clean_encoded.csv`
- No se creo Parquet porque falta una dependencia opcional: Unable to find a usable engine; tried using: 'pyarrow', 'fastparquet'.
A suitable version of pyarrow or fastparquet is required for parquet support.
Trying to import the above resulted in these errors:
 - `Import pyarrow` failed. pyarrow is required for parquet support. Use pip or conda to install the pyarrow package.
 - `Import fastparquet` failed. fastparquet is required for parquet support. Use pip or conda to install the fastparquet package.

## Cambios aplicados

| Paso | Decision |
| --- | --- |
| Fecha original | Se conserva en `date_original` para trazabilidad. |
| Estructura intermedia de fecha | Se crea `date_standardized`, reemplazando `-` por `/`. |
| Fecha final | `date` se parsea como datetime usando formato `%m/%d/%Y`. |
| Nulos en `transaction_type` | Se imputan como `Unknown`, no como `Cash` ni `Online`. |
| One-hot encoding | Se aplica a `item_name`, `item_type`, `transaction_type`, `received_by`, `time_of_sale`. |
| Dataset original | No se modifica. |

## Resultado

| Metrica | Valor |
| --- | --- |
| Filas originales | 1000 |
| Columnas originales | 10 |
| Filas procesadas | 1000 |
| Columnas antes de one-hot | 12 |
| Columnas despues de one-hot | 26 |
| Columnas one-hot creadas | 19 |
| Nulos restantes | 0 |
| Fecha minima | 2022-04-01 |
| Fecha maxima | 2023-03-30 |

## Columnas one-hot creadas

- `item_name_Aalopuri`
- `item_name_Cold coffee`
- `item_name_Frankie`
- `item_name_Panipuri`
- `item_name_Sandwich`
- `item_name_Sugarcane juice`
- `item_name_Vadapav`
- `item_type_Beverages`
- `item_type_Fastfood`
- `transaction_type_Cash`
- `transaction_type_Online`
- `transaction_type_Unknown`
- `received_by_Mr.`
- `received_by_Mrs.`
- `time_of_sale_Afternoon`
- `time_of_sale_Evening`
- `time_of_sale_Midnight`
- `time_of_sale_Morning`
- `time_of_sale_Night`

## Vista rapida del dataset procesado

| order_id | date_original | date | item_price | quantity | transaction_amount | date_standardized | item_name_Aalopuri | item_name_Cold coffee | item_name_Frankie | item_name_Panipuri | item_name_Sandwich | item_name_Sugarcane juice | item_name_Vadapav | item_type_Beverages | item_type_Fastfood | transaction_type_Cash | transaction_type_Online | transaction_type_Unknown | received_by_Mr. | received_by_Mrs. | time_of_sale_Afternoon | time_of_sale_Evening | time_of_sale_Midnight | time_of_sale_Morning | time_of_sale_Night |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 07-03-2022 | 2022-07-03 00:00:00 | 20 | 13 | 260 | 07/03/2022 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2 | 8/23/2022 | 2022-08-23 00:00:00 | 20 | 15 | 300 | 8/23/2022 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| 3 | 11/20/2022 | 2022-11-20 00:00:00 | 20 | 1 | 20 | 11/20/2022 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| 4 | 02-03-2023 | 2023-02-03 00:00:00 | 25 | 6 | 150 | 02/03/2023 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| 5 | 10-02-2022 | 2022-10-02 00:00:00 | 25 | 8 | 200 | 10/02/2022 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| 6 | 11/14/2022 | 2022-11-14 00:00:00 | 20 | 10 | 200 | 11/14/2022 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| 7 | 05-03-2022 | 2022-05-03 00:00:00 | 25 | 9 | 225 | 05/03/2022 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| 8 | 12/22/2022 | 2022-12-22 00:00:00 | 20 | 14 | 280 | 12/22/2022 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| 9 | 06-10-2022 | 2022-06-10 00:00:00 | 20 | 1 | 20 | 06/10/2022 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| 10 | 9/16/2022 | 2022-09-16 00:00:00 | 20 | 5 | 100 | 9/16/2022 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |

## Comprobaciones

- `transaction_type_Unknown` suma 107, que coincide con los 107 nulos originales.
- `date` no tiene valores sin parsear.
- No quedan nulos en el dataset procesado.
- El CSV procesado guarda la fecha en formato ISO (`YYYY-MM-DD`). Al leerlo de nuevo, usar `parse_dates=['date']` para recuperar dtype datetime.
