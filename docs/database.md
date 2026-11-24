
# Base de datos SQLite

## 1. Objetivo

El proyecto ScraperPEN utiliza SQLite para almacenar las estadísticas inmobiliarias obtenidas del Portal Estadístico del Notariado.

La base de datos permite:

- Mantener un catálogo de códigos postales de la provincia de Málaga.
- Almacenar las estadísticas inmobiliarias por código postal y periodo.
- Registrar los intentos de consulta y el resultado de cada descarga.
- Actualizar los datos existentes sin generar duplicados.
- Mantener la integridad de las relaciones entre tablas.

## 2. Ubicación

La base de datos principal se encuentra en:

```text
data/database/inmobiliario.db
```

La ruta se define en `DatabaseManager.py` a partir de la ubicación del proyecto, por lo que no depende del directorio desde el que se ejecute el programa.

## 3. Estructura general

La base de datos contiene tres tablas principales:

1. `codigos_postales`
2. `datos_crudos`
3. `log_descargas`

Sus relaciones son las siguientes:

```text
codigos_postales
       |
       | 1
       |
       | N
datos_crudos

codigos_postales
       |
       | 1
       |
       | N
log_descargas
```

Cada código postal puede tener múltiples observaciones estadísticas y múltiples registros de consulta.

## 4. Tabla `codigos_postales`

Contiene el catálogo maestro de códigos postales incluidos en el proyecto.

| Campo         | Tipo | Restricciones | Descripción               |
| ------------- | ---- | ------------- | -------------------------- |
| `cp`        | TEXT | PRIMARY KEY   | Código postal             |
| `municipio` | TEXT | NOT NULL      | Municipio al que pertenece |

El código postal se almacena como texto para conservar su formato.

Esta tabla es la referencia para las demás tablas. Los códigos postales deben existir en ella antes de almacenar observaciones o registrar consultas.

El catálogo se mantiene como referencia de los códigos postales que se procesan en el proyecto.

## 5. Tabla `datos_crudos`

Almacena las observaciones estadísticas inmobiliarias obtenidas para cada código postal.

| Campo              | Tipo    | Restricciones         | Descripción                                 |
| ------------------ | ------- | --------------------- | -------------------------------------------- |
| `fecha_consulta` | TEXT    | NOT NULL              | Fecha en la que se obtuvo la información    |
| `cp`             | TEXT    | NOT NULL, FOREIGN KEY | Código postal al que corresponden los datos |
| `metrica`        | TEXT    | NOT NULL, CHECK       | Tipo de indicador estadístico               |
| `periodo`        | TEXT    | NOT NULL              | Periodo temporal de la observación          |
| `valor`          | NUMERIC | —                    | Valor de la métrica                         |

### 5.1. Métricas admitidas

La columna `metrica` admite únicamente estos valores:

- `precio_m2`: precio por metro cuadrado.
- `compraventas`: número de compraventas.
- `importe_medio`: importe medio en euros.

La restricción `CHECK` impide almacenar métricas distintas de las admitidas.

### 5.2. Clave única

La tabla tiene una restricción de unicidad sobre:

```text
(cp, periodo, metrica)
```

Esto significa que no puede existir más de una observación para la misma combinación de código postal, periodo y métrica.

La fecha de consulta no forma parte de esta clave.

### 5.3. Actualización de registros

`DatabaseManager.py` utiliza una operación UPSERT.

Su comportamiento es:

- Si la combinación de código postal, periodo y métrica no existe, inserta un registro.
- Si ya existe, actualiza la fecha de consulta y el valor cuando el valor recibido es diferente.
- Si el valor no ha cambiado, no realiza una actualización innecesaria.

De esta manera, las nuevas consultas permiten mantener actualizada la información sin duplicar observaciones.

### 5.4. Datos válidos

La tabla `datos_crudos` debe contener exclusivamente observaciones correspondientes a datos propios del código postal.

Cuando el portal muestra datos provinciales en sustitución de los datos específicos de un código postal, esos valores no deben incorporarse como si pertenecieran a dicho código postal.

La validez de cada consulta se registra en `log_descargas`.

## 6. Tabla `log_descargas`

Registra los intentos de consulta realizados por el scraper.

A diferencia de `datos_crudos`, esta tabla conserva el historial de las consultas. No se deduplican los intentos.

| Campo              | Tipo    | Restricciones         | Descripción                                |
| ------------------ | ------- | --------------------- | ------------------------------------------- |
| `id`             | INTEGER | PRIMARY KEY           | Identificador del registro                  |
| `fecha_descarga` | TEXT    | NOT NULL              | Fecha y hora del intento                    |
| `cp`             | TEXT    | NOT NULL, FOREIGN KEY | Código postal consultado                   |
| `estado`         | TEXT    | NOT NULL, CHECK       | Resultado de la consulta                    |
| `valido`         | INTEGER | CHECK                 | Indicador de validez                        |
| `observaciones`  | TEXT    | —                    | Mensaje del portal o descripción del error |

