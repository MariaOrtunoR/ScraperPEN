# Arquitectura de ScraperPEN

Este documento explica cómo se organiza ScraperPEN y cómo circula la información desde el portal de origen hasta el dashboard.

## 1. Visión general

ScraperPEN se compone de dos partes principales:

1. **Proceso de extracción y preparación de datos**, desarrollado en Python y respaldado por SQLite.
2. **Dashboard web**, una aplicación estática que carga un JSON y un archivo GeoJSON.

El flujo completo es:

```text
Catálogo de ubicaciones en SQLite
              |
              v
       ScraperPEN.py
              |
              v
 Portal Estadístico del Notariado
       (navegación Playwright)
              |
       +------+------+
       |             |
       v             v
 Datos propios   Sin datos propios / error
       |             |
       v             v
 datos_crudos    log_descargas
       |
       v
 ProcessData.py
       |
       v
 datos_resumen
       |
       v
 ExportWebData.py
       |
       v
 web/data/datos_resumen.json
       |
       v
 Dashboard (HTML, CSS y JavaScript)
       |
       +---- web/data/malaga.geojson
```

La información provincial se consulta directamente en el portal. No se calcula sumando los códigos postales. Si una consulta de código postal muestra datos provinciales en sustitución de datos propios, el scraper registra `sin_datos_cp` y no atribuye esos valores al código postal.

## 2. Componentes Python

| Archivo | Responsabilidad |
|---|---|
| `src/ScraperPEN.py` | Coordina el navegador, selecciona ubicaciones, consulta el portal, descarga archivos, extrae métricas y registra resultados. |
| `src/CreateDatabase.py` | Define y prepara el esquema de las cuatro tablas SQLite. Incluye operaciones de migración del modelo territorial. |
| `src/DatabaseManager.py` | Centraliza conexiones, validación del esquema, catálogo, cuotas, inserciones, actualizaciones y logs. |
| `src/ProcessData.py` | Transforma las observaciones del formato largo al formato resumido. |
| `src/ExportWebData.py` | Exporta `datos_resumen` a `web/data/datos_resumen.json`. |

## 3. Componentes web

| Archivo | Responsabilidad |
|---|---|
| `web/index.html` | Estructura y contenido de la aplicación. |
| `web/assets/css/styles.css` | Diseño, distribución y estilos adaptables. |
| `web/assets/js/app.js` | Carga los datos, gestiona filtros, calcula indicadores y dibuja gráficos y mapa. |
| `web/data/datos_resumen.json` | Datos estadísticos que consume el dashboard. |
| `web/data/malaga.geojson` | Geometrías de los códigos postales representados en el mapa. |

El dashboard es estático: no se conecta directamente a SQLite ni ejecuta Python en el navegador. Lee los archivos JSON y GeoJSON mediante `fetch`.

## 4. Identidad de las ubicaciones

Cada ubicación se identifica mediante la combinación `(municipio, cp)`.

- Un código postal utiliza `tipo_ambito = 'cp'`.
- La provincia se representa como `municipio = 'Málaga'`, `cp = 'Todos'` y `tipo_ambito = 'provincia'`.

La fila provincial es independiente de los códigos postales. Esta separación evita mezclar el dato oficial provincial con los valores particulares de cada CP.

## 5. Cuentas y control de consultas

El catálogo contiene 161 ubicaciones: 160 códigos postales y una ubicación provincial. La asignación actual se distribuye entre cuatro cuentas internas:

| Cuenta | Ubicaciones asignadas |
|---|---:|
| `cuenta_1` | 45 |
| `cuenta_2` | 45 |
| `cuenta_3` | 45 |
| `cuenta_4` | 26 |
| **Total** | **161** |

Cada cuenta tiene un máximo configurado de 45 consultas enviadas por mes natural. El consumo se registra en `log_descargas.consulta_enviada`: se marca cuando el scraper pulsa «Más estadísticas». Los fallos anteriores a ese paso no consumen consulta; los posteriores sí.

Las ubicaciones mantienen una asignación fija. El programa procesa las cuentas secuencialmente y no inicia sesión en una cuenta si no tiene ubicaciones candidatas o cuota disponible.

## 6. Modos de ejecución

- **Modo individual:** se indican una o varias claves `clave_portal`. El scraper las resuelve en SQLite y respeta su asignación de cuenta.
- **Modo de prueba por defecto:** si no se indican argumentos y `PEN_EJECUTAR_TODOS_CP=0`, se utiliza `PEN_CP_PRUEBA` (por defecto, `29710`).
- **Modo general:** si no se indican argumentos y `PEN_EJECUTAR_TODOS_CP=1`, se seleccionan ubicaciones pendientes. Se priorizan errores técnicos y después ubicaciones nunca consultadas. Se omiten las que terminaron `completada` o `sin_datos_cp`.

## 7. Tratamiento y exportación

`ProcessData.py` agrupa por `(municipio, cp, periodo)` y pivota las tres métricas para crear una fila con `precio_m2`, `compraventas` e `importe_medio`. Los valores no disponibles se conservan como `NULL`.

`ExportWebData.py` consulta `datos_resumen`, incorpora `tipo_ambito` desde el catálogo y escribe un JSON con esta estructura general:

```json
{
  "fecha_exportacion": "fecha y hora de exportación",
  "total_registros": 0,
  "datos": []
}
```

Cada elemento de `datos` contiene municipio, CP, tipo de ámbito, periodo y las tres métricas.

## 8. Ejecución del dashboard

Para probar la web desde el equipo local:

```powershell
python -m http.server 8000 --directory web
```

Después se abre `http://localhost:8000`. Se necesita servir la carpeta por HTTP porque el navegador carga los ficheros JSON y GeoJSON con `fetch`.
