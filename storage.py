"""Layer penyimpanan SQLite untuk aplikasi Monitoring BBM & Alat.

Jalankan app.py. DB default: bbm.db (bisa dioverride via env BBM_DB).
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("BBM_DB", str(BASE_DIR / "bbm.db"))
_LOCK = threading.Lock()

DEFAULT_SETTINGS = {
    "nama_instansi": "PT GEMBIRA ANGGUN SETIA",
    "periode": "September 2026",
    "batas_harian": "0",         # 0 = tanpa peringatan; kalau diisi, muncul warning saat pemakaian periode lewat batas (liter)
    "harga_default": "17200",
    "stok_awal": "0",
    "mata_uang": "Rp",
    # jenis/judul kolom yang boleh dipakai aplikasi
    "batas_harian": "0",          # 0 = tanpa peringatan batas
    "auto_refresh": "0",
}

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  username    TEXT NOT NULL UNIQUE,
  nama        TEXT NOT NULL DEFAULT '',
  role        TEXT NOT NULL CHECK (role IN ('admin','operator')) DEFAULT 'operator',
  pass_hash   TEXT NOT NULL,
  aktif       INTEGER NOT NULL DEFAULT 1,
  dibuat      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS units (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  no_lambung  TEXT NOT NULL UNIQUE,
  tipe        TEXT NOT NULL DEFAULT '',
  vendor      TEXT NOT NULL DEFAULT '',
  kapasitas   REAL NOT NULL DEFAULT 0,
  cost        REAL NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'Aktif'
);

CREATE TABLE IF NOT EXISTS drivers (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  nama    TEXT NOT NULL UNIQUE,
  jabatan TEXT NOT NULL DEFAULT 'OPT',
  telepon TEXT NOT NULL DEFAULT '',
  aktif   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS activities (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  nama TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS locations (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  nama TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS entries (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tanggal     TEXT NOT NULL,
  driver      TEXT NOT NULL DEFAULT '',
  no_lambung  TEXT NOT NULL DEFAULT '',
  aktivitas   TEXT NOT NULL DEFAULT '',
  lokasi      TEXT NOT NULL DEFAULT '',
  keluar      REAL NOT NULL DEFAULT 0,
  masuk       REAL NOT NULL DEFAULT 0,
  harga       REAL NOT NULL DEFAULT 0,
  hm_awal     REAL,
  hm_akhir    REAL,
  keterangan  TEXT NOT NULL DEFAULT '',
  jenis       TEXT NOT NULL DEFAULT 'BBM',   -- BBM | KOREKSI | HILANG
  user_id     INTEGER,
  kunci       TEXT,                         -- penanda unik dari HP (anti data dobel)
  dibuat      TEXT NOT NULL DEFAULT '',
  diubah      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_entries_tanggal ON entries(tanggal);
CREATE INDEX IF NOT EXISTS idx_entries_alat ON entries(no_lambung);
CREATE INDEX IF NOT EXISTS idx_entries_lokasi ON entries(lokasi);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS log_aktivitas (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  waktu  TEXT NOT NULL,
  user   TEXT NOT NULL DEFAULT '',
  aksi   TEXT NOT NULL DEFAULT '',
  detail TEXT NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------- koneksi
def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db() -> None:
    with _LOCK, connect() as con:
        con.executescript(SCHEMA)
        # pangkasan (patch) fitur baru
        kol = {r["name"] for r in con.execute("PRAGMA table_info(entries)")}
        if "kunci" not in kol:
            con.execute("ALTER TABLE entries ADD COLUMN kunci TEXT")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_kunci "
                    "ON entries(kunci) WHERE kunci IS NOT NULL")
        for k, v in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    if not any(u["role"] == "admin" for u in list_users()):
        add_user("admin", "admin", "admin", role="admin")


# ---------------------------------------------------------------- util
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _num(v, default=0.0) -> float:
    if v in (None, ""):
        return float(default)
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(".", "").replace(",", ".") if str(v).count(",") and str(v).count(".") == 0 \
        else str(v).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return float(default)


def tgl_iso(v) -> str:
    """Normalisasi berbagai format tanggal ke YYYY-MM-DD."""
    if v is None or v == "":
        return date.today().isoformat()
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (int, float)):           # tanggal serial Excel
        return (date(1899, 12, 30)).fromordinal(date(1899, 12, 30).toordinal() + int(v)).isoformat()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s[:10]


# ---------------------------------------------------------------- setting
def get_settings() -> dict:
    out = dict(DEFAULT_SETTINGS)
    with connect() as con:
        for r in con.execute("SELECT key,value FROM settings"):
            out[r["key"]] = r["value"]
    return out


def set_settings(data: dict) -> None:
    with _LOCK, connect() as con:
        for k, v in data.items():
            con.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (k, "" if v is None else str(v)),
            )


# ---------------------------------------------------------------- user
def _hash(password: str, salt: str = "") -> str:
    salt = salt or secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000)
    return f"pbkdf2${salt}${dk.hex()}"


def cek_password(password: str, stored: str) -> bool:
    try:
        _, salt, _ = stored.split("$", 2)
    except ValueError:
        return False
    return hmac.compare_digest(_hash(password, salt), stored)


def add_user(username: str, password: str, nama: str = "", role: str = "operator") -> int:
    with _LOCK, connect() as con:
        cur = con.execute(
            "INSERT INTO users(username,nama,role,pass_hash,aktif,dibuat) VALUES(?,?,?,?,1,?)",
            (username.strip().lower(), nama or username, role, _hash(password), _now()),
        )
        return cur.lastrowid


def set_password(user_id: int, password: str) -> None:
    with _LOCK, connect() as con:
        con.execute("UPDATE users SET pass_hash=? WHERE id=?", (_hash(password), user_id))


def list_users() -> list[dict]:
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT id,username,nama,role,aktif,dibuat FROM users ORDER BY username")]


def find_user(username: str):
    with connect() as con:
        r = con.execute("SELECT * FROM users WHERE username=? AND aktif=1",
                        ((username or "").strip().lower(),)).fetchone()
        return dict(r) if r else None


def update_user(user_id: int, nama=None, role=None, aktif=None) -> None:
    sets, vals = [], []
    for k, v in (("nama", nama), ("role", role), ("aktif", aktif)):
        if v is not None:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    vals.append(user_id)
    with _LOCK, connect() as con:
        con.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", vals)


def delete_user(user_id: int) -> None:
    with _LOCK, connect() as con:
        con.execute("DELETE FROM users WHERE id=? AND role<>'admin'", (user_id,))


# ---------------------------------------------------------------- log
def catat_log(aksi: str, detail: str = "", user: str = "") -> None:
    with _LOCK, connect() as con:
        con.execute("INSERT INTO log_aktivitas(waktu,user,aksi,detail) VALUES(?,?,?,?)",
                    (_now(), user, aksi, detail))


def list_log(limit: int = 200) -> list[dict]:
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM log_aktivitas ORDER BY id DESC LIMIT ?", (limit,))]


# ---------------------------------------------------------------- master
_MASTER = {
    "unit": ("units", ("no_lambung", "tipe", "vendor", "kapasitas", "cost", "status")),
    "driver": ("drivers", ("nama", "jabatan", "telepon", "aktif")),
    "activity": ("activities", ("nama",)),
    "location": ("locations", ("nama",)),
}


def master_list(kind: str) -> list[dict]:
    tabel, cols = _MASTER[kind]
    urut = "nama" if kind != "unit" else "no_lambung"
    with connect() as con:
        return [dict(r) for r in con.execute(f"SELECT * FROM {tabel} ORDER BY {urut}")]


def master_save(kind: str, data: dict, rec_id: int | None = None) -> int:
    tabel, cols = _MASTER[kind]
    vals = []
    for c in cols:
        v = data.get(c, "")
        if c in ("kapasitas", "cost"):
            v = _num(v)
        elif c == "aktif":
            v = 1 if str(v) in ("1", "True", "true", "on") else 0
        vals.append(v)
    with _LOCK, connect() as con:
        if rec_id:
            con.execute(f"UPDATE {tabel} SET {', '.join(c + '=?' for c in cols)} WHERE id=?",
                        vals + [rec_id])
            return rec_id
        cur = con.execute(f"INSERT OR IGNORE INTO {tabel}({','.join(cols)}) "
                          f"VALUES({','.join('?' * len(cols))})", vals)
        return cur.lastrowid or 0


def master_delete(kind: str, rec_id: int) -> None:
    tabel, _ = _MASTER[kind]
    with _LOCK, connect() as con:
        con.execute(f"DELETE FROM {tabel} WHERE id=?", (rec_id,))


def import_master(kind: str, rows: list[dict], kosongkan: bool = False) -> int:
    tabel, cols = _MASTER[kind]
    n = 0
    with _LOCK, connect() as con:
        if kosongkan:
            con.execute(f"DELETE FROM {tabel}")
        for r in rows:
            name = str(r.get(cols[0], "") or "").strip()
            if not name:
                continue
            vals = []
            for c in cols:
                v = r.get(c, "")
                if c in ("kapasitas", "cost"):
                    v = _num(v)
                elif c == "aktif":
                    v = 1
                elif c != cols[0]:
                    v = str(v or "").strip()
                vals.append(v)
            cur = con.execute(f"INSERT OR IGNORE INTO {tabel}({','.join(cols)}) "
                              f"VALUES({','.join('?' * len(cols))})", vals)
            n += cur.rowcount or 0
    return n


# ---------------------------------------------------------------- entries
ENTRY_FIELDS = ("tanggal", "driver", "no_lambung", "aktivitas", "lokasi",
                "keluar", "masuk", "harga", "hm_awal", "hm_akhir",
                "keterangan", "jenis")


def entry_simpan(data: dict, user_id: int | None = None, rec_id: int | None = None) -> int:
    # `kunci` = penanda unik dari HP. Kalau data yang sama dikirim dua kali
    # (sinyal putus setelah server menyimpan), yang kedua tidak digandakan.
    kunci = str(data.get("kunci") or "").strip()
    d = {k: data.get(k) for k in ENTRY_FIELDS}
    d["tanggal"] = tgl_iso(d["tanggal"])
    for k in ("driver", "no_lambung", "aktivitas", "lokasi", "keterangan"):
        d[k] = str(d.get(k) or "").strip()
    for k in ("keluar", "masuk", "harga"):
        d[k] = _num(d.get(k))
    for k in ("hm_awal", "hm_akhir"):
        d[k] = None if d.get(k) in (None, "") else _num(d[k])
    d["jenis"] = d.get("jenis") or "BBM"
    if not d["harga"]:
        d["harga"] = _num(get_settings().get("harga_default", 0))
    with _LOCK, connect() as con:
        if kunci and not rec_id:
            lama = con.execute("SELECT id FROM entries WHERE kunci=? LIMIT 1",
                               (kunci,)).fetchone()
            if lama:
                return lama["id"]          # sudah tersimpan -> jangan digandakan
        if rec_id:
            con.execute(
                f"UPDATE entries SET {', '.join(k + '=?' for k in ENTRY_FIELDS)}, diubah=? "
                "WHERE id=?",
                [d[k] for k in ENTRY_FIELDS] + [_now(), rec_id],
            )
            return rec_id
        cur = con.execute(
            f"INSERT INTO entries({','.join(ENTRY_FIELDS)},user_id,kunci,dibuat,diubah) "
            f"VALUES({','.join('?' * len(ENTRY_FIELDS))},?,?,?,?)",
            [d[k] for k in ENTRY_FIELDS] + [user_id, (kunci or None), _now(), _now()],
        )
        return cur.lastrowid


def entry_hapus(rec_id: int) -> None:
    with _LOCK, connect() as con:
        con.execute("DELETE FROM entries WHERE id=?", (rec_id,))


def entry_ambil(rec_id: int):
    with connect() as con:
        r = con.execute("SELECT * FROM entries WHERE id=?", (rec_id,)).fetchone()
        return dict(r) if r else None


def _where(f: dict):
    sql, args = " WHERE 1=1", []
    if f.get("dari"):
        sql += " AND tanggal>=?"
        args.append(tgl_iso(f["dari"]))
    if f.get("sampai"):
        sql += " AND tanggal<=?"
        args.append(tgl_iso(f["sampai"]))
    if f.get("bulan"):                      # YYYY-MM
        sql += " AND substr(tanggal,1,7)=?"
        args.append(str(f["bulan"])[:7])
    if f.get("alat"):
        sql += " AND no_lambung LIKE ?"
        args.append(f"%{f['alat']}%")
    if f.get("lokasi"):
        sql += " AND lokasi LIKE ?"
        args.append(f"%{f['lokasi']}%")
    if f.get("driver"):
        sql += " AND driver LIKE ?"
        args.append(f"%{f['driver']}%")
    if f.get("jenis"):
        sql += " AND jenis=?"
        args.append(f["jenis"])
    if f.get("q"):
        like = f"%{f['q']}%"
        sql += (" AND (driver LIKE ? OR no_lambung LIKE ? OR aktivitas LIKE ?"
                " OR lokasi LIKE ? OR keterangan LIKE ?)")
        args += [like] * 5
    return sql, args


def entry_daftar(f: dict | None = None, limit: int = 200, offset: int = 0) -> dict:
    f = f or {}
    sql, args = _where(f)
    awal = _num(get_settings().get("stok_awal", 0))
    with connect() as con:
        total = con.execute(f"SELECT COUNT(*) c FROM entries{sql}", args).fetchone()["c"]
        agg = con.execute(
            f"SELECT COALESCE(SUM(keluar),0) k, COALESCE(SUM(masuk),0) m,"
            f" COALESCE(SUM(keluar*harga),0) biaya FROM entries{sql}", args).fetchone()
        # Saldo berjalan dihitung atas SELURUH tabel dulu (window function),
        # baru difilter/di-limit. Kalau dihitung setelah limit, sisa stok baris
        # jadi ngawur karena saldo awalnya dianggap 0.
        rows = [dict(r) for r in con.execute(
            "WITH base AS (SELECT *, COALESCE(?,0) + SUM(COALESCE(masuk,0)-COALESCE(keluar,0))"
            " OVER (ORDER BY tanggal, id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)"
            f" AS sisa_stok FROM entries) SELECT * FROM base{sql}"
            " ORDER BY tanggal DESC, id DESC LIMIT ? OFFSET ?",
            [awal] + args + [limit, offset])]
    return {"total": total, "rows": rows,
            "total_keluar": agg["k"], "total_masuk": agg["m"], "total_biaya": agg["biaya"]}


def _hitung_sisa(rows: list[dict]) -> None:
    """Isi sisa_stok berjalan untuk daftar baris lengkap (tanpa limit)."""
    if not rows:
        return
    awal = _num(get_settings().get("stok_awal", 0))
    saldo = awal
    for r in sorted(rows, key=lambda r: (r["tanggal"], r["id"])):
        saldo += (r["masuk"] or 0) - (r["keluar"] or 0)
        r["sisa_stok"] = round(saldo, 2)


def semua_entries(f: dict | None = None) -> list[dict]:
    sql, args = _where(f or {})
    with connect() as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT * FROM entries{sql} ORDER BY tanggal, id", args)]
    awal = _num(get_settings().get("stok_awal", 0))
    saldo = awal
    for r in rows:
        saldo += (r["masuk"] or 0) - (r["keluar"] or 0)
        r["sisa_stok"] = round(saldo, 2)
    return rows


# Baris catatan khusus berasal dari Excel: kolom tanggal berisi teks
# ("BBM HILANG/BOCOR"), bukan pemakaian alat. Kalau ikut dijumlahkan,
# angka pemakaian jadi menyesatkan — jadi dipisah dari rekap pemakaian.
_CATATAN_SQL = " AND keterangan LIKE 'catatan khusus%'"
_BUKAN_CATATAN_SQL = " AND (keterangan IS NULL OR keterangan NOT LIKE 'catatan khusus%')"


def _kelompok(con, sql: str, args: list, kolom: str, batas: int | None,
              buang_kosong: bool = False) -> tuple[list[dict], dict]:
    """Ambil rekap per satu kolom. Kembalikan (baris teratas, sisa yang dipotong).

    Sisa yang dipotong ikut dihitung supaya baris TOTAL di layar tetap sama
    dengan total sebenarnya — bukan hanya jumlah 30 teratas.
    """
    syarat = f" AND trim(coalesce({kolom},'')) <> ''" if buang_kosong else ""
    mentah = [dict(r) for r in con.execute(
        f"SELECT {kolom} kunci, COALESCE(SUM(keluar),0) keluar,"
        f" COALESCE(SUM(keluar*harga),0) biaya, COUNT(*) baris FROM entries{sql}"
        f"{syarat} GROUP BY {kolom} ORDER BY keluar DESC, kunci", args)]
    # Kunci dikembalikan dengan nama kolom aslinya (no_lambung/driver/...)
    # supaya Excel, laporan, dan halaman tetap jalan tanpa diubah.
    semua = []
    for r in mentah:
        r[kolom] = r.pop("kunci")
        semua.append(r)
    if batas is None or len(semua) <= batas:
        return semua, {"n": 0, "keluar": 0.0, "biaya": 0.0, "total_grup": len(semua)}
    teratas, sisa = semua[:batas], semua[batas:]
    return teratas, {
        "n": len(sisa),
        "keluar": round(sum(x["keluar"] for x in sisa), 2),
        "biaya": round(sum(x["biaya"] for x in sisa), 2),
        "total_grup": len(semua),
    }


def rekap(f: dict | None = None) -> dict:
    f = f or {}
    sql, args = _where(f)
    with connect() as con:
        t = con.execute(
            f"SELECT COALESCE(SUM(keluar),0) keluar, COALESCE(SUM(masuk),0) masuk,"
            f" COUNT(*) baris, COALESCE(SUM(keluar*harga),0) biaya,"
            f" COALESCE(AVG(NULLIF(harga,0)),0) harga_rata,"
            f" MIN(tanggal) t0, MAX(tanggal) t1 FROM entries{sql}", args).fetchone()
        # --- pemakaian sah (catatan khusus dikeluarkan) ---
        pakai_sql, pakai_args = sql + _BUKAN_CATATAN_SQL, args
        p = con.execute(
            f"SELECT COALESCE(SUM(keluar),0) keluar, COUNT(*) baris,"
            f" COALESCE(SUM(keluar*harga),0) biaya FROM entries{pakai_sql}",
            pakai_args).fetchone()
        per_alat, sisa_alat = _kelompok(con, pakai_sql, pakai_args, "no_lambung", 30)
        per_lokasi, sisa_lokasi = _kelompok(con, pakai_sql, pakai_args, "lokasi", None)
        # driver kosong dibuang: baris seperti "BBM HILANG/BOCOR" tidak punya
        # driver, jadi tidak boleh muncul sebagai "(kosong)" di rekap driver.
        per_driver, sisa_driver = _kelompok(con, pakai_sql, pakai_args, "driver", 30,
                                            buang_kosong=True)
        per_aktivitas, sisa_aktivitas = _kelompok(con, pakai_sql, pakai_args,
                                                  "aktivitas", 20, buang_kosong=True)
        harian = [dict(r) for r in con.execute(
            f"SELECT tanggal, COALESCE(SUM(keluar),0) keluar, COALESCE(SUM(masuk),0) masuk,"
            f" COALESCE(SUM(keluar*harga),0) biaya FROM entries{sql}"
            f" GROUP BY tanggal ORDER BY tanggal", args)]
        catatan = [dict(r) for r in con.execute(
            f"SELECT id, tanggal, no_lambung, keterangan, driver, lokasi,"
            f" COALESCE(keluar,0) keluar, COALESCE(masuk,0) masuk,"
            f" COALESCE(keluar*harga,0) biaya FROM entries{sql}{_CATATAN_SQL}"
            f" ORDER BY tanggal, id", args)]
    stok_awal = _num(get_settings().get("stok_awal", 0))
    keluar_catatan = round(sum(c["keluar"] for c in catatan), 2)
    biaya_catatan = round(sum(c["biaya"] for c in catatan), 2)

    # --- sisa stok bersifat SALDO BERJALAN, bukan hitungan periode.
    # Kalau hanya bulan yang difilter yang dihitung, September (masuk 0) jadi
    # "sisa stok -6.624 L" walau saldo sebenarnya masih 691 L. Jadi jumlahkan
    # seluruh mutasi sampai akhir periode yang diminta.
    batas = t["t1"] or date.today().isoformat()
    if f.get("dari") or f.get("sampai"):
        batas = tgl_iso(f.get("sampai") or batas) or batas
    s_sql, s_args = _where({k: v for k, v in f.items()
                            if k not in ("dari", "sampai", "bulan")})
    s_sql += " AND substr(tanggal,1,10)<=?"
    s_args = s_args + [batas[:10]]
    with connect() as con:
        kum = con.execute(
            f"SELECT COALESCE(SUM(masuk),0) masuk, COALESCE(SUM(keluar),0) keluar"
            f" FROM entries{s_sql}", s_args).fetchone()
    return {
        "stok_awal": stok_awal,
        "total_masuk": t["masuk"],
        "total_keluar": t["keluar"],
        # saldo berjalan sampai akhir periode (bukan hanya mutasi periode ini)
        "sisa_stok": round(stok_awal + kum["masuk"] - kum["keluar"], 2),
        "sisa_periode_ini": round(stok_awal + t["masuk"] - t["keluar"], 2),
        "sisa_basis": batas[:10],
        "kumulatif_masuk": kum["masuk"],
        "kumulatif_keluar": kum["keluar"],
        "total_biaya": t["biaya"],
        "harga_rata": t["harga_rata"],
        "baris": t["baris"],
        "periode_awal": t["t0"],
        "periode_akhir": t["t1"],
        # pemakaian alat saja (tanpa baris catatan seperti BBM HILANG/BOCOR)
        "pemakaian_keluar": p["keluar"],
        "pemakaian_biaya": p["biaya"],
        "pemakaian_baris": p["baris"],
        "catatan_keluar": keluar_catatan,
        "catatan_biaya": biaya_catatan,
        "catatan": catatan,
        "per_alat": per_alat, "sisa_alat": sisa_alat,
        "per_lokasi": per_lokasi, "sisa_lokasi": sisa_lokasi,
        "per_driver": per_driver, "sisa_driver": sisa_driver,
        "per_aktivitas": per_aktivitas, "sisa_aktivitas": sisa_aktivitas,
        "harian": harian,
    }


def ringkasan_cepat() -> dict:
    bulan = date.today().strftime("%Y-%m")
    r = rekap({"bulan": bulan})
    return {
        "bulan": bulan,
        "keluar": r["total_keluar"],
        "masuk": r["total_masuk"],
        "sisa_stok": r["sisa_stok"],
        "biaya": r["total_biaya"],
        "baris": r["baris"],
    }


def seed_demo() -> int:
    """Isi contoh 5 baris supaya tampilan tidak kosong saat pertama buka."""
    contoh = [
        {"tanggal": date.today().isoformat(), "driver": "RONALD", "no_lambung": "LOADER (GAS 009)",
         "aktivitas": "MAINTENANCE JALAN", "lokasi": "PT GAS", "keluar": 150, "masuk": 0, "harga": 17200},
        {"tanggal": date.today().isoformat(), "driver": "A.JUMRIN", "no_lambung": "PC 200 XCMG (EXCA 001 GAS)",
         "aktivitas": "JETTY AMI", "lokasi": "PT GAS", "keluar": 105, "masuk": 0, "harga": 17200},
        {"tanggal": date.today().isoformat(), "driver": "DANI", "no_lambung": "TANGKI BBM",
         "aktivitas": "BBM MASUK", "lokasi": "PT GAS", "keluar": 0, "masuk": 4900, "harga": 17200},
    ]
    n = 0
    for c in contoh:
        entry_simpan(c, user_id=1)
        n += 1
    return n
