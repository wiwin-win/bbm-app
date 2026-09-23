"""Bandingkan endpoint yang dipanggil inline JS dengan route yang benar-benar terdaftar."""
import json
import os
import re
import pathlib

import requests

s = requests.Session()
s.post("http://127.0.0.1:8791/api/login", data={"username": "admin", "password": "admin"})
spes = s.get("http://127.0.0.1:8791/openapi.json").json()
terdaftar = set()
for p, m in spes["paths"].items():
    for metode in m:
        terdaftar.add((metode.upper(), p))

dipakai = set()
for f in ("templates/index.html", "templates/mobile.html", "templates/login.html"):
    teks = pathlib.Path(f).read_text(encoding="utf-8")
    for m in re.finditer(r"""api\(\s*['"`]([^'"`?]+)""", teks):
        dipakai.add(("GET", m.group(1)))
    for m in re.finditer(r"""api\(\s*['"`]([^'"`?]+)[^)]*method:\s*['"](\w+)""", teks):
        dipakai.add((m.group(2).upper(), m.group(1)))
    for m in re.finditer(r"""fetch\(\s*['"`]([^'"`?]+)""", teks):
        dipakai.add(("GET", m.group(1)))

def cocok(metode, jalur):
    for mo, p in terdaftar:
        if mo != metode:
            continue
        if p == jalur:
            return True
        if "{" in p and re.fullmatch(re.sub(r"\{[^}]+\}", r"[^/]+", p), jalur):
            return True
    return False

print("endpoint dipanggil JS:", len(dipakai))
kurang = sorted(x for x in dipakai if not cocok(*x))
print("TIDAK ADA di server:", kurang if kurang else "tidak ada")
