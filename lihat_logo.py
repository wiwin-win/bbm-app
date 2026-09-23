"""Lihat layout logo: peta blok warna + lokasi piksel mencolok."""
from PIL import Image

im = Image.open(r"C:\Users\wiwin\Documents\logo gas.jpeg").convert("RGB")
W, H = im.size
print("ukuran:", W, H)
px_all = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())

gw, gh = 8, 6
print("\npeta blok (warna dominan non-putih):")
for gy in range(gh):
    baris = []
    for gx in range(gw):
        box = im.crop((gx * W // gw, gy * H // gh, (gx + 1) * W // gw, (gy + 1) * H // gh))
        px = [c for c in list(box.getdata()) if not (c[0] > 225 and c[1] > 225 and c[2] > 225)]
        if len(px) < 20:
            baris.append("  .    ")
        else:
            r = sum(c[0] for c in px) // len(px)
            g = sum(c[1] for c in px) // len(px)
            b = sum(c[2] for c in px) // len(px)
            baris.append("#%02X%02X%02X" % (r, g, b))
    print("  ", " ".join(baris))

merah = max(((c, i) for i, c in enumerate(px_all)), key=lambda t: t[0][0] - t[0][2])
print("\npaling merah: #%02X%02X%02X" % merah[0], "di (x,y)=", merah[1] % W, merah[1] // W)
gelap = min(((c, i) for i, c in enumerate(px_all)), key=lambda t: sum(t[0]))
print("paling gelap : #%02X%02X%02X" % gelap[0], "di (x,y)=", gelap[1] % W, gelap[1] // W)
