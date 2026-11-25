
# Diccionario de datos

## 1. Objetivo

Este documento describe los campos y valores almacenados en la base de datos SQLite del proyecto ScraperPEN.

Su finalidad es establecer un vocabulario común para interpretar los datos, facilitar su mantenimiento y servir de referencia para futuros procesos de análisis.

La base de datos contiene cuatro tablas:

- `codigos_postales`
- `datos_crudos`
- `datos_resumen`
- `log_descargas`

## 2. Convenciones generales

- Los códigos postales se almacenan como texto (`TEXT`).
- Las fechas se almacenan como texto (`TEXT`).
- Los periodos estadísticos se normalizan al formato `AAAA-MM`.
- Los nombres de las métricas se almacenan mediante identificadores normalizados.
- Los valores estadísticos se almacenan como valores numéricos (`NUMERIC`).
- Los campos sujetos a claves foráneas deben corresponder a códigos postales existentes en el catálogo.

## 3. Tabla `codigos_postales`

Contiene el catálogo maestro de códigos postales del proyecto.

| Campo         | Tipo | Obligatorio | Descripción                                |
| ------------- | ---- | ----------- | ------------------------------------------- |
| `cp`        | TEXT | Sí         | Código postal. Clave primaria de la tabla. |
| `municipio` | TEXT | Sí         | Municipio asociado al código postal.       |

### Reglas

- `cp` es la clave primaria.
- `municipio` no puede ser nulo.
- El código postal se almacena como texto para conservar su formato.

## 4. Tabla `datos_crudos`

Contiene las observaciones estadísticas inmobiliarias obtenidas para cada código postal.

| Campo              | Tipo    | Obligatorio | Descripción                                      |
| ------------------ | ------- | ----------- | ------------------------------------------------- |
| `fecha_consulta` | TEXT    | Sí         | Fecha en la que se obtuvo la información.        |
| `cp`             | TEXT    | Sí         | Código postal al que pertenece la observación.  |
| `metrica`        | TEXT    | Sí         | Identificador de la métrica estadística.        |
| `periodo`        | TEXT    | Sí         | Periodo estadístico al que corresponde el valor. |
| `valor`          | NUMERIC | No          | Valor numérico de la observación.               |

### 4.1. `fecha_consulta`

Fecha en la que se obtuvo la observación desde el portal.

Formato normalizado:

```text
AAAA-MM-DD
```

Ejemplo:

```text
2026-11-24
```

`DatabaseManager.py` admite como entrada los siguientes formatos:

- `AAAA-MM-DD`
- `AAAAMMDD`
- `AAAA-MM-DD HH:MM:SS`
- `DD/MM/AAAA`

La fecha se normaliza antes de almacenar el registro.

### 4.2. `cp`

Código postal al que corresponde la observación.

Debe existir previamente en `codigos_postales`.

Es una clave foránea que referencia:

```text
codigos_postales.cp
```

### 4.3. `metrica`

Identifica el indicador inmobiliario al que corresponde el valor.

Los identificadores admitidos son:

| Identificador     | Nombre descriptivo        | Unidad o interpretación          |
| ----------------- | ------------------------- | --------------------------------- |
| `precio_m2`     | Precio por metro cuadrado | Euros por metro cuadrado (€/m²) |
| `compraventas`  | Compraventas              | Número de compraventas           |
| `importe_medio` | Importe medio             | Euros (€)                        |

`DatabaseManager.py` normaliza distintas denominaciones de entrada para almacenarlas mediante estos identificadores.

La base de datos restringe los valores de esta columna a los tres identificadores anteriores.

### 4.4. `periodo`

Periodo estadístico al que corresponde la observación.

Formato normalizado:

```text
AAAA-MM
```

Ejemplo:

```text
2025-03
```

`DatabaseManager.py` reconoce distintas representaciones de entrada, entre ellas:

- `2025-3`
- `3/2025`
- `03-2025`
- `marzo 2025`
- `mar 2025`

