"""Uji tampilan tanpa browser: validitas CSS + semua kelas/atribut terdefinisi.

Cek ini menangkap kerusakan gaya yang paling sering terjadi: kurung tidak
seimbang, kelas dipakai tapi tidak ada definisinya, aset hilang.
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
GAGAL = 0


def cek(nama, syarat, info=""):
    global GAGAL
    if not syarat:
        GAGAL += 1
    print(f"  [{'OK  ' if syarat else 'GAGAL'}] {nama} {info}")


def periksa_css(berkas: Path) -> None:
    teks = berkas.read_text(encoding="utf-8")
    print(f"\n-> {berkas.name} ({len(teks)} bytes)")
    cek("kurung { } seimbang", teks.count("{") == teks.count("}"),
        f"{teks.count('{')} vs {teks.count('}')}")
    cek("tidak ada deklarasi kosong ';;'", ";;" not in teks)
    cek("tidak ada var() tanpa definisi",
        set(re.findall(r"var\((--[a-z0-9-]+)\)", teks)) <= set(re.findall(r"(--[a-z0-9-]+):", teks)))
    # warna: pastikan tidak ada nilai kosong
    cek("tidak ada ': ;'", ": ;" not in teks)
    cek("tidak ada aturan tanpa properti", not re.search(r"[{]\s*[}]", teks))


def kelas_dipakai(html: str) -> set:
    kel = set()
    for m in re.findall(r'class="([^"]+)"', html):
        # buang ekspresi template literal JS: ${...}
        m = re.sub(r"\$\{[^}]*\}", " ", m)
        kel |= {c for c in m.split() if c}
    for m in re.findall(r"classList\.(?:add|remove|toggle)\(([^)]+)\)", html):
        for c in m.split(","):
            c = c.strip().strip("'\"")
            if c and not c.startswith("$"):
                kel.add(c)
    for m in re.findall(r"className\s*=\s*['\"]([^'\"]+)['\"]", html):
        kel |= {c for c in m.split() if c and not c.startswith("$")}
    # buang potongan kode JS yang ikut tertangkap; kelas CSS selalu
    # cocok pola ini, jadi apa pun yang tidak cocok pasti bukan kelas
    return {k for k in kel if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", k)}


print("=" * 50)
print("UJI TAMPILAN")
print("=" * 50)

periksa_css(BASE / "static" / "gaya.css")
periksa_css(BASE / "static" / "gaya-hp.css")

print("\n-> cakupan kelas (dipakai HTML/JS vs ada di CSS)")
for nama_html, nama_css in (("index.html", "gaya.css"), ("mobile.html", "gaya-hp.css")):
    html = (BASE / "templates" / nama_html).read_text(encoding="utf-8")
    css = (BASE / "static" / nama_css).read_text(encoding="utf-8")
    terdefinisi = set(re.findall(r"\.([a-zA-Z][a-zA-Z0-9_-]*)", css))
    dipakai = kelas_dipakai(html)
    hilang = sorted(dipakai - terdefinisi)
    cek(f"{nama_html:12s} semua kelas punya gaya", not hilang, f"hilang: {hilang}" if hilang else
        f"{len(dipakai)} kelas")

print("\n-> aset yang dirujuk halaman benar-benar ada")
static = BASE / "static"
for nama_html in ("index.html", "mobile.html", "login.html"):
    html = (BASE / "templates" / nama_html).read_text(encoding="utf-8")
    rujukan = set(re.findall(r'/static/([A-Za-z0-9._-]+)', html))
    ada = {r: (static / r).exists() for r in rujukan}
    kurang = [r for r, v in ada.items() if not v]
    cek(f"{nama_html:12s} aset lengkap", not kurang, f"hilang: {kurang}" if kurang else
        f"{len(rujukan)} aset: {', '.join(sorted(rujukan))}")

print("\n-> merek & logo di setiap halaman")
for nama_html in ("index.html", "mobile.html", "login.html"):
    html = (BASE / "templates" / nama_html).read_text(encoding="utf-8")
    cek(f"{nama_html:12s} menampilkan logo", 'src="/static/logo.png"' in html)
    cek(f"{nama_html:12s} ada theme-color navy", "#1F3864" in html)

print("\n" + "=" * 50)
print("GAGAL" if GAGAL else "TAMPILAN RAPI & LENGKAP", f"({GAGAL} gagal)")
