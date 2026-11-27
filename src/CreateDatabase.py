"""Inicialización y migración controlada del esquema SQLite."""

import shutil
from datetime import datetime

from src.DatabaseManager import CUENTAS, DB_PATH, LIMITE_MENSUAL_CUENTA, obtener_conexion, validar_esquema_principal


def crear_tablas(conexion):
    """Crea el modelo geográfico compuesto para una base vacía."""
    conexion.executescript("""
        CREATE TABLE IF NOT EXISTS codigos_postales (
            municipio TEXT NOT NULL, cp TEXT NOT NULL, tipo_ambito TEXT NOT NULL CHECK (tipo_ambito IN ('provincia', 'cp')),
            clave_portal TEXT NOT NULL, cuenta_id TEXT NOT NULL CHECK (cuenta_id IN ('cuenta_1', 'cuenta_2', 'cuenta_3', 'cuenta_4')),
            PRIMARY KEY (municipio, cp)
        );
        CREATE TABLE IF NOT EXISTS datos_crudos (
            fecha_consulta TEXT NOT NULL, municipio TEXT NOT NULL, cp TEXT NOT NULL,
            metrica TEXT NOT NULL CHECK (metrica IN ('precio_m2', 'compraventas', 'importe_medio')),
            periodo TEXT NOT NULL, valor NUMERIC,
            UNIQUE (municipio, cp, periodo, metrica),
            FOREIGN KEY (municipio, cp) REFERENCES codigos_postales (municipio, cp)
        );
        CREATE TABLE IF NOT EXISTS datos_resumen (
            municipio TEXT NOT NULL, cp TEXT NOT NULL, periodo TEXT NOT NULL,
            precio_m2 NUMERIC, compraventas NUMERIC, importe_medio NUMERIC,
            PRIMARY KEY (municipio, cp, periodo),
            FOREIGN KEY (municipio, cp) REFERENCES codigos_postales (municipio, cp)
        );
        CREATE TABLE IF NOT EXISTS log_descargas (
            id INTEGER PRIMARY KEY, fecha_descarga TEXT NOT NULL, municipio TEXT NOT NULL, cp TEXT NOT NULL,
            cuenta_id TEXT CHECK (cuenta_id IN ('cuenta_1', 'cuenta_2', 'cuenta_3', 'cuenta_4') OR cuenta_id IS NULL),
            estado TEXT NOT NULL CHECK (estado IN ('completada', 'sin_datos_cp', 'error')),
            valido INTEGER CHECK (valido IN (0, 1) OR valido IS NULL), consulta_enviada INTEGER NOT NULL DEFAULT 0 CHECK (consulta_enviada IN (0, 1)), observaciones TEXT,
            FOREIGN KEY (municipio, cp) REFERENCES codigos_postales (municipio, cp)
        );
        CREATE INDEX IF NOT EXISTS idx_log_descargas_cuenta_fecha ON log_descargas (cuenta_id, fecha_descarga);
        CREATE INDEX IF NOT EXISTS idx_log_descargas_ubicacion_fecha ON log_descargas (municipio, cp, fecha_descarga);
    """)


