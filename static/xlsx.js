/* Penulis XLSX mini — tanpa pustaka luar, jalan penuh OFFLINE di HP.
   Dipakai halaman HP supaya data bisa ditarik ke Excel walau laptop/server mati.
   Format: ZIP (metode "stored", tanpa kompresi) + XML SpreadsheetML. */

(function (global) {
  "use strict";

  var TABEL_CRC = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();

  function crc32(buf) {
    var c = 0xFFFFFFFF;
    for (var i = 0; i < buf.length; i++) c = TABEL_CRC[(c ^ buf[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  function bytes(s) { return new TextEncoder().encode(s); }

  /* ---------- ZIP sederhana (stored) ---------- */
  function zipStored(daftar) {
    // daftar: [{name, data:Uint8Array}] -> Uint8Array
    var tglDos = ((2026 - 1980) << 9) | (1 << 5) | 1;      // 2026-01-01
    var jamDos = 0;
    var lokal = [], pusat = [], offset = 0;

    daftar.forEach(function (f) {
      var nama = bytes(f.name), data = f.data, crc = crc32(data);
      var lh = new Uint8Array(30 + nama.length);
      var v = new DataView(lh.buffer);
      v.setUint32(0, 0x04034b50, true);
      v.setUint16(4, 20, true);          // versi minimum
      v.setUint16(6, 0x0800, true);      // nama file UTF-8
      v.setUint16(8, 0, true);           // metode 0 = stored
      v.setUint16(10, jamDos, true);
      v.setUint16(12, tglDos, true);
      v.setUint32(14, crc, true);
      v.setUint32(18, data.length, true);
      v.setUint32(22, data.length, true);
      v.setUint16(26, nama.length, true);
      v.setUint16(28, 0, true);
      lh.set(nama, 30);
      lokal.push(lh, data);

      var ch = new Uint8Array(46 + nama.length);
      var w = new DataView(ch.buffer);
      w.setUint32(0, 0x02014b50, true);
      w.setUint16(4, 20, true);
      w.setUint16(6, 20, true);
      w.setUint16(8, 0x0800, true);
      w.setUint16(10, 0, true);
      w.setUint16(12, jamDos, true);
      w.setUint16(14, tglDos, true);
      w.setUint32(16, crc, true);
      w.setUint32(20, data.length, true);
      w.setUint32(24, data.length, true);
      w.setUint16(28, nama.length, true);
      w.setUint32(42, offset, true);     // offset local header
      ch.set(nama, 46);
      pusat.push(ch);

      offset += lh.length + data.length;
    });

    var ukuranPusat = pusat.reduce(function (a, b) { return a + b.length; }, 0);
    var eocd = new Uint8Array(22);
    var e = new DataView(eocd.buffer);
    e.setUint32(0, 0x06054b50, true);
    e.setUint16(8, daftar.length, true);
    e.setUint16(10, daftar.length, true);
    e.setUint32(12, ukuranPusat, true);
    e.setUint32(16, offset, true);

    var total = offset + ukuranPusat + 22, out = new Uint8Array(total), p = 0;
    lokal.concat(pusat, [eocd]).forEach(function (b) { out.set(b, p); p += b.length; });
    return out;
  }

  /* ---------- XML ---------- */
  function xesc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/\x00-\x08|\x0B|\x0C|\x0E-\x1F/g, "");
  }

  function kolomKeHuruf(n) {                 // 1 -> A, 27 -> AA
    var s = "";
    while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = (n - 1 - m) / 26; }
    return s;
  }

  function sel(rujuk, nilai) {
    if (nilai === null || nilai === undefined || nilai === "") return "";
    if (typeof nilai === "number" && isFinite(nilai)) {
      return '<c r="' + rujuk + '"><v>' + nilai + "</v></c>";
    }
    return '<c r="' + rujuk + '" t="inlineStr"><is><t xml:space="preserve">' +
      xesc(nilai) + "</t></is></c>";
  }

  function barisXml(no, nilai) {
    var isi = nilai.map(function (v, i) { return sel(kolomKeHuruf(i + 1) + no, v); }).join("");
    return '<row r="' + no + '">' + isi + "</row>";
  }

  function sheetXml(judul, barisBaris, lebar) {
    var cols = (lebar || []).map(function (w, i) {
      return '<col min="' + (i + 1) + '" max="' + (i + 1) + '" width="' + w + '" customWidth="1"/>';
    }).join("");
    var rows = barisBaris.map(function (b, i) { return barisXml(i + 1, b); }).join("");
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
      (cols ? "<cols>" + cols + "</cols>" : "") +
      "<sheetData>" + rows + "</sheetData></worksheet>";
  }

  function workbookXml(namaSheet) {
    var sheets = namaSheet.map(function (n, i) {
      return '<sheet name="' + xesc(n) + '" sheetId="' + (i + 1) + '" r:id="rId' + (i + 1) + '"/>';
    }).join("");
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' +
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
      "<sheets>" + sheets + "</sheets></workbook>";
  }

  function workbookRelsXml(n) {
    var rels = "";
    for (var i = 1; i <= n; i++) {
      rels += '<Relationship Id="rId' + i + '" ' +
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" ' +
        'Target="worksheets/sheet' + i + '.xml"/>';
    }
    rels += '<Relationship Id="rId' + (n + 1) + '" ' +
      'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>';
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      rels + "</Relationships>";
  }

  var CONTENT_TYPES = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' +
    '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' +
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
    "</Types>";

  var ROOT_RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' +
    "</Relationships>";

  var STYLES = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>' +
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>' +
    '<fills count="2"><fill><patternFill patternType="none"/></fill>' +
    '<fill><patternFill patternType="gray125"/></fill></fills>' +
    '<borders count="1"><border/></borders>' +
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
    '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>' +
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>' +
    "</styleSheet>";

  /* ---------- API utama ---------- */
  function buatXlsx(sheet1, sheet2) {
    var berkas = [
      { name: "[Content_Types].xml", data: bytes(CONTENT_TYPES) },
      { name: "_rels/.rels", data: bytes(ROOT_RELS) },
      { name: "xl/workbook.xml", data: bytes(workbookXml([sheet1.nama, sheet2.nama])) },
      { name: "xl/_rels/workbook.xml.rels", data: bytes(workbookRelsXml(2)) },
      { name: "xl/styles.xml", data: bytes(STYLES) },
      { name: "xl/worksheets/sheet1.xml", data: bytes(sheetXml(sheet1.nama, sheet1.baris, sheet1.lebar)) },
      { name: "xl/worksheets/sheet2.xml", data: bytes(sheetXml(sheet2.nama, sheet2.baris, sheet2.lebar)) }
    ];
    return zipStored(berkas);
  }

  var KEPALA = ["NO", "BULAN", "TANGGAL", "NAMA OPT / DRIVER", "ALAT / NO LAMBUNG",
    "DESKRIPSI AKTIVITAS", "LOKASI KEGIATAN", "BBM / LTR (KELUAR)", "BBM MASUK (LTR)",
    "HARGA / LTR (RP)", "SISA STOK (LTR)", "NILAI BBM KELUAR (RP)",
    "NILAI BBM MASUK (RP)", "KETERANGAN"];
  var LEBAR = [5, 11, 12, 20, 26, 24, 18, 14, 14, 14, 14, 18, 18, 26];

  var BULAN_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
    "Agustus", "September", "Oktober", "November", "Desember"];

  function namaBulan(tgl) {
    var m = /^(\d{4})-(\d{2})/.exec(String(tgl || ""));
    return m ? (BULAN_ID[parseInt(m[2], 10) - 1] + " " + m[1]) : "";
  }

  function angka(v) { var n = Number(v); return isFinite(n) ? n : 0; }

  /**
   * Buat workbook dari daftar baris BBM.
   * setting: {nama_instansi, stok_awal, periode}
   * hasil: {blob, namaBerkas, totalBaris, totalKeluar, totalMasuk, biaya}
   */
  function buatLaporan(rows, setting, judulPeriode) {
    setting = setting || {};
    var awal = angka(setting.stok_awal);
    var baris = [], saldo = awal, keluar = 0, masuk = 0, biaya = 0;
    var perAlat = {}, perLokasi = {}, perDriver = {};

    var urut = rows.slice().sort(function (a, b) {
      if (a.tanggal !== b.tanggal) return a.tanggal < b.tanggal ? -1 : 1;
      return angka(a._urut) - angka(b._urut);
    });

    urut.forEach(function (r, i) {
      var k = angka(r.keluar), m = angka(r.masuk), h = angka(r.harga);
      saldo += m - k; keluar += k; masuk += m; biaya += k * h;
      baris.push([i + 1, namaBulan(r.tanggal), r.tanggal, r.driver || "", r.no_lambung || "",
        r.aktivitas || "", r.lokasi || "", k, m, h, Math.round(saldo * 100) / 100,
        k * h, m * h, r.keterangan || ""]);
      [["alat", r.no_lambung], ["lokasi", r.lokasi], ["driver", r.driver]].forEach(function (p) {
        var map = p[0] === "alat" ? perAlat : (p[0] === "lokasi" ? perLokasi : perDriver);
        var nama = (p[1] || "(kosong)").trim() || "(kosong)";
        if (!map[nama]) map[nama] = { keluar: 0, biaya: 0, baris: 0 };
        map[nama].keluar += k; map[nama].biaya += k * h; map[nama].baris += 1;
      });
    });

    var judul = (setting.nama_instansi || "MONITORING BBM") + " — PENCATATAN BBM / SOLAR";
    var lembar1 = [
      [judul],
      ["Periode: " + (judulPeriode || "Semua data")],
      [],
      KEPALA
    ].concat(baris);
    lembar1.push([]);
    lembar1.push(["TOTAL", baris.length + " baris", "", "", "", "", "", keluar, masuk, "",
      Math.round(saldo * 100) / 100, biaya, "", ""]);

    var tukangUrut = function (map, namaKolom) {
      return Object.keys(map).map(function (n) {
        return [n, map[n].baris, Math.round(map[n].keluar * 100) / 100, map[n].biaya];
      }).sort(function (a, b) { return b[2] - a[2]; });
    };
    var lembar2 = [
      ["REKAP " + judul],
      ["Periode: " + (judulPeriode || "Semua data")],
      [],
      ["Stok awal (L)", awal],
      ["Total masuk (L)", masuk],
      ["Total keluar (L)", keluar],
      ["Sisa stok (L)", Math.round(saldo * 100) / 100],
      ["Total nilai keluar (Rp)", biaya],
      ["Jumlah baris", baris.length],
      [],
      ["PER ALAT", "", "", ""],
      ["ALAT / NO LAMBUNG", "Jumlah baris", "BBM keluar (L)", "Nilai (Rp)"]
    ].concat(tukangUrut(perAlat))
      .concat([[], ["PER LOKASI", "", "", ""],
        ["LOKASI KEGIATAN", "Jumlah baris", "BBM keluar (L)", "Nilai (Rp)"]])
      .concat(tukangUrut(perLokasi))
      .concat([[], ["PER DRIVER", "", "", ""],
        ["NAMA OPT / DRIVER", "Jumlah baris", "BBM keluar (L)", "Nilai (Rp)"]])
      .concat(tukangUrut(perDriver));

    var data = buatXlsx({ nama: "BBM", baris: lembar1, lebar: LEBAR },
      { nama: "REKAP", baris: lembar2, lebar: [28, 13, 16, 18] });

    var tgl = new Date().toISOString().slice(0, 10);
    return {
      blob: new Blob([data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
      namaBerkas: "BBM_HP_" + tgl + ".xlsx",
      totalBaris: baris.length, totalKeluar: keluar, totalMasuk: masuk, biaya: biaya,
      sisaStok: Math.round(saldo * 100) / 100
    };
  }

  global.BBMXlsx = { buatLaporan: buatLaporan, buatXlsx: buatXlsx, KEPALA: KEPALA };
})(typeof window !== "undefined" ? window : globalThis);
