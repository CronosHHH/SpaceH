"""Comparación técnica con bloques espaciales y controles conocidos, sin etiquetas de análogos reales."""

from time import perf_counter

import numpy as np

from .metodos import IndiceAnalogos
from .normalizacion import Normalizacion


def dividir_bloques(tablas, semilla=42):
    """La celda de un bloque de 10° nunca aparece en dos particiones."""
    resultado = {}
    for i, planeta in enumerate(("tierra", "marte")):
        tabla = tablas[planeta]
        bloques = np.floor((tabla["latitud"] + 90)/10).astype(int)*36 + np.floor((tabla["longitud"]+180)/10).astype(int)
        unicos = np.unique(bloques)
        orden = np.random.default_rng(semilla+i).permutation(unicos)
        n = len(orden); a, b = int(.6*n), int(.8*n)
        grupos = (orden[:a], orden[a:b], orden[b:])
        resultado[planeta] = {nombre: np.isin(bloques, grupo) for nombre, grupo in
                              zip(("calibracion", "desarrollo", "prueba"), grupos)}
    return resultado


def _controles(tabla, mascara, escala, semilla, max_anclas=80):
    ids = np.flatnonzero(mascara & tabla["elegible"])
    if len(ids) < 8:
        raise ValueError("Menos de ocho candidatos en una partición; revisar filtros y bloques")
    rng = np.random.default_rng(semilla)
    ids = rng.choice(ids, size=min(max_anclas, len(ids)), replace=False)
    consultas, originales = [], []
    for ruido in (.01, .05):
        for _ in range(2):
            X = tabla["X"][ids] + rng.normal(size=(len(ids), 3))*escala*ruido
            X[:, 0] = np.clip(X[:, 0], 0, 1); X[:, 1:] = np.maximum(X[:, 1:], 0)
            consultas.append(X); originales.append(ids)
    return np.vstack(consultas), np.concatenate(originales)


def _hit(indice, queries, anchors, raw_referencia, k, motor, centros):
    _, ids = indice.buscar(queries, planeta="tierra", k=k, motor=motor, n_centroides=centros)
    # También se aceptan puntos con el mismo vector físico, si existen empates.
    iguales = np.isclose(indice.X[ids], raw_referencia[anchors, None, :], rtol=0, atol=1e-12).all(axis=2)
    return float(iguales.any(axis=1).mean())


def recall_con_empates(exactas, propuestas, tolerancia=1e-12):
    """Exige los vecinos interiores; solo permite intercambiar los de frontera.

    Cada fila contiene k distancias de candidatos distintos. Contar únicamente
    d <= d_k ocultaría vecinos estrictamente cercanos que no se recuperaron.
    """
    frontera = exactas[:, -1, None]
    obligatorios = (exactas < frontera-tolerancia).sum(axis=1)
    interiores = (propuestas < frontera-tolerancia).sum(axis=1)
    empatados = (np.abs(propuestas-frontera) <= tolerancia).sum(axis=1)
    aciertos = interiores + np.minimum(exactas.shape[1]-obligatorios, empatados)
    return float(np.mean(aciertos/exactas.shape[1]))


def _recall_y_tiempo(indice, queries, k, motor, centros):
    exactas, _ = indice.buscar(queries, k=k)
    propuesto, _ = indice.buscar(queries, k=k, motor=motor, n_centroides=centros)
    recall = recall_con_empates(exactas, propuesto)
    tiempos = []
    for _ in range(5):
        start = perf_counter(); indice.buscar(queries, k=k, motor=motor, n_centroides=centros)
        tiempos.append(1000*(perf_counter()-start)/len(queries))
    return recall, float(np.median(tiempos))


