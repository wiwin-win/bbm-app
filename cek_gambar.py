"""Verifikasi screenshot tanpa mata manusia: warna dominan, logo hadir, teks (OCR).

Dipakai karena model tidak bisa melihat gambar. Menangkap masalah tampilan
yang paling mungkin: halaman putih kosong, CSS gagal termuat, logo hilang,
atau teks tidak terbaca.
"""
import os

from PIL import Image
from rapidocr_onnxruntime import RapidOCR

BASE = os.path.dirname(os.path.abspath(__file__))
GAGAL = 0
ocr = RapidOCR()


def analisa(nama: str, wajib_teks: list[str], warna_min: dict | None = None,
            harus_ada_merah: bool = True):
    """warna_min: {'putih': 0.05, 'navy': 0.02} = proporsi minimal."""
    global GAGAL
    jalur = os.path.join(BASE, nama)
    if not os.path.exists(jalur):
        print(f"[GAGAL] {nama}: tidak ada")
        GAGAL += 1
        return
    im = Image.open(jalur).convert("RGB")
    w, h = im.size
    px = im.resize((min(w, 420), int(h * min(w, 420) / w))).getdata()
    total = len(px)
    kunci = {
        "putih": lambda p: p[0] > 235 and p[1] > 235 and p[2] > 235,
        "navy": lambda p: p[2] > p[0] + 12 and p[2] > 55 and p[2] < 160 and p[0] < 110,
        "merah": lambda p: p[0] > 140 and p[0] - p[2] > 60 and p[1] < 140,
        "gelap": lambda p: p[0] < 90 and p[1] < 90 and p[2] < 110,
    }
    prop = {k: sum(1 for p in px if f(p)) / total for k, f in kunci.items()}
    res, _ = ocr(jalur)
    teks = " | ".join(t[1] for t in (res or []))
    print(f"\n-> {nama}  {im.size}  proporsi: "
          + ", ".join(f"{k}={v:.1%}" for k, v in prop.items()))

    punya = [t for t in wajib_teks if t.lower() in teks.lower()]
    for t in wajib_teks:
        ok = t.lower() in teks.lower()
        if not ok:
            GAGAL += 1
        print(f"  [{'OK  ' if ok else 'GAGAL'}] teks '{t}'")
    if warna_min:
        for k, v in warna_min.items():
            ok = prop[k] >= v
            if not ok:
                GAGAL += 1
            print(f"  [{'OK  ' if ok else 'GAGAL'}] warna {k} >= {v:.0%} (ada {prop[k]:.1%})")
    if harus_ada_merah:
        ok = prop["merah"] > 0.0002
        if not ok:
            GAGAL += 1
        print(f"  [{'OK  ' if ok else 'GAGAL'}] ada aksen merah logo (ada {prop['merah']:.2%})")
    print("  teks terbaca:", (teks[:200] or "(kosong)"))


analisa("pratinjau-login.png", ["Monitoring BBM", "USERNAME", "PASSWORD", "Masuk"],
        {"putih": 0.05, "navy": 0.15})
analisa("pratinjau-pc.png", ["GEMBIRA ANGGUN SETIA", "TANGGAL", "ALAT", "Export Excel"],
        {"putih": 0.25})
analisa("pratinjau-hp.png", ["Input", "Simpan"], {"putih": 0.20})
analisa("pratinjau-hp-excel.png", ["Excel"], {"putih": 0.20})

print("\n" + "=" * 46)
print("SEMUA GAMBAR WAJAR" if not GAGAL else f"ADA MASALAH: {GAGAL} gagal")
