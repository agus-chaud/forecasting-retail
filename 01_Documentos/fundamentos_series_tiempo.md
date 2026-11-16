# Fundamentos de series de tiempo para el notebook 04

Este documento acompaña a [`04_SARIMA.ipynb`](../03_notebooks/04_SARIMA.ipynb). La idea es que, al leer una celda, puedas saber qué problema resuelve y por qué está escrita así y no de otra forma. 

Los ejemplos usan siempre la misma serie, `CA_3` / `FOODS_3_586`: las ventas diarias de un producto de comida en una tienda de California, del 2013-01-01 al 2015-11-10. Los números salen del notebook. Las secciones 1 a 6 explican lo que ya está construido; de la 7 en adelante se explica lo que todavía falta construir, así que esa parte se va a revisar cuando exista el código.

---

## 1. Qué cambia cuando los datos tienen fecha

En un problema tabular típico (predecir si un cliente compra, por ejemplo) cada fila es un caso independiente. Podés mezclar las filas, partir al azar en train y test, y el modelo no se entera.

En una serie de tiempo lo que pasó ayer dice algo sobre lo que pasa hoy. Esta serie vendió 73,8 unidades por día en promedio, pero si sabés que hoy es domingo y que el domingo pasado se vendieron 95, tu estimación cambia bastante. Esa dependencia entre días cercanos es justamente lo que vamos a modelar, y tiene dos consecuencias prácticas.

**No se parte al azar.** Si mezclás los días y elegís el 20 % para validar, en el entrenamiento quedan días posteriores a los que querés predecir. El modelo "ve el futuro" (fuga de información, o *data leakage*) y la métrica de validación sale mejor que lo que vas a obtener en producción, donde el futuro no está disponible. Por eso el split es por fecha: todo `train` es anterior a todo `valid` (DEC-002).

**La validación imita el uso real.** En producción vas a tener la historia hasta hoy y vas a tener que predecir los próximos días. El split reproduce eso: `train` hasta el 2015-11-10, `valid` los 28 días siguientes y `reserva` los 23 días posteriores, que no se tocan hasta el final. Que `valid` tenga 28 días no es casual: son exactamente 4 semanas, así que tiene cuatro lunes, cuatro martes y así con cada día. Si tuviera 30 días, dos días de la semana pesarían más que el resto en la métrica.

Una tercera regla, menos obvia: cualquier número que se calcule a partir de los datos (un umbral, una media para imputar, los parámetros del modelo) se calcula solo con `train`. Si usás `valid` para decidir algo, deja de ser una prueba honesta.

## 2. Cómo se representa una serie en pandas

Para `statsmodels`, la librería donde viven ARIMA y SARIMA, una serie es una `pd.Series` cuyo índice son fechas y que tiene una frecuencia declarada. La función `extraer_serie` del notebook hace exactamente eso: filtra una tienda y un producto, pone la fecha como índice y llama a `.asfreq("D")`.

`.asfreq("D")` le dice a pandas "tiene que haber un dato por día". Si falta una fecha, la agrega con `NaN`. Parece un detalle, pero es una protección importante. Todos los modelos de este notebook trabajan con la idea de "el dato anterior", y asumen que el dato anterior es el día anterior. Si faltara el 3 de marzo, para el modelo el 2 de marzo pasaría a ser "ayer" del 4 de marzo, y todo lo que aprenda sobre la relación entre días consecutivos quedaría mal. Por eso la función falla si encuentra huecos en vez de seguir de largo. Esta serie tiene los 1.044 días completos, pero la función está pensada para cuando lleguen datos nuevos.

El índice de fechas también te da herramientas cómodas: `y["2014-07"]` devuelve todo julio de 2014, `y.index.day_of_week` da el día de la semana (0 es lunes) y `y.resample("MS").mean()` agrupa por mes.

