"""Acceso normalizado al modelo geográfico y estadístico de ScraperPEN."""

import re
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "database" / "inmobiliario.db"
CUENTAS = ("cuenta_1", "cuenta_2", "cuenta_3", "cuenta_4")
LIMITE_MENSUAL_CUENTA = 45
METRICAS = {"precio (€/m²)": "precio_m2", "precio (€/m2)": "precio_m2", "precio_m2": "precio_m2", "compraventas": "compraventas", "importe medio (€)": "importe_medio", "importe medio": "importe_medio", "importe_medio": "importe_medio"}
MESES = {"ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3, "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6, "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "sept": 9, "septiembre": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12}
ESTADOS_DESCARGA = {"completada", "sin_datos_cp", "error"}


def obtener_conexion():
    """Abre una conexión SQLite con las claves foráneas activadas."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion


def validar_esquema_principal(conexion):
    """Comprueba que se está usando el modelo compuesto vigente."""
    tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    faltantes = {"codigos_postales", "datos_crudos", "datos_resumen", "log_descargas"} - tablas
    if faltantes:
        raise RuntimeError("La base de datos no está inicializada. Faltan: " + ", ".join(sorted(faltantes)))
    requeridas = {"codigos_postales": {"municipio", "cp", "tipo_ambito", "clave_portal", "cuenta_id"}, "datos_crudos": {"fecha_consulta", "municipio", "cp", "metrica", "periodo", "valor"}, "datos_resumen": {"municipio", "cp", "periodo", "precio_m2", "compraventas", "importe_medio"}, "log_descargas": {"id", "fecha_descarga", "municipio", "cp", "cuenta_id", "estado", "valido", "consulta_enviada", "observaciones"}}
    for tabla, campos in requeridas.items():
        columnas = {fila[1] for fila in conexion.execute(f"PRAGMA table_info({tabla})")}
        if faltantes_tabla := campos - columnas:
            raise RuntimeError(f"El esquema de {tabla} es incompleto: {', '.join(sorted(faltantes_tabla))}")
    for tabla in ("datos_crudos", "datos_resumen", "log_descargas"):
        claves = conexion.execute(f"PRAGMA foreign_key_list({tabla})").fetchall()
        if not {fila[3] for fila in claves if fila[2] == "codigos_postales"} >= {"municipio", "cp"}:
            raise RuntimeError(f"{tabla} debe referenciar codigos_postales mediante municipio y cp.")


def normalizar_fecha_consulta(fecha):
    for formato in ("%Y%m%d", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(fecha).strip(), formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Fecha de consulta no reconocida: {fecha!r}")


def normalizar_periodo(periodo):
    texto = str(periodo).strip()
    if coincidencia := re.fullmatch(r"(\d{4})-(\d{1,2})", texto):
        anio, mes = map(int, coincidencia.groups())
        if 1 <= mes <= 12:
            return f"{anio:04d}-{mes:02d}"
    if coincidencia := re.fullmatch(r"(\d{1,2})[/-](\d{4})", texto):
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
    if not texto or texto.lower() in {"nan", "none", "null", "n/a", "na", "-", "—"}:
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


def _a_diccionario(fila):
    return dict(zip(("municipio", "cp", "tipo_ambito", "clave_portal", "cuenta_id"), fila))


def obtener_ubicacion(identificador):
    """Obtiene una ubicación por CP o la provincia al recibir ``Málaga``."""
    texto = str(identificador).strip()
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        if texto.casefold() == "málaga".casefold():
            fila = conexion.execute("SELECT municipio, cp, tipo_ambito, clave_portal, cuenta_id FROM codigos_postales WHERE municipio = ? AND cp = 'Todos' AND tipo_ambito = 'provincia'", (texto,)).fetchone()
        else:
            fila = conexion.execute("SELECT municipio, cp, tipo_ambito, clave_portal, cuenta_id FROM codigos_postales WHERE cp = ? AND tipo_ambito = 'cp'", (texto,)).fetchone()
    if not fila:
        raise ValueError(f"No existe una ubicación consultable para {texto!r}.")
    return _a_diccionario(fila)


def obtener_ubicaciones():
    """Devuelve todas las ubicaciones, ya ordenadas por su cuenta asignada."""
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        filas = conexion.execute("SELECT municipio, cp, tipo_ambito, clave_portal, cuenta_id FROM codigos_postales ORDER BY cuenta_id, cp").fetchall()
    return [_a_diccionario(fila) for fila in filas]



def obtener_consumo_mensual(cuenta_id, fecha=None):
    """Cuenta consultas enviadas al portal durante el mes natural indicado."""
    if cuenta_id not in CUENTAS:
        raise ValueError(f"Cuenta no reconocida: {cuenta_id!r}")
    referencia = datetime.fromisoformat(fecha) if isinstance(fecha, str) else (fecha or datetime.now())
    inicio = referencia.strftime("%Y-%m-01")
    siguiente = f"{referencia.year + (referencia.month == 12):04d}-{(referencia.month % 12) + 1:02d}-01"
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        return conexion.execute("SELECT COUNT(*) FROM log_descargas WHERE cuenta_id = ? AND consulta_enviada = 1 AND fecha_descarga >= ? AND fecha_descarga < ?", (cuenta_id, inicio, siguiente)).fetchone()[0]


def obtener_ubicaciones_pendientes(ubicaciones):
    """En modo general devuelve primero errores técnicos y después ubicaciones nunca consultadas."""
    if not ubicaciones:
        return []
    claves = [(ubicacion["municipio"], ubicacion["cp"]) for ubicacion in ubicaciones]
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        estados = {}
        for municipio, cp in claves:
            fila = conexion.execute("""SELECT estado FROM log_descargas
                WHERE municipio = ? AND cp = ?
                ORDER BY fecha_descarga DESC, id DESC LIMIT 1""", (municipio, cp)).fetchone()
            estados[(municipio, cp)] = fila[0] if fila else None
    errores = [u for u in ubicaciones if estados[(u["municipio"], u["cp"])] == "error"]
    nuevas = [u for u in ubicaciones if estados[(u["municipio"], u["cp"])] is None]
    return errores + nuevas


def guardar_registros(municipio, cp, fecha_consulta, registros):
    """Inserta o actualiza observaciones válidas usando la identidad compuesta."""
    municipio, cp, fecha = str(municipio).strip(), str(cp).strip(), normalizar_fecha_consulta(fecha_consulta)
    preparados = []
    for registro in registros:
        metrica, periodo = registro.get("Métrica", registro.get("metrica")), registro.get("Periodo", registro.get("periodo"))
        if metrica is None or periodo is None:
            raise ValueError(f"Registro incompleto para {municipio} / {cp}: {registro!r}")
        preparados.append((fecha, municipio, cp, normalizar_metrica(metrica), normalizar_periodo(periodo), normalizar_valor(registro.get("Valor", registro.get("valor")))))
    modificados = 0
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        for fila in preparados:
            cursor = conexion.execute("""INSERT INTO datos_crudos (fecha_consulta, municipio, cp, metrica, periodo, valor) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (municipio, cp, periodo, metrica) DO UPDATE SET fecha_consulta = excluded.fecha_consulta, valor = excluded.valor
                WHERE datos_crudos.valor IS NOT excluded.valor""", fila)
            modificados += max(cursor.rowcount, 0)
    return {"municipio": municipio, "cp": cp, "recibidos": len(preparados), "insertados_o_actualizados": modificados, "base_datos": str(DB_PATH)}


def registrar_descarga(municipio, cp, cuenta_id, estado, valido, observaciones=None, fecha_descarga=None, consulta_enviada=False):
    """Registra cada intento e indica si se pulsó «Más estadísticas»."""
    if estado not in ESTADOS_DESCARGA or cuenta_id not in CUENTAS:
        raise ValueError("Estado o cuenta de descarga no reconocidos.")
    esperado = {"completada": 1, "sin_datos_cp": 0, "error": None}[estado]
    if valido != esperado:
        raise ValueError(f"El estado {estado!r} requiere valido={esperado!r}.")
    if not isinstance(consulta_enviada, bool):
        raise ValueError("consulta_enviada debe ser un booleano.")
    if estado in {"completada", "sin_datos_cp"} and not consulta_enviada:
        raise ValueError(f"El estado {estado!r} requiere una consulta enviada al portal.")
    marca = fecha_descarga or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with obtener_conexion() as conexion:
        validar_esquema_principal(conexion)
        cursor = conexion.execute("INSERT INTO log_descargas (fecha_descarga, municipio, cp, cuenta_id, estado, valido, consulta_enviada, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (marca, municipio, cp, cuenta_id, estado, valido, int(consulta_enviada), observaciones))
    return cursor.lastrowid
