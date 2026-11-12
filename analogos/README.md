# Prototipo conjunto de análogos Tierra–Marte

Abrir [AnalogosEnTierraDeMarte.ipynb](../AnalogosEnTierraDeMarte.ipynb) y ejecutar
sus celdas en orden con `marte/.venv/bin/python`. Es el punto de entrada: muestra
fuentes, armonización, fórmulas, unidades, normalización, ejemplos visuales de
KNN y KMeans, comparación, candidatos terrestres y el anexo de Mahalanobis.

```bash
marte/.venv/bin/python -m pip install -r analogos/requirements.txt
```

Los cuatro TIFF pequeños y su catálogo se leen a memoria desde una revisión
única de `Renato-R-V/hspace-datasets`. Se verifican hashes y se conserva NoData.
No se descargan los mapas globales originales ni se crean nuevas copias TIFF.
La ejecución completa utiliza aproximadamente 1,3 MB de datos remotos.

## Organización

| Archivo | Responsabilidad |
|---|---|
| `datos.py`, `fuentes.md` | Significado de entradas, procedencia y carga verificada |
| `armonizacion.py` | Agregación independiente a cuadrados sinusoidales de 120 km |
| `variables.py` | Proxy solar, energía de 24 h, relieve regional y filtros |
| `normalizacion.py` | Referencias por planeta, z-score y percentiles con empates |
| `metodos.py` | KNN exacto y búsqueda con prefiltro KMeans |
| `evaluacion.py` | Bloques espaciales, controles perturbados y selección técnica |
| `graficas.py` | Figuras Matplotlib de entradas, salidas, métodos y resultados |
| `salidas.py` | Tablas, ranking CSV e informe JSON |
| `comprobaciones.py` | Controles de unidades, NoData, empates y separación espacial |
| `resultados/` | Figuras, ranking y parámetros de la ejecución del notebook |

Los umbrales, pesos y coordenadas de consulta son visibles al principio del
notebook. Las referencias estadísticas se fijan antes de filtrar candidatos:
cambiar el límite de vegetación no cambia la población usada para normalizar.

## Alcance del resultado

La búsqueda usa albedo, un proxy de flujo solar absorbido y dispersión del
relieve dentro de 300 km. La elevación absoluta, los minerales, la vegetación,
las ciudades y el agua no se fuerzan como equivalentes entre planetas. Las tres
últimas variables filtran candidatos terrestres y permanecen como contexto.

GHI terrestre anual y modelo marciano para Ls=18,9° no son observaciones
equivalentes. El albedo también tiene definiciones diferentes. La normalización
produce posiciones **relativas dentro de cada población**, no una corrección
física de esas diferencias. La superficie nominal común es 14.400 km² en el
modelo esférico de cada planeta; no resuelve un punto de aterrizaje.

La selección compara recuperación de puntos conocidos con perturbaciones y
recall frente a búsqueda exacta. No hay etiquetas de análogos geológicos reales:
las tasas del informe no son probabilidades de encontrar un análogo válido.
KNN con percentiles y ordenación directa por esa misma distancia son el mismo
criterio matemático, no dos evidencias científicas independientes.

Las fuentes y atribuciones se detallan en [fuentes.md](./fuentes.md). Los
resultados combinados que incorporan las máscaras OpenGeoHub mantienen
**CC BY-SA 4.0**. No se publica automáticamente nada en Hugging Face.
