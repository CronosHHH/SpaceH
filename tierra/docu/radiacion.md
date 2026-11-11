# Radiación y albedo terrestres

Fuente: [NASA POWER — servicios ArcGIS](https://power.larc.nasa.gov/docs/services/arcgis/),
servicio científico [POWER_CLIMATOLOGY_RADIATION_LST](https://gis.earthdata.nasa.gov/portal/rest/services/POWER/POWER_CLIMATOLOGY_RADIATION_LST/ImageServer).
Consulta y validación: 11 de noviembre de 2026.

## Productos y unidades

| Archivo | Variable POWER | Significado | Unidad |
|---|---|---|---|
| `GHI_tierra.tif` | `ALLSKY_SFC_SW_DWN` | Irradiancia solar descendente total sobre superficie horizontal bajo todo cielo, media anual | W/m² |
| `Albedo_tierra.tif` | `ALLSKY_SRF_ALB` | Albedo superficial bajo todo cielo, media anual | adimensional, 0–1 |

Ambos mapas tienen **360 × 180 celdas globales de 1°**, EPSG:4326, extensión
−180°…180° / −90°…90°, centros en semigrados y norte arriba. La transformación
GDAL es `(-180, 1, 0, 90, 0, -1)`. Es la resolución nativa del producto de
radiación; equivale aproximadamente a **111 km en el ecuador**, y no a 463 m.
Su compatibilidad con elevación y cobertura del suelo se consigue agregando esas
capas a una malla de análisis común o consultándolas conjuntamente por coordenadas.
Remuestrear NASA POWER a 463 m no genera información climática de esa resolución.

La climatología actual del servicio abarca **2001–2025**, y se selecciona el
resumen anual `month=13`. Se comprueba el periodo en los metadatos vivos del
[elemento NASA](https://gis.earthdata.nasa.gov/portal/home/item.html?id=0d75022c26f844668ec99f64a0cc2f67)
antes de generar cada mapa. Algunas páginas o resultados de búsqueda antiguos
todavía indican 2001–2020; no se utilizan para etiquetar esta descarga.
El script se detiene si el periodo publicado cambia.

El servicio numérico entrega GHI directamente en **W m⁻²**: no se aplica una
conversión desde kWh/m²/día. Las unidades de ambas variables se consultan y validan
antes de convertir. El [albedo POWER](https://power.larc.nasa.gov/docs/methodology/data/derived/derived-parameters/)
es una razón de flujos radiativos en superficie, y no el albedo planetario de
aproximadamente 0,3 medido en el techo de la atmósfera terrestre.

## Conversión y controles

`generar_ghi.py` y `generar_albedo.py` comparten `power_comun.py` en
`tierra/origen_ds_gui_Y_albeolo/`. Cada generador:

1. Consulta el periodo, la resolución, las unidades y el resumen anual del servicio.
2. Solicita `exportImage` como **TIFF Float32 numérico**, con la función de ráster
   `None`, sin colores ni estiramiento y en la cuadrícula nativa exacta.
3. Lee la respuesta en memoria. No descarga archivos globales de alta resolución.
4. Convierte el relleno declarado `-999` a `NaN`/NoData; no sustituye ausencias por cero.
5. Exige albedo entre 0 y 1, GHI entre 0 y 1.500 W/m² y valores válidos finitos.
6. Escribe un GeoTIFF comprimido y vuelve a leer todos los píxeles para comprobar
   igualdad exacta de valores y máscara.

Los metadatos del TIFF guardan fuente, variable, periodo, unidades y SHA256 del
TIFF numérico recibido. Los informes JSON guardan también la petición y una copia
de los atributos científicos del servicio. NASA POWER aplica **BitGroom con dos
cifras significativas** en la fuente: Float32 conserva ese producto, sin añadir
precisión científica.

`validar_radiacion.py` comprueba las dos cuadrículas, sus unidades, periodos y
solapamiento. Contrasta además píxeles de España, océano ecuatorial y Australia
con la **API puntual independiente de NASA POWER**, solicitando expresamente
2001–2025, `community=SB` y el promedio `ANN`. Admite la diferencia de cuantización
BitGroom del servicio y el redondeo decimal de la API, sin volver a escalar datos.

| Control global | GHI | Albedo |
|---|---:|---:|
| Mínimo | 55,25 W/m² | 0,020019531 |
| Máximo | 307 W/m² | 0,800781190 |
| Media global ponderada por coseno de latitud | 186,123853 W/m² | 0,149031393 |
| Celdas válidas | 64.800 | 64.800 |
| Celdas NoData | 0 | 0 |

El albedo alto en nieve/hielo y bajo en océano, y el orden de magnitud de GHI
son coherentes con los significados físicos del producto. Los valores no se
recortan para forzar estadísticas esperadas. Las **64.800 celdas conjuntas**
comparten ubicación y periodo. Informes:
`tierra/auditoria/radiacion_ghi.json`, `radiacion_albedo.json` y `radiacion.json`.

## Ejecución sin ocupar el disco principal

Desde la raíz del repositorio, con el entorno geoespacial ya existente:

```bash
marte/.venv/bin/python tierra/origen_ds_gui_Y_albeolo/generar_ghi.py
marte/.venv/bin/python tierra/origen_ds_gui_Y_albeolo/generar_albedo.py
marte/.venv/bin/python tierra/origen_ds_gui_Y_albeolo/validar_radiacion.py
```

Los TIFF se crean por defecto en `/tmp/hspace_tierra_productos/` y pesan menos de
100 KB entre ambos. `--salida` y `--informe` permiten elegir rutas de salida.
El validador admite `--directorio`; `--sin-api` repite únicamente los controles
locales. Los scripts generan y verifican; la publicación y eliminación posteriores
se realizan en el flujo conjunto para comprobar primero lo publicado en Hugging Face.

## Uso junto a los mapas de Marte

Las unidades permiten una exploración conjunta, pero los productos no son
mediciones equivalentes: el GHI de Marte es un modelo simplificado para
Ls = 18,9°, mientras que el terrestre es una climatología anual. El albedo de
Marte es Lambert bolométrico; el de POWER es una razón de flujos bajo todo cielo.
La definición angular, el periodo, la atmósfera y la escala física deben
armonizarse antes de interpretar semejanzas como análogos ambientales.

NASA POWER permite el uso, acceso y descarga sin restricciones, con atribución
a NASA POWER; véase su [registro oficial de datos abiertos](https://registry.opendata.aws/nasa-power/).
