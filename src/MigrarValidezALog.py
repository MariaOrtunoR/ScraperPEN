"""Migración única: elimina observaciones no válidas y retira su marcador legado."""

import shutil
from datetime import datetime

from src.DatabaseManager import DB_PATH, crear_tabla_log_descargas, obtener_conexion


def migrar():
    """Respalda la base y reconstruye datos_crudos sin la columna ``valido``.

    No crea entradas históricas en log_descargas: el antiguo indicador procedía de
    una clasificación estática, no de registros verificables del portal.
    """
    with obtener_conexion() as conexion:
        columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(datos_crudos)")}
        if "valido" not in columnas:
            crear_tabla_log_descargas(conexion)
            return {"migrada": False, "motivo": "La migración ya fue aplicada."}
        excluidos = conexion.execute("SELECT COUNT(*) FROM datos_crudos WHERE valido = 0").fetchone()[0]

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.with_name(f"inmobiliario_backup_antes_migracion_validez_{marca}.db")
    shutil.copy2(DB_PATH, backup)

    with obtener_conexion() as conexion:
        crear_tabla_log_descargas(conexion)
        conexion.execute("ALTER TABLE datos_crudos RENAME TO datos_crudos_legado;")
        conexion.execute("""
            CREATE TABLE datos_crudos (
                fecha_consulta TEXT NOT NULL,
                cp TEXT NOT NULL,
                metrica TEXT NOT NULL CHECK (
                    metrica IN ('precio_m2', 'compraventas', 'importe_medio')
                ),
                periodo TEXT NOT NULL,
                valor NUMERIC,
                CONSTRAINT uq_datos_crudos UNIQUE (cp, periodo, metrica),
                CONSTRAINT fk_datos_crudos_cp
                    FOREIGN KEY (cp) REFERENCES codigos_postales(cp)
            );
        """)
        conexion.execute("""
            INSERT INTO datos_crudos (fecha_consulta, cp, metrica, periodo, valor)
            SELECT fecha_consulta, cp, metrica, periodo, valor
            FROM datos_crudos_legado
            WHERE valido = 1;
        """)
        conexion.execute("DROP TABLE datos_crudos_legado;")
        errores_fk = conexion.execute("PRAGMA foreign_key_check").fetchall()
        if errores_fk:
            raise RuntimeError(f"La migración dejó errores de integridad: {errores_fk!r}")
        conservados = conexion.execute("SELECT COUNT(*) FROM datos_crudos").fetchone()[0]
    return {"migrada": True, "backup": str(backup), "eliminados": excluidos, "conservados": conservados}


if __name__ == "__main__":
    resultado = migrar()
    print(resultado)
