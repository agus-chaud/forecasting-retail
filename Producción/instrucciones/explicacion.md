# Explicación del proceso de despliegue y ejecución

Esta carpeta contiene **todo lo necesario** para reentrenar el modelo y generar predicciones de ventas. Aquí tienes la secuencia de pasos y archivos implicados:

## 1. Reentrenamiento del modelo

- **Script:** `reentrenamiento.py`
- **Qué hace:**
  - Carga el archivo `train.pkl` (debe estar en esta carpeta).
  - Preprocesa los datos y entrena los modelos para cada producto.
  - Guarda los artefactos necesarios para la predicción:
    - `lista_modelos_retail.pkl` (modelos entrenados)
    - `ohe_retail.pkl` (encoder OneHot)
    - `te_retail.pkl` (encoder Target)
- **Cómo lanzarlo:**
  
  ```bash
  python reentrenamiento.py
  ```

## 2. Generación de predicciones

- **Script:** `ejecucion.py`
- **Qué hace:**
  - Carga el archivo `DatosParaProduccion.csv` (debe estar en esta carpeta).
  - Carga los artefactos generados en el paso anterior.
  - Preprocesa los datos y genera las predicciones para los próximos días.
  - Guarda el resultado en `predicciones.csv` (en esta misma carpeta).
- **Cómo lanzarlo:**
  
  ```bash
  python ejecucion.py
  ```

## 3. Archivos clave

- `funciones.py`: contiene todas las funciones auxiliares necesarias para el preprocesado, entrenamiento y predicción.
- `train.pkl`: datos históricos para reentrenar el modelo (**debe estar aquí**).
- `DatosParaProduccion.csv`: datos para los que se quieren obtener predicciones (**debe estar aquí**).
- `predicciones.csv`: archivo de salida con las predicciones generadas.
- `lista_modelos_retail.pkl`, `ohe_retail.pkl`, `te_retail.pkl`: artefactos generados automáticamente.

## 4. Secuencia típica de uso

1. Coloca `train.pkl` y `DatosParaProduccion.csv` en esta carpeta.
2. Ejecuta `reentrenamiento.py` para crear/actualizar los modelos y encoders.
3. Ejecuta `ejecucion.py` para generar el archivo `predicciones.csv`.

---

**Nota:** No es necesario modificar rutas ni mover archivos fuera de esta carpeta. Todo el proceso es autocontenido.
