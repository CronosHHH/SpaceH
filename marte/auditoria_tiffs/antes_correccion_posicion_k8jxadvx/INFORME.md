# Auditoría de los TIFF y sus vistas PNG

Fecha: 9 de noviembre de 2026. GDAL 3.12.2, Python del sistema.

## Resultado

**94 comprobaciones pasan, 4 fallan y 1 queda como advertencia.** Se leyeron
los **1.476.468.000 píxeles** de los seis TIFF, por bloques. Las estadísticas
de esta auditoría son exactas; no proceden del muestreo de los archivos `.aux.xml`.

Los cuatro fallos corresponden a **georreferenciación de los mapas minerales**.
Sus valores y máscaras son correctos, pero requieren corregir su posición antes
de cruzarlos espacialmente con otras capas. No se han modificado los TIFF, los
originales, las etiquetas, los PNG ni los generadores durante esta auditoría.

| Capa | Rango observado de valores válidos | Píxeles válidos | Dictamen |
|---|---:|---:|---|
| [OSP1](../olivine_osp1_equ_map.tiff) | 1,040000–1,332499 | 1.529.424 · 1,47514 % | Valores correctos; corregir posición |
| [OSP2](../olivine_osp2_equ_map.tiff) | 1,040004–1,328869 | 29.352 · 0,02831 % | Valores correctos; muy escaso; corregir posición |
| [OSP3](../olivine_osp3_equ_map.tiff) | 0,831068–1,025506 | 23.597 · 0,02276 % | Valores correctos; muy escaso; corregir posición |
| [Piroxeno BD2000](../pyroxene_bd2000_equ_map.tiff) | 0,010000–0,109973 | 39.904.582 · 38,48822 % | Valores correctos; corregir posición |
| [MOLA](../1-Mars_MGS_MOLA_DEM_mosaic_global_463m.tif) | −8.201–21.241 m | 100 % | Coherente para relieve regional; advertencia sobre malla |
| [GHI](../GHI_marte.tif) | 0–142,867126 W/m² | 100 % | Coherente con su modelo simplificado; no es observación |

Porcentajes calculados sobre el número de píxeles de cada ráster, **no sobre el
área real de Marte**. Los valores minerales son parámetros espectrales
adimensionales; no indican directamente porcentajes de mineral.

## 1. Minerales: conversión numérica correcta, posición incorrecta

Se contrastó cada TIFF con su pareja `.IMG`/`.LBL` de
[origen_ds_minerales](../origen_ds_minerales/). Los binarios se leyeron además
directamente con NumPy como enteros de 16 bits little endian, independientemente
del controlador PDS de GDAL.

Comprobaciones completas:

- Cada IMG tiene 207.360.000 bytes: 14.400 × 7.200 × 2.
- En todos los píxeles válidos: `TIFF = Float32(IMG × SCALING_FACTOR + OFFSET)`.
  **Diferencia máxima observada: cero.**
- La máscara `IMG == -32768` coincide exactamente con la máscara NoData del TIFF.
  **Cero discrepancias** en los cuatro productos.
- No hay NaN o infinitos no enmascarados.
- Mínimos, máximos, medias y desviaciones son coherentes con las etiquetas,
  admitiendo 0,0005 de tolerancia por sus tres decimales publicados.
- Float32 conserva los valores ya escalados; no hay una segunda escala pendiente.
- Las cuatro capas comparten dimensiones, resolución y geotransformación.

`gdal_translate -ot Float32 -unscale` es adecuado para la conversión de valores.
El problema encontrado está en la interpretación de los offsets de proyección
PDS. Las etiquetas declaran un mapa global simétrico, centrado en 0°/0°.
Los TIFF actuales sitúan su centro en **X = −1.481,78 m, Y = +1.481,78 m**:
**un píxel al oeste y un píxel al norte**. Es un desplazamiento por eje; su
distancia diagonal es de unos 2,10 km.

