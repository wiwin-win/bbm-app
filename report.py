"""Pembuat laporan: teks WhatsApp + HTML siap cetak."""
import html
from datetime import datetime


def _rp(v) -> str:
    try:
        return "Rp " + f"{float(v):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def _ltr(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "0"
    return f"{f:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")


def _tgl_id(s: str) -> str:
    bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d")
        return f"{d.day} {bulan[d.month]} {d.year}"
    except (ValueError, TypeError):
        return s or "-"


def _judul_periode(f: dict) -> str:
    if f.get("dari") or f.get("sampai"):
        return f"{_tgl_id(f.get('dari') or '')} s/d {_tgl_id(f.get('sampai') or '')}".strip()
    if f.get("bulan"):
        b = str(f["bulan"])[:7]
        try:
            d = datetime.strptime(b + "-01", "%Y-%m-%d")
            bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
                     "Agustus", "September", "Oktober", "November", "Desember"]
            return f"{bulan[d.month]} {d.year}"
        except ValueError:
            return b
    return "Semua Periode"


def laporan_teks(rk: dict, setting: dict, f: dict | None = None) -> str:
    f = f or {}
    L = []
    L.append("*LAPORAN BBM / SOLAR*")
    L.append(setting.get("nama_instansi", ""))
    L.append(f"Periode: {_judul_periode(f)}")
    L.append("")
    L.append(f"Stok awal      : {_ltr(rk['stok_awal'])} L")
    L.append(f"BBM masuk      : {_ltr(rk['total_masuk'])} L")
    L.append(f"BBM keluar     : {_ltr(rk['total_keluar'])} L")
    L.append(f"Sisa stok      : {_ltr(rk['sisa_stok'])} L"
             + (f" (saldo s/d {rk['sisa_basis']})" if rk.get("sisa_basis") else ""))
    L.append(f"Biaya keluar   : {_rp(rk['total_biaya'])}")
    L.append(f"Jumlah catatan : {rk['baris']} baris")
    # Baris catatan (mis. "BBM HILANG/BOCOR") tetap mengurangi stok tapi bukan
    # pemakaian alat — sebutkan terpisah supaya angka rincian bisa ditelusuri.
    if rk.get("catatan"):
        L.append("")
        L.append(f"*Pemakaian alat: {_ltr(rk.get('pemakaian_keluar', 0))} L "
                 f"({_rp(rk.get('pemakaian_biaya', 0))})*")
        L.append(f"Catatan khusus : {_ltr(rk.get('catatan_keluar', 0))} L "
                 f"({_rp(rk.get('catatan_biaya', 0))}) dari {len(rk['catatan'])} baris")
        for c in rk["catatan"]:
            L.append(f"  - {c.get('no_lambung') or '-'} ({c.get('tanggal') or '-'}): "
                     f"{_ltr(c.get('keluar', 0))} L")
    L.append("")
    if rk.get("per_lokasi"):
        L.append("*Rincian per Lokasi*")
        for r in rk["per_lokasi"]:
            L.append(f"- {r['lokasi'] or '(kosong)'}: {_ltr(r['keluar'])} L ({_rp(r['biaya'])})")
        L.append("")
    if rk.get("per_alat"):
        L.append("*Top Pemakai per Alat*")
        for r in rk["per_alat"][:10]:
            L.append(f"- {r['no_lambung'] or '(kosong)'}: {_ltr(r['keluar'])} L")
        L.append("")
    if rk.get("per_driver"):
        L.append("*Top Pemakai per Driver*")
        for r in rk["per_driver"][:10]:
            L.append(f"- {r['driver'] or '(kosong)'}: {_ltr(r['keluar'])} L")
    L.append("")
    L.append(f"Dicetak: {datetime.now():%d/%m/%Y %H:%M}")
    return "\n".join(L)


def _bagian_catatan_html(rk: dict, e) -> str:
    """Tabel khusus baris catatan: mengurangi stok, tapi bukan pemakaian alat."""
    if not rk.get("catatan"):
        return ""
    baris = "".join(
        f"<tr><td>{e(str(c.get('no_lambung') or '-'))}</td>"
        f"<td>{e(str(c.get('tanggal') or '-'))}</td>"
        f"<td>{e(str(c.get('lokasi') or '-'))}</td>"
        f"<td class='n'>{_ltr(c.get('keluar', 0))}</td>"
        f"<td class='n'>{_rp(c.get('biaya', 0))}</td></tr>" for c in rk["catatan"])
    return (
        "<h2>Catatan Khusus (bukan pemakaian alat)</h2>"
        "<table><thead><tr><th>KETERANGAN ASLI</th><th>TANGGAL DATA</th><th>LOKASI</th>"
        "<th>LITER</th><th>BIAYA</th></tr></thead>"
        f"<tbody>{baris}</tbody>"
        "<tfoot><tr><td colspan='3'>TOTAL CATATAN</td>"
        f"<td class='n'>{_ltr(rk.get('catatan_keluar', 0))}</td>"
        f"<td class='n'>{_rp(rk.get('catatan_biaya', 0))}</td></tr></tfoot></table>"
        "<div style='font-size:11px;color:#667;margin-bottom:10px'>Baris ini tetap mengurangi sisa "
        f"stok, tapi dipisahkan dari rekap pemakaian alat. Pemakaian alat saja: "
        f"{_ltr(rk.get('pemakaian_keluar', 0))} L ({_rp(rk.get('pemakaian_biaya', 0))}).</div>")


