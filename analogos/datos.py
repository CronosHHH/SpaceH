"""Carga verificada de los resúmenes Tierra–Marte, sin descargar mapas grandes.

Las matrices conservan sus unidades físicas y NoData como NaN. Igualar la
cuadrícula angular no convierte las observaciones de ambos planetas en medidas
equivalentes. Las diferencias se explicitan en ``fuentes.md``.
"""

from pathlib import Path
import hashlib
import importlib.util
import json

from huggingface_hub import HfApi, hf_hub_url
import numpy as np
import rasterio as rio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin


REPO = "Renato-R-V/hspace-datasets"
FORMA = (180, 360)
TRANSFORMACION = from_origin(-180, 90, 1, 1)
MAX_ARCHIVO = 16 * 1024 * 1024
ARCHIVOS = {
    "tierra": ("tierra/tierra_1grado.tif", "tierra/coberturas_tierra_1grado.tif"),
    "marte": ("marte/prototipo_alineado/marte_1grado.tif",
              "marte/prototipo_alineado/cobertura_minerales_1grado.tif"),
}
BANDAS = {
    "tierra": ("Elevación NASADEM", "GHI terrestre", "Albedo terrestre",
               "Fracción ciudades", "Fracción agua", "Cobertura vegetal"),
    "marte": ("Elevación MOLA", "GHI modelado", "Albedo TES", "Olivino OSP1",
              "Olivino OSP2", "Olivino OSP3", "Piroxeno BD2000"),
}
CLAVES = {
    "tierra": ("elevacion", "ghi", "albedo", "ciudades", "agua", "vegetacion"),
    "marte": ("elevacion", "ghi", "albedo", "osp1", "osp2", "osp3", "piroxeno"),
}
COBERTURAS = {
    "tierra": ("elevacion", "clasificacion", "vegetacion"),
    "marte": ("osp1", "osp2", "osp3", "piroxeno"),
}
NOMBRES_COBERTURA = {
    "tierra": ("Cobertura NASADEM", "Cobertura clasificada", "Cobertura de datos de vegetación"),
    "marte": ("Olivino OSP1", "Olivino OSP2", "Olivino OSP3", "Piroxeno BD2000"),
}


