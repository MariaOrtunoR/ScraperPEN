
"""Transformación de datos_crudos a datos_resumen para su análisis."""

import pandas as pd

from src.DatabaseManager import obtener_conexion, validar_esquema_principal


METRICAS = [
    "precio_m2",
    "compraventas",
    "importe_medio",
]


def crear_tabla_resumen(conexion):
    """Crea la tabla de datos transformados si todavía no existe."""
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS datos_resumen (
            cp TEXT NOT NULL,
            periodo TEXT NOT NULL,
            precio_m2 NUMERIC,
            compraventas NUMERIC,
            importe_medio NUMERIC,
            CONSTRAINT pk_datos_resumen PRIMARY KEY (cp, periodo),
            CONSTRAINT fk_datos_resumen_cp
                FOREIGN KEY (cp) REFERENCES codigos_postales(cp)
        );
    """)


def obtener_datos_transformados(conexion):
    """Lee los datos originales y pivota las métricas a columnas."""
    datos = pd.read_sql_query("""
        SELECT cp, periodo, metrica, valor
        FROM datos_crudos
        ORDER BY cp, periodo;
    """, conexion)

    if datos.empty:
        return []

    datos_pivotados = datos.pivot(
        index=["cp", "periodo"],
        columns="metrica",
        values="valor"
    ).reset_index()

    datos_pivotados.columns.name = None

    # Garantiza que siempre existan las tres columnas de métricas.
    for metrica in METRICAS:
        if metrica not in datos_pivotados.columns:
            datos_pivotados[metrica] = None

    datos_pivotados = datos_pivotados[
        ["cp", "periodo", *METRICAS]
    ]

    # Convierte los valores NaN de pandas en None para SQLite.
    datos_pivotados = datos_pivotados.astype(object).where(
        pd.notna(datos_pivotados),
        None
    )

    return list(datos_pivotados.itertuples(index=False, name=None))


def guardar_datos_resumen(conexion, registros):
    """Inserta o actualiza los registros transformados."""
    if not registros:
        return 0

    conexion.executemany("""
        INSERT INTO datos_resumen (
            cp,
            periodo,
            precio_m2,
            compraventas,
            importe_medio
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (cp, periodo) DO UPDATE SET
            precio_m2 = excluded.precio_m2,
            compraventas = excluded.compraventas,
            importe_medio = excluded.importe_medio
        WHERE
            datos_resumen.precio_m2 IS NOT excluded.precio_m2
            OR datos_resumen.compraventas IS NOT excluded.compraventas
            OR datos_resumen.importe_medio IS NOT excluded.importe_medio;
    """, registros)

    return len(registros)


def procesar_datos():
    """Ejecuta la transformación completa y actualiza datos_resumen."""
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)

        crear_tabla_resumen(conexion)

        registros = obtener_datos_transformados(conexion)
        cantidad = guardar_datos_resumen(conexion, registros)

        total = conexion.execute(
            "SELECT COUNT(*) FROM datos_resumen;"
        ).fetchone()[0]

    print(
        "Transformación completada: "
        f"{cantidad} registros procesados. "
        f"Total de registros en datos_resumen: {total}."
    )

    return cantidad


if __name__ == "__main__":
    procesar_datos()
