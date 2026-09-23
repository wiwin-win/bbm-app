"""Ambil screenshot halaman NYATA (sudah login) lewat Chrome DevTools Protocol.

Chrome headless biasa sering gagal menulis file; cara ini mengontrol Chrome
langsung (Page.captureScreenshot) sehingga hasilnya pasti.

    python ambil_pratinjau.py
"""
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://127.0.0.1:8791"
PORT = 9339
PROFIL = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "bbm-cdp")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import websockets


def http_json(jalur: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{jalur}", timeout=10) as r:
        return json.load(r)


async def tunggu_chrome(detik=25):
    for _ in range(detik * 4):
        try:
            v = http_json("/json/version")
            return v
        except Exception:
            time.sleep(0.25)
    return None


class CDP:
    """Pembungkus sederhana untuk satu tab."""

    def __init__(self, ws):
        self.ws = ws
        self.no = 0
        self.tunggu = {}

    async def kirim(self, metode: str, **param):
        self.no += 1
        mid = self.no
        await self.ws.send(json.dumps({"id": mid, "method": metode, "params": param}))
        while True:
            pesan = json.loads(await self.ws.recv())
            if pesan.get("id") == mid:
                if "error" in pesan:
                    raise RuntimeError(f"{metode}: {pesan['error']}")
                return pesan.get("result", {})

    async def eval(self, ekspresi: str, tunggu_promise: bool = False):
        r = await self.kirim("Runtime.evaluate", expression=ekspresi,
                             returnByValue=True, awaitPromise=tunggu_promise)
        return r.get("result", {}).get("value")

    async def buka(self, url: str, jeda: float = 2.5):
        await self.kirim("Page.navigate", url=url)
        await asyncio.sleep(jeda)

    async def shot(self, nama: str) -> str:
        r = await self.kirim("Page.captureScreenshot", format="png", captureBeyondViewport=True)
        keluar = os.path.join(BASE_DIR, nama)
        with open(keluar, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return keluar


async def main():
    if os.path.exists(PROFIL):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", PROFIL], capture_output=True)
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
        "--disable-extensions", "--hide-scrollbars", f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFIL}", "--window-size=1460,1050", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        v = await tunggu_chrome()
        if not v:
            print("GAGAL: Chrome tidak menjawab di port", PORT)
            return 1
        print("Chrome:", v.get("Browser"))
        # buat tab baru lewat browser target
        import websockets.asyncio.client as wsc
        async with wsc.connect(v["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024) as bw:
            async def perintah(mid, metode, **param):
                await bw.send(json.dumps({"id": mid, "method": metode, "params": param}))
                while True:
                    p = json.loads(await bw.recv())
                    if p.get("id") == mid:
                        return p.get("result", {})
            t = await perintah(1, "Target.createTarget", url="about:blank")
            tid = t["targetId"]
            t2 = await perintah(2, "Target.getTargetInfo", targetId=tid)
            ws_url = None
            for info in http_json("/json/list"):
                if info.get("id") == tid:
                    ws_url = info["webSocketDebuggerUrl"]
            if not ws_url:
                print("GAGAL: tidak dapat URL tab")
                return 1

        async with wsc.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
            c = CDP(ws)
            await c.kirim("Page.enable")
            await c.kirim("Runtime.enable")

            # 1) login
            await c.buka(BASE + "/login")
            print("pratinjau-login.png  ->", os.path.basename(await c.shot("pratinjau-login.png")))
            hasil = await c.eval(
                "fetch('/api/login',{method:'POST',body:new URLSearchParams("
                "{username:'admin',password:'admin'})}).then(r=>r.status)", tunggu_promise=True)
            print("login status:", hasil)

            # 2) halaman PC (dashboard)
            await c.buka(BASE + "/", jeda=3.5)
            judul = await c.eval("document.querySelector('header h1')?.textContent || document.title")
            print("h1 PC:", judul)
            print("pratinjau-pc.png    ->", os.path.basename(await c.shot("pratinjau-pc.png")))

            # 3) halaman HP (ukuran layar HP)
            await c.kirim("Emulation.setDeviceMetricsOverride", width=412, height=915,
                          deviceScaleFactor=2, mobile=True)
            await c.buka(BASE + "/m", jeda=3.5)
            print("pratinjau-hp.png    ->", os.path.basename(await c.shot("pratinjau-hp.png")))

            # tab Excel di HP (tab terakhir)
            await c.eval("document.querySelector('.tab a[data-t=\"xl\"]').click()")
            await asyncio.sleep(2.5)
            print("pratinjau-hp-excel.png ->", os.path.basename(await c.shot("pratinjau-hp-excel.png")))

            # tab Data di PC + tab Rekap, untuk cek tabel & grafik
            await c.kirim("Emulation.setDeviceMetricsOverride", width=1460, height=1050,
                          deviceScaleFactor=1, mobile=False)
            await c.buka(BASE + "/", jeda=3.5)
            await c.eval("pindahTab('data')")
            await asyncio.sleep(2.0)
            print("pratinjau-pc-data.png ->", os.path.basename(await c.shot("pratinjau-pc-data.png")))
            await c.eval("pindahTab('rekap')")
            await asyncio.sleep(2.0)
            print("pratinjau-pc-rekap.png ->", os.path.basename(await c.shot("pratinjau-pc-rekap.png")))

        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
