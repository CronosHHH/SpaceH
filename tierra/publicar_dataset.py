#!/usr/bin/env python3
"""Valida y publica productos terrestres; borra locales solo tras verificar HF.

Uso (desde la raíz):
  marte/.venv/bin/python tierra/publicar_dataset.py /tmp/hspace_tierra_productos/*.tif --eliminar-locales

El catálogo guarda hashes, unidades, estadísticas completas y georreferencias.
Los GeoTIFF grandes se verifican mediante el SHA256 LFS que confirma HF, sin
descargar otra copia. Los archivos pequeños se verifican leyendo su contenido.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import rasterio as rio
from rasterio.transform import from_origin
# El caché de subida tampoco debe llenar el disco principal del usuario.
os.environ.setdefault("HF_XET_CACHE", "/tmp/hspace_hf_xet")
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_url


ROOT = Path(__file__).resolve().parent
REPO = "Renato-R-V/hspace-datasets"
CATALOGO = ROOT / "catalogo.json"


def hash_archivo(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def especificacion(nombre, count):
    if nombre == "GHI_tierra.tif":
        return [(0, 600, "W/m^2")]
    if nombre == "Albedo_tierra.tif":
        return [(0, 1, "1")]
    if nombre == "NASADEM_tierra_15arcsec.tif":
        return [(-500, 9000, "m EGM96")]
    if nombre == "NASADEM_tierra_1grado.tif":
        return [(-500, 9000, "m EGM96"), (0, 1, "fracción válida")]
    if nombre.startswith("Mascaras_tierra_"):
        return [(0, 15, "bits: ciudad=1; agua=2; vegetación=4; océano suplementario=8")]
    if nombre.startswith("Fracciones_mascaras_tierra_") and count == 4:
        return [(0, 1, "fracción")] * 4
    if nombre == "tierra_1grado.tif" and count == 6:
        return [(-500, 9000, "m EGM96"), (0, 600, "W/m^2"), (0, 1, "1")] + [(0, 1, "fracción")] * 3
    if nombre == "coberturas_tierra_1grado.tif" and count == 2:
        return [(0, 1, "fracción")] * 2
    raise ValueError(f"Producto no reconocido: {nombre}; añadir su especificación antes de publicarlo")


def hash_auditado(nombre):
    """Una cabecera global correcta no basta para certificar una ejecución completa."""
    if nombre in ("GHI_tierra.tif", "Albedo_tierra.tif"):
        report = json.loads((ROOT / "auditoria/radiacion.json").read_text())
        if report.get("compatible") is not True:
            raise ValueError("Falta la validación conjunta de GHI y albedo")
        key = "ghi" if nombre.startswith("GHI") else "albedo"
        return report["capas"][key]["sha256"]
    if nombre.startswith("NASADEM_"):
        report = json.loads((ROOT / "auditoria/nasadem.json").read_text())
        if report.get("producto_completo") is not True:
            raise ValueError("NASADEM todavía no tiene una auditoría global completa")
        return report["sha256_tif" if "15arcsec" in nombre else "sha256_resumen"]
    if nombre.startswith(("Mascaras_", "Fracciones_mascaras_")):
        report = json.loads((ROOT / "auditoria/mascaras.json").read_text())
        if report.get("validado") is not True:
            raise ValueError("Las máscaras todavía no tienen una auditoría completa")
    else:
        report = json.loads((ROOT / "auditoria/prototipo.json").read_text())
        if report.get("compatible") is not True:
            raise ValueError("El prototipo todavía no tiene una auditoría completa")
    return next(r["sha256"] for r in report["productos"] if r["archivo"] == nombre)


def auditar(path):
    path = Path(path)
    stats = []
    with rio.Env(GDAL_PAM_ENABLED="NO"), rio.open(path) as src:
        step = 1 / 240 if "15arcsec" in path.name else 1
        expected = (round(180 / step), round(360 / step))
        if (src.crs != rio.crs.CRS.from_epsg(4326) or src.shape != expected
                or not src.transform.almost_equals(from_origin(-180, 90, step, step))):
            raise ValueError(f"{path.name}: no coincide con la malla WGS84 global declarada")
        spec = especificacion(path.name, src.count)
        if len(spec) != src.count or src.nodata is None:
            raise ValueError(f"{path.name}: número de bandas o NoData inesperado")
        for i, (lo, hi, unit) in enumerate(spec, 1):
            count = 0
            total = 0.0
            minimum, maximum = float("inf"), -float("inf")
            for _, window in src.block_windows(i):
                array = src.read(i, window=window, masked=True)
                values = array.compressed()
                if not values.size:
                    continue
                if not np.isfinite(values).all() or values.min() < lo or values.max() > hi:
                    raise ValueError(f"{path.name}, banda {i}: valor fuera de [{lo}, {hi}]")
                if path.name.startswith("Mascaras_tierra_") and not np.isin(values, [0, 1, 2, 4, 10]).all():
                    raise ValueError(f"{path.name}: código de máscara no documentado")
                count += values.size
                total += values.sum(dtype="float64")
                minimum = min(minimum, float(values.min()))
                maximum = max(maximum, float(values.max()))
            if count == 0:
                raise ValueError(f"{path.name}, banda {i}: sin datos válidos")
            stats.append({"banda": i, "nombre": src.descriptions[i-1], "unidad": unit,
                          "validos": int(count), "min": minimum, "max": maximum,
                          "media": total / count, "tags": src.tags(i)})
        result = {
            "archivo": "tierra/" + path.name, "bytes": path.stat().st_size,
            "sha256": hash_archivo(path), "crs": src.crs.to_string(),
            "dimensiones": [src.width, src.height], "geotransform": list(src.transform.to_gdal()),
            "tipo": list(src.dtypes), "nodata": "NaN" if np.isnan(src.nodata) else src.nodata,
            "bandas": stats, "tags": src.tags(),
        }
    print(f"Validado completo: {path.name}", flush=True)
    return result


def verificar_remoto(api, repo, records, revision):
    paths = [r["archivo"] for r in records]
    infos = {x.path: x for x in api.get_paths_info(repo, paths=paths, repo_type="dataset", revision=revision)}
    for record in records:
        info = infos[record["archivo"]]
        if info.size != record["bytes"]:
            raise ValueError(f"Tamaño remoto distinto: {record['archivo']}")
        if info.lfs:
            if info.lfs.sha256 != record["sha256"]:
                raise ValueError(f"SHA256 remoto distinto: {record['archivo']}")
        else:
            digest = hashlib.sha256()
            with urlopen(hf_hub_url(repo, record["archivo"], repo_type="dataset", revision=revision), timeout=120) as f:
                while block := f.read(1024 * 1024):
                    digest.update(block)
            if digest.hexdigest() != record["sha256"]:
                raise ValueError(f"Contenido remoto distinto: {record['archivo']}")
        print("Remoto verificado:", record["archivo"], flush=True)


def publicar(paths, eliminar=False, repo=REPO):
    paths = [Path(p).resolve() for p in paths]
    if eliminar:
        # Nunca eliminar rutas arbitrarias que no sean productos de este proyecto.
        for path in paths:
            if not (path.is_relative_to(ROOT) or path.is_relative_to(Path("/tmp/hspace_tierra_productos"))):
                raise ValueError(f"Borrado permitido solo para productos terrestres del proyecto: {path}")
    expected_hashes = [hash_auditado(p.name) for p in paths]
    records = [auditar(p) for p in paths]
    if any(r["sha256"] != expected for r, expected in zip(records, expected_hashes)):
        raise ValueError("Un TIFF ha cambiado desde su auditoría: volver a generar y validar antes de publicar")
    catalog = json.loads(CATALOGO.read_text()) if CATALOGO.exists() else {"dataset": repo, "productos": {}}
    for record in records:
        catalog["productos"][Path(record["archivo"]).name] = record
    catalog["actualizacion_utc"] = datetime.now(timezone.utc).isoformat()
    catalog["notas"] = [
        "15 segundos de arco equivalen a unos 464 m en el ecuador; ancho este-oeste decrece con la latitud.",
        "GHI y albedo POWER son nativos a 1 grado; no tienen resolución local de 464 m.",
        "Las capas mantienen fechas y definiciones físicas diferentes; consultar documentación por producto.",
    ]
    candidate = ROOT / ".catalogo_publicacion.json"
    candidate.write_text(json.dumps(catalog, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    api = HfApi()
    parent = api.repo_info(repo, repo_type="dataset").sha
    additions = [CommitOperationAdd(path_in_repo=r["archivo"], path_or_fileobj=str(p))
                 for p, r in zip(paths, records)]
    additions.append(CommitOperationAdd(path_in_repo="tierra/catalogo.json", path_or_fileobj=str(candidate)))
    result = api.create_commit(
        repo_id=repo, repo_type="dataset", parent_commit=parent, operations=additions,
        commit_message="Add validated Earth products: " + ", ".join(p.name for p in paths),
    )
    verificar_remoto(api, repo, records, result.oid)
    candidate.replace(CATALOGO)
    receipt = ROOT / "auditoria" / ("publicacion_" + result.oid[:12] + ".json")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "commit": result.oid, "url": result.commit_url, "productos": records,
        "remoto_sha256_y_tamano_verificados": True, "eliminacion_local_solicitada": eliminar,
    }, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    if eliminar:
        for path in paths:
            path.unlink()
            Path(str(path) + ".aux.xml").unlink(missing_ok=True)
            path.with_suffix(".progreso.jsonl").unlink(missing_ok=True)
            print("Eliminado tras verificar la publicación:", path, flush=True)
    print("Publicado:", result.commit_url, flush=True)
    return result.oid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivos", type=Path, nargs="+")
    parser.add_argument("--eliminar-locales", action="store_true")
    parser.add_argument("--repo", default=REPO)
    args = parser.parse_args()
    publicar(args.archivos, args.eliminar_locales, args.repo)
