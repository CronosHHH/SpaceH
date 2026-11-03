# HSpace: MVP de analogías Luna–Tierra

Una demo para elegir un punto de la Luna y un radio, ajustar la importancia de la temperatura superficial y de la composición mineral, y ordenar un pequeño catálogo de lugares terrestres por similitud.

**Todos los valores ambientales del catálogo son sintéticos e ilustrativos.** No son mediciones de esos lugares ni permiten identificar análogos científicos. La puntuación expresa la semejanza dentro de este modelo de demostración; no es una probabilidad.

## Abrir y entender el proyecto

Abre [index.html](./index.html) con doble clic en el navegador. No hace falta instalar nada, iniciar un servidor ni tener claves de API. La demo funciona sin consultas a servicios externos.

| Paso | Herramienta | Para qué sirve |
| --- | --- | --- |
| Interfaz | HTML y CSS | Formulario, visualización y resultados. |
| Cálculo | JavaScript del navegador | Filtrar muestras, calcular medias y ordenar coincidencias. |
| Datos | [data.js](./data.js) | Catálogo pequeño, legible y editable. |
| Backend y base de datos | Ninguno | No hacen falta para este alcance. |
| Compilación | Ninguna | El navegador ejecuta los archivos directamente. |

## Uso

1. Introduce latitud lunar (−90 a 90°), longitud lunar (−180 a 180°) y radio en kilómetros.
2. Ajusta los pesos de temperatura y composición mineral. Un peso cero excluye esa variable; ambos a cero producen un error.
3. Consulta las muestras lunares incluidas, sus valores medios y el ranking terrestre. Si el círculo no contiene muestras, aparece «sin datos».

El catálogo tiene cobertura limitada: no contiene datos para cualquier coordenada y no busca en toda la superficie terrestre. Las temperaturas mínima y máxima son **superficiales**, ilustrativas y sin un periodo de observación real asociado.

## Cálculo, sin servicios externos

Se calcula la distancia esférica entre el punto elegido y cada muestra mediante la fórmula de haversine, usando el radio de la Luna: **1.737,4 km**. Entran las muestras cuya distancia es menor o igual que el radio indicado.

Después se calculan medias aritméticas de las temperaturas mínimas y máximas y de las tres fracciones minerales. Las fracciones no negativas se expresan como porcentajes normalizados para sumar 100 entre los tres minerales representados. Esta simplificación no describe toda la mineralogía de una roca.

Cada muestra tiene el mismo peso. El resultado es una media de las muestras encontradas, **no un promedio continuo de toda el área**. La media de las mínimas y la media de las máximas tampoco son los extremos de temperatura de todo el círculo.

Para cada candidato terrestre se comparan sus valores con los valores lunares medios:

```text
similitud_temperatura = 100 × max(0,
  1 − (abs(Tmin_tierra − Tmin_luna) + abs(Tmax_tierra − Tmax_luna)) / 400
)

similitud_mineral = 100 × (1 − suma(abs(mineral_tierra − mineral_luna)) / 200)

puntuación = (peso_temperatura × similitud_temperatura
           + peso_mineral × similitud_mineral)
           / (peso_temperatura + peso_mineral)
```

Las temperaturas se expresan en °C y las diferencias minerales en puntos porcentuales. La escala térmica de **200 °C de diferencia media** es una decisión heurística de esta demo: equivale al divisor 400 al sumar las dos diferencias y fija cuándo la similitud térmica llega a cero. No tiene una calibración científica. Las puntuaciones van de 0 a 100.

## Pasos para un hackathon

1. Abrir la demo y recorrer el flujo completo con los ejemplos disponibles.
2. Editar el catálogo para explicar cómo cambian las coincidencias al variar los valores y los pesos.
3. Comprobar entradas inválidas, ambos pesos a cero y círculos sin muestras.
4. Mostrar el resultado junto a sus límites: datos sintéticos, catálogo pequeño y escala de similitud elegida para la demo.
5. Sustituir los ejemplos por datos científicos solo después de acordar unidades, resolución, periodos y tratamiento de zonas sin datos.

## Evolución hacia datos reales

Los siguientes son enlaces oficiales de referencia **pendientes de verificar**; esta demo no los consulta ni incluye endpoints numéricos verificados para un punto y un radio.

- **Mapa lunar:** [NASA Trek](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon). Sus tiles WMTS permiten visualizar capas. Un color de imagen no sustituye al valor numérico original de temperatura o mineralogía.
- **Temperatura superficial lunar:** [Diviner/LRO en PDS](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm). Elegir un producto raster numérico y definir el periodo y la hora lunar antes de extraer valores.
- **Composición mineral lunar:** [M³/Chandrayaan-1 en PDS](https://pds-imaging.jpl.nasa.gov/volumes/m3.html). Los datos espectrales requieren procesamiento y una definición explícita de los minerales comparados; no son porcentajes listos para usar.
- **Temperatura superficial terrestre:** [MODIS MOD11A2 en Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD11A2). Definir observaciones diurnas/nocturnas, periodos y calidad; no sustituir temperatura superficial por temperatura del aire. Earth Engine añade cuenta, configuración y procesamiento.

Para la mineralogía terrestre habría que preparar un catálogo con cartografía geológica o mediciones compatibles. Un tipo de roca y sus fracciones minerales son datos distintos. Al integrar datos reales, lo más sencillo es empezar con unas pocas regiones y exportar resultados preprocesados al catálogo existente; añadir un backend solo cuando haga falta consultar áreas nuevas.
