# Monitoring BBM & Alat

Aplikasi pencatatan & monitoring pemakaian BBM/solar per alat. FastAPI + SQLite,
satu file DB, bisa dibuka dari PC dan HP (Wi-Fi yang sama).

Kolom input persis file Excel BBM.xlsx:
TANGGAL | NAMA OPT / DRIVER | ALAT / NO LAMBUNG | DESKRIPSI AKTIVITAS |
LOKASI KEGIATAN | BBM / LTR (KELUAR) | BBM MASUK (LTR) | HARGA / LTR |
KETERANGAN (+ HM AWAL / HM AKHIR opsional).

## Cara jalan

- PC saja      : dobel-klik `jalankan.bat`     -> http://127.0.0.1:8791
- PC + HP      : dobel-klik `jalankan_hp.bat`  -> http://<IP-LAN>:8791/m

Login awal: admin / admin  (ganti di menu Pengguna setelah masuk).
Di HP: buka alamat /m, lalu menu browser > "Tambahkan ke layar utama" -> jadi ikon.

Cek kesehatan aplikasi: `python selftest.py` (uji DB, laporan, Excel, API -- tanpa server)
dan `python cek_sweep.py` (uji semua endpoint, server harus jalan).

## Isi data

1. Muat master dari Excel lama (sekali saja):
       python muat_master.py "C:\Users\wiwin\Documents\BBM.xlsx"
   Menambah daftar alat (182), driver (153), lokasi (9), aktivitas (57).
2. Import riwayat transaksi: menu Data > Import Excel, pilih file BBM.xlsx.
   Sudah teruji 680 baris Mei-Sep 2026 dan totalnya sama dengan file asli:
   keluar 86.649 L, masuk 87.340 L, sisa stok akhir 691 L,
   nilai keluar Rp 1.560.043.200.
3. Input harian: menu Tambah Data (PC) atau tab Input (HP) -- ada saran otomatis
   dari master, jadi ngetik cukup beberapa huruf.
4. Export: menu Data > Export Excel. Hasilnya juga bisa dipakai sebagai template.
   `python banding_excel.py` membandingkan export aplikasi vs file asli
   (harus "SEMUA COCOK").

## Perbandingan dengan Excel asli

- Total keluar/masuk/nilai: cocok persis dengan baris TOTAL di Excel.
- Sisa stok dihitung otomatis (stok awal + masuk - keluar) dan tampil per baris,
  jadi tidak perlu lagi isi kolom SISA STOK manual.
- Baris tanpa tanggal seperti "BBM HILANG/BOCOR" (3.290 L) tetap dihitung,
  ditandai lewat kolom KETERANGAN: "catatan khusus dari Excel: ...".
  Saat import, baris seperti ini dilaporkan di kotak pesan supaya kelihatan.

## Isi aplikasi

- Dashboard PC: kartu stok (awal/masuk/keluar/sisa/biaya), grafik harian,
  tabel data dengan filter tanggal/bulan/driver/alat/lokasi/kata kunci,
  rekap per alat / lokasi / driver / aktivitas, log aktivitas.
- HP (/m): tab Input, Data, Excel, Rekap, Siapkan -- layar sentuh, tombol besar.
- Laporan: tombol "Laporan WA" (teks siap kirim WhatsApp) dan
  "Laporan Cetak" (HTML siap Ctrl+P / simpan PDF).
- Admin: pengguna & peran (admin/operator), pengaturan (nama instansi,
  harga BBM, stok awal, periode), ganti password, backup DB.
- Keamanan: session cookie HttpOnly, password di-hash PBKDF2, operator tidak
  bisa menghapus data atau mengubah pengguna.

## Cara download aplikasinya (ke HP)

Ada 3 cara, dari yang paling gampang:

1. Lewat PC (paling mudah)
   - Jalankan jalankan_hp.bat di laptop.
   - Di PC buka http://127.0.0.1:8791 -> tombol "Aplikasi HP (offline)".
     File BBM-HP-Input.html tersimpan di folder Download.
   - Kirim file itu ke HP (WhatsApp/Telegram/USB), lalu buka di HP.
2. Lewat HP langsung (WiFi sama)
   - Buka http://<IP-LAN>:8791/m -> tab "Siapkan" -> "Muat Versi Mandiri (1 file)".
   - Di HP modern tombol ini munculkan menu Bagikan; pilih simpan ke File/Drive,
     atau file langsung masuk folder Download.
3. Instal seperti aplikasi (perlu laptop menyala)
   - Buka http://<IP-LAN>:8791/m di Chrome -> menu > "Tambahkan ke layar utama".
   - jadi ikon di layar HP; jalan tanpa buka browser, tapi butuh laptop hidup.

### Aplikasi HP offline (laptop mati tetap jalan)

File `BBM-HP-Input.html` sudah berisi seluruh aplikasi dalam SATU file
(tanpa gambar/JS dari luar, jadi jalan dari memori HP):

- Input tetap bisa, walau laptop mati dan tidak ada WiFi.
  Data disimpan di HP (localStorage) dan diberi penanda "belum terkirim".
- Tarik Excel tetap bisa dari HP sendiri: tab Excel > "Tarik Data"/"Bagikan".
  File .xlsx dibuat DI HP (penulis XLSX mini, tanpa internet), lengkap 2 sheet
  (BBM + REKAP) dan sisa stok berjalan.
  -> hasilnya sudah diuji dibuka dengan Excel/openpyxl, angkanya benar.
- Sinkron saat kembali ke kantor: tab Siapkan > isi alamat server
  (mis. http://192.168.1.59:8791) > Simpan > Sinkron.
  Data yang belum terkirim dikirim, master + data terbaru ditarik.
  Setiap data punya kunci unik, jadi kiriman ulang TIDAK bikin data dobel.
- Sinkron otomatis jalan saat app dibuka dan saat sinyal kembali.

Catatan: file di HP dan data di server digabung saat Sinkron. Kalau HP hilang,
data yang sudah tersinkron tetap aman di laptop; yang belum tersinkron ikut hilang
(karena hanya ada di HP). Karena itu biasakan Sinkron tiap balik ke kantor.


## Berkas penting

    app.py            server + route API + login
    storage.py        SQLite: tabel, rekap, sisa stok berjalan
    excel.py          import (tahan file kotor) & export Excel
    report.py         laporan teks WA + HTML cetak
    templates/        index.html (PC), mobile.html (/m), login.html
    static/           ikon + manifest PWA
    buat_ikon.py      bikin ulang ikon PWA
    muat_master.py    isi master dari Excel lama
    selftest.py       uji mandiri (tanpa server)
    cek_sweep.py      uji semua endpoint (server jalan)
    banding_excel.py  banding export vs Excel asli
    bbm.db            database (backup: folder backup/)

## Reset

Hapus `bbm.db` -> aplikasi membuat DB baru kosong saat dijalankan.
Untuk mengosongkan transaksi tapi tetap simpan master: pakai menu Pengaturan >
Kosongkan data transaksi, atau import ulang dengan opsi "kosongkan dulu".