Un detalle que confunde: el tablón tiene una columna `wday` que sigue la convención de la competencia M5, donde 1 es sábado. El notebook 04 no la usa; usa `day_of_week` de pandas, donde 0 es lunes y 6 es domingo. Son dos numeraciones distintas del mismo dato.

## 3. Mirar la serie antes de modelar

El primer paso con cualquier serie es graficarla entera. No hay atajo para esto. Con tres años de datos diarios el gráfico se ve como una franja gris temblorosa, y por eso se le superponen **medias móviles**.

Una media móvil de 7 días es, para cada fecha, el promedio de ese día y los seis anteriores (`y.rolling(7).mean()`). Tiene una propiedad muy útil acá: cualquier ventana de 7 días consecutivos contiene exactamente un lunes, un martes, un miércoles y así hasta el domingo. El efecto del fin de semana entra una vez en cada promedio y se cancela. Lo que queda es el movimiento de fondo. La media de 28 días suaviza todavía más y deja ver la forma del año.

En esta serie el gráfico muestra tres cosas, que después los números confirmaron:

- Un ciclo semanal muy marcado. El domingo se venden en promedio 89,5 unidades y el miércoles 63,2: unas 26 unidades de diferencia sobre una media de 73,8.
- Una ola anual. Juntando los tres años, agosto promedia 87,4 y enero 62,3.
- Ninguna tendencia de largo plazo. La media por año fue 72,8, 75,3 y 73,2.

Y una rareza: los únicos dos días con cero ventas son los 25 de diciembre de 2013 y 2014. No es que nadie quiso comprar; la tienda estaba cerrada. Esa diferencia (no hubo demanda contra no se pudo vender) importa, y todavía está pendiente decidir cómo tratarla.

## 4. Las piezas de una serie

Casi todo el análisis clásico parte de pensar la serie como la combinación de tres piezas:

- **Tendencia**: el nivel de fondo, que cambia despacio. En esta serie es casi plana.
- **Estacionalidad**: un patrón que se repite con un período fijo. Acá hay dos: el semanal (período 7) y el anual (período 365).
- **Residuo**: lo que queda después de sacar las otras dos. Incluye el ruido de cada día, los eventos y las sorpresas.

Hay que distinguir estacionalidad de ciclo. Estacionalidad es un patrón de período fijo y conocido, como la semana o el año calendario. Un ciclo económico, que dura "algunos años" sin período fijo, no es estacionalidad y los modelos de este notebook no lo capturan.

Las piezas se pueden combinar sumando o multiplicando. En la forma **aditiva**, `y = tendencia + estacionalidad + residuo`, el domingo agrega siempre la misma cantidad de unidades. En la **multiplicativa**, `y = tendencia × estacionalidad × residuo`, el domingo agrega un porcentaje: si el nivel general sube, el pico del domingo sube con él.

La forma de elegir es medir si el tamaño del ciclo crece con el nivel. El notebook calcula, para cada uno de los 35 meses, la media del mes y la diferencia entre el día de la semana más alto y el más bajo. Si la multiplicativa fuera la correcta, los meses de nivel alto tendrían ciclos más grandes. No pasa: enero de 2013 (nivel 62,1) tiene una amplitud de 30,1 y agosto de 2014 (nivel 90,1), de 30,2. La correlación entre las dos cosas es 0,11, prácticamente nula. Por eso se usa la aditiva (DEC-008). La multiplicativa además tiene problemas con los ceros, y acá hay dos.

## 5. Dos formas de descomponer

Descomponer es estimar esas tres piezas a partir de la serie. El notebook usa dos métodos.

**Descomposición clásica** (`seasonal_decompose`). Primero estima la tendencia con una media móvil centrada de 7 días (tres días antes, el día y tres después). Después, para cada día de la semana, promedia cuánto se aparta la serie de esa tendencia: así obtiene un único número por día, igual para los tres años. Lo que sobra es el residuo. En esta serie da domingo +15,5, sábado +10,9 y miércoles −10,5 unidades respecto de la tendencia. Como la media es centrada, no se puede calcular en los tres primeros ni en los tres últimos días, y por eso la tendencia tiene 6 valores `NaN`.