Todas se normalizan al formato `2025-03`.

El periodo representa el momento al que corresponde el dato estadístico, no la fecha en la que se realizó la consulta.

### 4.5. `valor`

Valor numérico de la métrica para el código postal y periodo correspondientes.

Puede contener:

- Números enteros.
- Números decimales.
- `NULL`, cuando el valor recibido no está disponible o se representa mediante determinados marcadores vacíos.

`DatabaseManager.py` normaliza valores numéricos que llegan como texto, incluyendo formatos con separadores decimales y de millares.

## 5. Clave única de `datos_crudos`

La combinación de estos tres campos identifica una observación:

```text
cp + periodo + metrica
```

No pueden existir dos registros con la misma combinación.

Por ejemplo, para el CP `29001`, el periodo `2025-03` y la métrica `precio_m2` solo puede existir una observación.

Cuando se recibe una nueva consulta para esa misma combinación, se actualiza el registro existente si cambia el valor.

## 6. Tabla `datos_resumen`

Contiene una representación transformada de `datos_crudos`, con una fila por código postal y periodo. La columna `metrica` deja de existir en esta tabla porque sus tres valores posibles se convierten en columnas.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `cp` | TEXT | Sí | Código postal; parte de la clave primaria compuesta y clave foránea a `codigos_postales.cp` |
| `periodo` | TEXT | Sí | Periodo estadístico (`AAAA-MM`); parte de la clave primaria compuesta |
| `precio_m2` | NUMERIC | No | Precio por metro cuadrado |
| `compraventas` | NUMERIC | No | Número de compraventas |
| `importe_medio` | NUMERIC | No | Importe medio en euros |

### Clave primaria y relación

La clave primaria compuesta es `(cp, periodo)`. La columna `cp` referencia `codigos_postales(cp)`.

### Transformación

`src/ProcessData.py` lee `cp`, `periodo`, `metrica` y `valor` de `datos_crudos`, pivota las métricas y guarda el resultado en `datos_resumen` mediante UPSERT.

La correspondencia es:

| `metrica` en `datos_crudos` | Columna en `datos_resumen` |
|---|---|
| `precio_m2` | `precio_m2` |
| `compraventas` | `compraventas` |
| `importe_medio` | `importe_medio` |

Cuando una métrica no tiene valor para un periodo, la columna correspondiente queda como `NULL`. Los `NULL` no se sustituyen por cero: indican que el valor no está disponible.

`datos_resumen` es una tabla derivada. `datos_crudos` sigue siendo la fuente original y no se modifica durante el proceso.

## 7. Tabla `log_descargas`

Registra los intentos de consulta realizados por el scraper.

| Campo              | Tipo    | Obligatorio | Descripción                               |
| ------------------ | ------- | ----------- | ------------------------------------------ |
| `id`             | INTEGER | Sí         | Identificador único del intento.          |
| `fecha_descarga` | TEXT    | Sí         | Fecha y hora del intento de consulta.      |
| `cp`             | TEXT    | Sí         | Código postal consultado.                 |
| `estado`         | TEXT    | Sí         | Resultado de la consulta.                  |
| `valido`         | INTEGER | No          | Indicador de validez de los datos.         |
| `observaciones`  | TEXT    | No          | Información adicional sobre el resultado. |

### 6.1. `id`

Identificador del registro de consulta.

Es la clave primaria de `log_descargas`.

SQLite genera el identificador al insertar cada nuevo intento.

### 6.2. `fecha_descarga`

Fecha y hora en la que se registra el intento de consulta.

Formato utilizado por `DatabaseManager.py` cuando genera automáticamente la fecha:

```text
AAAA-MM-DD HH:MM:SS
```

Ejemplo:

```text
2026-11-24 17:30:00
```

### 6.3. `cp`

Código postal que se ha intentado consultar.

Debe existir en `codigos_postales`.

