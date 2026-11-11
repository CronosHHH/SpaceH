#!/usr/bin/env python3
"""Prototipo terrestre a 1°: seis variables y dos coberturas, sin caché de TIFF.

Descarga únicamente los cuatro GeoTIFF pequeños del catálogo terrestre mediante
HTTP a memoria, verifica su SHA256 y conserva todos los NoData. Los productos
globales de 15 segundos de arco permanecen en Hugging Face.
"""

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
import rasterio as rio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from huggingface_hub import hf_hub_url


TIERRA = Path(__file__).resolve().parent
REPO = "Renato-R-V/hspace-datasets"
SALIDA = Path(tempfile.gettempdir()) / "hspace_tierra_productos" / "prototipo"
FORMA = (180, 360)
TRANSFORMACION = from_origin(-180, 90, 1, 1)
MAX_DESCARGA = 16 * 1024 * 1024
ARCHIVOS = (
    "NASADEM_tierra_1grado.tif", "GHI_tierra.tif", "Albedo_tierra.tif",
    "Fracciones_mascaras_tierra_MODIS_2021_1grado.tif",
)
VARIABLES = {
    "Elevación NASADEM": ("m EGM96", "terrain"),
    "GHI terrestre": ("W/m²", "inferno"),
    "Albedo terrestre": ("adimensional", "cividis"),
    "Fracción ciudades": ("fracción clasificada", "Reds"),
    "Fracción agua": ("fracción clasificada", "Blues"),
    "Fracción vegetación": ("fracción clasificada", "Greens"),
}
COBERTURAS = ("Cobertura NASADEM", "Cobertura clasificada")
LICENCIA = "CC-BY-SA-4.0"
ATRIBUCION = (
    "NASA POWER; NASA/JPL-Caltech NASADEM; Rolf Simoes/OpenGeoHub (2023), "
    "doi:10.5281/zenodo.8367523, MODIS MCD12Q1.061; Made with Natural Earth"
)


def descargar_memoria(url, limite=MAX_DESCARGA):
    """Limita la descarga incluso cuando el servidor no declara Content-Length."""
    request = Request(url, headers={"User-Agent": "HSpace-Earth-prototype/1.0"})
    with urlopen(request, timeout=120) as response:
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > limite:
            raise ValueError(f"Descarga superior al límite de {limite} bytes")
        content = response.read(limite + 1)
    if len(content) > limite:
        raise ValueError("La respuesta excede el límite permitido para los resúmenes")
    return content


def cargar_catalogo(ruta=None, revision=None):
    """Fija un commit remoto por ejecución; acepta el catálogo local o publicado."""
    ruta = Path(ruta or TIERRA / "catalogo.json")
    if ruta.exists():
        content = ruta.read_bytes()
    else:
        url = hf_hub_url(REPO, "tierra/catalogo.json", repo_type="dataset", revision=revision or "main")
        content = descargar_memoria(url)
    catalogo = json.loads(content)
    repo = catalogo.get("dataset", REPO)
    if revision is None:
        # Solo metadatos HTTP; no crea entradas en ~/.cache/huggingface.
        metadata = json.loads(descargar_memoria("https://huggingface.co/api/datasets/" + quote(repo, safe="/")))
        revision = metadata["sha"]
    for archivo in ARCHIVOS:
        if archivo not in catalogo.get("productos", {}):
            raise ValueError(f"El catálogo aún no contiene {archivo}; publicar todos los productos primero")
    catalogo["_sha256_catalogo"] = hashlib.sha256(content).hexdigest()
    return catalogo, revision


