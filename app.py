"""Monitoring BBM & Alat - FastAPI + SQLite.

Jalankan:  python app.py          -> PC   http://127.0.0.1:8791
           jalankan_hp.bat        -> PC + HP (WiFi sama)  /m
"""
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import excel
import report
import storage as db

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
STATIC = BASE / "static"
STATIC.mkdir(exist_ok=True)
UPLOAD = BASE / "upload"
UPLOAD.mkdir(exist_ok=True)

SESI: dict[str, dict] = {}          # token -> {id, username, nama, role}
COOKIE = "bbm_sesi"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    if os.environ.get("BBM_SEED", "0") == "1":
        db.seed_demo()
    yield


app = FastAPI(title="Monitoring BBM & Alat", version="1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def _lan_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def pengguna(request: Request):
    return SESI.get(request.cookies.get(COOKIE, ""))


def perlu_login(request: Request):
    u = pengguna(request)
    if not u:
        raise HTTPException(status_code=401, detail="Belum login")
    return u


def perlu_admin(request: Request):
    u = perlu_login(request)
    if u["role"] != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin")
    return u


def _html(nama: str, request: Request, **ctx):
    ctx.setdefault("u", pengguna(request))
    ctx.setdefault("s", db.get_settings())
    ctx.setdefault("versi", app.version)
    r = templates.TemplateResponse(request, nama, ctx)
    # Selalu ambil halaman utama dari server, jangan dari cache PWA lama
    # supaya perombakan terbaru tampil.
    if nama in ("index.html", "mobile.html", "login.html"):
        r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
    return r


# ---------------------------------------------------------------- halaman
@app.get("/", response_class=HTMLResponse)
def beranda(request: Request):
    if not pengguna(request):
        return RedirectResponse("/login")
    return _html("index.html", request)


@app.get("/m", response_class=HTMLResponse)
def mobile(request: Request):
    if not pengguna(request):
        return RedirectResponse("/login?m=1")
    return _html("mobile.html", request)


@app.get("/login", response_class=HTMLResponse)
def halaman_login(request: Request, m: int = 0):
    kembali = "/m" if m else "/"
    return _html("login.html", request, kembali=kembali)


@app.post("/api/login")
def api_login(request: Request, username: str = Form(...), password: str = Form(...)):
    u = db.find_user(username)
    if not u or not db.cek_password(password, u["pass_hash"]):
        return JSONResponse({"ok": False, "pesan": "Username / password salah"}, status_code=401)
    token = secrets.token_urlsafe(24)
    SESI[token] = {"id": u["id"], "username": u["username"], "nama": u["nama"], "role": u["role"]}
    db.catat_log("login", f"{u['username']} masuk", u["username"])
    resp = JSONResponse({"ok": True, "role": u["role"]})
    resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 12)
    return resp


@app.post("/api/logout")
def api_logout(request: Request):
    tok = request.cookies.get(COOKIE, "")
    SESI.pop(tok, None)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/api/saya")
def api_saya(request: Request):
    u = perlu_login(request)
    return {"ok": True, "user": u, "settings": db.get_settings()}


# ---------------------------------------------------------------- entries
@app.get("/api/ringkasan")
def api_ringkasan(request: Request):
    perlu_login(request)
    return {"ok": True, "data": db.ringkasan_cepat(), "lan": _lan_ip()}


@app.get("/api/entries")
def api_entries(request: Request, dari: str = "", sampai: str = "", bulan: str = "",
                alat: str = "", lokasi: str = "", driver: str = "", q: str = "",
                jenis: str = "", limit: int = 200, offset: int = 0):
    perlu_login(request)
    f = {"dari": dari, "sampai": sampai, "bulan": bulan, "alat": alat,
         "lokasi": lokasi, "driver": driver, "q": q, "jenis": jenis}
    return {"ok": True, **db.entry_daftar(f, limit=limit, offset=offset)}


@app.post("/api/entries")
def api_entry_baru(request: Request, data: dict = Body(...)):
    u = perlu_login(request)
    if not (data.get("keluar") or data.get("masuk")):
        raise HTTPException(400, "Isi minimal salah satu: BBM keluar atau BBM masuk")
    rid = db.entry_simpan(data, user_id=u["id"])
    db.catat_log("tambah", f"#{rid} {data.get('no_lambung','')} keluar={data.get('keluar',0)} "
                           f"masuk={data.get('masuk',0)}", u["username"])
    return {"ok": True, "id": rid}


@app.put("/api/entries/{rid}")
def api_entry_ubah(rid: int, request: Request, data: dict = Body(...)):
    u = perlu_login(request)
    if not db.entry_ambil(rid):
        raise HTTPException(404, "Data tidak ditemukan")
    db.entry_simpan(data, user_id=u["id"], rec_id=rid)
    db.catat_log("ubah", f"#{rid}", u["username"])
    return {"ok": True, "id": rid}


