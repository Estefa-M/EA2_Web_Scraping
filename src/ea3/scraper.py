"""Extracción de las publicaciones de una categoría de Calzatodo.

El sitio publica, dentro del HTML, un bloque ``<script type="application/ld+json">``
con un objeto ``ItemList``: un arreglo ordenado de productos con su marca,
referencia y precios. Ese bloque es la fuente del proyecto; no se raspan
clases CSS ni textos sueltos, de modo que un cambio de diseño no rompe el
scraper mientras el sitio siga publicando metadatos estructurados.

Cómo se usa:

    from ea3.config import load_settings
    from ea3.scraper import scrape

    productos = scrape(load_settings())

Las peticiones se hacen con pausas, se reintentan con espera creciente y
se audita el código HTTP de cada página (200, 404, 5xx, fallo de red), que
es justo lo que el profesor mostró en la clase de la semana 8.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from .config import Settings

logger = logging.getLogger(__name__)
BOGOTA = ZoneInfo("America/Bogota")


class ScrapeError(RuntimeError):
    """La extracción no produjo datos utilizables."""


@dataclass
class Producto:
    """Una publicación del catálogo, ya normalizada.

    Los nombres de los campos coinciden con las columnas del CSV de la
    Evidencia 2 para que la serie de entregas sea comparable.
    """

    nombre: str
    marca: str
    sku: str
    precio_minimo: float | None
    precio_maximo: float | None
    moneda: str
    disponible: str
    categoria: str
    url: str
    fecha_extraccion: str = field(
        default_factory=lambda: datetime.now(BOGOTA).isoformat(timespec="seconds")
    )

    def a_fila(self) -> dict:
        """Devuelve el registro con los encabezados que usa el proyecto."""
        return {
            "Nombre": self.nombre,
            "Marca": self.marca,
            "SKU de referencia": self.sku,
            "Precio mínimo": self.precio_minimo,
            "Precio máximo": self.precio_maximo,
            "Moneda": self.moneda,
            "Disponible": self.disponible,
            "Categoría": self.categoria,
            "URL": self.url,
            "Fecha de extracción": self.fecha_extraccion,
        }


def _precio(valor) -> float | None:
    """Convierte el precio que llega del JSON-LD a número.

    El sitio entrega enteros (``239920``), pero se toleran textos como
    ``"$ 239.920"`` o ``"239,920.00"`` por si cambia la representación.
    """
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    limpio = str(valor).replace("$", "").replace("COP", "").strip()
    # Si el último separador es la coma, el formato es 239.920,00.
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    else:
        limpio = limpio.replace(".", "").replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None


def _texto(valor) -> str:
    """Normaliza espacios y convierte ``None`` en cadena vacía."""
    return " ".join(str(valor or "").split())


def _disponibilidad(item: dict) -> str:
    """Resume si el producto tiene al menos una talla disponible."""
    ofertas = (item.get("offers") or {}).get("offers") or []
    estados = {str(o.get("availability", "")) for o in ofertas}
    if not estados:
        return "No informado"
    if any("InStock" in estado for estado in estados):
        return "Disponible"
    if any("OutOfStock" in estado for estado in estados):
        return "Agotado"
    return "No informado"


def parsear_item_list(html: str, categoria: str = "") -> list[Producto]:
    """Extrae los productos del bloque ``ItemList`` de una página.

    Se ignoran los demás bloques JSON-LD (el sitio también publica un
    ``BreadcrumbList``), y si no hay ``ItemList`` se devuelve una lista
    vacía: quien llama decide si eso es un error o el final del catálogo.
    """
    soup = BeautifulSoup(html, "html.parser")
    productos: list[Producto] = []

    for bloque in soup.find_all("script", type="application/ld+json"):
        crudo = bloque.string or bloque.get_text()
        try:
            datos = json.loads(crudo)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Bloque JSON-LD ilegible, se omite")
            continue
        if not isinstance(datos, dict) or datos.get("@type") != "ItemList":
            continue

        for elemento in datos.get("itemListElement") or []:
            item = (elemento or {}).get("item") or {}
            nombre = _texto(item.get("name"))
            sku = _texto(item.get("sku") or item.get("mpn"))
            if not nombre or not sku:
                logger.debug("Publicación sin nombre o referencia: %s", elemento)
                continue

            ofertas = item.get("offers") or {}
            minimo = _precio(ofertas.get("lowPrice"))
            maximo = _precio(ofertas.get("highPrice"))
            if minimo is None:
                precios: list[float] = []
                for oferta in ofertas.get("offers") or []:
                    precio = _precio(oferta.get("price"))
                    if precio is not None:
                        precios.append(precio)
                if precios:
                    minimo, maximo = min(precios), max(precios)

            marca = item.get("brand")
            marca = _texto(marca.get("name")) if isinstance(marca, dict) else _texto(marca)

            productos.append(
                Producto(
                    nombre=nombre,
                    marca=marca or "Sin marca",
                    sku=sku,
                    precio_minimo=minimo,
                    precio_maximo=maximo if maximo is not None else minimo,
                    moneda=_texto(ofertas.get("priceCurrency")) or "COP",
                    disponible=_disponibilidad(item),
                    categoria=categoria,
                    url=_texto(item.get("@id")),
                )
            )
    return productos


def _sesion(settings: Settings) -> requests.Session:
    """Sesión HTTP con el User-Agent configurado."""
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": settings.user_agent})
    return sesion


def descargar_pagina(
    sesion: requests.Session, settings: Settings, pagina: int
) -> str:
    """Descarga una página del catálogo, con reintentos y espera creciente.

    La espera entre intentos es 1, 2 y 4 segundos: si el sitio responde 429
    o 5xx se le da tiempo en vez de martillarlo. Los errores 4xx distintos
    de 429 no se reintentan porque no van a cambiar solos.
    """
    for intento in range(1, settings.retries + 1):
        try:
            respuesta = sesion.get(
                settings.base_url,
                params={"page": pagina},
                timeout=settings.timeout,
            )
            if respuesta.status_code == 200:
                logger.info("HTTP 200 página %s (%s caracteres)", pagina, len(respuesta.content))
                return respuesta.text
            logger.warning("HTTP %s en página %s (intento %s)", respuesta.status_code, pagina, intento)
            if respuesta.status_code < 500 and respuesta.status_code != 429:
                respuesta.raise_for_status()
        except requests.RequestException as error:
            logger.warning("Fallo de red en página %s (intento %s): %s", pagina, intento, error)

        if intento < settings.retries:
            time.sleep(2 ** (intento - 1))

    raise ScrapeError(
        f"No se pudo descargar la página {pagina} después de {settings.retries} intentos"
    )


def scrape(settings: Settings | None = None) -> list[Producto]:
    """Recorre las páginas configuradas y devuelve los productos sin repetir.

    La deduplicación se hace por referencia (SKU): el mismo producto puede
    aparecer en dos páginas cuando el catálogo se reordena entre peticiones.
    """
    from .config import load_settings

    settings = settings or load_settings()
    sesion = _sesion(settings)
    productos: list[Producto] = []
    vistos: set[str] = set()

    for pagina in range(1, settings.pages + 1):
        html = descargar_pagina(sesion, settings, pagina)
        encontrados = parsear_item_list(html, categoria=settings.base_url)
        logger.info("Página %s: %s publicaciones", pagina, len(encontrados))
        for producto in encontrados:
            if producto.sku in vistos:
                logger.debug("Referencia repetida, se omite: %s", producto.sku)
                continue
            vistos.add(producto.sku)
            productos.append(producto)
        if pagina < settings.pages:
            time.sleep(settings.delay)

    if not productos:
        raise ScrapeError("La extracción terminó sin productos; revisa la URL o el bloque ItemList")

    logger.info("Extracción terminada: %s productos únicos de %s páginas", len(productos), settings.pages)
    return productos


def a_filas(productos: Iterable[Producto]) -> list[dict]:
    """Convierte los productos en filas listas para el DataFrame."""
    return [producto.a_fila() for producto in productos]


def a_dicts(productos: Iterable[Producto]) -> list[dict]:
    """Representación completa (útil para depurar o serializar)."""
    return [asdict(producto) for producto in productos]