Es fácil de entender pero tiene dos debilidades. Fuerza el mismo patrón semanal durante tres años, aunque la costumbre de los clientes cambie. Y un día raro, como un 25 de diciembre con cero ventas, entra con todo su peso en los promedios.

**STL** (*Seasonal-Trend decomposition using Loess*). Hace el mismo trabajo con un método de suavizado local llamado *loess*, que deja que el patrón semanal cambie de a poco con el tiempo. Con `robust=True` les da menos peso a los días que se apartan mucho del resto, así que el 25 de diciembre contamina menos.

Para resumir cuánto pesa cada pieza se usa una medida llamada **fuerza**, que propone el libro *Forecasting: Principles and Practice* de Hyndman y Athanasopoulos:

```
fuerza = 1 − var(residuo) / var(componente + residuo)
```

La lógica es esta: si el componente es grande comparado con el ruido, sacarlo achica mucho la varianza y la fuerza se acerca a 1. Si el componente es chico, el residuo explica casi todo y la fuerza queda cerca de 0. En esta serie la fuerza semanal con STL da 0,45, moderada. No es que el ciclo semanal sea débil (son 26 unidades entre el mejor y el peor día); es que el ruido diario también es grande.

Hay un detalle del gráfico de STL que conviene notar. Como solo le dijimos que existía el período 7, la ola anual no tiene dónde ir y termina dentro de la "tendencia", que sube en verano y baja en invierno. Una descomposición solo separa lo que le pedís que separe.

## 6. Sobreajuste y términos de Fourier

Para separar también la ola anual probamos `MSTL`, que acepta varios períodos a la vez: le pedimos 7 y 365. El resultado fue malo, y entender por qué es probablemente lo más útil de este paso.

Una estacionalidad anual real debería ser una curva suave: las ventas suben en verano y bajan en invierno sin saltar de un día al otro. La componente anual que devolvió MSTL salta en promedio 9,8 unidades entre días consecutivos, y sus valores más extremos son días sueltos: los dos 25 de diciembre (cerca de −59) y el 4 de julio de 2013 (+52).

La causa es la cantidad de datos. Para estimar "cuánto vende esta serie un 25 de diciembre en comparación con el resto del año", MSTL solo tiene dos 25 de diciembre (los datos cubren 2,86 años). Con dos observaciones, la mejor estimación posible es copiar lo que pasó esos dos días. Eso es **sobreajuste**: el método memoriza el ruido de los datos que vio en vez de aprender un patrón que se repita. En ML tabular lo conocés como un árbol de decisión sin límite de profundidad que termina con una hoja por fila. Acá es lo mismo con otra forma.

La solución es restringir la forma que puede tener la curva anual. Los **términos de Fourier** hacen eso. En lugar de estimar 365 valores (uno por día del año), se describen con unas pocas ondas seno y coseno que completan un ciclo por año. La función `terminos_fourier` crea, para cada fecha, columnas como estas:

```
sin_1 = sin(2π · día_del_año / 365,25)
cos_1 = cos(2π · día_del_año / 365,25)
sin_2 = sin(2π · 2 · día_del_año / 365,25)
cos_2 = cos(2π · 2 · día_del_año / 365,25)
```

El primer par (k = 1) dibuja una sola ola por año, un máximo y un mínimo. El segundo par (k = 2) completa dos olas por año y permite formas un poco más complejas. Una regresión lineal busca cuánto pesa cada columna, y la suma ponderada da la curva anual. Con `K = 2` pares se estiman 4 números en lugar de 365, y la curva no puede saltar de un día al otro aunque quiera. El resultado en esta serie es una ola con 18,5 unidades de diferencia entre su pico y su valle, que explica el 42 % de la variación de la media móvil de 7 días.

Las columnas de Fourier tienen otra ventaja práctica: dependen solo de la fecha. Para predecir el 2 de diciembre de 2015 se pueden calcular sin saber nada de ese día, cosa que no pasa con una variable como "ventas de ayer".

