"""Uji aset logo: transparansi, kontras, dan isi ikon."""
import os
from PIL import Image

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
GAGAL = 0


def cek(nama, syarat, info=""):
    global GAGAL
    print(f"  [{'OK' if syarat else 'GAGAL'}]   {nama} {info}")
    if not syarat:
        GAGAL += 1


print("1) Kelengkapan berkas")
for f in ("logo.png", "logo-bening.png", "logo-putih.png",
          "icon-192.png", "icon-512.png", "icon-maskable-512.png", "favicon.ico"):
    cek(f"{f} ada", os.path.exists(os.path.join(STATIC, f)))

print("\n2) Transparansi logo-bening.png")
im = Image.open(os.path.join(STATIC, "logo-bening.png")).convert("RGBA")
w, h = im.size
px = list(im.getdata())
transparan = sum(1 for p in px if p[3] < 20) / len(px)
cek("latar bening > 25%", transparan > 0.25, f"{transparan*100:.1f}%")
cek("sudut transparan", all(im.getpixel(p)[3] < 20 for p in ((0, 0), (w-1, 0), (0, h-1))))
sisa = sum(1 for r, g, b, a in px if a > 200 and r > 240 and g > 240 and b > 240)
cek("tidak ada sisa kotak putih opaque", sisa < 40, f"{sisa} px")
ada_isi = sum(1 for p in px if p[3] > 200)
cek("logo masih ada isinya", ada_isi > 500, f"{ada_isi} px")

print("\n3) Siluet putih (logo-putih.png)")
im2 = Image.open(os.path.join(STATIC, "logo-putih.png")).convert("RGBA")
op = [p for p in im2.getdata() if p[3] > 200]
cek("semua opaque berwarna putih", all(p[0] == 255 and p[1] == 255 and p[2] == 255 for p in op),
    f"{len(op)} px")
cek("bentuknya sama dengan logo asli",
    im2.size == im.size)

print("\n4) Ikon PWA")
for sisi, nama in ((192, "icon-192.png"), (512, "icon-512.png")):
    ik = Image.open(os.path.join(STATIC, nama)).convert("RGB")
    cek(f"{nama} ukuran {sisi}px", ik.size == (sisi, sisi), str(ik.size))
    pxk = list(ik.getdata())
    putih = sum(1 for p in pxk if p[0] > 240 and p[1] > 240 and p[2] > 240)
    navy = sum(1 for p in pxk if abs(p[0]-23) < 20 and abs(p[1]-42) < 20 and abs(p[2]-76) < 20)
    cek(f"{nama} ada kartu putih", putih > sisi*sisi*0.15, f"{putih*100//(sisi*sisi)}%")
    cek(f"{nama} ada latar navy", navy > sisi*sisi*0.10, f"{navy*100//(sisi*sisi)}%")
    # logo harus jelas: ada piksel merah (warna logo) di dalam
    merah = sum(1 for p in pxk if p[0] > 120 and p[0] - p[2] > 45)
    cek(f"{nama} logo terlihat (ada warna merah logo)", merah > 300, f"{merah} px")

print("\n5) Favicon")
fav = Image.open(os.path.join(STATIC, "favicon.ico"))

cek("favicon terbaca", fav.size[0] >= 16, str(fav.size))
cek("favicon punya isi logo", sum(1 for p in fav.convert("RGB").getdata()
                                  if p[0] > 120 and p[0] - p[2] > 45) > 20)

print("\n" + "=" * 40)
print("GAGAL" if GAGAL else "SEMUA ASET LOGO SIAP", f"({GAGAL} gagal)")
print("=" * 40)
raise SystemExit(1 if GAGAL else 0)