def laporan_html(rk: dict, rows: list[dict], setting: dict, f: dict | None = None) -> str:
    f = f or {}
    e = html.escape
    rs = "".join(
        f"<tr><td>{i}</td><td>{e(r['tanggal'])}</td><td>{e(r['driver'])}</td>"
        f"<td>{e(r['no_lambung'])}</td><td>{e(r['aktivitas'])}</td><td>{e(r['lokasi'])}</td>"
        f"<td class='n'>{_ltr(r['keluar'])}</td><td class='n'>{_ltr(r['masuk'])}</td>"
        f"<td class='n'>{_ltr(r.get('sisa_stok', 0))}</td>"
        f"<td class='n'>{_rp(r['keluar'] * r['harga'])}</td></tr>"
        for i, r in enumerate(rows, start=1))

    def tab(judul, data, kunci, label):
        baris = "".join(
            f"<tr><td>{e(str(r.get(kunci) or '(kosong)'))}</td>"
            f"<td class='n'>{_ltr(r['keluar'])}</td>"
            f"<td class='n'>{_rp(r.get('biaya', 0))}</td></tr>" for r in data)
        return (f"<h2>{e(judul)}</h2><table><thead><tr><th>{e(label)}</th>"
                f"<th>LITER</th><th>BIAYA</th></tr></thead><tbody>{baris}</tbody></table>")

    return f"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<title>Laporan BBM — {e(_judul_periode(f))}</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#12233b}}
 h1{{font-size:19px;margin:0 0 2px}} h2{{font-size:14px;margin:22px 0 6px;color:#1F3864}}
 .sub{{color:#666;font-size:12px;margin-bottom:14px}}
 .kartu{{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 18px}}
 .kartu div{{border:1px solid #d5dce6;border-radius:8px;padding:8px 14px;min-width:150px}}
 .kartu span{{display:block;font-size:11px;color:#667}}
 .kartu b{{font-size:16px}}
 table{{border-collapse:collapse;width:100%;font-size:11.5px;margin-bottom:8px}}
 th,td{{border:1px solid #c9d2de;padding:4px 6px}} th{{background:#1F3864;color:#fff;text-align:center}}
 td.n{{text-align:right}} tbody tr:nth-child(even){{background:#f5f7fb}}
 tfoot td{{font-weight:bold;background:#FFF2CC}}
 @media print{{@page{{size:A4 landscape;margin:10mm}} .noprint{{display:none}}}}
 .noprint{{margin:10px 0}} button{{padding:8px 16px;font-size:13px;cursor:pointer;
  background:#1F3864;color:#fff;border:0;border-radius:6px}}
</style></head><body>
<div class="noprint"><button onclick="window.print()">Cetak / Simpan PDF</button></div>
<h1>PENCATATAN BAHAN BAKAR MINYAK (BBM) / SOLAR</h1>
<div class="sub">{e(setting.get('nama_instansi',''))} &nbsp;|&nbsp; Periode: {e(_judul_periode(f))}
 &nbsp;|&nbsp; Dicetak {datetime.now():%d/%m/%Y %H:%M}</div>
<div class="kartu">
 <div><span>Stok Awal</span><b>{_ltr(rk['stok_awal'])} L</b></div>
 <div><span>BBM Masuk</span><b>{_ltr(rk['total_masuk'])} L</b></div>
 <div><span>BBM Keluar</span><b>{_ltr(rk['total_keluar'])} L</b></div>
 <div><span>Sisa Stok</span><b>{_ltr(rk['sisa_stok'])} L</b></div>
 <div><span>Biaya BBM</span><b>{_rp(rk['total_biaya'])}</b></div>
 <div><span>Jumlah Baris</span><b>{rk['baris']}</b></div>
</div>
{_bagian_catatan_html(rk, e)}
<table><thead><tr><th>NO</th><th>TANGGAL</th><th>NAMA OPT / DRIVER</th><th>ALAT / NO LAMBUNG</th>
<th>DESKRIPSI AKTIVITAS</th><th>LOKASI KEGIATAN</th><th>BBM KELUAR (L)</th><th>BBM MASUK (L)</th>
<th>SISA STOK (L)</th><th>NILAI KELUAR</th></tr></thead><tbody>{rs}</tbody>
<tfoot><tr><td colspan="6">TOTAL</td><td class="n">{_ltr(rk['total_keluar'])}</td>
<td class="n">{_ltr(rk['total_masuk'])}</td><td class="n">{_ltr(rk['sisa_stok'])}</td>
<td class="n">{_rp(rk['total_biaya'])}</td></tr></tfoot></table>
{tab('BBM KELUAR PER ALAT / NO LAMBUNG', rk['per_alat'], 'no_lambung', 'ALAT / NO LAMBUNG')}
{tab('BBM PER LOKASI KEGIATAN', rk['per_lokasi'], 'lokasi', 'LOKASI KEGIATAN')}
{tab('BBM PER DRIVER', rk['per_driver'], 'driver', 'NAMA OPT / DRIVER')}
</body></html>"""
