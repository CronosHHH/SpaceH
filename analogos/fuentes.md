# Entradas y armonización del prototipo conjunto

`datos.cargar_datos(raiz, revision=None)` lee una sola revisión de
[`Renato-R-V/hspace-datasets`](https://huggingface.co/datasets/Renato-R-V/hspace-datasets).
Comprueba tamaño y hash de cada archivo contra los metadatos de esa revisión;
en Tierra contrasta además SHA256 con su catálogo científico. Solo descarga a
memoria el catálogo y cuatro TIFF pequeños. No descarga originales ni crea
una caché TIFF. El campo `procedencia` conserva revisión, URL, bytes y SHA256.

La salida por planeta tiene `variables`, `coberturas`, `unidades`, `geometria`,
`latitudes` y `longitudes`. Todas las matrices son Float64 de 180 filas × 360
columnas, norte arriba y con centros en semigrados. NoData continúa como `NaN`.
La carga no normaliza valores ni cambia sus unidades físicas.

## Qué aporta cada dataset

| Dataset | Entrada original | Transformación ya aplicada | Variable de salida |
|---|---|---|---|
| [NASADEM HGT.001](https://www.earthdata.nasa.gov/data/catalog/lpcloud-nasadem-hgt-001) | Altura en m sobre EGM96, 1″; principalmente SRTM febrero 2000 | Servicio remoto reduce a 15″ por media y redondeo Int16; media de 240 × 240 valores válidos por celda de 1° | Elevación terrestre [m], cobertura válida [0–1] |
| [NASA POWER](https://power.larc.nasa.gov/docs/services/arcgis/) | Irradiancia descendente bajo todo cielo y albedo superficial, nativos a 1° | Exportación numérica anual `month=13`, climatología 2001–2025; relleno→NaN, sin volver a escalar | GHI [W/m²], albedo [0–1] |
| [MCD12Q1.061/OpenGeoHub](https://zenodo.org/records/8367523) y [Natural Earth](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-ocean/) | Clases de suelo IGBP 2021; océano cartográfico 1:10M | Lecturas nativas y vecino próximo a 15″; clase 13=urbano,17=agua; suplemento oceánico solo donde falta clasificación; conteos a 1° | Fracciones ciudad/agua entre píxeles clasificados y cobertura de clasificación [0–1] |
| [MOD44B.061/ICDC](https://www.geo.uni-hamburg.de/en/service/icdc/data/land/modis-vcf-forest.html) | Fracción no vegetada en %, CMG 0,5°; ciclo 2021-03-05…2022-03-04 | `(100−no_vegetado)/100`; fill 127→NaN; media de las celdas CMG válidas 2 × 2 | Cobertura vegetal física [0–1], fracción de las 4 celdas CMG con datos [0–1] |
| [MGS MOLA](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | Altura marciana sobre el areoide en m;128 píxeles/grado (~463 m) | Reproyección al CRS marciano esférico y media válida a 1° | Elevación marciana [m] |
| [Modelo GHI del proyecto](../marte/origen_ds_gui_Y_albeolo/generar_ghi.py) | Geometría solar esférica, 590 W/m² y transmisión atmosférica constante 0,75 | Media diaria analítica para Ls = 18,9°, oblicuidad 25,19°; se preserva malla 1° | GHI marciano modelado [W/m²] |
| [MGS TES/ASU](https://www.mars.asu.edu/data/tes_albedo/) | Albedo Lambert bolométrico numérico adimensional a 8 píxeles/grado | Se permutan 1.440 columnas de 0…360° a −180…180°; alfa PNG solo define desconocidos; media válida 8 × 8 | Albedo marciano [0–1] |
| [Mars Express OMEGA](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/) | PDS IMG entero de 16 bits y su etiqueta; parámetros espectrales OSP1/2/3 y BD2000 | `IMG×SCALING_FACTOR+OFFSET`; posición corregida sin modificar valores; promedio de detecciones y cobertura a 1° | Cuatro índices espectrales [1], no porcentajes de mineral |

Los detalles auditados se conservan en [Tierra](../tierra/README.md) y en la
[auditoría de Marte](../marte/auditoria_tiffs/INFORME.md).

## Qué significa armonizar

La malla terrestre es EPSG:4326. La marciana es longitud/latitud planetocéntrica
sobre una esfera de radio 3.396.190 m. Tienen la misma **forma angular**, pero no
comparten CRS ni distancia física: un grado mide aproximadamente 111 km en el
ecuador terrestre y 59,3 km en el marciano. No se reproyecta un planeta sobre otro.
Los resúmenes actuales no permiten recuperar el relieve de 15″ ni resolver un
emplazamiento local. La dispersión de elevaciones derivada aquí es regional.

La elevación terrestre usa EGM96 y MOLA usa el areoide. Sus valores en metros no
comparten cero vertical. El GHI terrestre es una climatología anual observacional
y modelada; el marciano es un modelo simplificado de una estación solar. El
albedo POWER es una razón de flujos superficiales bajo todo cielo; TES es un
albedo Lambert bolométrico. Igualar unidades o convertir a percentiles no corrige
esas diferencias físicas. Una clasificación relativa requiere declarar esa
interpretación y no equivale a verificar un análogo climático real.

La vegetación no tiene una observación marciana equivalente en este dataset.
Su ausencia en Marte **no se rellena con cero**. Ciudades, agua y vegetación son
variables auxiliares terrestres para filtrar candidatos; los índices minerales
son información auxiliar marciana hasta disponer de una capa terrestre
comparable. No se mezclan automáticamente como coordenadas del mismo vector.

## Cobertura y desconocidos

La media de elevación se condiciona a píxeles con elevación válida. Las fracciones
de ciudades/agua se condicionan a píxeles clasificados. OSP/BD2000 se promedian
solo donde hay detección, por lo que sus medias no son abundancias de toda la
celda. Las coberturas minerales tampoco equivalen a porcentajes de mineral.

La cobertura vegetal MOD44B es la media de recuperaciones válidas originales de
250 m agregadas por ICDC. Puede no representar toda el área de la celda CMG. La
banda de cobertura usada aquí cuenta celdas CMG conocidas, no calidad ni cobertura
interna de esas recuperaciones. Océano o hielo desconocido sigue como NaN, sin
confundir ausencia de estimación con cero vegetación.

Los productos combinados que incluyen las fracciones de OpenGeoHub mantienen
**CC BY-SA 4.0** y atribución. MOD44B/ICDC se atribuye a NASA e ICDC, CEN,
Universidad de Hamburgo, bajo CC BY 4.0. El archivo de procedencia no expone tokens;
el lector HTTP restringe su envío a Hugging Face y los elimina al redirigir a CDN.
