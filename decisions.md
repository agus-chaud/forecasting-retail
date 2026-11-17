# Registro de Decisiones Técnicas

Por qué se tomó cada decisión, el código ya explica qué se hizo.
Formato corto: decisión → por qué (con la cifra clave) → regla a futuro.

**El razonamiento completo, con todas las cifras, alternativas descartadas y
código afectado, está en [`decisions_detalle.md`](decisions_detalle.md)** —
mismos IDs, mismo orden. Las decisiones superadas no se borran de ninguno de
los dos archivos.

---

## Índice

| ID | Área | Decisión |
|----|------|----------|
| DEC-001 | calidad-datos | Eliminar las 71 filas de `FOODS_3_288` sin precio (0,32 % del tablón) |
| DEC-002 | evaluacion | Split temporal: train hasta 2015-11-10, valid 28 días, reserva 23 días |
| DEC-003 | calidad-datos | `year`, `month` y `wday` como `category` ordenada (no `object`) |
| DEC-004 | transversal | Conservar `state_id`, `dept_id` y `cat_id` aunque hoy sean constantes |
| DEC-005 | transversal | Análisis en funciones reutilizables con parámetros, para pasar a `04_scripts/` |
| DEC-006 | modelado | Aprender ARIMA/SARIMA con una sola serie: `CA_3` / `FOODS_3_586` (0,19 % de ceros, CV 0,24) |
| DEC-007 | transversal | Entorno en `.venv/` del repo con `requirements.txt`, registrado como kernel `agentic_ds_forecasting_retail` |
| DEC-008 | modelado | Descomposición aditiva (la amplitud semanal no crece con el nivel: correlación 0,11) |
| DEC-009 | modelado | Estacionalidad anual con términos de Fourier como variables externas de SARIMAX, no con MSTL ni `s = 365` |
| DEC-010 | modelado | Estacionariedad con ADF y KPSS juntos (KPSS alrededor de un nivel); sin diferencia simple como punto de partida (`d = 0`) |
| DEC-011 | evaluacion | MAE a 28 días, líneas base y backtesting de 6 cortes dentro de `train`; `valid` una sola vez al final |
| DEC-012 | modelado | En la serie de aprendizaje, los 25 de diciembre se imputan con el mismo día de la semana anterior (`y[t-7]`) |
| DEC-013 | modelado | Sin diferenciar: `d = 0` y `D = 0`; el ciclo semanal (fijo) se modela con términos estacionales `P`, `Q` (`s = 7`); `D = 1` solo como alternativa en el backtesting |

---

## Pendientes reales

| Decisión | Área |
|---|---|
| Tratamiento de las rachas largas de ceros (hasta 361 días) y las semanas con ventas casi nulas: dejarlas, marcarlas con una variable o excluirlas del entrenamiento | calidad-datos |
| Confirmar con quien conozca el origen de los datos si el precio 1,00 de `FOODS_3_090` (`CA_3`) es un relleno por falta de disponibilidad o un descuento real | calidad-datos |
| Tratamiento del 25 de diciembre (tiendas cerradas, ventas 0 en las 20 series): variable propia o filtrado. Ya resuelto para la serie de aprendizaje de SARIMA (DEC-012); falta para el resto de las series | feature-engineering |
| Cómo representar la promoción de agosto-septiembre 2013 de `FOODS_3_090` (por ejemplo, precio relativo a la mediana de la serie) | feature-engineering |
| Probar un efecto de día del mes como variable externa del SARIMAX (por ejemplo, primera o segunda mitad del mes, o Fourier del día del mes). Mirada rápida en `CA_3` / `FOODS_3_586`: los días 1 a 13 venden entre 1 % y 10 % más que la media y los días 22 a 31 entre 0 % y 14 % menos (posible efecto del cobro o de la ayuda alimentaria SNAP, columna `snap_CA` que el tablón no tiene). Sin test todavía; se conserva solo si baja el error del backtesting | modelado |
| Cuántos pares de Fourier (`K`) usar para el ciclo anual en SARIMAX: elegir en el paso 5 comparando el error en el backtesting dentro de `train` (DEC-011), no en `valid` | modelado |

