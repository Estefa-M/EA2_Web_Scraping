"""Pruebas del tablero: que se genere, que muestre los datos y que no queden marcas de plantilla."""

from __future__ import annotations

from pathlib import Path

from ea3 import report, transform
from ea3.config import Settings


def preparar(tmp_path: Path):
    filas = [
        {
            "Nombre": "Tenis Deportivo de Mujer Skechers 117863wlv",
            "Marca": "Skechers",
            "SKU de referencia": "461841",
            "Precio mínimo": 239920,
            "Precio máximo": 239920,
            "Moneda": "COP",
            "Disponible": "Disponible",
            "Categoría": "https://www.calzatodo.com.co/es/mujeres/tenis/deportivo",
            "URL": "https://www.calzatodo.com.co/tenis-117863wlv/p",
            "Fecha de extracción": "2026-11-26T10:00:00-05:00",
        },
        {
            "Nombre": "Tenis Deportivo de Mujer Throwing aa5133w",
            "Marca": "Throwing",
            "SKU de referencia": "451565",
            "Precio mínimo": 111920,
            "Precio máximo": 139900,
            "Moneda": "COP",
            "Disponible": "Agotado",
            "Categoría": "https://www.calzatodo.com.co/es/mujeres/tenis/deportivo",
            "URL": "https://www.calzatodo.com.co/tenis-aa5133w/p",
            "Fecha de extracción": "2026-11-26T10:00:00-05:00",
        },
    ]
    tabla = transform.limpiar(transform.a_dataframe(filas))
    settings = Settings(
        data_dir=tmp_path / "data",
        report_dir=tmp_path / "report",
        log_dir=tmp_path / "logs",
    )
    return tabla, transform.resumen(tabla), settings


def test_genera_el_html_con_productos_y_cifras(tmp_path):
    tabla, metricas, settings = preparar(tmp_path)

    ruta = report.construir_tablero(tabla, metricas, settings)
    html = ruta.read_text(encoding="utf-8")

    assert ruta == settings.report_path
    assert ruta.exists()
    assert "Observatorio de precios" in html
    assert "Tenis Deportivo de Mujer Skechers 117863wlv" in html
    assert "$ 239.920" in html
    assert "Agotado" in html
    assert "{{" not in html and "{%" not in html


def test_formato_de_pesos():
    assert report.pesos(239920) == "$ 239.920"
    assert report.pesos("111920") == "$ 111.920"
    assert report.pesos(None) == "—"
