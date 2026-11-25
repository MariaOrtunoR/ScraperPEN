
# Registro de decisiones del proyecto

## 1. Objetivo

Este documento recoge las principales decisiones de organización, arquitectura, almacenamiento y funcionamiento adoptadas durante el desarrollo de ScraperPEN.

Su finalidad es mantener un historial de referencia que permita conocer qué se ha decidido, por qué se ha decidido y qué criterios deben respetarse en futuras modificaciones.

Las decisiones aquí recogidas deben consultarse antes de plantear cambios que afecten a la estructura o al funcionamiento general del proyecto.

## 2. Decisiones sobre la estructura del proyecto

### DEC-001. Mantener `ScraperPEN.py` como un único módulo

**Decisión:** mantener toda la lógica del scraper en `src/ScraperPEN.py`, sin dividirlo en varios módulos.

**Motivo:** se ha decidido conservar una estructura sencilla y centralizada para el proceso de extracción.

**Consecuencia:** las futuras modificaciones del scraper deberán realizarse en ese archivo, salvo que se acuerde expresamente cambiar esta decisión.

### DEC-002. Mantener los módulos principales dentro de `src/` (sustituida parcialmente por DEC-028)

**Decisión original:** la carpeta `src/` contenía únicamente `ScraperPEN.py`, `CreateDatabase.py` y `DatabaseManager.py`.

**Motivo:** separar las responsabilidades principales sin fragmentar innecesariamente el código.

**Estado:** el límite de tres módulos ha sido sustituido por DEC-028. Se conserva el criterio de mantener una estructura sencilla y de no añadir módulos sin una decisión expresa.

### DEC-003. Eliminar los scripts de migración y transformación antiguos

**Decisión:** eliminar del proyecto los siguientes archivos:

- `MigrarValidezALog.py`
- `TransformData.py`

**Motivo:** se ha decidido simplificar la estructura y retirar esos scripts del conjunto de módulos activos.

**Consecuencia:** no se recuperan esos archivos antiguos. La creación posterior de `src/ProcessData.py` es un módulo nuevo, aprobado específicamente en la Fase 7, y no una recuperación del antiguo `TransformData.py`.

### DEC-004. Mantener `resources/` sin modificaciones

**Decisión:** conservar la carpeta `resources/` y su contenido actual.

**Motivo:** contiene archivos de referencia necesarios para el proyecto.

**Consecuencia:** no mover, renombrar ni eliminar sus archivos sin autorización expresa.

### DEC-005. Organizar las descargas por formato

**Decisión:** utilizar estas rutas:

```text
data/raw/excel/
data/raw/pdf/
```

**Motivo:** separar los archivos originales descargados según su formato.

**Consecuencia:** las nuevas descargas deben guardarse en las carpetas correspondientes.

### DEC-006. Crear una carpeta específica para pruebas

**Decisión:** incorporar `tests/` a la estructura del proyecto.

**Motivo:** disponer de un espacio separado para las futuras pruebas automatizadas y comprobaciones del código.

**Consecuencia:** las pruebas no deben mezclarse con los módulos de producción.

### DEC-007. Crear una carpeta de documentación técnica

**Decisión:** utilizar `docs/` para centralizar la documentación detallada del proyecto.

**Documentos previstos:**

- `architecture.md`
- `database.md`
- `data_dictionary.md`
- `decisions.md`
- `operations.md`

**Motivo:** separar la documentación técnica de los archivos principales del proyecto.

### DEC-008. No crear una carpeta `scripts/`

**Decisión:** no incorporar una carpeta independiente para scripts auxiliares.

**Motivo:** mantener la estructura acordada sin añadir directorios innecesarios.

## 3. Decisiones sobre la base de datos

### DEC-009. Utilizar SQLite como almacenamiento principal

**Decisión:** mantener SQLite como sistema de almacenamiento del proyecto.

**Motivo:** centralizar los datos extraídos en una base de datos local, sencilla de mantener y consultar.

**Consecuencia:** el archivo principal será:

```text
data/database/inmobiliario.db
```

### DEC-010. Mantener el catálogo maestro de códigos postales

**Decisión:** utilizar `codigos_postales` como catálogo de referencia.

**Motivo:** garantizar que las observaciones y consultas estén asociadas a códigos postales registrados.