Por qué no usar directamente un SARIMA con período 365 se explica en la sección 9. La decisión completa está en DEC-009. La regla práctica que queda: no intentes estimar una estacionalidad punto por punto si no tenés al menos tres ciclos completos, y desconfiá de cualquier componente estacional cuyos valores más extremos coinciden con días puntuales.

## 7. Estacionariedad (paso 3)

ARIMA aprende relaciones del tipo "el valor de hoy se parece en tal proporción al de ayer". Para que tenga sentido aprender una proporción así con los datos de 2013 y usarla en 2015, esa relación tiene que ser la misma en todo el período. Esa propiedad se llama **estacionariedad**.

Una serie es estacionaria (en el sentido que nos importa) cuando su media, su varianza y la relación entre un día y los anteriores no cambian con el tiempo. Una serie con tendencia no lo es, porque su media va subiendo. Una serie con estacionalidad tampoco, porque la media del domingo es distinta de la del miércoles: la media depende de qué día mires.

### Diferenciar

La forma estándar de volver estacionaria una serie es **diferenciarla**: en vez de modelar las ventas, modelar cuánto cambiaron.

- **Diferencia simple**: `y[t] − y[t−1]`, el cambio respecto de ayer. Elimina una tendencia. En pandas, `y.diff(1)`.
- **Diferencia estacional**: `y[t] − y[t−7]`, el cambio respecto del mismo día de la semana anterior. Elimina el ciclo semanal, porque compara domingo contra domingo. En pandas, `y.diff(7)`.

Cuántas veces se diferencia es una decisión, y el exceso también es un problema. Si diferenciás una serie que ya era estacionaria, le agregás ruido y una correlación negativa artificial entre días consecutivos. Una señal típica de sobrediferenciación es que la autocorrelación en el retardo 1 (sección 8) quede cerca de −0,5. Por lo general se termina con una diferencia simple, una estacional o ninguna, y casi nunca con más de dos en total.

Para esta serie, por lo que vimos, lo esperable es que la diferencia estacional de 7 sea necesaria (el ciclo semanal es fuerte) y que la simple no lo sea (no hay tendencia). Pero eso hay que comprobarlo en el paso 3, no suponerlo.

### Tests de estacionariedad

Hay dos tests que se usan juntos porque plantean la pregunta al revés:

- **ADF** (*Augmented Dickey-Fuller*). Su hipótesis nula es que la serie **no** es estacionaria. Un p-valor menor que 0,05 permite rechazarla y concluir que la serie es estacionaria.
- **KPSS**. Su hipótesis nula es que la serie **sí** es estacionaria. Un p-valor menor que 0,05 indica que no lo es.

Si los dos coinciden, la conclusión es firme. Si se contradicen, la serie está en una zona gris y conviene mirar los gráficos antes de decidir. Ninguno de los dos detecta bien la estacionalidad, así que la diferencia estacional se decide sobre todo mirando la serie y la autocorrelación en los retardos 7, 14 y 21.

## 8. Autocorrelación: ACF y PACF (paso 4)

La **autocorrelación** en el retardo *k* es la correlación entre la serie y la misma serie corrida *k* días. Es la correlación de Pearson de siempre, solo que entre `y[t]` y `y[t−k]`. Si la autocorrelación en el retardo 7 es alta, lo que se vende un día se parece a lo que se vendió el mismo día de la semana anterior.

La **ACF** (*autocorrelation function*) es el gráfico de esas correlaciones para los retardos 1, 2, 3... La **PACF** (*partial autocorrelation function*) muestra la correlación en el retardo *k* después de descontar lo que ya explican los retardos intermedios. La diferencia importa. Si hoy se parece a ayer y ayer se parece a anteayer, hoy va a parecerse algo a anteayer aunque no haya ninguna relación directa entre esos dos días; la ACF muestra esa correlación indirecta, la PACF la descuenta.

