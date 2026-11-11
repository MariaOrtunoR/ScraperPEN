# Proyecto PEN — Seguimiento

**Última actualización:** 8 de noviembre de 2026  
**Estado general:** histórico válido conservado; registro de descargas y base de extracción preparados; prueba real con un CP pendiente.

## 1. Objetivo

Descargar las estadísticas inmobiliarias del **Portal Estadístico del Notariado** para los códigos postales de la provincia de Málaga y centralizarlas en SQLite.

El proyecto debe permitir:

- Descargar Excel y PDF mediante Playwright.
- Conservar los archivos originales.
- Guardar los datos normalizados en SQLite.
- Actualizar datos históricos sin duplicar registros.
- Preparar los datos para análisis y un futuro dashboard.

## 2. Estructura del proyecto

```text
ScraperPEN/
├── data/
│   ├── database/
│   │   ├── inmobiliario.db
│   │   ├── inmobiliario_backup.db
│   │   └── copias_de_seguridad...
│   ├── processed/
│   │   └── resultado.xlsx
│   └── raw/
│       ├── descargas_excel/
│       └── descargas_pdf/
├── resources/
│   ├── CodigosPostalesMalaga.xlsx
│   ├── evolucionpreciovivienda.xlsx
│   ├── MALAGA.geojson
│   └── Metodologia PIN CTNotariado.pdf
├── src/
│   ├── CreateDatabase.py
│   ├── DatabaseManager.py
│   ├── ImportarHistoricoExcel.py
│   ├── ScraperPEN.py
│   └── TransformData.py
├── aplicar_cambios_sql_unico.py
├── comprobar_excel.py
├── requirements.txt
├── .gitignore
└── SEGUIMIENTO_PROYECTO.md
```

> La estructura refleja los archivos documentados. Comprueba el Explorador de VS Code si has movido o renombrado alguno.

## 3. Estado actual

### 3.1. Entorno y base de datos

- [x] Python y SQLite comprobados.
- [x] Base de datos SQLite creada.
- [x] Estructura principal del proyecto organizada.
- [x] Declaradas las dependencias en `requirements.txt`.
- [x] Configurado `.gitignore` para Python, credenciales locales y datos regenerables.

### 3.2. Datos históricos

Se importaron los Excel históricos desde `data/raw/descargas_excel/`.

| Comprobación | Resultado |
|---|---:|
| Archivos Excel procesados | 157 |
| Filas leídas de los Excel | 5.686 |
| Registros importados antes de la migración | 5.652 |
| Registros actuales válidos en `datos_crudos` | 2.088 |
| Códigos postales con registros antes de la migración | 157 |
| Registros actuales de cada métrica | 696 |
| Periodo más antiguo | `2025-06` |
| Periodo más reciente | `2026-05` |
| Errores reportados por el importador | 0 |

Los 5.686 datos leídos no equivalían necesariamente a 5.686 filas finales: la base evita duplicados mediante una clave única. Posteriormente se retiraron de la tabla operativa las observaciones clasificadas como no válidas.

También se comprobó que había 5.652 combinaciones históricas únicas de código postal, periodo y métrica antes de la migración de calidad.

### 3.3. Calidad de los datos

Durante la carga histórica se clasificaron 99 CP como no válidos para el análisis por código postal y se estableció `valor = NULL` para `precio_m2` del CP `29492`. Esa clasificación fue una regla estática de calidad, no un registro de respuesta del portal.

**Migración realizada el 08/11/2026:** se creó una copia de seguridad en `data/database/inmobiliario_backup_antes_migracion_validez_20261108_102632.db`, se eliminaron los 3.564 registros con `valido = 0` y se retiró la columna `valido` de `datos_crudos`. Permanecen 2.088 observaciones válidas. No se añadieron entradas históricas a `log_descargas`: la clasificación anterior era estática y no prueba una consulta concreta al portal.

### 3.4. Catálogo de códigos postales y relación entre tablas

Se revisó `resources/CodigosPostalesMalaga.xlsx` y se ejecutaron consultas de validación en SQLite.

| Comprobación | Resultado |
|---|---:|
| Códigos del catálogo | 160 |
| Códigos duplicados en `codigos_postales` | 0 |
| Códigos de `datos_crudos` sin correspondencia en el catálogo | 0 |
| Códigos distintos presentes antes de la migración | 157 |
| Códigos distintos presentes actualmente | 58 |

Estas comprobaciones demuestran que los códigos presentes en `datos_crudos` tienen correspondencia en el catálogo y que el catálogo no contiene duplicados. **No demuestran por sí solas que los 160 códigos sean la lista oficial completa y vigente de la provincia de Málaga**; esa cobertura aún debe contrastarse con una fuente postal de referencia.

La relación de SQLite se comprobó mediante:

```sql
PRAGMA foreign_key_list(datos_crudos);
```

El resultado confirmó esta relación:

- Tabla padre: `codigos_postales`.
- Clave primaria: `codigos_postales.cp`.
- Tabla hija: `datos_crudos`.
- Clave foránea: `datos_crudos.cp`.
- Cardinalidad: `1:N` (un código postal puede tener muchos registros históricos).

La consulta:

```sql
PRAGMA foreign_key_list(codigos_postales);
```

devolvió `No Results`, que es lo esperado: el catálogo es la tabla padre y no necesita una clave foránea hacia `datos_crudos`.

También se comprobó que no hay códigos huérfanos ni duplicados en el catálogo.

**Importante para Python:** SQLite requiere activar las claves foráneas en cada conexión mediante `PRAGMA foreign_keys = ON`. Hay que revisar `DatabaseManager.py` y confirmar que lo hace antes de ejecutar operaciones.

### 3.5. Scraper Playwright

