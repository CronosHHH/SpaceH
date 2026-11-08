
---

para ver todo bonito ----- > 

EL MOLA
- esta en el DRIVE

EL albedo y la radiacion solar(GHI)
- al medir cambio más suaves, pesan menos y estan en aqui
- estos se obtiene por scripts 
    - es muy facil, el tuto está al final


--- 


EXPLICACION DE LA IA:


## Las 3 Variables Base

El modelo se apoya en tres capas fundamentales de datos planetarios:

| Variable | Fuente / Origen | ¿Qué mide de forma simple? | Función en el Proyecto |
| :--- | :--- | :--- | :--- |
| **1. Topografía ($MOLA$)** | Mars Orbiter Laser Altimeter (NASA/USGS) | **La elevación y forma del terreno** (altitud en metros). | Define la rugosidad del relieve, la altitud y la inclinación de las laderas. |
| **2. Albedo ($TES$)** | Thermal Emission Spectrometer (ASU/NASA) | **El color / reflectividad del suelo** (rango de $0.05$ a $0.40$). | Indica cuánta luz solar rebota (polvo claro) y cuánta es absorbida (roca oscura). |
| **3. Radiación Solar ($GHI$)** | Mars Climate Database (LMD) / Modelo Sol | **La "gasolina solar" en suelo plano** ($\text{W/m}^2$). | Mide la potencia solar entrante disponible en la superficie para una estación solar ($L_s$). |

---

## Generación de Datos Derivados

A partir del cruce de las tres variables base, derivamos información física y logística de alto valor mediante análisis espacial:

### 1. Pendiente y Orientación (*Slope & Aspect*)
* **Origen:** Derivado de la **Topografía ($MOLA$)**.
* **Qué nos dice:** Muestra qué tan empinado es el terreno y hacia qué punto cardinal miran las laderas.
* **Obtención:** 
  * En QGIS: `Ráster -> Análisis -> Pendiente` y `Orientación`.

---

### 2. Radiación Solar en Plano Inclinado ($GTI$)
* **Origen:** Combinación de **$GHI$ + Pendiente ($MOLA$)**.
* **Qué nos dice:** Ajusta la radiación solar al relieve real. Una ladera orientada al Sol recibe más energía que un plano horizontal o una cara en sombra.
* **Fórmula / Cálculo:**
  $$\text{GTI} = \text{GHI} \cdot \cos(\text{Pendiente})$$

---

### 3. Temperatura Superficial Marciana ($T_s$)
* **Origen:** Combinación de las 3 variables (**$GHI$ + $TES$ + $MOLA$**).
* **Qué nos dice:** La temperatura real del suelo ($^\circ\text{C}$) mediante el principio de balance de energía de Stefan-Boltzmann.
* **Fórmula / Cálculo:**
  $$T_s = \sqrt[4]{\frac{(1 - A) \cdot \text{GTI}}{\epsilon \cdot \sigma}} - 273.15$$
  * *Donde $A$ es el Albedo, $\epsilon = 0.95$ (emisividad marciana) y $\sigma = 5.67 \times 10^{-8}$ (constante de Stefan-Boltzmann).*

---

### 4. Mapa de Zonas Óptimas de Asentamiento (Multicriterio)
* **Origen:** Cruce final en Calculadora Ráster.
* **Qué nos dice:** Identifica visualmente en verde los lugares ideales para aterrizar y construir una base (suelo plano, cálido y con alta radiación útil).
* **Criterio de ejemplo:**
  $$(\text{GHI} > 120 \text{ W/m}^2) \text{ AND } (\text{Pendiente} < 8^\circ) \text{ AND } (\text{Temperatura} > -60^\circ\text{C})$$

---

## Ejecución Rápida en Python

Los datos GeoTIFF georreferenciados para el elipsoide marciano (`+proj=longlat +a=3396190 +b=3376200`) se generan ejecutando los scripts del repositorio en tu entorno virtual:

```bash
# 1. Crear el entorno virtual (solo la primera vez)
python3 -m venv venv

# 2. Activar entorno virtual
source venv/bin/activate

# 3. Generar capas GeoTIFF base
python generar_ghi.py
python generar_albedo.py
