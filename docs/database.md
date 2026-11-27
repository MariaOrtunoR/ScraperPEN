# Base de datos SQLite

ScraperPEN utiliza SQLite como almacenamiento principal. La base de datos conserva el catálogo de ubicaciones, las observaciones estadísticas, el resumen preparado para análisis y el historial de consultas.

## 1. Ubicación

El archivo de trabajo se encuentra en:

```text
data/database/inmobiliario.db
```

La base contiene cuatro tablas:

- `codigos_postales`
- `datos_crudos`
- `datos_resumen`
- `log_descargas`

## 2. Relaciones

La tabla `codigos_postales` es el catálogo maestro. Las otras tres tablas la referencian mediante la clave compuesta `(municipio, cp)`.

```text
                 codigos_postales
                  (municipio, cp)
                   /     |     \
                  /      |      \
                 v       v       v
          datos_crudos datos_resumen log_descargas
```

`DatabaseManager.py` activa `PRAGMA foreign_keys = ON` en cada conexión y comprueba que el esquema contiene las tablas, columnas y relaciones esperadas.

## 3. Tabla `codigos_postales`

Contiene una fila por ubicación del catálogo.

| Campo | Tipo | Descripción |
|---|---|---|
| `municipio` | TEXT | Municipio asociado a la ubicación. |
| `cp` | TEXT | Código postal guardado como texto; para provincia se utiliza `Todos`. |
| `tipo_ambito` | TEXT | `cp` o `provincia`. |
| `clave_portal` | TEXT | Texto utilizado para localizar la ubicación en el portal. |
| `cuenta_id` | TEXT | Cuenta interna asignada (`cuenta_1` a `cuenta_4`). |

Clave primaria: `(municipio, cp)`.

El catálogo de la base revisada contiene 160 códigos postales y una fila provincial: `Málaga / Todos`.

## 4. Tabla `datos_crudos`

Guarda las observaciones en formato largo: una fila por ubicación, periodo y métrica.

| Campo | Tipo | Descripción |
|---|---|---|
| `fecha_consulta` | TEXT | Fecha en la que se obtuvo la observación. |
| `municipio` | TEXT | Municipio de la ubicación. |
| `cp` | TEXT | Código postal o `Todos` para provincia. |
| `metrica` | TEXT | `precio_m2`, `compraventas` o `importe_medio`. |
| `periodo` | TEXT | Periodo estadístico en formato `AAAA-MM`. |
| `valor` | NUMERIC | Valor de la métrica; admite `NULL`. |

Restricciones:

- Clave foránea `(municipio, cp)` hacia `codigos_postales`.
- Unicidad `(municipio, cp, periodo, metrica)`.

Cuando se vuelve a consultar un periodo, el almacenamiento utiliza UPSERT para actualizar la observación existente en lugar de duplicarla. Solo se guardan datos correspondientes al ámbito consultado.

## 5. Tabla `datos_resumen`

Es una tabla derivada de `datos_crudos`, preparada para consultas y visualizaciones. Tiene una fila por ubicación y periodo.

| Campo | Tipo | Descripción |
|---|---|---|
| `municipio` | TEXT | Municipio de la ubicación. |
| `cp` | TEXT | Código postal o `Todos`. |
| `periodo` | TEXT | Periodo estadístico `AAAA-MM`. |
| `precio_m2` | NUMERIC | Precio por metro cuadrado. |
| `compraventas` | NUMERIC | Número de compraventas. |
| `importe_medio` | NUMERIC | Importe medio en euros. |

Clave primaria: `(municipio, cp, periodo)`.

Las tres columnas de métricas pueden contener `NULL` cuando el indicador no está disponible. `ProcessData.py` reconstruye esta tabla a partir de `datos_crudos`; no modifica la tabla original.

## 6. Tabla `log_descargas`

Registra cada intento de consulta, incluso cuando no se incorporan observaciones estadísticas.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER | Identificador del intento. |
| `fecha_descarga` | TEXT | Fecha y hora del intento. |
| `municipio` | TEXT | Municipio de la ubicación. |
| `cp` | TEXT | Código postal o `Todos`. |
| `cuenta_id` | TEXT | Cuenta utilizada; puede ser `NULL` en registros históricos sin atribución. |
| `estado` | TEXT | `completada`, `sin_datos_cp` o `error`. |
| `valido` | INTEGER | `1`, `0` o `NULL`, según el resultado. |
| `consulta_enviada` | INTEGER | `1` si se pulsó «Más estadísticas»; `0` si no. |
| `observaciones` | TEXT | Información adicional del resultado o del error. |

Interpretación de estados:

| Estado | `valido` | Significado |
|---|---:|---|
| `completada` | 1 | Consulta con datos propios de la ubicación. |
| `sin_datos_cp` | 0 | El portal mostró datos provinciales en lugar de datos propios del CP. |
| `error` | NULL | Se produjo un error durante el proceso. |

`consulta_enviada` permite distinguir los errores anteriores y posteriores al envío de la consulta. El consumo mensual se calcula contando los registros enviados por cuenta.

## 7. Reglas para interpretar la base

1. Identificar cada ubicación mediante `(municipio, cp)`, no solo mediante el CP.
2. Diferenciar `Málaga / Todos` de los códigos postales del municipio de Málaga.
3. No sumar ni promediar el dato provincial con los datos de CP.
4. No guardar datos provinciales sustitutorios como si fueran datos de un CP.
5. Diferenciar `fecha_consulta` de `periodo`: la primera indica cuándo se obtuvo el dato; el segundo, a qué mes corresponde.
6. Interpretar `NULL` como dato no disponible, no como cero.
7. Utilizar `log_descargas` para estudiar intentos; no es una tabla de estadísticas.

## 8. Comprobaciones de integridad

Estas consultas permiten revisar la base:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

La primera debe devolver `ok`. La segunda no debe devolver filas.
