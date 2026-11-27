# Decisiones técnicas

Este documento resume las decisiones de diseño que explican cómo funciona la versión actual de ScraperPEN. Las decisiones antiguas que quedaron sustituidas se resumen aquí para que una persona que llegue al repositorio pueda entender el modelo vigente sin recorrer todo el historial de desarrollo.

## DEC-001. Python y Playwright para la extracción

El acceso al portal se automatiza con Playwright desde Python. La lógica principal de navegación y extracción se mantiene en `src/ScraperPEN.py`.

## DEC-002. SQLite como almacenamiento principal

SQLite conserva el catálogo, las observaciones, los datos resumidos y el historial de consultas. La base de trabajo se encuentra en `data/database/inmobiliario.db`.

## DEC-003. Separar observaciones e intentos

`datos_crudos` almacena valores estadísticos. `log_descargas` registra los intentos y sus resultados. Un intento puede existir aunque no genere una observación.

## DEC-004. Identificar ubicaciones con `(municipio, cp)`

La clave territorial es compuesta porque el código postal no debe tratarse como identificador aislado. Las claves de observaciones, resúmenes y logs referencian el catálogo mediante `(municipio, cp)`.

## DEC-005. Diferenciar el ámbito provincial

La provincia se representa como `Málaga / Todos`, con `tipo_ambito = 'provincia'`. Se consulta directamente en el portal; no se calcula agregando los códigos postales.

## DEC-006. No atribuir datos provinciales a un CP

Cuando una consulta de CP muestra datos provinciales sustitutorios, se registra `sin_datos_cp`. Esos valores no se guardan como observaciones propias del código postal.

## DEC-007. Mantener las observaciones únicas

La combinación `(municipio, cp, periodo, metrica)` identifica una observación de `datos_crudos`. Las nuevas consultas actualizan el valor existente cuando corresponde mediante UPSERT.

## DEC-008. Mantener una tabla resumida

`ProcessData.py` transforma el formato largo de `datos_crudos` al formato ancho de `datos_resumen`, con una fila por `(municipio, cp, periodo)` y tres columnas de métricas. Los valores ausentes permanecen como `NULL`.

## DEC-009. Separar la exportación web

`ExportWebData.py` obtiene los datos de `datos_resumen`, incorpora `tipo_ambito` y genera `web/data/datos_resumen.json`. El dashboard consume el JSON y no accede directamente a SQLite.

## DEC-010. Asignación fija de cuentas y control de cuota

El catálogo tiene 161 ubicaciones distribuidas entre cuatro cuentas: 45, 45, 45 y 26. Cada cuenta tiene un máximo configurado de 45 consultas enviadas por mes natural. La asignación no se recalcula durante una ejecución.

Solo cuenta como consulta enviada un registro de `log_descargas` con `consulta_enviada = 1`. Este indicador se activa al pulsar «Más estadísticas».

## DEC-011. Dos modos de ejecución

- El modo individual recibe una o varias claves `clave_portal` y permite solicitar expresamente una ubicación.
- El modo general se activa con `PEN_EJECUTAR_TODOS_CP=1`; prioriza errores técnicos y ubicaciones no consultadas, y omite las que ya terminaron `completada` o `sin_datos_cp`.

Ambos modos respetan la asignación fija y la cuota disponible.

## DEC-012. Mantener el histórico

Las observaciones y los intentos se conservan. Las transformaciones reconstruyen `datos_resumen` a partir de `datos_crudos`, sin alterar la tabla de observaciones original.

## DEC-013. Mantener responsabilidades separadas

- `ScraperPEN.py`: consulta y extracción.
- `DatabaseManager.py`: acceso y persistencia SQLite.
- `CreateDatabase.py`: definición del esquema.
- `ProcessData.py`: transformación.
- `ExportWebData.py`: exportación para la web.
- `web/`: presentación y visualización.

## Actualización de este documento

Cuando cambie una regla estructural, se debe actualizar la decisión correspondiente y revisar los documentos de arquitectura, base de datos, diccionario de datos y operaciones.
