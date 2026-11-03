"""Cálculos de la demo, independientes de la interfaz y del servidor."""

from math import asin, cos, isfinite, radians, sin, sqrt
from statistics import mean

from datos import LUGARES_TIERRA, MINERALES, MUESTRAS_LUNA


def distancia_lunar(a, b):
    """Devuelve la distancia en km entre coordenadas lunares en grados (haversine)."""
    diferencia_lat = radians(b["lat"] - a["lat"])
    diferencia_lon = radians(b["lon"] - a["lon"])
    h = (
        sin(diferencia_lat / 2) ** 2
        + cos(radians(a["lat"])) * cos(radians(b["lat"])) * sin(diferencia_lon / 2) ** 2
    )
    return 2 * 1737.4 * asin(sqrt(min(1, max(0, h))))


def perfil_medio(muestras):
    """Promedia temperaturas (°C) y porcentajes minerales de una lista no vacía."""
    return {
        "min": mean(muestra["min"] for muestra in muestras),
        "max": mean(muestra["max"] for muestra in muestras),
        "minerales": [
            mean(muestra["minerales"][i] for muestra in muestras)
            for i in range(len(MINERALES))
        ],
    }


def comparar(lugar, perfil, peso_temperatura, peso_minerales):
    """Añade similitudes y puntuación (0–100); requiere pesos ≥0 con suma >0."""
    diferencia_temperatura = (
        abs(lugar["min"] - perfil["min"]) + abs(lugar["max"] - perfil["max"])
    ) / 2
    diferencia_minerales = sum(
        abs(valor - perfil["minerales"][i])
        for i, valor in enumerate(lugar["minerales"])
    )
    temperatura = 100 * max(0, 1 - diferencia_temperatura / 200)
    composicion = 100 * (1 - diferencia_minerales / 200)
    puntuacion = (
        temperatura * peso_temperatura + composicion * peso_minerales
    ) / (peso_temperatura + peso_minerales)
    return {**lugar, "temperatura": temperatura, "composicion": composicion, "puntuacion": puntuacion}


def analizar_region(lat, lon, radio, peso_temperatura, peso_minerales):
    """Valida coordenadas, radio (km) y pesos; devuelve muestras, perfil y ranking."""
    limites = [
        ("La latitud", lat, -90, 90),
        ("La longitud", lon, -180, 180),
        ("El radio", radio, 1, 1000),
        ("El peso de temperatura", peso_temperatura, 0, 100),
        ("El peso de minerales", peso_minerales, 0, 100),
    ]
    for nombre, valor, inferior, superior in limites:
        if not isinstance(valor, (int, float)) or not isfinite(valor) or not inferior <= valor <= superior:
            raise ValueError(f"{nombre} debe ser un número entre {inferior} y {superior}.")
    if peso_temperatura + peso_minerales == 0:
        raise ValueError("Asigna un peso mayor que cero a alguna variable.")

    punto = {"lat": lat, "lon": lon}
    indices = [
        i for i, muestra in enumerate(MUESTRAS_LUNA)
        if distancia_lunar(punto, muestra) <= radio
    ]
    if not indices:
        return {"indices": [], "perfil": None, "rocas": [], "ranking": []}

    muestras = [MUESTRAS_LUNA[i] for i in indices]
    perfil = perfil_medio(muestras)
    # El diccionario elimina duplicados y conserva el orden de aparición.
    rocas = list(dict.fromkeys(muestra["roca"] for muestra in muestras))
    ranking = sorted(
        [comparar(lugar, perfil, peso_temperatura, peso_minerales) for lugar in LUGARES_TIERRA],
        key=lambda lugar: lugar["puntuacion"],
        reverse=True,
    )
    return {"indices": indices, "perfil": perfil, "rocas": rocas, "ranking": ranking}
