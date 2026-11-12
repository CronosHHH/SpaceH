"""Controles numéricos del flujo: unidades, empates, NoData y separación espacial."""

import numpy as np
from sklearn.neighbors import NearestNeighbors

from .armonizacion import armonizar
from .evaluacion import recall_con_empates
from .normalizacion import PercentilEmpirico, distancia_percentiles
from .variables import comprobaciones_unidades, construir_tablas


def verificar(armonizados, tablas, comparacion, brutos):
    ejemplos = comprobaciones_unidades()
    modelo = PercentilEmpirico().fit(np.array([[10.], [10.], [20.], [40.]]))
    assert np.allclose(modelo.transform([[10], [20], [40], [0], [50]]).ravel(), [.25,.625,.875,0,1])
    assert np.isclose(distancia_percentiles([.2,.7,.3], [[.3,.6,.4]])[0], .1)
    X = np.array([[.1,.2,.3], [.8,.7,.9], [.4,.6,.2], [.1,.2,.3]])
    query = np.array([.2,.3,.4]); pesos = np.array([.2,.3,.5])
    directa = np.sort(distancia_percentiles(query, X, pesos))
    dist, _ = NearestNeighbors(n_neighbors=4).fit(X*np.sqrt(pesos)).kneighbors(query[None]*np.sqrt(pesos))
    assert np.allclose(dist[0], directa)
    assert recall_con_empates(np.array([[0., 1.]]), np.array([[1., 1.]])) == .5
    assert recall_con_empates(np.array([[0., 1.]]), np.array([[0., 1.]])) == 1
    for conjuntos in comparacion["particiones"].values():
        assert np.all(np.sum(list(conjuntos.values()), axis=0) == 1)
    base = construir_tablas(armonizados)
    alteradas = construir_tablas(armonizados, max_vegetacion=.1)
    assert np.array_equal(alteradas["tierra"]["X"], base["tierra"]["X"])
    # Fixture de ceros conocidos y ausencias: reproyección en ambos planetas.
    fixture = {"procedencia": {}}
    for p in ("tierra", "marte"):
        array = np.zeros((180,360)); array[:30] = np.nan
        fixture[p] = {"variables": {"ghi": array}, "coberturas": {},
                      "unidades": {"ghi": "W/m²"}, "geometria": brutos[p]["geometria"]}
    agregado = armonizar(fixture)
    for p in ("tierra", "marte"):
        array = agregado[p]["variables"]["ghi"]; coverage = agregado[p]["coberturas"]["ghi"]
        assert np.all(array[np.isfinite(array)] == 0)
        assert np.all(np.isnan(array[coverage == 0]))
    return {"unidades_y_ejemplos": ejemplos, "percentiles_con_empates": True,
            "distancia_percentiles_independiente": True, "knn_igual_a_formula_ponderada": True,
            "recall_no_oculta_vecinos_interiores": True,
            "particiones_disjuntas": True, "referencias_independientes_de_filtros": True,
            "ceros_validos_y_nodata_conservados": True}
