"""Uji nyata fitur unggah Excel DARI HALAMAN HP — pakai Chrome DevTools Protocol.

Yang diuji bukan cuma API-nya, tapi jalur yang dipakai operator: buka /m,
login, isi alamat server, buka tab Excel, lalu kirim file .xlsx ke server.

    python uji_hp_unggah.py        (server harus jalan di 8791)
"""
import asyncio
import base64
import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets
from openpyxl import Workbook

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://127.0.0.1:8791"
PORT = 9341
PROFIL = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "bbm-cdp-unggah")
BASE_DIR = Path(__file__).resolve().parent
PENANDA = "UJI-HP-UNGGAH"
GAGAL = 0


def cek(nama, syarat, info=""):
    global GAGAL
    if not syarat:
        GAGAL += 1
    print(f"  [{'OK  ' if syarat else 'GAGAL'}] {nama} {info}")


def http_json(jalur):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{jalur}", timeout=10) as r:
        return json.load(r)


async def tunggu_chrome(detik=25):
    for _ in range(detik * 4):
        try:
            return http_json("/json/version")
        except Exception:
            time.sleep(0.25)
    return None


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.no = 0

    async def kirim(self, metode, **param):
        self.no += 1
        mid = self.no
        await self.ws.send(json.dumps({"id": mid, "method": metode, "params": param}))
        while True:
            pesan = json.loads(await self.ws.recv())
            if pesan.get("id") == mid:
                if "error" in pesan:
                    raise RuntimeError(f"{metode}: {pesan['error']}")
                return pesan.get("result", {})

    async def eval(self, ekspresi, tunggu=False):
        r = await self.kirim("Runtime.evaluate", expression=ekspresi, returnByValue=True,
                             awaitPromise=tunggu)
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:300])
        return r.get("result", {}).get("value")


def bikin_berkas_uji() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "BBM"
    ws.append(["TANGGAL", "NAMA OPT / DRIVER", "ALAT / NO LAMBUNG", "DESKRIPSI AKTIVITAS",
               "LOKASI KEGIATAN", "BBM / LTR (KELUAR)", "BBM / LTR (MASUK)", "HARGA/LITER",
               "KETERANGAN"])
    ws.append(["2026-09-22", PENANDA, "UJI-HP-01", "UJI DARI HP", "UJI LOKASI", 33.5, "", 17200, ""])
    p = BASE_DIR / f"uji-hp-{PENANDA.lower()}.xlsx"
    wb.save(p)
    return p


def hitung_uji():
    kon = sqlite3.connect(str(BASE_DIR / "bbm.db"))
    n = kon.execute("SELECT COUNT(*) FROM entries WHERE driver=?", (PENANDA,)).fetchone()[0]
    kon.close()
    return n


async def utama():
    berkas = bikin_berkas_uji()
    print("=" * 52)
    print("UJI UNGGAH EXCEL DARI HALAMAN HP (/m)")
    print("=" * 52)
    print(f"  berkas uji: {berkas.name} ({berkas.stat().st_size} B)")

    chrome = subprocess.Popen([
        CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFIL}", "--no-first-run", "--no-default-browser-check",
        "--window-size=412,915", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not await tunggu_chrome():
        print("  Chrome gagal start"); return 1

    tab = [t for t in http_json("/json/list") if t.get("type") == "page"][0]
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=30 * 1024 * 1024) as ws:
        c = CDP(ws)
        await c.kirim("Page.enable")
        await c.kirim("Runtime.enable")

        # --- login lewat halaman HP
        await c.kirim("Page.navigate", url=f"{BASE}/login?m=1")
        for _ in range(40):                     # tunggu elemen login siap
            await asyncio.sleep(0.4)
            if await c.eval("!!document.getElementById('u')"):
                break
        ada = await c.eval("!!document.getElementById('u')")
        cek("halaman login HP terbuka", ada,
            await c.eval("location.href + ' | ' + document.readyState + ' | ' + document.title"))
        if not ada:
            return 1
        await c.eval("document.getElementById('u').value='admin';"
                     "document.getElementById('p').value='admin';"
                     "document.querySelector('form').dispatchEvent(new Event('submit',{cancelable:true}))")
        await asyncio.sleep(3)
        url = await c.eval("location.href")
        cek("login HP berhasil masuk /m", "/m" in (url or ""), str(url))

        # --- perlengkapan halaman baru ada?
        cek("kotak unggah Excel ada di HP",
            await c.eval("!!document.getElementById('fileXlHP')"))
        cek("info server ada di HP",
            await c.eval("!!document.getElementById('infoServerXl')"))
        cek("fungsi unggahExcelHP terdaftar",
            await c.eval("typeof unggahExcelHP === 'function'"))
        cek("fungsi bukaTemplate terdaftar",
            await c.eval("typeof bukaTemplate === 'function'"))

        # --- buka tab Excel dan isi alamat server
        await c.eval("document.querySelector('.tab a[data-t=\"xl\"]').click()")
        await asyncio.sleep(1)
        await c.eval(f"simpanLS(K_SERVER, '{BASE}')")
        await c.eval("cekServerXl()")
        await asyncio.sleep(2)
        info = await c.eval("document.getElementById('infoServerXl').textContent")
        cek("info server tampil (bukan error)", info and "tidak terjangkau" not in info, str(info)[:90])

        # --- kirim berkas lewat jalur yang dipakai operator: File + FormData
        data = base64.b64encode(berkas.read_bytes()).decode()
        skrip = f"""
        (async () => {{
          const b = Uint8Array.from(atob('{data}'), ch => ch.charCodeAt(0));
          const f = new File([b], '{berkas.name}', {{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}});
          const dt = new DataTransfer(); dt.items.add(f);
          const inp = document.getElementById('fileXlHP');
          inp.files = dt.files;
          await unggahExcelHP(inp);
          return document.getElementById('hasilUnggahHP').textContent;
        }})()
        """
        hasil = await c.eval(skrip, tunggu=True)
        cek("halaman HP melaporkan berhasil", hasil and "Berhasil" in hasil, str(hasil)[:120])
        n = hitung_uji()
        cek("1 baris uji masuk ke database server", n == 1, f"{n} baris")

        # --- bersihkan
        kon = sqlite3.connect(str(BASE_DIR / "bbm.db"))
        kon.execute("DELETE FROM entries WHERE driver=?", (PENANDA,))
        kon.execute("DELETE FROM drivers WHERE nama=?", (PENANDA,))
        kon.execute("DELETE FROM units WHERE no_lambung='UJI-HP-01'")
        kon.commit()
        kon.close()
        sisa = hitung_uji()
        cek("data uji dibersihkan", sisa == 0, f"{sisa} sisa")

    berkas.unlink(missing_ok=True)
    chrome.terminate()
    print("\n" + "=" * 52)
    print("UNGGAH DARI HP BERJALAN" if not GAGAL else f"GAGAL ({GAGAL})")
    print("=" * 52)
    return 1 if GAGAL else 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(utama()))
    finally:
        os.system("taskkill /F /IM chrome.exe >nul 2>&1")
