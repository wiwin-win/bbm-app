"""Bandingkan export Excel aplikasi dengan file Excel asli user (per-nama kolom, bukan index)."""
import io
from datetime import datetime

import openpyxl
import requests

BASE = "http://127.0.0.1:8791"
ASLI = r"C:\Users\wiwin\Documents\BBM.xlsx"


def peta_kolom(ws, maks=8):
    """Cari baris header (yang memuat 'BULAN' + 'TANGGAL') lalu kembalikan {nama: index}."""
    for n, r in enumerate(ws.iter_rows(min_row=1, max_row=maks, values_only=True), start=1):
        if not r:
            continue
        teks = [str(c).strip().upper() for c in r if c is not None]
        if any("BULAN" in t for t in teks) and any("TANGGAL" in t for t in teks):
            return n, {str(c).strip().upper(): i for i, c in enumerate(r) if c is not None}
    raise RuntimeError("baris header tidak ditemukan")


def total(ws, peta, baris_head, nama, akhiri=True):
    """Jumlahkan kolom `nama` untuk baris data + sel TOTAL milik Excel (kalau ada)."""
    i = peta[nama]
    it = peta.get("TANGGAL", 1)
    jml, sel_total = 0.0, None
    for r in ws.iter_rows(min_row=baris_head + 1, values_only=True):
        if not r:
            continue
        kepala = str(r[0]).strip().upper()
        if kepala.startswith("TOTAL"):
            if len(r) > i and isinstance(r[i], (int, float)):
                sel_total = r[i]           # nilai yang tertulis di baris TOTAL file
            if akhiri:
                break
            continue
        if kepala.startswith("SISA STOK"):
            break
        tgl = r[it] if len(r) > it else None
        if isinstance(tgl, datetime):
            pass                           # file asli: tanggal bertipe datetime
        elif isinstance(tgl, str) and len(tgl.strip()) == 10 and tgl.count("-") == 2:
            pass                           # hasil ekspor: tanggal teks ISO
        else:
            continue                       # bukan baris data (judul/kosong/catatan)
        if len(r) > i and isinstance(r[i], (int, float)):
            jml += r[i]
    return round(jml, 2), (round(sel_total, 2) if sel_total is not None else None)


s = requests.Session()
s.post(BASE + "/api/login", data={"username": "admin", "password": "admin"})
bio = io.BytesIO(s.get(BASE + "/api/export/excel").content)

lama = openpyxl.load_workbook(ASLI, data_only=True)["BBM"]
baru = openpyxl.load_workbook(bio)["BBM"]
h1, p1 = peta_kolom(lama)
h2, p2 = peta_kolom(baru)
print("header asli  baris", h1, "| kolom:", len(p1))
print("header ekspor baris", h2, "| kolom:", len(p2))

print("\n" + "KOLOM".ljust(24), "EXCEL ASLI".rjust(15), "APLIKASI".rjust(15), "  COCOK")
pasangan = [("BBM / LTR (KELUAR)", "BBM / LTR (KELUAR)"),
            ("BBM MASUK (LTR)", "BBM MASUK (LTR)"),
            ("NILAI BBM KELUAR (RP)", "NILAI BBM KELUAR (RP)")]
semua_cocok = True
for ka, kb in pasangan:
    va_baris, va_total = total(lama, p1, h1, ka)
    vb, _ = total(baru, p2, h2, kb)
    # Excel asli: patokan = sel TOTAL yang ditulis user. Baris tanpa tanggal
    # (mis. 'BBM HILANG/BOCOR' 3.290 L) hanya ikut di sel TOTAL itu.
    va = va_total if va_total is not None else va_baris
    cocok = abs(va - vb) < 0.01
    semua_cocok &= cocok
    tag = "(sel TOTAL Excel)"
    print(ka.ljust(24), f"{va:>15,.0f}", f"{vb:>15,.0f}", ("  YA " + tag) if cocok else "  TIDAK")

sisa_lama = [r[p1["SISA STOK (LTR)"]] for r in lama.iter_rows(min_row=h1 + 1, values_only=True)
             if isinstance(r[p1["TANGGAL"]], datetime)][-1]
sisa_baru = [r[p2["SISA STOK (LTR)"]] for r in baru.iter_rows(min_row=h2 + 1, values_only=True)
             if isinstance(r[p2["SISA STOK (LTR)"]], (int, float))][-1]
cocok_sisa = abs(sisa_lama - sisa_baru) < 0.01
print("\nsisa stok terakhir  — asli:", sisa_lama, "| aplikasi:", sisa_baru,
      "->", "COCOK" if cocok_sisa else "BEDA")
print("baris: asli", lama.max_row, "| ekspor", baru.max_row)
print("\nHASIL:", "SEMUA COCOK" if (semua_cocok and cocok_sisa) else "ADA SELISIH")