Los dos gráficos traen una franja sombreada. Las barras que quedan adentro no se distinguen de cero. Con 1.044 días, el borde de la franja está aproximadamente en ±1,96/√1044 ≈ ±0,06.

Estos gráficos se usan para elegir los órdenes del modelo (las letras de la sección 9) con unas reglas de lectura clásicas:

| Lo que ves | Lo que sugiere |
|---|---|
| La PACF se corta de golpe después del retardo *p* y la ACF decae de a poco | Un componente AR de orden *p* |
| La ACF se corta de golpe después del retardo *q* y la PACF decae de a poco | Un componente MA de orden *q* |
| Picos en los retardos 7, 14, 21 | Estructura estacional semanal: lo mismo, mirando solo los múltiplos de 7 |

Con datos reales los gráficos casi nunca son tan limpios como en los libros. Sirven para elegir un punto de partida razonable y un par de alternativas cercanas, que después se comparan con un criterio objetivo (sección 10). Siempre se leen sobre la serie ya diferenciada, porque una serie no estacionaria tiene una ACF que decae muy lento y tapa todo lo demás.

## 9. ARIMA, SARIMA y SARIMAX (paso 5)

**ARIMA(p, d, q)** combina tres ideas, una por letra:

- **AR(p)**, autorregresivo: el valor de hoy es una combinación lineal de los *p* valores anteriores. Con p = 2, algo como `hoy ≈ a·ayer + b·anteayer`. Es una regresión lineal donde las variables son el pasado de la propia serie.
- **I(d)**, integrado: la serie se diferencia *d* veces antes de aplicar lo demás (sección 7). El modelo después deshace la diferencia para devolver las predicciones en unidades vendidas.
- **MA(q)**, media móvil: el valor de hoy también depende de los errores que cometió el modelo en los *q* días anteriores. Si ayer el modelo predijo 70 y se vendieron 80, ese error de +10 puede ajustar la predicción de hoy. No tiene nada que ver con la media móvil de la sección 3, aunque se llame igual; es una coincidencia de nombres que confunde a todo el mundo.

**SARIMA(p, d, q)(P, D, Q)s** agrega la misma estructura en los retardos estacionales. Con s = 7, P = 1 significa "el valor de hoy depende del valor de hace 7 días", D = 1 es la diferencia estacional `y[t] − y[t−7]` y Q = 1 usa el error de hace 7 días. Un ejemplo de especificación para esta serie podría ser SARIMA(1, 0, 1)(1, 1, 1)7, pero los números concretos se eligen en los pasos 3 y 4.

**SARIMAX** agrega la X: variables externas que no salen de la propia serie. Acá son los términos de Fourier de la sección 6. En `statsmodels` el modelo funciona como una regresión lineal sobre esas variables, donde el error de la regresión, en vez de ser ruido independiente, sigue un SARIMA. La regresión captura la ola anual y el SARIMA captura el ciclo semanal y la dependencia entre días cercanos.

¿Por qué no un SARIMA con s = 365 y listo? Por dos razones. La primera es la misma del MSTL: con menos de 3 ciclos anuales no hay datos para estimar la relación entre un día y el mismo día del año anterior. La segunda es computacional: un modelo con retardos de 365 días es muy lento de ajustar y, en la práctica, con datos diarios muchas veces ni siquiera converge.

## 10. Elegir entre modelos: AIC y residuos (paso 5)

Con varios candidatos razonables (por ejemplo, distintos p, q, P, Q, o distinta cantidad de pares de Fourier) hace falta un criterio para elegir.

El **AIC** (*Akaike Information Criterion*) resume qué tan bien ajusta un modelo a `train` y le resta puntos por cada parámetro que agrega. Más bajo es mejor. Existe para evitar el sobreajuste de la sección 6: un modelo con más parámetros siempre ajusta mejor los datos que vio, y el AIC solo lo premia si la mejora compensa la complejidad. Una precaución: solo se pueden comparar AIC de modelos con el mismo orden de diferenciación (los mismos d y D), porque si cambia la diferenciación cambian los datos sobre los que se mide el ajuste.

