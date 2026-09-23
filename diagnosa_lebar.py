"""Ukur lebar elemen & leluhur di tab Rekap untuk cari sebab canvas lebar 0."""
import asyncio, json, os, subprocess, urllib.request
import websockets

BASE = "http://127.0.0.1:8791"
PORT = 9347
PROFIL = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "bbm-diag2")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def hj(p):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{p}", timeout=5) as r:
        return json.load(r)


class C:
    def __init__(s, w): s.w, s.i = w, 0
    async def kirim(s, m, **p):
        s.i += 1
        await s.w.send(json.dumps({"id": s.i, "method": m, "params": p}))
        while True:
            r = json.loads(await s.w.recv())
            if r.get("id") == s.i: return r
    async def ev(s, e):
        r = await s.kirim("Runtime.evaluate", expression=e, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r.get("result", {}): return "ERR:" + str(r["result"]["exceptionDetails"])[:200]
        return r["result"]["result"].get("value")


async def main():
    ch = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
                           f"--user-data-dir={PROFIL}", "--no-first-run", "about:blank"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        await asyncio.sleep(0.4)
        try:
            t = [x for x in hj("/json/list") if x.get("type") == "page"]
            if t: break
        except Exception: pass
    async with websockets.connect(t[0]["webSocketDebuggerUrl"], max_size=2**24) as ws:
        c = C(ws)
        await c.kirim("Page.enable")
        await c.kirim("Page.navigate", url=BASE + "/login")
        for _ in range(40):
            await asyncio.sleep(0.4)
            if await c.ev("!!document.getElementById('u')"): break
        await c.ev("document.getElementById('u').value='admin';document.getElementById('p').value='admin';"
                   "document.querySelector('form').dispatchEvent(new Event('submit',{cancelable:true}))")
        await asyncio.sleep(3)
        await c.ev("pindahTab('rekap')")
        await asyncio.sleep(3)
        print(await c.ev("""(()=>{
          const out=[]; let el=document.getElementById('grafik');
          while(el && out.length<6){
            const cs=getComputedStyle(el);
            out.push([el.tagName+(el.id?'#'+el.id:'')+(el.className?'.'+String(el.className).split(' ')[0]:''),
                      'cw='+el.clientWidth, 'ow='+el.offsetWidth, 'disp='+cs.display,
                      'pos='+cs.position, 'w='+cs.width]);
            el=el.parentElement;
          }
          return out.map(x=>x.join(' ')).join('\\n');
        })()"""))
        print("--- lebar jendela:", await c.ev("innerWidth + 'x' + innerHeight"))
    ch.terminate()


asyncio.run(main())
