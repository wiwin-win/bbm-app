"""Cek tag HTML berpasangan (div/section/table/tr/... ) di semua template.

Tag yang tidak seimbang bikin layout berantakan tanpa pesan error, jadi
diperiksa terpisah dari uji tampilan.

    python cek_tag.py
"""
import re
import sys

TEMPLATES = {
    "index.html": "templates/index.html",
    "mobile.html": "templates/mobile.html",
    "login.html": "templates/login.html",
}
PASANG = ("div", "section", "table", "thead", "tbody", "tr", "form", "label", "nav", "header", "footer")
VOID = {"input", "br", "hr", "img", "meta", "link", "source", "col"}

GAGAL = 0
for nama, jalur in TEMPLATES.items():
    try:
        html = open(jalur, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"  [LEWAT] {nama} tidak ada")
        continue
    # buang isi <script>/<style> supaya string di JS tidak dihitung tag
    bersih = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S | re.I)
    masalah = []
    for tag in PASANG:
        buka = len(re.findall(rf"<{tag}\b(?![^>]*/>)", bersih, re.I))
        tutup = len(re.findall(rf"</{tag}\s*>", bersih, re.I))
        if buka != tutup:
            masalah.append(f"<{tag}> {buka} vs </{tag}> {tutup}")
    if masalah:
        GAGAL += 1
        print(f"  [GAGAL] {nama:12s} " + "; ".join(masalah))
    else:
        print(f"  [OK  ] {nama:12s} semua tag berpasangan")

print("\n" + "=" * 52)
print("TAG HTML SEIMBANG" if not GAGAL else f"GAGAL ({GAGAL} berkas)")
print("=" * 52)
sys.exit(1 if GAGAL else 0)
