
# Guía de operaciones

## 1. Objetivo

Este documento describe cómo preparar, configurar, ejecutar y comprobar el proyecto ScraperPEN.

Está dirigido a las personas que necesiten trabajar con el scraper, mantener la base de datos o realizar pruebas controladas.

El procedimiento se basa en la estructura y el código actuales del proyecto.

## 2. Requisitos previos

Para ejecutar el proyecto se necesita:

- Python instalado.
- Un entorno virtual de Python.
- Las dependencias declaradas en `requirements.txt`.
- Acceso autorizado al Portal Estadístico del Notariado.
- Credenciales válidas para acceder al portal.
- Una base de datos SQLite inicializada y con el catálogo de códigos postales.

## 3. Preparación del entorno

### 3.1. Abrir el proyecto

Abrir una terminal en la carpeta raíz de `ScraperPEN`.

La estructura debe contener, entre otros, estos elementos:

```text
ScraperPEN/
├── data/
├── resources/
├── src/
├── tests/
├── docs/
├── .env
├── .env.example
└── requirements.txt
```

### 3.2. Crear el entorno virtual

Si todavía no existe:

```powershell
python -m venv .venv
```

### 3.3. Activar el entorno virtual

En Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Cuando esté activado, la terminal mostrará normalmente `(.venv)` al principio de la línea.

### 3.4. Instalar las dependencias

Con el entorno virtual activado:

```powershell
python -m pip install -r requirements.txt
```

Las dependencias actuales incluyen:

- `pandas`
- `playwright`
- `openpyxl`
- `python-dotenv`

### 3.5. Instalar el navegador de Playwright

Si Chromium todavía no está instalado para Playwright:

```powershell
python -m playwright install chromium
```

## 4. Configuración de credenciales

El proyecto utiliza variables de entorno para acceder al portal.

El archivo local `.env` debe contener:

```dotenv
PEN_USER_EMAIL=tu_correo
PEN_USER_PASSWORD=tu_contrasena
```

No deben utilizarse credenciales reales en documentación, ejemplos compartidos ni archivos publicados en Git.

El archivo `.env` está excluido del control de versiones mediante `.gitignore`.

`ScraperPEN.py` utiliza `python-dotenv` para cargar las variables al iniciar el módulo.

Si las variables no están configuradas, el programa muestra un error indicando que faltan las credenciales.

## 5. Configuración de ejecución

El scraper dispone de dos variables adicionales:

| Variable                  | Valor por defecto | Función                                             |
| ------------------------- | ----------------- | ---------------------------------------------------- |
| `PEN_CP_PRUEBA`         | `29710`         | Código postal utilizado en la ejecución de prueba. |
| `PEN_EJECUTAR_TODOS_CP` | `0`             | Controla la ejecución del catálogo completo.       |

Para mantener el modo de prueba:

```dotenv
PEN_CP_PRUEBA=29710
PEN_EJECUTAR_TODOS_CP=0
```

Para habilitar expresamente la ejecución completa:

```dotenv
PEN_EJECUTAR_TODOS_CP=1
```

La ejecución masiva no debe activarse hasta haber comprobado satisfactoriamente el proceso con códigos postales individuales.

## 6. Preparación de la base de datos

La base de datos principal se encuentra en:

```text
data/database/inmobiliario.db
```

Antes de ejecutar el scraper se debe comprobar que:

- El archivo existe.
- La tabla `codigos_postales` está creada.
- El catálogo contiene los códigos postales que se desean consultar.
- Existe la tabla `datos_crudos`.
- Existe la tabla `datos_resumen`.
- Las relaciones entre las tablas son correctas.

### 6.1. Inicializar una base de datos nueva

Si se necesita crear una base nueva, el módulo disponible es:

```powershell
python -m src.CreateDatabase
```

Este procedimiento crea las tablas `codigos_postales`, `datos_crudos`, `datos_resumen`, `log_descargas` y el índice mediante instrucciones `IF NOT EXISTS`. Si `datos_resumen` no existe, la crea; si ya existe, no la sustituye ni altera sus datos.

**Importante:** crear el esquema no importa automáticamente el catálogo de códigos postales. La carga del catálogo debe realizarse por el procedimiento correspondiente y comprobarse antes de ejecutar el scraper.

No ejecutar este procedimiento como sustituto de una copia de seguridad ni como solución automática ante problemas de una base existente.

### 6.2. Comprobar el acceso a SQLite

Se puede ejecutar:

```powershell
python -m src.DatabaseManager
```

El módulo muestra la ruta de la base de datos configurada.

Esta ejecución no sustituye a una comprobación completa de los registros ni de su integridad.

## 7. Ejecución del scraper

El módulo principal es:

```text
src/ScraperPEN.py
```

### 7.1. Ejecutar en modo de prueba

Con `PEN_EJECUTAR_TODOS_CP=0`, ejecutar:

```powershell
python -m src.ScraperPEN
```

El comportamiento por defecto es consultar el CP configurado en `PEN_CP_PRUEBA`, que actualmente es `29710`.

