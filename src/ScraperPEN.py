"""Descarga controlada de estadísticas inmobiliarias del Portal Notarial."""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.sync_api import Playwright, TimeoutError, sync_playwright

from dotenv import load_dotenv

load_dotenv()

from src.DatabaseManager import (
    guardar_registros,
    obtener_codigos_postales,
    registrar_descarga,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIR_PDF = PROJECT_ROOT / "data" / "raw" / "descargas_pdf"
DIR_EXCEL = PROJECT_ROOT / "data" / "raw" / "descargas_excel"
CP_PRUEBA = os.getenv("PEN_CP_PRUEBA", "29710")
EJECUTAR_TODOS_LOS_CP = os.getenv("PEN_EJECUTAR_TODOS_CP", "0") == "1"

# Este patrón deberá contrastarse con el mensaje exacto del portal en la prueba.
PATRONES_DATOS_PROVINCIALES = (r"Los datos mostrados a continuación no se corresponden con la ubicación indicada al no disponer de datos suficientes",)


def obtener_credenciales():
    usuario = os.getenv("PEN_USER_EMAIL")
    contrasena = os.getenv("PEN_USER_PASSWORD")
    if not usuario or not contrasena:
        raise RuntimeError(
            "Faltan PEN_USER_EMAIL y/o PEN_USER_PASSWORD en las variables de entorno."
        )
    return usuario, contrasena


def codigos_a_consultar(cps_argumentos=None):
    catalogo = obtener_codigos_postales()

    # Si se pasan CP por terminal, tienen prioridad
    if cps_argumentos:
        cps = list(dict.fromkeys(cps_argumentos))  # Elimina duplicados

        cps_invalidos = [cp for cp in cps if cp not in catalogo]
        if cps_invalidos:
            raise ValueError(f"CP no válidos: {cps_invalidos}")

        return cps

    # Comportamiento actual si no se pasan argumentos
    if EJECUTAR_TODOS_LOS_CP:
        return catalogo

    if CP_PRUEBA not in catalogo:
        raise ValueError(f"El CP de prueba {CP_PRUEBA!r} no existe en el catálogo.")

    return [CP_PRUEBA]


def extraer_tabla(page, metrica):
    """Extrae los datos priorizando estimaciones cuando existan."""
    registros = []
    page.wait_for_selector("table", timeout=5_000)

    for fila in page.locator("table tbody tr").all():
        datos = {c.get_attribute("data-label"): c.inner_text().strip() for c in fila.locator("td").all()}
        periodo = datos.get("Periodo")
        if not periodo:
            continue

        valor = datos.get("Estimación (€ / m²)", datos.get("Precio (€ / m²)", next((v for k, v in datos.items() if k != "Periodo"), None)))
        valor = None if valor is None or valor.upper() in {"N/A", "NA", "-", ""} else valor
        registros.append({"Métrica": metrica, "Periodo": periodo, "Valor": valor})

    if not registros:
        raise RuntimeError(f"La tabla de {metrica} no contiene registros.")
    return registros


def hay_datos_provinciales(page):
    mensaje = page.locator(".c-ctn-message__content").first
    try:
        mensaje.wait_for(state="visible", timeout=2_000)
        texto = mensaje.inner_text(timeout=2_000)
    except TimeoutError:
        return False
    return any(re.search(patron, texto, re.IGNORECASE) for patron in PATRONES_DATOS_PROVINCIALES)


def validar_metricas(registros):
    esperadas = {"Precio (€/m²)", "Compraventas", "Importe medio (€)"}
    encontradas = {registro["Métrica"] for registro in registros}
    if encontradas != esperadas:
        raise RuntimeError(
            "Extracción incompleta. Métricas encontradas: " + ", ".join(sorted(encontradas))
        )


def guardar_excel(cp, fecha_hoy, registros):
    dataframe = pd.DataFrame(registros)
    dataframe.insert(0, "Fecha_Consulta", fecha_hoy)
    dataframe.insert(1, "CP", cp)
    destino = DIR_EXCEL / f"estadisticas_{cp}_{fecha_hoy}.xlsx"
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Datos", index=False)
        resumen = dataframe.pivot(index=["CP", "Periodo"], columns="Métrica", values="Valor").reset_index()
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
    return destino


def iniciar_sesion(page, usuario, contrasena):
    page.goto("https://penotariado.com/inmobiliario/home", wait_until="domcontentloaded")
    page.get_by_role("button", name="Acceder").click()
    page.get_by_role("textbox", name="Correo electrónico").fill(usuario)
    page.get_by_role("textbox", name="Contraseña").fill(contrasena)
    page.get_by_role("button", name="Acceder").click()
    try:
        page.get_by_role("button", name="Aceptar").click(timeout=4_000)
    except Exception:
        pass
    page.wait_for_url(re.compile(r"penotariado\.com/inmobiliario"), timeout=10_000)


def consultar_cp(page, cp, fecha_hoy):
    """Consulta un CP, registra el resultado y nunca guarda datos provinciales."""
    try:
        page.goto("https://penotariado.com/inmobiliario/buscador-precio-vivienda", wait_until="domcontentloaded")
        frame = page.locator('iframe[title="map-container"]').content_frame
        if frame is None:
            raise RuntimeError("No se encontró el mapa de selección de ubicación.")
        buscador = frame.get_by_role("textbox", name="Buscar provincia, municipio o")
        buscador.fill(cp)
        frame.get_by_role("button", name=cp).click()
        frame.get_by_role("group", name="Tipo de construcción").get_by_test_id("dropdownBtn").click()
        frame.get_by_role("menuitemradio", name="Segunda mano").click()
        frame.get_by_role("combobox", name="Todos").click()
        frame.get_by_role("menuitemradio", name="Pisos").click()
        frame.get_by_role("button", name="Más estadísticas").click()
        try:
            page.get_by_role("button", name="Continuar").click(timeout=3_000)
        except Exception:
            pass

        if hay_datos_provinciales(page):
            registrar_descarga(cp, "sin_datos_cp", 0, "El portal muestra datos provinciales en lugar de datos del CP.")
            print(f" [SIN DATOS CP] {cp}: se omitieron los datos provinciales.")
            return

        with page.expect_download(timeout=10_000) as descarga:
            page.locator("menu").get_by_role("button", name="Descargar").click()
        pdf = DIR_PDF / f"informe_{cp}_{fecha_hoy}.pdf"
        descarga.value.save_as(pdf)

        configuracion = [
            ("Precio (€/m²)", lambda: page.get_by_role("button", name="Ver tabla").first.click()),
            ("Compraventas", lambda: (page.get_by_role("button", name="Número compraventas").click(), page.get_by_role("button", name="Ver tabla").click())),
            ("Importe medio (€)", lambda: (page.locator("button", has_text=re.compile(r"Importe medio", re.I)).click(), page.get_by_role("button", name="Ver tabla").click())),
        ]
        registros = []
        for metrica, accion in configuracion:
            accion()
            registros.extend(extraer_tabla(page, metrica))
        validar_metricas(registros)
        excel = guardar_excel(cp, fecha_hoy, registros)
        resultado = guardar_registros(cp, fecha_hoy, registros)
        registrar_descarga(cp, "completada", 1, f"PDF: {pdf.name}; Excel: {excel.name}; registros: {resultado['recibidos']}.")
        print(f" [COMPLETADA] {cp}: {resultado['insertados_o_actualizados']} registros insertados o actualizados.")
    except Exception as error:
        registrar_descarga(cp, "error", None, str(error))
        print(f" [ERROR] {cp}: {error}")


def run(playwright: Playwright) -> None:
    usuario, contrasena = obtener_credenciales()
    codigos = codigos_a_consultar(sys.argv[1:])
    DIR_PDF.mkdir(parents=True, exist_ok=True)
    DIR_EXCEL.mkdir(parents=True, exist_ok=True)
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    browser = playwright.chromium.launch(headless=False)
    try:
        page = browser.new_page()
        iniciar_sesion(page, usuario, contrasena)
        print(f"Iniciando {'prueba' if not EJECUTAR_TODOS_LOS_CP else 'ejecución completa'} con {len(codigos)} CP.")
        for cp in codigos:
            print(f"\n--- Procesando CP: {cp} ---")
            consultar_cp(page, cp, fecha_hoy)
    finally:
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