La integración con SQLite está iniciada, pero todavía falta validar el proceso completo.

- [x] `DatabaseManager.py` activa `PRAGMA foreign_keys = ON` y valida el esquema antes de guardar.
- [x] Creada `log_descargas`, con estados `completada`, `sin_datos_cp` y `error`.
- [x] Las rutas de PDF y Excel se anclan a `data/raw/` desde la raíz del proyecto.
- [x] Las credenciales se leen desde `PEN_USER_EMAIL` y `PEN_USER_PASSWORD`.
- [x] El catálogo se lee de `codigos_postales`; el modo por defecto consulta sólo `29710` y `PEN_EJECUTAR_TODOS_CP=1` habilita los 160 CP.
- [x] El scraper no se ejecuta al importarse como módulo.
- [ ] Validar en el portal el selector y el patrón que detecta el mensaje de datos provinciales.
- [ ] Probar con un único código postal.
- [ ] Comprobar los archivos descargados y los datos guardados en SQLite.
- [ ] Ejecutar la descarga completa solo después de superar la prueba individual.

**Modo de ejecución:** `29710` es deliberadamente el CP de prueba por defecto. La ejecución masiva queda bloqueada hasta superar la prueba individual y sólo se habilita con `PEN_EJECUTAR_TODOS_CP=1`.

### 3.6. Transformación y dashboard

- [ ] Revisar `src/TransformData.py`.
- [ ] Definir las transformaciones necesarias.
- [ ] Confirmar el diseño de la tabla `datos_resumen`.
- [ ] Preparar los datos para el dashboard.

## 4. Modelo de datos actual

### `codigos_postales` — catálogo maestro

Contiene un registro por código postal. `cp` es la clave primaria.

### `datos_crudos` — observaciones inmobiliarias

Contiene los datos históricos. `cp` es una clave foránea que referencia a `codigos_postales.cp`.

Relación:

```text
codigos_postales (1)
    cp — PK
       |
       | 1:N
       v
datos_crudos (N)
    cp — FK
```

Campos documentados de `datos_crudos`:

| Campo | Uso |
|---|---|
| `fecha_consulta` | Fecha en que se consultó el portal (`YYYY-MM-DD`) |
| `cp` | Código postal, guardado como texto |
| `metrica` | `precio_m2`, `compraventas` o `importe_medio` |
| `periodo` | Mes al que corresponde el dato (`YYYY-MM`) |
| `valor` | Valor numérico; puede ser `NULL` |
| *(eliminado)* `valido` | La validez se registra ahora por consulta en `log_descargas`. |

La combinación `(cp, periodo, metrica)` debe ser única. Si el portal corrige un valor histórico, se actualizan `valor` y `fecha_consulta`. Si el valor no cambia, no hace falta modificar el registro.

### `log_descargas` — auditoría de consultas

Registra cada intento sin deduplicarlo: `fecha_descarga`, `cp`, `estado`, `valido` y `observaciones`. Los estados son `completada` (`valido = 1`), `sin_datos_cp` (`valido = 0`) y `error` (`valido = NULL`).

La tabla `datos_resumen` está prevista para la segunda fase de transformación y Power BI; su diseño queda pendiente.

## 5. Siguiente paso recomendado

**El siguiente paso debe ser revisar `src/DatabaseManager.py` y `src/ScraperPEN.py` antes de ejecutar el scraper.**

Orden de trabajo:

1. Configurar `PEN_USER_EMAIL` y `PEN_USER_PASSWORD` en el entorno local.
2. Ejecutar una prueba controlada con el CP `29710`.
3. Confirmar en la página real los selectores y el texto de datos provinciales.
5. Verificar que se descargan los archivos y que los datos se insertan o actualizan correctamente en SQLite.
6. Solo entonces lanzar la descarga completa de Málaga.

No ejecutar todavía una descarga masiva hasta superar la prueba individual.

## 6. Mantenimiento y seguridad

- [ ] Completar `requirements.txt` con las dependencias que realmente utiliza el proyecto.
- [ ] Configurar `.gitignore` para excluir `__pycache__/`, archivos temporales, bases de datos locales y credenciales según la política de copias del proyecto.
- [ ] No guardar contraseñas reales directamente en el código; usar variables de entorno o configuración local protegida.
- [ ] Conservar la base de datos original como copia de seguridad hasta validar la nueva.
- [ ] Documentar cómo restaurar una copia de seguridad.
- [ ] Revisar antes de borrar o mover otros scripts.

## 7. Historial breve

| Fecha | Avance |
|---|---|
| 24/10/2026 | Entorno Python/SQLite comprobado y estructura inicial organizada. |
| 25/10/2026 | Diseño de `datos_crudos`, normalización e importación de 157 Excel históricos. |
| 25/10/2026 | Comprobación de 5.652 registros únicos en SQLite. |
| 25/10/2026 | Integración inicial de guardado en SQLite desde el scraper; falta la prueba completa. |
| 25/10/2026 | Preparación de reglas de calidad para `valido` y el CP `29492`. |
| 07/11/2026 | Comprobaciones del catálogo: 160 códigos, sin duplicados; no hay códigos de `datos_crudos` sin correspondencia. |
| 07/11/2026 | Confirmada la FK `datos_crudos.cp` → `codigos_postales.cp` y la relación 1:N. |
| 08/11/2026 | Creado `log_descargas`; activadas las FK por conexión; migrados y eliminados los registros históricos no válidos con copia de seguridad. |

---

**Resumen:** los datos históricos están importados, el catálogo y las correspondencias internas se han validado, y la relación entre las tablas está definida en la dirección correcta. El siguiente objetivo es revisar la activación de claves foráneas en Python y validar el scraper con un único código postal antes de descargar toda la provincia.
