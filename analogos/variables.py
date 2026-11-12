"""Variables físicas derivadas y tablas separadas de referencia y candidatos."""

import numpy as np
from sklearn.neighbors import BallTree


FEATURES = ("albedo", "q_abs", "relieve_m")
UNIDADES_FEATURES = ("1", "W/m²", "m")


def _dispersion(values):
    return float(np.std(values, ddof=0))


def _relieve(planeta, radio_local_m, cobertura_local_min):
    inside = planeta["inside"]
    flat = np.flatnonzero(inside)
    coordinates = np.deg2rad(np.column_stack([
        planeta["latitudes"].ravel()[flat], planeta["longitudes"].ravel()[flat]]))
    tree = BallTree(coordinates, metric="haversine")
    neighborhoods = tree.query_radius(coordinates, r=radio_local_m / planeta["radio_m"])
    elevation = planeta["variables"]["elevacion"].ravel()[flat]
    coverage = planeta["coberturas"]["elevacion"].ravel()[flat]
    full_cells = planeta.get("inside_completo", inside).ravel()[flat]
    good = np.isfinite(elevation) & (coverage >= .9) & full_cells
    relief = np.full(inside.shape, np.nan)
    support = np.zeros(inside.shape)
    for index, neighbors in enumerate(neighborhoods):
        available = neighbors[good[neighbors]]
        fraction = len(available) / len(neighbors)
        support.ravel()[flat[index]] = fraction
        if good[index] and len(available) >= 5 and fraction >= cobertura_local_min:
            relief.ravel()[flat[index]] = _dispersion(elevation[available])
    return relief, support


def agregar_derivadas(armonizados, radio_local_m=300000, cobertura_local_min=.8):
    """Añade Q absorbido, energía equivalente de 24 h y relieve regional.

    Q=(1−A)G [W/m²]; E24=Q×24/1000 [kWh/m² por intervalo de 24 h]. E24 no
    representa energía por sol marciano. El relieve es σ poblacional de medias
    DEM en un disco geodésico común; no es pendiente ni rugosidad de aterrizaje.
    """
    if radio_local_m <= 0 or not 0 < cobertura_local_min <= 1:
        raise ValueError("Radio y cobertura local deben ser positivos y cobertura ≤ 1")
    for nombre in ("tierra", "marte"):
        planet = armonizados[nombre]
        variables, coverage = planet["variables"], planet["coberturas"]
        variables["q_abs"] = (1 - variables["albedo"]) * variables["ghi"]
        variables["energia_24h"] = variables["q_abs"] * 24 / 1000
        coverage["q_abs"] = np.minimum(coverage["albedo"], coverage["ghi"])
        coverage["energia_24h"] = coverage["q_abs"].copy()
        variables["relieve_m"], coverage["relieve"] = _relieve(planet, radio_local_m, cobertura_local_min)
        planet["unidades"].update(q_abs="W/m²", energia_24h="kWh/m² por 24 h", relieve_m="m")
        planet["derivadas"] = {"radio_relieve_m": float(radio_local_m),
                               "cobertura_local_min": cobertura_local_min,
                               "relieve": "Desviación típica poblacional; celdas de igual área; vecinos haversine",
                               "q_abs": "Proxy de medias agregadas (1−A_media)G_media; aproxima albedo como reflectancia efectiva, no una media observada de absorción",
                               "energia_24h": "Diagnóstico redundante con Q; no se usa como característica adicional"}
    return armonizados


def _referencia(planeta, min_cobertura):
    variables, coverage = planeta["variables"], planeta["coberturas"]
    good = planeta.get("inside_completo", planeta["inside"]).copy()
    for nombre in FEATURES:
        good &= np.isfinite(variables[nombre])
    for nombre in ("elevacion", "ghi", "albedo"):
        good &= coverage[nombre] >= min_cobertura
    good &= coverage["relieve"] >= .8
    return good


