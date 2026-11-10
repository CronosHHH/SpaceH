#!/usr/bin/env python3
"""Auditoría reproducible, de solo lectura, de los seis TIFF de Marte.

Lee TODOS los píxeles por bloques, ignora estadísticas aproximadas en .aux.xml
y contrasta los minerales directamente con los enteros de los IMG originales.
Dependencias: numpy, GDAL (osgeo), Pillow. Salida: auditoria_tiffs/resultados.json.
Código de salida 1 si falla alguna comprobación, 0 si pasan todas.
"""

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image


ROOT = Path(__file__).resolve().parent
gdal.UseExceptions()
gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
gdal.SetCacheMax(128 * 1024 * 1024)
CHECKS = []


def check(file, name, condition, detail="", severity="error"):
    status = "PASS" if condition else ("WARN" if severity == "aviso" else "FAIL")
    result = {"archivo": file, "test": name, "ok": bool(condition), "estado": status, "detalle": detail}
    CHECKS.append(result)
    print(f"{status} {file}: {name} {detail}", flush=True)


def number(label, key):
    match = re.search(rf"^\s*{re.escape(key)}\s*=\s*([-+\d.eE]+)", label, re.M)
    if match is None:
        raise ValueError(f"Falta {key} en la etiqueta")
    return float(match[1])


def valid_mask(array, nodata):
    if nodata is None:
        return np.ones(array.shape, dtype=bool)
    if math.isnan(nodata):
        return ~np.isnan(array)
    return array != nodata


