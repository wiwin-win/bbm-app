"""Cek HTML yang diserve benar-benar memakai logo + gaya baru (tanpa style lama)."""
import requests

BASE = "http://127.0.0.1:8791"
s = requests.Session()
s.post(BASE + "/api/login", data={"username": "admin", "password": "admin"})
gagal = 0
for nama, jalur, gaya in (("PC", "/", "gaya.css"), ("HP", "/m", "gaya-hp.css"), ("Login", "/login", "gaya.css")):
    t = s.get(BASE + jalur).text
    ok = (gaya in t) and ("/static/logo.png" in t) and ("<style>" not in t)
    gagal += 0 if ok else 1
    print(f"[{'OK  ' if ok else 'GAGAL'}] {nama:6s} {jalur:7s} gaya={gaya in t} "
          f"logo={'/static/logo.png' in t} style-lama={'<style>' in t} {len(t)}b")
print("\nHASIL:", "BERSIH" if not gagal else f"{gagal} gagal")
