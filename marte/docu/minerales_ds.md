# Mapas mineralógicos clave de Marte — OMEGA

- es Olivino es complicado de medir por esos se usa 3 mediciones/señales distintas
- los dataset los he sacado de omega (venian con en extension .img y .csv con label)
    - los he pasado con 1 comando simple a .tiff
    - el de minerales hidratados(.csv) no renta pasarlo tiff al tener tan pocos datos
    - ademas los dataset, al pasarlos venian 1 pixel(7km aprox) movidos al norte y otro al oeste --> la ia creo un script que lo soluciona por ti

    
## Olivino OSP1

[Olivino OSP1](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/olivine/olivine_osp1_equ_map.img)
- Detecta la señal espectral de olivino OSP1.
- Lo usaremos para localizar terrenos marcianos con señal de olivino.
- Formato: `.IMG` PDS3, entero de 16 bits; aproximadamente 207 MB.
- [Etiqueta PDS](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/olivine/olivine_osp1_equ_map.lbl) (`.LBL`).

## Olivino OSP2

[Olivino OSP2](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/olivine/olivine_osp2_equ_map.img)
- Segundo parámetro espectral para detectar olivino.
- Lo usaremos junto con OSP1 y OSP3 para comparar distintas señales de olivino.
- Formato: `.IMG` PDS3, entero de 16 bits; aproximadamente 207 MB.
- [Etiqueta PDS](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/olivine/olivine_osp2_equ_map.lbl) (`.LBL`).

## Olivino OSP3

[Olivino OSP3](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/olivine/olivine_osp3_equ_map.img)
- Tercer parámetro espectral para detectar olivino.
- Lo usaremos como complemento de OSP1 y OSP2 en la comparación mineralógica.
- Formato: `.IMG` PDS3, entero de 16 bits; aproximadamente 207 MB.
- [Etiqueta PDS](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/olivine/olivine_osp3_equ_map.lbl) (`.LBL`).

## Piroxeno

[Piroxeno](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/pyroxene/pyroxene_bd2000_equ_map.img)
- Mapa de la señal de absorción espectral del piroxeno.
- Lo usaremos para identificar terrenos volcánicos y basálticos comparables.
- Formato: `.IMG` PDS3, entero de 16 bits; aproximadamente 207 MB.
- [Etiqueta PDS](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/pyroxene/pyroxene_bd2000_equ_map.lbl) (`.LBL`).

## Detecciones de minerales hidratados

[Sitios con minerales hidratados](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/hydrous/hydrous_sites_geo_map.csv)
- Localizaciones donde OMEGA/CRISM detectaron minerales hidratados.
- Lo usaremos para encontrar regiones relacionadas con alteración por agua antigua.
- Formato: `.CSV` (tabla de detecciones), no es un ráster TIFF.
- [Etiqueta PDS](https://pds-geosciences.wustl.edu/mex/mex-m-omega-5-ddr-global-maps-v1/mexomg_2000/data/hydrous/hydrous_sites_geo_map.lbl) (`.LBL`).

> Los mapas de olivino y piroxeno son parámetros espectrales, no porcentajes directos de abundancia. Conserva cada `.LBL` junto a su archivo de datos: contiene la escala, los valores NoData y la información espacial necesaria para interpretarlo.
