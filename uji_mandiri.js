/* Uji file mandiri apa adanya: jalankan JS di dalamnya dengan Node (tanpa server).
   Membuktikan file yang dikirim ke HP benar-benar jalan sendiri. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const berkas = process.argv[2] || path.join(__dirname, "..", "Documents", "BBM-HP-Input.html");
const html = fs.readFileSync(berkas, "utf8");

// ambil SEMUA blok <script> tanpa src
const blok = [];
const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
let m;
while ((m = re.exec(html))) blok.push(m[1]);

const dicatat = [];
function el(id) {
  if (!dicatat[id]) dicatat[id] = { id, value: "", textContent: "", innerHTML: "", className: "",
                                    style: {}, dataset: {}, classList: { add(){}, remove(){}, contains(){ return false; } },
                                    addEventListener(){}, appendChild(){}, focus(){}, reset(){} };
  return dicatat[id];
}
const simpan = {};
const ctx = {
  console,
  document: { getElementById: el, querySelector: () => el("_q"), querySelectorAll: () => [],
              addEventListener: () => {}, createElement: () => el("_c"),
              body: { appendChild() {} }, documentElement: { style: {} } },
  window: null, globalThis: null,
  navigator: { onLine: false, share: async () => {}, canShare: () => false, vibrate: () => {},
               userAgent: "node", serviceWorker: undefined },
  location: { protocol: "file:", origin: "null", href: "file:///BBM-HP-Input.html" },
  localStorage: { _d: simpan, getItem: k => (k in simpan ? simpan[k] : null),
                  setItem: (k, v) => { simpan[k] = String(v); }, removeItem: k => { delete simpan[k]; } },
  confirm: () => false, alert: () => {},
  fetch: async () => { throw new Error("harus offline: tidak boleh menghubungi server"); },
  File: class File {
    constructor(bagian, nama, opsi) {
      this.name = nama; this.type = (opsi || {}).type || "";
      this.blob = new Blob(bagian, { type: this.type });
    }
    async arrayBuffer() { return await this.blob.arrayBuffer(); }
  },
  Blob, TextEncoder, TextDecoder, Uint8Array, ArrayBuffer,
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  setTimeout, clearTimeout, Date, Math, JSON, Promise, Object, Array, String, Number, parseFloat,
  parseInt, isNaN, Error, RegExp, Set, Map, Intl,
  addEventListener: () => {},
  btoa: s => Buffer.from(s, "binary").toString("base64"),
  atob: s => Buffer.from(s, "base64").toString("binary"),
};
ctx.window = ctx;
ctx.globalThis = ctx;

let ok = true;
try {
  vm.createContext(ctx);
  vm.runInContext(blok.join("\n"), ctx, { filename: "BBM-HP-Input.html" });
  console.log("script blok:", blok.length, "| syntax + eksekusi: OK (offline, tanpa server)");
} catch (e) {
  ok = false;
  console.log("GAGAL eksekusi:", e.message);
}

if (ok) {
  const F = ctx.__UJI;
  console.log("fungsi inti:", F ? "tersedia" : "TIDAK ADA",
              "| mode mandiri:", ctx.sedangMandiri ? ctx.sedangMandiri() : "-");
}
process.exit(ok ? 0 : 1);
