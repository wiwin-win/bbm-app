/* Uji penulis XLSX offline: bikin file, lalu diverifikasi openpyxl (lihat uji_xlsx.py). */
const fs = require("fs");
const path = require("path");

global.window = global;
require(path.join(__dirname, "static", "xlsx.js"));

const baris = [
  { tanggal: "2026-09-20", driver: "AKBAR", no_lambung: "LOADER (GAS 009)", aktivitas: "MAINTENANCE JALAN",
    lokasi: "PT GAS", keluar: 140, masuk: 0, harga: 17200, keterangan: "", _urut: 1 },
  { tanggal: "2026-09-20", driver: "DANI", no_lambung: "TANGKI BBM", aktivitas: "BBM MASUK",
    lokasi: "PT GAS", keluar: 0, masuk: 4900, harga: 17200, keterangan: "isi tangki", _urut: 2 },
  { tanggal: "2026-09-21", driver: "TES & UJI", no_lambung: 'ALAT "KHUSUS" <x>', aktivitas: "UJI",
    lokasi: "PT CMM", keluar: 10.5, masuk: 0, harga: 19000, keterangan: "simbol & < > \" '", _urut: 3 }
];

const hasil = BBMXlsx.buatLaporan(baris, {
  nama_instansi: "PT GEMBIRA ANGGUN SETIA", stok_awal: 1000
}, "20/09/2026 s/d 21/09/2026");

const keluar = process.argv[2] || path.join(__dirname, "uji_xlsx_hasil.xlsx");
(async () => {
  const ab = await hasil.blob.arrayBuffer();
  fs.writeFileSync(keluar, Buffer.from(ab));
  console.log(JSON.stringify({
    berkas: keluar, baris: hasil.totalBaris, keluar: hasil.totalKeluar,
    masuk: hasil.totalMasuk, biaya: hasil.biaya, sisa: hasil.sisaStok,
    ukuran: fs.statSync(keluar).size, nama: hasil.namaBerkas
  }, null, 1));
})();
