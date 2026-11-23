"""Browser tab icon (favicon) from the university logo (owner 2026-11-22: "munculkan logo universitas pertamina").

The full logo has the words "Universitas Pertamina", unreadable at 16-32 px, so only the coloured emblem is kept:
pixels with low colour saturation (the grey and black lettering) become transparent, the remaining coloured
pixels are cropped and centred on a square. Writes, next to the logo:
  favicon.png            192x192, transparent background (browser tabs, Android)
  apple-touch-icon.png   180x180, white background (iPhone/iPad home screen)
  icon-512.png           512x512, transparent background (web app manifest, install on phone)

Run from the repo root (no arguments needed; an optional argument is another logo file):
  python tools/make_favicon.py
  python tools/make_favicon.py site/logo.png
"""
from __future__ import annotations

import colorsys
import sys
from pathlib import Path

from PIL import Image

LOGO = Path("site/logo.png")   # this prodi's logo; the template package ships logo.png instead
MIN_SATURATION = 0.35              # below this a pixel counts as lettering (grey/black), not emblem
MARGIN = 0.06                      # empty border around the emblem, as a share of the square side


def emblem(logo: Image.Image) -> Image.Image:
    """Coloured part of the logo on a transparent square."""
    img = logo.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a and colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[1] < MIN_SATURATION:
                px[x, y] = (0, 0, 0, 0)
    kotak = img.getbbox()
    if not kotak:
        raise SystemExit("Logo tidak punya bagian berwarna; favicon tidak dibuat.")
    img = img.crop(kotak)
    sisi = int(max(img.size) * (1 + 2 * MARGIN))
    persegi = Image.new("RGBA", (sisi, sisi), (0, 0, 0, 0))
    persegi.paste(img, ((sisi - img.width) // 2, (sisi - img.height) // 2), img)
    return persegi


def main(argv: list[str]) -> int:
    logo = Path(argv[0]) if argv else LOGO
    if not logo.is_file():
        print(f"Logo tidak ditemukan: {logo}")
        return 1
    lambang = emblem(Image.open(logo))
    tujuan = logo.parent
    lambang.resize((192, 192), Image.LANCZOS).save(tujuan / "favicon.png", optimize=True)
    lambang.resize((512, 512), Image.LANCZOS).save(tujuan / "icon-512.png", optimize=True)
    putih = Image.new("RGBA", (180, 180), (255, 255, 255, 255))
    kecil = lambang.resize((160, 160), Image.LANCZOS)
    putih.paste(kecil, (10, 10), kecil)
    putih.convert("RGB").save(tujuan / "apple-touch-icon.png", optimize=True)
    print(f"Ditulis: {tujuan / 'favicon.png'}, {tujuan / 'apple-touch-icon.png'}, {tujuan / 'icon-512.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