**Consecuencia:** las tablas que contienen observaciones o intentos de consulta deben mantener su relación con este catálogo.

### DEC-011. Mantener la unicidad de las observaciones

**Decisión:** establecer como clave única de `datos_crudos` la combinación:

```text
(cp, periodo, metrica)
```

**Motivo:** evitar duplicados para una misma métrica, código postal y periodo.

**Consecuencia:** las nuevas consultas actualizarán los registros existentes cuando corresponda, en lugar de generar duplicados.

### DEC-012. Utilizar UPSERT para actualizar los datos

**Decisión:** utilizar operaciones UPSERT en el almacenamiento de observaciones.

**Motivo:** permitir incorporar nuevos periodos y actualizar valores históricos cuando el portal publique correcciones.

**Consecuencia:** los datos existentes se conservan y se actualizan cuando corresponde.

### DEC-013. Separar los datos estadísticos del historial de consultas

**Decisión:** mantener dos tablas con finalidades diferentes:

- `datos_crudos`: observaciones estadísticas.
- `log_descargas`: historial de intentos de consulta.

**Motivo:** evitar mezclar los valores estadísticos con la información sobre el resultado de las descargas.

**Consecuencia:** los intentos de consulta se registran individualmente, incluso cuando no generan observaciones estadísticas.

### DEC-014. Registrar la validez en `log_descargas`

**Decisión:** utilizar el campo `valido` de `log_descargas` para indicar si los datos obtenidos corresponden al código postal consultado.

**Motivo:** la validez debe estar asociada a cada consulta concreta, no ser una clasificación permanente del código postal.

**Valores establecidos:**

- `1`: datos propios del código postal.
- `0`: datos provinciales sustitutorios.
- `NULL`: error técnico.

**Consecuencia:** no se mantiene una columna `valido` en `datos_crudos`.

### DEC-015. No almacenar datos provinciales como datos de un código postal

**Decisión:** cuando el portal muestre datos provinciales en sustitución de los datos específicos del CP, no incorporar esos valores a `datos_crudos`.

**Motivo:** evitar atribuir a un código postal información que corresponde al ámbito provincial.

**Consecuencia:** el resultado se registra en `log_descargas` con:

```text
estado = sin_datos_cp
valido = 0
```

### DEC-016. Activar las claves foráneas en cada conexión

**Decisión:** activar `PRAGMA foreign_keys = ON` en cada conexión SQLite.

**Motivo:** mantener la integridad referencial entre las tablas.

**Consecuencia:** no deben introducirse registros asociados a códigos postales inexistentes en el catálogo.

### DEC-017. No borrar datos históricos automáticamente

**Decisión:** preservar los registros históricos y evitar operaciones destructivas sin autorización.

**Motivo:** los datos históricos constituyen la base para estudiar la evolución inmobiliaria.

**Consecuencia:** cualquier migración o modificación estructural debe contar con una copia de seguridad y una comprobación posterior.

## 4. Decisiones sobre el scraper

### DEC-018. Utilizar Playwright para la extracción

**Decisión:** mantener Playwright como herramienta de automatización del navegador.

**Motivo:** permitir la navegación por el Portal Estadístico del Notariado, la consulta de códigos postales y la descarga de documentos.

### DEC-019. Proteger las credenciales mediante variables de entorno

**Decisión:** no almacenar las credenciales reales en el código fuente.

Se utilizan las variables:

```text
PEN_USER_EMAIL
PEN_USER_PASSWORD
```

El proyecto utiliza `python-dotenv` para cargar la configuración local desde `.env`.

**Motivo:** separar la configuración sensible del código y evitar publicar credenciales.

### DEC-020. Mantener una ejecución de prueba por defecto

**Decisión:** el scraper debe utilizar un código postal de prueba por defecto, actualmente `29710`.

**Motivo:** permitir comprobar el funcionamiento antes de procesar todo el catálogo.

### DEC-021. Proteger la ejecución masiva

**Decisión:** la ejecución completa del catálogo requiere habilitar expresamente:

```text
PEN_EJECUTAR_TODOS_CP=1
```

**Motivo:** evitar que una ejecución accidental inicie una descarga masiva.

### DEC-022. Permitir seleccionar códigos postales concretos

**Decisión:** permitir pasar códigos postales como argumentos de ejecución.

**Motivo:** facilitar pruebas controladas y consultas individuales sin necesidad de modificar el código.