### 6.1. Estados posibles

La columna `estado` admite tres valores:

| Estado           | Significado                                                        | `valido` |
| ---------------- | ------------------------------------------------------------------ | ---------- |
| `completada`   | Consulta realizada correctamente y con datos propios del CP        | 1          |
| `sin_datos_cp` | El portal muestra datos provinciales en sustitución de los del CP | 0          |
| `error`        | Se ha producido un error técnico durante la consulta o descarga   | NULL       |

La relación entre `estado` y `valido` también se comprueba desde `DatabaseManager.py` antes de insertar el registro.

### 6.2. Observaciones

El campo `observaciones` permite conservar información adicional sobre el resultado de la consulta.

Puede incluir, por ejemplo:

- Mensajes mostrados por el portal.
- Descripciones de errores técnicos.
- Información útil para revisar una incidencia.

### 6.3. Índice

La tabla dispone del índice:

```text
idx_log_descargas_cp_fecha
```

Se crea sobre las columnas:

```text
(cp, fecha_descarga)
```

Facilita las consultas del historial de descargas filtradas por código postal y fecha.

## 7. Relaciones e integridad referencial

Las tablas `datos_crudos` y `log_descargas` contienen una clave foránea hacia:

```text
codigos_postales(cp)
```

Esto impide registrar observaciones o intentos de consulta para códigos postales que no estén incluidos en el catálogo.

`DatabaseManager.py` activa la integridad referencial en cada conexión mediante:

```sql
PRAGMA foreign_keys = ON;
```

Esta instrucción debe mantenerse activa en todas las conexiones utilizadas por el proyecto.

## 8. Módulos que gestionan la base de datos

### `CreateDatabase.py`

Responsable de inicializar el esquema de la base de datos.

Crea las tablas y el índice mediante `CREATE TABLE IF NOT EXISTS` y `CREATE INDEX IF NOT EXISTS`.

No importa automáticamente el catálogo de códigos postales ni modifica las tablas que ya existen.

### `DatabaseManager.py`

Centraliza las operaciones de acceso y almacenamiento.

Sus principales responsabilidades son:

- Definir la ruta de la base de datos.
- Abrir conexiones con las claves foráneas activadas.
- Validar el esquema principal.
- Normalizar fechas, periodos, métricas y valores.
- Guardar o actualizar observaciones.
- Registrar los intentos de descarga.
- Recuperar el catálogo de códigos postales.

## 9. Reglas de mantenimiento

Cualquier modificación futura de la base de datos debe respetar estas reglas:

1. No eliminar registros históricos sin una decisión expresa.
2. No introducir códigos postales que no estén en el catálogo maestro.
3. Mantener la unicidad de `(cp, periodo, metrica)`.
4. Conservar las tres métricas admitidas, salvo que se apruebe una modificación del modelo.
5. No almacenar datos provinciales como si fueran datos específicos de un código postal.
6. Registrar los intentos de consulta en `log_descargas`.
7. Mantener activadas las claves foráneas.
8. Realizar una copia de seguridad antes de cualquier modificación estructural.
9. Comprobar la integridad de SQLite después de las operaciones de mantenimiento.

## 10. Comprobaciones de integridad

SQLite permite realizar comprobaciones mediante las siguientes instrucciones:

```sql
PRAGMA integrity_check;
```

Comprueba la integridad interna de la base de datos.

```sql
PRAGMA foreign_key_check;
```

Comprueba que no existan incumplimientos de las claves foráneas.

Para revisar las tablas existentes:

```sql
SELECT name
FROM sqlite_master
WHERE type = 'table';
```

Para consultar el número de registros de cada tabla:

```sql
SELECT COUNT(*) FROM codigos_postales;
SELECT COUNT(*) FROM datos_crudos;
SELECT COUNT(*) FROM log_descargas;
```

Los recuentos pueden variar a medida que se incorporen nuevos datos y se ejecuten nuevas consultas.

## 11. Copias de seguridad

Antes de realizar cambios en el esquema o tareas de mantenimiento que puedan afectar a los datos, debe crearse una copia de seguridad de:

```text
data/database/inmobiliario.db
```

La copia debe conservarse separada de la base de datos activa.

No se deben sustituir los datos originales hasta haber comprobado que la operación se ha realizado correctamente.

---

**Documento de referencia:** estructura y reglas de almacenamiento de SQLite del proyecto ScraperPEN.
