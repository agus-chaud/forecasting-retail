# Registro de Decisiones Técnicas — detalle completo

**Este es el archivo de detalle.** `decisions.md` tiene el índice, el resumen
corto de cada decisión y la lista de pendientes reales — es el que conviene
leer primero. Acá está el razonamiento completo de cada una: alternativa
descartada, cifras exactas, lección aprendida y código afectado. Mismos IDs que
`decisions.md`, en el mismo orden. Las decisiones superadas NO se borran.

---

## DEC-001: Eliminar las 71 filas de FOODS_3_288 sin precio

**Área:** calidad-datos | **Fase:** 02 Limpieza | **Fecha:** 2026-11-05 | **Estado:** Vigente

**Decisión:** Se eliminan las 71 filas (0,32 % de las 21.900 del tablón) donde `sell_price` es nulo. Todas son del producto `FOODS_3_288`, de las primeras semanas de 2013 (hasta el 2013-02-01 en `CA_3` y el 2013-02-08 en `CA_4`).

**Alternativa descartada:** Conservar las filas e imputar el precio (rellenar con el primer precio conocido) dejando `ventas = 0`.

**Por qué la descartamos:** Las 71 filas tienen 0 ventas (un `assert` en el notebook 02 lo comprueba) y representan días en que el producto todavía no se vendía, no días de demanda cero. Si se imputa el precio, el modelo aprende ceros falsos al inicio de esas dos series. Eliminarlas no pierde ninguna venta real. Es una regla fija que no calcula nada con los datos, así que se puede aplicar antes del split sin filtrar información del futuro.

**Conclusión:** Siempre distinguir "el producto no existía" (se elimina) de "no se vendió" (se conserva el cero). Si aparecen nulos de precio en datos nuevos, mirar primero cuántas ventas tienen esas filas y confirmar con un `assert` antes de eliminarlas.

**Código afectado:** `03_notebooks/02_Limpieza_EDA.ipynb`, sección 1.

---

## DEC-002: Split temporal con tres cortes (train, valid, reserva)

**Área:** evaluacion | **Fase:** 02 Limpieza | **Fecha:** 2026-11-05 | **Estado:** Vigente

**Decisión:** El split es por fecha: `train` hasta el 2015-11-10 (20.809 filas), `valid` del 2015-11-11 al 2015-12-08 (28 días, 560 filas) y `reserva` del 2015-12-09 al 2015-12-31 (23 días, 460 filas). `reserva` no se toca hasta el final.

**Alternativa descartada:** Un split aleatorio de filas (por ejemplo 70/15/15), o una `valid` más corta (14 días).

**Por qué la descartamos:**

| Criterio | Elegido (temporal, 28 días) | Descartado |
|---|---|---|
| Fuga de información | Ninguna: todo `train` es anterior a `valid` | Aleatorio: días futuros dentro de `train`, la validación sale mejor que la realidad |
| Días de la semana en `valid` | 4 de cada uno (4 semanas completas) | 14 días: 2 de cada uno, más ruido |
| Relación con producción | `reserva` coincide con `Producción/DatosParaProduccion.csv`, que predice 8 días | Sin vínculo |

**Conclusión:** Nunca partir series de tiempo al azar. Siempre separar por fecha, con `valid` en múltiplos de 7 días, y tocar `reserva` una sola vez al final. Cualquier umbral aprendido de los datos se calcula solo con `train`.

**Código afectado:** `03_notebooks/02_Limpieza_EDA.ipynb`, sección 2.

---

## DEC-003: `year`, `month` y `wday` como categóricas ordenadas (`category`)

**Área:** calidad-datos | **Fase:** 03 Calidad y EDA | **Fecha:** 2026-11-05 | **Estado:** Vigente

**Decisión:** `year`, `month` y `wday` pasan de `int64` a `category` ordenada con etiquetas de texto: `month` = `"01".."12"`, `wday` = `"1".."7"` (convención M5: 1 = sábado) y `year` aprendido de `train` (`"2013".."2015"`). La misma conversión se aplica a `train`, `valid` y `reserva`. Sin one-hot por ahora.

**Alternativa descartada:** Dejarlas como `int64`; convertirlas a `object` (lo que se pidió en un principio) o a `str`; hacer one-hot ya.

**Por qué la descartamos:**

| Opción | Problema |
|---|---|
| `int64` | Permite promediar o sumar meses, que no tiene sentido; mes 12 no es "el doble" de 6 |
| `object` | Contenedor genérico: la columna `weekday` (20.809 filas) ocupa 1.168.403 bytes, 55 veces más que como `category` (21.048). En pandas 3 el texto es `str` |
| `str` | Tipo de texto libre (315.234 bytes). No guarda el conjunto cerrado de valores ni el orden |
| one-hot ahora | Es feature engineering: va después, y solo sobre `train` |