El navegador Chromium se abre en modo visible.

### 7.2. Consultar un código postal concreto

También se pueden indicar códigos postales como argumentos:

```powershell
python -m src.ScraperPEN 29001
```

Para consultar varios:

```powershell
python -m src.ScraperPEN 29001 29002 29003
```

Cuando se indican argumentos, estos tienen prioridad sobre el código postal de prueba y sobre la selección del catálogo completo.

El programa elimina los códigos repetidos y comprueba que todos existan en el catálogo SQLite.

### 7.3. Ejecutar el catálogo completo

Solo después de superar las pruebas individuales:

1. Crear una copia de seguridad de SQLite.
2. Revisar las credenciales.
3. Comprobar las rutas de almacenamiento.
4. Activar `PEN_EJECUTAR_TODOS_CP=1`.
5. Ejecutar:

```powershell
python -m src.ScraperPEN
```

El scraper recupera el catálogo desde SQLite y procesa los códigos postales disponibles.

Al finalizar, devolver `PEN_EJECUTAR_TODOS_CP` a `0` para evitar ejecuciones masivas accidentales posteriores.

## 8. Funcionamiento de una consulta

Para cada código postal, el scraper realiza las siguientes operaciones:

1. Accede al buscador inmobiliario del portal.
2. Selecciona el código postal.
3. Configura los filtros de consulta.
4. Comprueba si el portal muestra datos provinciales en sustitución de los datos específicos del CP.
5. Si los datos son provinciales, registra el resultado y omite su almacenamiento como datos del código postal.
6. Si la consulta es válida, descarga el PDF.
7. Extrae las tres métricas disponibles.
8. Comprueba que se han obtenido las métricas esperadas.
9. Genera un Excel.
10. Inserta o actualiza los registros en SQLite.
11. Registra el resultado de la descarga.

Cuando termina el bucle de códigos postales, `ScraperPEN.py` ejecuta una sola vez `procesar_datos()` para actualizar `datos_resumen` a partir de todos los registros existentes en `datos_crudos`. Esto también sucede en ejecuciones de un único CP.

## 9. Archivos generados

El scraper utiliza las siguientes carpetas:

### 9.1. PDF

```text
data/raw/pdf/
```

Nombre de los archivos:

```text
informe_CP_FECHA.pdf
```

Ejemplo:

```text
informe_29001_20261124.pdf
```

### 9.2. Excel

```text
data/raw/excel/
```

Nombre de los archivos:

```text
estadisticas_CP_FECHA.xlsx
```

Ejemplo:

```text
estadisticas_29001_20261124.xlsx
```

El Excel contiene dos hojas:

- `Datos`: observaciones extraídas.
- `Resumen`: datos organizados por código postal, periodo y métrica.

Los directorios se crean automáticamente si no existen.

## 10. Interpretación de los resultados

Durante la ejecución pueden aparecer distintos mensajes:

| Mensaje            | Significado                                                           |
| ------------------ | --------------------------------------------------------------------- |
| `[COMPLETADA]`   | Consulta realizada y datos insertados o actualizados.                 |
| `[SIN DATOS CP]` | El portal ha mostrado datos provinciales y se han omitido.            |
| `[ERROR]`        | Se ha producido un error durante el procesamiento del código postal. |

Los resultados de cada intento quedan registrados en `log_descargas`.

Los estados almacenados son:

- `completada`
- `sin_datos_cp`
- `error`

## 11. Comprobación posterior a la ejecución

Después de una ejecución se deben revisar tres elementos.

### 11.1. Archivos descargados

Comprobar que los PDF y Excel se han guardado en sus carpetas correspondientes.

Revisar que los nombres de archivo contienen el código postal y la fecha esperados.

### 11.2. Tabla `datos_crudos`

Comprobar que las observaciones se han almacenado correctamente.

Consulta de ejemplo:

```sql
SELECT *
FROM datos_crudos
WHERE cp = '29001'
ORDER BY periodo, metrica;
```

Comprobar que:

- Las tres métricas están presentes cuando la extracción ha sido completa.
- Los periodos están normalizados.
- Los valores son coherentes con el Excel descargado.
- No existen duplicados para `(cp, periodo, metrica)`.

### 11.3. Tabla `log_descargas`

Consultar el historial de un código postal:

```sql
SELECT *
FROM log_descargas
WHERE cp = '29001'
ORDER BY fecha_descarga DESC;
```

Comprobar que el estado registrado coincide con el resultado observado durante la ejecución.

### 11.4. Tabla `datos_resumen`

Después de la ejecución del scraper, comprobar la tabla transformada:

```sql
SELECT *
FROM datos_resumen
WHERE cp = '29001'
ORDER BY periodo DESC;
```

Comprobar los recuentos:

```sql
SELECT COUNT(*) FROM datos_crudos;
SELECT COUNT(*) FROM datos_resumen;
```

Comprobar los valores ausentes por métrica:

