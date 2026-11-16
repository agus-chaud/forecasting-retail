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

**Decisión:** El ciclo semanal lo modela SARIMA con `s = 7`. El ciclo anual entra como variables externas de `SARIMAX`: pares seno/coseno del día del año (términos de Fourier, función `terminos_fourier`). La cantidad de pares `K` se elige en el paso 5 con el error en `valid`; `K = 2` es el punto de partida.

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