def leer_resumen(catalogo, revision, nombre, bandas):
    record = catalogo["productos"][nombre]
    size = record["bytes"]
    if not isinstance(size, int) or size <= 0 or size > MAX_DESCARGA:
        raise ValueError(f"{nombre}: solo se permiten resúmenes pequeños, no el mosaico global")
    url = hf_hub_url(catalogo.get("dataset", REPO), record["archivo"],
                     repo_type="dataset", revision=revision)
    content = descargar_memoria(url, limite=size)
    if len(content) != size or hashlib.sha256(content).hexdigest() != record["sha256"]:
        raise ValueError(f"{nombre}: tamaño o SHA256 distintos al catálogo")
    with MemoryFile(content) as memory, memory.open() as source:
        if (source.shape != FORMA or source.crs.to_epsg() != 4326
                or source.transform != TRANSFORMACION or source.count != bandas
                or source.nodata is None or not np.isnan(source.nodata)):
            raise ValueError(f"{nombre}: no coincide con la cuadrícula global de 1° o NoData esperado")
        arrays = source.read(masked=True).filled(np.nan).astype("float32")
        if np.isinf(arrays).any():
            raise ValueError(f"{nombre}: hay infinitos")
        info = {"archivo": record["archivo"], "sha256": record["sha256"], "url": url,
                "revision": revision, "tags": source.tags(), "bandas": []}
        for i in range(1, bandas + 1):
            info["bandas"].append({"nombre": source.descriptions[i - 1], "tags": source.tags(i)})
    print(f"Verificado en memoria: {nombre} · {size:,} bytes · {bandas} banda(s)", flush=True)
    return arrays, info


def fraccion_valida(array, nombre, permitir_nan=False):
    good = np.isfinite(array)
    if (not permitir_nan and not good.all()) or np.any((array[good] < 0) | (array[good] > 1)):
        raise ValueError(f"{nombre}: fracción fuera de 0–1 o sin cobertura declarada")


def preparar_datos(catalogo, revision):
    """Reúne resúmenes ya alineados: no infla radiación de 1° a 463 m."""
    fuentes = {}
    dem, fuentes["dem"] = leer_resumen(catalogo, revision, ARCHIVOS[0], 2)
    ghi, fuentes["ghi"] = leer_resumen(catalogo, revision, ARCHIVOS[1], 1)
    albedo, fuentes["albedo"] = leer_resumen(catalogo, revision, ARCHIVOS[2], 1)
    masks, fuentes["mascaras"] = leer_resumen(catalogo, revision, ARCHIVOS[3], 4)
    if fuentes["ghi"]["bandas"][0]["tags"].get("units") != "W/m^2":
        raise ValueError("GHI debe estar en W/m²")
    if fuentes["albedo"]["bandas"][0]["tags"].get("units") != "1":
        raise ValueError("Albedo debe ser adimensional")
    periodo = fuentes["ghi"]["tags"].get("climatology_period")
    if not periodo or periodo != fuentes["albedo"]["tags"].get("climatology_period"):
        raise ValueError("GHI y albedo no comparten el periodo climatológico")
    dem_tags = fuentes["dem"]["bandas"][0]["tags"]
    if dem_tags.get("units") != "m" or dem_tags.get("vertical_datum") != "EGM96":
        raise ValueError("La elevación NASADEM debe estar en metros respecto a EGM96")
    if fuentes["mascaras"]["tags"].get("license") != LICENCIA:
        raise ValueError("Revisar la licencia de las máscaras antes de combinar datos")
    fraccion_valida(dem[1], "Cobertura NASADEM")
    if not np.array_equal(np.isfinite(dem[0]), dem[1] > 0):
        raise ValueError("La máscara de elevación no coincide con su cobertura")
    finite_dem = dem[0][np.isfinite(dem[0])]
    if not finite_dem.size or finite_dem.min() < -500 or finite_dem.max() > 9000:
        raise ValueError("La elevación no tiene valores plausibles en metros")
    fraccion_valida(masks[3], "Cobertura clasificada")
    classified = masks[3] > 0
    if not classified.any():
        raise ValueError("La máscara no contiene ninguna celda clasificada")
    for i, label in enumerate(("Ciudades", "Agua", "Vegetación")):
        fraccion_valida(masks[i], label, permitir_nan=True)
        if not np.array_equal(np.isfinite(masks[i]), classified):
            raise ValueError(f"{label}: desconocidos y cobertura no coinciden")
    if np.any(masks[:3, classified].sum(axis=0) > 1 + 1e-6):
        raise ValueError("Las fracciones clasificadas suman más de 1")
    for array, limits, label in ((ghi[0], (0, 600), "GHI"), (albedo[0], (0, 1), "Albedo")):
        good = array[np.isfinite(array)]
        if not good.size or good.min() < limits[0] or good.max() > limits[1]:
            raise ValueError(f"{label}: rango físico inesperado")
    datos = {
        "Elevación NASADEM": dem[0], "GHI terrestre": ghi[0], "Albedo terrestre": albedo[0],
        "Fracción ciudades": masks[0], "Fracción agua": masks[1], "Fracción vegetación": masks[2],
    }
    coberturas = {COBERTURAS[0]: dem[1], COBERTURAS[1]: masks[3]}
    procedencia = {"fuentes": fuentes, "revision_hf": revision,
                   "sha256_catalogo": catalogo["_sha256_catalogo"], "periodo_radiacion": periodo,
                   "dataset": catalogo.get("dataset", REPO)}
    return datos, coberturas, procedencia


