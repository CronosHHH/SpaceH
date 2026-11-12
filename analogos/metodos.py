"""Búsqueda exacta y prefiltro por KMeans con la misma distancia ponderada."""

from time import perf_counter

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

from .normalizacion import pesos_normalizados


class IndiceAnalogos:
    """El índice recuerda candidatos terrestres; no predice clases de análogos."""

    def __init__(self, normalizador, pesos=None):
        self.normalizador = normalizador
        self.escala = np.sqrt(pesos_normalizados(pesos))

    def fit(self, X, X_calibracion, opciones_clusters=(3, 5, 8), semilla=42):
        inicio = perf_counter()
        self.X = np.asarray(X)
        self.Z = self.normalizador.transform("tierra", X) * self.escala
        self.vecinos = NearestNeighbors(algorithm="kd_tree", metric="euclidean", n_jobs=1).fit(self.Z)
        Z_cal = self.normalizador.transform("tierra", X_calibracion) * self.escala
        self.evaluacion_clusters = []
        candidatos = []
        for k in opciones_clusters:
            if k >= len(Z_cal):
                continue
            modelo = KMeans(n_clusters=k, n_init=10, random_state=semilla).fit(Z_cal)
            score = silhouette_score(Z_cal, modelo.labels_, sample_size=min(500, len(Z_cal)), random_state=semilla)
            self.evaluacion_clusters.append({"k": k, "silhouette": float(score)})
            candidatos.append((score, modelo))
        if not candidatos:
            raise ValueError("No hay suficientes datos de calibración para agrupar")
        self.kmeans = max(candidatos, key=lambda pair: pair[0])[1]
        self.etiquetas = self.kmeans.predict(self.Z)
        self.grupos = {int(c): np.flatnonzero(self.etiquetas == c) for c in np.unique(self.etiquetas)}
        self.vecinos_grupo = {c: NearestNeighbors(algorithm="kd_tree").fit(self.Z[ids]) for c, ids in self.grupos.items()}
        self.segundos_ajuste = perf_counter() - inicio
        return self

    def _clusters(self, Z, k, n_centroides):
        distancias, indices = [], []
        for consulta in Z:
            orden = np.argsort(np.linalg.norm(self.kmeans.cluster_centers_ - consulta, axis=1))
            grupos = []
            disponibles = 0
            for grupo in orden:
                if int(grupo) not in self.grupos:
                    continue
                grupos.append(int(grupo))
                disponibles += len(self.grupos[int(grupo)])
                if len(grupos) >= n_centroides and disponibles >= k:
                    break
            dist, ids = [], []
            for grupo in grupos:
                n = min(k, len(self.grupos[grupo]))
                d, j = self.vecinos_grupo[grupo].kneighbors(consulta[None], n_neighbors=n)
                dist.extend(d[0]); ids.extend(self.grupos[grupo][j[0]])
            top = np.argsort(dist, kind="stable")[:k]
            distancias.append(np.asarray(dist)[top]); indices.append(np.asarray(ids)[top])
        return np.asarray(distancias), np.asarray(indices)

    def buscar(self, X, planeta="marte", k=10, motor="knn", n_centroides=1):
        if not 1 <= k <= len(self.X):
            raise ValueError("k fuera del número de candidatos")
        Z = self.normalizador.transform(planeta, X) * self.escala
        if motor == "knn":
            return self.vecinos.kneighbors(Z, n_neighbors=k)
        if motor == "clusters":
            return self._clusters(Z, k, n_centroides)
        if motor == "directa":
            dist = np.linalg.norm(Z[:, None, :] - self.Z[None, :, :], axis=2)
            ids = np.argsort(dist, axis=1, kind="stable")[:, :k]
            return np.take_along_axis(dist, ids, axis=1), ids
        raise ValueError("Motor desconocido")


def celda_marciana(tabla, latitud=-5.4, longitud=137.8):
    """Centro regional más próximo por distancia angular, no vecino ambiental."""
    if not np.isfinite([latitud, longitud]).all() or not -90 <= latitud <= 90:
        raise ValueError("Coordenadas no válidas")
    longitud = (longitud + 180) % 360 - 180
    lat = np.deg2rad(tabla["latitud"])
    dlat = lat - np.deg2rad(latitud)
    dlon = np.deg2rad(tabla["longitud"] - longitud)
    hav = np.sin(dlat / 2) ** 2 + np.cos(lat) * np.cos(np.deg2rad(latitud)) * np.sin(dlon / 2) ** 2
    hav = np.clip(hav, 0, 1)
    i = int(np.argmin(hav))
    desplazamiento = float(np.rad2deg(2*np.arcsin(np.sqrt(hav[i]))))
    if desplazamiento > 3:
        raise ValueError("No hay una celda marciana QC a menos de 3°; elegir otra consulta")
    return {"indice": i, "X": tabla["X"][i], "latitud": float(tabla["latitud"][i]),
            "longitud": float(tabla["longitud"][i]), "entrada_latitud": latitud,
            "entrada_longitud": longitud, "desplazamiento_angular_grados": desplazamiento}
