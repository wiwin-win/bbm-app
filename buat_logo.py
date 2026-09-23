"""Siapkan aset logo dari file logo perusahaan.

Masukan : C:\\Users\\wiwin\\Documents\\logo gas.jpeg  (bisa diganti via argumen)
Keluaran: static/logo.png, static/logo-putih.png, static/icon-192.png,
          static/icon-512.png, static/favicon.ico
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
SUMBER = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\wiwin\Documents\logo gas.jpeg")

NAVY = (31, 56, 100)          # warna utama aplikasi
NAVY_TUA = (23, 42, 76)
PUTIH = (255, 255, 255)


def potong_putih(im: Image.Image, ambang: int = 242) -> Image.Image:
    """Buang tepi putih di sekeliling logo."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    kiri, atas, kanan, bawah = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if not (r >= ambang and g >= ambang and b >= ambang):
                kiri, atas = min(kiri, x), min(atas, y)
                kanan, bawah = max(kanan, x), max(bawah, y)
    if kanan <= kiri or bawah <= atas:
        return rgb
    return rgb.crop((kiri, atas, kanan + 1, bawah + 1))


def transparankan(im: Image.Image, ambang: int = 230, lunak: int = 14) -> Image.Image:
    """Bikin latar putih jadi transparan dengan tepi halus.

    `ambang` = tingkat kecerahan yang mulai dipudarkan; >= ambang+lunak jadi bening total.
    Dipakai ambang 230 + lunak 14 -> latar JPEG (247) langsung bening, tepi tetap halus.
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            terang = min(r, g, b)
            if terang >= ambang + lunak:
                px[x, y] = (r, g, b, 0)
            elif terang >= ambang:
                px[x, y] = (r, g, b, int(a * (1 - (terang - ambang) / lunak)))
    return im


def dalam_kotak(logo: Image.Image, sisi: int, latar, tepi_rasio: float = 0.78,
                radius_rasio: float = 0.16, kotak_putih: bool = False,
                porsi_kartu: float = 0.74) -> Image.Image:
    """Tempel logo di tengah kanvas persegi (untuk ikon PWA / favicon).

    `porsi_kartu` = besar kartu putih relatif sisi; sisanya jadi bingkai navy,
    supaya ikon tetap terbaca di layar HP (tidak tampak putih polos).
    """
    kanvas = Image.new("RGBA", (sisi, sisi), latar + (255,))
    if kotak_putih:
        dalam = int(sisi * porsi_kartu)
        geser = (sisi - dalam) // 2
        r = int(dalam * radius_rasio)
        putih = Image.new("RGBA", (sisi, sisi), (0, 0, 0, 0))
        d = ImageDraw.Draw(putih)
        d.rounded_rectangle([geser, geser, geser + dalam - 1, geser + dalam - 1],
                            radius=r, fill=PUTIH + (255,))
        kanvas = Image.alpha_composite(kanvas, putih)
        maks = int(dalam * tepi_rasio)
    else:
        maks = int(sisi * tepi_rasio)
    kecil = logo.copy()
    kecil.thumbnail((maks, maks), Image.LANCZOS)
    kanvas.alpha_composite(kecil, ((sisi - kecil.width) // 2, (sisi - kecil.height) // 2))
    return kanvas


def main() -> None:
    STATIC.mkdir(exist_ok=True)
    asli = Image.open(SUMBER).convert("RGB")
    print("sumber:", SUMBER, asli.size)

    rapi = potong_putih(asli)
    print("setelah dipotong:", rapi.size)
    rapi.save(STATIC / "logo.png")
    print("  -> static/logo.png")

    bening = transparankan(rapi)
    bening.save(STATIC / "logo-bening.png")
    print("  -> static/logo-bening.png (latar transparan)")

    # versi putih untuk latar gelap (logo asli digambar jadi putih polos)
    lebar = Image.new("RGBA", bening.size, (0, 0, 0, 0))
    lp, bp = lebar.load(), bening.load()
    for y in range(bening.height):
        for x in range(bening.width):
            r, g, b, a = bp[x, y]
            if a > 0:
                lp[x, y] = (255, 255, 255, a)
    lebar.save(STATIC / "logo-putih.png")
    print("  -> static/logo-putih.png (siluet putih)")

    # ikon PWA: logo di atas kartu putih, latar navy
    for sisi in (192, 512):
        ikon = dalam_kotak(bening, sisi, NAVY_TUA, tepi_rasio=0.60,
                           radius_rasio=0.18, kotak_putih=True)
        ikon.convert("RGB").save(STATIC / f"icon-{sisi}.png")
        print(f"  -> static/icon-{sisi}.png")
    # versi maskable (logo lebih kecil, aman kalau dipotong bulat)
    dalam_kotak(bening, 512, NAVY_TUA, tepi_rasio=0.44, kotak_putih=True).convert("RGB").save(
        STATIC / "icon-maskable-512.png")
    print("  -> static/icon-maskable-512.png")

    fav = dalam_kotak(bening, 64, PUTIH, tepi_rasio=0.86, kotak_putih=False)
    fav.convert("RGB").save(STATIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("  -> static/favicon.ico")

    # gambar pratinjau untuk dicek manual
    pratinjau = Image.new("RGB", (400, 160), NAVY)
    pratinjau.paste(dalam_kotak(bening, 120, NAVY_TUA, kotak_putih=True), (16, 20))
    pratinjau.paste(dalam_kotak(bening, 120, PUTIH), (150, 20))
    pratinjau.paste(dalam_kotak(bening, 120, (245, 247, 250)), (284, 20))
    pratinjau.save(BASE / "pratinjau-logo.png")
    print("  -> pratinjau-logo.png (cek tampilan di 3 latar)")


if __name__ == "__main__":
    main()
