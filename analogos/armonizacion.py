"""Agrega cada planeta por separado a celdas sinusoidales de igual tamaño.

No reproyecta la Tierra sobre Marte: emplea el radio de cada planeta. Las
coberturas conocidas a 1° se tratan como uniformes dentro de su celda de origen.
"""

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import Affine, from_origin
from rasterio.warp import reproject, Resampling


RADIOS = {"tierra": 6371007.181, "marte": 3396190.0}


def _geometria(radio, celda_m):
    width = int(np.ceil(2 * np.pi * radio / celda_m))
    height = int(np.ceil(np.pi * radio / celda_m))
    transform = from_origin(-np.pi * radio, np.pi * radio / 2, celda_m, celda_m)
    x, y = np.meshgrid(transform.c + (np.arange(width) + .5) * celda_m,
                       transform.f - (np.arange(height) + .5) * celda_m)
    phi = y / radio
    lat_ok = np.abs(phi) < np.pi / 2
    inside = lat_ok & (np.abs(x) <= np.pi * radio * np.cos(phi))
    lon = np.full(x.shape, np.nan)
    np.divide(x, radio * np.cos(phi), out=lon, where=inside)
    latitudes = np.where(inside, np.rad2deg(phi), np.nan)
    longitudes = np.where(inside, np.rad2deg(lon), np.nan)
    ymax = np.abs(y) + celda_m / 2
    xmax = np.abs(x) + celda_m / 2
    full = (ymax <= np.pi * radio / 2) & (xmax <= np.pi * radio * np.cos(ymax / radio))
    crs = CRS.from_string(f"+proj=sinu +lon_0=0 +R={radio} +units=m +no_defs")
    geometry = {"forma": [height, width], "crs": crs.to_wkt(),
                "geotransformacion": list(transform.to_gdal()), "resolucion_m": celda_m,
                "area_nominal_km2": (celda_m / 1000) ** 2,
                "modelo": "Sinusoidal sobre esfera; radio terrestre autálico y radio marciano del proyecto"}
    return geometry, latitudes, longitudes, inside, full


def _promedio(array, origen, destino):
    result = np.full(destino["forma"], np.nan, dtype="float64")
    reproject(
        source=array, destination=result,
        src_transform=Affine.from_gdal(*origen["geotransformacion"]), src_crs=origen["crs"],
        src_nodata=None, dst_transform=Affine.from_gdal(*destino["geotransformacion"]),
        dst_crs=destino["crs"], dst_nodata=np.nan,
        resampling=Resampling.average, num_threads=2, warp_mem_limit=128,
    )
    if np.isinf(result).any():
        raise ValueError("La agregación produjo infinitos")
    return np.where(np.isnan(result), 0, result)


def _cobertura(planeta, nombre):
    key = "clasificacion" if nombre in ("ciudades", "agua") else nombre
    if key in planeta["coberturas"]:
        return np.asarray(planeta["coberturas"][key], dtype="float64")
    return np.isfinite(planeta["variables"][nombre]).astype("float64")


def _armonizar_planeta(planeta, radio, celda_m):
    geometry, lat, lon, inside, full = _geometria(radio, celda_m)
    values, coverages = {}, {}
    for nombre, array in planeta["variables"].items():
        coverage = _cobertura(planeta, nombre)
        known = np.isfinite(array) & np.isfinite(coverage) & (coverage > 0)
        source_coverage = np.where(known, coverage, 0)
        numerator = np.where(known, np.nan_to_num(array) * source_coverage, 0)
        denominator = _promedio(source_coverage, planeta["geometria"], geometry)
        mean = np.full(denominator.shape, np.nan)
        np.divide(_promedio(numerator, planeta["geometria"], geometry), denominator,
                  out=mean, where=(denominator > 0) & inside)
        values[nombre] = np.where(inside, mean, np.nan)
        coverages[nombre] = np.where(inside, np.clip(denominator, 0, 1), 0)
    if "ciudades" in values:
        coverages["clasificacion"] = np.minimum(coverages["ciudades"], coverages["agua"])
    return {"variables": values, "coberturas": coverages, "unidades": dict(planeta["unidades"]),
            "geometria": geometry, "latitudes": lat, "longitudes": lon,
            "radio_m": radio, "celda_m": celda_m, "inside": inside, "inside_completo": full}


def armonizar(datos, celda_m=120000):
    """Devuelve dos mapas agregados a celdas nominales de 120 × 120 km.

    Para cada variable: media = promedio(valor × cobertura)/promedio(cobertura).
    Cero conocido se conserva. La ausencia de datos nunca se rellena con cero.
    Las celdas recortadas por el borde de la proyección quedan fuera del modelo.
    """
    if not np.isfinite(celda_m) or celda_m < 120000:
        raise ValueError("La celda debe ser al menos 120 km para no fingir detalle de los resúmenes de 1°")
    result = {name: _armonizar_planeta(datos[name], radio, float(celda_m))
              for name, radio in RADIOS.items()}
    result["procedencia"] = dict(datos.get("procedencia", {}))
    result["procedencia"]["armonizacion"] = {
        "celda_m": float(celda_m), "area_nominal_km2": (celda_m / 1000) ** 2,
        "radios_m": dict(RADIOS), "operacion": "Reproyección independiente, sinusoidal esférica, media ponderada por cobertura",
        "aproximacion": "Coberturas uniformes dentro del píxel angular de origen; área esférica, no elipsoidal exacta",
        "borde": "El modelo excluye píxeles cuyo cuadrado no cabe entero en la huella sinusoidal",
    }
    return result
