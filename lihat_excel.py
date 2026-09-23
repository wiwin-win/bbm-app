"""Lihat struktur kolom & sisa stok dari Excel asli user."""
import collections
from datetime import datetime

import openpyxl

wb = openpyxl.load_workbook(r"C:\Users\wiwin\Documents\BBM.xlsx", data_only=True)
ws = wb["BBM"]
rows = list(ws.iter_rows(values_only=True))
print("kolom:", rows[1])

bulan_harga = collections.defaultdict(collections.Counter)
pesan_urut = []
for n, r in enumerate(rows[2:], start=3):
    if not isinstance(r[1], datetime):
        continue
    bulan = r[1].strftime("%Y-%m")
    if r[9]:
        bulan_harga[bulan][r[9]] += 1
    if len(pesan_urut) < 3 or n > len(rows) - 4:
        pesan_urut.append((n, r[1].date().isoformat(), r[3], r[7], r[8], r[9]))

for b in sorted(bulan_harga):
    print(b, bulan_harga[b].most_common(3))

print("\ncontoh baris (no, tanggal, alat, keluar, sisa_stok_excel, harga):")
for x in pesan_urut:
    print(" ", x)