def _descargador(raiz):
    """Reutiliza el lector autenticado, acotado y seguro del prototipo terrestre."""
    path = raiz / "tierra" / "prototipo_analogos.py"
    spec = importlib.util.spec_from_file_location("_lector_tierra_analogos", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.descargar_memoria


def _leer_archivo(path, info, revision, descargar, sha256_esperado=None):
    if info.size <= 0 or info.size > MAX_ARCHIVO:
        raise ValueError(f"{path}: solo se permiten resúmenes de hasta 16 MB")
    url = hf_hub_url(REPO, path, repo_type="dataset", revision=revision)
    if not info.lfs:
        url = url.replace("/resolve/", "/raw/", 1)
    raw = descargar(url, limite=info.size)
    if len(raw) != info.size:
        raise ValueError(f"{path}: tamaño distinto al de la revisión remota")
    sha256 = hashlib.sha256(raw).hexdigest()
    if info.lfs:
        if sha256 != info.lfs.sha256:
            raise ValueError(f"{path}: SHA256 LFS no coincide")
    else:
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != info.blob_id:
            raise ValueError(f"{path}: identificador Git no coincide")
    if sha256_esperado is not None and sha256 != sha256_esperado:
        raise ValueError(f"{path}: SHA256 distinto al catálogo científico")
    return raw, {"archivo": path, "bytes": len(raw), "sha256": sha256,
                 "revision": revision, "url": url, "hash_remoto_verificado": True}


def _leer_raster(raw, planeta, nombres):
    with MemoryFile(raw) as memory, memory.open() as source:
        if (source.shape != FORMA or source.count != len(nombres)
                or source.transform != TRANSFORMACION or source.descriptions != nombres
                or source.nodata is None or not np.isnan(source.nodata)
                or any(dtype != "float32" for dtype in source.dtypes)):
            raise ValueError(f"{planeta}: bandas, geometría o NoData del resumen inesperados")
        if planeta == "tierra":
            crs_correcto = source.crs is not None and source.crs.to_epsg() == 4326
        else:
            esperado = rio.crs.CRS.from_string("+proj=longlat +R=3396190 +no_defs")
            crs_correcto = source.crs is not None and source.crs.to_dict() == esperado.to_dict()
        if not crs_correcto:
            raise ValueError(f"{planeta}: el CRS ya no representa el planeta esperado")
        arrays = source.read(masked=True).astype("float64").filled(np.nan)
        if np.isinf(arrays).any():
            raise ValueError(f"{planeta}: hay infinitos no enmascarados")
        geometria = {"forma": list(FORMA), "crs": source.crs.to_wkt(),
                     "geotransformacion": list(source.transform.to_gdal()),
                     "resolucion_grados": 1, "limites": list(source.bounds)}
        etiquetas = [source.tags(i) for i in range(1, source.count + 1)]
    return arrays, geometria, etiquetas


def _validar_valores(planeta):
    variables, coberturas = planeta["variables"], planeta["coberturas"]
    for nombre, array in variables.items():
        good = np.isfinite(array)
        if not good.any():
            raise ValueError(f"La variable {nombre} no contiene datos")
        if nombre in ("albedo", "ciudades", "agua", "vegetacion"):
            if np.any((array[good] < 0) | (array[good] > 1)):
                raise ValueError(f"{nombre}: fracción fuera de 0–1")
        if nombre == "ghi" and np.any(array[good] < 0):
            raise ValueError("GHI negativo")
    for nombre, array in coberturas.items():
        if not np.isfinite(array).all() or np.any((array < 0) | (array > 1)):
            raise ValueError(f"Cobertura {nombre}: debe estar definida entre 0 y 1")
    if "vegetacion" in variables:
        for variable, coverage in (("elevacion", "elevacion"), ("ciudades", "clasificacion"),
                                   ("agua", "clasificacion"), ("vegetacion", "vegetacion")):
            if not np.array_equal(np.isfinite(variables[variable]), coberturas[coverage] > 0):
                raise ValueError(f"{variable}: NoData no coincide con su cobertura")
    else:
        for variable in ("osp1", "osp2", "osp3", "piroxeno"):
            if not np.array_equal(np.isfinite(variables[variable]), coberturas[variable] > 0):
                raise ValueError(f"{variable}: NoData no coincide con la cobertura mineral")


def cargar_datos(raiz, revision=None):
    """Devuelve variables, coberturas y procedencia de una única revisión de HF.

    Estructura: ``datos['tierra']['variables']['albedo']`` es una matriz
    Float64 de 180 × 360 con NaN para desconocidos. ``coberturas`` usa los
    nombres elevacion/clasificacion/vegetacion en Tierra y los minerales en
    Marte. No se crean TIFF ni entradas de caché de datos.
    """
    raiz = Path(raiz).resolve()
    descargar = _descargador(raiz)
    api = HfApi()
    revision = revision or api.repo_info(REPO, repo_type="dataset").sha
    paths = ["tierra/catalogo.json"] + [p for pair in ARCHIVOS.values() for p in pair]
    infos = {info.path: info for info in api.get_paths_info(REPO, paths, repo_type="dataset", revision=revision)}
    if set(infos) != set(paths):
        raise ValueError("La revisión remota no contiene todos los resúmenes necesarios")
    raw, catalog_info = _leer_archivo(paths[0], infos[paths[0]], revision, descargar)
    catalogo = json.loads(raw)
    if catalogo.get("dataset") != REPO:
        raise ValueError("El catálogo terrestre pertenece a otro dataset")
    result = {}
    archivos = [catalog_info]
    for nombre in ("tierra", "marte"):
        matrices = []
        for index, path in enumerate(ARCHIVOS[nombre]):
            record = catalogo["productos"].get(Path(path).name) if nombre == "tierra" else None
            expected = record["sha256"] if record is not None else None
            raw, provenance = _leer_archivo(path, infos[path], revision, descargar, expected)
            descriptions = BANDAS[nombre] if index == 0 else NOMBRES_COBERTURA[nombre]
            data, geometry, tags = _leer_raster(raw, nombre, descriptions)
            matrices.append(data)
            provenance["geometria"] = geometry
            provenance["bandas"] = [{"nombre": label, "etiquetas": tag} for label, tag in zip(descriptions, tags)]
            archivos.append(provenance)
            if index == 0:
                if tags[0].get("units") != "m" or tags[1].get("units") not in ("W/m^2", "W/m²"):
                    raise ValueError(f"{nombre}: unidades de elevación o GHI inesperadas")
                if nombre == "tierra" and tags[5].get("quantity") != "vegetated_surface_fraction":
                    raise ValueError("La sexta banda terrestre no es cobertura vegetal física")
                main_geometry = geometry
        units = {key: ("m" if key == "elevacion" else "W/m²" if key == "ghi" else "1")
                 for key in CLAVES[nombre]}
        result[nombre] = {
            "variables": dict(zip(CLAVES[nombre], matrices[0])),
            "coberturas": dict(zip(COBERTURAS[nombre], matrices[1])),
            "unidades": units, "geometria": main_geometry,
            "latitudes": 89.5 - np.arange(180), "longitudes": -179.5 + np.arange(360),
        }
        _validar_valores(result[nombre])
    result["procedencia"] = {
        "dataset": REPO, "revision": revision, "archivos": archivos,
        "bytes_descargados": sum(p["bytes"] for p in archivos),
        "licencia_resultados_combinados": "CC-BY-SA-4.0",
        "nota": "Misma malla angular; CRS, distancia física, época y definiciones radiativas diferentes por planeta",
    }
    return result


def tabla_variables():
    """Definiciones breves de entradas físicas y salidas del cargador."""
    registros = []
    fuentes = tabla_fuentes()
    indices = {"tierra": (0, 1, 1, 2, 2, 3), "marte": (4, 5, 6, 7, 7, 7, 7)}
    definiciones = {
        "elevacion": ("Elevación", "Altura sobre la referencia vertical del planeta; no nivel absoluto común"),
        "ghi": ("GHI", "Irradiancia solar descendente media sobre un plano horizontal"),
        "albedo": ("Albedo", "Fracción radiativa reflejada según la definición del producto"),
        "ciudades": ("Fracción de ciudades", "Proporción de píxeles IGBP urbanos entre los clasificados"),
        "agua": ("Fracción de agua", "Proporción de píxeles de agua entre los clasificados, incluido océano suplementario"),
        "vegetacion": ("Cobertura vegetal", "Fracción superficial estimada por MOD44B sobre recuperaciones válidas"),
        "osp1": ("Olivino OSP1", "Parámetro espectral OMEGA; no porcentaje de olivino"),
        "osp2": ("Olivino OSP2", "Segundo parámetro espectral OMEGA; no abundancia porcentual"),
        "osp3": ("Olivino OSP3", "Tercer parámetro espectral OMEGA; definición distinta de OSP1/OSP2"),
        "piroxeno": ("Piroxeno BD2000", "Parámetro de absorción espectral OMEGA; no porcentaje de piroxeno"),
    }
    for planet in ("tierra", "marte"):
        for index, key in enumerate(CLAVES[planet]):
            label, meaning = definiciones[key]
            unit = "m" if key == "elevacion" else "W/m²" if key == "ghi" else "1"
            fuente = fuentes[indices[planet][index]]
            registros.append({"planeta": planet, "variable": key, "nombre": label,
                              "unidad_entrada": unit, "unidad_salida": unit,
                              "significado": meaning, "salida": "180×360; Float64; NaN desconocido",
                              "dataset": fuente["dataset"], "fuente_url": fuente["fuente_url"],
                              "resolucion_origen": fuente["resolucion_origen"], "periodo": fuente["periodo"],
                              "transformacion_previa": fuente["transformacion"], "cobertura": fuente["cobertura"]})
    return registros


def tabla_fuentes():
    """Dataset original → transformación aplicada antes del prototipo conjunto."""
    registros = [
        {"planeta": "Tierra", "dataset": "NASADEM HGT.001", "entrada": "Elevación, m EGM96; 1″ (~30 m); SRTM 2000",
         "transformacion": "Media remota a 15″, redondeo Int16; media válida y cobertura de 240×240 celdas a 1°",
         "salida": "elevacion [m] y cobertura de datos [1]", "fuente_url": "https://www.earthdata.nasa.gov/data/catalog/lpcloud-nasadem-hgt-001"},
        {"planeta": "Tierra", "dataset": "NASA POWER", "entrada": "GHI [W/m²] y albedo [1]; nativos 1°; climatología 2001–2025",
         "transformacion": "Exportación numérica anual month=13; sin cambio de unidades; relleno a NaN",
         "salida": "ghi [W/m²], albedo [1]", "fuente_url": "https://power.larc.nasa.gov/docs/services/arcgis/"},
        {"planeta": "Tierra", "dataset": "MCD12Q1.061 + Natural Earth", "entrada": "Clases IGBP 2021; mosaico ~15″; océano cartográfico 1:10M",
         "transformacion": "Vecino nativo a malla 15″; clase 13=urbano,17=agua; océano solo en huecos; conteos/validados a 1°",
         "salida": "ciudades, agua y cobertura clasificada [1]", "fuente_url": "https://zenodo.org/records/8367523"},
        {"planeta": "Tierra", "dataset": "MOD44B.061 / ICDC", "entrada": "No vegetado [%]; CMG 0,5°; ciclo 2021-03-05 a 2022-03-04",
         "transformacion": "vegetacion=(100−no vegetado)/100; fill 127→NaN; media de celdas válidas 2×2 a 1°",
         "salida": "vegetacion [1], cobertura de celdas CMG [1]", "fuente_url": "https://www.geo.uni-hamburg.de/en/service/icdc/data/land/modis-vcf-forest.html"},
        {"planeta": "Marte", "dataset": "MGS MOLA", "entrada": "Altura [m] sobre el areoide; ~463 m, 128 píxeles/grado",
         "transformacion": "Reproyección al CRS esférico marciano y media válida a 1°; se conserva advertencia de bordes",
         "salida": "elevacion [m]", "fuente_url": "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html"},
        {"planeta": "Marte", "dataset": "Generador GHI del proyecto", "entrada": "Modelo esférico: S = 590 W/m², transmisión 0,75, oblicuidad 25,19°, Ls = 18,9°",
         "transformacion": "Media diaria analítica; malla nativa 1° preservada; latitudes interpretadas como planetocéntricas",
         "salida": "ghi [W/m²]; modelo de una estación, no media anual", "fuente_url": "../marte/origen_ds_gui_Y_albeolo/generar_ghi.py"},
        {"planeta": "Marte", "dataset": "MGS TES / ASU", "entrada": "VICAR albedo Lambert bolométrico [1], 8 píxeles/grado",
         "transformacion": "Rotación de 1.440 columnas a −180..180; alfa PNG solo como NoData; media válida 8 × 8 a 1°",
         "salida": "albedo [1]; rango fuente≈0,081–0,321", "fuente_url": "https://www.mars.asu.edu/data/tes_albedo/"},
        {"planeta": "Marte", "dataset": "Mars Express OMEGA", "entrada": "PDS IMG entero de 16 bits; índices OSP1/2/3 y BD2000; ~40 píxeles/grado",
         "transformacion": "IMG×SCALING_FACTOR+OFFSET; corrección de posición sin cambiar valores; media de detecciones y cobertura a 1°",
         "salida": "osp1/osp2/osp3/piroxeno [1] y coberturas [1]", "fuente_url": "https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/"},
    ]
    detalles = [
        ("1″ → 15″ → 1°", "Principalmente febrero de 2000", "Huella NASADEM; 14.520 celdas de 1°; polos sin datos"),
        ("1° nativo", "Climatología anual 2001–2025", "Global; los ceros de GHI son válidos"),
        ("Mosaico ≈15″ → 1°", "IGBP 2021; Natural Earth versión fijada en el generador", "Clasificación conocida y cobertura; huecos terrestres conservados"),
        ("CMG 0,5° → 1°", "2021-03-05 a 2022-03-04", "Recuperaciones MOD44B válidas; océano/hielo no estimado como NaN"),
        ("128 píxeles/grado → 1°", "Mosaico MGS; sin época única declarada en el resumen", "Global; advertencia previa de bordes conservada"),
        ("1° nativo", "Ls = 18,9°; media de un sol; sin fecha terrestre", "Global; cero modelado durante noche polar"),
        ("8 píxeles/grado → 1°", "Mosaico MGS/TES; sin época única declarada en el resumen", "63.360 celdas de 1° válidas; polos desconocidos"),
        ("40 píxeles/grado → 1°", "Mosaicos Mars Express; sin época única declarada en el resumen", "Detecciones parciales: medias condicionadas a datos y cobertura separada"),
    ]
    for row, (resolucion, periodo, cobertura) in zip(registros, detalles):
        row.update(resolucion_origen=resolucion, periodo=periodo, cobertura=cobertura)
    return registros
