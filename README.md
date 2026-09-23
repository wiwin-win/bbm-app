# BBM App

Aplikasi monitoring BBM / Solar dengan antarmuka neumorphism (soft UI).

## Fitur

- Input BBM masuk & keluar
- Rekap dan laporan
- Export Excel
- Multi-role user: maker, admin, fuelman, watcher
- Mode terang/gelap
- Aplikasi HP mandiri (offline)

## User Default (lokal/dev)

| Username | Password | Role |
|----------|----------|------|
| admin    | admin    | admin |
| maker    | maker    | maker |
| fuelman  | fuelman  | fuelman |
| watcher  | watcher  | watcher |

## Deploy ke Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/wiwin-win/bbm-app)

Atau manual via **New +** → **Web Service**:
- Runtime: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `BBM_HOST=0.0.0.0`
  - `BBM_PORT=10000`
  - `BBM_SEED=1` (untuk membuat user default pertama kali)
  - `BBM_DB=/tmp/bbm.db`

Catatan: di Render free tier, SQLite disimpan di `/tmp` dan akan hilang saat redeploy. Untuk produksi gunakan PostgreSQL.

## Aplikasi HP

Buka halaman `/unduh/bbm-hp.html` setelah login untuk mengunduh file HTML mandiri yang bisa dibuka di HP tanpa internet.

## Jalankan Lokal

```bash
pip install -r requirements.txt
python app.py
```

Buka http://localhost:8791
