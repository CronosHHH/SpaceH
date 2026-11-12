"""Tablas legibles y exportación pequeña de resultados, sin guardar nuevos TIFF."""

import csv
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .normalizacion import pesos_normalizados


def guardar_figura(figura, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(path, dpi=140, metadata={
        "License": "CC-BY-SA-4.0", "Attribution": "NASA; NASA/JPL; ASU TES; ESA OMEGA; ICDC Universität Hamburg; OpenGeoHub; Natural Earth",
    })
    return str(path)


def tabla_markdown(registros, columnas=None):
    registros = list(registros)
    if not registros:
        return "Sin registros."
    columnas = columnas or list(registros[0])
    def texto(value):
        if value is None:
            return "—"
        if isinstance(value, (float, np.floating)):
            return f"{value:.5g}"
        return str(value).replace("|", "/").replace("\n", " ")
    filas = ["| " + " | ".join(columnas) + " |", "| " + " | ".join(["---"]*len(columnas)) + " |"]
    filas += ["| " + " | ".join(texto(r.get(c)) for c in columnas) + " |" for r in registros]
    return "\n".join(filas)


def tabla_candidatos(tabla, consulta, indices, distancias, normalizador, pesos=None):
    puntos = normalizador.transform("tierra", tabla["X"][indices])
    target = normalizador.transform("marte", consulta["X"])[0]
    costes = (puntos-target)**2*pesos_normalizados(pesos)
    if not np.allclose(np.sqrt(costes.sum(axis=1)), distancias):
        raise AssertionError("Las contribuciones no reproducen la distancia reportada")
    filas = []
    for rank, (i, d, terms) in enumerate(zip(indices, distancias, costes), 1):
        contexto = tabla["variables"]
        filas.append({
            "rango": rank, "latitud": float(tabla["latitud"][i]), "longitud": float(tabla["longitud"][i]),
            "distancia": float(d), "albedo": float(contexto["albedo"][i]),
            "q_abs_W_m2": float(contexto["q_abs"][i]), "relieve_m": float(contexto["relieve_m"][i]),
            "vegetacion": float(contexto["vegetacion"][i]), "agua": float(contexto["agua"][i]),
            "ciudades": float(contexto["ciudades"][i]), "elevacion_m_contexto": float(contexto["elevacion"][i]),
            "ghi_W_m2_contexto": float(contexto["ghi"][i]),
            "coste_cuadrado_albedo": float(terms[0]), "coste_cuadrado_q_abs": float(terms[1]),
            "coste_cuadrado_relieve": float(terms[2]),
        })
    return filas


def _json_simple(value):
    if isinstance(value, dict):
        return {str(k): _json_simple(v) for k,v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_simple(x) for x in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def guardar_resultados(carpeta, filas, comparacion, tablas, consulta, procedencia,
                       configuracion, motor_final, comprobaciones):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    with (carpeta / "candidatos.csv").open("w", newline="", encoding="utf8") as output:
        writer = csv.DictWriter(output, fieldnames=list(filas[0]))
        writer.writeheader(); writer.writerows(filas)
    particiones = {p: {nombre: int(mask.sum()) for nombre, mask in sets.items()}
                   for p, sets in comparacion["particiones"].items()}
    reporte = {
        "objetivo": "Consulta marciana → candidatos terrestres; similitud regional relativa",
        "validacion_fisica_de_analogos": False,
        "alcance_validacion": "Recuperación de positivos conocidos bajo perturbaciones y fidelidad de búsqueda; no etiquetas geológicas",
        "configuracion": configuracion, "procedencia": procedencia, "consulta": consulta,
        "versiones": {package: version(package) for package in
                      ("numpy", "rasterio", "matplotlib", "scikit-learn", "scipy")},
        "comprobaciones": comprobaciones,
        "referencias": {p: {"qc": t["n_referencia"], "elegibles": t["n_elegibles"],
                            "filtros": t["resumen_filtros"]} for p,t in tablas.items()},
        "particiones": particiones, "criterio": comparacion["criterio"],
        "seleccion": comparacion["seleccion"], "comparacion": comparacion["filas"],
        "busqueda_aplicada": {"motor": motor_final, "modo": comparacion["seleccion"]["modo"],
                              "fallback": motor_final != comparacion["seleccion"]["motor"]},
        "clusters_calibracion": {modo: idx.evaluacion_clusters for modo,idx in comparacion["indices"].items()},
        "ajuste_segundos": {modo: idx.segundos_ajuste for modo,idx in comparacion["indices"].items()},
        "k": comparacion["k"], "niveles_ruido_fraccion_iqr": comparacion["anclas_ruido_iqr"],
        "consultas_desarrollo_controles": comparacion["consultas_desarrollo"],
        "candidatos": filas, "licencia": "CC-BY-SA-4.0",
        "advertencia": "Distancia no es probabilidad, equivalencia física, seguridad de aterrizaje ni aptitud para misiones",
    }
    (carpeta / "informe.json").write_text(json.dumps(_json_simple(reporte), ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    return {"ranking": str(carpeta/"candidatos.csv"), "informe": str(carpeta/"informe.json")}