Los códigos postales indicados deben existir en el catálogo SQLite.

## 5. Decisiones sobre configuración y dependencias

### DEC-023. Mantener las dependencias declaradas

**Decisión:** utilizar `requirements.txt` como archivo de referencia de las dependencias Python.

Entre las dependencias actuales se encuentran:

- pandas
- playwright
- openpyxl
- python-dotenv

**Motivo:** facilitar la instalación y reproducción del entorno de ejecución.

### DEC-024. Excluir archivos sensibles y temporales del control de versiones

**Decisión:** mantener reglas en `.gitignore` para excluir, entre otros:

- El archivo `.env`.
- Los entornos virtuales.
- Los archivos de caché de Python.
- Las bases de datos locales.
- Determinados archivos de descargas y resultados regenerables.

**Motivo:** evitar publicar información sensible y archivos locales que no deben formar parte del código fuente.

## 6. Decisiones sobre documentación y mantenimiento

### DEC-025. Mantener documentación específica para cada responsabilidad

**Decisión:** separar la documentación general, las instrucciones para asistentes de IA, el seguimiento del proyecto y la documentación técnica.

**Archivos principales:**

- `README.md`: presentación y guía general.
- `AGENTS.md`: instrucciones para agentes de IA.
- `ROADMAP.md`: planificación y fases de trabajo.
- `SEGUIMIENTO_PROYECTO.md`: estado y evolución del proyecto.
- `docs/`: documentación técnica detallada.

**Motivo:** evitar duplicidades y facilitar la incorporación de nuevas personas o asistentes.

### DEC-026. Trabajar por fases y archivo a archivo

**Decisión:** abordar los cambios de forma progresiva, revisando cada archivo antes de modificarlo.

**Motivo:** reducir el riesgo de introducir errores y facilitar la comprobación de cada avance.

**Consecuencia:** no realizar reorganizaciones o modificaciones amplias sin revisar previamente su impacto.

### DEC-027. Documentar los cambios importantes

**Decisión:** actualizar la documentación cuando se modifique una decisión de arquitectura, una regla de almacenamiento o un procedimiento operativo.

**Motivo:** mantener la documentación alineada con el funcionamiento real del proyecto.

### DEC-028. Incorporar `ProcessData.py` y `datos_resumen`

**Decisión:** incorporar `src/ProcessData.py` como cuarto módulo principal. El módulo transforma los registros de `datos_crudos` a la tabla `datos_resumen`, pivotando `metrica` para obtener las columnas `precio_m2`, `compraventas` e `importe_medio`.

La tabla `datos_resumen` tendrá:

- Clave primaria compuesta `(cp, periodo)`.
- Clave foránea `cp` hacia `codigos_postales(cp)`.
- Una columna numérica para cada una de las tres métricas.
- Valores `NULL` cuando una métrica no esté disponible.

**Motivo:** disponer de una estructura analítica en formato ancho, más cómoda para consultas, comparaciones y visualizaciones, sin alterar la tabla de observaciones original.

**Consecuencias:**

- `CreateDatabase.py` crea la tabla `datos_resumen` mediante `CREATE TABLE IF NOT EXISTS`.
- `ProcessData.py` lee todos los registros de `datos_crudos` y actualiza `datos_resumen` mediante UPSERT.
- `ScraperPEN.py` ejecuta la transformación una vez al finalizar el bucle de códigos postales.
- La transformación también puede ejecutarse de forma independiente con `python -m src.ProcessData`.
- `datos_crudos` no se modifica ni se elimina durante la transformación.
- La carpeta `src/` pasa a contener cuatro módulos principales, sustituyendo el límite establecido en DEC-002.

## 7. Cómo modificar este registro

Cuando se adopte una nueva decisión importante:

1. Asignar un identificador consecutivo (`DEC-029`, `DEC-030`, etc.).
2. Describir la decisión de forma clara.
3. Explicar brevemente el motivo.
4. Indicar sus consecuencias para el proyecto.
5. Actualizar la documentación relacionada si resulta necesario.

Si una decisión anterior deja de estar vigente, no debe eliminarse silenciosamente. Se debe indicar que ha sido sustituida y señalar cuál es la nueva decisión.

---

**Documento de referencia:** historial de decisiones de arquitectura, organización y funcionamiento del proyecto ScraperPEN.
