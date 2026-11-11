# NASADEM reducido a una malla de unos 464 metros

Fuente: [NASADEM HGT v001, NASA/JPL](https://www.earthdata.nasa.gov/data/catalog/lpcloud-nasadem-hgt-001),
DOI `10.5067/MEASURES/NASADEM/NASADEM_HGT.001`, distribuido como COG por
[Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/dataset/nasadem).
NASADEM reprocesa principalmente las observaciones SRTM de febrero de 2000;
la publicación es de 2020. No representa una medición de relieve de 2026.

## Productos

- `NASADEM_tierra_15arcsec.tif`: una banda Int16 de elevación en metros sobre
  el geoide **EGM96**, CRS horizontal **EPSG:4326**, 86.400 × 43.200 píxeles,
  extensión global −180°…180°, −90°…90° y resolución 1/240° = 15 segundos de arco.
- `NASADEM_tierra_1grado.tif`: dos bandas Float32, 360 × 180 píxeles. La primera
  contiene la **media de elevaciones válidas** de cada bloque de 240 × 240;
  la segunda, su **fracción de cobertura válida** entre 0 y 1. Permite trabajar
  en el prototipo sin descargar el mosaico grande.

La dimensión de 15 segundos de arco equivale a aproximadamente **463,8 m
este-oeste y 460,7 m norte-sur en el ecuador**; el ancho este-oeste disminuye
con la latitud. No es una cuadrícula de 463 m constantes ni de áreas iguales.

El catálogo consultado contiene **14.520 teselas** de un grado. La cobertura
nominal de NASADEM se describe como terrestre entre 56° S y 60° N; este catálogo
contiene orígenes de tesela desde −56° hasta +60° y sus bordes pueden alcanzar
61° N. Se conservan todas las teselas disponibles. El resto del globo, incluidos
los polos y los océanos sin tesela, permanece como **NoData = −32768**. Una
elevación **cero** proporcionada como válida por NASADEM sigue siendo un dato.
No se inventa una superficie oceánica ni se sustituye NASADEM por otro DEM.

## Método y almacenamiento

[generar_nasadem.py](../origen_ds_nasadem/generar_nasadem.py) consulta el catálogo
STAC y pide al servicio remoto una versión **ya reducida de 240 × 240 píxeles**
de cada tesela. Activa `resampling=average` y `reproject=average`, sin paleta,
sombreado, estiramiento ni conversión de unidades. Los datos recibidos son
elevaciones Int16 y una banda alfa de cobertura; el redondeo a metros enteros
del servicio se conserva.

El servicio puede utilizar las pirámides del COG. Por ello la conversión se
documenta como **reducción por media del servicio y redondeo Int16**: no se
afirma que cada resultado sea la media exacta demostrada de 225 muestras
nativas. Las comprobaciones nativas informan las diferencias observadas.

Los originales de 30 m **nunca se almacenan localmente**. Como máximo hay un
conjunto acotado de pequeñas respuestas en memoria y un único TIFF final
comprimido en `/tmp`. El mosaico usa BigTIFF, compresión DEFLATE y bloques
dispersos de 240 × 240; los bloques sin fuente no ocupan su tamaño lógico en
disco. El archivo global tiene una dimensión lógica de unos 7,5 GB sin compresión,
pero solo se escriben las teselas de cobertura disponible y se comprimen.

El diario `.progreso.jsonl` permite reanudar una descarga interrumpida. Antes
de omitir una tesela se vuelve a leer su ventana del TIFF y se compara su SHA256;
así no se confía en escrituras que pudieran haber quedado pendientes en GDAL.
Un error de red no se convierte en una tesela vacía: se reintenta o se detiene
la ejecución sin declarar el producto completo. El orden físico de los bloques
puede variar por la concurrencia; el hash del archivo verifica una publicación
concreta, mientras que los hashes de ventanas verifican los valores científicos.

## Validación

- Se comprueban dimensiones, posición, resolución, CRS y máscara de cada respuesta.
- Todos los valores válidos deben estar entre −500 y 9.000 m; estos límites
  permiten depresiones reales y las cumbres terrestres, detectando errores de
  unidades o valores de relleno.
- Se vuelve a leer el mosaico completo por bloques y su número de píxeles válidos
  debe coincidir con la suma del diario.
- Se comprueba expresamente que un bloque polar no escrito se lea como NoData.
- Tres teselas se vuelven a consultar al proveedor y deben ser idénticas a las
  ventanas guardadas.
- [validar_muestras_nativas.py](../origen_ds_nasadem/validar_muestras_nativas.py)
  contrasta tres muestras (España, mar Muerto e Himalaya) con ventanas de 15 × 15
  píxeles a aproximadamente un segundo de arco. El valor reducido debe estar
  dentro del rango nativo y se registra la diferencia respecto de su media.

Los resultados y hashes están en [nasadem.json](../auditoria/nasadem.json) y
[nasadem_muestras_nativas.json](../auditoria/nasadem_muestras_nativas.json).

La ejecución del 11 de noviembre de 2026 procesó las **14.520 teselas** en unos
10,4 minutos y produjo un TIFF de **584.900.273 bytes**, con **836.352.000 píxeles
válidos** y rango **−418 a 8.588 m**. El máximo es menor que el de los datos
nativos porque se ha reducido su resolución. Las 14.520 ventanas coinciden con
sus hashes de origen reducidos y el resumen conserva todas sus medias y
coberturas. Las diferencias entre las muestras reducidas y las medias de las
ventanas nativas fueron −0,164 m en España, −0,120 m en el mar Muerto y −6,493 m
en el Himalaya; estas tres muestras no constituyen una estimación global del error.

## Repetir

Desde la raíz del repositorio, usando el entorno de las dependencias del proyecto:

```bash
marte/.venv/bin/python tierra/origen_ds_nasadem/generar_nasadem.py
marte/.venv/bin/python tierra/origen_ds_nasadem/validar_muestras_nativas.py
```

Las opciones `--salida`, `--resumen`, `--catalogo`, `--informe` y `--workers`
permiten elegir las rutas y concurrencia. `--limite` sirve exclusivamente para
pruebas parciales; el informe no las declara un producto global completo.
El programa no publica ni elimina el resultado: la publicación verifica sus
hashes en Hugging Face antes de borrar los archivos TIFF temporales.
