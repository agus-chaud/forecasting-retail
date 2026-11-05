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
