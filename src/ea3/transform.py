"""Limpieza, validación y métricas del catálogo extraído.

El scraper entrega objetos ``Producto``; aquí se convierten en una tabla,
se descartan los registros inservibles y se calculan las cifras que
alimentan el tablero y el informe. Separar esta etapa permite probarla
sin internet: las pruebas construyen filas a mano y verifican las reglas.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

COLUMNAS = [
    "Nombre",
    "Marca",
    "SKU de referencia",
    "Precio mínimo",
    "Precio máximo",
    "Moneda",
    "Disponible",
    "Categoría",
    "URL",
    "Fecha de extracción",
]

RANGOS = [
    ("Menos de $150.000", 0, 150_000),
    ("$150.000 – $250.000", 150_000, 250_000),
    ("$250.000 – $350.000", 250_000, 350_000),
    ("$350.000 o más", 350_000, float("inf")),
]


def a_dataframe(filas: Iterable[dict]) -> pd.DataFrame:
    """Crea la tabla con las columnas del proyecto en el orden esperado."""
    tabla = pd.DataFrame(list(filas))
    for columna in COLUMNAS:
        if columna not in tabla.columns:
            tabla[columna] = None
    return tabla[COLUMNAS]


def limpiar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Normaliza textos, convierte precios y elimina duplicados.

    Reglas, en orden:
    1. Espacios repetidos y extremos fuera de los textos.
    2. Precios a número (lo que no se pueda convertir queda vacío).
    3. Se descartan filas sin nombre o sin precio: no sirven para el tablero.
    4. Se conserva la primera aparición de cada referencia.
    """
    limpia = tabla.copy()
    for columna in ["Nombre", "Marca", "SKU de referencia", "Moneda", "Disponible", "URL"]:
        limpia[columna] = (
            limpia[columna].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        )

    for columna in ["Precio mínimo", "Precio máximo"]:
        limpia[columna] = pd.to_numeric(limpia[columna], errors="coerce")

    limpia = limpia.dropna(subset=["Precio mínimo"])
    limpia = limpia[limpia["Nombre"] != ""]
    limpia = limpia.drop_duplicates(subset=["SKU de referencia"], keep="first")
    return limpia.reset_index(drop=True)


def validar(tabla: pd.DataFrame) -> list[str]:
    """Devuelve la lista de problemas de calidad; vacía significa apto.

    Estas reglas son las que el workflow de integración continua ejecuta
    con ``python -m ea3.pipeline --check``: si alguna falla, el job se
    detiene y no se publica un tablero con datos rotos.
    """
    problemas: list[str] = []

    if tabla.empty:
        return ["La tabla está vacía: no hay productos para publicar"]

    faltantes = [columna for columna in COLUMNAS if columna not in tabla.columns]
    if faltantes:
        problemas.append(f"Faltan columnas obligatorias: {', '.join(faltantes)}")

    duplicados = int(tabla["SKU de referencia"].duplicated().sum())
    if duplicados:
        problemas.append(f"Hay {duplicados} referencias duplicadas")

    sin_precio = int(tabla["Precio mínimo"].isna().sum())
    if sin_precio:
        problemas.append(f"Hay {sin_precio} productos sin precio")

    precios_invalidos = int((tabla["Precio mínimo"].fillna(0) <= 0).sum())
    if precios_invalidos:
        problemas.append(f"Hay {precios_invalidos} precios menores o iguales a cero")

    completitud = tabla[COLUMNAS].notna().sum().sum() / (len(tabla) * len(COLUMNAS))
    if completitud < 0.90:
        problemas.append(f"La completitud de campos es {completitud:.0%}, por debajo del 90%")

    return problemas


def _pesos(valor: float | None) -> int:
    """Redondea a pesos colombianos (sin centavos)."""
    return int(round(float(valor))) if valor is not None else 0


def resumen(tabla: pd.DataFrame) -> dict:
    """Calcula las cifras del tablero y del informe.

    Todas salen de la tabla limpia, nunca de valores escritos a mano: si
    mañana cambia el catálogo, el documento y el tablero cambian con él.
    """
    precios = tabla["Precio mínimo"].dropna()
    marcas = tabla["Marca"].value_counts()
    total = int(len(tabla))
    celdas = total * len(COLUMNAS)
    completas = int(tabla[COLUMNAS].notna().sum().sum())

    rangos = []
    for etiqueta, desde, hasta in RANGOS:
        cantidad = int(((precios >= desde) & (precios < hasta)).sum())
        rangos.append({"rango": etiqueta, "cantidad": cantidad})

    return {
        "total_productos": total,
        "marcas_unicas": int(tabla["Marca"].nunique()),
        "precio_minimo": _pesos(precios.min()) if not precios.empty else 0,
        "precio_maximo": _pesos(precios.max()) if not precios.empty else 0,
        "precio_promedio": _pesos(precios.mean()) if not precios.empty else 0,
        "precio_mediana": _pesos(precios.median()) if not precios.empty else 0,
        "disponibles": int((tabla["Disponible"] == "Disponible").sum()),
        "completitud_pct": round(completas / celdas * 100, 2) if celdas else 0.0,
        "top_marcas": [
            {"marca": str(marca), "cantidad": int(cantidad)}
            for marca, cantidad in marcas.head(8).items()
        ],
        "rangos_precio": rangos,
        "fecha_extraccion": str(tabla["Fecha de extracción"].iloc[0]) if total else "",
        "categoria": str(tabla["Categoría"].iloc[0]) if total else "",
    }


def guardar_csv(tabla: pd.DataFrame, ruta: Path) -> Path:
    """Escribe el CSV con el formato de las entregas anteriores.

    ``utf-8-sig`` y punto y coma: Excel en español abre el archivo con las
    tildes correctas y sin tener que importar nada.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    salida = tabla.copy()
    # Precios enteros sin ".0": el CSV queda legible al abrirlo en Excel.
    for columna in ["Precio mínimo", "Precio máximo"]:
        serie = salida[columna]
        if serie.notna().all() and (serie % 1 == 0).all():
            salida[columna] = serie.astype("Int64")
    salida.to_csv(ruta, index=False, encoding="utf-8-sig", sep=";")
    return ruta


def leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee el CSV del proyecto (detecta el separador y el BOM)."""
    return pd.read_csv(ruta, sep=";", encoding="utf-8-sig")


def guardar_metricas(metricas: dict, ruta: Path) -> Path:
    """Guarda las cifras en JSON para que el informe las consuma."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
