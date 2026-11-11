#!/usr/bin/env python3
"""Descarga el albedo numérico TES de ASU y lo convierte a GeoTIFF marciano.

Desde la raíz del repositorio:
  marte/.venv/bin/python marte/origen_ds_gui_Y_albeolo/generar_albedo.py
  marte/.venv/bin/python marte/origen_ds_gui_Y_albeolo/generar_albedo.py --comprobar-compatibilidad

No reconstruye albedo desde colores. Los valores proceden del VICAR numérico;
del PNG del mismo proveedor solo se utiliza su canal alfa como máscara.
Ver ../docu/albedo_ds.md para procedencia, precisión y convención de CRS.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.request import Request, urlopen
import warnings

import numpy as np
import rasterio as rio
from rasterio.crs import CRS
from rasterio.enums import ColorInterp, Resampling
from rasterio.errors import NotGeoreferencedWarning
from rasterio.transform import from_origin
from rasterio.warp import reproject


ROOT = Path(__file__).resolve().parents[1]
REPO = "Renato-R-V/hspace-datasets"
SOURCE_PAGE = "https://www.mars.asu.edu/data/tes_albedo/"
NUMERIC_URL = (
    "https://ms-mars.mars.asu.edu/alb32?SERVICE=WMS&REQUEST=GetMap"
    "&FORMAT=image/vicar&WIDTH=2880&HEIGHT=1440&SRS=JMARS:4"
    "&BBOX=0,-90,360,90&STYLES=&VERSION=1.1.1&LAYERS=TES_Lambert_Albedo_numeric"
)
MASK_URL = (
    "https://ms-mars.mars.asu.edu/TES_Lambert_Albedo?SERVICE=WMS&REQUEST=GetMap"
    "&FORMAT=image/png&WIDTH=2880&HEIGHT=1440&SRS=JMARS:4"
    "&BBOX=-180,-90,180,90&STYLES=&VERSION=1.1.1&LAYERS=TES_Lambert_Albedo"
)
# El encabezado VICAR incluye DAT_TIM: solo el payload tiene hash estable.
PAYLOAD_SHA256 = "8ef70069ffb483d0872f9c73abf9d108b0bad8b30c444b2e464c13ac89d8643c"
MASK_SHA256 = "7c65e78701622685b73a2845ef2c01a824e6192d81d909e1fca1dde12d6148b3"
CRS_MARTE = CRS.from_string("+proj=longlat +R=3396190 +no_defs")
TRANSFORM = from_origin(-180, 90, 0.125, 0.125)
GRID = from_origin(-180, 90, 1, 1)
SHAPE = (1440, 2880)
REFERENCIAS = (
    "1-Mars_MGS_MOLA_DEM_mosaic_global_463m.tif", "GHI_marte.tif",
    "olivine_osp1_equ_map.tiff", "olivine_osp2_equ_map.tiff",
    "olivine_osp3_equ_map.tiff", "pyroxene_bd2000_equ_map.tiff",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def descargar(url, destino):
    """Una descarga interrumpida nunca pasa a ser una fuente cacheada válida."""
    if destino.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as tmp:
            temporal = Path(tmp.name)
            request = Request(url, headers={"User-Agent": "HSpace-Mars-albedo/1.0"})
            with urlopen(request, timeout=120) as response:
                shutil.copyfileobj(response, tmp)
        temporal.replace(destino)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def leer_fuentes(carpeta):
    vic = carpeta / "tes_albedo_numeric.vic"
    png = carpeta / "tes_albedo_mask.png"
    descargar(NUMERIC_URL, vic)
    descargar(MASK_URL, png)
    contenido = vic.read_bytes()
    match = re.match(rb"LBLSIZE\s*=\s*(\d+)", contenido)
    if match is None:
        raise ValueError("La respuesta de ASU no es un VICAR: falta LBLSIZE")
    size = int(match[1])
    header = contenido[:size].decode("ascii")
    expected = {"FORMAT": "REAL", "REALFMT": "RIEEE", "ORG": "BSQ",
                "NL": "1440", "NS": "2880", "NB": "1", "NBB": "0", "NLB": "0"}
    for key, value in expected.items():
        field = re.search(rf"\b{key}\s*=\s*(?:'([^']*)'|(\d+))", header)
        if field is None or (field[1] or field[2]) != value:
            raise ValueError(f"VICAR inesperado: {key} debe ser {value}")
    payload = contenido[size:]
    if len(payload) != np.prod(SHAPE) * 4 or sha256(payload) != PAYLOAD_SHA256:
        raise ValueError("El contenido numérico de ASU ha cambiado o está incompleto; revisar la fuente")
    png_bytes = png.read_bytes()
    if sha256(png_bytes) != MASK_SHA256:
        raise ValueError("La máscara de ASU ha cambiado o está incompleta; revisar la fuente")
    values = np.frombuffer(payload, dtype="<f4").reshape(SHAPE)
    # El VICAR tiene BBOX 0..360; el PNG, -180..180. Se permutan columnas.
    values = np.roll(values, SHAPE[1] // 2, axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rio.open(png) as image:
            if image.shape != SHAPE or ColorInterp.alpha not in image.colorinterp:
                raise ValueError("El PNG debe tener la misma cuadrícula y un canal alfa")
            alpha_band = image.colorinterp.index(ColorInterp.alpha) + 1
            alpha = image.read(alpha_band)
    if not np.isin(alpha, [0, 255]).all():
        raise ValueError("La máscara contiene transparencias parciales no previstas")
    missing = alpha == 0
    if not np.array_equal(missing, values == np.float32(0.08)):
        raise ValueError("La máscara no corresponde al relleno del VICAR de esta versión")
    valid = values[~missing]
    if not valid.size or not np.isfinite(valid).all() or not ((valid >= 0) & (valid <= 1)).all():
        raise ValueError("El albedo válido debe ser finito y estar entre 0 y 1")
    values[missing] = np.nan
    provenance = {
        "pagina_fuente": SOURCE_PAGE, "url_numerico": NUMERIC_URL, "url_mascara": MASK_URL,
        "sha256_payload_vicar": sha256(payload), "sha256_png_mascara": sha256(png_bytes),
        "dimensiones": [SHAPE[1], SHAPE[0]], "resolucion_grados": 0.125,
        "rotacion_columnas": 1440, "validos": int(valid.size), "nodata": int(missing.sum()),
        "min": float(valid.min()), "max": float(valid.max()), "media": float(valid.mean(dtype="float64")),
        "niveles_validos": int(np.unique(valid).size), "paso_cuantizacion_aprox": 0.24 / 254,
        "crs": CRS_MARTE.to_wkt(), "geotransform": list(TRANSFORM.to_gdal()),
        "criterio_nodata": "Solo alfa cero del PNG oficial de la misma versión; salida NaN",
        "convencion_crs": "Coordenadas angulares planetocéntricas; esfera R=3396190 m elegida como en el notebook. El VICAR no declara CRS ni radio.",
    }
    return values, provenance


def crear_geotiff(destino, values, provenance):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destino.parent, suffix=".tif", delete=False) as tmp:
        temporal = Path(tmp.name)
    try:
        with rio.open(
            temporal, "w", driver="GTiff", height=SHAPE[0], width=SHAPE[1], count=1,
            dtype="float32", crs=CRS_MARTE, transform=TRANSFORM, nodata=np.nan,
            compress="deflate", predictor=3, tiled=True,
        ) as dst:
            dst.write(values, 1)
            dst.set_band_description(1, "Albedo TES (Lambert; adimensional)")
            dst.update_tags(
                source=SOURCE_PAGE, source_numeric=NUMERIC_URL, source_mask=MASK_URL,
                source_payload_sha256=PAYLOAD_SHA256, source_mask_sha256=MASK_SHA256,
                latitude_type="planetocentric", longitude_direction="positive east",
                crs_note=provenance["convencion_crs"],
                processing="VICAR Float32; roll 1440 columns; alpha=0 to NaN; no resampling",
                precision_note="Provider quantization approximately 0.24/254; original values retained",
                citation="Christensen et al. (2001), JGR 106, 23823-23871; ASU TES Lambert Albedo",
            )
            dst.update_tags(1, units="1", long_name="TES Lambert bolometric albedo")
        with rio.open(temporal) as src:
            # GeoTIFF puede serializar los ejes del WKT como lat/lon; Rasterio
            # usa x/y tradicional. Comparar los parámetros evita un falso fallo.
            if (src.crs.to_dict() != CRS_MARTE.to_dict() or src.transform != TRANSFORM or src.shape != SHAPE
                    or src.count != 1 or src.dtypes != ("float32",) or not np.isnan(src.nodata)
                    or not np.array_equal(src.read(1), values, equal_nan=True)
                    or not np.array_equal(src.read_masks(1) == 0, np.isnan(values))):
                raise ValueError("El GeoTIFF no conserva exactamente los valores, máscara o georreferencia")
        temporal.replace(destino)
    finally:
        temporal.unlink(missing_ok=True)
    provenance["sha256_geotiff"] = sha256(destino.read_bytes())


def comprobar_compatibilidad(albedo, revision=None):
    """Repite la alineación del notebook con los seis originales de Hugging Face."""
    from huggingface_hub import HfApi, hf_hub_download

    # Fijar una revisión única para no mezclar versiones durante la auditoría.
    revision = revision or HfApi().repo_info(REPO, repo_type="dataset").sha
    results = []
    for nombre in (*REFERENCIAS, albedo.name):
        print("Comprobando:", nombre, flush=True)
        path = str(albedo) if nombre == albedo.name else hf_hub_download(
            REPO, filename=f"marte/{nombre}", repo_type="dataset", revision=revision,
        )
        with rio.Env(GDAL_PAM_ENABLED="NO"), rio.open(path) as src:
            if src.crs is None or src.count != 1:
                raise ValueError(f"{nombre}: falta CRS o no es monobanda")
            target = np.full((180, 360), np.nan, dtype="float32")
            if nombre == "GHI_marte.tif":
                if src.shape != target.shape or not src.transform.almost_equals(GRID):
                    raise ValueError("El GHI no tiene la malla de 1° esperada")
                target[:] = src.read(1, masked=True).filled(np.nan)
            else:
                reproject(
                    source=rio.band(src, 1), destination=target,
                    src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata,
                    dst_transform=GRID, dst_crs=CRS_MARTE, dst_nodata=np.nan,
                    resampling=Resampling.average, num_threads=2, warp_mem_limit=128,
                )
            if not np.isfinite(target).any() or np.isinf(target).any():
                raise ValueError(f"{nombre}: reproyección vacía o con infinitos")
            result = {
                "archivo": nombre, "dimensiones_origen": [src.width, src.height],
                "crs_origen": src.crs.to_wkt(), "malla_destino": [360, 180],
                "celdas_validas_1grado": int(np.isfinite(target).sum()),
                "min_1grado": float(np.nanmin(target)), "max_1grado": float(np.nanmax(target)),
            }
            if nombre == albedo.name:
                # Referencia independiente: media de los 8x8 píxeles nativos.
                native = src.read(1).reshape(180, 8, 360, 8).astype("float64")
                counts = np.isfinite(native).sum(axis=(1, 3))
                expected = np.full(target.shape, np.nan, dtype="float64")
                np.divide(np.nansum(native, axis=(1, 3)), counts, out=expected, where=counts > 0)
                if not np.array_equal(np.isnan(target), counts == 0):
                    raise ValueError("La reproyección ha rellenado huecos de albedo")
                error = float(np.nanmax(np.abs(target - expected)))
                if error > 1e-6:
                    raise ValueError(f"La media reproyectada difiere de los bloques 8x8: {error}")
                result["error_max_media_8x8"] = error
                result["nodata_conservado"] = True
            results.append(result)
    return {
        "compatible": True, "dataset": REPO, "revision_referencias": revision,
        "crs_destino": CRS_MARTE.to_wkt(), "geotransform_destino": list(GRID.to_gdal()),
        "criterio": "Reproyección a la malla del notebook, no igualdad de resoluciones nativas",
        "GHI": "Misma interpretación planetocéntrica del notebook; celdas originales conservadas",
        "capas": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--salida", type=Path, default=ROOT / "Albedo_marte.tif")
    parser.add_argument("--fuentes", type=Path, default=Path(__file__).resolve().parent / "fuentes_albedo")
    parser.add_argument("--informe", type=Path, default=ROOT / "auditoria_tiffs" / "albedo.json")
    parser.add_argument("--comprobar-compatibilidad", action="store_true")
    parser.add_argument("--revision", help="Commit HF de las seis capas; permite validación offline desde caché")
    args = parser.parse_args()
    values, provenance = leer_fuentes(args.fuentes)
    crear_geotiff(args.salida, values, provenance)
    report = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "producto": provenance}
    if args.comprobar_compatibilidad:
        report["compatibilidad"] = comprobar_compatibilidad(args.salida, args.revision)
    args.informe.parent.mkdir(parents=True, exist_ok=True)
    args.informe.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(f"GeoTIFF verificado: {args.salida}")
    print(f"Píxeles válidos: {provenance['validos']}; NoData: {provenance['nodata']}")
    print(f"Informe: {args.informe}")


if __name__ == "__main__":
    main()
