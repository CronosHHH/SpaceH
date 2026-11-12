#!/usr/bin/env python3
"""Comprueba la compatibilidad de los productos terrestres, sin cachear TIFF."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio as rio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from huggingface_hub import HfApi, hf_hub_url
from publicar_dataset import hash_auditado
from prototipo_analogos import descargar_memoria


ROOT = Path(__file__).resolve().parent
PRODUCTOS = Path("/tmp/hspace_tierra_productos")
NOMBRES = (
    "GHI_tierra.tif", "Albedo_tierra.tif", "NASADEM_tierra_1grado.tif",
    "Fracciones_mascaras_tierra_MODIS_2021_1grado.tif",
    "Vegetacion_tierra_MOD44B_2021_1grado.tif",
)


def cargar_pequeno(nombre, catalog, revision, git_paths):
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
        url = hf_hub_url(catalog["dataset"], record["archivo"], repo_type="dataset", revision=revision)
        if record["archivo"] in git_paths:
            url = url.replace("/resolve/", "/raw/", 1)
        raw = descargar_memoria(url, limite=4 * 1024 * 1024)
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
    revision = HfApi().repo_info(catalog["dataset"], repo_type="dataset").sha
    paths = [catalog["productos"][n]["archivo"] for n in NOMBRES if n in catalog["productos"]]
    git_paths = {info.path for info in HfApi().get_paths_info(catalog["dataset"], paths, repo_type="dataset", revision=revision) if not info.lfs}
    ghi, albedo, dem, masks, vegetation = (cargar_pequeno(n, catalog, revision, git_paths) for n in NOMBRES)
    if (ghi.shape != (1, 180, 360) or albedo.shape != ghi.shape or dem.shape != (2, 180, 360)
            or masks.shape != (4, 180, 360) or vegetation.shape != (2, 180, 360)):
        raise ValueError("Número de bandas inesperado")
    for name, values, lo, hi in (("GHI", ghi, 0, 600), ("albedo", albedo, 0, 1),
                                  ("elevación", dem[0], -500, 9000), ("cobertura DEM", dem[1], 0, 1),
                                  ("máscaras y cobertura", masks, 0, 1),
                                  ("cobertura vegetal y cobertura de datos", vegetation, 0, 1)):
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
    if (not np.isfinite(vegetation[1]).all()
            or not np.array_equal(np.isfinite(vegetation[0]), vegetation[1] > 0)):
        raise ValueError("La cobertura de datos de vegetación no corresponde a sus estimaciones")
    if not np.any((vegetation[0] > 0) & (vegetation[0] < 1)):
        raise ValueError("La cobertura vegetal no contiene valores intermedios")
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
    vegetation_name = "Vegetacion_tierra_MOD44B_2021_0p5grado.tif"
    local = PRODUCTOS / vegetation_name
    if local.exists():
        with rio.open(local) as source:
            vegetation_geometry = (source.shape, source.crs.to_string(), source.transform)
    else:
        r = catalog["productos"][vegetation_name]
        vegetation_geometry = ((r["dimensiones"][1], r["dimensiones"][0]), r["crs"],
                               rio.Affine.from_gdal(*r["geotransform"]))
    if vegetation_geometry != ((360, 720), "EPSG:4326", from_origin(-180, 90, .5, .5)):
        raise ValueError("La vegetación no tiene su malla nativa de 0,5°")
    joint = (np.isfinite(ghi[0]) & np.isfinite(albedo[0]) & np.isfinite(dem[0])
             & (masks[3] > 0) & np.isfinite(vegetation[0]))
    if not joint.any():
        raise ValueError("Las capas no tienen solapamiento útil")
    report = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(), "compatible": True,
        "revision_hf_referencias": revision,
        "productos_1grado": list(NOMBRES), "productos_15arcsec_misma_malla": native,
        "sha256_resumenes": {n: hash_auditado(n) if (PRODUCTOS / n).exists()
                             else catalog["productos"][n]["sha256"] for n in NOMBRES},
        "celdas_1grado": 64800, "celdas_conjuntas": int(joint.sum()),
        "elevacion_celdas_validas": int(np.isfinite(dem[0]).sum()),
        "clasificacion_celdas_con_datos": int((masks[3] > 0).sum()),
        "vegetacion_celdas_con_datos": int(np.isfinite(vegetation[0]).sum()),
        "vegetacion_valores_intermedios": True,
        "vegetacion_rango_1grado": [float(np.nanmin(vegetation[0])), float(np.nanmax(vegetation[0]))],
        "vegetacion_nativa": {"archivo": vegetation_name, "resolucion_grados": .5,
                              "cantidad": "vegetated_surface_fraction"},
        "rangos_y_mascaras_correctos": True, "fracciones_exclusivas_correctas": True,
        "limitaciones": [
            "POWER: climatología anual 2001–2025 a 1°; no tiene resolución climática de 463 m.",
            "NASADEM: alturas sobre EGM96, principalmente SRTM de 2000; cobertura limitada.",
            "Máscaras: clasificación MODIS 2021 y océano cartográfico Natural Earth; consultar su cobertura.",
            "Vegetación: cobertura física MOD44B/ICDC, ciclo marzo 2021 a marzo 2022, malla nativa 0.5°; no códigos IGBP ni NDVI.",
            "Compatibilidad geométrica y de unidades para exploración; no son observaciones simultáneas ni equivalentes a los modelos marcianos.",
        ],
    }
    path = ROOT / "auditoria/conjunto.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    validar()
