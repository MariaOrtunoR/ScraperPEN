"""Exportación de datos_resumen a JSON para el dashboard web."""

import json
from datetime import datetime
from pathlib import Path

from src.DatabaseManager import obtener_conexion, validar_esquema_principal


# La raíz del proyecto es la carpeta que contiene src/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "web" / "data"
OUTPUT_FILE = OUTPUT_DIR / "datos_resumen.json"


def obtener_datos_web(conexion):
    """Obtiene los datos resumidos junto al municipio de cada código postal."""
    cursor = conexion.execute("""
        SELECT
            dr.municipio,
            dr.cp,
            cp.tipo_ambito,
            dr.periodo,
            dr.precio_m2,
            dr.compraventas,
            dr.importe_medio
        FROM datos_resumen AS dr
        INNER JOIN codigos_postales AS cp
            ON cp.municipio = dr.municipio
            AND cp.cp = dr.cp
        ORDER BY dr.periodo, dr.municipio, dr.cp;
    """)

    nombres_columnas = [columna[0] for columna in cursor.description]
    return [
        dict(zip(nombres_columnas, fila))
        for fila in cursor.fetchall()
    ]


def exportar_datos_web():
    """Genera el JSON que consumirá la aplicación web."""
    conexion = obtener_conexion()

    try:
        validar_esquema_principal(conexion)

        tablas = {
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table';"
            )
        }
        if "datos_resumen" not in tablas:
            raise RuntimeError(
                "No existe la tabla datos_resumen. "
                "Ejecuta primero ProcessData.py."
            )

        columnas_resumen = {
            fila[1]
            for fila in conexion.execute("PRAGMA table_info(datos_resumen);")
        }
        columnas_requeridas = {
            "municipio", "cp", "periodo", "precio_m2", "compraventas", "importe_medio"
        }
        faltantes = columnas_requeridas - columnas_resumen
        if faltantes:
            raise RuntimeError(
                "La tabla datos_resumen no tiene las columnas necesarias: "
                + ", ".join(sorted(faltantes))
            )

        registros = obtener_datos_web(conexion)
    finally:
        conexion.close()

    contenido = {
        "fecha_exportacion": datetime.now().astimezone().isoformat(timespec="seconds"),
        "total_registros": len(registros),
        "datos": registros,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as archivo:
        json.dump(
            contenido,
            archivo,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

    print(
        f"Exportación completada: {len(registros)} registros.\n"
        f"Archivo generado: {OUTPUT_FILE}"
    )
    return len(registros)


if __name__ == "__main__":
    exportar_datos_web()