def inspect(path):
    ds = gdal.Open(str(path), gdal.GA_ReadOnly)
    name = path.name
    band = ds.GetRasterBand(1)
    width, height = ds.RasterXSize, ds.RasterYSize
    gt = ds.GetGeoTransform()
    crs = ds.GetSpatialRef()
    nodata = band.GetNoDataValue()
    check(name, "una_banda", ds.RasterCount == 1)
    check(name, "CRS_marciano", crs is not None and 3.3e6 < crs.GetSemiMajor() < 3.5e6)
    check(name, "norte_arriba", gt[1] > 0 and gt[5] < 0 and gt[2] == gt[4] == 0)

    label_path = ROOT / "origen_ds_minerales" / f"{path.stem}.LBL"
    raw = None
    label = None
    raw_valid_count = mask_errors = value_errors = 0
    max_error = 0.0
    if label_path.exists():
        label = label_path.read_text()
        image_name = re.search(r'^\s*\^IMAGE\s*=\s*"([^"]+)"', label, re.M).group(1)
        img = label_path.parent / image_name
        source_width = int(number(label, "LINE_SAMPLES"))
        source_height = int(number(label, "LINES"))
        check(name, "dimensiones_PDS", (width, height) == (source_width, source_height))
        check(name, "formato_PDS", "LSB_INTEGER" in label and number(label, "SAMPLE_BITS") == 16)
        check(name, "bytes_IMG", img.stat().st_size == source_width * source_height * 2)
        raw = np.memmap(img, mode="r", dtype="<i2", shape=(source_height, source_width))
        scale, offset = number(label, "SCALING_FACTOR"), number(label, "OFFSET")
        missing = number(label, "MISSING_CONSTANT")
        check(name, "NoData_PDS", nodata == missing)
        check(name, "valores_fisicos_sin_doble_escala",
              band.DataType == gdal.GDT_Float32 and band.GetScale() in (None, 1.0)
              and band.GetOffset() in (None, 0.0))

    count = nonfinite = 0
    total = total_sq = 0.0
    minimum, maximum = math.inf, -math.inf
    for y in range(0, height, 128):
        rows = min(128, height - y)
        array = band.ReadAsArray(0, y, width, rows)
        mask = valid_mask(array, nodata)
        nonfinite += int(np.count_nonzero(mask & ~np.isfinite(array)))
        values = array[mask & np.isfinite(array)].astype(np.float64)
        count += values.size
        if values.size:
            minimum = min(minimum, float(values.min()))
            maximum = max(maximum, float(values.max()))
            total += float(values.sum())
            total_sq += float(np.square(values).sum())
        if raw is not None:
            source = raw[y:y + rows]
            source_mask = source != missing
            raw_valid_count += int(np.count_nonzero(source_mask))
            mask_errors += int(np.count_nonzero(mask != source_mask))
            # Se aplica la transformación en Float64 y después se redondea a Float32.
            expected = (source[source_mask].astype(np.float64) * scale + offset).astype(np.float32)
            actual = array[source_mask]
            if expected.size:
                error = np.abs(actual.astype(np.float64) - expected)
                max_error = max(max_error, float(error.max()))
                value_errors += int(np.count_nonzero(~np.isclose(actual, expected, rtol=2e-7, atol=1e-8)))

    check(name, "lectura_completa_y_valores_finitos", count > 0 and nonfinite == 0)
    mean = total / count if count else None
    metrics = {
        "dimensiones": [width, height], "tipo": gdal.GetDataTypeName(band.DataType),
        "pixeles_totales": width * height, "validos": count,
        "porcentaje_valido": 100 * count / (width * height), "no_finitos_no_enmascarados": nonfinite,
        "min": minimum if count else None, "max": maximum if count else None, "media": mean,
        "desviacion": math.sqrt(max(0.0, total_sq / count - mean * mean)) if count else None,
        "nodata": nodata, "geotransform": gt, "crs": ds.GetProjection(),
    }
    if label is not None:
        check(name, "mascara_igual_al_IMG", mask_errors == 0, f"diferencias={mask_errors}")
        check(name, "escala_igual_al_IMG", value_errors == 0, f"error_max={max_error:.9g}")
        lo, hi = number(label, "MINIMUM"), number(label, "MAXIMUM")
        check(name, "rango_publicado_PDS", minimum >= lo - 0.0005 and maximum <= hi + 0.0005,
              f"observado=[{minimum:.9g}, {maximum:.9g}], etiqueta=[{lo}, {hi}]")
        expected_pixel = number(label, "MAP_SCALE") * 1000
        check(name, "resolucion_PDS", abs(gt[1] - expected_pixel) < 1e-6)
        # La etiqueta declara cobertura simétrica -180..180, -90..90 y centro 0,0.
        center = [gt[0] + width * gt[1] / 2, gt[3] + height * gt[5] / 2]
        check(name, "centro_global_coherente_con_etiqueta", max(map(abs, center)) <= expected_pixel * .01,
              f"centro_m={center}; esperado=[0,0]")
        metrics.update({"validos_IMG": raw_valid_count, "diferencias_mascara": mask_errors,
                        "diferencias_valores": value_errors, "error_max_escala": max_error,
                        "rango_etiqueta": [lo, hi], "media_etiqueta": number(label, "MEAN"),
                        "centro_m": center})
        check(name, "media_coherente_con_PDS", abs(mean - number(label, "MEAN")) <= .0005)
        check(name, "desviacion_coherente_con_PDS",
              abs(metrics["desviacion"] - number(label, "STANDARD_DEVIATION")) <= .0005)
        # Verificar la interpretación alternativa SIN crear ni modificar TIFFs.
        options = ("PDS_SampleProjOffset_Shift", "PDS_LineProjOffset_Shift")
        previous = [gdal.GetConfigOption(key) for key in options]
        try:
            for key in options:
                gdal.SetConfigOption(key, "-0.5")
            corrected_source = gdal.Open(str(label_path))
            corrected_gt = corrected_source.GetGeoTransform()
            corrected_center = [corrected_gt[0] + width * corrected_gt[1] / 2,
                                corrected_gt[3] + height * corrected_gt[5] / 2]
            check(name, "opciones_PDS_corrigen_centro_en_memoria",
                  max(map(abs, corrected_center)) < 1e-6)
            metrics["geotransform_con_shift_menos_0_5"] = corrected_gt
            corrected_source = None
        finally:
            for key, value in zip(options, previous):
                gdal.SetConfigOption(key, value)
    elif name == "GHI_marte.tif":
        values = band.ReadAsArray().astype(np.float64)
        check(name, "malla_GHI_1_grado", (width, height) == (360, 180)
              and gt == (-180.0, 1.0, 0.0, 90.0, 0.0, -1.0))
        lat = np.deg2rad(90 - (np.arange(height) + .5))
        declination = np.arcsin(np.sin(np.deg2rad(25.19)) * np.sin(np.deg2rad(18.9)))
        # Verificación independiente: integrar radiación instantánea durante un sol.
        hour = -np.pi + (np.arange(1440) + .5) * 2 * np.pi / 1440
        cos_zenith = (np.sin(lat[:, None]) * np.sin(declination)
                      + np.cos(lat[:, None]) * np.cos(declination) * np.cos(hour))
        expected_daily = 590 * .75 * np.maximum(cos_zenith, 0).mean(axis=1)
        error = float(np.abs(values - expected_daily[:, None]).max())
        global_mean = float(np.average(values.mean(axis=1), weights=np.cos(lat)))
        check(name, "rango_fisico_modelo", minimum >= 0 and maximum <= 590 * .75)
        check(name, "integracion_independiente_sol", error < .001, f"error_max_Wm2={error:.9g}")
        check(name, "media_global_S_sobre_4", abs(global_mean - 590 * .75 / 4) < .01,
              f"media_Wm2={global_mean:.9g}")
        check(name, "constancia_longitudinal_modelo", np.ptp(values, axis=1).max() == 0)
        check(name, "unidades_y_estacion", band.GetMetadataItem("units") == "W/m^2"
              and band.GetMetadataItem("solar_longitude_deg") == "18.9")
        metrics.update({"error_integracion_Wm2": error, "media_global_ponderada_Wm2": global_mean,
                        "ceros": int(np.count_nonzero(values == 0)),
                        "uso": "Modelo simplificado de media diaria Ls=18.9; no observación ni media anual."})
    elif "MOLA" in name:
        check(name, "dimensiones_MOLA_128ppd", (width, height) == (46080, 23040))
        check(name, "rango_plausible_elevacion_m", -10000 < minimum < -6000 and 18000 < maximum < 25000,
              f"rango_m=[{minimum}, {maximum}]")
        expected_pixel = 2 * np.pi * crs.GetSemiMajor() / width
        edge_error = width * (gt[1] - expected_pixel) / 2
        check(name, "coincidencia_exacta_malla_nominal_USGS", abs(gt[1] - expected_pixel) < 1e-6
              and abs(gt[0] + width * gt[1] / 2) < 1e-5
              and abs(gt[3] + height * gt[5] / 2) < 1e-5,
              f"pixel_real={gt[1]:.10f}, nominal={expected_pixel:.10f}, exceso_borde_X_m={edge_error:.6f}",
              severity="aviso")
        metrics["desviacion_borde_X_m_frente_malla_nominal"] = edge_error
        metrics["pixel_nominal_USGS_m"] = expected_pixel
        metrics["procedencia"] = "Sin fuente raw/checksum local: solo integridad, geometría y plausibilidad."

    png_path = ROOT / "imagenes_png" / f"{path.stem}.png"
    check(name, "PNG_existe", png_path.exists())
    if png_path.exists():
        with Image.open(png_path) as image:
            png = np.asarray(image)
            metrics["png"] = {"dimensiones": list(image.size), "min": int(png.min()),
                              "max": int(png.max()), "niveles": int(np.unique(png).size),
                              "porcentaje_negro": 100 * float(np.mean(png == 0))}
            check(name, "PNG_no_uniforme", np.unique(png).size > 1)
            if raw is not None and image.size == (width // 4, height // 4):
                # El generador usa vecino más próximo al reducir cada eje a 25 %.
                selected_mask = raw[2::4, 2::4] != missing
                selected_count = int(selected_mask.sum())
                black_count = int(np.count_nonzero(selected_mask & (png == 0)))
                occupied_cells = 0
                for row in range(0, height, 128):
                    source_mask = raw[row:row + 128] != missing
                    occupied_cells += int(source_mask.reshape(-1, 4, width // 4, 4).any(axis=(1, 3)).sum())
                metrics["png"].update({"validos_seleccionados_vecino_proximo": selected_count,
                                       "celdas_con_algun_dato_en_bloque_4x4": occupied_cells,
                                       "validos_pintados_negro": black_count,
                                       "porcentaje_validos_pintados_negro": 100 * black_count / selected_count
                                       if selected_count else None})
    return metrics


def main():
    paths = sorted(p for p in ROOT.iterdir() if p.suffix.lower() in {".tif", ".tiff"})
    expected = {"1-Mars_MGS_MOLA_DEM_mosaic_global_463m.tif", "GHI_marte.tif",
                "pyroxene_bd2000_equ_map.tiff",
                *(f"olivine_osp{i}_equ_map.tiff" for i in (1, 2, 3))}
    check("inventario", "seis_TIFF_esperados", {p.name for p in paths} == expected)
    metrics = {}
    for path in paths:
        print(f"Leyendo todos los píxeles: {path.name}", flush=True)
        try:
            metrics[path.name] = inspect(path)
        except Exception as exc:
            check(path.name, "auditoria_sin_excepcion", False, f"{type(exc).__name__}: {exc}")
    mineral = [v for k, v in metrics.items() if "equ_map" in k]
    check("minerales", "misma_malla_entre_4", len(mineral) == 4
          and all(v["geotransform"] == mineral[0]["geotransform"] for v in mineral))
    failed = sum(c["estado"] == "FAIL" for c in CHECKS)
    warnings = sum(c["estado"] == "WARN" for c in CHECKS)
    report = {"fecha_UTC": datetime.now(timezone.utc).isoformat(), "GDAL": gdal.VersionInfo(),
              "metodo": "Lectura completa por bloques. IMG por memmap independiente de GDAL. Sin estadísticas caché.",
              "tests": CHECKS, "fallos": failed, "avisos": warnings, "total_tests": len(CHECKS), "rasters": metrics}
    output = ROOT / "auditoria_tiffs" / "resultados.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"\n{len(CHECKS) - failed - warnings}/{len(CHECKS)} PASS; {failed} FAIL; {warnings} WARN. Informe: {output}")
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