@app.delete("/api/entries/{rid}")
def api_entry_hapus(rid: int, request: Request):
    u = perlu_login(request)
    if u["role"] != "admin" and not os.environ.get("BBM_HAPUS_BEBAS") == "1":
        raise HTTPException(403, "Hanya admin yang bisa menghapus")
    db.entry_hapus(rid)
    db.catat_log("hapus", f"#{rid}", u["username"])
    return {"ok": True}


# ---------------------------------------------------------------- rekap
@app.get("/api/rekap")
def api_rekap(request: Request, dari: str = "", sampai: str = "", bulan: str = "",
              alat: str = "", lokasi: str = "", driver: str = "", q: str = "", jenis: str = ""):
    perlu_login(request)
    f = {"dari": dari, "sampai": sampai, "bulan": bulan, "alat": alat,
         "lokasi": lokasi, "driver": driver, "q": q, "jenis": jenis}
    return {"ok": True, "data": db.rekap(f)}


# ---------------------------------------------------------------- master
@app.get("/api/master")
def api_master(request: Request):
    perlu_login(request)
    return {"ok": True, "unit": db.master_list("unit"), "driver": db.master_list("driver"),
            "activity": db.master_list("activity"), "location": db.master_list("location")}


@app.post("/api/master/{kind}")
def api_master_simpan(kind: str, request: Request, data: dict = Body(...)):
    u = perlu_login(request)
    if kind not in ("unit", "driver", "activity", "location"):
        raise HTTPException(400, "Jenis master tidak dikenal")
    rid = db.master_save(kind, data, rec_id=data.get("id"))
    db.catat_log(f"master-{kind}", str(data.get("nama") or data.get("no_lambung") or ""), u["username"])
    return {"ok": True, "id": rid}


@app.delete("/api/master/{kind}/{rid}")
def api_master_hapus(kind: str, rid: int, request: Request):
    u = perlu_admin(request)
    if kind not in ("unit", "driver", "activity", "location"):
        raise HTTPException(400, "Jenis master tidak dikenal")
    db.master_delete(kind, rid)
    db.catat_log(f"master-{kind}-hapus", str(rid), u["username"])
    return {"ok": True}


# ---------------------------------------------------------------- user & setting
@app.get("/api/users")
def api_users(request: Request):
    perlu_admin(request)
    return {"ok": True, "rows": db.list_users()}


@app.post("/api/users")
def api_user_baru(request: Request, data: dict = Body(...)):
    u = perlu_admin(request)
    username = str(data.get("username", "")).strip()
    if not username or not data.get("password"):
        raise HTTPException(400, "Username dan password wajib")
    if db.find_user(username):
        raise HTTPException(400, "Username sudah dipakai")
    uid = db.add_user(username, str(data["password"]), str(data.get("nama", "")),
                      str(data.get("role", "operator")))
    db.catat_log("user-baru", username, u["username"])
    return {"ok": True, "id": uid}


@app.put("/api/users/{uid}")
def api_user_ubah(uid: int, request: Request, data: dict = Body(...)):
    u = perlu_admin(request)
    if data.get("password"):
        db.set_password(uid, str(data["password"]))
    db.update_user(uid, nama=data.get("nama"), role=data.get("role"),
                   aktif=data.get("aktif"))
    db.catat_log("user-ubah", str(uid), u["username"])
    return {"ok": True}


@app.delete("/api/users/{uid}")
def api_user_hapus(uid: int, request: Request):
    u = perlu_admin(request)
    db.delete_user(uid)
    db.catat_log("user-hapus", str(uid), u["username"])
    return {"ok": True}


@app.post("/api/settings")
def api_settings(request: Request, data: dict = Body(...)):
    u = perlu_admin(request)
    db.set_settings(data)
    db.catat_log("setting", ", ".join(data.keys()), u["username"])
    return {"ok": True, "settings": db.get_settings()}


# ---------------------------------------------------------------- import / export
@app.post("/api/import/excel")
async def api_import_excel(request: Request, file: UploadFile = File(...),
                           kosongkan: int = Form(0)):
    u = perlu_admin(request)
    nama = f"upload_{datetime.now():%Y%m%d_%H%M%S}_{file.filename}"
    path = UPLOAD / nama
    path.write_bytes(await file.read())
    try:
        hasil = excel.impor_excel(str(path), kosongkan=bool(kosongkan))
    except Exception as e:                     # noqa: BLE001
        raise HTTPException(400, f"Gagal membaca file: {e}") from e
    db.catat_log("import", f"{file.filename} -> {hasil}", u["username"])
    return {"ok": True, **hasil}


