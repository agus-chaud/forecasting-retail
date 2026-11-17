# Forecasting de ventas retail 

Predicción de ventas diarias de 10 productos en 2 tiendas (`CA_3`, `CA_4`), a partir de la base de datos `hipermercado.db`. Ventana: 2013-01-01 a 2015-12-31 (1.095 días, 21.900 filas).

Registro de decisiones: [`decisions.md`](decisions.md) (resumen) y [`decisions_detalle.md`](decisions_detalle.md) (razonamiento completo). Fundamentos teóricos: [`01_Documentos/fundamentos_series_tiempo.md`](01_Documentos/fundamentos_series_tiempo.md).

## Hallazgos clave

- **8 de las 20 series no tienen ninguna alerta de calidad** (menos de 2,5 % de ceros, sin semanas hundidas) y **6 tienen 3 o 4 alertas**: rachas de ceros de hasta **361 días** con el precio cargado, que no son demanda normal.
- **sábado y domingo venden +17 % y +23 % sobre el promedio**. El ciclo anual es débil (julio alto, diciembre bajo) y no hay tendencia (medias anuales de la serie estudiada: 72,8, 75,3 y 73,2).
- **Los 25 de diciembre venden 0 en las 20 series**: estan cerrada las tiendas.
- **La vara a superar es MAE = 13,7 unidades/día (18,6 % de la media)** a 28 días, la de la mejor línea base (media de las últimas 4 semanas) en la serie `CA_3` / `FOODS_3_586`. Repetir la semana pasada comete 18,2.

## Resumen ejecutivo

 Se armó el tablón analítico desde la base SQLite, se limpió, se separó por fecha y se auditó la calidad serie por serie. Ahora se esta trabajando con ARIMA/SARIMA sobre una serie limpia, antes de pasar a las 20.

## Problema

Con series diarias de ventas hay tres cosas que pueden sesgar el resultado :

- **Fuga de información:** un split al azar mete días futuros en el entrenamiento y la validación sale mejor que la realidad.
- **Ceros que no son demanda:** productos que todavía no existían, tiendas cerradas y rachas largas sin ventas se leen como "demanda cero".
- **Evaluar sobre muy pocos datos:** 28 días de validación son una sola prueba; elegir el modelo mirando ese mes lo sobreajusta.

## Objetivo

Predecir las ventas diarias a 28 días por producto y tienda.

## Enfoque técnico

1. **Importación** (`01_Importacion_Datos*.ipynb`): conexión a `hipermercado.db` (SQLite) con SQLAlchemy, tablas `calendar`, `sales` y `sell_prices`; hecho en pandas y repetido en SQL.
2. **Tablón analítico:** `melt` de `sales` a formato largo y `left join` con calendario y precios: una fila por producto, tienda y día.
3. **Limpieza y split temporal** (`02_Limpieza_EDA.ipynb`): se eliminan las filas de un producto que aún no se vendía y se separa en `train`, `valid` y `reserva`.
4. **Calidad profunda y EDA** (`03_Calidad_Datos_EDA.ipynb`): ceros, extremos, precio, patrones y ficha de alertas por cada una de las 20 series.
5. **Modelado clásico** (`04_SARIMA.ipynb`): descomposición, estacionariedad, líneas base y backtesting sobre `CA_3` / `FOODS_3_586`.
6. **Producción** (`Producción/`): reentrenamiento y predicción con modelos por producto (ver [`explicacion.md`](Producción/instrucciones/explicacion.md)).
7. **Documentación:** cada decisión no obvia queda en `decisions.md`.

## Decisiones técnicas importantes

El detalle completo (alternativas descartadas, código afectado) está en [`decisions_detalle.md`](decisions_detalle.md). Acá las que más condicionan el resultado.

### Split temporal en tres partes (DEC-002)

 Se separó por fecha: `train` hasta 2015-11-10 (20.809 filas), `valid` 28 días (560) y `reserva` 23 días (460). 28 días son 4 semanas completas: cada día de la semana aparece 4 veces.

### Eliminar 71 filas sin precio (DEC-001)

Las 71 filas de `FOODS_3_288` sin `sell_price` (0,32 % del tablón) tienen 0 ventas: el producto aún no existía. Imputar el precio habría enseñado ceros falsos.

### Una sola serie para aprender SARIMA (DEC-006)

ARIMA/SARIMA son univariados y suponen una serie continua alrededor de un nivel. Se eligió `CA_3` / `FOODS_3_586`: 0,19 % de ceros (solo los dos 25 de diciembre) y el menor CV (0,24). Las series con 30-45 % de ceros son demanda intermitente y necesitan otros métodos.

### Estacionalidad anual con Fourier, no con `s = 365` (DEC-009)

Con 2,86 años de datos, MSTL sobreajusta el ciclo anual: salta 9,8 unidades por día y copia los 25 de diciembre. Con 2 pares de Fourier sale una curva suave de 18,5 unidades de rango que explica el 42 % de la variación lenta. Un SARIMA con `s = 365` es inviable.

En simple: la serie tiene un ritmo semanal (7 días) y uno anual (365 días). SARIMA aprende un ritmo mirando "qué pasó hace `s` días"; con `s = 365` haría falta mucha más historia (cada día del calendario aparece solo 2 o 3 veces) y el modelo sería muy lento. Por eso SARIMA se queda con el ciclo semanal. Para el anual se usan términos de Fourier: unas pocas ondas seno/coseno que dibujan una curva suave con 4 números en vez de 365, y que entran a `SARIMAX` como variables externas.

