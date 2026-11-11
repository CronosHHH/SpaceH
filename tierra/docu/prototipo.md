# Prototipo terrestre de mapas a 1°

El [script](../prototipo_analogos.py) y el [notebook](../prototipo_analogos.ipynb)
reúnen las variables terrestres publicadas en `Renato-R-V/hspace-datasets`.
Preparan una exploración regional; todavía no calculan similitudes con Marte.

## Archivos utilizados y almacenamiento

El catálogo `tierra/catalogo.json` registra rutas, tamaños, hashes, unidades y
georreferencias. El prototipo fija un commit de Hugging Face por ejecución y
descarga solamente estos **cuatro resúmenes pequeños**, por HTTP a memoria:

- `NASADEM_tierra_1grado.tif`: elevación media válida en metros EGM96 y fracción
  de píxeles con elevación conocida.
- `GHI_tierra.tif`: GHI terrestre anual, W/m², NASA POWER 2001–2025.
- `Albedo_tierra.tif`: albedo superficial adimensional, misma climatología POWER.
- `Fracciones_mascaras_tierra_MODIS_2021_1grado.tif`: fracciones de ciudades,
  agua, vegetación y cobertura clasificada.

Se comprueban tamaño, SHA256, CRS, extensión, unidades, periodo y cobertura antes
de combinar datos. No se usa `hf_hub_download`, ni se crea una caché de TIFF en
el disco del usuario. Cada descarga está limitada a 16 MB; los mosaicos globales
de 15 segundos de arco quedan remotos.

El informe `tierra/auditoria/prototipo.json` registra los hashes de entradas y
salidas, las comprobaciones, las coberturas y el número de celdas conocidas en
las seis variables. La publicación exige cotejar esos hashes con los productos.

La malla común es EPSG:4326, **360 × 180 celdas de 1°**, norte arriba, extensión
−180°…180° / −90°…90°. Un grado terrestre representa aproximadamente **111 km
en el ecuador**; la distancia este-oeste disminuye con la latitud. Los resúmenes
no adquieren detalle de 463 m por contener datos derivados de productos más finos.

## Variables, cobertura y exclusión

`tierra_1grado.tif` contiene seis bandas, en este orden:

1. Elevación NASADEM, metros EGM96.
2. GHI terrestre, W/m².
3. Albedo terrestre, adimensional.
4. Fracción de ciudades entre los píxeles clasificados.
5. Fracción de agua entre los píxeles clasificados.
6. Fracción de vegetación entre los píxeles clasificados.

`coberturas_tierra_1grado.tif` contiene la fracción de elevación conocida y la
fracción clasificada. **NoData permanece como `NaN`; cobertura cero es un dato
válido.** La elevación media está condicionada a sus píxeles válidos. Las tres
fracciones temáticas están condicionadas a los píxeles clasificados y no son
mediciones biofísicas subpíxel. Debe consultarse la cobertura antes de comparar
una celda parcial con una completamente conocida.

Las dos coberturas usan como denominador **todos los píxeles de la malla detallada
dentro de la celda de análisis**, incluidos los desconocidos. Sus denominadores
se guardan en los metadatos de cada banda y no se confunden con el denominador
condicionado de las tres fracciones temáticas.

El prototipo no impone un umbral arbitrario para excluir celdas globales de 1°.
La máscara detallada de `Mascaras_tierra_MODIS_2021_15arcsec.tif` permite construir
la exclusión en ventanas pequeñas: bit 1 ciudades, bit 2 agua, bit 4 vegetación;
el bit 8 registra el suplemento de océano Natural Earth, aplicado únicamente
donde MODIS no clasifica. El código 10 combina agua y esa procedencia oceánica.
**255 significa desconocido y debe comprobarse antes de usar bits.** Por ejemplo,
para una ventana `a` ya leída del TIFF remoto:

```python
conocido = a != 255
ciudades = conocido & ((a & 1) != 0)
agua = conocido & ((a & 2) != 0)
vegetacion = conocido & ((a & 4) != 0)
excluir = ciudades | agua | vegetacion
```

Los desconocidos necesitan una decisión explícita de tratamiento; no se
interpretan como suelo desnudo. Natural Earth tiene escala cartográfica
1:10.000.000: rasterizar sus costas a 15 segundos de arco no añade detalle.

## Ejecución

Desde la raíz del repositorio, después de publicar los cuatro productos:

```bash
MPLBACKEND=Agg marte/.venv/bin/python tierra/prototipo_analogos.py
```

Para el notebook, seleccionar el kernel existente `marte/.venv/bin/python` y
ejecutar las celdas en orden. El script permite `--catalogo`, `--revision` y
`--salida`. Por defecto los TIFF preparados y la vista de seis paneles se escriben
en `/tmp/hspace_tierra_productos/prototipo/`. La publicación debe verificarse
antes de borrar esos TIFF temporales.

Cada etapa del notebook llama a una función del script: catálogo, lectura y
validación, resumen, guardado y visualización. La figura mantiene las fracciones
y el albedo entre 0 y 1; el contraste de elevación y GHI entre percentiles 2 y 98
afecta solo a la imagen.

## Interpretación y atribución

NASADEM cubre su huella de adquisición; los huecos y regiones fuera de esa huella
permanecen desconocidos. NASA POWER representa una climatología anual; las
clases de suelo corresponden a 2021. No son observaciones simultáneas de una
misma fecha. El GHI de Marte es un modelo simplificado para Ls = 18,9°, y su
albedo Lambert bolométrico tiene una definición diferente del albedo POWER
superficial bajo todo cielo. Las unidades facilitan la exploración, pero una
comparación ambiental exige armonizar esas definiciones y escalas.

Las máscaras se derivan de Rolf Simoes/OpenGeoHub (2023),
DOI `10.5281/zenodo.8367523`, MODIS MCD12Q1.061, con suplemento Natural Earth.
Sus fracciones están bajo **CC BY-SA 4.0**. El cubo combinado, el ráster de
coberturas y la figura que incluyen esos derivados mantienen **CC BY-SA 4.0**
y la atribución, escrita también en los metadatos de salida. Fuentes de radiación:
NASA POWER. Elevación: NASA/JPL-Caltech NASADEM.
