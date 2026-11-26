"""Pruebas de limpieza, reglas de calidad y métricas.

Construyen filas a mano: así se comprueba el comportamiento exacto de cada
regla sin depender de lo que el sitio publique ese día.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ea3 import transform


def fila(sku="1", nombre="Tenis de prueba", marca="Marca A", precio=100000, disponible="Disponible"):
    return {
        "Nombre": nombre,
        "Marca": marca,
        "SKU de referencia": sku,
        "Precio mínimo": precio,
        "Precio máximo": precio,
        "Moneda": "COP",
        "Disponible": disponible,
        "Categoría": "https://www.calzatodo.com.co/es/mujeres/tenis/deportivo",
        "URL": f"https://www.calzatodo.com.co/p/{sku}",
        "Fecha de extracción": "2026-11-26T10:00:00-05:00",
    }


def test_limpiar_elimina_duplicados_y_filas_sin_precio():
    tabla = transform.a_dataframe(
        [
            fila(sku="1", precio=100000),
            fila(sku="1", precio=999999),  # misma referencia: se conserva la primera
            fila(sku="2", precio=None),
            fila(sku="3", nombre="  Tenis   con   espacios  ", precio=150000),
        ]
    )

    limpia = transform.limpiar(tabla)

    assert len(limpia) == 2
    assert list(limpia["SKU de referencia"]) == ["1", "3"]
    assert limpia.loc[1, "Nombre"] == "Tenis con espacios"
    assert float(limpia.loc[0, "Precio mínimo"]) == 100000


def test_validar_acepta_un_conjunto_limpio():
    limpia = transform.limpiar(transform.a_dataframe([fila("1"), fila("2")]))

    assert transform.validar(limpia) == []


def test_validar_reporta_duplicados_y_precios_invalidos():
    tabla = transform.a_dataframe([fila("1", precio=100000), fila("1", precio=0)])

    problemas = "\n".join(transform.validar(tabla))

    assert "duplicadas" in problemas
    assert "precios menores o iguales a cero" in problemas


def test_validar_reporta_tabla_vacia():
    assert transform.validar(transform.a_dataframe([])) == [
        "La tabla está vacía: no hay productos para publicar"
    ]


def test_resumen_calcula_precios_y_completitud():
    limpia = transform.limpiar(
        transform.a_dataframe(
            [
                fila("1", marca="Marca A", precio=100000),
                fila("2", marca="Marca B", precio=200000),
                fila("3", marca="Marca A", precio=300000),
            ]
        )
    )

    metricas = transform.resumen(limpia)

    assert metricas["total_productos"] == 3
    assert metricas["marcas_unicas"] == 2
    assert metricas["precio_minimo"] == 100000
    assert metricas["precio_maximo"] == 300000
    assert metricas["precio_promedio"] == 200000
    assert metricas["precio_mediana"] == 200000
    assert metricas["completitud_pct"] == 100.0
    assert metricas["top_marcas"][0] == {"marca": "Marca A", "cantidad": 2}
    assert sum(rango["cantidad"] for rango in metricas["rangos_precio"]) == 3


def test_guardar_y_leer_csv_conserva_los_datos(tmp_path: Path):
    limpia = transform.limpiar(transform.a_dataframe([fila("1"), fila("2")]))
    ruta = tmp_path / "data" / "productos.csv"

    transform.guardar_csv(limpia, ruta)
    recuperada = transform.leer_csv(ruta)

    assert ruta.exists()
    assert len(recuperada) == 2
    assert list(recuperada.columns) == transform.COLUMNAS
    assert pd.api.types.is_numeric_dtype(recuperada["Precio mínimo"])
