# Guía de operaciones

Esta guía explica cómo instalar ScraperPEN, configurar el entorno, ejecutar consultas, actualizar los datos y abrir el dashboard.

## 1. Requisitos

- Python instalado.
- Acceso al Portal Estadístico del Notariado.
- Las cuentas necesarias para realizar las consultas.
- Las dependencias indicadas en `requirements.txt`.
- Chromium instalado mediante Playwright.

Los ejemplos de comandos están escritos para PowerShell en Windows.

## 2. Preparar el entorno

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 3. Configurar las cuentas

Copia `.env.example` con el nombre `.env` y completa los datos de acceso:

```dotenv
PEN_USER_1_EMAIL=
PEN_USER_1_PASSWORD=
PEN_USER_2_EMAIL=
PEN_USER_2_PASSWORD=
PEN_USER_3_EMAIL=
PEN_USER_3_PASSWORD=
PEN_USER_4_EMAIL=
PEN_USER_4_PASSWORD=
PEN_CP_PRUEBA=29710
PEN_EJECUTAR_TODOS_CP=0
```

El programa busca las variables de las cuentas según la asignación `cuenta_1` a `cuenta_4` que figura en SQLite. No introduzcas las credenciales en el código fuente.

## 4. Ejecutar consultas

### 4.1. Consultar un código postal

```powershell
python -m src.ScraperPEN 29001
```

### 4.2. Consultar varias ubicaciones

```powershell
python -m src.ScraperPEN 29001 29002
```

Los argumentos son claves `clave_portal` del catálogo. La cuenta correspondiente se obtiene de SQLite.

### 4.3. Ejecutar el modo de prueba por defecto

Si no se indican argumentos y `PEN_EJECUTAR_TODOS_CP=0`, se consulta la ubicación indicada en `PEN_CP_PRUEBA`. Si no se configura, el valor predeterminado es `29710`.

### 4.4. Ejecutar el modo general

Activa la variable para la sesión actual de PowerShell:

```powershell
$env:PEN_EJECUTAR_TODOS_CP = "1"
python -m src.ScraperPEN
```

Al terminar, vuelve al modo de prueba:

```powershell
$env:PEN_EJECUTAR_TODOS_CP = "0"
```

El modo general selecciona primero las ubicaciones cuyo último intento fue `error` y después las que nunca se han consultado. Omite las que terminaron `completada` o `sin_datos_cp`.

## 5. Cómo funciona el control de consultas

El proyecto utiliza cuatro cuentas con asignación fija. Cada cuenta tiene un máximo de 45 consultas enviadas por mes natural.

`log_descargas.consulta_enviada` indica si se pulsó «Más estadísticas»:

- `0`: el proceso falló antes de enviar la consulta.
- `1`: la consulta se envió y cuenta para el límite mensual.

Las ubicaciones no se reasignan automáticamente a otra cuenta. Si una cuenta no tiene cuota disponible, las ubicaciones que no pueda procesar quedan pendientes.

## 6. Procesar y exportar los datos

El scraper ejecuta el procesamiento y la exportación al finalizar. También se pueden ejecutar por separado:

```powershell
python -m src.ProcessData
python -m src.ExportWebData
```

El primer comando reconstruye `datos_resumen` desde `datos_crudos`. El segundo genera:

```text
web/data/datos_resumen.json
```

El archivo JSON es el conjunto de datos que carga el dashboard.

## 7. Abrir el dashboard en local

Desde la raíz del proyecto:

```powershell
python -m http.server 8000 --directory web
```

Abre `http://localhost:8000` en el navegador. No abras `index.html` directamente desde el explorador de archivos: la aplicación necesita cargar el JSON y el GeoJSON mediante peticiones HTTP.

## 8. Actualizar los archivos publicados

Cuando se incorporen nuevas observaciones:

1. Ejecuta el scraper para las ubicaciones que quieras actualizar.
2. Comprueba los resultados en SQLite.
3. Ejecuta `python -m src.ProcessData`.
4. Ejecuta `python -m src.ExportWebData`.
5. Comprueba que se ha actualizado `web/data/datos_resumen.json`.
6. Abre el dashboard en local y revisa los indicadores, gráficos y mapa.
7. Incorpora al repositorio los cambios de los archivos web que correspondan.

El archivo `web/data/malaga.geojson` debe permanecer en la ruta esperada por la aplicación.

## 9. Comprobaciones de SQLite

Para comprobar la integridad de la base:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

El primer comando debe devolver `ok`. El segundo no debe devolver filas.

Antes de realizar cambios estructurales, crea una copia de seguridad y comprueba el esquema. `CreateDatabase.py` incluye funciones de preparación y migración del modelo; no ejecutes una inicialización sobre una base con histórico sin revisar antes qué operación se va a realizar.

## 10. Interpretar los resultados

- `completada`: consulta correcta con datos propios del ámbito.
- `sin_datos_cp`: el portal no ha proporcionado datos propios del código postal y ha mostrado datos provinciales sustitutorios.
- `error`: se produjo un problema técnico; revisa `observaciones` y `consulta_enviada`.

La fila provincial `Málaga / Todos` es independiente de las filas de códigos postales.