def comparar_metodos(tablas, k=10, pesos=None, semilla=42):
    particiones = dividir_bloques(tablas, semilla)
    tierra, marte = tablas["tierra"], tablas["marte"]
    ref_ids = np.flatnonzero(tierra["elegible"])
    X_ref = tierra["X"][ref_ids]
    X_cal = tierra["X"][tierra["elegible"] & particiones["tierra"]["calibracion"]]
    if len(X_ref) < 2*k or len(X_cal) < 10:
        raise ValueError("Demasiados pocos candidatos; configurar filtros explícitamente")
    escala = np.subtract(*np.percentile(tierra["X"][particiones["tierra"]["calibracion"]], [75,25], axis=0))
    consultas, anchors = _controles(tierra, particiones["tierra"]["desarrollo"], escala, semilla)
    rng = np.random.default_rng(semilla)
    mars_ids = np.flatnonzero(particiones["marte"]["desarrollo"])
    mars_queries = marte["X"][rng.choice(mars_ids, min(96, len(mars_ids)), replace=False)]
    filas, indices, normalizadores = [], {}, {}
    for modo in ("zscore", "percentiles"):
        norm = Normalizacion(modo).fit(tablas, particiones)
        indice = IndiceAnalogos(norm, pesos).fit(X_ref, X_cal, semilla=semilla)
        normalizadores[modo] = norm; indices[modo] = indice
        for motor, centros in (("knn", 0), ("clusters", 1), ("clusters", 2)):
            hit = _hit(indice, consultas, anchors, tierra["X"], k, motor, centros)
            recall, ms = _recall_y_tiempo(indice, mars_queries, k, motor, centros)
            grupo = "grupo" if centros == 1 else "grupos"
            filas.append({"metodo": f"{modo} + {motor}"+(f" ({centros} {grupo})" if centros else ""),
                          "modo": modo, "motor": motor, "centros": centros, "hit_dev": hit,
                          "recall_dev": recall, "ms_consulta": ms, "hit_test": None, "recall_test": None})
    seleccion = _seleccionar(filas)
    _evaluar_prueba(seleccion, indices[seleccion["modo"]], tablas, particiones, escala, k, semilla)
    return {"filas": filas, "seleccion": seleccion, "indices": indices,
            "normalizadores": normalizadores, "particiones": particiones, "referencia_ids": ref_ids,
            "k": k, "consultas_desarrollo": len(consultas), "anclas_ruido_iqr": [.01, .05],
            "criterio": "Mayor Hit@k de desarrollo; empate de hasta 2 puntos porcentuales favorece percentiles por interpretación relativa. Prefiltro solo si recall >= 0.99 y mejora >= 20% en latencia, sin perder más de 1 punto porcentual de Hit@k."}


def _seleccionar(filas):
    exactos = {r["modo"]:r for r in filas if r["motor"] == "knn"}
    modo = "percentiles" if exactos["percentiles"]["hit_dev"] >= exactos["zscore"]["hit_dev"]-.02 else "zscore"
    base = exactos[modo]
    admisibles = [r for r in filas if r["modo"] == modo and r["recall_dev"] >= .99
                  and r["hit_dev"] >= base["hit_dev"]-.01 and r["ms_consulta"] <= base["ms_consulta"]*.8]
    return min(admisibles, key=lambda r:r["ms_consulta"]) if admisibles else base


def _evaluar_prueba(fila, indice, tablas, particiones, escala, k, semilla):
    queries, anchors = _controles(tablas["tierra"], particiones["tierra"]["prueba"], escala, semilla+1)
    fila["hit_test"] = _hit(indice, queries, anchors, tablas["tierra"]["X"], k, fila["motor"], fila["centros"])
    ids = np.flatnonzero(particiones["marte"]["prueba"])
    rng = np.random.default_rng(semilla+1)
    mars = tablas["marte"]["X"][rng.choice(ids, min(96, len(ids)), replace=False)]
    fila["recall_test"], _ = _recall_y_tiempo(indice, mars, k, fila["motor"], fila["centros"])
    fila["consultas_prueba_controles"] = len(queries)
    fila["consultas_prueba_marte"] = len(mars)
    # Un control operativo falla cerrado; no se retocan hiperparámetros con prueba.
    fila["prefiltro_seguro_prueba"] = fila["recall_test"] >= .99


def buscar_analogos(comparacion, tablas, consulta, k=None):
    seleccion = comparacion["seleccion"]
    modo = seleccion["modo"]
    indice = comparacion["indices"][modo]
    motor = seleccion["motor"] if seleccion["prefiltro_seguro_prueba"] else "knn"
    dist, ids = indice.buscar(consulta["X"][None], k=k or comparacion["k"], motor=motor,
                            n_centroides=seleccion["centros"])
    # Comprobación de implementación, distinta de validación científica.
    if motor == "knn":
        directas, _ = indice.buscar(consulta["X"][None], k=k or comparacion["k"], motor="directa")
        if not np.allclose(dist, directas, rtol=1e-12, atol=1e-12):
            raise AssertionError("KNN y ordenación directa no coinciden")
    return comparacion["referencia_ids"][ids[0]], dist[0], motor
