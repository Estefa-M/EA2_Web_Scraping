# Observatorio de precios de Calzatodo

Proyecto del curso **Programación para el Análisis de Datos** de la Institución
Universitaria Digital de Antioquia. Extrae el catálogo público de tenis deportivos
para mujer de [Calzatodo](https://www.calzatodo.com.co/es/mujeres/tenis/deportivo),
lo valida, lo publica como tablero web y automatiza todo el ciclo con
**GitHub Actions** (integración continua, entrega continua y extracción programada).

**Evidencia de aprendizaje 3** — Optimización de procesos de desarrollo.
Continúa las evidencias 1 y 2, que siguen en el repositorio como historial.

**Integrantes**

- Estefanía Martínez Guzmán
- Carlos Andrés Osorio Agudelo
- Valentina Pérez Flórez

---

## 1. Introducción

Comparar precios de un catálogo a mano es lento y se desactualiza el mismo día.
Este proyecto automatiza esa tarea: un scraper lee las publicaciones, un pipeline
las limpia y calcula indicadores, y un tablero web muestra el resultado sin que
nadie tenga que abrir un cuaderno.

La entrega no se queda en el script. Lo que se evalúa es el **flujo completo**:
el mismo comando corre en el portátil y en GitHub, las pruebas frenan un cambio
roto antes de llegar a `main`, el tablero se publica solo y una ejecución semanal
mantiene los datos al día con un commit automático. Es el ciclo que la unidad
llama *optimización de procesos de desarrollo*: menos pasos manuales, más
verificación automática y un despliegue repetible.

## 2. Qué hay en el repositorio

| Ruta | Para qué sirve |
|---|---|
| `src/ea3/config.py` | Variables de entorno y rutas del proyecto |
| `src/ea3/scraper.py` | Descarga las páginas y lee el bloque JSON-LD `ItemList` |
| `src/ea3/transform.py` | Limpieza, reglas de calidad y métricas |
| `src/ea3/report.py` | Genera el tablero HTML |
| `src/ea3/pipeline.py` | Orquestador de la línea de comandos |
| `tests/` | Pruebas unitarias con Pytest y un recorte real de la página |
| `.github/workflows/ci.yml` | Integración continua: Ruff, Pytest y validación del dataset |
| `.github/workflows/deploy.yml` | Entrega continua: publica el tablero en GitHub Pages |
| `.github/workflows/scrape.yml` | Extracción programada semanal con commit automático |
| `data/productos.csv` | Última ejecución del catálogo (40 publicaciones) |
| `data/metricas.json` | Cifras calculadas, consumidas por el informe |
| `report/index.html` | Tablero publicado |
| `notebooks/Osorio_Carlos_Actividad_EA3.ipynb` | Cuaderno de la evidencia, con salidas |
| `docs/Osorio_Carlos_Actividad_EA3.pdf` | Informe de la actividad |
| `calzatodo_ea2.ipynb` | Evidencia 2: extracción y control de versiones |
| `calzatodo_tenis_deportivos_mujer.csv` | Resultado de la Evidencia 2 (26 publicaciones) |

## 3. Requisitos e instalación

- Python 3.11 o superior
- Las dependencias están en `requirements.txt`

```bash
git clone https://github.com/Estefa-M/EA2_Web_Scraping.git
cd EA2_Web_Scraping
python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Las variables de entorno son opcionales: el código trae valores por defecto.
Para cambiarlas, copie `.env.example` como `.env` o expórtelas en la terminal.

| Variable | Para qué sirve | Por defecto |
|---|---|---|
| `EA3_BASE_URL` | Categoría que se extrae | tenis deportivo para mujer |
| `EA3_PAGES` | Páginas que se recorren | `2` |
| `EA3_DELAY_SEG` | Pausa entre peticiones | `2.0` |
| `EA3_TIMEOUT_SEG` | Tiempo máximo por petición | `30` |
| `EA3_REINTENTOS` | Reintentos por página | `3` |
| `EA3_VIGENCIA_HASTA` | Fin de la automatización programada | `2026-12-09` |

## 4. Uso

```bash
# Extraer, validar, guardar el CSV y generar el tablero
PYTHONPATH=src python -m ea3.pipeline

# Cambiar el número de páginas sin tocar el código
PYTHONPATH=src python -m ea3.pipeline --pages 3

# Regenerar el tablero con los datos ya guardados (sin salir a internet)
PYTHONPATH=src python -m ea3.pipeline --desde-csv data/productos.csv

# Solo validar la calidad del dataset (lo que corre la integración continua)
PYTHONPATH=src python -m ea3.pipeline --check

# Pruebas y análisis de estilo
pytest -q
ruff check .
```

El pipeline termina con un resumen en consola (productos, marcas, precios,
completitud) y escribe `data/productos.csv`, `data/metricas.json` y
`report/index.html`. Si los datos no pasan las reglas de calidad, sale con
código 2 y no publica nada.

## 5. Automatización con GitHub Actions

El repositorio tiene tres workflows; los tres se ven en la pestaña **Actions**.

### `ci.yml` — integración continua

Se dispara en **cada push y cada pull request**. Instala dependencias, corre
`ruff check .`, ejecuta `pytest -q` y valida el dataset versionado con
`python -m ea3.pipeline --check`. Si algo falla, el check queda en rojo.

### `deploy.yml` — entrega continua

Se dispara con **push a `main`** o a mano. Primero repite las pruebas; solo si
pasan, regenera el tablero desde `data/productos.csv` y lo publica en GitHub
Pages con `actions/upload-pages-artifact` y `actions/deploy-pages`. La URL
pública queda en el job y en la pestaña **Deployments**.

### `scrape.yml` — extracción programada

Corre **todos los miércoles a las 19:00 UTC** (2:00 p. m. de Colombia) y también
con `workflow_dispatch`. Valida la vigencia del curso, ejecuta el pipeline contra
el sitio real, versiona `data/productos.csv`, `data/metricas.json` y
`report/index.html`, y vuelve a desplegar el tablero. La ejecución se detiene
cuando la fecha supera `EA3_VIGENCIA_HASTA`.

**Variables y secretos.** Los valores del comportamiento (`EA3_PAGES`,
`EA3_VIGENCIA_HASTA`) se leen de *Settings → Secrets and variables → Actions →
Variables*. El token para hacer push lo genera GitHub en cada ejecución
(`secrets.GITHUB_TOKEN`), así que **no hay credenciales guardadas en el
repositorio**; el workflow lo usa solo en el paso de `git push`. Los permisos
mínimos están declarados en cada archivo (`contents`, `pages`, `id-token`).

## 6. Despliegue

El tablero se publica en **GitHub Pages** como sitio estático:

- URL: **https://estefa-m.github.io/EA2_Web_Scraping/**
- Origen: la carpeta `report/` del repositorio, empaquetada por el workflow
  `deploy.yml`. `actions/configure-pages` habilita Pages con origen
  *GitHub Actions* la primera vez.
- Entorno: `github-pages`, con la URL expuesta en el job de despliegue.
- No requiere servidor, base de datos ni variables secretas en el sitio: el HTML
  se genera en el pipeline y se sirve tal cual.
- Cada push a `main` y cada ejecución semanal reemplazan el sitio por la versión
  con los datos más recientes.

## 7. Resultados (ejecución del 26/11/2026)

| Métrica | Resultado |
|---|---|
| Publicaciones únicas | 40 |
| Marcas | 3 (Throwing 27, Skechers 8, New Balance 5) |
| Precio mínimo | $ 107.920 |
| Precio máximo | $ 279.920 |
| Precio promedio | $ 151.168 |
| Precio mediano | $ 111.920 |
| Completitud de campos | 100 % |
| Publicaciones entre $150.000 y $350.000 | 13 de 40 |

Las cifras no están escritas a mano: salen de `data/metricas.json`, que genera el
mismo pipeline que alimenta el tablero. La lectura del catálogo es clara: el 67 %
de las publicaciones está por debajo de $150.000 y la mediana ($ 111.920) es muy
inferior al promedio ($ 151.168), porque unas pocas referencias de marca suben el
promedio.

## 8. Historial de evidencias

| Evidencia | Qué aportó | Dónde está |
|---|---|---|
| EA1 | Primera extracción de Calzatodo (24 publicaciones, JSON-LD y paginación) | `calzatodo_ea2.ipynb` (sección 1) |
| EA2 | Limpieza, métricas de calidad y control de versiones con Git/GitHub | `calzatodo_ea2.ipynb` y su CSV |
| EA3 | Pipeline CI/CD, pruebas, tablero y despliegue en la nube | `src/`, `tests/`, `report/`, `.github/workflows/` |

## 9. Limitaciones

- La extracción depende de que Calzatodo siga publicando el bloque JSON-LD
  `ItemList`; un cambio de estructura exige ajustar `parsear_item_list`.
- La muestra son las dos primeras páginas de una categoría, no todo el catálogo.
- Los precios son una foto del momento de la ejecución; el histórico se puede
  reconstruir con los commits de `data/productos.csv`.
- GitHub Pages sirve contenido público: el tablero no debe incluir datos
  personales.
- La ejecución programada se detiene el 9 de diciembre de 2026, cuando cierra la
  ventana del curso.

## 10. Referencias

Chacon, S. y Straub, B. (2014). *Pro Git* (2.ª ed.). Apress.
https://git-scm.com/book/es/v2

GitHub. (2026). *Documentación de GitHub Actions*.
https://docs.github.com/es/actions

GitHub. (2026). *Publicar sitios con GitHub Pages*.
https://docs.github.com/es/pages

Richardson, L. (2024). *Beautiful Soup Documentation*.
https://www.crummy.com/software/BeautifulSoup/bs4/doc/

The pandas development team. (2026). *pandas documentation*.
https://pandas.pydata.org/docs/
