"""Cek tampilan: halaman, logo terpasang, gaya termuat, file mandiri berisi aset."""
import base64
import re

import requests

BASE = "http://127.0.0.1:8791"
s = requests.Session()
s.post(BASE + "/api/login", data={"username": "admin", "password": "admin"})
GAGAL = 0


def cek(nama, syarat, info=""):
    global GAGAL
    if not syarat:
        GAGAL += 1
    print(f"  [{'OK  ' if syarat else 'GAGAL'}] {nama} {info}")


print("1) Halaman & aset")
for jalur in ("/", "/m", "/login", "/static/gaya.css", "/static/gaya-hp.css",
              "/static/logo.png", "/static/logo-bening.png", "/static/logo-putih.png",
              "/static/icon-192.png", "/static/icon-512.png", "/static/icon-maskable-512.png",
              "/static/favicon.ico", "/manifest.webmanifest", "/sw.js"):
    r = s.get(BASE + jalur)
    cek(f"{jalur:32s}", r.status_code == 200, f"{r.status_code} {len(r.content)}b")

print("\n2) Logo & gaya terpasang di halaman")
ix = s.get(BASE + "/").text
hp = s.get(BASE + "/m").text
lg = s.get(BASE + "/login").text
cek("PC pakai gaya.css", "/static/gaya.css" in ix)
cek("PC pakai logo", "/static/logo.png" in ix)
cek("PC tanpa <style> inline", "<style>" not in ix)
cek("PC ada favicon", "favicon.ico" in ix)
cek("HP pakai gaya-hp.css", "/static/gaya-hp.css" in hp)
cek("HP pakai logo", "/static/logo.png" in hp)
cek("HP tanpa <style> inline", "<style>" not in hp)
cek("Login pakai logo", "/static/logo.png" in lg)
cek("Judul PC = Monitoring BBM", "MONITORING BBM" in ix.upper())

print("\n3) File aplikasi HP mandiri")
r = s.get(BASE + "/unduh/bbm-hp.html")
m = r.text
cek("status 200 & nama file", r.status_code == 200
    and "bbm-hp-mandiri.html" in r.headers.get("content-disposition", ""))
cek("gaya sudah di-inline (ada <style>)", "<style>" in m)
cek("xlsx.js di-inline", "BBMXlsx" in m)
cek("logo di-inline (data:image)", "data:image/png;base64" in m)
cek("tidak ada rujukan ke /static/", "/static/" not in m)
# /api/ hanya muncul sebagai jalur sinkron opsional (server bisa tidak ada) — tidak fatal
cek("sinkron server bersifat opsional (ada mode mandiri)", "sedangMandiri" in m
    and "alamatApi" in m)
cek("service worker dimatikan", "serviceWorker.register" not in m or "(function(){})" in m)
cek("ukuran wajar (<2MB)", len(m.encode()) < 2_000_000, f"{len(m.encode())//1024} KB")

print("\n4) Simpan file mandiri (untuk dikirim ke HP)")
with open(r"C:\Users\wiwin\Documents\BBM-HP-Input.html", "wb") as f:
    f.write(m.encode("utf-8"))
cek("tersimpan di Documents", True, "BBM-HP-Input.html")

print("\n" + "=" * 44)
print("GAGAL" if GAGAL else "SEMUA TAMPILAN SIAP", f"({GAGAL} gagal)")