def resumir(datos, coberturas):
    for nombre, array in datos.items():
        good = np.isfinite(array)
        print(f"{nombre:23} {good.mean():7.2%} con datos | "
              f"{np.nanmin(array):.6g} a {np.nanmax(array):.6g} [{VARIABLES[nombre][0]}]")
    print("Forma del cubo:", (len(datos), *FORMA))
    for nombre, array in coberturas.items():
        print(f"{nombre}: {(array > 0).sum():,} celdas con algún píxel de origen; "
              f"{np.count_nonzero((array > 0) & (array < 1)):,} parcialmente cubiertas")


def guardar(datos, coberturas, procedencia, salida=SALIDA, informe=None):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    resultados = {}
    productos = []
    for filename, bands in (("tierra_1grado.tif", datos), ("coberturas_tierra_1grado.tif", coberturas)):
        path = salida / filename
        arrays = np.stack(list(bands.values())).astype("float32")
        with rio.open(path, "w", driver="GTiff", height=180, width=360, count=len(bands),
                      dtype="float32", crs="EPSG:4326", transform=TRANSFORMACION,
                      nodata=np.nan, compress="deflate", predictor=3, tiled=True) as dst:
            dst.write(arrays)
            for i, name in enumerate(bands, 1):
                dst.set_band_description(i, name)
                unit = "m" if name == "Elevación NASADEM" else "W/m^2" if name == "GHI terrestre" else "1"
                dst.update_tags(i, units=unit)
                if name == "Elevación NASADEM":
                    dst.update_tags(i, vertical_datum="EGM96")
                elif name.startswith("Fracción"):
                    dst.update_tags(i, denominator="classified pixels only")
                elif name in coberturas:
                    dst.update_tags(i, denominator="all native pixels in analysis cell")
            fraction_note = (
                "Valid or classified pixel counts divided by all native pixels in each analysis cell"
                if bands is coberturas else
                "Thematic fractions among classified pixels, not subpixel biophysical abundance; coverage in companion raster"
            )
            dst.update_tags(
                license=LICENCIA, attribution=ATRIBUCION,
                source_dataset=procedencia["dataset"], source_revision=procedencia["revision_hf"],
                source_catalog_sha256=procedencia["sha256_catalogo"],
                source_files=json.dumps({k: v["archivo"] for k, v in procedencia["fuentes"].items()}),
                grid="Earth WGS84; 1 degree; 360x180; native POWER scale",
                climatology_period=procedencia["periodo_radiacion"],
                classification_year="2021",
                fractions_note=fraction_note,
                unknown_note="NaN remains unknown; zero coverage is a valid fraction",
                attribution_note="Mixed derived product contains CC-BY-SA-4.0 mask fractions; share alike",
            )
        with rio.open(path) as check:
            if (check.crs.to_epsg() != 4326 or check.transform != TRANSFORMACION or check.shape != FORMA
                    or not np.array_equal(check.read(), arrays, equal_nan=True)
                    or not np.array_equal(check.read_masks() == 0, np.isnan(arrays))):
                raise ValueError(f"{filename}: valores modificados durante la escritura")
        resultados[filename] = str(path)
        productos.append({"archivo": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "bandas": len(bands), "bytes": path.stat().st_size})
        print("GeoTIFF guardado y verificado:", path)
    joint = np.logical_and.reduce([np.isfinite(a) for a in datos.values()])
    if not joint.any():
        raise ValueError("El cubo no contiene ninguna celda con las seis variables conocidas")
    report = {
        "compatible": True, "productos": productos, "revision_hf_fuentes": procedencia["revision_hf"],
        "sha256_catalogo_fuentes": procedencia["sha256_catalogo"],
        "fuentes": {k: {"archivo": v["archivo"], "sha256": v["sha256"]}
                    for k, v in procedencia["fuentes"].items()},
        "crs": "EPSG:4326", "dimensiones": [360, 180], "geotransform": list(TRANSFORMACION.to_gdal()),
        "cubo": [6, 180, 360], "celdas_seis_variables_conocidas": int(joint.sum()),
        "celdas_validas_por_variable": {k: int(np.isfinite(v).sum()) for k, v in datos.items()},
        "coberturas": {k: {"min": float(v.min()), "max": float(v.max()),
                            "celdas_cobertura_positiva": int((v > 0).sum())} for k, v in coberturas.items()},
        "checks": {"malla_comun": True, "valores_y_mascaras_conservados": True,
                   "rangos_fisicos_y_unidades": True, "cobertura_y_nodata_coherentes": True,
                   "periodo_radiacion_coincidente": True, "sha256_fuentes_verificados": True,
                   "licencia_y_atribucion_conservadas": True},
        "licencia": LICENCIA,
    }
    report_path = Path(informe or TIERRA / "auditoria" / "prototipo.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print("Informe del prototipo:", report_path)
    return resultados


def visualizar(datos, salida=SALIDA):
    import matplotlib.pyplot as plt

    columns = 2
    rows = (len(datos) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(14, 3.5 * rows), squeeze=False, constrained_layout=True)
    for axis, (name, array) in zip(axes.flat, datos.items()):
        unit, palette = VARIABLES[name]
        cmap = plt.get_cmap(palette).copy()
        cmap.set_bad("#d9dfe5")
        if name.startswith("Fracción") or name == "Albedo terrestre":
            vmin, vmax = 0, 1
        else:
            vmin, vmax = np.nanpercentile(array, [2, 98])
        image = axis.imshow(np.ma.masked_invalid(array), extent=(-180, 180, -90, 90),
                            origin="upper", interpolation="nearest", cmap=cmap, vmin=vmin, vmax=vmax)
        axis.set(title=name, xlabel="Longitud (°)", ylabel="Latitud (°)")
        fig.colorbar(image, ax=axis, label=unit, shrink=.8, extend="neither" if vmax == 1 else "both")
    for axis in axes.flat[len(datos):]:
        axis.set_visible(False)
    fig.suptitle("Tierra · mapas a 1° · gris = sin datos", fontsize=15)
    if salida is not None:
        path = Path(salida) / "tierra_conjunto.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=160, metadata={"License": LICENCIA, "Attribution": ATRIBUCION})
        print("Vista conjunta:", path)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogo", type=Path)
    parser.add_argument("--revision", help="Commit HF; por defecto se fija el HEAD al comenzar")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args()
    catalogo, revision = cargar_catalogo(args.catalogo, args.revision)
    datos, coberturas, procedencia = preparar_datos(catalogo, revision)
    resumir(datos, coberturas)
    guardar(datos, coberturas, procedencia, args.salida)
    fig = visualizar(datos, args.salida)
    import matplotlib.pyplot as plt
    plt.close(fig)


if __name__ == "__main__":
    main()