`category` además fija el orden (`"01"` antes de `"02"`) y la función de conversión **falla** si aparece un valor no declarado (por ejemplo un año 2016) en vez de dejar un nulo silencioso.

**Conclusión:** Usar `category` ordenada para variables que son etiquetas con pocos valores y orden fijo, no `object`. Siempre construir las categorías con una lista explícita, aprender solo de `train` el vocabulario que no sea calendario fijo, y dejar que la función falle ante valores nuevos.

**Código afectado:** `03_notebooks/03_Calidad_Datos_EDA.ipynb`, función `a_categoricas`.

---

## DEC-004: Conservar `state_id`, `dept_id` y `cat_id` aunque sean constantes

**Área:** transversal | **Fase:** 03 Calidad y EDA | **Fecha:** 2026-11-05 | **Estado:** Vigente

**Decisión:** No se eliminan `state_id` (solo `CA`), `dept_id` (solo `FOODS_3`) ni `cat_id` (solo `FOODS`), aunque hoy tengan un único valor.

**Alternativa descartada:** Eliminarlas por tener varianza cero (no aportan información al modelo hoy).

**Por qué la descartamos:** Más adelante se podrán crear datos ficticios para ampliar el dataset con más estados, departamentos y categorías. Si se eliminan ahora, habría que volver a reconstruir el esquema y cada función que agrupe por jerarquía. Conservarlas cuesta tres columnas de texto repetidas.

**Conclusión:** Nunca asumir que hay un solo estado, departamento o categoría. Escribir las agrupaciones sin valores fijos y, cuando una columna constante estorbe en un modelo, excluirla ahí, no en el tablón.

**Código afectado:** `03_notebooks/03_Calidad_Datos_EDA.ipynb` (la serie se define con `CLAVE_SERIE`, sin asumir un solo estado).

---

## DEC-005: Funciones reutilizables en el notebook, pensadas para `04_scripts/`

**Área:** transversal | **Fase:** 03 Calidad y EDA | **Fecha:** 2026-11-05 | **Estado:** Vigente

**Decisión:** El análisis se escribe como funciones que reciben un DataFrame (y rutas con `Path`), sin valores fijos adentro: nombres de columnas y clave de serie van como parámetros o constantes arriba del notebook. Más adelante se pasan a `04_scripts/`.

**Alternativa descartada:** Código suelto en celdas, con rutas y nombres de columnas escritos en cada una.

**Por qué la descartamos:** Las ventas son datos incrementales que se van actualizando, y el proyecto también sirve para practicar data engineering y reentrenamiento. Con código suelto, cada dato nuevo obliga a copiar y editar celdas; con funciones, se llaman de nuevo con el DataFrame actualizado.

**Conclusión:** Siempre que una celda se pueda repetir con datos nuevos, convertirla en función con parámetros explícitos. Evitar rutas absolutas y valores fijos adentro de las funciones.

**Código afectado:** `03_notebooks/03_Calidad_Datos_EDA.ipynb` (funciones `cobertura_por_serie`, `intermitencia_por_serie`, `limites_extremos`, `resumen_precio`, `indice_semanal`, `autocorrelacion`, `razon_eventos`, entre otras).

---

## DEC-006: Aprender ARIMA/SARIMA con una sola serie (`CA_3` / `FOODS_3_586`)

**Área:** modelado | **Fase:** 04 SARIMA | **Fecha:** 2026-11-15 | **Estado:** Vigente

**Decisión:** El notebook 04 trabaja con una única serie, `CA_3` / `FOODS_3_586`, extraída de `train` como `pd.Series` diaria (`freq="D"`) de 1.044 días, del 2013-01-01 al 2015-11-10, sin huecos ni fechas repetidas.

**Alternativa descartada:** Ajustar un SARIMA a cada una de las 20 series desde el principio, o empezar por una serie con muchos ceros.

**Por qué la descartamos:** ARIMA y SARIMA son modelos **univariados**: cada uno aprende de la historia de una sola serie, así que 20 series implican 20 modelos con 20 diagnósticos distintos. Para aprender el método eso multiplica el trabajo sin enseñar nada nuevo. Además, estos modelos suponen que la serie se mueve de forma más o menos continua alrededor de un nivel. Una serie con muchos días en cero (demanda *intermitente*) rompe ese supuesto y se modela con otros métodos (por ejemplo Croston).

| Serie | % de días en cero | CV (desvío / media) | Media diaria |
|---|---|---|---|
| `CA_3` / `FOODS_3_586` (elegida) | 0,19 | 0,24 | 73,8 |
| `CA_3` / `FOODS_3_555` | 0,19 | 0,31 | 32,6 |
| `CA_3` / `FOODS_3_090` | 9,6 | 0,76 | 127,2 |
| `CA_4` / `FOODS_3_120` (la más difícil) | 45,3 | 1,30 | 10,9 |

