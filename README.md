# EA2_Web_Scraping
Evidencia de aprendizaje 2. Optimizando la productividad en el mundo del software

Este proyecto continúa la primera evidencia de Programación para el Análisis de Datos. El objetivo es organizar los resultados de la extracción y usar Git y GitHub para registrar los cambios del proyecto.

## ¿Qué hace el proyecto?

El notebook consulta las dos primeras páginas de tenis deportivos para mujer de Calzatodo. Usa BeautifulSoup para localizar los datos de los productos y pandas para organizarlos en una tabla, eliminar publicaciones con URLs repetidas y exportar el resultado a un CSV.

## Archivos del proyecto

- [Notebook de extracción](calzatodo_ea1.ipynb): contiene el código y la explicación del proceso. Para repetir la extracción en Google Colab, ejecuta las secciones de herramientas, extracción, preparación y almacenamiento. Las celdas de Git al final documentan cómo se subió el CSV.
- [CSV de resultados](calzatodo_tenis_deportivos_mujer.csv): contiene los nombres, marcas, SKU de referencia, precios mínimo y máximo, moneda y enlaces. Si lo importas en Excel, selecciona el punto y coma (`;`) como separador.

## Resultados

El CSV publicado contiene 24 publicaciones únicas. La salida guardada en el notebook muestra 26 publicaciones porque corresponde a otra ejecución de la extracción.
