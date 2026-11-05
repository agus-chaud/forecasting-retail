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

---

## Pendientes reales

| Decisión | Área |
|---|---|
| Tratamiento de las rachas largas de ceros (hasta 361 días) y las semanas con ventas casi nulas: dejarlas, marcarlas con una variable o excluirlas del entrenamiento | calidad-datos |
| Confirmar con quien conozca el origen de los datos si el precio 1,00 de `FOODS_3_090` (`CA_3`) es un relleno por falta de disponibilidad o un descuento real | calidad-datos |
| Tratamiento del 25 de diciembre (tiendas cerradas, ventas 0 en las 20 series): variable propia o filtrado | feature-engineering |
| Cómo representar la promoción de agosto-septiembre 2013 de `FOODS_3_090` (por ejemplo, precio relativo a la mediana de la serie) | feature-engineering |

---

## Decisiones

**DEC-001 — Eliminar las 71 filas sin precio.** Se eliminan las 71 filas de `FOODS_3_288` con `sell_price` nulo (0,32 % del tablón). **Por qué:** tienen 0 ventas y son días en que el producto no existía; imputar el precio dejaría ceros falsos. **Regla:** Distinguir siempre "no existía" (se elimina) de "no se vendió" (se conserva el cero), y confirmar con un `assert` que las filas no tienen ventas.

**DEC-002 — Split temporal.** `train` hasta 2015-11-10 (20.809 filas), `valid` 28 días (560) y `reserva` 23 días (460). **Por qué:** un split al azar mete días futuros en `train`; 28 días son 4 semanas completas y `reserva` coincide con `DatosParaProduccion.csv`. **Regla:** Nunca partir series de tiempo al azar; `valid` en múltiplos de 7 días y los umbrales aprendidos se calculan solo con `train`.

**DEC-003 — Tipos categóricos.** `year`, `month` (`"01".."12"`) y `wday` (`"1".."7"`, 1 = sábado) pasan a `category` ordenada, igual en `train`, `valid` y `reserva`. **Por qué:** son etiquetas, no cantidades, y `category` pesa 55 veces menos que `object` (21.048 contra 1.168.403 bytes en `weekday`). **Regla:** Usar `category` ordenada con lista explícita de categorías y dejar que la función falle ante valores no declarados.

**DEC-004 — Columnas constantes.** Se conservan `state_id` (solo `CA`), `dept_id` (solo `FOODS_3`) y `cat_id` (solo `FOODS`). **Por qué:** más adelante se podrán crear datos ficticios con más estados, departamentos y categorías. **Regla:** Nunca asumir un solo estado, departamento o categoría; si una constante estorba en un modelo, excluirla ahí y no en el tablón.

**DEC-005 — Funciones reutilizables.** El análisis se escribe en funciones que reciben un DataFrame y rutas con `Path`, sin valores fijos. **Por qué:** las ventas son datos incrementales y el proyecto practica reentrenamiento; con funciones, un dato nuevo se procesa llamando de nuevo, no editando celdas. **Regla:** Toda celda repetible con datos nuevos se convierte en función con parámetros explícitos.

---
