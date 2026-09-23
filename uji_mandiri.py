"""Uji berkas MANDIRI halaman HP (`/unduh/bbm-hp.html`).

Berkas ini dipakai kalau laptop mati / tidak ada WiFi, jadi isinya harus
selalu cocok dengan halaman HP yang sedang disajikan server. Dulu berkas ini
sempat tertinggal jauh setelah halaman HP dirombak.

    python uji_mandiri.py            (server harus jalan di 8791)
"""
import io
import json
import os
import re
import sys
import urllib.request
import http.cookiejar

BASE = "http://127.0.0.1:8791"
SIMBOL = ("pilihFileXl", "fileXlHP", "data-t=\"xl\"", "id=\"vXl\"",
          "id=\"iLiter\"", "pil-angka", "cekServerXl", "kunciBaru")


def ambil(url, data=None, cj=None):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    if data is not None:
        data = urllib.parse.urlencode(data).encode()
    with op.open(urllib.request.Request(url, data=data), timeout=30) as r:
        return r.status, r.read()


def main() -> int:
    import urllib.parse
    lulus = gagal = 0

    def cek(nama, syarat, info=""):
        nonlocal lulus, gagal
        if syarat:
            lulus += 1
            print(f"  [OK  ] {nama}")
        else:
            gagal += 1
            print(f"  [GAGAL] {nama} {info}")

    try:
        cj = http.cookiejar.CookieJar()
        st, _ = ambil(f"{BASE}/api/login", {"username": "admin", "password": "admin"}, cj)
        cek("login admin", st == 200, str(st))
        st, isi = ambil(f"{BASE}/unduh/bbm-hp.html", None, cj)
        cek("unduh berkas mandiri", st == 200, str(st))
        teks = isi.decode("utf-8", "replace")
        cek("berkas tidak kosong", len(teks) > 40000, f"{len(teks)} byte")

        # 1) tidak ada aset dari luar server (harus jalan tanpa WiFi)
        luar = re.findall(r'(?:src|href)="(https?://[^"]+)"', teks)
        luar = [u for u in luar if "127.0.0.1" not in u and "localhost" not in u]
        cek("tidak ada aset internet", not luar, str(luar[:3]))
        cek("gaya di-inline", "<style" in teks)
        cek("tidak merujuk /static/", "/static/" not in teks)

        # 2) fitur halaman HP terbaru ikut terbawa
        for s in SIMBOL:
            cek(f"berisi {s}", s in teks)
        cek("ada mode mandiri (file:)",
            "location.protocol==='file:'" in teks.replace(" ", ""))
        cek("ada tab Excel", 'data-t="xl"' in teks and 'id="vXl"' in teks)
        cek("ada input BBM di HP", 'id="iLiter"' in teks and 'id="iTanggal"' in teks)
        cek("pakai localStorage", "localStorage" in teks)
        cek("ada sw-registrasi tidak dipaksa (offline)",
            "serviceWorker" not in teks or "file:" not in teks.split("serviceWorker")[0][-200:])

        # 3) gaya perbaikan terbaru (bilah Simpan tidak menutupi kolom)
        cek("textarea tidak terjepit", "min-height:64px" in teks.replace(" ", "")
            or "min-height: 64px" in teks)
        cek("notifikasi di atas, bukan menutupi tombol",
            "safe-area-inset-top" in teks)

        # 4) ukuran wajar: kalau halaman HP berubah banyak, berkas ini basi
        halaman_st, halaman = ambil(f"{BASE}/m", None, cj)
        cek("halaman HP tersedia", halaman_st == 200, str(halaman_st))
        hp = halaman.decode("utf-8", "replace")
        fungsi_hp = set(re.findall(r"function\s+([A-Za-z0-9_]+)\s*\(", hp))
        hilang = sorted(f for f in fungsi_hp if f not in teks)
        cek("semua fungsi halaman HP ada di berkas mandiri", not hilang,
            f"hilang: {hilang[:6]}")
        id_hp = set(re.findall(r'id="([A-Za-z0-9_]+)"', hp))
        id_md = set(re.findall(r'id="([A-Za-z0-9_]+)"', teks))
        cek("semua id halaman HP ada di berkas mandiri", not (id_hp - id_md),
            f"hilang: {sorted(id_hp - id_md)[:6]}")

        # 5) simpan salinan untuk pemakaian nyata kalau diminta
        if "--simpan" in sys.argv:
            tujuan = os.path.join(os.path.expanduser("~"), "Documents", "BBM-HP-Input.html")
            with open(tujuan, "wb") as f:
                f.write(isi)
            print(f"  salinan ditulis: {tujuan} ({len(isi)} byte)")
    except Exception as e:  # noqa: BLE001
        print(f"  [GAGAL] tidak bisa menguji: {e}")
        gagal += 1

    print("\n" + "=" * 52)
    print(f"BERKAS MANDIRI {'SEGAR' if not gagal else 'BERMASALAH'} "
          f"({lulus} lulus / {gagal} gagal)")
    print("=" * 52)
    return 1 if gagal else 0


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    sys.exit(main())
