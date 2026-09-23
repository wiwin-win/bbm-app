/* Uji halaman HP secara offline: syntax JS + alur simpan -> tarik Excel.
   Meniru DOM seperlunya di Node supaya fungsi halaman bisa benar-benar dijalankan. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const berkas = process.argv[2] || path.join(__dirname, "uji_mandiri.html");
const html = fs.readFileSync(berkas, "utf8");

// ambil semua blok <script> tanpa src, urut
const blok = [...html.matchAll(/<script(?![^>]*src=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
console.log("blok script inline:", blok.length);

// ---- DOM tiruan ----
const idPalsu = new Set([...html.matchAll(/id="([A-Za-z0-9_]+)"/g)].map(m => m[1]));
const elemen = new Map();
function el(id) {
  if (!elemen.has(id)) elemen.set(id, {
    id, value: "", textContent: "", innerHTML: "", className: "", style: {}, dataset: {},
    classList: { add() {}, remove() {} }, addEventListener() {}, appendChild() {}, remove() {},
    click() {}, select() {}, href: "", download: ""
  });
  return elemen.get(id);
}
const dibuat = [];
const dokumen = {
  getElementById: (id) => (idPalsu.has(id) ? el(id) : null),
  querySelectorAll: () => [],
  createElement: (t) => { const e = el("buat_" + t + dibuat.length); e.tag = t; dibuat.push(e); return e; },
  addEventListener: () => {},
  body: { appendChild() {}, removeChild() {} },
  execCommand: () => true,
  hidden: false
};
const simpanan = new Map();
const localStorage = {
  getItem: k => (simpanan.has(k) ? simpanan.get(k) : null),
  setItem: (k, v) => simpanan.set(k, String(v)),
  removeItem: k => simpanan.delete(k)
};
let dibagikan = null;
const ctx = {
  console, setTimeout, clearTimeout, Date, Math, JSON, URLSearchParams, Promise, Number, String,
  parseFloat, parseInt, isNaN, Object, Array, Error, Buffer,
  document: dokumen, localStorage,
  navigator: {
    onLine: false, vibrate() {}, clipboard: { writeText: async () => {} },
    canShare: () => true,
    share: async (o) => { dibagikan = o; }
  },
  location: { protocol: "file:", origin: "null", href: "" },
  confirm: () => false, alert: () => {},
  fetch: async () => { throw new Error("offline: tidak boleh butuh server"); },
  File: class File {
    constructor(bagian, nama, opsi) {
      this.name = nama; this.type = (opsi || {}).type || "";
      this.blob = new Blob(bagian, {type: this.type});   // Node Blob asli
    }
    async arrayBuffer() { return await this.blob.arrayBuffer(); }
  },
  Blob: Blob,
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  addEventListener: () => {}
};
ctx.window = ctx;
ctx.globalThis = ctx;
ctx.TextEncoder = TextEncoder;          // tersedia di browser & Node 11+
ctx.TextDecoder = TextDecoder;
ctx.Uint8Array = Uint8Array;
ctx.ArrayBuffer = ArrayBuffer;
const semua = blok.join("\n") + "\n;globalThis.__UJI={saring,teksLaporan,tarikExcel,simpan,settingLokal,setSettingLokal,setDataLokal,dataLokal,belongsBelumTerkirim,meta,setMeta,iso};";
try {
  vm.createContext(ctx);
  new vm.Script(semua, { filename: "halaman-hp.js" }).runInContext(ctx);
  console.log("syntax + eksekusi: OK");
} catch (e) {
  console.log("GAGAL eksekusi:", e.message);
  process.exit(1);
}

(async () => {
  const U = ctx.__UJI;
  if (!U) { console.log("GAGAL: fungsi tidak terdaftar"); process.exit(1); }
  // ---- isi data seolah diinput di HP (tanpa server) ----
  U.setSettingLokal({ nama_instansi: "PT UJI", harga_default: 17200, stok_awal: 1000 });
  U.setDataLokal([
    { tanggal: "2026-09-20", driver: "AKBAR", no_lambung: "LOADER (GAS 009)", aktivitas: "MAINTENANCE JALAN",
      lokasi: "PT GAS", keluar: 140, masuk: 0, harga: 17200, keterangan: "", _sinkron: false, _urut: 1 },
    { tanggal: "2026-09-20", driver: "DANI", no_lambung: "TANGKI BBM", aktivitas: "BBM MASUK",
      lokasi: "PT GAS", keluar: 0, masuk: 4900, harga: 17200, keterangan: "isi tangki", _sinkron: false, _urut: 2 },
    { tanggal: "2026-09-21", driver: "TES & UJI", no_lambung: 'ALAT "KHUSUS" <x>', aktivitas: "UJI",
      lokasi: "PT CMM", keluar: 10.5, masuk: 0, harga: 19000, keterangan: "simbol", _sinkron: false, _urut: 3 }
  ]);
  console.log("belum terkirim:", U.belongsBelumTerkirim().length, "(harus 3)");
  console.log("saring 20-21:", U.saring("2026-09-20", "2026-09-21").length, "(harus 3)");
  console.log("saring 21 saja:", U.saring("2026-09-21", "2026-09-21").length, "(harus 1)");
  const teks = U.teksLaporan();
  console.log("laporan memuat sisa stok:", /Sisa stok\s*:\s*5\.749,5 L/.test(teks));
  console.log("laporan memuat peringatan belum sinkron:", teks.includes("belum tersinkron"));

  // ---- KASUS PENTING: klik "SIMPAN" saat laptop mati & alamat server belum diisi ----
  el("iTanggal").value = "2026-09-22";
  el("iLiter").value = "25";
  el("iAlat").value = "EXCA UJI";
  el("iDriver").value = "BUDI";
  const sebelum = U.dataLokal().length;
  try { await U.simpan(); } catch (e) { console.log("simpan error:", e.message); }
  const sesudah = U.dataLokal().length;
  console.log("input tanpa server:", sesudah - sebelum, "(harus 1)");
  console.log("pesan di layar:", el("pesan").textContent);
  console.log("data barunya tersimpan:", JSON.stringify(
    U.dataLokal()[U.dataLokal().length - 1]).slice(0, 120));
  // ---- tarik Excel offline ----
  el("xDari").value = "2026-09-20"; el("xSampai").value = "2026-09-21";
  try { await U.tarikExcel(true); } catch (e) { console.log("tarikExcel error:", e.message); }
  console.log("pesan di layar:", el("pesan").textContent);
  const f = dibagikan && dibagikan.files && dibagikan.files[0];
  console.log("tipe f:", typeof f, "| punya blob:", !!(f && f.blob), "| tipe arrayBuffer:",
    f && f.blob ? typeof f.blob.arrayBuffer : "-", "| konstruktor:", f && f.blob && f.blob.constructor.name);
  if (f) {
    const ab = await f.blob.arrayBuffer();
    fs.writeFileSync(path.join(__dirname, "uji_hp_offline.xlsx"), Buffer.from(ab));
    console.log("ditulis ke uji_hp_offline.xlsx");
  }
})();

// debug cepat
