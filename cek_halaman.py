"""Cek konsistensi halaman PC: id JS<->HTML, fungsi onclick, sintaks JS.

Dijalankan tanpa browser. Kalau ada id yang dipakai JS tapi tidak ada di HTML,
halaman akan error "null" saat diklik — cek ini menangkapnya lebih awal.
"""
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
GAGAL = 0


def cek(nama, syarat, info=""):
    global GAGAL
    if not syarat:
        GAGAL += 1
    print(f"  [{'OK  ' if syarat else 'GAGAL'}] {nama} {info}")


html = (BASE / "templates" / "index.html").read_text(encoding="utf-8")
mob = (BASE / "templates" / "mobile.html").read_text(encoding="utf-8")

print("=" * 52)
print("UJI HALAMAN PC (index.html)")
print("=" * 52)

ids_js = set(re.findall(r"\$\('([A-Za-z0-9_]+)'\)", html))
ids_js |= set(re.findall(r"getElementById\('([A-Za-z0-9_]+)'\)", html))
ids_html = set(re.findall(r'id="([A-Za-z0-9_]+)"', html))
hilang = sorted(ids_js - ids_html)
cek("semua id yang dipakai JS ada di HTML", not hilang, f"hilang: {hilang}")

fungsi = set(re.findall(r"function\s+([A-Za-z0-9_]+)\s*\(", html))
dipanggil = set(re.findall(r'on(?:click|change|submit)="([A-Za-z0-9_]+)\(', html))
kurang = sorted(dipanggil - fungsi)
cek("semua onclick/onchange punya fungsinya", not kurang, f"tak terdefinisi: {kurang}")

# sintaks JS: potong isi <script> terakhir lalu cek pakai node
skrip = re.findall(r"<script>(.*?)</script>", html, re.S)
if skrip:
    tmp = BASE / "_tmp_index.js"
    tmp.write_text(skrip[-1], encoding="utf-8")
    r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
    cek("sintaks JS halaman PC valid", r.returncode == 0, r.stderr.strip()[:200])
    tmp.unlink(missing_ok=True)

print("\n-> fitur yang diminta")
cek("fokus input BBM: bidang Liter besar", 'class="besar"' in html and 'id="iLiter"' in html)
cek("pilihan jenis keluar/masuk", 'id="segKeluar"' in html and 'id="segMasuk"' in html)
cek("angka cepat (20/50/100/200 L)", "pil-angka" in html and 'id="literCepat"' in html)
cek("panel Perbarui Data dari Excel", "Perbarui Data dari Excel" in html)
cek("zona lepas file (drag & drop)", 'id="zona"' in html and "dataTransfer" in html)
cek("input file .xlsx/.xlsm", 'accept=".xlsx,.xlsm"' in html)
cek("tombol Unduh Template Excel", "/api/template/excel" in html)
cek("panel Unduh Data ke Excel", "Unduh Data ke Excel" in html)
cek("unduh excel pakai filter", "unduhExcel" in html and "/api/export/excel" in html)
cek("opsi kosongkan data lama", 'id="uKosongkan"' in html)
cek("hasil unggah ditampilkan ke user", 'id="hasilUnggah"' in html and "hasil-unggah" in html)

# id/fungsi/JS di halaman HP juga diperiksa — dulu hanya HTML yang dicek
ids_js_hp = set(re.findall(r"\$\('([A-Za-z0-9_]+)'\)", mob))
ids_js_hp |= set(re.findall(r"getElementById\('([A-Za-z0-9_]+)'\)", mob))
ids_html_hp = set(re.findall(r'id="([A-Za-z0-9_]+)"', mob))
hilang_hp = sorted(ids_js_hp - ids_html_hp)
cek("HP: semua id yang dipakai JS ada di HTML", not hilang_hp, f"hilang: {hilang_hp}")

fungsi_hp = set(re.findall(r"function\s+([A-Za-z0-9_]+)\s*\(", mob))
fungsi_hp |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(", mob))
dipanggil_hp = set(re.findall(r'on(?:click|change|submit)="(?:[\w.]+\.)?([A-Za-z0-9_]+)\(', mob))
kurang_hp = sorted(dipanggil_hp - fungsi_hp)
cek("HP: semua onclick/onchange punya fungsinya", not kurang_hp, f"tak terdefinisi: {kurang_hp}")

skrip_hp = re.findall(r"<script>(.*?)</script>", mob, re.S)
if skrip_hp:
    tmp = BASE / "_tmp_hp.js"
    tmp.write_text(skrip_hp[-1], encoding="utf-8")
    r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
    cek("HP: sintaks JS valid", r.returncode == 0, r.stderr.strip()[:200])
    tmp.unlink(missing_ok=True)
cek("HP: bisa unggah Excel ke server", 'id="fileXlHP"' in mob and "/api/import/excel" in mob)
cek("HP: info data di server", 'id="infoServerXl"' in mob and "/api/ringkasan" in mob)
cek("HP: bisa unduh template", "bukaTemplate" in mob and "/api/template/excel" in mob)

print("\n-> halaman HP (mobile.html) setelah perbaikan")
cek("tab Excel tetap ada", 'data-t="xl"' in mob and 'id="vXl"' in mob)
cek("angka cepat di HP", 'id="literCepat"' in mob and "pil-angka" in mob)
cek("hitungan nilai real-time", "hitungNilai" in mob and 'id="kNilai"' in mob)
cek("tombol simpan tetap paling menonjol", 'class="btn ok"' in mob)

print("\n" + "=" * 52)
print("GAGAL" if GAGAL else "HALAMAN PC & HP RAPI", f"({GAGAL} gagal)")
print("=" * 52)
sys.exit(1 if GAGAL else 0)
