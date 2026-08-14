#!/usr/bin/env python3
"""
Incrusta `portada.jfif` dentro de `index.html` como data URI.

El entregable tiene que seguir siendo UN SOLO archivo que funcione sin conexión
(ver CLAUDE.md), así que la portada no puede quedar como archivo aparte. Este
script la recomprime y la escribe dentro del `<img id="portada">`.

Correr después de cambiar `portada.jfif`:
    python embed_portada.py

Requiere Pillow (viene en Anaconda).
"""

import base64
import io
import pathlib
import re
import sys

from PIL import Image

RAIZ = pathlib.Path(__file__).parent
ORIGEN = RAIZ / "portada.jfif"
DESTINO = RAIZ / "index.html"

# La portada se muestra a lo sumo a ~900 px de ancho; más resolución sólo infla
# el archivo. Calidad 82 es el punto donde el JPEG deja de verse degradado.
ANCHO_MAX = 900
CALIDAD = 82


def main():
    if not ORIGEN.exists():
        sys.exit(f"No encontré {ORIGEN}")

    im = Image.open(ORIGEN).convert("RGB")
    if im.width > ANCHO_MAX:
        alto = round(im.height * ANCHO_MAX / im.width)
        im = im.resize((ANCHO_MAX, alto), Image.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=CALIDAD, optimize=True, progressive=True)
    datos = buf.getvalue()
    uri = "data:image/jpeg;base64," + base64.b64encode(datos).decode("ascii")

    html = DESTINO.read_text(encoding="utf-8")
    nuevo, n = re.subn(
        r'(<img id="portada"[^>]*\ssrc=")[^"]*(")',
        lambda m: m.group(1) + uri + m.group(2),
        html,
        count=1,
    )
    if n != 1:
        sys.exit('No encontré el <img id="portada" ... src="..."> en index.html')

    DESTINO.write_text(nuevo, encoding="utf-8")
    print(f"Portada incrustada: {im.width}x{im.height}, "
          f"{len(datos)/1024:.0f} KB → {len(uri)/1024:.0f} KB en base64")
    print(f"index.html quedó en {len(nuevo)/1024:.0f} KB")


if __name__ == "__main__":
    main()
