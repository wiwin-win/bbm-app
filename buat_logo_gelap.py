# -*- coding: utf-8 -*-
"""Buat varian logo gelap: piksel outline gelap/kebiruan -> abu terang #C8D0DC.

Aturan remap per piksel (alpha dipertahankan):
- Dingin (B >= R - 10) DAN luminance < 140  -> digeser ke arah abu terang
  sebesar f = (140 - L) / 140.  Semakin gelap, semakin penuh remapnya,
  anti-alias ikut halus.
- Hangat / jenuh (merah, oranye, emas)      -> tidak disentuh.
"""
import os
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")

TERANG = (200, 208, 220)          # #C8D0DC
AMBAT_LUM = 140.0

SUMBER = ("logo-login.png", "logo-header-hp.png", "logo-header-pc.png")


def lum(r, g, b):
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def jadi_gelap(nama):
    src = os.path.join(STATIC, nama)
    dst = os.path.join(STATIC, nama.replace(".png", "-gelap.png"))
    im = Image.open(src).convert("RGBA")
    out = []
    berubah = 0
    for r, g, b, a in im.getdata():
        if a == 0:
            out.append((r, g, b, a))
            continue
        L = lum(r, g, b)
        dingin = b >= r - 10
        if dingin and L < AMBAT_LUM:
            # sangat gelap -> remap penuh; anti-alias (70..140) bertahap
            f = 1.0 if L <= 70 else (AMBAT_LUM - L) / (AMBAT_LUM - 70)
            nr = round(r + (TERANG[0] - r) * f)
            ng = round(g + (TERANG[1] - g) * f)
            nb = round(b + (TERANG[2] - b) * f)
            out.append((nr, ng, nb, a))
            berubah += 1
        else:
            out.append((r, g, b, a))
    baru = Image.new("RGBA", im.size)
    baru.putdata(out)
    baru.save(dst)
    print(f"{nama} -> {os.path.basename(dst)}  ({im.size[0]}x{im.size[1]}, "
          f"{berubah} px diremap dari {sum(1 for p in out if p[3] > 0)} px opaque)")


if __name__ == "__main__":
    for n in SUMBER:
        jadi_gelap(n)
    print("Selesai.")
