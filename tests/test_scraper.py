"""Pruebas del extractor: lectura del JSON-LD, precios, reintentos y deduplicación.

Ninguna prueba de este archivo sale a internet: usan el recorte guardado en
``tests/fixtures`` y sesiones falsas. La prueba marcada ``integracion`` sí
consulta el sitio real y solo corre cuando se pide con ``EA3_LIVE=1``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ea3 import scraper
from ea3.config import Settings

FIXTURE = Path(__file__).parent / "fixtures" / "calzatodo_pagina.html"


def leer_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parsea_las_tres_publicaciones_del_itemlist():
    productos = scraper.parsear_item_list(leer_fixture(), categoria="tenis mujer")

    assert len(productos) == 3
    primero = productos[0]
    assert primero.sku == "461841"
    assert "Skechers" in primero.nombre
    assert primero.marca == "Skechers"
    assert primero.precio_minimo == 239920
    assert primero.precio_maximo == 239920
    assert primero.moneda == "COP"
    assert primero.categoria == "tenis mujer"
    assert primero.url.startswith("https://www.calzatodo.com.co/")


def test_ignora_breadcrumb_y_json_roto():
    # El fixture incluye un BreadcrumbList y un bloque JSON inválido a propósito.
    productos = scraper.parsear_item_list(leer_fixture())

    assert len(productos) == 3
    assert all(producto.nombre for producto in productos)


def test_pagina_sin_itemlist_devuelve_lista_vacia():
    assert scraper.parsear_item_list("<html><body><p>Sin metadatos</p></body></html>") == []


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (239920, 239920.0),
        ("239920", 239920.0),
        ("$ 239.920", 239920.0),
        ("239.920,00", 239920.0),
        (None, None),
        ("", None),
        ("no disponible", None),
    ],
)
def test_conversion_de_precios(entrada, esperado):
    assert scraper._precio(entrada) == esperado


class RespuestaFalsa:
    """Imita lo mínimo de ``requests.Response`` que usa el scraper."""

    def __init__(self, status_code: int, texto: str = "<html>ok</html>"):
        self.status_code = status_code
        self.text = texto
        self.content = texto.encode()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise scraper.requests.HTTPError(f"HTTP {self.status_code}")


class SesionFalsa:
    """Devuelve una secuencia de respuestas y cuenta las llamadas."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = 0

    def get(self, *args, **kwargs):
        self.llamadas += 1
        return self.respuestas.pop(0)


def ajustes(tmp_path: Path, **cambios) -> Settings:
    base = Settings(
        data_dir=tmp_path / "data",
        report_dir=tmp_path / "report",
        log_dir=tmp_path / "logs",
        delay=0.0,
        retries=3,
    )
    return base if not cambios else Settings(**{**base.__dict__, **cambios})


def test_reintenta_cuando_el_servidor_falla(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper.time, "sleep", lambda *_: None)
    sesion = SesionFalsa([RespuestaFalsa(500), RespuestaFalsa(503), RespuestaFalsa(200, "<html>bien</html>")])

    html = scraper.descargar_pagina(sesion, ajustes(tmp_path), pagina=1)

    assert html == "<html>bien</html>"
    assert sesion.llamadas == 3


def test_falla_tras_agotar_reintentos(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper.time, "sleep", lambda *_: None)
    sesion = SesionFalsa([RespuestaFalsa(500) for _ in range(3)])

    with pytest.raises(scraper.ScrapeError):
        scraper.descargar_pagina(sesion, ajustes(tmp_path), pagina=2)
    assert sesion.llamadas == 3


def test_scrape_no_repite_referencias_entre_paginas(monkeypatch, tmp_path):
    html = leer_fixture()
    monkeypatch.setattr(scraper, "descargar_pagina", lambda sesion, settings, pagina: html)
    monkeypatch.setattr(scraper.time, "sleep", lambda *_: None)

    productos = scraper.scrape(ajustes(tmp_path, pages=2))

    assert len(productos) == 3  # las mismas tres publicaciones en dos páginas
    assert len({producto.sku for producto in productos}) == 3


@pytest.mark.integracion
@pytest.mark.skipif(os.environ.get("EA3_LIVE") != "1", reason="consulta el sitio real")
def test_extraccion_real(tmp_path):
    productos = scraper.scrape(ajustes(tmp_path, pages=1))

    assert len(productos) >= 10
    assert all(producto.precio_minimo and producto.precio_minimo > 0 for producto in productos)