---

## Decisiones

**DEC-001 — Eliminar las 71 filas sin precio.** Se eliminan las 71 filas de `FOODS_3_288` con `sell_price` nulo (0,32 % del tablón). **Por qué:** tienen 0 ventas y son días en que el producto no existía; imputar el precio dejaría ceros falsos. **Regla:** Distinguir siempre "no existía" (se elimina) de "no se vendió" (se conserva el cero), y confirmar con un `assert` que las filas no tienen ventas.

**DEC-002 — Split temporal.** `train` hasta 2015-11-10 (20.809 filas), `valid` 28 días (560) y `reserva` 23 días (460). **Por qué:** un split al azar mete días futuros en `train`; 28 días son 4 semanas completas y `reserva` coincide con `DatosParaProduccion.csv`. **Regla:** Nunca partir series de tiempo al azar; `valid` en múltiplos de 7 días y los umbrales aprendidos se calculan solo con `train`.

**DEC-003 — Tipos categóricos.** `year`, `month` (`"01".."12"`) y `wday` (`"1".."7"`, 1 = sábado) pasan a `category` ordenada, igual en `train`, `valid` y `reserva`. **Por qué:** son etiquetas, no cantidades, y `category` pesa 55 veces menos que `object` (21.048 contra 1.168.403 bytes en `weekday`). **Regla:** Usar `category` ordenada con lista explícita de categorías y dejar que la función falle ante valores no declarados.

**DEC-004 — Columnas constantes.** Se conservan `state_id` (solo `CA`), `dept_id` (solo `FOODS_3`) y `cat_id` (solo `FOODS`). **Por qué:** más adelante se podrán crear datos ficticios con más estados, departamentos y categorías. **Regla:** Nunca asumir un solo estado, departamento o categoría; si una constante estorba en un modelo, excluirla ahí y no en el tablón.

**DEC-005 — Funciones reutilizables.** El análisis se escribe en funciones que reciben un DataFrame y rutas con `Path`, sin valores fijos. **Por qué:** las ventas son datos incrementales y el proyecto practica reentrenamiento; con funciones, un dato nuevo se procesa llamando de nuevo, no editando celdas. **Regla:** Toda celda repetible con datos nuevos se convierte en función con parámetros explícitos.

**DEC-006 — Una sola serie para aprender SARIMA.** Se usa `CA_3` / `FOODS_3_586`: empata en primer lugar con menos ceros (0,19 %, solo los dos 25 de diciembre), tiene el menor CV (0,24) y 73,8 unidades por día de media. **Por qué:** ARIMA/SARIMA son univariados (un modelo por serie) y suponen una serie que se mueve de forma continua alrededor de un nivel; las series con 30-45 % de ceros son demanda intermitente y necesitan otros métodos. **Regla:** Para aprender un método, empezar por la serie que mejor cumple sus supuestos; recién después pasar a las difíciles.

**DEC-007 — Entorno reproducible en el repo.** El entorno vive en `.venv/` (ya ignorado por git), las librerías están en `requirements.txt` y se registra como kernel `agentic_ds_forecasting_retail`. **Por qué:** el kernel original no estaba en este usuario de Windows y no había lista de dependencias para rearmarlo. **Regla:** Toda librería nueva se agrega a `requirements.txt` antes de usarla en un notebook.

**DEC-008 — Descomposición aditiva.** La serie se descompone como `tendencia + estacionalidad + residuo`. **Por qué:** la amplitud del ciclo semanal no crece con el nivel (correlación 0,11 entre los 35 meses); enero de 2013 (nivel 62,1) y agosto de 2014 (nivel 90,1) tienen la misma amplitud, unas 30 unidades. **Regla:** Antes de elegir entre aditiva y multiplicativa, medir si la amplitud estacional crece con el nivel; no elegir a ojo.

