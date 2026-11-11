import pandas as pd
from pathlib import Path

def procesar_excel(archivo):
    df = pd.read_excel(archivo)
    print(archivo)
    # 1. Cambiar nombres de campos
    df = df.rename(columns={"Fecha_Consulta": "Fecha", "Métrica": "Metrica"})

    # 2. Cambiar valores de Metrica
    df["Metrica"] = df["Metrica"].replace({
        "Precio (€/m²)": "precio_m2",
        "Compraventas": "compraventas",
        "Importe medio (€)": "precio"
    })
    
    # 3. Convertir Valor
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

    # Precio: 4.363 -> 4363
    df.loc[df["Metrica"] == "precio_m2", "Valor"] *= 1000

    # Importe medio: 450.000 -> 450000
    df.loc[df["Metrica"] == "precio", "Valor"] *= 1000

    # compraventas: 7.000 -> 7
    # No hacemos nada

    df["Valor"] = df["Valor"].round().astype("Int64")
    
    # 4. Pivotar
    df = df.pivot_table(
        index=["Fecha", "CP", "Periodo"],
        columns="Metrica",
        values="Valor",
        aggfunc="first"
    ).reset_index()

    df.columns.name = None

    # 5. Eliminar los dos últimos dígitos de Fecha
    df["Fecha"] = df["Fecha"].astype(str).str[:-2].astype(int)

    # 6. Separar Periodo en Mes y Año
    df[["Mes", "Año"]] = df["Periodo"].str.split(" ", expand=True)
    df["Año"] = df["Año"].astype(int)
    df = df.drop(columns="Periodo")

    # 7. Ordenar columnas
    return df[["Fecha", "CP", "Año", "Mes", "precio_m2", "compraventas", "precio"]]


# Carpeta donde están los Excel
carpeta = Path("descargas_excel")

# Buscar todos los Excel
archivos = list(carpeta.glob("*.xlsx"))

# Procesar todos los archivos
dfs = [procesar_excel(archivo) for archivo in archivos]

# Unir todos los DataFrames
df_final = pd.concat(dfs, ignore_index=True)

# Ordenar meses cronológicamente
df_final["Mes"] = pd.Categorical(
    df_final["Mes"],
    categories=["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
    ordered=True
)

# Ordenar por CP, Año y Mes
df_final = df_final.sort_values(["CP", "Año", "Mes"]).reset_index(drop=True)

# Guardar resultado
df_final.to_excel("resultado.xlsx", index=False)

print(f"Procesados {len(archivos)} archivos.")
print(f"Resultado guardado en: resultado.xlsx")