El primer vistazo a la serie elegida (notebook 04, sección 1) mostró:
- un **patrón semanal** fuerte: domingo 89,5 y sábado 84,7 de media, contra 63,2 del miércoles;
- un **patrón anual** suave: agosto es el mes más fuerte (87,4) y enero el más flojo (62,3);
- **ninguna tendencia clara**: 72,8 de media en 2013, 75,3 en 2014 y 73,2 en 2015;
- solo **2 ceros**, los dos un 25 de diciembre (tienda cerrada, no demanda cero).

**Conclusión:** Para aprender un método, empezar por la serie que mejor cumple sus supuestos: pocos ceros, volumen alto y poca variación relativa. Recién cuando el método se entiende, pasar a las series difíciles y ver dónde falla. Antes de modelar cualquier serie, convertirla a `pd.Series` con frecuencia fija y comprobar que no tenga huecos, porque el modelo asume que el dato anterior es el día anterior.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, sección 1 (funciones `resumen_series`, `extraer_serie`, `graficar_serie`, `graficar_zoom`).

---

## DEC-007: Entorno reproducible en `.venv/` del repo, con `requirements.txt`

**Área:** transversal | **Fase:** 04 SARIMA | **Fecha:** 2026-11-15 | **Estado:** Vigente

**Decisión:** El entorno de Python (3.12) se crea en `.venv/` dentro del repo, que ya está en `.gitignore`. Las librerías se listan en `requirements.txt` y el entorno se registra como el kernel de Jupyter `agentic_ds_forecasting_retail`, el mismo nombre que ya usaban los notebooks. Para rearmarlo en Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m ipykernel install --user --name agentic_ds_forecasting_retail --display-name agentic_ds_forecasting_retail
```

**Alternativa descartada:** Crear el entorno en una carpeta del usuario, fuera del proyecto.

**Por qué la descartamos:** El kernel original no existía en este usuario de Windows (el repo fue creado por otro usuario) y no había ninguna lista de dependencias para rearmarlo. Hubo que reconstruirla leyendo los `import` de los notebooks. Con el entorno junto al proyecto y un `requirements.txt` versionado, cualquiera puede rearmarlo con tres comandos. `requirements.txt` pide `pandas>=3.0` porque el notebook 03 se escribió con pandas 3.

**Conclusión:** Toda librería nueva se agrega a `requirements.txt` antes de usarla en un notebook. Si un notebook pide un kernel que no aparece, rearmarlo con los comandos de arriba en vez de usar otro entorno.

**Código afectado:** `requirements.txt`, `.venv/` (no versionado).

---

## DEC-008: Descomposición aditiva

**Área:** modelado | **Fase:** 04 SARIMA | **Fecha:** 2026-11-15 | **Estado:** Vigente

**Decisión:** La serie `CA_3` / `FOODS_3_586` se descompone en forma aditiva: `y = tendencia + estacionalidad + residuo`. El efecto de cada día de la semana se expresa en unidades fijas (domingo +15,5, sábado +10,9, miércoles −10,5 según `seasonal_decompose`).

**Alternativa descartada:** Descomposición multiplicativa (`y = tendencia × estacionalidad × residuo`), o aplicar logaritmo para pasar de multiplicativa a aditiva.

**Por qué la descartamos:** La multiplicativa se usa cuando el ciclo estacional crece con el nivel; por ejemplo, si en verano el pico del domingo es mucho más alto que en invierno. Para verificarlo se calculó, para cada uno de los 35 meses de `train`, el nivel medio y la amplitud semanal (día más alto menos día más bajo):

| Mes | Nivel | Amplitud semanal |
|---|---|---|
| 2013-01 | 62,1 | 30,1 |
| 2014-08 | 90,1 | 30,2 |
| 2015-01 | 58,3 | 27,8 |
| 2015-08 | 86,9 | 40,4 |

La correlación entre nivel y amplitud es 0,11: prácticamente nula. El ciclo semanal mide lo mismo con nivel alto o bajo, así que la multiplicativa no aporta nada. Además, la multiplicativa y el logaritmo se rompen con ceros, y la serie tiene dos (los 25 de diciembre).

**Conclusión:** Antes de elegir entre aditiva y multiplicativa, medir si la amplitud estacional crece con el nivel (correlación nivel-amplitud por mes). Si la correlación es clara y positiva, probar la multiplicativa o el logaritmo; si no, quedarse con la aditiva, que es más simple.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, secciones 2.1 y 2.2 (función `amplitud_vs_nivel`).

---

## DEC-009: Estacionalidad anual con términos de Fourier, no con MSTL ni `s = 365`

**Área:** modelado | **Fase:** 04 SARIMA | **Fecha:** 2026-11-15 | **Estado:** Vigente

**Decisión:** El ciclo semanal lo modela SARIMA con `s = 7`. El ciclo anual entra como variables externas de `SARIMAX`: pares seno/coseno del día del año (términos de Fourier, función `terminos_fourier`). La cantidad de pares `K` se elige en el paso 5 con el error en `valid`; `K = 2` es el punto de partida. *(Actualizado por DEC-011: `K` se elige con el backtesting dentro de `train`, no con `valid`.)*

**Alternativa descartada:** (a) Estimar el ciclo anual día por día con `MSTL(periods=(7, 365))` y restarlo antes de modelar. (b) Un SARIMA con período estacional `s = 365`.

**Por qué la descartamos:**

| Opción | Problema |
|---|---|
| MSTL con 365 | Con 2,86 años de datos, cada día del calendario aparece 2 o 3 veces. La componente anual salta 9,8 unidades por día de media y sus valores extremos son días sueltos: 25 de diciembre de 2014 (−59,1), 25 de diciembre de 2013 (−58,3), 4 de julio de 2013 (+52,5). Memoriza el ruido en vez de aprender la forma (sobreajuste) |
| SARIMA con `s = 365` | Tendría que estimar relaciones entre días separados por un año con menos de 3 ciclos; además, con datos diarios es muy lento y suele no converger |
| **Fourier, K = 2 (elegida)** | Curva suave con 4 parámetros: 18,5 unidades de rango, explica el 42 % de la variación de la media móvil de 7 días. Los términos se calculan con la fecha, así que también existen para los días futuros que hay que predecir |

**Conclusión:** No estimar una estacionalidad día por día sin al menos 3 ciclos completos de datos. Con pocos ciclos, describirla con una forma suave de pocos parámetros (Fourier) y validar `K` contra datos que el modelo no vio. Desconfiar de cualquier componente estacional cuyos valores extremos coinciden con días puntuales: es señal de sobreajuste.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, secciones 2.3 y 2.4 (funciones `fuerza`, `terminos_fourier`).

---

## DEC-010: Estacionariedad con ADF y KPSS juntos; `d = 0` como punto de partida

**Área:** modelado | **Fase:** 04 SARIMA (paso 3, parte A) | **Fecha:** 2026-11-15 | **Estado:** Vigente

**Decisión:** La estacionariedad se diagnostica con dos tests a la vez, ADF (`autolag="AIC"`) y KPSS (`regression="c"`, `nlags="auto"`), mediante la función `test_estacionariedad`. Con los resultados sobre la serie original, el modelo parte sin diferencia simple (`d = 0`). La diferencia estacional (`D`) se decide en la parte B.

**Alternativa descartada:** (a) Usar solo ADF, que es lo más común en tutoriales. (b) KPSS con `regression="ct"` (estacionaria alrededor de una tendencia lineal). (c) Diferenciar de entrada (`d = 1`) "por las dudas".

**Por qué la descartamos:**

| Opción | Problema |
|---|---|
| Solo ADF | Un test de hipótesis solo puede rechazar su H0. Si ADF no rechazara, no sabríamos si la serie no es estacionaria o si faltan datos para verlo. KPSS tiene la hipótesis opuesta y cubre ese hueco |
| KPSS con `"ct"` | Supone una tendencia lineal que la serie no tiene (medias anuales 72,8, 75,3 y 73,2; 72,4 en la primera mitad y 75,2 en la segunda) |
| `d = 1` de entrada | Diferenciar una serie que no lo necesita agrega ruido y una autocorrelación negativa artificial en el retardo 1 (sobrediferenciación) |

Resultados sobre la serie original (1.044 días de `train`):

| Test | Estadístico | Valores críticos | p | Lectura al 5 % |
|---|---|---|---|---|
| ADF | −3,569 (21 retardos) | −3,44 (1 %), −2,86 (5 %), −2,57 (10 %) | 0,006 | Estacionaria |
| KPSS | 0,419 | 0,347 (10 %), 0,463 (5 %), 0,739 (1 %) | ≈ 0,07 | Estacionaria (rechazaría al 10 %) |

Los dos coinciden en que no hay tendencia ni deriva. El KPSS cerca del límite y la media trimestral que va de 60,3 a 83,5 muestran que la media no es del todo constante, pero esa variación es estacional (ola anual y ciclo semanal), y ninguno de los dos tests está diseñado para medirla. Los 21 retardos que eligió ADF (tres semanas) confirman el peso del ciclo semanal.

**Conclusión:** Nunca decidir la diferenciación con un único test; usar dos con hipótesis opuestas y mirar los gráficos. Recordar que los dos miden tendencia y deriva, no estacionalidad: la diferencia estacional se decide con la serie diferenciada y la autocorrelación en los múltiplos del período. `d = 0` es un punto de partida; se revisa en la parte B si la serie con diferencia estacional muestra otra cosa. *(Actualizado por DEC-013: la parte B confirmó `d = 0` y además eligió `D = 0`.)*

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, sección 3, parte A (funciones `graficar_media_desvio_movil`, `test_estacionariedad`).

---

## DEC-011: Métrica, horizonte, líneas base y backtesting fijados antes de modelar

**Área:** evaluacion | **Fase:** 04 SARIMA (secciones 0.1 y 1.6) | **Fecha:** 2026-11-16 | **Estado:** Vigente

**Decisión:** Todo modelo del notebook 04 se evalúa igual:
- **Horizonte:** 28 días, igual que `valid` (DEC-002).
- **Métrica:** MAE en unidades por día, también expresado como % de la media de la serie. **Métrica secundaria:** RMSE, solo como diagnóstico (el cociente RMSE/MAE indica si hay pocos errores muy grandes); no decide qué modelo gana.
- **Líneas base:** naive estacional (repetir la última semana, `y[t-7]`) y media de las últimas 4 apariciones de cada día de la semana.
- **Backtesting *rolling origin*:** 6 cortes de 28 días dentro de `train`; el último termina el 2015-11-10.

Los órdenes de SARIMA y la cantidad `K` de pares de Fourier se eligen con el MAE medio del backtesting. `valid` se usa una sola vez, al final del paso 5, con el modelo ya elegido. Funciones: `mae`, `rmse`, `cortes_backtest`, `naive_estacional`, `media_ultimas_semanas`, `backtest`.

**Alternativa descartada:** (a) Elegir órdenes y `K` con el error en `valid` (lo que decía DEC-009 y el plan original del notebook). (b) Comparar SARIMA solo contra el modelo de boosting del curso, sin línea base simple. (c) Usar RMSE como métrica principal.

**Por qué la descartamos:**

| Opción | Problema |
|---|---|
| Elegir con `valid` | Son 28 días: una sola prueba. Probar muchas combinaciones de órdenes y quedarse con la que mejor da en ese mes ajusta el modelo a ese mes, y el error de `valid` deja de ser una medida honesta |
| Sin línea base simple | No hay forma de saber si SARIMA aporta algo. Si no le gana a "repetir la semana pasada", su complejidad no se justifica |
| RMSE como principal | Penaliza mucho los días extremos y no se lee tan directo; MAE se lee como "unidades por día de error". Se reporta al lado como métrica secundaria (diagnóstico, no decide) |

Resultados de las líneas base en los 6 cortes (2015-05-27 a 2015-11-10):

| Método | MAE medio | Mínimo | Máximo | % de la media | RMSE medio | RMSE/MAE |
|---|---|---|---|---|---|---|
| Media de 4 semanas | 13,7 | 11,5 | 15,1 | 18,6 % | 17,5 | 1,28 |
| Naive estacional | 18,2 | 12,4 | 24,6 | 24,7 % | 23,0 | 1,26 |

La naive estacional es peor y más inestable porque copia el ruido de una sola semana; promediar 4 semanas lo suaviza. Gana en un solo corte (24-jun a 21-jul de 2015).

**Conclusión:** Fijar la métrica, el horizonte y la línea base antes de ajustar cualquier modelo. Elegir hiperparámetros con varias pruebas dentro de `train` y reservar `valid` para una única medición final. La vara a superar para esta serie es 13,7 unidades por día.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, secciones 0.1 y 1.6.

---

## DEC-012: En la serie de aprendizaje, los 25 de diciembre se imputan con `y[t-7]`

**Área:** modelado | **Fase:** 04 SARIMA (sección 2.5) | **Fecha:** 2026-11-16 | **Estado:** Vigente

**Decisión:** En `CA_3` / `FOODS_3_586`, los dos 25 de diciembre (ventas 0, tienda cerrada) se reemplazan por el valor del mismo día de la semana anterior: 2013-12-25 pasa de 0 a 67 y 2014-12-25 de 0 a 73. La serie tratada se llama `y_modelo` y es la que usan los pasos 3, 4 y 5; `y` queda como la original. La función `imputar_cierres` falla si alguna de las fechas indicadas tiene ventas. Esta decisión vale solo para la serie de aprendizaje; el tratamiento para el resto de las series sigue pendiente.

**Alternativa descartada:** (a) Dejar los ceros como están. (b) Una variable indicadora (*dummy*) del 25 de diciembre como variable externa del `SARIMAX`. (c) Eliminar esos días.

**Por qué la descartamos:**

| Opción | Problema |
|---|---|
| Dejar los ceros | El modelo los toma como demanda real. Ya contaminaron MSTL, que los copió como −59 unidades de "estacionalidad anual" |
| Variable indicadora | Recién podría entrar en el paso 5 (SARIMAX); los pasos 3 y 4 trabajan con la serie sola, y los tests y la ACF quedarían contaminados mientras tanto |
| Eliminar los días | Rompe la regla de un dato por día (`asfreq("D")`): "ayer" dejaría de ser el día anterior para el 26 de diciembre |

Efecto medido: ADF −3,569 (p = 0,0064) en la original contra −3,573 (p = 0,0063) en `y_modelo`; KPSS 0,419 (p ≈ 0,069) contra 0,400 (p ≈ 0,077). La conclusión no cambia. Ni `valid` (11-nov a 8-dic) ni los cortes del backtesting incluyen un 25 de diciembre, así que la evaluación tampoco cambia.

**Conclusión:** Un cero por tienda cerrada no es demanda: tratarlo antes de modelar. Para pronosticar un cierre futuro alcanza con una regla (cerrado = 0), sin pedírselo al modelo.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, sección 2.5 (función `imputar_cierres`).

---

## DEC-013: Sin diferenciar (`d = 0`, `D = 0`); el ciclo semanal con términos estacionales

**Área:** modelado | **Fase:** 04 SARIMA (paso 3, parte B) | **Fecha:** 2026-11-16 | **Estado:** Vigente, con matiz (ver la actualización y DEC-015)

**Decisión:** El modelo base es un SARIMA(p, 0, q)(P, 0, Q)₇ sobre `y_modelo`: sin diferencia simple ni estacional. El ciclo semanal lo capturan los términos estacionales `P` y `Q` con `s = 7`. La misma especificación con `D = 1` se compara en el backtesting del paso 5 como alternativa. Funciones: `diferenciar`, `resumen_diferenciacion`.

**Alternativa descartada:** (a) Diferencia estacional (`D = 1`), lo más común en tutoriales con datos semanales. (b) Diferencia simple (`d = 1`). (c) Las dos (`d = 1`, `D = 1`).

**Por qué la descartamos:**

| Versión | ADF p | KPSS p | Autocorr. retardo 1 | Autocorr. retardo 7 | Desvío |
|---|---|---|---|---|---|
| **Sin diferenciar (elegida)** | 0,006 | 0,077 | 0,43 | 0,41 | 17,7 |
| Simple (`d = 1`) | < 0,001 | > 0,10 | −0,29 | 0,23 | 18,8 |
| Estacional (`D = 1`) | < 0,001 | > 0,10 | 0,27 | −0,45 | 19,3 |
| Las dos | < 0,001 | > 0,10 | −0,46 | −0,52 | 23,3 |

- Las cuatro versiones salen estacionarias en los dos tests, así que los tests no alcanzan para elegir.
- Cada diferencia que sobra deja una autocorrelación negativa cerca de −0,5 en el retardo que diferenció y sube el desvío (sobrediferenciación). Es lo que pasa con `D = 1` en el retardo 7 y con `d = 1` en el retardo 1.
- La fuerza estacional semanal de `y_modelo` es 0,46. La regla de Hyndman y Athanasopoulos (*Forecasting: Principles and Practice*, cap. 9) aplica `D = 1` recién por encima de 0,64.
- El argumento a favor de `D = 1` es que, sin diferenciar, la autocorrelación en los múltiplos de 7 casi no baja (0,40, 0,35, 0,36, 0,36, 0,34, 0,29 y 0,33 en los retardos 7 a 49). Pero ese patrón plano es el de un ciclo **fijo**: el domingo suma unas 15,5 unidades en toda la serie (descomposición clásica, 2.2). La diferencia estacional es para un ciclo que cambia de forma al azar con el tiempo; aplicada a un ciclo fijo lo borra y deja el −0,45 en el retardo 7.

**Conclusión:** Usar la menor cantidad de diferencias que deja la serie estacionaria. Cuando los tests no discriminan, decidir con la autocorrelación en el retardo diferenciado (cerca de −0,5 significa que la diferencia sobra) y con el desvío (si sube, se agregó ruido). Como la evidencia sobre `D` no es unánime, la decisión final entre `D = 0` y `D = 1` la toma el error del backtesting en el paso 5.

**Actualización (2026-11-17, paso 5):** el backtesting no desempató: `Q = 1` (sin diferenciar) y `D = 1` con `(0, 1, 1)₇` dan el mismo error (MAE 13,4 y 13,3 sin Fourier; 11,7 y 11,6 con `K = 1`). Además, el ajuste de `Q = 1` dejó el AR estacional en 0,98 (0,9997 con Fourier) y el MA estacional en −0,88 (−0,986): casi se cancelan, y el modelo se comporta como uno con `D = 1`. La sobrediferenciación que se vio en el paso 3 era la de `D = 1` **sin** término MA; con `(0, 1, 1)₇` el MA la compensa. Por lo tanto el argumento de "ciclo fijo" vale a medias: el patrón semanal parece moverse despacio. Se mantiene `d = 0`, `D = 0` en el modelo elegido (DEC-015) porque el empate no justifica cambiarlo, pero `D = 1` sigue siendo una alternativa equivalente.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, sección 3, parte B (secciones 3.4 y 3.5).

---

## DEC-014: Lista corta de candidatos de SARIMA leída de ACF/PACF

**Área:** modelado | **Fase:** 04 SARIMA (paso 4, partes A y B) | **Fecha:** 2026-11-17 | **Estado:** Vigente

**Decisión:** Los gráficos de ACF y PACF de `y_modelo` sin diferenciar dan un punto de partida, SARIMA(1, 0, 0)(1, 0, 0)₇, y el paso 5 compara una lista corta (`GRILLA_ORDENES`) con backtesting y AIC:

| Candidato | `order` | `seasonal_order` |
|---|---|---|
| base | (1, 0, 0) | (1, 0, 0, 7) |
| `q = 1` | (1, 0, 1) | (1, 0, 0, 7) |
| `p = 2` | (2, 0, 0) | (1, 0, 0, 7) |
| `Q = 1` | (1, 0, 0) | (1, 0, 1, 7) |
| `P = 2` | (1, 0, 0) | (2, 0, 0, 7) |
| `D = 1` (DEC-013) | (1, 0, 0) | (0, 1, 1, 7) |

Funciones: `tabla_acf_pacf`, `graficar_acf_pacf`.

**Alternativa descartada:** (a) Elegir un solo modelo a ojo con la lectura de los gráficos. (b) Una búsqueda automática amplia (todas las combinaciones hasta un orden máximo, por ejemplo con `auto_arima`).

**Por qué la descartamos:**

| Opción | Problema |
|---|---|
| Un solo modelo a ojo | La lectura no es nítida: en los múltiplos de 7 la ACF no se corta ni decae (0,40, 0,35, 0,36, 0,36, 0,34, 0,29, 0,33) y la PACF baja de a poco (0,24, 0,16, 0,17, 0,08, 0,11, 0,06, 0,09). Los gráficos no distinguen entre `P = 1` y `P = 2`, ni dicen nada sobre `Q` |
| Búsqueda amplia | Cada especificación extra es otra comparación contra solo 6 cortes de 28 días. Cuantas más se prueban, más probable es que gane una por azar, el mismo problema que DEC-011 evita con `valid`. Además cada ajuste de un SARIMA estacional tiene costo de cómputo |
| Lista corta (elegida) | Los gráficos acotan los candidatos y el backtesting decide entre pocos, cada uno con un motivo |

Lo que muestran los gráficos:
- **Retardos cortos (parte A):** la PACF vale 0,43 en el retardo 1 y 0,01, −0,05 y 0,00 en los retardos 2 a 4, dentro de la franja (±0,06). La ACF decae: 0,43, 0,20, 0,05, 0,00. Un AR(1) puro daría 0,43² = 0,19 en el retardo 2, y la observada es 0,20. Lectura: `p = 1`, `q = 0`.
- **Retardos estacionales (parte B):** el retardo 7 es el más fuerte de la PACF (0,24); los retardos 14 y 21 (0,16 y 0,17) hacen de `P = 2` una alternativa. La ACF no se corta, así que `Q` solo puede ser una alternativa. Los retardos 6 y 8 (ACF 0,28 y 0,27) flanquean al 7 y se toman como parte del ciclo semanal, no como un AR de orden 6.

**Conclusión:** Usar ACF/PACF para acotar candidatos y decidir entre ellos con el backtesting. Si los residuos del modelo con `P = 1` dejan barras en los retardos 5 y 6, revisar. Si el coeficiente estacional sale cerca de 1 o el ajuste no converge, queda pendiente probar variables indicadoras del día de la semana (ver pendientes en `decisions.md`).

**Resultado (2026-11-17):** los 6 candidatos convergieron. Con `P = 1` el coeficiente estacional dio 0,32 (el riesgo no se dio); con `Q = 1` subió a 0,98. El detalle de la comparación está en DEC-015.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, sección 4, partes A y B (`GRILLA_ORDENES`, `tabla_acf_pacf`, `graficar_acf_pacf`).

---

## DEC-015: Modelo del paso 5: SARIMAX(1, 0, 0)(1, 0, 1)₇ con Fourier `K = 1`, que no supera de forma consistente a la línea base

**Área:** modelado | **Fase:** 04 SARIMA (paso 5, partes A a D) | **Fecha:** 2026-11-17 | **Estado:** Vigente

**Decisión:** Se elige SARIMAX(1, 0, 0)(1, 0, 1)₇ con un par de términos de Fourier (`K = 1`) y constante, sobre `y_modelo`, ajustado con todo `train`. Es el candidato `Q = 1` de DEC-014 más la ola anual. **No se retoca con el resultado de `valid`.** Funciones: `metodo_sarima`, `resumir`, `backtest_fechas`.

**Alternativa descartada:** (a) `D = 1` con `(0, 1, 1)₇`. (b) `K = 2` y `K = 3`. (c) El modelo de partida (1, 0, 0)(1, 0, 0)₇ y las variantes `q = 1`, `p = 2` y `P = 2`.

**Por qué la descartamos:**

Ajuste de los 6 candidatos sobre toda la serie (parte A):

| Candidato | AIC | `sigma` | Coeficiente estacional |
|---|---|---|---|
| base | 8.645 | 15,1 | AR 0,32 |
| `q = 1` | 8.640 | 15,1 | AR 0,34 |
| `p = 2` | 8.640 | 15,1 | AR 0,34 |
| `Q = 1` | 8.480 | 13,9 | AR 0,98 y MA −0,88 |
| `P = 2` | 8.591 | 14,7 | AR 0,25 y 0,23 |
| `D = 1` | 8.430 (no comparable) | 14,0 | MA −0,90 |

Backtesting a 28 días, 6 cortes (parte B), MAE medio: media de 4 semanas 13,7; `D = 1` 13,3; `Q = 1` 13,4; `P = 2` 14,5; base, `p = 2` y `q = 1` 15,1 a 15,2; naive estacional 18,2. Con Fourier, los dos mejores bajan a 11,6 a 11,9 para `K = 1, 2 y 3`, y le ganan a la media de 4 semanas en los 6 cortes. Con Fourier `K = 1`: `D = 1` 11,6 y `Q = 1` 11,7.

- **`D = 1` vs `Q = 1`:** empate, y el ajuste de `Q = 1` ya se comporta como `D = 1` (ver actualización de DEC-013). Se elige `Q = 1` por desempate, para no abandonar `d = 0`, `D = 0`.
- **`K`:** `K = 1, 2 y 3` difieren en 0,3 como máximo, que con 6 cortes es ruido; se toma el más simple. DEC-009 hablaba de `K = 2`.
- **Variante `p = 2`** (parte C): los residuos del elegido dejan el retardo 2 en 0,10 y Ljung-Box da p ≈ 0. La variante dio el mismo MAE (11,7), pero su ajuste cayó en un resultado degenerado (AIC 8.696 contra 8.416, `ar.S.L7` = −0,997, `ma.S.L7` = +1,000, constante 99). **No se evaluó bien** y queda pendiente.

**Resultado en `valid` (medición única, parte C):** SARIMAX elegido MAE 10,4 (RMSE 13,9); media de 4 semanas 9,2 (11,4); naive estacional 10,1 (14,4). **No le gana a la línea base**, al revés del backtesting.

**Noviembre-diciembre (parte D):** los 6 cortes terminan el 10-nov y no cubren esas semanas. Se probó el modelo en el 11-nov a 8-dic de 2013 y de 2014 (ventanas dentro de `train`, **elegidas después de ver `valid`**, así que `valid` ya no es una medición del todo limpia; la de 2013 tiene 314 días de historia). MAE promedio: media de 4 semanas 13,2; `Q = 1` sin Fourier 12,5; `Q = 1` con `K = 1` 12,3; `D = 1` con `K = 1` 12,3. La ventaja es del 7 %, contra 15 % en los cortes originales, y Fourier no mejora en esas semanas. En `valid` todos los métodos erraron menos que en 2013 y 2014, y la media de 4 semanas bajó más que el SARIMAX.

**Conclusión:** El SARIMAX gana en 8 ventanas de backtesting (6 originales y 2 de noviembre-diciembre) pero pierde en `valid`; con tan pocas ventanas no se puede separar un modelo flojo de un mes con mala suerte. **No se puede afirmar que supere a la línea base de forma consistente.** Reglas: (1) los cortes del backtesting deben cubrir las épocas del año que se van a pronosticar; (2) si agregar un parámetro empeora mucho el AIC, el ajuste falló y la comparación no vale; (3) una vez medido `valid`, no se retoca el modelo con ese resultado.

**Código afectado:** `03_notebooks/04_SARIMA.ipynb`, sección 5 (partes A a D).

---
