"""Acceso normalizado a la base de datos inmobiliaria."""

import re
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "database" / "inmobiliario.db"
METRICAS = {"precio (€/m²)": "precio_m2", "precio (€/m2)": "precio_m2", "precio_m2": "precio_m2", "compraventas": "compraventas", "importe medio (€)": "importe_medio", "importe medio": "importe_medio", "importe_medio": "importe_medio"}
MESES = {"ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3, "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6, "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "sept": 9, "septiembre": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12}
ESTADOS_DESCARGA = {"completada", "sin_datos_cp", "error"}


def obtener_conexion():
    """Abre una conexión con la integridad referencial activada."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion


def validar_esquema_principal(conexion):
    """Evita operar sobre una base sin el esquema de producción esperado."""
    tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    faltantes = {"codigos_postales", "datos_crudos"} - tablas
    if faltantes:
        raise RuntimeError("La base de datos no está inicializada. Faltan las tablas: " + ", ".join(sorted(faltantes)))
    columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(datos_crudos)")}
    faltantes = {"fecha_consulta", "cp", "metrica", "periodo", "valor"} - columnas
    if faltantes:
        raise RuntimeError("El esquema de datos_crudos es incompleto. Faltan las columnas: " + ", ".join(sorted(faltantes)))
    claves_foraneas = conexion.execute("PRAGMA foreign_key_list(datos_crudos)").fetchall()
    if not any(fila[2] == "codigos_postales" and fila[3] == "cp" for fila in claves_foraneas):
        raise RuntimeError("datos_crudos debe tener una clave foránea hacia codigos_postales(cp).")


def crear_tabla_log_descargas(conexion):
    """Crea el registro de intentos de consulta, sin deduplicarlos."""
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS log_descargas (
            id INTEGER PRIMARY KEY,
            fecha_descarga TEXT NOT NULL,
            cp TEXT NOT NULL,
            estado TEXT NOT NULL CHECK (estado IN ('completada', 'sin_datos_cp', 'error')),
            valido INTEGER CHECK (valido IN (0, 1) OR valido IS NULL),
            observaciones TEXT,
            CONSTRAINT fk_log_descargas_cp FOREIGN KEY (cp) REFERENCES codigos_postales(cp)
        );
    """)
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_log_descargas_cp_fecha ON log_descargas (cp, fecha_descarga);")


def normalizar_fecha_consulta(fecha):
    texto = str(fecha).strip()
    for formato in ("%Y%m%d", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Fecha de consulta no reconocida: {fecha!r}")


def normalizar_periodo(periodo):
    texto = str(periodo).strip()
    coincidencia = re.fullmatch(r"(\d{4})-(\d{1,2})", texto)
    if coincidencia:
        anio, mes = map(int, coincidencia.groups())
        if 1 <= mes <= 12:
            return f"{anio:04d}-{mes:02d}"
    coincidencia = re.fullmatch(r"(\d{1,2})[/-](\d{4})", texto)
    if coincidencia:
        mes, anio = map(int, coincidencia.groups())
        if 1 <= mes <= 12:
            return f"{anio:04d}-{mes:02d}"
    partes = re.sub(r"[.,]", "", texto.lower()).split()
    if len(partes) == 2:
        for nombre_mes, texto_anio in ((partes[0], partes[1]), (partes[1], partes[0])):
            if nombre_mes in MESES and re.fullmatch(r"\d{4}", texto_anio):
                return f"{int(texto_anio):04d}-{MESES[nombre_mes]:02d}"
    raise ValueError(f"Periodo no reconocido: {periodo!r}")


def normalizar_metrica(metrica):
    clave = re.sub(r"\s+", " ", str(metrica).strip().lower())
    if clave in METRICAS:
        return METRICAS[clave]
    if "compraventa" in clave:
        return "compraventas"
    if "precio" in clave and ("m²" in clave or "m2" in clave):
        return "precio_m2"
    if "importe medio" in clave:
        return "importe_medio"
    raise ValueError(f"Métrica no reconocida: {metrica!r}")


def normalizar_valor(valor):
    if valor is None:
        return None
    if isinstance(valor, bool):
        return int(valor)
    if isinstance(valor, (int, float)):
        return valor
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "null", "-", "—"}:
        return None
    texto = texto.replace("€", "").replace("\u00a0", "").replace(" ", "")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".") if texto.rfind(",") > texto.rfind(".") else texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    elif "." in texto and re.fullmatch(r"[+-]?\d{1,3}(?:\.\d{3})+", texto):
        texto = texto.replace(".", "")
    try:
        numero = float(texto)
    except ValueError as error:
        raise ValueError(f"Valor numérico no reconocido: {valor!r}") from error
    return int(numero) if numero.is_integer() else numero


def guardar_registros(cp, fecha_consulta, registros):
    """Inserta o actualiza exclusivamente observaciones de una consulta válida."""
    cp = str(cp).strip()
    if not cp:
        raise ValueError("El código postal está vacío.")
    fecha = normalizar_fecha_consulta(fecha_consulta)
    preparados = []
    for registro in registros:
        metrica = registro.get("Métrica", registro.get("metrica"))
        periodo = registro.get("Periodo", registro.get("periodo"))
        valor = registro.get("Valor", registro.get("valor"))
        if metrica is None or periodo is None:
            raise ValueError(f"Registro incompleto para CP {cp}: {registro!r}")
        preparados.append((fecha, cp, normalizar_metrica(metrica), normalizar_periodo(periodo), normalizar_valor(valor)))
    modificados = 0
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        for fila in preparados:
            cursor = conexion.execute("""
                INSERT INTO datos_crudos (fecha_consulta, cp, metrica, periodo, valor)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (cp, periodo, metrica) DO UPDATE SET
                    fecha_consulta = excluded.fecha_consulta, valor = excluded.valor
                WHERE datos_crudos.valor IS NOT excluded.valor;
            """, fila)
            modificados += max(cursor.rowcount, 0)
    return {"cp": cp, "recibidos": len(preparados), "insertados_o_actualizados": modificados, "base_datos": str(DB_PATH)}


def registrar_descarga(cp, estado, valido, observaciones=None, fecha_descarga=None):
    """Registra un intento de consulta, también cuando termina con error."""
    cp = str(cp).strip()
    if estado not in ESTADOS_DESCARGA:
        raise ValueError(f"Estado de descarga no reconocido: {estado!r}")
    esperados = {"completada": 1, "sin_datos_cp": 0, "error": None}
    if valido != esperados[estado]:
        raise ValueError(f"El estado {estado!r} requiere valido={esperados[estado]!r}.")
    marca_tiempo = fecha_descarga or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        crear_tabla_log_descargas(conexion)
        cursor = conexion.execute("""
            INSERT INTO log_descargas (fecha_descarga, cp, estado, valido, observaciones)
            VALUES (?, ?, ?, ?, ?)
        """, (marca_tiempo, cp, estado, valido, observaciones))
    return cursor.lastrowid


def obtener_codigos_postales():
    """Devuelve el catálogo maestro en orden, sin duplicados."""
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        return [fila[0] for fila in conexion.execute("SELECT cp FROM codigos_postales ORDER BY cp")]


if __name__ == "__main__":
    print(f"Módulo preparado. Base de datos: {DB_PATH}")
