# Diccionario de datos

Este documento explica los campos de SQLite y del JSON que utiliza el dashboard.

## 1. Identificación geográfica

| Campo | Significado |
|---|---|
| `municipio` | Municipio asociado a la ubicación. Para la fila provincial contiene `Málaga`. |
| `cp` | Código postal guardado como texto. Para la provincia contiene `Todos`. |
| `tipo_ambito` | `cp` para un código postal o `provincia` para la observación provincial. |
| `clave_portal` | Clave utilizada para seleccionar la ubicación en el portal. |
| `cuenta_id` | Identificador interno de la cuenta asignada. |

La provincia se identifica mediante `municipio = 'Málaga'`, `cp = 'Todos'` y `tipo_ambito = 'provincia'`. No equivale al municipio de Málaga ni a la suma de sus códigos postales.

## 2. Métricas

| Identificador | Nombre mostrado | Unidad | Descripción |
|---|---|---|---|
| `precio_m2` | Precio medio por m² | €/m² | Precio medio por metro cuadrado publicado para el ámbito y periodo. |
| `compraventas` | Compraventas | operaciones | Número de operaciones registradas. |
| `importe_medio` | Importe medio | € | Importe medio de las operaciones. |

El dashboard también muestra una **superficie media estimada**, calculada como:

```text
importe_medio / precio_m2
```

Es una estimación derivada de dos indicadores medios; no es un campo descargado directamente ni una medición individual de superficie.

## 3. Periodos y fechas

- `periodo`: mes al que corresponde la estadística, normalizado como `AAAA-MM` (por ejemplo, `2026-09`).
- `fecha_consulta`: fecha en la que se obtuvo la observación.
- `fecha_descarga`: fecha y hora de un intento registrado en `log_descargas`.
- `fecha_exportacion`: fecha y hora en que se generó el JSON para la web.

No deben confundirse la fecha de consulta y el periodo estadístico: una observación puede descargarse hoy y corresponder a un mes anterior.

## 4. Valores ausentes

`NULL` indica que el valor no está disponible para esa combinación de ubicación, periodo y métrica. No equivale a cero.

En el JSON, los valores ausentes se representan como `null`.

## 5. Estados del historial

| Estado | Significado |
|---|---|
| `completada` | Consulta completada con datos propios del ámbito. |
| `sin_datos_cp` | En una consulta de CP, el portal mostró datos provinciales en sustitución de datos específicos. |
| `error` | La consulta terminó con un error técnico. |

`consulta_enviada` indica si se llegó a pulsar «Más estadísticas». Su valor es `1` o `0`.

## 6. Estructura del JSON

El archivo `web/data/datos_resumen.json` tiene tres propiedades principales:

| Propiedad | Tipo | Descripción |
|---|---|---|
| `fecha_exportacion` | texto | Fecha y hora de generación del archivo, con zona horaria. |
| `total_registros` | número | Número de filas incluidas en `datos`. |
| `datos` | array | Observaciones resumidas que utiliza el dashboard. |

Cada objeto de `datos` contiene:

| Campo | Tipo | Descripción |
|---|---|---|
| `municipio` | texto | Municipio de la ubicación. |
| `cp` | texto | Código postal o `Todos`. |
| `tipo_ambito` | texto | `cp` o `provincia`. |
| `periodo` | texto | Periodo estadístico `AAAA-MM`. |
| `precio_m2` | número o null | Precio medio por metro cuadrado. |
| `compraventas` | número o null | Número de compraventas. |
| `importe_medio` | número o null | Importe medio. |

Ejemplo abreviado:

```json
{
  "fecha_exportacion": "2026-11-27T17:15:12+01:00",
  "total_registros": 1,
  "datos": [
    {
      "municipio": "Málaga",
      "cp": "Todos",
      "tipo_ambito": "provincia",
      "periodo": "2026-09",
      "precio_m2": 3726,
      "compraventas": 1635,
      "importe_medio": 364419
    }
  ]
}
```

Los valores del ejemplo ilustran el formato del archivo; los datos reales pueden cambiar con futuras exportaciones.
