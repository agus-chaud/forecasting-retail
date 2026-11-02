import warnings

warnings.filterwarnings("ignore")

# Cargar las funciones auxiliares
from funciones import *

# Cargar los datos
df = pd.read_csv(
    "./DatosParaProduccion.csv", sep=";", parse_dates=["date"], index_col="date"
)

# Seleccionar solo las que se han usado
variables_finales = [
    "store_id",
    "item_id",
    "event_name_1",
    "month",
    "sell_price",
    "wday",
    "weekday",
    "ventas",
]

df = df[variables_finales]

# Determinar el último día real de ventas (el 9º desde el final, antes de los 8 días a predecir)
ultimo_dia_real = df.index.sort_values().unique()[-9]

# Lanzar la predicción
forecast = forecast_recursivo(df).sort_values(by=["store_id", "item_id"])

# Filtrar solo las predicciones posteriores al último día real
forecast_filtrado = forecast.reset_index()
forecast_filtrado = forecast_filtrado[forecast_filtrado["date"] > ultimo_dia_real]

# Filtrar columnas para la salida final
cols_salida = ["date", "store_id", "item_id", "ventas"]
if all(col in forecast_filtrado.columns for col in cols_salida):
    forecast_filtrado = forecast_filtrado[cols_salida]

# Ordenar por date, store_id, item_id
forecast_filtrado = forecast_filtrado.sort_values(by=["date", "store_id", "item_id"])
# Guardar el resultado filtrado
forecast_filtrado.to_csv("./predicciones.csv", index=False)