### 6.4. `estado`

Indica el resultado del intento de consulta.

Valores admitidos:

| Valor            | Significado                                                                                        |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| `completada`   | Consulta realizada correctamente con datos propios del código postal.                             |
| `sin_datos_cp` | El portal muestra datos provinciales en sustitución de los datos específicos del código postal. |
| `error`        | Se ha producido un error técnico durante la consulta o descarga.                                  |

### 6.5. `valido`

Indica si los datos obtenidos corresponden realmente al código postal consultado.

Valores:

| Valor    | Significado                                                                 |
| -------- | --------------------------------------------------------------------------- |
| `1`    | Datos propios del código postal.                                           |
| `0`    | Datos provinciales, no válidos como datos específicos del código postal. |
| `NULL` | Error técnico; no se ha podido determinar la validez.                      |

La correspondencia entre `estado` y `valido` es:

| `estado`       | `valido` |
| ---------------- | ---------- |
| `completada`   | `1`      |
| `sin_datos_cp` | `0`      |
| `error`        | `NULL`   |

### 6.6. `observaciones`

Campo de texto opcional para conservar información adicional.

Puede contener el mensaje mostrado por el portal o una descripción del error producido durante la consulta.

## 8. Catálogo de métricas

Las tres métricas almacenadas en `datos_crudos` son:

| Métrica                  | Identificador     | Unidad                 |
| ------------------------- | ----------------- | ---------------------- |
| Precio por metro cuadrado | `precio_m2`     | €/m²                 |
| Compraventas              | `compraventas`  | Número de operaciones |
| Importe medio             | `importe_medio` | €                     |

Los nombres descriptivos facilitan la interpretación de los datos, mientras que los identificadores normalizados permiten mantener una estructura homogénea en SQLite.

## 9. Diferencia entre fecha de consulta y periodo estadístico

Es importante distinguir estos dos conceptos:

- `fecha_consulta`: indica cuándo se obtuvo la información del portal.
- `periodo`: indica a qué periodo estadístico corresponde la observación.

Por ejemplo, una consulta realizada el 24 de noviembre de 2026 puede recuperar datos correspondientes a marzo de 2025.

En ese caso:

```text
fecha_consulta = 2026-11-24
periodo        = 2025-03
```

Ambos campos cumplen funciones diferentes y no deben confundirse.

## 10. Reglas de interpretación

Para trabajar correctamente con los datos se deben respetar las siguientes reglas:

1. Cada observación pertenece a un único código postal.
2. Cada observación corresponde a una única métrica y periodo.
3. Las métricas deben interpretarse utilizando sus unidades correspondientes.
4. Los valores de `datos_crudos` deben corresponder a datos propios del código postal.
5. Los resultados provinciales sustitutorios se registran en `log_descargas`, no como observaciones específicas del CP.
6. Los errores técnicos se registran con `estado = error` y `valido = NULL`.
7. La fecha de consulta no sustituye al periodo estadístico.
8. Los registros de `log_descargas` representan intentos individuales y no deben interpretarse como observaciones estadísticas.

## 11. Consideraciones para futuros análisis

Al preparar consultas, informes o modelos estadísticos:

- Utilizar `cp` para identificar el ámbito geográfico.
- Utilizar `periodo` para ordenar y comparar la evolución temporal.
- Utilizar `metrica` para seleccionar el indicador.
- Utilizar `valor` como dato cuantitativo en `datos_crudos`.
- Utilizar las columnas de métricas de `datos_resumen` para análisis en formato ancho.
- Utilizar `fecha_consulta` para conocer cuándo se obtuvo la información.
- Consultar `log_descargas` para analizar la disponibilidad y el resultado de las consultas.

Este diccionario debe actualizarse si se incorporan nuevas métricas, campos, estados o cambios en las reglas de almacenamiento.

---

**Documento de referencia:** significado y estructura de los campos de la base de datos del proyecto ScraperPEN.