Elegido un modelo, se revisan sus **residuos**: la diferencia entre lo vendido y lo que el modelo predijo para cada día de `train`. Si el modelo capturó toda la estructura, los residuos tienen que parecer ruido sin patrón, lo que se llama *ruido blanco*. Se revisan tres cosas:

- La ACF de los residuos no debería tener barras fuera de la franja, sobre todo en los retardos 1 y 7.
- El **test de Ljung-Box**, cuya hipótesis nula es "los residuos no tienen autocorrelación". Acá se quiere un p-valor **mayor** que 0,05, al revés de lo habitual.
- El gráfico de residuos en el tiempo, para ver si quedan días con errores enormes. Ya sabemos que los 25 de diciembre van a aparecer, porque el modelo no tiene forma de saber que la tienda cierra.

Si los residuos todavía tienen patrón, el modelo se quedó corto y hay que volver a los pasos 3 y 4.

## 11. Predecir y medir el error (paso 5)

Para predecir los 28 días de `valid`, el modelo arranca desde el último día de `train` y avanza un día por vez. El día 1 lo predice con datos reales; desde el día 2 en adelante, parte de lo que necesita son sus propias predicciones anteriores, porque los valores reales de esos días todavía no se conocen. La solución del curso hace lo mismo a mano con su `forecast_recursivo` ([`Producción/funciones.py`](../Producción/funciones.py)). Una consecuencia es que el error tiende a crecer con el horizonte, y por eso los intervalos de predicción que devuelve SARIMAX se van abriendo hacia el final.

Para medir el error sobre `valid` hay varias métricas y cada una tiene un sesgo distinto:

| Métrica | Qué mide | Cuidado con |
|---|---|---|
| **MAE** (error absoluto medio) | Cuántas unidades se equivoca el modelo en promedio por día | Nada especial. Es la que usa la solución del curso, así que facilita la comparación |
| **RMSE** (raíz del error cuadrático medio) | Parecido al MAE, pero castiga más los errores grandes | Un solo día muy malo lo infla |
| **MAPE** (error porcentual absoluto medio) | El error como porcentaje de lo vendido | Se rompe cuando las ventas reales son 0 (división por cero), como el 25 de diciembre |

El MAE solo no dice si un modelo es bueno. Hace falta compararlo con una referencia simple, un **baseline**. El estándar en series con estacionalidad es el **naive estacional**: predecir que cada día se vende lo mismo que el mismo día de la semana anterior. No requiere entrenar nada. Si un SARIMA no le gana a eso, toda la complejidad no está sirviendo. Es más común de lo que parece, y es la primera comparación que conviene hacer.

Una última aclaración: medir sobre un único bloque de 28 días da una sola cifra, que puede haber salido buena o mala por suerte. La evaluación más sólida repite el ejercicio desde varios puntos de corte (validación con origen móvil). La solución del curso lo hace con `TimeSeriesSplit` de scikit-learn: 5 cortes con bloques de prueba de 8 días. Para aprender alcanza con un solo corte; para tomar decisiones en serio conviene hacer varios.

## 12. SARIMA contra boosting (paso 6)

La solución del curso usa otro enfoque: un `HistGradientBoostingRegressor` por producto, entrenado sobre variables construidas a mano. Esas variables son las ventas de los 7 días anteriores (*lags*), medias, mínimos y máximos móviles de distintas ventanas, los precios de los días anteriores, los eventos del calendario y unas marcas de posible rotura de stock (varios días seguidos sin ventas).

Visto de cerca, los dos enfoques buscan lo mismo: usar el pasado reciente de la serie para predecir el día siguiente. Lo que cambia es quién decide la forma de esa relación.