**DEC-009 — Ciclo anual con Fourier.** El ciclo anual entra al modelo como pares seno/coseno (términos de Fourier) usados como variables externas de `SARIMAX`; el ciclo semanal lo modela SARIMA con `s = 7`. **Por qué:** con 2,86 años de datos, MSTL sobreajusta el ciclo anual (salta 9,8 unidades por día de media y copia los 25 de diciembre); con 2 pares de Fourier sale una curva suave de 18,5 unidades de rango que explica el 42 % de la variación lenta. Un SARIMA con `s = 365` es inviable. **Regla:** No estimar una estacionalidad día por día sin al menos 3 ciclos completos; con pocos ciclos, usar una forma suave con pocos parámetros.

**DEC-010 — ADF y KPSS juntos, `d = 0` de partida.** La estacionariedad se diagnostica con los dos tests a la vez; KPSS con `regression="c"` (alrededor de un nivel). En la serie original ADF da p = 0,006 (rechaza la raíz unitaria) y KPSS p ≈ 0,07 (no rechaza la estacionariedad al 5 %), así que se parte de `d = 0`. **Por qué:** tienen hipótesis nulas opuestas; un solo test que no rechaza no prueba nada, dos que coinciden sí. No hay tendencia (medias anuales 72,8, 75,3 y 73,2), por eso `"c"` y no `"ct"`. **Regla:** Nunca decidir la diferenciación con un único test, y recordar que ninguno de los dos mide la estacionalidad: `D` se decide aparte (paso 3, parte B).

**DEC-011 — Cómo se mide, fijado antes de modelar.** Horizonte de 28 días, métrica MAE (también como % de la media; RMSE como métrica secundaria, solo diagnóstico), dos líneas base (naive estacional `y[t-7]` y media de las últimas 4 semanas por día) y backtesting *rolling origin* con 6 cortes de 28 días dentro de `train`. Los órdenes de SARIMA y `K` de Fourier se eligen con el backtesting; `valid` se usa una sola vez, al final del paso 5. **Por qué:** `valid` son 28 días, una sola prueba; elegir órdenes mirando su error ajusta el modelo a ese mes. La mejor línea base (media de 4 semanas) comete 13,7 unidades/día (18,6 % de la media), contra 18,2 de la naive estacional: esa es la vara a superar. **Regla:** Fijar métrica, horizonte y línea base antes de ajustar cualquier modelo, y no tomar decisiones con el conjunto que se usa para la medición final.

**DEC-012 — 25 de diciembre imputado en la serie de aprendizaje.** En `CA_3` / `FOODS_3_586` los dos 25 de diciembre (ventas 0, tienda cerrada) se reemplazan por el valor del mismo día de la semana anterior: 67 en 2013 y 73 en 2014 (`y_modelo`). **Por qué:** los pasos 3 y 4 usan la serie sola, sin variables externas, así que una variable indicadora recién podría entrar en el paso 5; mientras tanto esos ceros contaminan la descomposición (MSTL los copió como −59). Ni `valid` ni los cortes del backtesting incluyen un 25 de diciembre, así que la evaluación no cambia, y los tests ADF/KPSS dan casi lo mismo (ADF −3,57 en las dos versiones). **Regla:** Un cero por tienda cerrada no es demanda: tratarlo antes de modelar y pronosticar los cierres futuros con una regla (cerrado = 0), no con el modelo.

**DEC-013 — Sin diferenciar (`d = 0`, `D = 0`).** El SARIMA base es (p, 0, q)(P, 0, Q)₇ sobre `y_modelo`; la variante con `D = 1` se compara en el backtesting del paso 5. **Por qué:** las cuatro combinaciones pasan ADF y KPSS, así que los tests no deciden. `d = 1` deja −0,29 en el retardo 1 y sube el desvío de 17,7 a 18,8; `D = 1` deja −0,45 en el retardo 7 (huella de sobrediferenciación) y sube el desvío a 19,3. La fuerza estacional semanal es 0,46, por debajo del umbral de 0,64 para `D = 1`. La autocorrelación plana en los múltiplos de 7 (0,40 a 0,33) es la de un ciclo fijo, que se modela con términos estacionales y no se resta. **Regla:** Usar la menor cantidad de diferencias que deja la serie estacionaria; cuando los tests no discriminan, decidir con la autocorrelación en el retardo diferenciado (−0,5 = sobra) y con el desvío.

---
