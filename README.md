# EA2_Web_Scraping

Proyecto de extracción de datos de la categoría de tenis deportivos para mujer de
[Calzatodo](https://www.calzatodo.com.co/es/mujeres/tenis/deportivo), con control de
versiones en GitHub.

**Evidencia de aprendizaje 2** — Programación para el Análisis de Datos
Universidad Digital de Antioquia

## Integrantes

- Estefanía Martínez Guzmán
- Carlos Andrés Osorio Agudelo
- Valentina Pérez Flórez

## Qué hace el proyecto

El cuaderno consulta las dos primeras páginas de la categoría, localiza los bloques
JSON-LD de tipo `ItemList` que publica el sitio y extrae, de cada publicación, el
nombre, la marca, la referencia, el precio mínimo, el precio máximo, la moneda y la
dirección del producto. Después elimina las publicaciones repetidas por dirección,
convierte los precios a valores numéricos y exporta el resultado a un CSV.

La extracción se apoya en `requests`, `BeautifulSoup`, `json` y `pandas`.

## Contenido del repositorio

| Archivo | Descripción |
|---|---|
| `calzatodo_ea2.ipynb` | Cuaderno con la extracción, la validación de datos y el flujo de Git |
| `calzatodo_tenis_deportivos_mujer.csv` | Resultados de la última ejecución (26 publicaciones) |
| `README.md` | Este documento |

## Requisitos

- Python 3.11 o superior
- `requests`, `beautifulsoup4`, `pandas`

```bash
pip install requests beautifulsoup4 pandas
```

## Cómo ejecutar

1. Abrir `calzatodo_ea2.ipynb` en Google Colab o en Jupyter.
2. Ejecutar las celdas en orden.

El cuaderno genera `calzatodo_tenis_deportivos_mujer.csv` en la carpeta de trabajo y,
cuando se ejecuta en Colab, lo descarga automáticamente.

### Publicar los resultados en GitHub

Las celdas de la sección 5 clonan el repositorio, copian el CSV, registran el cambio
con un commit y lo publican en la rama `main`.

La clonación es idempotente: si la carpeta ya existe se reutiliza, así que el cuaderno
puede ejecutarse varias veces sin errores. Para el `git push` se requiere un token de
acceso personal guardado como secreto `GITHUB_TOKEN` en Colab; la celda lo lee desde
los secretos y no lo escribe en el cuaderno ni en el repositorio.

## Resultados

La última ejecución descargó 40 registros y quedaron **26 publicaciones únicas**, sin
valores faltantes en las siete columnas. Los precios se ubicaron entre 134.900 y
349.900 COP.

| Métrica | Meta | Resultado |
|---|---|---|
| Completitud de campos | ≥ 95 % | 100 % (182/182 celdas) |
| Publicaciones con dirección única | 100 % | 100 % (26/26) |
| Precios almacenados como número | 100 % | 100 % |
| Respuestas HTTP distintas de 200 | 0 | 0 |
| Ejecución sin celdas con error | 1 | 1 |

## Nota sobre la paginación

En la primera evidencia la página uno se solicitaba sin el parámetro `page`, porque la
dirección base de la categoría entregaba el bloque `ItemList`. El sitio cambió ese
comportamiento: hoy la dirección base ya no incluye el bloque y la página uno debe
pedirse con `page=1`. El cuaderno se ajustó a ese cambio y por eso los resultados de la
última ejecución no coinciden cifra a cifra con los de la primera entrega.

## Flujo de trabajo con Git

- La rama `main` contiene la versión estable del proyecto.
- Los cambios de documentación se trabajaron en la rama `mejora-readme` y se
  integraron mediante una solicitud de extracción.
- Los mensajes de commit describen la modificación realizada.

## Alcance

La muestra corresponde a las dos primeras páginas de la categoría en un momento
determinado, de modo que no representa la totalidad del catálogo ni permite comparar
precios en el tiempo. El pipeline de integración continua con GitHub Actions y el
despliegue continuo corresponden a la Unidad 3 del curso.

## Referencias

- [Calzatodo — Tenis deportivos para mujer](https://www.calzatodo.com.co/es/mujeres/tenis/deportivo)
- [Pro Git (Chacon y Straub, 2014)](https://git-scm.com/book/es/v2)
- [GitHub Docs — Solicitudes de extracción](https://docs.github.com/es/pull-requests)
- [Beautiful Soup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
