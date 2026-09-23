"""Uji regresi: file Excel ASLI perusahaan masih terbaca benar setelah perubahan.

Impor dijalankan ke database SEMENTARA (tidak menyentuh bbm.db), lalu hasilnya
dibandingkan dengan angka acuan yang sudah terbukti benar:
    680 baris, termasuk catatan khusus "BBM HILANG/BOCOR" 3.290 L.

    python uji_impor_asli.py
"""
import os
import sqlite3
import sys
import tempfile

DB = os.path.join(tempfile.gettempdir(), "uji_impor_asli.db")
ASLI = r"C:\Users\wiwin\Documents\BBM.xlsx"

if os.path.exists(DB):
    os.remove(DB)
os.environ["BBM_DB"] = DB

import excel  # noqa: E402  (harus setelah BBM_DB diset)
import storage as db  # noqa: E402

GAGAL = 0


def cek(nama, syarat, info=""):
    global GAGAL
    if not syarat:
        GAGAL += 1
    print(f"  [{'OK  ' if syarat else 'GAGAL'}] {nama} {info}")


print("=" * 52)
print(f"IMPOR FILE ASLI: {os.path.basename(ASLI)}")
print("=" * 52)
db.init_db()
hasil = excel.impor_excel(ASLI)
print(f"  hasil: {hasil}\n")

with sqlite3.connect(DB) as con:
    n = con.execute("select count(*) from entries").fetchone()[0]
    khusus = con.execute(
        "select count(*) from entries where keterangan like '%BBM HILANG/BOCOR%'").fetchone()[0]
    ltr_khusus = con.execute(
        "select coalesce(sum(keluar),0) from entries where keterangan like '%BBM HILANG/BOCOR%'"
    ).fetchone()[0]
    kosong_alat = con.execute(
        "select count(*) from entries where trim(coalesce(no_lambung,''))=''").fetchone()[0]
    nama_tanggal = con.execute(
        "select count(*) from entries where no_lambung like '____-__-__'").fetchone()[0]
    masuk = con.execute("select coalesce(sum(masuk),0) from entries").fetchone()[0]
    keluar = con.execute("select coalesce(sum(keluar),0) from entries").fetchone()[0]
    unit = con.execute("select count(*) from units").fetchone()[0]
    driver = con.execute("select count(*) from drivers").fetchone()[0]

cek("terbaca 680 baris", n == 680, f"{n} baris")
cek("catatan khusus BBM HILANG/BOCOR ada", khusus >= 1, f"{khusus} baris")
cek("liter catatan khusus 3.290 L", abs(ltr_khusus - 3290) < 1, f"{ltr_khusus} L")
cek("tidak ada nama alat kosong", kosong_alat == 0, f"{kosong_alat} baris")
cek("tidak ada nama alat berupa tanggal", nama_tanggal == 0, f"{nama_tanggal} baris")
cek("total masuk > 0", masuk > 0, f"{masuk:,.0f} L")
cek("total keluar > 0", keluar > 0, f"{keluar:,.0f} L")
cek("master alat terisi", unit >= 182, f"{unit} alat")
cek("master driver terisi", driver >= 153, f"{driver} driver")
cek("rentang periode Mei-Sep 2026", hasil["dari"][:7] == "2026-05" and hasil["sampai"][:7] == "2026-09",
    f"{hasil['dari']} s/d {hasil['sampai']}")

print("\n" + "=" * 52)
print("FILE ASLI MASIH TERBACA BENAR" if not GAGAL else f"GAGAL ({GAGAL})")
print("=" * 52)
db_tutup = None                      # lepas koneksi supaya file bisa dihapus
try:
    os.remove(DB)
except PermissionError:
    print(f"  (catatan: file sementara {DB} tidak bisa dihapus, tidak masalah)")
sys.exit(1 if GAGAL else 0)
