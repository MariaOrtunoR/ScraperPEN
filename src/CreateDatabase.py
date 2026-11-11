"""Inicialización explícita del esquema SQLite para una base nueva."""

from src.DatabaseManager import DB_PATH, obtener_conexion, validar_esquema_principal


def create_database():
    """Crea el esquema completo, sin alterar tablas ya existentes."""
    with obtener_conexion() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS codigos_postales (
                cp TEXT PRIMARY KEY,
                municipio TEXT NOT NULL
            );
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS datos_crudos (
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
        connection.execute("""
            CREATE TABLE IF NOT EXISTS log_descargas (
                id INTEGER PRIMARY KEY,
                fecha_descarga TEXT NOT NULL,
                cp TEXT NOT NULL,
                estado TEXT NOT NULL CHECK (
                    estado IN ('completada', 'sin_datos_cp', 'error')
                ),
                valido INTEGER CHECK (valido IN (0, 1) OR valido IS NULL),
                observaciones TEXT,
                CONSTRAINT fk_log_descargas_cp
                    FOREIGN KEY (cp) REFERENCES codigos_postales(cp)
            );
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_log_descargas_cp_fecha ON log_descargas (cp, fecha_descarga);")
        validar_esquema_principal(connection)
    print(f"Base de datos preparada: {DB_PATH}")


if __name__ == "__main__":
    create_database()