@app.get("/api/export/excel")
def api_export_excel(request: Request, dari: str = "", sampai: str = "", bulan: str = "",
                     alat: str = "", lokasi: str = "", driver: str = "", q: str = "",
                     jenis: str = ""):
    perlu_login(request)
    f = {"dari": dari, "sampai": sampai, "bulan": bulan, "alat": alat,
         "lokasi": lokasi, "driver": driver, "q": q, "jenis": jenis}
    data = db.semua_entries(f)
    rk = db.rekap(f)
    bio = excel.ekspor_excel(data, rk, db.get_settings())
    nama = f"BBM_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return Response(
        content=bio.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nama}"'},
    )


@app.get("/api/template/excel")
def api_template(request: Request):
    perlu_login(request)
    bio = excel.template_kosong()
    return Response(
        content=bio.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="template_bbm.xlsx"'},
    )


@app.get("/unduh/bbm-hp.html")
def api_unduh_mandiri(request: Request):
    """Satu file HTML berisi seluruh aplikasi input HP.

    Semua aset (gaya + xlsx.js + logo) di-inline supaya file ini jalan dari
    memori HP, tanpa server dan tanpa WiFi — dipakai kalau laptop sedang mati.
    """
    perlu_login(request)
    html = (BASE / "templates" / "mobile.html").read_text(encoding="utf-8")
    skrip = (STATIC / "xlsx.js").read_text(encoding="utf-8")
    gaya = (STATIC / "gaya-hp.css").read_text(encoding="utf-8")
    import base64
    logo_b64 = base64.b64encode((STATIC / "logo.png").read_bytes()).decode()
    fav_b64 = base64.b64encode((STATIC / "icon-192.png").read_bytes()).decode()
    aset = {
        '<link rel="stylesheet" href="/static/gaya-hp.css">':
            "<style>\n" + gaya.replace("/static/logo.png", f"data:image/png;base64,{logo_b64}") + "\n</style>",
        '<link rel="manifest" href="/manifest.webmanifest">': "",
        '<link rel="icon" href="/static/favicon.ico" sizes="any">':
            f'<link rel="icon" href="data:image/png;base64,{fav_b64}">',
        '<link rel="apple-touch-icon" href="/static/icon-192.png">':
            f'<link rel="apple-touch-icon" href="data:image/png;base64,{fav_b64}">',
        '<script src="/static/xlsx.js"></script>':
            "<script>\n" + skrip + "\n</" + "script>",
        "navigator.serviceWorker.register('/sw.js')": "(function(){})",
    }
    for a, b in aset.items():
        html = html.replace(a, b)
    # logo di dalam HTML (kalau ada tag img) juga di-inline
    html = html.replace('src="/static/logo.png"', f'src="data:image/png;base64,{logo_b64}"')
    nama = "bbm-hp-mandiri.html"
    return Response(content=html, media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nama}"'})


@app.get("/api/laporan/html", response_class=HTMLResponse)
def api_laporan(request: Request, dari: str = "", sampai: str = "", bulan: str = "",
                alat: str = "", lokasi: str = "", driver: str = ""):
    perlu_login(request)
    f = {"dari": dari, "sampai": sampai, "bulan": bulan, "alat": alat,
         "lokasi": lokasi, "driver": driver}
    return HTMLResponse(report.laporan_html(db.rekap(f), db.semua_entries(f), db.get_settings(), f))


@app.get("/api/laporan/wa")
def api_laporan_wa(request: Request, dari: str = "", sampai: str = "", bulan: str = "",
                   alat: str = "", lokasi: str = "", driver: str = "", simpan: int = 0):
    perlu_login(request)
    f = {"dari": dari, "sampai": sampai, "bulan": bulan, "alat": alat,
         "lokasi": lokasi, "driver": driver}
    teks = report.laporan_teks(db.rekap(f), db.get_settings(), f)
    if simpan:
        out = BASE / "laporan_terakhir.txt"
        out.write_text(teks, encoding="utf-8")
    return {"ok": True, "teks": teks}


@app.get("/api/log")
def api_log(request: Request, limit: int = 200):
    perlu_admin(request)
    return {"ok": True, "rows": db.list_log(limit)}


@app.get("/api/backup")
def api_backup(request: Request):
    perlu_admin(request)
    folder = BASE / "backup"
    folder.mkdir(exist_ok=True)
    tujuan = folder / f"bbm-{datetime.now():%Y%m%d-%H%M%S}.db"
    with db.connect() as con:
        con.execute("VACUUM INTO ?", (str(tujuan),))
    return {"ok": True, "file": tujuan.name}


# ---------------------------------------------------------------- PWA
@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest",
                        media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("BBM_HOST", "127.0.0.1")
    port = int(os.environ.get("BBM_PORT", "8791"))
    ip = _lan_ip()
    print("=" * 62)
    print("  MONITORING BBM & ALAT")
    print(f"  PC   : http://127.0.0.1:{port}")
    print(f"  HP   : http://{ip}:{port}/m   (WiFi sama)")
    print("  Login: admin / admin  (ganti setelah masuk!)")
    print("  Stop : CTRL+C")
    print("=" * 62)
    uvicorn.run(app, host=host, port=port, log_level="warning")
