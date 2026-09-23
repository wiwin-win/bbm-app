"""Buat ikon PWA (192 & 512 px) untuk aplikasi Monitoring BBM."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
OUT = BASE / "static"
OUT.mkdir(exist_ok=True)


def ikon(ukuran: int) -> Image.Image:
    img = Image.new("RGB", (ukuran, ukuran), "#1F3864")
    d = ImageDraw.Draw(img)
    # bentuk tetes BBM
    cx = ukuran // 2
    r = int(ukuran * 0.20)
    d.ellipse([cx - r, int(ukuran * 0.30), cx + r, int(ukuran * 0.30) + 2 * r], fill="#FFC107")
    d.polygon([(cx, int(ukuran * 0.16)), (cx - r, int(ukuran * 0.42)), (cx + r, int(ukuran * 0.42))],
              fill="#FFC107")
    # teks BBM
    try:
        font = ImageFont.truetype("arialbd.ttf", int(ukuran * 0.19))
    except OSError:
        font = ImageFont.load_default()
    teks = "BBM"
    kotak = d.textbbox((0, 0), teks, font=font)
    d.text((cx - (kotak[2] - kotak[0]) / 2 - kotak[0], int(ukuran * 0.66) - kotak[1]), teks,
           fill="#FFFFFF", font=font)
    return img


for uk in (192, 512):
    ikon(uk).save(OUT / f"icon-{uk}.png")
    print("dibuat:", OUT / f"icon-{uk}.png")
