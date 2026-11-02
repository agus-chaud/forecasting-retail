import warnings

warnings.filterwarnings("ignore")

# Cargar las funciones auxiliares
from funciones import *

# Cargar los datos
df = pd.read_pickle("./train.pkl")

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

paso1_df = calidad_datos(df)
paso2_df = crear_variables(paso1_df)

lanzar_entrenamiento(paso2_df)