def _elegibilidad(planeta, indices, max_vegetacion, max_agua, max_ciudades,
                  min_cobertura, min_cobertura_vegetacion):
    variables, coverages = planeta["variables"], planeta["coberturas"]
    conditions = {
        "Vegetación conocida y baja": np.isfinite(variables["vegetacion"]) & (variables["vegetacion"] <= max_vegetacion),
        "Agua conocida y baja": np.isfinite(variables["agua"]) & (variables["agua"] <= max_agua),
        "Ciudades conocidas y bajas": np.isfinite(variables["ciudades"]) & (variables["ciudades"] <= max_ciudades),
        "Cobertura de clasificación suficiente": coverages["clasificacion"] >= min_cobertura,
        "Cobertura de vegetación suficiente": coverages["vegetacion"] >= min_cobertura_vegetacion,
    }
    eligible = np.ones(len(indices), dtype=bool)
    counts = [{"filtro": "Referencia física antes de filtros de candidatos", "restantes": len(indices)}]
    for label, mask in conditions.items():
        eligible &= mask.ravel()[indices]
        counts.append({"filtro": label, "restantes": int(eligible.sum())})
    return eligible, counts


def construir_tablas(armonizados, max_vegetacion=.2, max_agua=.05, max_ciudades=.02,
                     min_cobertura=.9, min_cobertura_vegetacion=.75):
    """Devuelve referencias QC antes de filtrar candidatos; X tiene tres columnas.

    Cada tabla contiene X, índices planos, coordenadas, contexto y ``elegible``.
    Vegetación/agua/ciudades son restricciones terrestres; no se inventan
    equivalentes marcianos ni se añaden a la distancia entre planetas.
    """
    limits = (max_vegetacion, max_agua, max_ciudades, min_cobertura, min_cobertura_vegetacion)
    if any(not np.isfinite(x) or not 0 <= x <= 1 for x in limits):
        raise ValueError("Los umbrales de fracciones deben estar en 0–1")
    tables = {}
    for name in ("tierra", "marte"):
        planet = armonizados[name]
        indices = np.flatnonzero(_referencia(planet, min_cobertura))
        table = {"X": np.column_stack([planet["variables"][key].ravel()[indices] for key in FEATURES]),
                 "indices": indices, "latitud": planet["latitudes"].ravel()[indices],
                 "longitud": planet["longitudes"].ravel()[indices],
                 "variables": {key: array.ravel()[indices] for key, array in planet["variables"].items()},
                 "features": FEATURES, "unidades_features": UNIDADES_FEATURES,
                 "forma_mapa": tuple(planet["inside"].shape)}
        if name == "tierra":
            eligible, counts = _elegibilidad(planet, indices, *limits[:3], *limits[3:])
        else:
            eligible = np.ones(len(indices), dtype=bool)
            counts = [{"filtro": "Referencia marciana QC", "restantes": len(indices)}]
        table.update(elegible=eligible, resumen_filtros=counts,
                     n_referencia=len(indices), n_elegibles=int(eligible.sum()))
        tables[name] = table
    return tables


def comprobaciones_unidades():
    """Ejemplos numéricos y propiedades que comprueban las transformaciones."""
    albedo, ghi = .25, 200.0
    q = (1 - albedo) * ghi
    energy = q * 24 / 1000
    heights = np.array([100, 200, 300, 400, 500], dtype="float64")
    assert np.isclose(q, 150) and np.isclose(energy, 3.6)
    assert np.isclose(_dispersion(heights), _dispersion(heights + 8000))
    return {"albedo_entrada_1": albedo, "ghi_entrada_W_m2": ghi,
            "q_salida_W_m2": q, "energia_salida_kWh_m2_por_24h": energy,
            "relieve_ejemplo_m": _dispersion(heights), "invariante_a_offset_vertical": True,
            "unidades": "(1)×W/m²=W/m²; W/m²×h/1000=kWh/m²; σ(elevación[m])=m"}
