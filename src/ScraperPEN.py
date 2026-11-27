"""Descarga controlada de estadísticas del Portal Estadístico del Notariado."""

import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import Playwright, TimeoutError, sync_playwright

from src.DatabaseManager import (CUENTAS, LIMITE_MENSUAL_CUENTA, guardar_registros,
    obtener_consumo_mensual, obtener_ubicacion, obtener_ubicaciones, obtener_ubicaciones_pendientes, registrar_descarga)
from src.ExportWebData import exportar_datos_web
from src.ProcessData import procesar_datos

load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIR_PDF, DIR_EXCEL = PROJECT_ROOT / "data" / "raw" / "pdf", PROJECT_ROOT / "data" / "raw" / "excel"
CP_PRUEBA = os.getenv("PEN_CP_PRUEBA", "29710")
EJECUTAR_TODOS_LOS_CP = os.getenv("PEN_EJECUTAR_TODOS_CP", "0") == "1"
PATRONES_DATOS_PROVINCIALES = (r"Los datos mostrados a continuación no se corresponden con la ubicación indicada al no disponer de datos suficientes",)


def obtener_credenciales(cuenta_id):
    """Resuelve centralizadamente cuenta_1..4 contra las variables de entorno."""
    try:
        sufijo = cuenta_id.removeprefix("cuenta_")
        if not sufijo or str(int(sufijo)) != sufijo:
            raise ValueError
    except ValueError as error:
        raise RuntimeError(f"Identificador de cuenta no válido: {cuenta_id!r}") from error
    usuario, contrasena = os.getenv(f"PEN_USER_{sufijo}_EMAIL"), os.getenv(f"PEN_USER_{sufijo}_PASSWORD")
    if not usuario or not contrasena:
        raise RuntimeError(f"Faltan las credenciales configuradas para {cuenta_id}.")
    return usuario, contrasena


def ubicaciones_a_consultar(argumentos):
    if argumentos:
        return [obtener_ubicacion(argumento) for argumento in dict.fromkeys(argumentos)]
    if EJECUTAR_TODOS_LOS_CP:
        return obtener_ubicaciones()
    return [obtener_ubicacion(CP_PRUEBA)]


def extraer_tabla(page, metrica):
    registros = []
    page.wait_for_selector("table", timeout=5_000)
    for fila in page.locator("table tbody tr").all():
        datos = {celda.get_attribute("data-label"): celda.inner_text().strip() for celda in fila.locator("td").all()}
        if not (periodo := datos.get("Periodo")):
            continue
        valor = datos.get("Estimación (€ / m²)", datos.get("Precio (€ / m²)", next((v for clave, v in datos.items() if clave != "Periodo"), None)))
        registros.append({"Métrica": metrica, "Periodo": periodo, "Valor": None if valor is None or valor.upper() in {"N/A", "NA", "-", ""} else valor})
    if not registros:
        raise RuntimeError(f"La tabla de {metrica} no contiene registros.")
    return registros


def hay_datos_provinciales(page):
    mensaje = page.locator(".c-ctn-message__content").first
    try:
        mensaje.wait_for(state="visible", timeout=2_000)
        return any(re.search(patron, mensaje.inner_text(timeout=2_000), re.IGNORECASE) for patron in PATRONES_DATOS_PROVINCIALES)
    except TimeoutError:
        return False


def validar_metricas(registros):
    esperadas = {"Precio (€/m²)", "Compraventas", "Importe medio (€)"}
    if {registro["Métrica"] for registro in registros} != esperadas:
        raise RuntimeError("La extracción no contiene las tres métricas requeridas.")


def guardar_excel(ubicacion, fecha_hoy, registros):
    datos = pd.DataFrame(registros)
    datos.insert(0, "Fecha_Consulta", fecha_hoy)
    datos.insert(1, "Municipio", ubicacion["municipio"])
    datos.insert(2, "CP", ubicacion["cp"])
    destino = DIR_EXCEL / f"estadisticas_{ubicacion['cp']}_{fecha_hoy}.xlsx"
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        datos.to_excel(writer, sheet_name="Datos", index=False)
        datos.pivot(index=["Municipio", "CP", "Periodo"], columns="Métrica", values="Valor").reset_index().to_excel(writer, sheet_name="Resumen", index=False)
    return destino


def iniciar_sesion(page, usuario, contrasena):
    page.goto("https://penotariado.com/inmobiliario/home", wait_until="domcontentloaded")
    page.get_by_role("button", name="Acceder").click()
    page.get_by_role("textbox", name="Correo electrónico").fill(usuario)
    page.get_by_role("textbox", name="Contraseña").fill(contrasena)
    page.get_by_role("button", name="Acceder").click()
    try:
        page.get_by_role("button", name="Aceptar").click(timeout=4_000)
    except TimeoutError:
        pass
    page.wait_for_url(re.compile(r"penotariado\.com/inmobiliario"), timeout=10_000)


def seleccionar_ubicacion(frame, ubicacion):
    """Selecciona la provincia o municipio usando la clave registrada para el portal."""
    clave = ubicacion["clave_portal"]
    buscador = frame.get_by_role("textbox", name="Buscar provincia, municipio o")
    buscador.fill(clave)
    if ubicacion["tipo_ambito"] == "provincia":
        frame.get_by_role("listbox", name="Provincia").get_by_role("button", name=clave, exact=True).click()
    else:
        frame.get_by_role("button", name=clave, exact=True).click()


