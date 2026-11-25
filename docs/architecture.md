
# Arquitectura del proyecto ScraperPEN

## 1. Objetivo

Este documento describe la arquitectura técnica de ScraperPEN, la organización de sus componentes y el flujo de información desde el Portal Estadístico del Notariado hasta la base de datos SQLite.

Su finalidad es facilitar el mantenimiento del proyecto y permitir que cualquier desarrollador o asistente de IA comprenda cómo funciona sin tener que deducir la arquitectura examinando todo el código.

## 2. Arquitectura general

ScraperPEN utiliza una arquitectura sencilla basada en cuatro módulos Python con responsabilidades diferenciadas.

| Componente         | Responsabilidad                                                             |
| ------------------ | --------------------------------------------------------------------------- |
| ScraperPEN.py      | Automatización de la navegación, descarga y extracción de estadísticas. |
| DatabaseManager.py | Acceso a SQLite, normalización y almacenamiento de información.           |
| CreateDatabase.py  | Creación e inicialización de la estructura de la base de datos.           |
| ProcessData.py     | Transformación de `datos_crudos` a `datos_resumen` para el análisis.       |

El sistema utiliza:

- Playwright para automatizar el navegador.
- pandas para organizar los datos extraídos.
- openpyxl para generar archivos Excel.
- python-dotenv para cargar la configuración local.
- SQLite para almacenar los datos históricos.

## 3. Organización de carpetas

```text
ScraperPEN/
│
├── data/
│   ├── database/
│   │   └── inmobiliario.db
│   │
│   ├── processed/
│   │
│   └── raw/
│       ├── excel/
│       └── pdf/
│
├── resources/
│
├── src/
│   ├── ScraperPEN.py
│   ├── CreateDatabase.py
│   ├── DatabaseManager.py
│   └── ProcessData.py
│
├── tests/
│
├── docs/
│
├── .env
├── .env.example
├── .gitignore
├── AGENTS.md
├── README.md
├── ROADMAP.md
├── SEGUIMIENTO_PROYECTO.md
└── requirements.txt
```

### 3.1. `src/`

Contiene los cuatro módulos principales del proyecto.

### 3.2. `data/`

Almacena la información generada y utilizada por el sistema.

- `database/`: base de datos SQLite y copias de seguridad.
- `raw/excel/`: archivos Excel descargados.
- `raw/pdf/`: informes PDF descargados.
- `processed/`: archivos derivados y resultados de procesamiento.

### 3.3. `resources/`

Contiene los recursos de referencia del proyecto, como el catálogo de códigos postales, archivos geográficos y documentación metodológica.

### 3.4. `tests/`

Contendrá las pruebas automatizadas de los distintos componentes.

### 3.5. `docs/`

Contiene la documentación técnica y las decisiones arquitectónicas.

## 4. Responsabilidades de los módulos

### 4.1. ScraperPEN.py

Es el módulo principal y coordina el proceso de obtención de información.

Sus responsabilidades son:

1. Cargar las variables de entorno.
2. Obtener las credenciales de acceso.
3. Consultar el catálogo de códigos postales mediante DatabaseManager.
4. Determinar los códigos postales que se van a procesar.
5. Iniciar el navegador mediante Playwright.
6. Acceder al Portal Estadístico del Notariado.
7. Seleccionar el código postal y los filtros correspondientes.
8. Detectar si el portal muestra datos provinciales.
9. Descargar el informe PDF cuando corresponda.
10. Extraer las tres métricas inmobiliarias.
11. Generar el archivo Excel.
12. Enviar los registros válidos a DatabaseManager.
13. Registrar el resultado de la consulta.

El módulo contiene también las funciones auxiliares necesarias para seleccionar ubicaciones, extraer tablas, validar métricas y gestionar las descargas.

El scraper debe mantenerse como un único archivo.

### 4.2. DatabaseManager.py

Centraliza las operaciones relacionadas con SQLite.

Sus responsabilidades son:

- Definir la ubicación de la base de datos.
- Crear conexiones SQLite.
- Activar las claves foráneas.
- Validar el esquema principal.
- Normalizar fechas de consulta.
- Normalizar periodos estadísticos.
- Normalizar nombres de métricas.
- Normalizar valores numéricos.
- Insertar y actualizar observaciones.
- Registrar los resultados de las consultas.
- Obtener el catálogo de códigos postales.

Este módulo es el intermediario entre el scraper y la base de datos.

Los demás componentes no deben duplicar sus operaciones de acceso y normalización.

### 4.3. CreateDatabase.py

Se encarga de inicializar la estructura SQLite.

Crea las tablas:

- `codigos_postales`
- `datos_crudos`
- `log_descargas`

También define las restricciones de integridad y los índices correspondientes.

Este módulo está destinado a la preparación de la estructura de la base de datos, no a la ejecución habitual de las consultas al portal.

### 4.4. ProcessData.py

Se encarga de preparar los datos para su análisis mediante la tabla `datos_resumen`.

Sus responsabilidades son:

