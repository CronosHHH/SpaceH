"""Escalas relativas ajustadas solo con la población de calibración."""

import numpy as np
from sklearn.preprocessing import StandardScaler


CARACTERISTICAS = ("albedo", "q_abs", "relieve_m")


class PercentilEmpirico:
    """F(x) con rango medio de los empates; no añade ruido ni interpola clases."""

    def fit(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or len(X) < 2 or not np.isfinite(X).all():
            raise ValueError("Se necesita una matriz finita de calibración")
        self.columnas = [np.sort(col) for col in X.T]
        return self

    def transform(self, X):
        X = np.atleast_2d(np.asarray(X, dtype=float))
        if X.shape[1] != len(self.columnas) or not np.isfinite(X).all():
            raise ValueError("Dimensiones o valores incorrectos al normalizar")
        output = np.empty_like(X)
        for j, referencia in enumerate(self.columnas):
            izquierda = np.searchsorted(referencia, X[:, j], side="left")
            derecha = np.searchsorted(referencia, X[:, j], side="right")
            output[:, j] = (izquierda + derecha) / (2 * len(referencia))
        return output


class Normalizacion:
    """Una referencia independiente por planeta; filtros posteriores no la alteran."""

    def __init__(self, modo):
        if modo not in ("zscore", "percentiles"):
            raise ValueError("Modo admitido: zscore o percentiles")
        self.modo = modo
        self.modelos = {}
        self.limites = {}

    def fit(self, tablas, particiones):
        for planeta in ("tierra", "marte"):
            X = tablas[planeta]["X"][particiones[planeta]["calibracion"]]
            modelo = StandardScaler() if self.modo == "zscore" else PercentilEmpirico()
            self.modelos[planeta] = modelo.fit(X)
            self.limites[planeta] = (X.min(axis=0), X.max(axis=0))
        return self

    def transform(self, planeta, X):
        return self.modelos[planeta].transform(np.atleast_2d(X))

    def fuera_referencia(self, planeta, X):
        minimo, maximo = self.limites[planeta]
        X = np.atleast_2d(X)
        return (X < minimo) | (X > maximo)


def pesos_normalizados(pesos=None):
    pesos = np.ones(3) if pesos is None else np.asarray(pesos, dtype=float)
    if pesos.shape != (3,) or not np.isfinite(pesos).all() or np.any(pesos <= 0):
        raise ValueError("Definir tres pesos positivos y finitos")
    return pesos / pesos.sum()


def distancia_percentiles(consulta, candidatos, pesos=None):
    """RMS ponderada de posiciones 0–1; resultado adimensional, no probabilidad."""
    pesos = pesos_normalizados(pesos)
    return np.sqrt(np.sum((np.asarray(candidatos) - np.asarray(consulta)) ** 2 * pesos, axis=-1))
