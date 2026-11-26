"""Genera el tablero HTML que se publica como aplicación web.

El tablero es un archivo estático: no necesita servidor ni base de datos.
Se construye a partir del CSV y las métricas de la ejecución, y GitHub
Pages lo sirve en una URL pública. Esa es la "aplicación web simple" que
pide la Evidencia 3 y la que se enlaza desde el informe.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Settings

BOGOTA = ZoneInfo("America/Bogota")
PLANTILLA = Path(__file__).resolve().parent / "templates" / "tablero.html.j2"


def pesos(valor) -> str:
    """Formatea un número como pesos colombianos: ``$ 239.920``."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return "—"
    return "$ " + f"{numero:,.0f}".replace(",", ".")


def _filas(tabla: pd.DataFrame) -> list[dict]:
    """Prepara los registros que consume la tabla del tablero."""
    filas = []
    for _, fila in tabla.iterrows():
        minimo = fila["Precio mínimo"]
        maximo = fila["Precio máximo"]
        rango = pesos(minimo)
        if pd.notna(maximo) and pd.notna(minimo) and maximo > minimo:
            rango = f"{pesos(minimo)} – {pesos(maximo)}"
        filas.append(
            {
                "nombre": str(fila["Nombre"]),
                "marca": str(fila["Marca"]),
                "sku": str(fila["SKU de referencia"]),
                "precio": rango,
                "precio_numero": float(minimo) if pd.notna(minimo) else 0.0,
                "disponible": str(fila["Disponible"]),
                "url": str(fila["URL"]),
            }
        )
    return filas


def construir_tablero(
    tabla: pd.DataFrame, metricas: dict, settings: Settings
) -> Path:
    """Renderiza ``report/index.html`` y devuelve la ruta del archivo."""
    entorno = Environment(
        loader=FileSystemLoader(str(PLANTILLA.parent)),
        autoescape=select_autoescape(["html"]),
    )
    entorno.filters["pesos"] = pesos
    plantilla = entorno.get_template(PLANTILLA.name)

    html = plantilla.render(
        generado=datetime.now(BOGOTA).strftime("%d/%m/%Y %I:%M %p"),
        vigencia=settings.vigencia_hasta,
        repo_url=settings.repo_url,
        fuente=settings.base_url,
        metricas=metricas,
        productos=_filas(tabla),
    )
    settings.report_path.parent.mkdir(parents=True, exist_ok=True)
    settings.report_path.write_text(html, encoding="utf-8")
    return settings.report_path
