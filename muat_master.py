"""Muat master data (alat, driver, lokasi, aktivitas) dari file BBM.xlsx milik user."""
import sys
from pathlib import Path

import openpyxl

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import storage as db  # noqa: E402

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\wiwin\Documents\BBM.xlsx")

BUKAN_ALAT = {"BBM HILANG/BOCOR", "TOTAL", "SISA STOK (LTR)", ""}


def main() -> None:
    db.init_db()
    wb = openpyxl.load_workbook(SRC, data_only=True)
    # --- master alat dari sheet MASTER (kolom B..F mulai baris 11)
    unit = []
    if "MASTER" in wb.sheetnames:
        ws = wb["MASTER"]
        for r in ws.iter_rows(min_row=11, values_only=True):
            nama = (r[1] or "").strip() if isinstance(r[1], str) else None
            if not nama or nama.upper() in ("NO LAMBUNG", "DAFTAR ALAT / UNIT"):
                continue
            unit.append({"no_lambung": nama, "tipe": r[2] or "", "cost": r[3] or 0,
                         "vendor": r[4] or "", "kapasitas": r[5] or 0,
                         "status": r[6] or "Aktif"})
    # --- dari sheet BBM sebagai pelengkap
    driver, lokasi, aktivitas, alat_bbm = set(), set(), set(), set()
    if "BBM" in wb.sheetnames:
        ws = wb["BBM"]
        for r in ws.iter_rows(min_row=3, values_only=True):
            tgl = r[1]
            if tgl in (None, ""):               # kolom tanggal harus terisi
                continue
            if isinstance(tgl, str) and not any(ch.isdigit() for ch in tgl):
                continue                        # lewati baris judul/kosong
            alat = (r[3] or "").strip(); drv = (r[2] or "").strip()
            if alat and alat.upper() not in BUKAN_ALAT:
                alat_bbm.add(alat)
            if drv and drv.upper() not in BUKAN_ALAT:
                driver.add(drv)
            if isinstance(r[5], str) and r[5].strip():
                lokasi.add(r[5].strip())
            if isinstance(r[4], str) and r[4].strip():
                aktivitas.add(r[4].strip())
    tambahan = [{"no_lambung": a, "status": "Aktif"} for a in sorted(alat_bbm)
                if a not in {u["no_lambung"] for u in unit}]
    n1 = db.import_master("unit", unit + tambahan)
    n2 = db.import_master("driver", [{"nama": d} for d in sorted(driver)])
    n3 = db.import_master("location", [{"nama": x} for x in sorted(lokasi)])
    n4 = db.import_master("activity", [{"nama": x} for x in sorted(aktivitas)])
    print(f"Muat master: {n1} alat, {n2} driver, {n3} lokasi, {n4} aktivitas -> {db.DB_PATH}")


if __name__ == "__main__":
    main()