def crear_copia_seguridad():
    """Crea una copia independiente antes de cualquier migración estructural."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")
    destino = DB_PATH.with_name(f"{DB_PATH.stem}_backup_antes_modelo_ambitos_{datetime.now():%Y%m%d_%H%M%S}{DB_PATH.suffix}")
    shutil.copy2(DB_PATH, destino)
    return destino


def migrar_modelo_ambitos():
    """Reconstruye las tablas, conserva históricos y asigna cuentas una sola vez.

    El reparto es determinista: CP reales por orden ascendente y, al final, Málaga/Todos.
    """
    copia = crear_copia_seguridad()
    conexion = obtener_conexion()
    try:
        conteos_antes = {tabla: conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                          for tabla in ("codigos_postales", "datos_crudos", "datos_resumen", "log_descargas")}
        catalogo = conexion.execute("SELECT cp, municipio FROM codigos_postales ORDER BY cp").fetchall()
        columnas_log = {fila[1] for fila in conexion.execute("PRAGMA table_info(log_descargas)")}
        consulta_enviada_anterior = "l.consulta_enviada" if "consulta_enviada" in columnas_log else "0"
        if len(catalogo) + 1 > len(CUENTAS) * LIMITE_MENSUAL_CUENTA:
            raise RuntimeError("El catálogo supera la capacidad total de 180 consultas mensuales.")
        conexion.close()
        # SQLite exige desactivar temporalmente la comprobación durante el reemplazo de tablas.
        conexion = obtener_conexion()
        conexion.execute("PRAGMA foreign_keys = OFF")
        conexion.execute("BEGIN IMMEDIATE")
        for tabla in ("codigos_postales", "datos_crudos", "datos_resumen", "log_descargas"):
            conexion.execute(f"ALTER TABLE {tabla} RENAME TO {tabla}_anterior")
        crear_tablas(conexion)
        ubicaciones = [(municipio, cp, "cp", cp) for cp, municipio in catalogo] + [("Málaga", "Todos", "provincia", "Málaga")]
        filas_catalogo = []
        for posicion, (municipio, cp, tipo_ambito, clave_portal) in enumerate(ubicaciones):
            cuenta = CUENTAS[posicion // LIMITE_MENSUAL_CUENTA]
            filas_catalogo.append((municipio, cp, tipo_ambito, clave_portal, cuenta))
        conexion.executemany("INSERT INTO codigos_postales (municipio, cp, tipo_ambito, clave_portal, cuenta_id) VALUES (?, ?, ?, ?, ?)", filas_catalogo)
        conexion.execute("""INSERT INTO datos_crudos (fecha_consulta, municipio, cp, metrica, periodo, valor)
            SELECT d.fecha_consulta, c.municipio, d.cp, d.metrica, d.periodo, d.valor
            FROM datos_crudos_anterior d JOIN codigos_postales c ON c.cp = d.cp AND c.tipo_ambito = 'cp'""")
        conexion.execute("""INSERT INTO datos_resumen (municipio, cp, periodo, precio_m2, compraventas, importe_medio)
            SELECT c.municipio, d.cp, d.periodo, d.precio_m2, d.compraventas, d.importe_medio
            FROM datos_resumen_anterior d JOIN codigos_postales c ON c.cp = d.cp AND c.tipo_ambito = 'cp'""")
        conexion.execute(f"""INSERT INTO log_descargas (id, fecha_descarga, municipio, cp, cuenta_id, estado, valido, consulta_enviada, observaciones)
            SELECT l.id, l.fecha_descarga, c.municipio, l.cp, NULL, l.estado, l.valido, {consulta_enviada_anterior}, l.observaciones
            FROM log_descargas_anterior l JOIN codigos_postales c ON c.cp = l.cp AND c.tipo_ambito = 'cp'""")
        for tabla in ("codigos_postales", "datos_crudos", "datos_resumen", "log_descargas"):
            conexion.execute(f"DROP TABLE {tabla}_anterior")
        conexion.commit()
        conexion.execute("PRAGMA foreign_keys = ON")
        validar_esquema_principal(conexion)
        errores_fk = conexion.execute("PRAGMA foreign_key_check").fetchall()
        integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        conteos_despues = {tabla: conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                            for tabla in ("codigos_postales", "datos_crudos", "datos_resumen", "log_descargas")}
        if errores_fk or integridad != "ok" or any(conteos_despues[t] != conteos_antes[t] for t in conteos_antes if t != "codigos_postales"):
            raise RuntimeError("La verificación posterior de la migración ha fallado.")
        return {"copia_seguridad": str(copia), "antes": conteos_antes, "despues": conteos_despues, "integridad": integridad}
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def create_database():
    """Crea el esquema vigente solo si la base está vacía."""
    with obtener_conexion() as conexion:
        crear_tablas(conexion)
        validar_esquema_principal(conexion)
    print(f"Base de datos preparada: {DB_PATH}")


if __name__ == "__main__":
    print(migrar_modelo_ambitos())