- Leer `cp`, `periodo`, `metrica` y `valor` de `datos_crudos`.
- Pivotar las métricas para convertirlas en las columnas `precio_m2`, `compraventas` e `importe_medio`.
- Mantener una fila por combinación `(cp, periodo)`.
- Crear `datos_resumen` si no existe y realizar UPSERT de los registros.
- Conservar los valores no disponibles como `NULL`.
- No modificar ni eliminar registros de `datos_crudos`.

Puede ejecutarse independientemente con `python -m src.ProcessData`. El scraper también lo invoca una vez al terminar el bucle de códigos postales.

## 5. Flujo general de ejecución

El proceso habitual sigue esta secuencia:

```text
INICIO
  |
  v
Cargar configuración y credenciales
  |
  v
Obtener códigos postales de SQLite
  |
  v
Determinar los CP que se consultarán
  |
  v
Iniciar Playwright
  |
  v
Acceder al Portal del Notariado
  |
  v
Iniciar sesión
  |
  v
Seleccionar código postal
  |
  v
Aplicar filtros estadísticos
  |
  v
Consultar mensaje de disponibilidad
  |
  +----------------------------+
  |                            |
  v                            v
Datos provinciales        Datos propios del CP
  |                            |
  v                            v
Registrar resultado       Descargar PDF
sin_datos_cp                    |
  |                            v
  |                       Extraer métricas
  |                            |
  |                            v
  |                       Validar métricas
  |                            |
  |                            v
  |                       Generar Excel
  |                            |
  |                            v
  |                       Guardar en SQLite
  |                            |
  |                            v
  |                       Registrar resultado
  |                       completada
  |                            |
  +-------------+--------------+
                |
                v
          Siguiente CP
                |
                v
       ¿Quedan códigos CP?
                |
                v
       ProcessData.py
                |
                v
               FIN
```

Si se produce un error técnico durante la consulta, se registra el estado `error` en `log_descargas`.

## 6. Flujo de almacenamiento

El proyecto distingue entre los archivos originales descargados, las observaciones estadísticas y el historial de consultas.

### 6.1. Archivos originales

Los archivos descargados se conservan en:

- `data/raw/pdf/`
- `data/raw/excel/`

Su finalidad es permitir la consulta y comprobación posterior de la información obtenida del portal.

### 6.2. Datos normalizados

Las observaciones extraídas se envían a DatabaseManager para su normalización y almacenamiento en `datos_crudos`.

La clave única es:

`(cp, periodo, metrica)`

Si una observación ya existe, se actualiza cuando corresponde.

### 6.3. Datos transformados

`ProcessData.py` genera `datos_resumen`, con una fila por `(cp, periodo)` y las columnas `precio_m2`, `compraventas` e `importe_medio`. La tabla es una representación derivada de `datos_crudos`; los valores ausentes se conservan como `NULL`. La transformación utiliza UPSERT y no modifica la tabla original.

### 6.4. Registro de consultas

Cada intento de consulta genera una entrada independiente en `log_descargas`.

El registro permite conocer si una consulta terminó correctamente, si el portal mostró datos provinciales o si se produjo un error técnico.

## 7. Configuración del sistema

Las variables de entorno utilizadas son:

| Variable                  | Función                                            |
| ------------------------- | --------------------------------------------------- |
| `PEN_USER_EMAIL`        | Usuario de acceso al portal.                        |
| `PEN_USER_PASSWORD`     | Contraseña de acceso.                              |
| `PEN_CP_PRUEBA`         | Código postal utilizado en modo de prueba.         |
| `PEN_EJECUTAR_TODOS_CP` | Habilita la ejecución sobre el catálogo completo. |

Las credenciales se almacenan localmente en `.env`.

El archivo `.env.example` proporciona la plantilla de configuración sin incluir información sensible.

## 8. Integridad y calidad de datos

La arquitectura incorpora varias medidas para proteger la información:

- Activación de claves foráneas en cada conexión SQLite.
- Validación del esquema antes de realizar operaciones.
- Comprobación de la existencia del código postal.
- Restricción de unicidad de las observaciones.
- Normalización de fechas, periodos, métricas y valores.
- Separación entre datos válidos e intentos de consulta.
- Registro de errores técnicos.
- Exclusión de datos provinciales de las observaciones propias de un CP.

## 9. Pruebas

La carpeta `tests/` está destinada a contener pruebas automatizadas.

Se priorizarán las pruebas de:

- Acceso y operaciones SQLite.
- Normalización de datos.
- Inserción y actualización de observaciones.
- Registro de consultas.
- Extracción y validación de métricas.

Las pruebas deben evitar modificaciones accidentales de la base de datos de producción y descargas masivas.

## 10. Principios arquitectónicos

La arquitectura de ScraperPEN debe respetar los siguientes principios:

1. Mantener los cuatro módulos principales y sus responsabilidades actuales.
2. Evitar duplicar operaciones de acceso a SQLite.
3. Mantener separada la automatización del portal y el almacenamiento.
4. Conservar los archivos originales descargados.
5. Proteger la integridad de los datos históricos.
6. Evitar introducir datos provinciales como datos de un código postal.
7. Mantener una estructura sencilla y comprensible.
8. Documentar cualquier cambio arquitectónico importante.

Cualquier modificación de la arquitectura deberá analizarse previamente y contar con la aprobación del responsable del proyecto.
