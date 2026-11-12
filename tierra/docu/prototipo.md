# Prototipo terrestre de mapas a 1°

El [script](../prototipo_analogos.py) y el [notebook](../prototipo_analogos.ipynb)
reúnen las variables terrestres publicadas en `Renato-R-V/hspace-datasets`.
Preparan una exploración regional; todavía no calculan similitudes con Marte.

## Archivos utilizados y almacenamiento

El catálogo `tierra/catalogo.json` registra rutas, tamaños, hashes, unidades y
georreferencias. El prototipo fija un commit de Hugging Face por ejecución y
descarga solamente estos **cinco resúmenes pequeños**, por HTTP a memoria:

- `NASADEM_tierra_1grado.tif`: elevación media válida en metros EGM96 y fracción
  de píxeles con elevación conocida.
- `GHI_tierra.tif`: GHI terrestre anual, W/m², NASA POWER 2001–2025.
- `Albedo_tierra.tif`: albedo superficial adimensional, misma climatología POWER.
- `Fracciones_mascaras_tierra_MODIS_2021_1grado.tif`: fracciones de ciudades,
  agua, categorías vegetadas y cobertura clasificada. La fracción categórica de
  vegetación se conserva en este producto, pero ya no alimenta la sexta variable.
- `Vegetacion_tierra_MOD44B_2021_1grado.tif`: cobertura superficial vegetal
  continua de MOD44B 2021 y cobertura de sus datos, ambas entre 0 y 1. Procede
  del producto CMG de ICDC, Universität Hamburg, con resolución real de **0,5°**;
  el resumen agrega esa malla a 1°, sin atribuirle detalle de 15 segundos de arco.
  El ciclo MOD44B 2021 abarca **5 de marzo de 2021–4 de marzo de 2022**, no el
  año natural 2021. Su periodo se verifica en las etiquetas del resumen.

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
6. Cobertura vegetal: fracción física de superficie vegetada, entre 0 y 1.

`coberturas_tierra_1grado.tif` contiene **tres bandas**, en orden: cobertura
NASADEM, cobertura clasificada IGBP y cobertura de datos de vegetación.
**NoData permanece como `NaN`; cobertura de datos cero es un valor válido.**
La elevación media usa sus píxeles válidos. Las fracciones de ciudades y agua
usan los píxeles clasificados; no son mediciones biofísicas subpíxel. La nueva
cobertura vegetal usa las fracciones físicas válidas de MOD44B y tiene una
huella de datos independiente de la clasificación IGBP.

Las coberturas de datos usan como denominador **todas las celdas potenciales de
su propia fuente dentro de la celda de análisis**, incluidos los desconocidos.
Para vegetación son las celdas CMG de 0,5°; para NASADEM y las máscaras son sus
píxeles de 15″. Los denominadores se guardan en los metadatos de cada banda.
Debe consultarse la cobertura correspondiente antes de comparar una celda
parcial con una completamente conocida.

## Consultar vegetación entre 0 y 1

La cobertura vegetal es una media de estimaciones MOD44B válidas de 250 m;
puede no representar toda el área de cada celda CMG. La cobertura de datos
cuenta celdas CMG conocidas y no mide su cobertura interna ni su calidad.

Después de `preparar_datos`, `datos["Cobertura vegetal"]` contiene directamente
la fracción: **0 significa ausencia estimada de vegetación y 1 superficie
completamente vegetada**. Los valores intermedios conservan su significado;
por ejemplo, 0,37 representa una cobertura estimada del 37 %. Los desconocidos
son `NaN` y no se sustituyen por cero.

```python
vegetacion = datos["Cobertura vegetal"]
cobertura_datos = coberturas["Cobertura de datos de vegetación"]
latitud, longitud = 40.5, -3.5
fila, columna = int(90 - latitud), int(longitud + 180)
print(vegetacion[fila, columna], cobertura_datos[fila, columna])
```

La sexta banda de `tierra_1grado.tif` guarda la misma matriz y declara
`quantity=vegetated_surface_fraction`, unidad `1`. Es una estimación física de
cobertura superficial, no un NDVI normalizado ni una recodificación binaria del
bit de vegetación IGBP. La comprobación exige valores intermedios, rango 0–1
y correspondencia exacta entre valores válidos y cobertura de datos positiva.
La cobertura vegetal continua no participa en la suma de categorías exclusivas
ciudades/agua/vegetación de IGBP.

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

Desde la raíz del repositorio, después de publicar los cinco resúmenes:

```bash
MPLBACKEND=Agg marte/.venv/bin/python tierra/prototipo_analogos.py
```

Para el notebook, seleccionar el kernel existente `marte/.venv/bin/python` y
ejecutar las celdas en orden. El script permite `--catalogo`, `--revision` y
`--salida`. Por defecto los TIFF preparados y la vista de seis paneles se escriben
en `/tmp/hspace_tierra_productos/prototipo/`. La publicación debe verificarse
antes de borrar esos TIFF temporales.

Cada etapa del notebook llama a una función del script: catálogo, lectura y
validación, resumen, guardado y visualización. La figura mantiene las fracciones,
la cobertura vegetal y el albedo entre 0 y 1; el contraste de elevación y GHI entre percentiles 2 y 98
afecta solo a la imagen.

## Interpretación y atribución

NASADEM cubre su huella de adquisición; los huecos y regiones fuera de esa huella
permanecen desconocidos. NASA POWER representa una climatología anual; las
clases de suelo corresponden a 2021; la cobertura vegetal utiliza el ciclo
MOD44B 2021, del 5 de marzo de 2021 al 4 de marzo de 2022. No son observaciones
simultáneas de una misma fecha. El GHI de Marte es un modelo simplificado para Ls = 18,9°, y su
albedo Lambert bolométrico tiene una definición diferente del albedo POWER
superficial bajo todo cielo. Las unidades facilitan la exploración, pero una
comparación ambiental exige armonizar esas definiciones y escalas.

Las máscaras se derivan de Rolf Simoes/OpenGeoHub (2023),
DOI `10.5281/zenodo.8367523`, MODIS MCD12Q1.061, con suplemento Natural Earth.
Sus fracciones están bajo **CC BY-SA 4.0**. El cubo combinado, el ráster de
coberturas y la figura que incluyen esos derivados mantienen **CC BY-SA 4.0**
y la atribución, escrita también en los metadatos de salida. Fuentes de radiación:
NASA POWER. Elevación: NASA/JPL-Caltech NASADEM.
La cobertura vegetal añade MOD44B 2021, producto CMG de ICDC, Universität Hamburg,
bajo **CC BY 4.0**; su atribución se conserva. La licencia del cubo combinado,
las coberturas y la figura sigue siendo CC BY-SA 4.0 por los derivados IGBP que
también contienen.
