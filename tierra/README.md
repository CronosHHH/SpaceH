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

Los 15 segundos de arco equivalen aproximadamente a **464 m este-oeste en el
ecuador**; el tamaño este-oeste disminuye con la latitud. NASA POWER conserva
su resolución climática nativa de 1°: remuestrearlo a 15″ no añade información.
El prototipo trabaja a 1° y utiliza resúmenes pequeños para evitar descargar
los mapas detallados completos.

La ejecución completa del 11 de noviembre de 2026 generó un NASADEM de
**584.900.273 bytes** y una máscara detallada de **18.471.392 bytes**. Hay
**14.520 celdas de 1°** con las seis variables conocidas. Véanse la
[validación conjunta](./auditoria/conjunto.json) y la
[consulta por ventanas remotas](./auditoria/ventanas_remotas.json).
El script y el notebook se ejecutaron completos y produjeron GeoTIFF idénticos;
los ocho TIFF publicados, incluidos resúmenes y cubo, se eliminaron localmente
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
marte/.venv/bin/python tierra/validar_conjunto.py
```

Las salidas temporales se escriben en `/tmp/hspace_tierra_productos/`.
NASADEM se reduce en el servidor: se reciben 14.520 teselas pequeñas, sin
almacenar los originales de 30 m. El generador permite reanudar interrupciones.
El mosaico MODIS original ocupa unos 133 MB; se procesa por franjas, sin cargar
el planeta completo en memoria. No se necesitan 90 GB locales.

[publicar_dataset.py](./publicar_dataset.py) exige auditorías completas y sus
hashes antes de publicar. Después coteja el tamaño y SHA256 confirmados por
Hugging Face, guarda un recibo local y, solo con `--eliminar-locales`, elimina
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
- [Prototipo](./docu/prototipo.md): notebook y script para cargar los productos publicados y visualizarlos juntos.

La máscara detallada distingue **ciudad = bit 1**, **agua = bit 2** y
**vegetación = bit 4**. El bit 8 identifica el suplemento oceánico y 255 es
desconocido: hay que comprobar NoData antes de aplicar operaciones de bits.
En la malla de 1° se utilizan fracciones y cobertura, sin promediar los códigos
categóricos ni tratar desconocido como terreno libre.

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
