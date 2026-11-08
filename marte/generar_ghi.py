from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.transform import from_bounds


# Grid cell centers for a global 1 degree equirectangular raster.
width, height = 360, 180
lons = -180.0 + (np.arange(width) + 0.5)
lats = 90.0 - (np.arange(height) + 0.5)
lon_grid, lat_grid = np.meshgrid(lons, lats)

# Mars solar geometry at solar longitude Ls = 18.9 degrees.
ls = np.radians(18.9)
obliquity = np.radians(25.19)
declination = np.arcsin(np.sin(obliquity) * np.sin(ls))
lat_rad = np.radians(lat_grid)

# Sunrise/sunset hour angle. Clipping also handles polar day and night.
cos_ws = -np.tan(lat_rad) * np.tan(declination)
ws = np.arccos(np.clip(cos_ws, -1.0, 1.0))

# Daily mean irradiance on a horizontal surface (W/m^2).
# 590 W/m^2 is the approximate solar flux at Mars; 0.75 is an
# assumed constant atmospheric transmission, not a measured local value.
solar_flux_surface = 590.0 * 0.75
ghi = (solar_flux_surface / np.pi) * (
    ws * np.sin(lat_rad) * np.sin(declination)
    + np.cos(lat_rad) * np.cos(declination) * np.sin(ws)
)
ghi = np.maximum(ghi, 0.0).astype(np.float32)

out_dir = Path(__file__).resolve().parent
transform = from_bounds(-180.0, -90.0, 180.0, 90.0, width, height)
tif_path = out_dir / "GHI_marte.tif"
png_path = out_dir / "GHI_marte.png"

with rasterio.open(
    tif_path,
    "w",
    driver="GTiff",
    height=height,
    width=width,
    count=1,
    dtype="float32",
    crs="+proj=longlat +a=3396190 +b=3376200 +no_defs",
    transform=transform,
) as dst:
    dst.write(ghi, 1)
    dst.set_band_description(1, "Daily mean surface solar irradiance")
    dst.update_tags(1, units="W/m^2", solar_longitude_deg="18.9")

# PNG is a labeled visualization of the same grid, with north at the top.
fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
image = ax.imshow(
    ghi,
    extent=(-180, 180, -90, 90),
    origin="upper",
    cmap="inferno",
    vmin=0,
    vmax=float(ghi.max()),
    aspect="auto",
)
ax.set(
    title="Radiación solar media diaria en Marte · Ls = 18,9°",
    xlabel="Longitud (°)",
    ylabel="Latitud (°)",
    xlim=(-180, 180),
    ylim=(-90, 90),
)
fig.colorbar(image, ax=ax, label="GHI (W/m²)")
fig.savefig(png_path, dpi=150)
plt.close(fig)

print(f"GeoTIFF creado: {tif_path}")
print(f"PNG creado: {png_path}")
