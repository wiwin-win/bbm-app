"""Sweep fungsional: panggil SEMUA endpoint yang dipakai UI, pastikan bukan 404/500."""
import json

import requests

BASE = "http://127.0.0.1:8791"
s = requests.Session()
hasil = []


def cek(nama, r, harap=200):
    ok = r.status_code == harap
    hasil.append(ok)
    print(f"{'OK  ' if ok else 'FAIL'} {nama:44s} {r.status_code} {len(r.content)}b")


cek("login", s.post(BASE + "/api/login", data={"username": "admin", "password": "admin"}))
cek("saya (user+settings)", s.get(BASE + "/api/saya"))
cek("master (unit/driver/location/activity)", s.get(BASE + "/api/master"))
cek("entries", s.get(BASE + "/api/entries?limit=5"))
cek("entries filter bulan", s.get(BASE + "/api/entries?bulan=2026-09&limit=5"))
cek("entries filter bulan+alat+driver+lokasi",
    s.get(BASE + "/api/entries?bulan=2026-09&alat=KOMATSU&driver=RONALD&lokasi=PT%20GAS"))
cek("entries filter rentang", s.get(BASE + "/api/entries?dari=2026-05-01&sampai=2026-09-30&limit=5"))
cek("entries q", s.get(BASE + "/api/entries?q=JETTY&limit=5"))
cek("rekap", s.get(BASE + "/api/rekap"))
cek("rekap bulan", s.get(BASE + "/api/rekap?bulan=2026-09"))
cek("ringkasan", s.get(BASE + "/api/ringkasan"))
cek("log", s.get(BASE + "/api/log"))
cek("users", s.get(BASE + "/api/users"))
cek("backup", s.get(BASE + "/api/backup"))
cek("template excel", s.get(BASE + "/api/template/excel"))
cek("export excel", s.get(BASE + "/api/export/excel"))
cek("laporan wa", s.get(BASE + "/api/laporan/wa?bulan=2026-09"))
cek("laporan html", s.get(BASE + "/api/laporan/html?bulan=2026-09"))
cek("halaman /", s.get(BASE + "/"))
cek("halaman /m", s.get(BASE + "/m"))
cek("logout", s.post(BASE + "/api/logout"))

# master tambah/hapus
s2 = requests.Session()
s2.post(BASE + "/api/login", data={"username": "admin", "password": "admin"})
r = s2.post(BASE + "/api/master/driver", json={"nama": "UJI_SWEEP"})
cek("master driver tambah", r)
r2 = s2.get(BASE + "/api/master").json()
baru = [d for d in r2["driver"] if d["nama"] == "UJI_SWEEP"]
hasil.append(bool(baru))
print(f"{'OK  ' if baru else 'FAIL'} {'master driver terbaca di list':44s} {len(r2['driver'])} driver")
if baru:
    cek("master driver hapus", s2.delete(f"{BASE}/api/master/driver/{baru[0]['id']}"))
sisa = [d for d in s2.get(BASE + "/api/master").json()["driver"] if d["nama"] == "UJI_SWEEP"]
print("   sisa UJI_SWEEP (harus 0):", len(sisa))

print(f"\nRINGKAS: {sum(1 for h in hasil if h)}/{len(hasil)} OK")
