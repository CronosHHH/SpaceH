# Cobertura vegetal: proporción de superficie entre 0 y 1

Generador: [generar_vegetacion.py](../origen_ds_vegetacion/generar_vegetacion.py).
Auditoría: [vegetacion.json](../auditoria/vegetacion.json).

La variable cuantitativa es **cobertura vegetal**, incluyendo vegetación arbórea
y no arbórea. Un valor de 0,55 representa una fracción estimada de 55 % de
superficie vegetada en las áreas con recuperación válida. No representa NDVI,
la probabilidad de una clase ni el código binario de la máscara IGBP.

## Fuente, fechas y resolución

Se utiliza [MODIS MOD44B.061, Vegetation Continuous Fields](https://modis-land.gsfc.nasa.gov/vcc.html),
en su [mosaico global de ICDC, Universidad de Hamburgo](https://www.geo.uni-hamburg.de/en/service/icdc/data/land/modis-vcf-forest.html).
ICDC agrega las recuperaciones MODIS de 250 m a una malla de **0,5°**, con
720 columnas y 360 filas. Esta es la resolución disponible en este archivo;
no se presenta como un mapa vegetal de 463 m ni de 250 m.

Se selecciona el ciclo etiquetado **2021**. Los atributos temporales del NetCDF
declaran **2021-03-05 a 2022-03-04**; no es un promedio del año natural enero–diciembre.
El nombre del archivo contiene `20210306`; se conserva la fecha del nombre y
se documenta el intervalo declarado en los atributos, sin corregirlos por suposición.
La URL completa y el SHA256 de la versión descargada están fijados en el script.
El NetCDF ocupa 5.197.612 bytes y GDAL lo lee directamente; no hacen falta nuevas
dependencias ni descargas masivas.

## Conversión física

El campo `novegetationfraction` contiene porcentajes de superficie no vegetada.
La conversión es:

```python
vegetacion = (100.0 - novegetationfraction) / 100.0
```

Se valida el intervalo de origen 0–100, su unidad `percent`, la geometría y la
ausencia de escala adicional. Como contraste independiente, la suma de los
campos bosque, otra vegetación y no vegetado cierra al 100 % con un error
máximo de un punto porcentual debido al redondeo publicado.

El relleno **127** queda como `NaN`/NoData. No se transforma océano desconocido
en cero vegetación. Se exige un número positivo de recuperaciones útiles de
origen; se mantienen los niveles de calidad publicados sin aplicar un filtro
adicional por nubosidad. Los indicadores de calidad originales siguen
disponibles en el NetCDF y deben considerarse para análisis posteriores.

Los valores válidos de esta versión son **0–0,99**, con **100 niveles** de paso
aproximado 0,01. No se fuerza el máximo a 1 mediante normalización mínimo–máximo.
El paso numérico no es una estimación de precisión científica. La fracción es
una estimación del producto sobre sus recuperaciones válidas, no una garantía
de cobertura observacional completa dentro de cada celda.

## GeoTIFF publicados

- `Vegetacion_tierra_MOD44B_2021_0p5grado.tif`: una banda Float32 de cobertura
  vegetal en la malla nativa 0,5°, extensión global y NoData `NaN`.
- `Vegetacion_tierra_MOD44B_2021_1grado.tif`: dos bandas Float32 a 1°. La primera
  es la media de las celdas de 0,5° disponibles en cada bloque 2 × 2. La segunda
  es la fracción de esas cuatro celdas con datos: 0, 0,25, 0,5, 0,75 o 1.

La segunda banda indica **cobertura de datos**, no cobertura vegetal ni calidad
instrumental. Tampoco describe la proporción de recuperaciones de 250 m válidas
dentro de cada celda CMG. La media a 1° usa celdas angulares disponibles con igual
peso, sin ponderación geodésica ni por número de recuperaciones subyacentes.
Donde ninguna celda tiene datos, la vegetación sigue siendo `NaN` y la cobertura
de datos vale cero.

El archivo CF declara coordenadas geográficas en grados y una geotransformación
exacta `(-180, 0.5, 0, 90, 0, -0.5)`, pero no declara CRS formal. Se codifican
esas coordenadas angulares como **EPSG:4326**, convención explícita del proyecto,
sin remuestrear el mapa nativo. El resumen a 1° coincide con la cuadrícula de
los demás productos. Su media se contrasta además con una agregación independiente
de Rasterio, conservando exactamente la máscara de ausencia de datos.

## Obtener y usar

```bash
marte/.venv/bin/python tierra/origen_ds_vegetacion/generar_vegetacion.py
```

`--fuente` admite el NetCDF revisado ya descargado; `--salida` y `--informe`
permiten cambiar las rutas. Por defecto los TIFF se crean en
`/tmp/hspace_tierra_productos/`. El publicador exige la auditoría completa y
sus hashes antes de subirlos y eliminarlos localmente.

El notebook carga el resumen directamente de Hugging Face a memoria.

```python
vegetacion = datos["Cobertura vegetal"]
datos_disponibles = coberturas["Cobertura de datos de vegetación"]
# Ejemplo: filtrar estimaciones bajas, conservando por separado los desconocidos.
seleccion = np.isfinite(vegetacion) & (datos_disponibles == 1) & (vegetacion < 0.2)
```

El cubo `tierra_1grado.tif` conserva seis variables: la sexta banda pasa a ser
esta cobertura vegetal física. El ráster de coberturas tiene ahora tres bandas,
siendo la tercera la cobertura de datos de vegetación. Las categorías y fracciones
IGBP anteriores se mantienen como productos de clasificación y exclusión; no se
confunden con la nueva estimación.

## Atribución

DiMiceli et al., NASA MOD44B.061, DOI `10.5067/MODIS/MOD44B.061`; mosaico global
de ICDC, CEN, Universidad de Hamburgo, DOI `10.25592/uhhfdm.11195`.
Agradecimiento: Thanks to ICDC, CEN, University of Hamburg for data support.
La distribución ICDC está bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
El cubo combinado mantiene CC BY-SA 4.0 porque también incorpora las fracciones
de ciudades y agua derivadas del mosaico OpenGeoHub.
