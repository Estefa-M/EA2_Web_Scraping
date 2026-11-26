"""Configuración central del proyecto.

Todo lo que cambia entre entornos (la URL que se extrae, cuántas páginas,
la pausa entre peticiones, dónde se guardan los archivos) se lee de
variables de entorno con un valor por defecto. Así el mismo código corre
igual en el portátil, en Google Colab y en GitHub Actions, sin rutas
absolutas ni secretos escritos en el repositorio.

Variables reconocidas (ver ``.env.example`` y el README):

=========================  ========================================  ============================
Variable                   Para qué sirve                           Valor por defecto
=========================  ========================================  ============================
``EA3_BASE_URL``           Categoría del sitio que se extrae         tenis deportivo para mujer
``EA3_PAGES``              Cuántas páginas se recorren               2
``EA3_DELAY_SEG``          Pausa entre peticiones (cortesía)         2.0
``EA3_TIMEOUT_SEG``        Tiempo máximo por petición                30
``EA3_REINTENTOS``         Reintentos por página                     3
``EA3_USER_AGENT``         Identificación del cliente HTTP           navegador de escritorio
``EA3_VIGENCIA_HASTA``     Último día de la ejecución programada     2026-12-09
``EA3_REPO_URL``           Enlace que muestra el tablero             github.com/Estefa-M/EA2_Web_Scraping
=========================  ========================================  ============================
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# config.py vive en <raiz>/src/ea3/config.py, por eso se suben tres niveles.
RAIZ = Path(__file__).resolve().parents[2]

URL_CATEGORIA = "https://www.calzatodo.com.co/es/mujeres/tenis/deportivo"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REPO_URL = "https://github.com/Estefa-M/EA2_Web_Scraping"


def _entero(nombre: str, defecto: int) -> int:
    """Lee un entero del entorno y falla con un mensaje claro si no sirve."""
    crudo = os.environ.get(nombre)
    if crudo is None or crudo.strip() == "":
        return defecto
    try:
        return int(crudo)
    except ValueError as error:
        raise ValueError(f"{nombre} debe ser un entero, llegó {crudo!r}") from error


def _decimal(nombre: str, defecto: float) -> float:
    """Lee un decimal del entorno (acepta coma o punto)."""
    crudo = os.environ.get(nombre)
    if crudo is None or crudo.strip() == "":
        return defecto
    try:
        return float(crudo.replace(",", "."))
    except ValueError as error:
        raise ValueError(f"{nombre} debe ser un número, llegó {crudo!r}") from error


@dataclass(frozen=True)
class Settings:
    """Parámetros de una ejecución del pipeline."""

    base_url: str = URL_CATEGORIA
    pages: int = 2
    delay: float = 2.0
    timeout: int = 30
    retries: int = 3
    user_agent: str = USER_AGENT
    vigencia_hasta: str = "2026-12-09"
    repo_url: str = REPO_URL
    data_dir: Path = RAIZ / "data"
    report_dir: Path = RAIZ / "report"
    log_dir: Path = RAIZ / "logs"

    # Rutas derivadas: se calculan solas para no repetirlas en cada archivo.
    @property
    def csv_path(self) -> Path:
        return self.data_dir / "productos.csv"

    @property
    def metricas_path(self) -> Path:
        return self.data_dir / "metricas.json"

    @property
    def report_path(self) -> Path:
        return self.report_dir / "index.html"

    @property
    def log_path(self) -> Path:
        return self.log_dir / "pipeline.log"


def load_settings(base_dir: Path | None = None) -> Settings:
    """Construye la configuración leyendo el entorno.

    ``base_dir`` permite apuntar a otra carpeta; las pruebas lo usan para
    escribir en un directorio temporal y no ensuciar el repositorio.
    """
    base = Path(base_dir) if base_dir else RAIZ
    return Settings(
        base_url=os.environ.get("EA3_BASE_URL") or URL_CATEGORIA,
        pages=_entero("EA3_PAGES", 2),
        delay=_decimal("EA3_DELAY_SEG", 2.0),
        timeout=_entero("EA3_TIMEOUT_SEG", 30),
        retries=_entero("EA3_REINTENTOS", 3),
        user_agent=os.environ.get("EA3_USER_AGENT") or USER_AGENT,
        vigencia_hasta=os.environ.get("EA3_VIGENCIA_HASTA") or "2026-12-09",
        repo_url=os.environ.get("EA3_REPO_URL") or REPO_URL,
        data_dir=Path(os.environ.get("EA3_DATA_DIR") or base / "data"),
        report_dir=Path(os.environ.get("EA3_REPORT_DIR") or base / "report"),
        log_dir=Path(os.environ.get("EA3_LOG_DIR") or base / "logs"),
    )
