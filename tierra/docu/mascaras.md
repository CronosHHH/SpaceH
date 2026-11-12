# Máscaras terrestres: ciudades, agua y vegetación

Generador: [generar_mascaras.py](../origen_ds_mascaras/generar_mascaras.py).
Auditoría: [mascaras.json](../auditoria/mascaras.json).

## Fuentes y alcance

Se utiliza la banda **LC_Type1 (IGBP) de MCD12Q1 versión 6.1 para 2021**,
en el mosaico GeoTIFF preparado por Rolf Simoes / OpenGeoHub:
[Zenodo, DOI 10.5281/zenodo.8367523](https://zenodo.org/records/8367523).
El registro lo distribuye bajo **CC BY-SA 4.0**; los dos GeoTIFF derivados de
esta carpeta se distribuyen con esa misma
[licencia CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Atribución: Rolf Simoes /
OpenGeoHub (2023), *MODIS MCD12Q1 Land Cover and Land Use Time Series Global
Mosaics*, v20230818, y NASA MCD12Q1.061,
[DOI 10.5067/MODIS/MCD12Q1.061](https://doi.org/10.5067/MODIS/MCD12Q1.061).

El [catálogo del productor en Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD12Q1)
describe la leyenda IGBP. Las clases se agrupan así:

| Grupo | Clases IGBP | Interpretación |
|---|---|---|
| Ciudades | 13 | Urbano y construido; al menos 30 % de superficie impermeable |
| Agua MODIS | 17 | Masas de agua permanentes, incluidos océanos donde están clasificados |
| Vegetación | 1–12 y 14 | Bosques, matorral, sabana, herbáceas, humedales, cultivos y mosaicos |
| Otros conocidos | 15–16 | Nieve/hielo permanente y terreno desnudo o muy poco vegetado |
| Desconocido | 0 del mosaico o fuera de él | Ausencia de clasificación; no significa terreno disponible |

Los humedales IGBP 11 se incluyen en vegetación, no en la máscara de agua libre.
La clase 16 puede contener hasta un 10 % de vegetación. La clasificación de una
celda no permite asegurar ausencia de edificios, agua o plantas a escala local.
No se ha aplicado un filtro adicional de calidad MODIS, por lo que se conserva
la clasificación publicada, con sus incertidumbres.

El mosaico tiene huecos en océano abierto y excluye la Antártida. Para completar
**solo los píxeles sin clasificación que caen en océano**, se rasterizan los
[polígonos de océano Natural Earth](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-ocean/),
escala **1:10.000.000**. Natural Earth es de
[dominio público](https://www.naturalearthdata.com/about/terms-of-use/).
Se fija una revisión del repositorio y su SHA256. Las clases MODIS conocidas
nunca se sustituyen por esos polígonos. Los huecos sobre tierra y Antártida
permanecen desconocidos. La costa de Natural Earth tiene menor detalle que la
malla de salida: rasterizarla a 15″ no mejora su exactitud costera.

## Productos

`Mascaras_tierra_MODIS_2021_15arcsec.tif` es una banda UInt8 en EPSG:4326,
malla global de **86.400 × 43.200** celdas, origen −180°/+90°, píxel de
**1/240° = 15 segundos de arco**, unos **464 m en el ecuador**.
El ancho este-oeste disminuye con la latitud. Se usa vecino más próximo
calculado desde los centros de los píxeles originales, cuyo origen real es
87,37° N; no se limita a cambiar la etiqueta de georreferencia.

| Valor | Significado |
|---:|---|
| 0 | Otros conocidos |
| 1 | Ciudades |
| 2 | Agua clasificada por MODIS |
| 4 | Vegetación |
| 10 | Agua de suplemento oceánico: bits 2 + 8 |
| 255 | NoData / desconocido |

Para obtener una **proporción física de superficie vegetada entre 0 y 1**, se
utiliza el [producto MOD44B de cobertura vegetal](./vegetacion.md), que alimenta
la sexta banda del cubo y el notebook. El bit 4 y la antigua fracción IGBP
continúan describiendo clases de suelo, no cobertura biofísica subpíxel.

Puede utilizarse como máscara categórica o mediante bits, comprobando primero
NoData. **No se deben promediar directamente sus códigos numéricos.**

```python
with rasterio.open(archivo) as src:
    # Leer una ventana, no el planeta entero.
    mascara = src.read(1, window=ventana)
conocido = mascara != 255
ciudades = conocido & ((mascara & 1) != 0)
agua = conocido & ((mascara & 2) != 0)
vegetacion = conocido & ((mascara & 4) != 0)
sin_estos_grupos = conocido & ~(ciudades | agua | vegetacion)
```

`Fracciones_mascaras_tierra_MODIS_2021_1grado.tif` contiene cuatro bandas
Float32 de **360 × 180** celdas globales alineadas a 1°:

1. Fracción ciudades.
2. Fracción agua, incluido el suplemento oceánico.
3. Fracción vegetación.
4. Cobertura clasificada.

Las tres primeras son fracciones de **píxeles clasificados** y son `NaN` cuando
no hay clasificación; la cuarta divide los píxeles conocidos por los 57.600
píxeles de la celda de 1°. Un píxel mixto etiquetado vegetación contribuye como
una celda vegetada completa: estas bandas no estiman cobertura biofísica
subpíxel. Son proporciones de píxeles angulares, no de área geodésica.
La cobertura debe acompañar a cualquier filtro de candidatos. Una fracción
pequeña no certifica ausencia del grupo.

## Memoria y comprobaciones

La fuente comprimida ocupa **132.512.453 bytes**, no decenas de GB. Se descarga
en `/tmp` y se comprueba su MD5 publicado. El proceso usa franjas de 1° para
mantener acotada la memoria y escribe un GeoTIFF comprimido por bloques.

Se detectó un defecto importante en los **overviews del mosaico de origen**:
una lectura reducida produce categorías 18/19 que no existen en sus píxeles
nativos. El generador utiliza exclusivamente ventanas del nivel nativo, sin
`out_shape` ni reducciones de overviews. Valida las clases nativas 0–17; la
auditoría registra las categorías espurias observadas en una muestra reducida
para advertir contra su reutilización.

Se comprueban la geometría real del origen, la leyenda, los rangos 0–1, la
exclusión mutua de clases, la conservación de desconocidos y la escritura
completa de los píxeles mediante SHA256. También se validan controles espaciales
en Madrid, Atlántico, Amazonia, Sahara y Antártida. El informe incluye hashes,
histogramas, licencia y tamaño de los dos productos.

La ejecución completa del 11 de noviembre de 2026 validó **3.732.480.000 píxeles**
de la máscara global. El TIFF detallado comprimido ocupa **18.471.392 bytes** y
el de fracciones **234.927 bytes**. A 1° hay **59.194 celdas con alguna
clasificación** y **5.606 completamente desconocidas**. Pasaron los cinco
controles espaciales y la comprobación de escritura completa.

Desde la raíz del repositorio:

```bash
marte/.venv/bin/python tierra/origen_ds_mascaras/generar_mascaras.py
```

`--fuentes`, `--salida` y `--informe` permiten cambiar las rutas. Por defecto los
TIFF se generan en `/tmp/hspace_tierra_productos`; el script no publica ni
elimina productos. El notebook utiliza las fracciones de ciudades y agua a 1°;
la vegetación cuantitativa procede del resumen MOD44B separado. Así se evita
descargar la máscara detallada completa durante la exploración global.
