"""Ukur posisi nyata elemen di halaman HP lewat Chrome DevTools Protocol.

Menjawab pertanyaan "apakah textarea KETERANGAN tertutup bilah Simpan yang
menempel di bawah?" dengan angka, bukan perkiraan dari gambar.

    python ukur_hp.py
"""
import asyncio
import json
import os
import subprocess
import time
import urllib.request

import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://127.0.0.1:8791"
PORT = 9361
PROFIL = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "bbm-ukur-hp")


def http_json(jalur: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{jalur}", timeout=10) as r:
        return json.load(r)


def tunggu_cdp():
    for _ in range(80):
        try:
            return http_json("/json/list")
        except Exception:
            time.sleep(0.4)
    raise SystemExit("CDP tidak siap di port " + str(PORT))


async def main():
    p = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={PROFIL}", "--window-size=412,915", "--no-first-run",
         "--disable-gpu", "--hide-scrollbars", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tabs = [t for t in tunggu_cdp() if t["type"] == "page"]
    assert tabs, "tidak ada tab halaman"
    ws = await websockets.connect(tabs[0]["webSocketDebuggerUrl"], max_size=8 * 1024 * 1024)
    n = [0]

    async def cmd(m, **kw):
        n[0] += 1
        await ws.send(json.dumps({"id": n[0], "method": m, "params": kw}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == n[0]:
                if "error" in r:
                    raise RuntimeError(f"{m}: {r['error']}")
                return r.get("result", {})

    async def js(e):
        r = await cmd("Runtime.evaluate", expression=e, returnByValue=True,
                      awaitPromise=True)
        return r.get("result", {}).get("value")

    try:
        await cmd("Page.enable")
        await cmd("Runtime.enable")
        # login lewat API (halaman /m adalah halaman terproteksi)
        await cmd("Page.navigate", url=f"{BASE}/login")
        await asyncio.sleep(2)
        status = await js("fetch('/api/login',{method:'POST',body:new URLSearchParams("
                          "{username:'admin',password:'admin'})}).then(r=>r.status)")
        print("login status :", status)
        if status != 200:
            print("GAGAL: tidak bisa login, ukuran dibatalkan")
            return 1
        await cmd("Emulation.setDeviceMetricsOverride", width=412, height=915,
                  deviceScaleFactor=2, mobile=True)
        await cmd("Page.navigate", url=f"{BASE}/m")
        await asyncio.sleep(3.5)
        print("url          :", await js("location.href"))
        ada = await js("!!document.getElementById('vIn') && !!document.getElementById('iKet')")
        print("vIn + iKet   :", ada)
        if not ada:
            print("GAGAL: elemen input tidak ditemukan -> ukuran tidak sah")
            return 1

        async def ukur(label):
            return await js("""(()=>{
              const ket=document.getElementById('iKet');
              const ak=document.querySelector('.aksi');
              if(!ket||!ak) return JSON.stringify({err:'elemen tak ada'});
              const rk=ket.getBoundingClientRect(), ra=ak.getBoundingClientRect();
              const gaya=getComputedStyle(ket);
              return JSON.stringify({
                ketAtas:Math.round(rk.y), ketBawah:Math.round(rk.bottom),
                ketTinggi:Math.round(rk.height), minTinggi:gaya.minHeight,
                aksiAtas:Math.round(ra.y), aksiTinggi:Math.round(ra.height),
                tertutup: rk.bottom > ra.y + 1,
                sisaGulir: document.documentElement.scrollHeight - innerHeight
              });})()""")

        print("posisi awal  :", await ukur("awal"))
        await js("window.scrollTo(0, document.documentElement.scrollHeight)")
        await asyncio.sleep(0.8)
        akhir = await ukur("bawah")
        print("setelah gulir:", akhir)
        tertutup = await js("""(()=>{
          const ak=document.querySelector('.aksi');
          const ra=ak.getBoundingClientRect();
          return JSON.stringify([...document.querySelectorAll('#vIn input,#vIn textarea,#vIn .nilai')]
            .filter(el=>{const r=el.getBoundingClientRect(); return r.bottom>ra.y+1 && r.height>0;})
            .map(el=>el.id||el.className));})()""")
        print("tertutup bilah:", tertutup)
        d = json.loads(akhir) if akhir and "err" not in akhir else {}
        if d.get("tertutup") or (tertutup and tertutup != "[]"):
            print("STATUS: MASIH TERTUTUP -> perlu perbaikan")
            return 1
        print("STATUS: AMAN, tidak ada kolom tertutup bilah Simpan")
        return 0
    finally:
        await ws.close()
        p.terminate()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
