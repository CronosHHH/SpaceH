import urllib.request
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds

# 1. Descargar el mapa global TES Albedo de ASU (8 píxeles por grado)
url = (
    "https://ms-mars.mars.asu.edu/TES_Lambert_Albedo"
    "?BBOX=-180,-90,180,90"
    "&FORMAT=image/png"
    "&HEIGHT=1440"
    "&LAYERS=TES_Lambert_Albedo"
    "&REQUEST=GetMap"
    "&SERVICE=WMS"
    "&SRS=JMARS:4"
    "&STYLES="
    "&VERSION=1.1.1"
    "&WIDTH=2880"
)
img_path = "tes_albedo.png"
urllib.request.urlretrieve(url, img_path)

# 2. La escala publicada por ASU es DN 0-254 = albedo 0.08-0.32.
img = Image.open(img_path).convert('L')
dn = np.array(img, dtype=np.uint8)
albedo_data = 0.08 + (dn.astype(np.float32) / 254.0) * 0.24
# DN 255 queda fuera del rango de escala de ASU; se conserva como NoData.
albedo_data[dn == 255] = np.nan

# 3. Exportar a GeoTIFF para Marte
height, width = albedo_data.shape
transform = from_bounds(-180, -90, 180, 90, width, height)

with rasterio.open(
    'Albedo_TES.tif',
    'w',
    driver='GTiff',
    height=height,
    width=width,
    count=1,
    dtype=np.float32,
    nodata=np.nan,
    crs='+proj=longlat +a=3396190 +b=3376200 +no_defs',
    transform=transform
) as dst:
    dst.write(albedo_data, 1)

print("¡Albedo_TES.tif generado correctamente en tu carpeta!")
