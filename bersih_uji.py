"""Hapus HANYA data uji (penanda UJI / nama alat yang keliru jadi tanggal).

Dipakai kalau uji unggah terputus di tengah sehingga sisa baris uji tertinggal
di database. Tidak menyentuh data asli.

    python bersih_uji.py
"""
import sqlite3

POLA_ENTRY = """upper(coalesce(no_lambung,'')) LIKE '%UJI%'
    OR upper(coalesce(driver,'')) LIKE '%UJI%'
    OR upper(coalesce(aktivitas,'')) LIKE '%UJI%'
    OR no_lambung LIKE '____-__-__'"""
POLA_MASTER = "upper({k}) LIKE '%UJI%' OR {k} LIKE '____-__-__'"

c = sqlite3.connect("bbm.db")
c.execute("PRAGMA foreign_keys=OFF")
print("--- sebelum ---")
for t in ("entries", "units", "drivers", "locations", "activities"):
    print(f"  {t:11s}", c.execute(f"select count(*) from {t}").fetchone()[0])

dibuang = c.execute(f"select count(*) from entries where {POLA_ENTRY}").fetchone()[0]
c.execute(f"delete from entries where {POLA_ENTRY}")
for t, k in (("units", "no_lambung"), ("drivers", "nama"),
             ("locations", "nama"), ("activities", "nama")):
    c.execute(f"delete from {t} where {POLA_MASTER.format(k=k)}")
c.commit()

print("--- sesudah ---")
for t in ("entries", "units", "drivers", "locations", "activities"):
    print(f"  {t:11s}", c.execute(f"select count(*) from {t}").fetchone()[0])
print(f"  baris uji dibuang: {dibuang}")
sisa = c.execute(f"select count(*) from entries where {POLA_ENTRY}").fetchone()[0]
print("BERSIH" if not sisa else f"MASIH ADA {sisa} SISA")