Al abrir las mismas etiquetas con `PDS_SampleProjOffset_Shift=-0.5` y
`PDS_LineProjOffset_Shift=-0.5`, el centro pasa a **(0,0)**. Esta comprobación
se ejecutó en memoria, sin reemplazar los archivos. Las opciones y el problema
de interpretación de offsets están documentados en el
[controlador PDS de GDAL](https://gdal.org/en/stable/drivers/raster/pds.html#georeferencing).

### Método de conversión corregido

Este bloque **no se ha ejecutado**. Desde la carpeta principal de Marte, crea
copias en una carpeta distinta para poder compararlas:

```bash
mkdir -p tiffs_corregidos
for nombre in olivine_osp1_equ_map olivine_osp2_equ_map olivine_osp3_equ_map pyroxene_bd2000_equ_map; do
  gdal_translate \
    --config PDS_SampleProjOffset_Shift -0.5 \
    --config PDS_LineProjOffset_Shift -0.5 \
    -of GTiff -ot Float32 -unscale \
    -co COMPRESS=LZW -co TILED=YES \
    "origen_ds_minerales/${nombre}.LBL" \
    "tiffs_corregidos/${nombre}.tiff"
done
```

Nota de los originales: `RECORD_BYTES × FILE_RECORDS` en estas etiquetas da
la mitad del tamaño real del binario. Las dimensiones de imagen, los 16 bits
por muestra y el tamaño de cada archivo sí concuerdan. No se ha usado ese
producto de registros como criterio de integridad.

## 2. Por qué los PNG del olivino aparecen casi negros

Se abrieron e inspeccionaron los seis PNG. La escasez de valores en OSP2/OSP3
ya está en los originales: no es pérdida de datos en los TIFF. Un píxel sin
dato no debe interpretarse como concentración cero ni como ausencia demostrada
de olivino.

El [generador de PNG](../generar_pngs.sh) añade dos limitaciones de visualización:

1. **Reducción al 25 % con vecino más próximo.** Conserva una muestra de cada
   bloque de 4 × 4 y puede saltarse pequeñas detecciones.
2. **Contraste automático con estadísticas aproximadas.** En OSP3, el mínimo
   almacenado en la caché es 0,980749, mientras que el mínimo real es 0,831068.
   Muchos valores válidos quedan negros al escalar la vista previa.

| PNG | Celdas de 4 × 4 con algún dato original | Muestras válidas conservadas | De ellas, pintadas en negro |
|---|---:|---:|---:|
| OSP1 | 134.636 | 95.551 | 1.978 · 2,07 % |
| OSP2 | 3.890 | 1.800 | 7 · 0,39 % |
| OSP3 | 3.636 | 1.463 | **959 · 65,55 %** |

En OSP3, 958 de esas muestras negras están por debajo del mínimo aproximado
de la caché. El PNG no permite distinguirlas del fondo sin datos. Además,
los tres OSP no deben interpretarse con una regla común de «más claro = más
olivino»; sus definiciones espectrales son diferentes.

El método de vista previa debe calcular el contraste sobre los valores válidos
con rangos fiables y mostrar NoData de forma diferenciada. Para visualizar
detecciones escasas, conviene agregar los bloques ignorando NoData y/o incluir
una máscara de presencia. Esa agregación sería solo de visualización.
Conservar el TIFF con sus valores originales para el análisis.

## 3. MOLA: datos plausibles y una advertencia de georreferenciación

Se leyeron sus 1.061.683.200 píxeles. No hay huecos NoData y las elevaciones
−8.201 a 21.241 m son plausibles para Marte. El PNG muestra relieve reconocible.
Que no haya huecos no significa que cada píxel sea una medida directa:
el producto incluye interpolación entre observaciones.

La [ficha USGS](https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m)
describe alturas sobre el areoide GMM-2B, 46.080 × 23.040 píxeles, esfera de
radio 3.396.190 m y resolución nominal de 463,0835744 m/píxel. El TIFF local
tiene 463,09354155 m/píxel y conserva el centro en cero. Frente a la extensión
nominal, los bordes difieren unos **229,64 m en X** y **114,82 m en Y**.

Se clasifica como **advertencia**, no como corrupción demostrada. No existe
en las carpetas de origen un raw/etiqueta/checksum independiente para comprobar
la exportación exacta de este producto. No se ha cambiado su CRS ni su tamaño
de píxel a partir de esa diferencia. Sirve para explorar relieve regional;
su resolución no permite verificar obstáculos pequeños de un lugar de aterrizaje.

## 4. GHI: pasa los tests de su modelo, con límites claros

El [generador de GHI](../origen_ds_gui_Y_albeolo/generar_ghi.py) calcula media
diaria para **Ls = 18,9°**, con flujo solar fijo de **590 W/m²** y transmisión
atmosférica constante del **75 %**. No consulta Mars Climate Database y no
representa un promedio anual ni una observación de la radiación local.

Tests independientes del cálculo analítico del generador:

- Integración de irradiancia instantánea con 1.440 pasos por sol:
  error máximo frente al TIFF **0,00021208 W/m²**, inferior a 0,001.
- Media global ponderada por área: **110,624026 W/m²**,
  coherente con `590 × 0,75 / 4 = 110,625 W/m²`.
- Valores finitos y no negativos; variación longitudinal nula, como espera el modelo.
- 2.880 ceros coherentes con noche polar austral en esa estación.
- Malla de 360 × 180, paso 1° y metadatos de unidades/estación correctos.

El PNG de 90 × 45 es pequeño pero su patrón de franjas es coherente con ese
modelo. GHI sirve para prototipos con esos supuestos; no valida diferencias
reales de polvo, atmósfera o clima entre sitios. El generador ahora está en una
subcarpeta y escribe junto a sí mismo: ejecutarlo no actualiza automáticamente
el TIFF ubicado en la carpeta principal.

## 5. Hallazgo adicional: albedo

No hay un TIFF de albedo entre los seis examinados. Se revisaron el
[script de origen](../origen_ds_gui_Y_albeolo/generar_albedo.py) y el
[PNG descargado](../imagenes/tes_albedo.png).

El PNG tiene canal gris y alfa. Sus **126.720 píxeles transparentes** contienen
gris cero. El generador elimina alfa con `convert('L')` y transforma esos
píxeles en albedo 0,08 válido: **pérdida de la máscara de ausencia de datos**.
Además hay 72.676 píxeles opacos de gris 255 cuyo significado debe confirmarse
antes de descartarlos solo por su intensidad.

La escala de visualización 0–254 → 0,08–0,32 está documentada por
[ASU](https://www.mars.asu.edu/mosaictools/cutMap/), pero reconstruir valores desde
el PNG produce datos cuantizados. Para un análisis mineralógico/climático,
priorizar el [producto científico TES y su etiqueta](https://tes.mars.asu.edu/products/).
También hay que comprobar latitudes planetocéntricas frente al CRS elipsoidal
asignado por el script.

Las [notas del proyecto](../docu/NOTAS.md) atribuyen GHI parcialmente a MCD y
presentan `GTI = GHI × cos(pendiente)` y una temperatura de equilibrio como
resultados físicos completos. Esas fórmulas omiten, entre otros factores,
orientación solar/de laderas e inercia térmica. No están validadas por estos tests.

## Uso conjunto de las capas

1. Corregir el desplazamiento demostrado de los mapas minerales.
2. Tratar `NoData` como desconocido, sin sustituirlo automáticamente por cero.
3. Definir un CRS marciano y una cuadrícula común: MOLA, OMEGA y GHI tienen
   resoluciones y definiciones de CRS diferentes. Igualar dimensiones o cambiar
   solamente el nombre del CRS no los alinea.
4. Conservar la máscara de validez al agregar minerales; la cobertura desigual
   puede sesgar una búsqueda de análogos. Distinguir indicadores espectrales,
   elevación observada/interpolada y radiación modelada.

## Repetir las comprobaciones

Desde la carpeta principal de Marte:

```bash
/usr/bin/python3 validar_tiffs.py
```

Se necesitan NumPy, GDAL/osgeo y Pillow (disponibles en el entorno utilizado).
La salida de la última ejecución está en [ejecucion.txt](./ejecucion.txt), y
los datos y tests en [resultados.json](./resultados.json). El script devuelve
código **1** mientras sigan fallando las cuatro comprobaciones espaciales.
Si se crean copias corregidas en una subcarpeta, no se validarán automáticamente:
el validador examina los seis TIFF de la carpeta principal.

La coincidencia con los IMG comprueba la conversión respecto de los originales
locales; no sustituye un checksum del archivo oficial ni la validación científica
de las detecciones. El catálogo externo DSMAP no pudo recuperarse; no se ha
afirmado haberlo contrastado.