| | SARIMA / SARIMAX | Boosting con lags |
|---|---|---|
| Qué relación supone | Lineal, con una estructura fija (AR, MA, estacional) | Cualquier forma: la aprenden los árboles |
| De dónde salen las variables | Del propio modelo (retardos y errores pasados) más las X que le des | Las construís vos (feature engineering) |
| Precio, promociones, eventos | Solo si los agregás como X | Entran como variables más |
| Incertidumbre | Da intervalos de predicción con base estadística | No los da de forma directa |
| Datos que necesita | Funciona con una serie corta | Necesita más datos para no sobreajustar |
| Interpretación | Cada coeficiente tiene un significado | Hay que usar herramientas aparte (importancia de variables, SHAP) |

La comparación del paso 6 tiene que ser justa: la misma serie, el mismo `train`, los mismos 28 días de `valid` y la misma métrica (MAE), con el naive estacional como piso para los dos. No hay un ganador fijo; depende de la serie. Para una serie estable como esta, con un ciclo semanal limpio y pocos eventos, SARIMA puede competir bien. En series con promociones fuertes o mucha intermitencia, el boosting suele tener ventaja porque puede usar el precio y los eventos de forma más flexible.

## Glosario

- **ACF / PACF**: gráficos de autocorrelación total y parcial según el retardo. Sección 8.
- **ADF / KPSS**: tests de estacionariedad con hipótesis nulas opuestas. Sección 7.
- **AIC**: criterio para comparar modelos que premia el ajuste y castiga la cantidad de parámetros. Sección 10.
- **Baseline / naive estacional**: predicción de referencia sin modelo: repetir el mismo día de la semana anterior. Sección 11.
- **Demanda intermitente**: serie con muchos días en cero. ARIMA no la modela bien. Ver DEC-006.
- **Diferenciar**: reemplazar la serie por sus cambios (`y.diff(1)`, `y.diff(7)`). Sección 7.
- **Estacionalidad**: patrón que se repite con período fijo. Sección 4.
- **Estacionariedad**: media, varianza y autocorrelación constantes en el tiempo. Sección 7.
- **Fuga de información (*leakage*)**: usar, al entrenar o validar, datos que en la realidad no estarían disponibles. Sección 1.
- **Fuerza de un componente**: proporción de la variación que explica, de 0 a 1. Sección 5.
- **Horizonte**: cuántos días hacia adelante se predice. Acá, 28. Sección 11.
- **Lag / retardo**: el valor de la serie *k* días antes. `y.shift(k)` en pandas.
- **Ljung-Box**: test sobre la autocorrelación de los residuos; se busca p > 0,05. Sección 10.
- **MAE, RMSE, MAPE**: métricas de error. Sección 11.
- **Media móvil (suavizado)**: promedio de los últimos *n* días. Sección 3. No confundir con el MA de ARIMA.
- **Residuo**: lo que queda de la serie después de sacar tendencia y estacionalidad, o la diferencia entre lo real y lo predicho por un modelo.
- **Ruido blanco**: serie sin ningún patrón ni autocorrelación. Es lo que deberían parecer los residuos de un buen modelo.
- **Sobreajuste**: aprender el ruido de los datos de entrenamiento en lugar del patrón. Sección 6.
- **Términos de Fourier**: pares seno/coseno que describen una estacionalidad suave con pocos parámetros. Sección 6.
- **Tendencia**: el nivel de fondo de la serie, que cambia despacio. Sección 4.
- **Univariado**: modelo que usa solo la historia de una serie. ARIMA y SARIMA lo son; SARIMAX agrega variables externas.

## Para seguir leyendo

*Forecasting: Principles and Practice* (3.ª edición), de Rob J. Hyndman y George Athanasopoulos, es gratuito en [otexts.com/fpp3](https://otexts.com/fpp3/). Los capítulos 3 (descomposición), 9 (ARIMA) y 10 (regresión con errores ARIMA, que es lo que hace SARIMAX) cubren casi todo lo de este documento con más profundidad. Los ejemplos están en R, pero los conceptos son los mismos.
