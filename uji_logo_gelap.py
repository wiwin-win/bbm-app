# -*- coding: utf-8 -*-
"""Uji visual logo terang/gelap: screenshot CDP + analisis piksel per elemen.

Untuk tiap halaman (login, PC, HP) x tema (terang, gelap):
- pasang localStorage bbm-tema, reload,
- ambil bounding box <img> logo,
- screenshot, crop area logo, cek warna outline & flame.
"""
import asyncio
import json
import os
import sys

from PIL import Image

from ambil_pratinjau import BASE, CDP, PROFIL, PORT, http_json, tunggu_chrome

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAGAL = 0


def cek(nama, syarat, info=""):
    global GAGAL
    if not syarat:
        GAGAL += 1
    print(f"  [{'OK  ' if syarat else 'GAGAL'}] {nama} {info}")


def analisis_crop(path, kotak, gelap):
    """Return (ada_outline, ada_flame, rata2_sudut) dari crop area logo."""
    im = Image.open(path).convert("RGB").crop((
        int(kotak["x"]), int(kotak["y"]),
        int(kotak["x"] + kotak["width"]), int(kotak["y"] + kotak["height"])))
    w, h = im.size
    px = list(im.getdata())
    outline = flame = 0
    for r, g, b in px:
        if gelap and 170 <= r <= 230 and 170 <= g <= 230 and 180 <= b <= 240 and b >= r:
            outline += 1                      # abu terang #C8D0DC-ish
        if not gelap and r < 110 and b > r and g < 110:
            outline += 1                      # navy gelap
        if r > 170 and g < 150 and b < 90:
            flame += 1                        # merah-oranye
    sudut = [im.getpixel(p) for p in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2))]
    return outline, flame, sudut


async def sesi(c, halaman, nama, selektor, gelap):
    path = os.path.join(BASE_DIR, f"uji-logo-{nama}.png")
    await c.eval(
        "localStorage.setItem('bbm-tema', %s)" % ("'gelap'" if gelap else "'terang'"))
    await c.buka(BASE + halaman, jeda=3.0)
    state = await c.eval(
        "(()=>{const i=document.querySelector(%s);"
        "const k=i?i.getBoundingClientRect():null;"
        "return JSON.stringify({gelap:document.body.classList.contains('gelap'),"
        "src:i?i.getAttribute('src'):'-',ok:i?i.naturalWidth>0:false,"
        "dpr:window.devicePixelRatio,"
        "kotak:k?{x:k.x,y:k.y,width:k.width,height:k.height}:null})})()"
        % json.dumps(selektor))
    st = json.loads(state)
    r = await c.kirim("Page.captureScreenshot", format="png")
    with open(path, "wb") as f:
        import base64
        f.write(base64.b64decode(r["data"]))
    print(f"\n[{nama} | {'GELAP' if gelap else 'TERANG'}]")
    cek("body.gelap benar", st["gelap"] == gelap)
    cek("src logo benar",
        st["src"].endswith("-gelap.png") if gelap else
        (st["src"].endswith(".png") and "gelap" not in st["src"]),
        st["src"])
    cek("logo termuat", st["ok"])
    if st["kotak"]:
        k = {n: v * st.get("dpr", 1) for n, v in st["kotak"].items()}
        outline, flame, sudut = analisis_crop(path, k, gelap)
        cek("warna outline tema-gelap" if gelap else "warna outline terang",
            outline > 30, f"{outline} px")
        cek("flame merah-oranye utuh", flame > 20, f"{flame} px")
        if nama == "login":
            cek("tak ada kotak putih JPG (sudut transparan)",
                all(not (p[0] > 235 and p[1] > 235 and p[2] > 235) for p in sudut),
                str(sudut[0]))
    else:
        cek("elemen img ketemu", False)


async def main():
    if os.path.exists(PROFIL):
        import subprocess
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", PROFIL], capture_output=True)
    from ambil_pratinjau import CHROME
    import subprocess
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
        "--disable-extensions", "--hide-scrollbars", f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFIL}", "--window-size=1460,1050", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not await tunggu_chrome():
            print("GAGAL: Chrome tidak hidup")
            return 1
        import websockets.asyncio.client as wsc
        v = http_json("/json/version")
        async with wsc.connect(v["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024) as bw:
            async def perintah(mid, metode, **param):
                await bw.send(json.dumps({"id": mid, "method": metode, "params": param}))
                while True:
                    p = json.loads(await bw.recv())
                    if p.get("id") == mid:
                        return p.get("result", {})
            t = await perintah(1, "Target.createTarget", url="about:blank")
            ws_url = next(i["webSocketDebuggerUrl"] for i in http_json("/json/list")
                          if i.get("id") == t["targetId"])
            async with wsc.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
                c = CDP(ws)
                await c.kirim("Page.enable")
                await c.kirim("Runtime.enable")
                # login dulu biar / dan /m tidak ditendang
                await c.buka(BASE + "/login", jeda=2.0)
                await c.eval(
                    "fetch('/api/login',{method:'POST',body:new URLSearchParams("
                    "{username:'admin',password:'admin'})}).then(r=>r.status)",
                    tunggu_promise=True)
                await sesi(c, "/login", "login-terang", ".masuk-plat img", False)
                await sesi(c, "/login", "login-gelap", ".masuk-plat img", True)
                await c.kirim("Emulation.setDeviceMetricsOverride", width=412,
                              height=915, deviceScaleFactor=2, mobile=True)
                await sesi(c, "/m", "hp-terang", ".plat img", False)
                await sesi(c, "/m", "hp-gelap", ".plat img", True)
                await c.kirim("Emulation.setDeviceMetricsOverride", width=1460,
                              height=1050, deviceScaleFactor=1, mobile=False)
                await sesi(c, "/", "pc-terang", ".plat img", False)
                await sesi(c, "/", "pc-gelap", ".plat img", True)
        print("\n" + "=" * 50)
        print("LOGO TERANG/GELAP", "BERES" if not GAGAL else f"({GAGAL} gagal)")
        return 0 if not GAGAL else 1
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