def consultar_ubicacion(page, ubicacion, fecha_hoy):
    """Consulta una ubicación y devuelve si consumió una consulta del portal."""
    municipio, cp, cuenta = ubicacion["municipio"], ubicacion["cp"], ubicacion["cuenta_id"]
    consulta_enviada = False
    try:
        page.goto("https://penotariado.com/inmobiliario/buscador-precio-vivienda", wait_until="domcontentloaded")
        frame = page.locator('iframe[title="map-container"]').content_frame
        if frame is None:
            raise RuntimeError("No se encontró el mapa de selección de ubicación.")
        seleccionar_ubicacion(frame, ubicacion)
        frame.get_by_role("group", name="Tipo de construcción").get_by_test_id("dropdownBtn").click()
        frame.get_by_role("menuitemradio", name="Segunda mano").click()
        frame.get_by_role("combobox", name="Todos").click()
        frame.get_by_role("menuitemradio", name="Pisos").click()
        frame.get_by_role("button", name="Más estadísticas").click()
        consulta_enviada = True
        try:
            page.get_by_role("button", name="Continuar").click(timeout=3_000)
        except TimeoutError:
            pass
        if ubicacion["tipo_ambito"] == "cp" and hay_datos_provinciales(page):
            registrar_descarga(municipio, cp, cuenta, "sin_datos_cp", 0, "El portal muestra datos provinciales en lugar de datos del CP.", consulta_enviada=consulta_enviada)
            print(f" [SIN DATOS CP] {municipio} / {cp}")
            return consulta_enviada
        with page.expect_download(timeout=10_000) as descarga:
            page.locator("menu").get_by_role("button", name="Descargar").click()
        pdf = DIR_PDF / f"informe_{cp}_{fecha_hoy}.pdf"
        descarga.value.save_as(pdf)
        configuracion = [("Precio (€/m²)", lambda: page.get_by_role("button", name="Ver tabla").first.click()),
                         ("Compraventas", lambda: (page.get_by_role("button", name="Número compraventas").click(), page.get_by_role("button", name="Ver tabla").click())),
                         ("Importe medio (€)", lambda: (page.locator("button", has_text=re.compile(r"Importe medio", re.I)).click(), page.get_by_role("button", name="Ver tabla").click()))]
        registros = []
        for metrica, accion in configuracion:
            accion(); registros.extend(extraer_tabla(page, metrica))
        validar_metricas(registros)
        excel = guardar_excel(ubicacion, fecha_hoy, registros)
        resultado = guardar_registros(municipio, cp, fecha_hoy, registros)
        registrar_descarga(municipio, cp, cuenta, "completada", 1, f"PDF: {pdf.name}; Excel: {excel.name}; registros: {resultado['recibidos']}.", consulta_enviada=consulta_enviada)
        print(f" [COMPLETADA] {municipio} / {cp}: {resultado['insertados_o_actualizados']} cambios.")
    except Exception as error:
        registrar_descarga(municipio, cp, cuenta, "error", None, str(error), consulta_enviada=consulta_enviada)
        print(f" [ERROR] {municipio} / {cp}: {error}")
    return consulta_enviada


def run(playwright: Playwright):
    argumentos = list(dict.fromkeys(sys.argv[1:]))
    modo_general = not argumentos and EJECUTAR_TODOS_LOS_CP
    ubicaciones = ubicaciones_a_consultar(argumentos)
    por_cuenta = defaultdict(list)
    for ubicacion in ubicaciones:
        por_cuenta[ubicacion["cuenta_id"]].append(ubicacion)
    DIR_PDF.mkdir(parents=True, exist_ok=True); DIR_EXCEL.mkdir(parents=True, exist_ok=True)
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    for cuenta in CUENTAS:
        asignadas = por_cuenta.get(cuenta, [])
        if not asignadas:
            continue
        consumo = obtener_consumo_mensual(cuenta)
        permitidas = max(0, LIMITE_MENSUAL_CUENTA - consumo)
        if permitidas == 0:
            print(f" [LÍMITE] {cuenta} ya ha consumido {consumo} consultas este mes; no se inicia sesión.")
            continue
        if modo_general:
            candidatas = obtener_ubicaciones_pendientes(asignadas)
            print(f" [MODO TODO] {cuenta}: {len(candidatas)} ubicaciones pendientes o con error técnico.")
        else:
            candidatas = asignadas[:permitidas]
            if len(asignadas) > permitidas:
                print(f" [LÍMITE] {cuenta}: se procesarán las primeras {permitidas} ubicaciones de las {len(asignadas)} indicadas; el resto queda pendiente.")
        if not candidatas:
            print(f" [SIN PENDIENTES] {cuenta}: no hay ubicaciones que consultar.")
            continue
        usuario, contrasena = obtener_credenciales(cuenta)
        browser = playwright.chromium.launch(headless=False)
        consultas_consumidas = 0
        try:
            page = browser.new_page(); iniciar_sesion(page, usuario, contrasena)
            for ubicacion in candidatas:
                if consultas_consumidas >= permitidas:
                    break
                if consultar_ubicacion(page, ubicacion, fecha_hoy):
                    consultas_consumidas += 1
        finally:
            browser.close()
        print(f" [CUOTA] {cuenta}: {consultas_consumidas} consultas consumidas en esta ejecución; {permitidas - consultas_consumidas} disponibles al inicio sin usar.")
    procesar_datos(); exportar_datos_web()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