### Sin diferenciar: `d = 0`, `D = 0` (DEC-010, DEC-013)

Las cuatro combinaciones pasan ADF y KPSS, así que los tests no deciden. `D = 1` deja −0,45 de autocorrelación en el retardo 7 (sobrediferenciación) y sube el desvío de 17,7 a 19,3. La autocorrelación plana en múltiplos de 7 es la de un ciclo fijo, que se modela con términos estacionales.

### Evaluación fijada antes de modelar (DEC-011)

Horizonte de 28 días, MAE como métrica, dos líneas base y backtesting con 6 cortes dentro de `train`. Los órdenes del modelo se eligen con el backtesting y `valid` se usa una sola vez, al final.

## Resultados principales

| Área analizada | Hallazgo | Interpretación |
|---|---|---|
| Calidad por serie | 8 series sin alertas, 6 con 3-4 | Las 8 limpias sirven de primer caso; las 6 dependen de cómo se traten las rachas de ceros |
| Ceros | Rachas de hasta 361 días con precio cargado | No es demanda normal; decisión pendiente |
| `valid` vs `train` | Mann-Whitney p = 0,88; 5,9 % de ceros contra 14,0 % | Se parece a `train`; la diferencia de media es compatible con la época del año |
| Estacionalidad | Fin de semana +17 % / +23 % | El ciclo semanal es la señal principal |
| Estacionariedad | ADF p = 0,006, KPSS p ≈ 0,07 | Sin tendencia: se parte de `d = 0` |
| Línea base | MAE 13,7 (media de 4 semanas) contra 18,2 (naive estacional) | Un SARIMA debe bajar de 13,7 para justificarse |
| Autocorrelación | PACF se corta tras el retardo 1 (0,43); ACF en múltiplos de 7 entre 0,29 y 0,40 | AR(1) más ciclo semanal fijo: se parte de SARIMA(1, 0, 0)(1, 0, 0)₇ y se comparan 6 candidatos (DEC-014) |

## Estructura del proyecto

```
.
├── 01_Documentos/           # Fundamentos de series de tiempo (guía de estudio)
├── 02_datos/
│   ├── 01_Originales/       # hipermercado.db (SQLite, no versionada)
│   ├── 02_Validacion/       # validacion.parquet y reserva.parquet
│   ├── 03_Entrenamiento/    # tablon_analitico, tablon_limpio y train (parquet)
│   └── 04_Caches/           # Intermedios regenerables
├── 03_notebooks/            # 01 importación (pandas y SQL), 02 limpieza/EDA, 03 calidad, 04 SARIMA
├── 04_scripts/              # Vacía: acá van las funciones de los notebooks (DEC-005)
├── 05_modelos/              # Vacía: modelos entrenados
├── 06_resultados/           # Vacía
├── 07_despliegue/           # Vacía
├── 99_otros/                # Diagrama de relaciones entre tablas
├── Producción/              # reentrenamiento.py, ejecucion.py, funciones.py e instrucciones
├── decisions.md             # Índice y pendientes de decisiones
├── decisions_detalle.md     # Razonamiento completo de cada decisión
├── Forecasting Retail.pdf   # Enunciado del caso
└── requirements.txt         # Dependencias de Python
```

## Cómo reproducir

**Requisitos:** Python 3.12 y la base `hipermercado.db` (material del caso, `Material descargable Caso 2.zip`). Los datos (`*.db`, `*.parquet`, `*.csv`) no están versionados.

**Entorno en Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m ipykernel install --user --name agentic_ds_forecasting_retail --display-name agentic_ds_forecasting_retail
```

**Entorno en macOS / Linux:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name agentic_ds_forecasting_retail --display-name agentic_ds_forecasting_retail
```

**Ejecución:**

1. Copiar `hipermercado.db` a `02_datos/01_Originales/`.
2. Abrir `03_notebooks/` con el kernel `agentic_ds_forecasting_retail` y correr en orden: `01_Importacion_Datos.ipynb`, `02_Limpieza_EDA.ipynb`, `03_Calidad_Datos_EDA.ipynb`, `04_SARIMA.ipynb`. (`01_Importacion_Datos_SQL.ipynb` es la versión en SQL del 01.)
3. Para producción: ver [`Producción/instrucciones/explicacion.md`](Producción/instrucciones/explicacion.md). Hacen falta `train.pkl` y `DatosParaProduccion.csv` en la carpeta; luego `python reentrenamiento.py` y `python ejecucion.py`.

**Ojo con los nombres:** la carpeta es `Producción` (con tilde). En Linux y macOS el casing importa.

## Limitaciones y próximos pasos

- **Solo una serie está modelada a fondo.** Los resultados de SARIMA valen para `CA_3` / `FOODS_3_586`, la más fácil; las series intermitentes (30-45 % de ceros) necesitan otros métodos, como Croston.
- **Falta el paso 5 del notebook 04:** ajustar SARIMA/SARIMAX, elegir órdenes y `K` de Fourier con el backtesting y medir `valid` una sola vez. Todavía no hay un modelo que supere la línea base.
- **Decisiones pendientes** (en `decisions.md`): rachas largas de ceros, el precio 1,00 de `FOODS_3_090` (¿relleno o descuento real?, no verificado), el 25 de diciembre para el resto de las series, la promoción de agosto-septiembre 2013 y un posible efecto del día del mes (SNAP).
- **Solo 2,86 años de datos:** no alcanza para estimar bien el ciclo anual día por día.
- **No cubre** precios futuros, promociones planificadas ni nuevos productos.
