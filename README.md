# ScraperPEN

## 1. Descripción del proyecto

ScraperPEN es un proyecto desarrollado en Python para recopilar y almacenar estadísticas inmobiliarias del **Portal Estadístico del Notariado (PEN)** correspondientes a los códigos postales de la provincia de Málaga.

El proyecto utiliza Playwright para automatizar la navegación y descarga de información, pandas para trabajar con los datos y SQLite como sistema de almacenamiento.

Su finalidad es construir un histórico de estadísticas inmobiliarias que pueda utilizarse posteriormente para análisis y visualización de datos.

## 2. Objetivos

El proyecto tiene los siguientes objetivos:

- Consultar las estadísticas inmobiliarias de los códigos postales de Málaga.
- Automatizar las consultas mediante Playwright.
- Descargar y conservar los archivos originales en Excel y PDF.
- Extraer y normalizar las estadísticas obtenidas.
- Almacenar los datos históricos en una base de datos SQLite.
- Actualizar los registros existentes sin generar duplicados.
- Registrar los resultados de las consultas y los errores producidos.
- Preparar los datos para futuros análisis y dashboards.

## 3. Tecnologías utilizadas

| Tecnología   | Función                         |
| ------------- | -------------------------------- |
| Python        | Lenguaje de programación        |
| Playwright    | Automatización del navegador    |
| pandas        | Tratamiento de datos             |
| openpyxl      | Lectura y escritura de Excel     |
| python-dotenv | Gestión de variables de entorno |
| SQLite        | Almacenamiento de datos          |

## 4. Estructura del proyecto

```text
ScraperPEN/
│
├── data/
│   ├── database/
│   ├── processed/
│   └── raw/
│       ├── excel/
│       └── pdf/
│
├── resources/
│
├── src/
│   ├── ScraperPEN.py
│   ├── CreateDatabase.py
│   └── DatabaseManager.py
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── data_dictionary.md
│   ├── decisions.md
│   └── operations.md
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

## 5. Componentes principales

### `src/`

Contiene los tres módulos Python principales:

- `ScraperPEN.py`: automatiza las consultas al portal, descarga los archivos, extrae las estadísticas y coordina su almacenamiento.
- `CreateDatabase.py`: inicializa la estructura de la base de datos SQLite.
- `DatabaseManager.py`: centraliza las operaciones de acceso, normalización y almacenamiento de datos.

### `data/`

Contiene los datos generados por el proyecto:

- `database/`: base de datos SQLite y copias de seguridad.
- `raw/excel/`: archivos Excel originales descargados.
- `raw/pdf/`: informes PDF originales descargados.
- `processed/`: archivos derivados y datos procesados.

### `resources/`

Contiene los archivos de referencia necesarios para el proyecto, como el catálogo de códigos postales y los recursos geográficos y metodológicos.

### `tests/`

Contendrá las pruebas automatizadas del proyecto.

### `docs/`

Contiene la documentación técnica y las decisiones de diseño.

## 6. Base de datos

La información se almacena en SQLite, mediante tres tablas principales:

- `codigos_postales`: catálogo maestro de códigos postales y municipios.
- `datos_crudos`: observaciones inmobiliarias válidas.
- `log_descargas`: historial de consultas y resultados.

Las tres métricas inmobiliarias almacenadas son:

- `precio_m2`: precio por metro cuadrado.
- `compraventas`: número de compraventas.
- `importe_medio`: importe medio de las operaciones.

La combinación de código postal, periodo y métrica identifica de forma única cada observación.

Los datos existentes se actualizan cuando se vuelven a descargar periodos ya almacenados.

## 7. Configuración del entorno

Se recomienda utilizar un entorno virtual de Python.

### Crear el entorno virtual

```powershell
python -m venv .venv
```

### Activar el entorno

```powershell
.\.venv\Scripts\Activate.ps1
```

### Instalar las dependencias

```powershell
pip install -r requirements.txt
```

### Instalar el navegador de Playwright

```powershell
playwright install chromium
```

### Configurar las credenciales

Crear el archivo `.env` a partir de `.env.example` y completar las credenciales de acceso al portal.

Las variables utilizadas son:

- `PEN_USER_EMAIL`
- `PEN_USER_PASSWORD`
- `PEN_CP_PRUEBA`
- `PEN_EJECUTAR_TODOS_CP`

El archivo `.env` contiene información privada y no debe publicarse en Git.

## 8. Ejecución del scraper

Desde la raíz del proyecto:

```powershell
python -m src.ScraperPEN
```

Por defecto, el programa utiliza un único código postal de prueba, configurado mediante `PEN_CP_PRUEBA`, cuyo valor predeterminado es `29710`.

Para habilitar la consulta de todo el catálogo, debe configurarse expresamente:

```text
PEN_EJECUTAR_TODOS_CP=1
```

La ejecución completa debe realizarse únicamente después de validar las pruebas individuales.

También es posible indicar códigos postales concretos como argumentos de ejecución, siempre que estén presentes en el catálogo.

## 9. Documentación adicional

El proyecto dispone de documentación específica:

| Documento                   | Contenido                                             |
| --------------------------- | ----------------------------------------------------- |
| `AGENTS.md`               | Instrucciones para las IA que trabajen en el proyecto |
| `ROADMAP.md`              | Plan de desarrollo y tareas pendientes                |
| `SEGUIMIENTO_PROYECTO.md` | Estado actual y evolución del proyecto               |
| `docs/architecture.md`    | Arquitectura y componentes                            |
| `docs/database.md`        | Diseño y funcionamiento de SQLite                    |
| `docs/data_dictionary.md` | Definición de campos y métricas                     |
| `docs/decisions.md`       | Decisiones técnicas y arquitectónicas               |
| `docs/operations.md`      | Instalación, ejecución y mantenimiento              |

## 10. Principios de desarrollo

El desarrollo de ScraperPEN seguirá estos principios:

- Mantener una estructura sencilla y coherente.
- Evitar duplicidades innecesarias.
- Proteger las credenciales y los datos locales.
- Conservar los archivos originales descargados.
- Preservar la integridad de la base de datos.
- Evitar la introducción de datos provinciales como si fueran datos propios de un código postal.
- Validar los cambios antes de incorporarlos al proyecto.
- Mantener actualizada la documentación.

Cualquier modificación arquitectónica importante deberá analizarse antes de realizarse.

---

**Proyecto:** ScraperPEN
**Ámbito geográfico:** provincia de Málaga, España
**Fuente estadística:** Portal Estadístico del Notariado
