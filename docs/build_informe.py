"""Genera el informe de la Evidencia 3 en Word y lo exporta a PDF.

Uso:
    python docs/build_informe.py

Las cifras se leen de ``data/metricas.json`` y ``data/productos.csv`` (las
produce el pipeline), no se escriben a mano. Las capturas se toman de
``docs/capturas``; si falta alguna, el informe lo advierte en el anexo en
lugar de insertar una imagen vacía.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
CAPTURAS = DOCS / "capturas"
BOGOTA = ZoneInfo("America/Bogota")
NOMBRE = "Osorio_Carlos_Actividad_EA3"

AZUL = RGBColor(0x1D, 0x3F, 0x6B)
GRIS = RGBColor(0x5B, 0x67, 0x76)


def pesos(valor) -> str:
    return "$ " + f"{float(valor):,.0f}".replace(",", ".")


def cargar_datos():
    metricas = json.loads((RAIZ / "data" / "metricas.json").read_text(encoding="utf-8"))
    tabla = pd.read_csv(RAIZ / "data" / "productos.csv", sep=";", encoding="utf-8-sig")
    por_marca = (
        tabla.groupby("Marca")
        .agg(
            publicaciones=("SKU de referencia", "count"),
            promedio=("Precio mínimo", "mean"),
            minimo=("Precio mínimo", "min"),
            maximo=("Precio máximo", "max"),
        )
        .sort_values("publicaciones", ascending=False)
    )
    return metricas, tabla, por_marca


def configurar_estilos(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for nombre, tamano in [("Heading 1", 16), ("Heading 2", 13), ("Title", 26)]:
        estilo = doc.styles[nombre]
        estilo.font.name = "Calibri"
        estilo.font.size = Pt(tamano)
        estilo.font.color.rgb = AZUL
        estilo.font.bold = True


def pie_de_pagina(doc: Document, texto: str) -> None:
    """Pie con el nombre del curso y el número de página."""
    for seccion in doc.sections:
        parrafo = seccion.footer.paragraphs[0]
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        corrida = parrafo.add_run(texto + "  ·  Página ")
        corrida.font.size = Pt(8)
        corrida.font.color.rgb = GRIS
        campo = OxmlElement("w:fldSimple")
        campo.set(qn("w:instr"), "PAGE")
        parrafo._p.append(campo)


def parrafo(doc: Document, texto: str, cursiva: bool = False, tamano: int = 11) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    corrida = p.add_run(texto)
    corrida.italic = cursiva
    corrida.font.size = Pt(tamano)


def vineta(doc: Document, texto: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.add_run(texto)


def tabla(doc: Document, encabezados: list[str], filas: list[list[str]], anchos: list[float] | None = None) -> None:
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, titulo in enumerate(encabezados):
        celda = t.rows[0].cells[i]
        celda.text = ""
        run = celda.paragraphs[0].add_run(titulo)
        run.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombra = OxmlElement("w:shd")
        sombra.set(qn("w:fill"), "1D3F6B")
        celda._tc.get_or_add_tcPr().append(sombra)
    # Encabezado repetido cuando la tabla ocupa más de una página.
    cabecera = OxmlElement("w:tblHeader")
    cabecera.set(qn("w:val"), "true")
    t.rows[0]._tr.get_or_add_trPr().append(cabecera)
    for fila in filas:
        nueva = t.add_row()
        # Una fila no se parte entre dos páginas.
        sin_corte = OxmlElement("w:cantSplit")
        nueva._tr.get_or_add_trPr().append(sin_corte)
        celdas = nueva.cells
        for i, valor in enumerate(fila):
            celdas[i].text = ""
            run = celdas[i].paragraphs[0].add_run(str(valor))
            run.font.size = Pt(9.5)
    if anchos:
        for fila in t.rows:
            for i, ancho in enumerate(anchos):
                fila.cells[i].width = Cm(ancho)
    doc.add_paragraph()


def figura(doc: Document, ruta: Path, leyenda: str, ancho: float = 16.0) -> bool:
    if not ruta.exists():
        return False
    doc.add_picture(str(ruta), width=Cm(ancho))
    imagen = doc.paragraphs[-1]
    imagen.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # La imagen y su leyenda viajan juntas: si no cabe, ambas pasan de página.
    imagen.paragraph_format.keep_with_next = True
    imagen.paragraph_format.keep_together = True
    caption = doc.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.keep_together = True
    run = caption.add_run(leyenda)
    run.italic = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = GRIS
    return True


def bloque_codigo(doc: Document, texto: str) -> None:
    for linea in texto.strip("\n").splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(linea if linea else " ")
        run.font.name = "Consolas"
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(0x22, 0x2B, 0x36)
    doc.add_paragraph()


def construir() -> Path:
    metricas, tabla_datos, por_marca = cargar_datos()
    doc = Document()
    configurar_estilos(doc)
    for seccion in doc.sections:
        seccion.top_margin = Cm(2.2)
        seccion.bottom_margin = Cm(2.0)
        seccion.left_margin = Cm(2.4)
        seccion.right_margin = Cm(2.4)
    pie_de_pagina(doc, "Programación para el Análisis de Datos · EA3")

    # ---------------- Portada ----------------
    for _ in range(3):
        doc.add_paragraph()
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run("Optimización de procesos de desarrollo")
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = AZUL
    subtitulo = doc.add_paragraph()
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitulo.add_run("Pipeline CI/CD, pruebas automáticas y despliegue en la nube\npara el observatorio de precios de Calzatodo")
    run.font.size = Pt(13)
    run.font.color.rgb = GRIS

    doc.add_paragraph()
    doc.add_paragraph()
    for texto, tamano, negrita in [
        ("Evidencia de aprendizaje 3", 14, True),
        ("Programación para el Análisis de Datos", 12, False),
        ("Institución Universitaria Digital de Antioquia", 12, False),
        ("Ingeniería de Software y Datos", 11, False),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(texto)
        run.font.size = Pt(tamano)
        run.bold = negrita

    for _ in range(4):
        doc.add_paragraph()

    for texto in [
        "Estefanía Martínez Guzmán",
        "Carlos Andrés Osorio Agudelo",
        "Valentina Pérez Flórez",
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(texto)
        run.font.size = Pt(12)

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(datetime.now(BOGOTA).strftime("%d de %B de %Y").replace("November", "noviembre"))
    run.font.size = Pt(11)
    run.font.color.rgb = GRIS
    doc.add_page_break()

    # ---------------- Contenido ----------------
    doc.add_heading("Contenido", level=1)
    for item in [
        "1. Introducción",
        "2. Descripción de la página y del artículo analizado",
        "3. Descripción del tema de interés",
        "4. Objetivos",
        "5. Metodología empleada de scraping",
        "6. Automatización con GitHub Actions",
        "7. Despliegue del servicio",
        "8. Resultados y conclusiones",
        "9. Bibliografía",
        "Anexo A. Código fuente",
        "Anexo B. Evidencias de la ejecución",
    ]:
        doc.add_paragraph(item)
    doc.add_page_break()

    # ---------------- 1. Introducción ----------------
    doc.add_heading("1. Introducción", level=1)
    parrafo(
        doc,
        "Este trabajo retoma el observatorio de precios construido en las evidencias 1 y 2 y lo lleva "
        "al punto que faltaba: convertir un cuaderno que se ejecuta a mano en un servicio que se "
        "verifica y se publica solo. La fuente sigue siendo la categoría de tenis deportivos para "
        "mujer de Calzatodo; lo nuevo es el flujo que la rodea.",
    )
    parrafo(
        doc,
        "La diferencia entre un script y un proceso se ve en un caso concreto. Si mañana el sitio "
        "cambia el nombre de un campo, el script sigue corriendo y publica una tabla incompleta; un "
        "proceso con pruebas y reglas de calidad se detiene antes de publicar y avisa. Si el catálogo "
        "se actualiza los miércoles, un script exige que alguien se acuerde de ejecutarlo; un proceso "
        "programado lo hace y deja el registro en el historial de commits. Ese es el objeto de la "
        "unidad: reducir el trabajo manual y la posibilidad de error humano sin perder trazabilidad.",
    )
    parrafo(
        doc,
        "El resultado es un repositorio con tres workflows de GitHub Actions. El primero corre "
        "análisis estático, pruebas y validación de datos en cada cambio. El segundo publica el "
        "tablero en GitHub Pages solo si las pruebas pasan. El tercero extrae el catálogo real todos "
        "los miércoles, versiona el resultado y vuelve a desplegar. El informe documenta cada "
        "decisión, muestra las ejecuciones y explica cómo reproducirlas.",
    )

    # ---------------- 2. Página y artículo ----------------
    doc.add_heading("2. Descripción de la página y del artículo analizado", level=1)
    parrafo(
        doc,
        "La página analizada es la categoría «Tenis deportivos para mujer» de Calzatodo "
        "(https://www.calzatodo.com.co/es/mujeres/tenis/deportivo), una tienda colombiana de calzado. "
        "El catálogo está montado sobre VTEX y se organiza en páginas de veinte publicaciones; cada "
        "publicación corresponde a un artículo: una referencia de tenis con su marca, su precio y su "
        "disponibilidad por talla.",
    )
    parrafo(
        doc,
        "Cada página incluye, en el encabezado, dos bloques de datos estructurados en formato JSON-LD: "
        "un BreadcrumbList con la ruta de navegación y un ItemList con las veinte publicaciones. El "
        "segundo es el que interesa: en lugar de leer el HTML visible clase por clase, el proyecto lee "
        "ese bloque, que declara explícitamente el nombre, la referencia (sku), la marca y los precios "
        "mínimo y máximo de cada artículo. La figura 1 resume la correspondencia entre lo que se ve en "
        "la tienda y lo que se extrae.",
    )
    parrafo(
        doc,
        "También se revisó que el sitio no prohíba la consulta automatizada: su archivo robots.txt no "
        "bloquea la categoría y las peticiones se hacen con un User-Agent de navegador, con pausas "
        "entre páginas y sin sesión autenticada. Solo se leen datos públicos de precios; no se copian "
        "imágenes ni descripciones completas.",
    )
    figura(
        doc,
        CAPTURAS / "diagrama_jsonld.png",
        "Figura 1. De la página al dato: el bloque ItemList se convierte en un objeto Producto normalizado.",
    )

    # ---------------- 3. Tema de interés ----------------
    doc.add_heading("3. Descripción del tema de interés", level=1)
    parrafo(
        doc,
        "El tema que se desarrolla es la observación de precios de una categoría como insumo para "
        "decisiones comerciales: qué marcas dominan la oferta, en qué rangos se concentra el catálogo "
        "y cuánto se separa el precio típico del promedio. Es una pregunta que un analista responde "
        "hoy abriendo fichas una por una, y que cambia cada semana.",
    )
    parrafo(
        doc,
        "Con cuarenta publicaciones la respuesta se calcula en segundos, pero el ejercicio no se trata "
        "del tamaño de la muestra sino del mecanismo: el mismo pipeline sirve para dos páginas o para "
        "doscientas, porque la paginación, la validación y la publicación están separadas en módulos. "
        "La observación se puede repetir sin intervención y deja un histórico en el repositorio, que "
        "es lo que permite comparar semanas más adelante.",
    )

    # ---------------- 4. Objetivos ----------------
    doc.add_heading("4. Objetivos", level=1)
    doc.add_heading("Objetivo general", level=2)
    parrafo(
        doc,
        "Automatizar el ciclo completo del observatorio de precios —extracción, validación, publicación "
        "y actualización— con un pipeline de integración y entrega continuas en GitHub Actions, "
        "desplegado como servicio web en la nube y documentado para que otra persona pueda replicarlo.",
    )
    doc.add_heading("Objetivos específicos", level=2)
    for texto in [
        "Modularizar la extracción de la evidencia anterior en funciones con configuración por variables de entorno, reintentos y registro de cada petición.",
        "Definir reglas de calidad verificables y aplicarlas como condición para publicar.",
        "Escribir pruebas automatizadas que corran sin conexión y cubran extracción, limpieza, métricas y tablero.",
        "Configurar integración continua (análisis estático y pruebas) y entrega continua (publicación en GitHub Pages) con GitHub Actions.",
        "Programar una ejecución semanal que actualice los datos y los versione con un commit automático.",
        "Producir un tablero web y un informe cuyas cifras provengan del mismo cálculo que los datos publicados.",
    ]:
        vineta(doc, texto)

    # ---------------- 5. Metodología ----------------
    doc.add_heading("5. Metodología empleada de scraping", level=1)
    parrafo(
        doc,
        "La extracción se apoya en los datos estructurados del sitio y se organiza con las fases de "
        "CRISP-DM, que es la metodología trabajada en el curso. La tabla 1 muestra qué se hizo en cada "
        "fase y dónde quedó en el código.",
    )
    tabla(
        doc,
        ["Fase de CRISP-DM", "Qué se hizo", "Dónde está"],
        [
            ["Comprensión del negocio", "Definir la pregunta: marcas y rangos de precio de la categoría, con actualización semanal.", "Este informe, secciones 3 y 4"],
            ["Comprensión de los datos", "Identificar el bloque ItemList y sus campos (sku, marca, precios, disponibilidad).", "src/ea3/scraper.py"],
            ["Preparación de los datos", "Convertir precios, normalizar textos, eliminar duplicados y filas sin precio.", "src/ea3/transform.py"],
            ["Modelado", "No hay modelo predictivo: se calculan indicadores descriptivos (conteo, mínimo, máximo, promedio, mediana y rangos).", "src/ea3/transform.py · resumen()"],
            ["Evaluación", "Reglas de calidad y pruebas automatizadas antes de publicar.", "transform.validar() y tests/"],
            ["Despliegue", "Tablero estático publicado en GitHub Pages y actualizado por un workflow semanal.", "report/ y .github/workflows/"],
        ],
        anchos=[4.2, 8.6, 3.6],
    )
    parrafo(
        doc,
        "En la práctica, el scraper hace tres cosas: descarga la página con un User-Agent de navegador y "
        "un tiempo máximo de espera; localiza todos los bloques application/ld+json y se queda con el "
        "que declara @type igual a ItemList; y convierte cada elemento en un objeto Producto, ignorando "
        "los que no tienen nombre o referencia. Los precios se llevan a número y, si el bloque no trae "
        "lowPrice, se toma el mínimo y el máximo del arreglo de ofertas.",
    )
    parrafo(
        doc,
        "La descarga tiene tres protecciones que se probaron con respuestas simuladas: reintenta hasta "
        "tres veces con espera creciente (1, 2 y 4 segundos) cuando el servidor responde 429 o 5xx; no "
        "reintenta un 404, porque volver a pedirlo no cambia el resultado; y registra el código HTTP de "
        "cada página en logs/pipeline.log y en la salida del job. La pausa entre páginas es de dos "
        "segundos por cortesía con el sitio.",
    )
    parrafo(
        doc,
        "La deduplicación se hace por referencia (sku), no por URL: el catálogo puede repetir un "
        "producto con dos direcciones distintas cuando cambia de colección, y la referencia es el "
        "identificador que usa la tienda. En la ejecución del 26 de noviembre se leyeron 40 "
        "publicaciones en dos páginas y quedaron 40 únicas.",
    )

    # ---------------- 6. Automatización ----------------
    doc.add_heading("6. Automatización con GitHub Actions", level=1)
    parrafo(
        doc,
        "GitHub Actions ejecuta los workflows definidos en .github/workflows. El proyecto tiene tres, "
        "con responsabilidades separadas para que un fallo se identifique rápido y para que la "
        "publicación dependa de las pruebas. La tabla 2 los resume.",
    )
    tabla(
        doc,
        ["Workflow", "Se dispara con", "Qué hace", "Evidencia"],
        [
            ["ci.yml", "Push y pull request", "Instala dependencias, corre Ruff, Pytest y valida el dataset versionado.", "Check verde en cada commit"],
            ["deploy.yml", "Push a main o manual", "Repite las pruebas y publica report/ en GitHub Pages.", "Job de despliegue y URL pública"],
            ["scrape.yml", "Miércoles 19:00 UTC y manual", "Extrae el catálogo, valida, versiona CSV, métricas y tablero, y despliega.", "Commit automático y ejecución programada"],
        ],
        anchos=[2.6, 3.6, 6.4, 3.8],
    )
    doc.add_heading("6.1 Integración continua", level=2)
    parrafo(
        doc,
        "La integración continua responde una pregunta: ¿este cambio deja el proyecto funcionando? El "
        "workflow instala las dependencias desde requirements.txt, ejecuta ruff check para detectar "
        "errores evidentes y ordenar los imports, corre pytest y por último valida la calidad del "
        "dataset que está versionado. Las pruebas no salen a internet: usan un recorte real de la "
        "página guardado en tests/fixtures, de modo que un fallo del sitio no se confunde con un fallo "
        "del código. La prueba que sí consulta el sitio está marcada como integración y solo corre "
        "cuando se pide explícitamente.",
    )
    bloque_codigo(
        doc,
        """- name: Analizar el estilo y los errores evidentes (Ruff)
  run: ruff check .

