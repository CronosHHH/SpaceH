#!/usr/bin/env python3
"""Comprueba la compatibilidad de los seis productos terrestres, sin cachear TIFF."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import rasterio as rio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from huggingface_hub import hf_hub_url
from publicar_dataset import hash_auditado


ROOT = Path(__file__).resolve().parent
PRODUCTOS = Path("/tmp/hspace_tierra_productos")
NOMBRES = (
    "GHI_tierra.tif", "Albedo_tierra.tif", "NASADEM_tierra_1grado.tif",
    "Fracciones_mascaras_tierra_MODIS_2021_1grado.tif",
)


def cargar_pequeno(nombre, catalog):
    local = PRODUCTOS / nombre
    if local.exists():
        if local.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("El validador conjunto solo lee resúmenes pequeños")
        raw = local.read_bytes()
        expected = hash_auditado(nombre)
    else:
        record = catalog["productos"][nombre]
        if record["bytes"] > 4 * 1024 * 1024:
            raise ValueError("El validador conjunto solo descarga resúmenes pequeños")
        url = hf_hub_url(catalog["dataset"], record["archivo"], repo_type="dataset")
        with urlopen(url, timeout=120) as source:
            raw = source.read(4 * 1024 * 1024 + 1)
        if len(raw) != record["bytes"]:
            raise ValueError(f"El tamaño remoto cambió respecto al catálogo: {nombre}")
        expected = record["sha256"]
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"El archivo cambió respecto a su auditoría o catálogo: {nombre}")
    with MemoryFile(raw) as memory, memory.open() as src:
        if (src.crs.to_epsg() != 4326 or src.shape != (180, 360)
                or not src.transform.almost_equals(from_origin(-180, 90, 1, 1))):
            raise ValueError(f"{nombre}: cuadrícula común incorrecta")
        return src.read(masked=True).astype("float32").filled(np.nan)


def validar():
    catalog = json.loads((ROOT / "catalogo.json").read_text())
    ghi, albedo, dem, masks = (cargar_pequeno(n, catalog) for n in NOMBRES)
    if ghi.shape != (1, 180, 360) or albedo.shape != ghi.shape or dem.shape != (2, 180, 360) or masks.shape != (4, 180, 360):
        raise ValueError("Número de bandas inesperado")
    for name, values, lo, hi in (("GHI", ghi, 0, 600), ("albedo", albedo, 0, 1),
                                  ("elevación", dem[0], -500, 9000), ("cobertura DEM", dem[1], 0, 1),
                                  ("máscaras y cobertura", masks, 0, 1)):
        valid = np.isfinite(values)
        if not valid.any() or np.isinf(values).any() or values[valid].min() < lo or values[valid].max() > hi:
            raise ValueError(f"{name}: valores físicos incorrectos")
    if not np.isfinite(dem[1]).all() or not np.array_equal(np.isfinite(dem[0]), dem[1] > 0):
        raise ValueError("La cobertura DEM no corresponde a sus datos válidos")
    if not np.isfinite(masks[3]).all():
        raise ValueError("La cobertura de clasificación debe incluir los ceros conocidos")
    for fraction in masks[:3]:
        if not np.array_equal(np.isfinite(fraction), masks[3] > 0):
            raise ValueError("Una fracción de máscara ha perdido sus desconocidos")
    if np.nanmax(np.sum(masks[:3], axis=0)) > 1 + 1e-6:
        raise ValueError("Las fracciones de grupos exclusivos suman más de uno")
    native = []
    for nombre in ("NASADEM_tierra_15arcsec.tif", "Mascaras_tierra_MODIS_2021_15arcsec.tif"):
        local = PRODUCTOS / nombre
        if local.exists():
            with rio.open(local) as src:
                geometry = (src.shape, src.crs.to_string(), src.transform)
        else:
            r = catalog["productos"][nombre]
            geometry = ((r["dimensiones"][1], r["dimensiones"][0]), r["crs"],
                        rio.Affine.from_gdal(*r["geotransform"]))
        if geometry != ((43200, 86400), "EPSG:4326", from_origin(-180, 90, 1/240, 1/240)):
            raise ValueError(f"{nombre}: malla detallada incorrecta")
        native.append(nombre)
    joint = np.isfinite(ghi[0]) & np.isfinite(albedo[0]) & np.isfinite(dem[0]) & (masks[3] > 0)
    if not joint.any():
        raise ValueError("Las capas no tienen solapamiento útil")
    report = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(), "compatible": True,
        "productos_1grado": list(NOMBRES), "productos_15arcsec_misma_malla": native,
        "sha256_resumenes": {n: hash_auditado(n) if (PRODUCTOS / n).exists()
                             else catalog["productos"][n]["sha256"] for n in NOMBRES},
        "celdas_1grado": 64800, "celdas_conjuntas": int(joint.sum()),
        "elevacion_celdas_validas": int(np.isfinite(dem[0]).sum()),
        "clasificacion_celdas_con_datos": int((masks[3] > 0).sum()),
        "rangos_y_mascaras_correctos": True, "fracciones_exclusivas_correctas": True,
        "limitaciones": [
            "POWER: climatología anual 2001–2025 a 1°; no tiene resolución climática de 463 m.",
            "NASADEM: alturas sobre EGM96, principalmente SRTM de 2000; cobertura limitada.",
            "Máscaras: clasificación MODIS 2021 y océano cartográfico Natural Earth; consultar su cobertura.",
            "Compatibilidad geométrica y de unidades para exploración; no son observaciones simultáneas ni equivalentes a los modelos marcianos.",
        ],
    }
    path = ROOT / "auditoria/conjunto.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    validar()
