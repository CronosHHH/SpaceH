"""Visualizaciones del prototipo: las funciones devuelven Figure y no escriben.

Las tres características se muestran siempre en orden: albedo, proxy solar
absorbido y relieve regional. Los gráficos distinguen datos físicos, escala
normalizada y coordenadas de cada planeta.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle


CARACTERISTICAS = ("Albedo", "Proxy solar absorbido", "Relieve regional")
UNIDADES = ("fracción [1]", "q_abs [W/m²]", "relieve [m]")
COLORES = {"tierra": "#2878a5", "marte": "#bd5837"}


def _matriz(values, columnas, nombre):
    array = np.asarray(values, dtype="float64")
    if array.ndim != 2 or array.shape[1] != columnas or not len(array):
        raise ValueError(f"{nombre}: se esperaba una matriz no vacía de {columnas} columnas")
    if not np.isfinite(array).all():
        raise ValueError(f"{nombre}: hay datos no finitos; aplicar primero el control de cobertura")
    return array


def _indices(values, total):
    indices = np.asarray(values, dtype="int64").reshape(-1)
    if not len(indices) or np.any(indices < 0) or np.any(indices >= total):
        raise ValueError("Los índices deben referirse a filas válidas de la tabla original")
    return indices


def normalizacion(tablas, normalizador):
    """Histogramas físicos y normalizados para cada característica y planeta."""
    modo = normalizador.modo
    if modo not in ("zscore", "percentiles"):
        raise ValueError("Normalización desconocida")
    fig, axes = plt.subplots(3, 2, figsize=(13, 10), constrained_layout=True)
    for planeta in ("tierra", "marte"):
        original = _matriz(tablas[planeta]["X"], 3, planeta)
        transformado = _matriz(normalizador.transform(planeta, original), 3, "normalizado")
        for columna, nombre in enumerate(CARACTERISTICAS):
            for lado, values in enumerate((original, transformado)):
                axes[columna, lado].hist(
                    values[:, columna], bins=35, density=True, histtype="step",
                    linewidth=1.7, color=COLORES[planeta], label=planeta.capitalize(),
                )
                axes[columna, lado].set_ylabel("Densidad")
                axes[columna, lado].grid(alpha=.18)
            axes[columna, 0].set(title=f"Entrada · {nombre}", xlabel=UNIDADES[columna])
            etiqueta = "Percentil marginal [0–1]" if modo == "percentiles" else "Valor estandarizado z [1]"
            axes[columna, 1].set(title=f"Salida · {nombre}", xlabel=etiqueta)
            if modo == "percentiles":
                axes[columna, 1].set_xlim(0, 1)
    axes[0, 0].legend()
    axes[0, 1].legend()
    fig.suptitle(
        f"Normalización: {modo}\nLa coincidencia de distribuciones marginales no demuestra equivalencia física",
        fontsize=13,
    )
    return fig


def ejemplo_knn(puntos, consulta, indices):
    """Ejemplo geométrico 2D con vecinos, segmentos y radio del vecino lejano."""
    puntos = _matriz(puntos, 2, "puntos")
    consulta = _matriz(np.asarray(consulta).reshape(1, -1), 2, "consulta")[0]
    indices = _indices(indices, len(puntos))
    vecinos = puntos[indices]
    radio = np.linalg.norm(vecinos - consulta, axis=1).max()
    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
    ax.scatter(*puntos.T, s=30, c="#91a9bb", label="Candidatos", zorder=2)
    ax.scatter(*vecinos.T, s=100, facecolors="none", edgecolors="#f18b26",
               linewidths=1.8, label=f"{len(indices)} vecinos seleccionados", zorder=3)
    for point in vecinos:
        ax.plot([consulta[0], point[0]], [consulta[1], point[1]], c="#f18b26", alpha=.65)
    ax.add_patch(Circle(consulta, radio, fill=False, linestyle="--", color="#bd5837",
                        label="Radio del vecino más lejano"))
    ax.scatter(*consulta, marker="*", s=200, color="#b62032", edgecolors="white",
               linewidths=.7, label="Consulta", zorder=4)
    ax.set(title="KNN: proximidad en un espacio didáctico de dos variables",
           xlabel="Característica normalizada 1", ylabel="Característica normalizada 2")
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale_view()
    ax.grid(alpha=.2)
    ax.legend(fontsize=8)
    return fig


def ejemplo_clusters(puntos, etiquetas, centros):
    """Partición 2D por KMeans; las cruces representan sus centroides."""
    puntos = _matriz(puntos, 2, "puntos")
    centros = _matriz(centros, 2, "centros")
    etiquetas = np.asarray(etiquetas, dtype="int64").reshape(-1)
    if len(etiquetas) != len(puntos) or np.any(etiquetas < 0) or np.any(etiquetas >= len(centros)):
        raise ValueError("Las etiquetas deben identificar uno de los centroides")
    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
    palette = plt.get_cmap("tab10")
    for grupo in np.unique(etiquetas):
        subset = puntos[etiquetas == grupo]
        ax.scatter(*subset.T, s=35, color=palette(grupo % 10), label=f"Grupo {grupo + 1}")
    ax.scatter(*centros.T, marker="X", s=180, c="black", edgecolors="white",
               linewidths=1, label="Centroides", zorder=3)
    ax.set(title="KMeans: agrupar por cercanía al centroide",
           xlabel="Característica normalizada 1", ylabel="Característica normalizada 2")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(alpha=.2)
    ax.legend(fontsize=8)
    return fig


def comparacion(rows):
    """Separa recuperación controlada, recall frente a búsqueda exacta y coste."""
    if not rows:
        raise ValueError("La comparación necesita resultados")
    nombres = [r["metodo"].replace(" + ", "\n+ ") for r in rows]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    for ax, metric, titulo in zip(axes[:2], ("hit", "recall"),
                                  ("Recuperación del positivo conocido", "Recall frente a búsqueda exacta")):
        for desplazamiento, split, color in ((-.18, "dev", "#2878a5"), (.18, "test", "#e78a36")):
            values = np.array([np.nan if r.get(f"{metric}_{split}") is None else r[f"{metric}_{split}"] for r in rows])
            finite = np.isfinite(values)
            if np.any((values[finite] < 0) | (values[finite] > 1)):
                raise ValueError("Las tasas de evaluación deben expresarse entre 0 y 1")
            ax.bar(x + desplazamiento, values, width=.34, label="Desarrollo" if split == "dev" else "Prueba", color=color)
            for posicion in x[~finite] + desplazamiento:
                ax.text(posicion, .02, "n/d", ha="center", fontsize=7)
        ax.set(title=titulo, ylabel="Fracción [0–1]", ylim=(0, 1.05))
        ax.legend(fontsize=8)
    tiempos = np.array([np.nan if r.get("ms_consulta") is None else r["ms_consulta"] for r in rows])
    axes[2].bar(x, tiempos, color="#557e69")
    for posicion in x[~np.isfinite(tiempos)]:
        axes[2].text(posicion, .03, "Sin medida", transform=axes[2].get_xaxis_transform(), ha="center", fontsize=8)
    axes[2].set(title="Tiempo de consulta", ylabel="Milisegundos por consulta")
    for ax in axes:
        ax.set_xticks(x, nombres, rotation=22, ha="right", fontsize=8)
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Banco de pruebas controlado: no constituye validación de análogos geológicos", fontsize=13)
    return fig


def mapa_candidatos(tabla_tierra, consulta, indices, distancias):
    """Mapa angular de candidatos terrestres y consulta marciana en ejes aparte."""
    lon = np.asarray(tabla_tierra["longitud"])
    lat = np.asarray(tabla_tierra["latitud"])
    indices = _indices(indices, len(lon))
    elegible = np.asarray(tabla_tierra["elegible"], dtype=bool)
    distancias = np.asarray(distancias, dtype="float64").reshape(-1)
    if len(lat) != len(lon) or len(elegible) != len(lon) or len(distancias) != len(indices):
        raise ValueError("Coordenadas, elegibilidad e índices no tienen el mismo tamaño")
    fig, axes = plt.subplots(1, 3, figsize=(17, 5),
                             gridspec_kw={"width_ratios": [2, 2, 1]}, constrained_layout=True)
    axes[0].scatter(lon[elegible], lat[elegible], s=3, c="#d7e2e8", label="Celdas terrestres elegibles")
    axes[0].scatter(lon[indices], lat[indices], c=distancias, cmap="viridis_r", s=25)
    points = axes[1].scatter(lon[indices], lat[indices], c=distancias, cmap="viridis_r",
                             s=65, edgecolors="black", linewidths=.5, zorder=3)
    for numero, index in enumerate(indices, 1):
        axes[1].annotate(str(numero), (lon[index], lat[index]), xytext=(5, 6),
                         textcoords="offset points", fontsize=8)
    fig.colorbar(points, ax=axes[1], label="Distancia adimensional", shrink=.8)
    axes[0].set(title="Tierra: distribución de candidatos", xlabel="Longitud terrestre (°)",
                ylabel="Latitud terrestre (°)", xlim=(-180, 180), ylim=(-90, 90))
    axes[0].legend(loc="lower left", fontsize=8)
    margen_lon = max(float(np.ptp(lon[indices])) * .15, 1)
    margen_lat = max(float(np.ptp(lat[indices])) * .2, 1)
    axes[1].set(title="Tierra: detalle del ranking", xlabel="Longitud terrestre (°)",
                ylabel="Latitud terrestre (°)",
                xlim=(lon[indices].min()-margen_lon, lon[indices].max()+margen_lon),
                ylim=(lat[indices].min()-margen_lat, lat[indices].max()+margen_lat))
    axes[2].scatter(consulta["longitud"], consulta["latitud"], marker="*", s=200, c="#bd5837", zorder=3)
    axes[2].set(title="Marte: celda consultada", xlabel="Longitud marciana (°)",
                ylabel="Latitud marciana (°)", xlim=(-180, 180), ylim=(-90, 90))
    axes[2].set_facecolor("#fcf2ed")
    for ax in axes:
        ax.grid(alpha=.25)
    fig.suptitle("Coordenadas de cada planeta en paneles separados; las celdas se comparan por sus variables")
    return fig


def perfiles(tabla_tierra, consulta, indices, normalizador):
    """Perfiles de los cinco primeros candidatos y de la consulta de Marte."""
    original = _matriz(tabla_tierra["X"], 3, "tabla terrestre")
    indices = _indices(indices, len(original))[:5]
    tierra = _matriz(normalizador.transform("tierra", original[indices]), 3, "candidatos normalizados")
    query = _matriz(np.asarray(consulta["X"]).reshape(1, -1), 3, "consulta")
    marte = _matriz(normalizador.transform("marte", query), 3, "consulta normalizada")[0]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for rank, values in enumerate(tierra, 1):
        ax.plot(x, values, marker="o", alpha=.8, label=f"Tierra · candidato {rank}")
    ax.plot(x, marte, marker="*", markersize=12, c="black", linewidth=2.5, label="Consulta en Marte", zorder=4)
    ax.set_xticks(x, CARACTERISTICAS)
    if normalizador.modo == "percentiles":
        ax.set(ylabel="Percentil marginal [0–1]", ylim=(-.03, 1.03))
    else:
        ax.set_ylabel("Valor estandarizado z [1]")
    ax.set_title("Perfiles relativos de los candidatos; coincidencia estadística, no equivalencia física")
    ax.grid(alpha=.2)
    ax.legend(fontsize=8, ncols=2)
    return fig