- name: Ejecutar las pruebas unitarias (Pytest)
  run: pytest -q

- name: Validar la calidad del dataset versionado
  run: PYTHONPATH=src python -m ea3.pipeline --check""",
    )
    parrafo(
        doc,
        "El paso de validación es el que conecta el código con los datos: ejecuta las mismas reglas que "
        "el pipeline y falla si hay referencias duplicadas, precios en cero, columnas faltantes o una "
        "completitud menor al 90 %. Así, un cambio en el scraper que rompa la extracción no llega a "
        "main solo porque las pruebas unitarias pasaron.",
    )

    doc.add_heading("6.2 Entrega continua", level=2)
    parrafo(
        doc,
        "La entrega continua publica el tablero. El workflow tiene dos jobs: calidad y despliegue. El "
        "segundo declara needs: calidad, así que GitHub no lo ejecuta si el primero falla. El "
        "despliegue regenera el HTML a partir del CSV versionado, empaqueta la carpeta report y la "
        "publica con las acciones oficiales de Pages. Los permisos están declarados al inicio del "
        "archivo: contents de lectura, pages de escritura y id-token para la autenticación del "
        "despliegue.",
    )
    bloque_codigo(
        doc,
        """permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  calidad:
    ...
  desplegar:
    needs: calidad
    environment:
      name: github-pages
      url: ${{ steps.despliegue.outputs.page_url }}""",
    )
    parrafo(
        doc,
        "Separar calidad de despliegue es deliberado: un push a main que rompe una prueba deja el sitio "
        "anterior en línea, en vez de reemplazarlo por una versión rota. El entorno github-pages "
        "registra la URL publicada y deja un historial de despliegues consultable.",
    )

    doc.add_heading("6.3 Extracción programada", level=2)
    parrafo(
        doc,
        "El tercer workflow es el que mantiene los datos al día. Corre todos los miércoles a las 19:00 "
        "UTC, que en Colombia son las 2:00 p. m., y también se puede lanzar a mano. Antes de extraer "
        "compara la fecha con la vigencia del curso y se detiene cuando la supera; después ejecuta el "
        "pipeline, versiona los tres archivos que cambian (CSV, métricas y tablero) y despliega. Si no "
        "hubo cambios, el commit se omite en lugar de crear un registro vacío.",
    )
    parrafo(
        doc,
        "Las credenciales no están en el repositorio. El push usa el token que GitHub genera en cada "
        "ejecución (secrets.GITHUB_TOKEN), con permisos de escritura declarados en el workflow. Los "
        "parámetros de comportamiento (EA3_PAGES y EA3_VIGENCIA_HASTA) se leen de las variables del "
        "repositorio, de modo que cambiar cuántas páginas se extraen no exige tocar el código.",
    )

    # ---------------- 7. Despliegue ----------------
    doc.add_heading("7. Despliegue del servicio", level=1)
    parrafo(
        doc,
        "El servicio se despliega en GitHub Pages, el alojamiento estático de GitHub. Se eligió porque "
        "el entregable es un tablero HTML que se genera en el pipeline: no necesita servidor de "
        "aplicaciones, base de datos ni variables secretas en tiempo de ejecución. El sitio queda en "
        "una URL pública, servida por la infraestructura de GitHub, y cada despliegue reemplaza la "
        "versión anterior de forma atómica.",
    )
    parrafo(
        doc,
        "La configuración tiene cuatro piezas: la carpeta report como artefacto; el workflow "
        "deploy.yml, que la empaqueta y la publica; la acción configure-pages, que habilita Pages con "
        "origen «GitHub Actions» la primera vez; y el entorno github-pages, que expone la URL. No hay "
        "variables de entorno en el sitio porque el HTML se genera antes de publicar; las variables "
        "del pipeline (URL de la categoría, número de páginas, pausa, reintentos y vigencia) están "
        "documentadas en el README y en .env.example.",
    )
    tabla(
        doc,
        ["Elemento", "Configuración"],
        [
            ["Servicio", "GitHub Pages (sitio estático)"],
            ["Artefacto publicado", "Carpeta report/ (index.html autónomo)"],
            ["Origen", "GitHub Actions, habilitado por configure-pages"],
            ["Entorno", "github-pages, con URL en el job de despliegue"],
            ["Disparadores", "Push a main, ejecución manual y extracción semanal"],
            ["Credenciales", "GITHUB_TOKEN generado por GitHub; sin secretos en el repositorio"],
        ],
        anchos=[5.0, 11.0],
    )
    parrafo(
        doc,
        "El tablero publicado (figura 2) muestra seis indicadores —publicaciones, marcas, precio mínimo, "
        "máximo, promedio y completitud—, dos gráficas (publicaciones por marca y distribución por rango "
        "de precio) y un explorador con búsqueda por producto, marca o referencia. Cada fila enlaza a la "
        "ficha original, de modo que cualquier cifra se puede verificar contra la tienda.",
    )
    figura(
        doc,
        CAPTURAS / "tablero_recorte.png",
        "Figura 2. Tablero generado por el pipeline; la versión publicada se sirve igual desde GitHub Pages.",
    )

    # ---------------- 8. Resultados ----------------
    doc.add_heading("8. Resultados y conclusiones", level=1)
    parrafo(
        doc,
        f"La ejecución del 26 de noviembre de 2026 leyó dos páginas y dejó {metricas['total_productos']} "
        f"publicaciones únicas de {metricas['marcas_unicas']} marcas. La completitud de campos fue del "
        f"{metricas['completitud_pct']:.1f} % y ninguna fila incumplió las reglas de calidad. La tabla 4 "
        "resume los indicadores y la tabla 5 los desagrega por marca.",
    )
    tabla(
        doc,
        ["Indicador", "Valor"],
        [
            ["Publicaciones únicas", str(metricas["total_productos"])],
            ["Marcas", str(metricas["marcas_unicas"])],
            ["Precio mínimo", pesos(metricas["precio_minimo"])],
            ["Precio máximo", pesos(metricas["precio_maximo"])],
            ["Precio promedio", pesos(metricas["precio_promedio"])],
            ["Precio mediano", pesos(metricas["precio_mediana"])],
            ["Completitud de campos", f"{metricas['completitud_pct']:.1f} %"],
        ],
        anchos=[8.0, 8.0],
    )
    tabla(
        doc,
        ["Marca", "Publicaciones", "Precio promedio", "Precio mínimo", "Precio máximo"],
        [
            [
                marca,
                str(int(fila["publicaciones"])),
                pesos(fila["promedio"]),
                pesos(fila["minimo"]),
                pesos(fila["maximo"]),
            ]
            for marca, fila in por_marca.iterrows()
        ],
        anchos=[3.6, 3.0, 3.4, 3.0, 3.0],
    )
    parrafo(
        doc,
        "Hay dos lecturas que el promedio solo no muestra. Primero, la mediana ($ 111.920) está muy por "
        "debajo del promedio ($ 151.168): la mayoría de las publicaciones es económica y unas pocas "
        "referencias de Skechers y New Balance, por encima de $ 220.000, estiran el promedio. Segundo, "
        "el 67,5 % del catálogo cuesta menos de $ 150.000 y solo dos publicaciones superan los "
        "$ 250.000, de modo que la competencia de esta categoría se juega en el tramo bajo. Esa "
        "diferencia entre promedio y mediana es una conclusión del análisis, no un detalle técnico: "
        "quien mire solo el promedio sobreestima el precio típico en casi cuarenta mil pesos.",
    )
    parrafo(
        doc,
        "En cuanto al proceso, el resultado es que la cifra se puede reproducir. El comando "
        "PYTHONPATH=src python -m ea3.pipeline produce el CSV, el JSON de métricas y el tablero; las "
        "pruebas (22, más una de integración que se ejecuta aparte) verifican el parser, los reintentos, "
        "la deduplicación, las reglas de calidad y el HTML; y los workflows repiten ese mismo comando "
        "en un runner limpio. El informe no tiene cifras escritas a mano: las lee de metricas.json.",
    )
    parrafo(
        doc,
        "Las limitaciones son claras. La muestra son dos páginas de una categoría, no todo el catálogo; "
        "los precios son una foto del momento y el histórico se reconstruye con los commits; el parser "
        "depende de que el sitio mantenga el bloque ItemList; y la automatización programada termina el "
        "9 de diciembre de 2026, cuando cierra la ventana del curso. Ninguna de esas limitaciones afecta "
        "la reproducibilidad del flujo, que es lo que evalúa esta evidencia.",
    )

    # ---------------- 9. Bibliografía ----------------
    doc.add_heading("9. Bibliografía", level=1)
    for referencia in [
        "Chacon, S. y Straub, B. (2014). Pro Git (2.ª ed.). Apress. https://git-scm.com/book/es/v2",
        "GitHub. (2026). Documentación de GitHub Actions. https://docs.github.com/es/actions",
        "GitHub. (2026). Publicar sitios con GitHub Pages. https://docs.github.com/es/pages",
        "Richardson, L. (2024). Beautiful Soup Documentation. https://www.crummy.com/software/BeautifulSoup/bs4/doc/",
        "The pandas development team. (2026). pandas documentation. https://pandas.pydata.org/docs/",
        "Schema.org. (2026). ItemList: datos estructurados. https://schema.org/ItemList",
    ]:
        p = doc.add_paragraph(referencia)
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # ---------------- Anexos ----------------
    doc.add_page_break()
    doc.add_heading("Anexo A. Código fuente", level=1)
    parrafo(
        doc,
        "El código completo está en el repositorio. La tabla 6 indica dónde mirar cada parte y qué "
        "responsabilidad tiene; los módulos están comentados para poder estudiarlos sin ejecutarlos.",
    )
    tabla(
        doc,
        ["Archivo", "Responsabilidad"],
        [
            ["src/ea3/config.py", "Variables de entorno, valores por defecto y rutas"],
            ["src/ea3/scraper.py", "Descarga con reintentos y lectura del bloque ItemList"],
            ["src/ea3/transform.py", "Limpieza, reglas de calidad, métricas y CSV"],
            ["src/ea3/report.py", "Renderizado del tablero con la plantilla"],
            ["src/ea3/templates/tablero.html.j2", "Estructura y estilos del tablero"],
            ["src/ea3/pipeline.py", "Orquestación y códigos de salida"],
            ["tests/", "Pruebas unitarias y recorte real de la página"],
            [".github/workflows/ci.yml", "Integración continua"],
            [".github/workflows/deploy.yml", "Entrega continua en GitHub Pages"],
            [".github/workflows/scrape.yml", "Extracción programada semanal"],
        ],
        anchos=[6.0, 10.0],
    )
    parrafo(
        doc,
        "Para reproducirlo: clonar el repositorio, crear un entorno virtual, instalar requirements.txt y "
        "ejecutar PYTHONPATH=src python -m ea3.pipeline. En GitHub, los workflows corren solos; el "
        "semanal se puede lanzar a mano desde Actions con Run workflow.",
    )

    doc.add_heading("Anexo B. Evidencias de la ejecución", level=1)
    parrafo(
        doc,
        "Repositorio: https://github.com/Estefa-M/EA2_Web_Scraping\n"
        "Acciones: https://github.com/Estefa-M/EA2_Web_Scraping/actions\n"
        "Tablero publicado: https://estefa-m.github.io/EA2_Web_Scraping/\n"
        "Cuaderno ejecutado: notebooks/Osorio_Carlos_Actividad_EA3.ipynb",
    )
    figuras = [
        ("actions_ci.png", "Figura 3. Ejecución de integración continua con Ruff, Pytest y validación del dataset."),
        ("actions_deploy.png", "Figura 4. Despliegue en GitHub Pages y URL publicada."),
        ("tablero_publicado.png", "Figura 5. Tablero publicado en la URL de GitHub Pages."),
    ]
    faltantes = []
    for archivo, leyenda in figuras:
        if not figura(doc, CAPTURAS / archivo, leyenda):
            faltantes.append(archivo)
    if faltantes:
        parrafo(
            doc,
            "Nota de generación: faltan las capturas " + ", ".join(faltantes) + ". Se agregan al "
            "regenerar el informe después de la primera ejecución en GitHub.",
            cursiva=True,
            tamano=9,
        )

    ruta_docx = DOCS / f"{NOMBRE}.docx"
    doc.save(ruta_docx)
    return ruta_docx


if __name__ == "__main__":
    ruta = construir()
    print("Documento generado:", ruta)
