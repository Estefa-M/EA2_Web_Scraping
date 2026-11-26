"""Orquestador del pipeline: extraer, validar, guardar y publicar.

Uso desde la raíz del repositorio:

    PYTHONPATH=src python -m ea3.pipeline                 # extrae y publica
    PYTHONPATH=src python -m ea3.pipeline --pages 3       # tres páginas
    PYTHONPATH=src python -m ea3.pipeline --desde-csv data/productos.csv
    PYTHONPATH=src python -m ea3.pipeline --check         # solo valida

Códigos de salida: 0 correcto, 2 datos que no pasan las reglas de calidad,
1 error inesperado. GitHub Actions usa esos códigos para detener el job.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

from . import report, transform
from .config import Settings, load_settings
from .scraper import ScrapeError, a_filas, scrape

logger = logging.getLogger("ea3")


def configurar_logging(settings: Settings, verbose: bool = False) -> None:
    """Envía el registro a la consola y a ``logs/pipeline.log``.

    En Actions interesa ver todo en el log del job; en local queda además
    una copia en el repositorio (ignorada por git) para revisar después.
    """
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    formato = "%(asctime)s [%(levelname)s] %(message)s"
    manejadores: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_path, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=formato,
        handlers=manejadores,
        force=True,
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def imprimir_resumen(metricas: dict, settings: Settings) -> None:
    """Resumen legible que aparece al final del job de Actions."""
    print("\n" + "=" * 62)
    print("RESUMEN DE LA EJECUCIÓN")
    print("=" * 62)
    print(f"Productos únicos .......... {metricas['total_productos']}")
    print(f"Marcas .................... {metricas['marcas_unicas']}")
    print(f"Precio mínimo ............. {report.pesos(metricas['precio_minimo'])}")
    print(f"Precio máximo ............. {report.pesos(metricas['precio_maximo'])}")
    print(f"Precio promedio ........... {report.pesos(metricas['precio_promedio'])}")
    print(f"Completitud de campos ..... {metricas['completitud_pct']:.2f} %")
    print(f"CSV ....................... {settings.csv_path}")
    print(f"Tablero ................... {settings.report_path}")
    print("=" * 62 + "\n")


def ejecutar(
    settings: Settings,
    desde_csv: Path | None = None,
    solo_validar: bool = False,
) -> int:
    """Corre el pipeline y devuelve el código de salida."""
    if desde_csv:
        logger.info("Leyendo datos existentes de %s", desde_csv)
        tabla = transform.limpiar(transform.leer_csv(desde_csv))
    elif solo_validar:
        if not settings.csv_path.exists():
            logger.error("No existe %s; ejecuta primero la extracción", settings.csv_path)
            return 2
        tabla = transform.limpiar(transform.leer_csv(settings.csv_path))
    else:
        logger.info("Extrayendo %s páginas de %s", settings.pages, settings.base_url)
        tabla = transform.limpiar(transform.a_dataframe(a_filas(scrape(settings))))

    problemas = transform.validar(tabla)
    if problemas:
        for problema in problemas:
            logger.error("Calidad: %s", problema)
        return 2

    metricas = transform.resumen(tabla)
    transform.guardar_csv(tabla, settings.csv_path)
    transform.guardar_metricas(metricas, settings.metricas_path)

    if not solo_validar:
        ruta = report.construir_tablero(tabla, metricas, settings)
        logger.info("Tablero generado en %s", ruta)

    imprimir_resumen(metricas, settings)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la línea de comandos."""
    parser = argparse.ArgumentParser(description="Pipeline de datos de Calzatodo (EA3)")
    parser.add_argument("--pages", type=int, help="número de páginas a recorrer")
    parser.add_argument(
        "--desde-csv",
        type=Path,
        help="no extrae: reprocesa un CSV ya guardado",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="solo valida los datos guardados (lo usa la integración continua)",
    )
    parser.add_argument("--verbose", action="store_true", help="registro detallado")
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.pages is not None:
        settings = replace(settings, pages=args.pages)

    configurar_logging(settings, verbose=args.verbose)

    try:
        return ejecutar(settings, desde_csv=args.desde_csv, solo_validar=args.check)
    except ScrapeError as error:
        logger.error("No se pudo completar la extracción: %s", error)
        return 1
    except Exception:  # noqa: BLE001 - el job debe mostrar la traza completa
        logger.exception("Error inesperado en el pipeline")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
