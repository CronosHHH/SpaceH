#!/usr/bin/env bash
set -euo pipefail

MARTE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$MARTE_DIR/imagenes_png"
mkdir -p "$OUTPUT_DIR"

while IFS= read -r -d '' tif; do
  relative_path="${tif#"$MARTE_DIR"/}"
  png_path="$OUTPUT_DIR/${relative_path%.*}.png"
  mkdir -p "$(dirname -- "$png_path")"

  gdal_translate \
    -q \
    -of PNG \
    -ot Byte \
    -scale \
    -outsize 25% 25% \
    "$tif" \
    "$png_path"

  printf 'Creada: %s\n' "$png_path"
done < <(
  find "$MARTE_DIR" -type f \( -iname '*.tif' -o -iname '*.tiff' \) -print0
)
