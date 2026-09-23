"""Diagnosa tab Rekap di browser: tangkap error JS + ukuran canvas + isi API.

Dipakai untuk mencari penyebab grafik tidak tampil.

    python diagnosa_rekap.py
"""
import asyncio, json, os, subprocess, sys, time, urllib.request

BASE = os.environ.get("BBM_BASE", "http://127.0.0.1:8791")
PORT = 9345
PROFIL = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "bbm-diag")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

import websockets


def http_json(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=5) as r:
        return json.load(r)


class CDP:
    def __init__(self, ws):
        self.ws, self.id = ws, 0
    async def kirim(self, method, **p):
        self.id += 1
        await self.ws.send(json.dumps({"id": self.id, "method": method, "params": p}))
        while True:
            m = json.loads(await self.ws.recv())
            if m.get("id") == self.id:
                return m
    async def eval(self, expr):
        r = await self.kirim("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r.get("result", {}):
            return {"__error__": str(r["result"]["exceptionDetails"])[:400]}
        return r["result"]["result"].get("value")


async def main():
    chrome = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
                               f"--user-data-dir={PROFIL}", "--no-first-run", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        await asyncio.sleep(0.4)
        try:
            tabs = [t for t in http_json("/json/list") if t.get("type") == "page"]
            if tabs:
                break
        except Exception:
            pass
    async with websockets.connect(tabs[0]["webSocketDebuggerUrl"], max_size=2**24) as ws:
        c = CDP(ws)
        await c.kirim("Page.enable"); await c.kirim("Runtime.enable"); await c.kirim("Log.enable")
        errs = []
        try:
            await c.kirim("Page.navigate", url=BASE + "/login")
            for _ in range(40):
                await asyncio.sleep(0.4)
                if await c.eval("!!document.getElementById('u')"):
                    break
            await c.eval("document.getElementById('u').value='admin';"
                         "document.getElementById('p').value='admin';"
                         "document.querySelector('form').dispatchEvent(new Event('submit',{cancelable:true}))")
            await asyncio.sleep(3)
            print("halaman:", await c.eval("location.pathname"))

            # API rekap langsung
            d = await c.eval("fetch('/api/rekap').then(r=>r.json()).then(j=>({ok:j.ok,"
                             "harian:(j.data.harian||[]).length,keluar:j.data.total_keluar}))")
            print("API /api/rekap  :", d)

            await c.eval("pindahTab('rekap')")
            await asyncio.sleep(3)
            print("canvas          :", await c.eval(
                "(()=>{const cv=document.getElementById('grafik');return cv?{ada:true,"
                "cw:cv.clientWidth,ch:cv.clientHeight,w:cv.width,h:cv.height}:{ada:false}})()"))
            print("error JS        :", await c.eval("window.__err||'(tidak ada)'"))
            print("isi tab rekap   :", (await c.eval("document.getElementById('tab-rekap').innerText") or "")[:200].replace("\n", " | "))
        finally:
            pass
    chrome.terminate()


asyncio.run(main())
