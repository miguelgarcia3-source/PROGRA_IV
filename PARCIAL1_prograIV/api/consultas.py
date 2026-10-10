from pathlib import Path
import math
import re
import pandas as pd

ARCHIVO_PREDETERMINADO = Path(__file__).resolve().parent.parent / "resultado_laboratorio_suelo.xlsx"

COLUMNAS = {
    "departamento": "Departamento",
    "municipio": "Municipio",
    "cultivo": "Cultivo",
    "topografia": "Topografia",
    "ph": "pH agua:suelo 2,5:1,0",
    "fosforo": "Fósforo (P) Bray II mg/kg",
    "potasio": "Potasio (K) intercambiable cmol(+)/kg",
}

# Límites amplios para detectar valores numéricos evidentemente mal escalados
# en algunas celdas del archivo de origen.
RANGOS_PLAUSIBLES = {
    "ph": (0.0, 14.0),
    "fosforo": (0.0, 10000.0),
    "potasio": (0.0, 1000.0),
}


def cargar_datos(ruta=ARCHIVO_PREDETERMINADO):
    """Lee el Excel y valida que existan las columnas necesarias."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de datos: {ruta}\n"
            "Coloque resultado_laboratorio_suelo.xlsx en la carpeta principal del proyecto."
        )
    try:
        datos = pd.read_excel(ruta)
    except Exception as error:
        raise RuntimeError(f"No fue posible leer el archivo Excel: {error}") from error

    faltantes = [col for col in COLUMNAS.values() if col not in datos.columns]
    if faltantes:
        raise ValueError("El Excel no contiene estas columnas requeridas: " + ", ".join(faltantes))

    for campo in ("departamento", "municipio", "cultivo", "topografia"):
        columna = COLUMNAS[campo]
        datos[columna] = datos[columna].fillna("").astype(str).str.strip()
    return datos


def _numero(valor, campo):
    """Convierte valores numéricos y marcas como ND o <3,87 a un número usable."""
    if pd.isna(valor):
        return math.nan
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        numero = float(valor)
    else:
        texto = str(valor).strip().replace(" ", "")
        if not texto or texto.upper() in {"ND", "N.D.", "NA", "N/A", "-", "NO INDICA"}:
            return math.nan
        # Para valores como "<3,87", se usa el límite numérico 3.87 como aproximación.
        texto = texto.replace(",", ".")
        texto = re.sub(r"^[<>]=?", "", texto)
        try:
            numero = float(texto)
        except ValueError:
            return math.nan

    if not math.isfinite(numero):
        return math.nan

    # El Excel suministrado contiene algunas celdas numéricas con escalas
    # evidentemente anómalas. Se intenta corregir solo si el valor está fuera
    # del rango amplio y existe una escala decimal que lo lleve al rango.
    minimo, maximo = RANGOS_PLAUSIBLES[campo]
    if numero < minimo or numero > maximo:
        candidatos = []
        for decimales in range(1, 18):
            candidato = numero / (10 ** decimales)
            if minimo <= candidato <= maximo:
                candidatos.append(candidato)
        if candidatos:
            # Se escoge el candidato más cercano al límite superior del rango
            # en escala logarítmica, evitando dejar valores claramente imposibles.
            objetivo = {"ph": 7.0, "fosforo": 100.0, "potasio": 1.0}[campo]
            numero = min(candidatos, key=lambda x: abs(math.log10(max(x, 1e-12)) - math.log10(objetivo)))
        else:
            return math.nan
    return numero


def _normalizar_texto(valor):
    return str(valor).strip().casefold()


def obtener_opciones(datos, campo, departamento=None, municipio=None):
    """Devuelve valores únicos ordenados para facilitar la consulta."""
    columna = COLUMNAS[campo]
    filtrados = datos
    if departamento:
        filtrados = filtrados[filtrados[COLUMNAS["departamento"]].map(_normalizar_texto)
                              == _normalizar_texto(departamento)]
    if municipio:
        filtrados = filtrados[filtrados[COLUMNAS["municipio"]].map(_normalizar_texto)
                              == _normalizar_texto(municipio)]
    return sorted(v for v in filtrados[columna].dropna().astype(str).str.strip().unique() if v)


def consultar(datos, departamento, municipio, cultivo, cantidad):
    """Filtra por ubicación/cultivo y calcula medianas sobre los primeros N registros."""
    if cantidad < 1:
        raise ValueError("El número de registros debe ser mayor que cero.")

    df = datos.copy()
    filtros = [
        ("departamento", departamento),
        ("municipio", municipio),
        ("cultivo", cultivo),
    ]
    for campo, valor in filtros:
        columna = COLUMNAS[campo]
        df = df[df[columna].map(_normalizar_texto) == _normalizar_texto(valor)]

    if df.empty:
        return df, None

    seleccion = df.head(cantidad).copy()
    medianas = {}
    for campo in ("ph", "fosforo", "potasio"):
        columna = COLUMNAS[campo]
        numeros = seleccion[columna].map(lambda v: _numero(v, campo)).dropna()
        medianas[campo] = float(numeros.median()) if not numeros.empty else None
    return seleccion, medianas


def formatear_numero(valor):
    if valor is None or pd.isna(valor):
        return "Sin datos numéricos"
    return f"{valor:.3f}".rstrip("0").rstrip(".")
