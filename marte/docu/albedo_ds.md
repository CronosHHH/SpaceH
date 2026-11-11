# Albedo de Marte: origen, conversión y compatibilidad

Verificado el 11 de noviembre de 2026. Producto: `marte/Albedo_marte.tif`.
Generador: [generar_albedo.py](../origen_ds_gui_Y_albeolo/generar_albedo.py).
Resultados reproducibles: [albedo.json](../auditoria_tiffs/albedo.json).

## Fuente y significado

Se utiliza el **VICAR numérico** enlazado como «Download raw numeric values» en
[ASU — TES Albedo](https://www.mars.asu.edu/data/tes_albedo/), del instrumento TES
de Mars Global Surveyor. Es albedo Lambert bolométrico, adimensional. Referencia:
Christensen et al. (2001), *JGR*, 106, 23.823–23.871, indicada por ASU.

Las URL completas de las peticiones WMS están en el script y el informe JSON.
Se pide el VICAR a `alb32`, capa `TES_Lambert_Albedo_numeric`, con
`BBOX=0,-90,360,90`, 2.880 × 1.440 píxeles. El PNG oficial de la capa
`TES_Lambert_Albedo` se pide con `BBOX=-180,-90,180,90` y las mismas dimensiones.
**Solo se usa el alfa del PNG** para reconocer la ausencia de datos. Ningún
valor de albedo se calcula a partir de sus colores.

Esta versión numérica del proveedor está cuantizada: tiene **255 niveles válidos**,
con paso aproximado de **0,000944882**. Float32 conserva esos niveles, sin añadir
precisión científica. Se conserva el rango original **0,080944881–0,320944875**;
no se recorta el máximo a 0,32. La resolución espacial y la cuantización tampoco
son una estimación de la incertidumbre instrumental.

Se examinó también el [producto PDS antiguo](https://pds-geosciences.wustl.edu/missions/mgs/tesspecial.html).
Difiere del mapa actual y su etiqueta no declara NoData. No se mezclaron sus
valores con la máscara de la versión actual.

## Conversión sin remuestreo

- Se valida la estructura VICAR: una banda Float32 little endian, BSQ, sin prefijos
  de línea ni registros binarios adicionales.
- Se permutan 1.440 columnas para pasar de 0–360° a −180–180°, sin invertir el eje
  este/oeste. El centro del primer píxel es −179,9375°, +89,9375°.
- La geotransformación GDAL es `(-180, 0.125, 0, 90, 0, -0.125)`, norte arriba.
- ASU declara coordenadas planetocéntricas. El VICAR no incluye CRS ni radio:
  se codifica la cuadrícula angular sobre la **esfera del proyecto de 3.396.190 m**,
  `+proj=longlat +R=3396190 +no_defs`, como el notebook. Esta es una convención
  explícita del proyecto; no se atribuye ese radio al archivo descargado.
- Los **126.720 píxeles transparentes** del PNG se guardan como `NaN`/NoData.
  Los **4.020.480 valores válidos** se conservan exactamente. No se interpreta
  el valor 0,08 como NoData de forma general: se comprueba la coincidencia con
  el alfa de esta versión y la máscara se obtiene exclusivamente de ese alfa.
- El TIFF resultante es Float32, una banda, comprimido y organizado en bloques.
  Sus etiquetas incluyen fuente, máscara, unidades, tratamiento y hashes.

El script comprueba los hashes de las fuentes antes de convertir. El encabezado
VICAR contiene una fecha de generación variable; por eso su hash estable se
calcula sobre el contenido numérico posterior a `LBLSIZE`, no sobre el archivo
entero. Si ASU cambia el producto, el script se detiene y exige revisar los
nuevos datos antes de actualizar los hashes.

## Compatibilidad comprobada

Se usaron los seis originales de `Renato-R-V/hspace-datasets`, revisión
`e88f169c94dd8a61e38d43333a3b9a81abd82073`. Se repitió el método del notebook:
media de valores válidos sobre la malla planetocéntrica de **360 × 180 celdas
de 1°**, con el tratamiento especial ya documentado para GHI.

| Capa | Celdas válidas a 1° |
|---|---:|
| MOLA | 64.800 |
| GHI modelado | 64.800 |
| Albedo TES | 63.360 |
| Olivino OSP1 | 5.170 |
| Olivino OSP2 | 483 |
| Olivino OSP3 | 660 |
| Piroxeno BD2000 | 39.737 |

Todas las capas se alinean correctamente. En albedo, la comparación independiente
con medias de bloques nativos de **8 × 8 píxeles** da un error máximo de
**1,49 × 10⁻⁸**, compatible con el redondeo Float32. La máscara a 1° coincide
exactamente con los bloques sin ningún dato: quedan **1.440 celdas NoData**.
Los bloques parcialmente cubiertos representan la media de los píxeles válidos.

La compatibilidad se confirma tras la alineación; las resoluciones nativas de
MOLA, OMEGA, TES y GHI son diferentes. Se mantienen la advertencia previa sobre
los bordes de MOLA y las limitaciones físicas del GHI modelado.

## Repetir

Desde la raíz del repositorio, con las dependencias de `marte/requirements.txt`:

```bash
marte/.venv/bin/python marte/origen_ds_gui_Y_albeolo/generar_albedo.py
marte/.venv/bin/python marte/origen_ds_gui_Y_albeolo/generar_albedo.py --comprobar-compatibilidad
```

Por defecto descarga y conserva las dos fuentes en `fuentes_albedo/`, junto al
script, y escribe el TIFF en `marte/`. No sube archivos automáticamente.
`--fuentes`, `--salida` y `--informe` permiten elegir otras rutas.
`--revision` fija el commit de referencia de Hugging Face. Si las seis capas ya
están cacheadas, puede repetirse la comprobación con `HF_HUB_OFFLINE=1` y la
revisión anterior sin volver a descargar los originales.

El notebook carga `Albedo_marte.tif` con `hf_hub_download`, igual que las otras
capas. El cubo `prototipo_alineado/marte_1grado.tif` tiene siete bandas, en orden:
MOLA, GHI, albedo TES, OSP1, OSP2, OSP3 y BD2000; cada banda incluye su descripción
y unidad. La vista conjunta muestra los siete paneles.
