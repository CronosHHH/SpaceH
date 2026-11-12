# Tierra: datos para explorar análogos ambientales

Los GeoTIFF se publican en
[Renato-R-V/hspace-datasets, carpeta tierra](https://huggingface.co/datasets/Renato-R-V/hspace-datasets/tree/main/tierra).
No se conservan copias TIFF locales tras verificar la publicación. El
[catálogo](./catalogo.json) registra SHA256, tamaños, unidades, estadísticas
completas y georreferencias. Las fuentes y sus limitaciones están documentadas
por producto.

| Producto | Fuente | Malla de salida |
|---|---|---|
| GHI y albedo superficial | NASA POWER, climatología anual 2001–2025 | Global, 1° |
| Elevación NASADEM | NASA/JPL, principalmente SRTM de febrero de 2000 | 15″ y resumen a 1° |
| Ciudades, agua y vegetación | MODIS MCD12Q1.061 de 2021, mosaico OpenGeoHub; océano suplementario Natural Earth | 15″ y fracciones a 1° |
| Cobertura vegetal física 0–1 | MODIS MOD44B.061, ciclo 2021, mosaico ICDC/Hamburgo | Nativa 0,5° y media a 1° |

Los 15 segundos de arco equivalen aproximadamente a **464 m este-oeste en el
ecuador**; el tamaño este-oeste disminuye con la latitud. NASA POWER conserva
su resolución climática nativa de 1°: remuestrearlo a 15″ no añade información.
El prototipo trabaja a 1° y utiliza resúmenes pequeños para evitar descargar
los mapas detallados completos.

La ejecución completa del 11 de noviembre de 2026 generó un NASADEM de
**584.900.273 bytes** y una máscara detallada de **18.471.392 bytes**. Hay
**13.617 celdas de 1°** con las seis variables conocidas, incluida la cobertura
vegetal cuantitativa MOD44B. Véanse la
[validación conjunta](./auditoria/conjunto.json) y la
[consulta por ventanas remotas](./auditoria/ventanas_remotas.json).
El script y el notebook se ejecutaron completos y produjeron GeoTIFF idénticos;
los diez TIFF publicados, incluidos resúmenes y cubo, se eliminan localmente
después de cotejar sus tamaños y hashes con Hugging Face.

## Generar, validar y publicar

Desde la raíz del repositorio, con `marte/.venv/bin/python` y las dependencias
de [requirements.txt](./requirements.txt):

```bash
# Radiación terrestre: GHI y albedo.
marte/.venv/bin/python tierra/origen_ds_gui_Y_albeolo/generar_ghi.py
marte/.venv/bin/python tierra/origen_ds_gui_Y_albeolo/generar_albedo.py
marte/.venv/bin/python tierra/origen_ds_gui_Y_albeolo/validar_radiacion.py
marte/.venv/bin/python tierra/origen_ds_nasadem/generar_nasadem.py
marte/.venv/bin/python tierra/origen_ds_mascaras/generar_mascaras.py
marte/.venv/bin/python tierra/origen_ds_vegetacion/generar_vegetacion.py
marte/.venv/bin/python tierra/validar_conjunto.py
```

Las salidas temporales se escriben en `/tmp/hspace_tierra_productos/`.
NASADEM se reduce en el servidor: se reciben 14.520 teselas pequeñas, sin
almacenar los originales de 30 m. El generador permite reanudar interrupciones.
El mosaico MODIS original ocupa unos 133 MB; se procesa por franjas, sin cargar
el planeta completo en memoria. No se necesitan 90 GB locales.

[publicar_dataset.py](./publicar_dataset.py) exige auditorías completas y sus
hashes antes de publicar. Después coteja el tamaño y el hash de contenido remoto
(SHA256 LFS o identificador Git), guarda el SHA256 auditado y un recibo local y,
solo con `--eliminar-locales`, elimina
los TIFF correspondientes. Si una comprobación falla, conserva los archivos.
Ejemplo tras generar y validar:

```bash
HF_HUB_DISABLE_PROGRESS_BARS=1 marte/.venv/bin/python tierra/publicar_dataset.py \
  /tmp/hspace_tierra_productos/GHI_tierra.tif \
  /tmp/hspace_tierra_productos/Albedo_tierra.tif --eliminar-locales
```

## Uso e interpretación

- [Radiación y albedo](./docu/radiacion.md): definiciones físicas, periodo y contraste con API puntual.
- [NASADEM](./docu/nasadem.md): altura EGM96, cobertura real, reducción remota y comprobaciones nativas.
- [Máscaras](./docu/mascaras.md): clases, código de bits, desconocidos y limitación de la costa oceánica.
- [Cobertura vegetal 0–1](./docu/vegetacion.md): fracción física, malla 0,5°, periodo, NoData y conversión reproducible.
- [Prototipo](./docu/prototipo.md): notebook y script para cargar los productos publicados y visualizarlos juntos.

La máscara detallada distingue **ciudad = bit 1**, **agua = bit 2** y
**vegetación = bit 4**. El bit 8 identifica el suplemento oceánico y 255 es
desconocido: hay que comprobar NoData antes de aplicar operaciones de bits.
En la malla de 1° se utilizan fracciones y cobertura, sin promediar los códigos
categóricos ni tratar desconocido como terreno libre.

La sexta banda del cubo y `datos["Cobertura vegetal"]` del notebook utilizan
ahora la **fracción física MOD44B**, no el bit 4 ni la proporción de clases IGBP.
Por ejemplo, 0,55 significa 55 % de superficie vegetada estimada; `NaN` significa
que no hay estimación. La fuente tiene valores de 0 a 0,99, sin estirar el máximo
a 1. Su resolución real es 0,5° y se agrega a 1° para el prototipo.

## Buscar un análogo terrestre en Marte

[buscar_analogos_marte.py](./buscar_analogos_marte.py) compara una celda de
Tierra con todas las celdas del cubo alineado de Marte y devuelve los mejores
candidatos. Usa elevación, GHI y albedo; la vegetación, las ciudades, el agua y
los minerales no se fuerzan como variables equivalentes. Cada variable se
convierte a percentil por planeta antes de calcular una distancia euclídea
ponderada, por lo que el resultado significa **entorno relativo parecido**, no
igualdad física de unidades.

El ejemplo consulta la celda que contiene Madrid y descarga los cinco
resúmenes terrestres pequeños del catálogo:

```bash
MPLBACKEND=Agg marte/.venv/bin/python tierra/buscar_analogos_marte.py \
  --latitud-tierra 40.5 --longitud-tierra -3.5 --top 10
```

Se puede añadir `--pendiente` para derivar pendiente de los DEM a 1°. La
pendiente solo se calcula donde el píxel central y sus vecinos necesarios
tienen elevación válida; no interpola huecos ni inventa relieve. El JSON conserva las
variables marcianas y las coordenadas del centro de cada celda. La coordenada
de entrada se redondea a la celda de 1° que la contiene.

Las capas coinciden espacialmente tras agregarse a la malla común, pero tienen
fechas, definiciones y escalas diferentes. El GHI terrestre anual y el modelo
marciano para Ls=18,9° no son mediciones equivalentes. Un grado terrestre y uno
marciano tampoco representan la misma distancia.

## Atribución y licencias

NASA POWER y NASADEM se atribuyen a NASA y NASA/JPL; sus registros oficiales y
condiciones de uso se enlazan en la documentación correspondiente. Las máscaras
derivadas del mosaico OpenGeoHub se distribuyen bajo
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), con
atribución a Rolf Simoes/OpenGeoHub (2023), DOI `10.5281/zenodo.8367523`, y a
NASA MCD12Q1.061. Natural Earth es de dominio público. Los productos derivados
que incorporan esas máscaras, incluidos el cubo y la figura del prototipo,
mantienen **CC BY-SA 4.0**. No se atribuye una licencia única al resto del dataset.
La nueva distribución de vegetación ICDC/MOD44B está bajo **CC BY 4.0**, con
atribución a NASA y a ICDC, CEN, Universidad de Hamburgo.