```sql
SELECT
    COUNT(*),
    SUM(precio_m2 IS NULL),
    SUM(compraventas IS NULL),
    SUM(importe_medio IS NULL)
FROM datos_resumen;
```

Los valores `NULL` representan métricas no disponibles; no deben interpretarse como cero.

### 11.5. Ejecutar la transformación de forma independiente

Desde la raíz del proyecto y con el entorno virtual activado:

```powershell
python -m src.ProcessData
```

El módulo lee todos los registros de `datos_crudos`, pivota las tres métricas y actualiza `datos_resumen` mediante UPSERT. No modifica `datos_crudos`. Puede ejecutarse repetidamente para volver a sincronizar la tabla derivada.

## 12. Comprobaciones de integridad de SQLite

Para revisar la integridad interna:

```sql
PRAGMA integrity_check;
```

El resultado esperado es:

```text
ok
```

Para comprobar las claves foráneas:

```sql
PRAGMA foreign_key_check;
```

Si no devuelve filas, no se han encontrado incumplimientos de las claves foráneas.

Para comprobar el número de registros:

```sql
SELECT COUNT(*) FROM codigos_postales;
SELECT COUNT(*) FROM datos_crudos;
SELECT COUNT(*) FROM datos_resumen;
SELECT COUNT(*) FROM log_descargas;
```

Los recuentos pueden cambiar con cada ejecución y no deben considerarse valores fijos.

## 13. Copias de seguridad

Antes de:

- Ejecutar modificaciones estructurales.
- Realizar migraciones.
- Ejecutar operaciones de mantenimiento.
- Lanzar procesos que puedan modificar muchos registros.

Se debe crear una copia de seguridad de:

```text
data/database/inmobiliario.db
```

La copia debe conservarse separada de la base de datos activa.

Antes de restaurarla, detener cualquier ejecución del scraper y verificar que se está sustituyendo el archivo correcto.

No sobrescribir copias anteriores sin comprobar previamente su contenido.

## 14. Resolución inicial de incidencias

### 14.1. Faltan las credenciales

Si aparece un error indicando que faltan `PEN_USER_EMAIL` o `PEN_USER_PASSWORD`:

1. Comprobar que existe `.env`.
2. Revisar que las variables están escritas correctamente.
3. Comprobar que el archivo está en la raíz del proyecto.
4. Volver a ejecutar el scraper.

No compartir el contenido real del archivo `.env`.

### 14.2. El código postal no existe en el catálogo

Si aparece un error indicando que el CP no existe:

1. Comprobar que se ha escrito correctamente.
2. Consultar `codigos_postales`.
3. Confirmar que el código está incluido en el catálogo SQLite.

No introducir códigos postales directamente en `datos_crudos` para resolver este problema.

### 14.3. No se detectan datos provinciales

El scraper utiliza un selector y un patrón de texto para identificar el mensaje del portal.

Si el portal modifica el mensaje o su estructura, la detección puede dejar de funcionar.

En ese caso:

1. Revisar el mensaje exacto que muestra el portal.
2. Comprobar el selector utilizado.
3. Revisar `hay_datos_provinciales()` y `PATRONES_DATOS_PROVINCIALES`.
4. Realizar una prueba controlada antes de continuar.

Esta detección debe considerarse pendiente de validación definitiva mientras no se haya contrastado con el mensaje real del portal en los casos correspondientes.

### 14.4. No se extraen las métricas

Si aparece un error de extracción incompleta:

1. Comprobar que el portal ha cargado las tablas.
2. Revisar los botones y selectores utilizados.
3. Comprobar los nombres de las columnas.
4. Verificar que las tres métricas se han extraído.

No modificar las reglas de almacenamiento para ocultar un problema de extracción.

### 14.5. Se produce un error de SQLite

Si aparece un error de base de datos:

1. Detener nuevas ejecuciones.
2. Conservar el mensaje de error completo.
3. Comprobar la existencia y ubicación de la base de datos.
4. Revisar el esquema y las claves foráneas.
5. Crear una copia de seguridad antes de realizar modificaciones.

## 15. Estado de validación

Los procedimientos descritos representan el funcionamiento implementado en el código revisado. No todos los escenarios están necesariamente validados de extremo a extremo.

Antes de considerar el scraper preparado para una ejecución masiva deben comprobarse:

- [ ] Acceso correcto al portal con las credenciales configuradas.
- [ ] Selección correcta de un código postal con datos.
- [ ] Detección correcta del mensaje de datos provinciales.
- [ ] Descarga correcta del PDF.
- [ ] Generación correcta del Excel.
- [ ] Extracción de las tres métricas.
- [ ] Inserción y actualización correctas en SQLite.
- [ ] Registro de consultas completadas, sin datos propios y con errores.
- [ ] Integridad de la base de datos después de la prueba.

La ejecución completa del catálogo de Málaga debe realizarse únicamente después de superar estas comprobaciones.

---

**Documento de referencia:** procedimientos de instalación, configuración, ejecución y mantenimiento operativo de ScraperPEN.
