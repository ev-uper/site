// LED kerangka per elemen (site/led-kerangka.js, 2026-11-24): run on the official
// LAMDEPILAR template stored in site/instrumen/lamdepilar-magister/led-template.docx.
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { isiKerangka, kodeJudul, paragrafAtas, daftarKata } from '../../site/led-kerangka.js';
import { bacaZip } from './baca_zip.mjs';

const SITE = new URL('../../site/', import.meta.url);
const LDP = new URL('instrumen/lamdepilar-magister/', SITE);

test('kodeJudul reads element codes as written in templates', () => {
  assert.equal(kodeJudul('D.1 Legalitas program'), 'D.1');
  assert.equal(kodeJudul('L2. Sumber Pengetahuan'), 'L.2');
  assert.equal(kodeJudul('I.1Sistem Penjaminan Mutu Internal'), 'I.1');
  assert.equal(kodeJudul('D.Diferensiasi Misi'), null);
  assert.equal(kodeJudul('4.1Bidang Keilmuan'), null);
});

test('every instrument points to LED and LKPS engines and files that exist', async () => {
  for (const id of readdirSync(new URL('instrumen/', SITE), { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name)) {
    const { LED, LKPS } = await import(new URL(`instrumen/${id}/dokumen.js`, SITE));
    for (const [nama, x] of [['LED', LED], ['LKPS', LKPS]]) {
      assert.ok(existsSync(new URL(x.mesin, SITE)), `${id} ${nama}: mesin ${x.mesin}`);
      assert.ok(existsSync(new URL(x.templat, SITE)), `${id} ${nama}: templat ${x.templat}`);
      if (x.contoh) assert.ok(existsSync(new URL(x.contoh, SITE)), `${id} ${nama}: contoh ${x.contoh}`);
    }
  }
});

test('LAMDEPILAR LED: every element heading gets its framework, links are registered', async () => {
  const zip = bacaZip(readFileSync(new URL('led-template.docx', LDP)));
  const xml = zip['word/document.xml'](), rels = zip['word/_rels/document.xml.rels']();
  const { BUTIR_MANUAL } = await import(new URL('butir-manual.js', LDP));
  const { UNSUR_BUTIR } = await import(new URL('unsur-butir.js', LDP));
  const bukti = no => no === '101' ? [{ label: 'SK Pendirian Prodi', url: 'https://example.org/sk?a=1&b=2', unsur: 1 }]
    : no === '121' ? [{ label: 'Daftar kerja sama', url: 'https://example.org/ks', unsur: null }] : [];
  const h = isiKerangka(xml, rels, { butirManual: BUTIR_MANUAL, unsurButir: UNSUR_BUTIR, bukti });

  assert.deepEqual(h.gagal, [], 'elemen tanpa judul di templat');
  assert.deepEqual(h.tanpaPengisi, [], 'judul tanpa paragraf pengisi');
  assert.equal(h.terisi.length, 29);   // 30 elemen; judul A.1 templat memuat elemen A.1 dan A.2
  // 29 element fillers by the framework; the rest (cover letter, chapters 1, 2, 4, 5) by isiDepan (2026-11-25)
  assert.equal(h.sisaPengisi, 0, 'no Lorem ipsum / Duis aute left');
  assert.ok(!/Lorem ipsum|Duis aute/.test(h.xml));
  assert.match(h.xml, /\(1\) Legalitas Institusi, UPPS, dan program studi yang lengkap/);
  assert.match(h.xml, /Elemen A\.2 Kerja Sama dan Kemitraan/);
  assert.match(h.xml, /Bukti lain untuk elemen ini: /);
  assert.ok(!/Skor|skor 0|NA /.test(h.xml.replace(/<[^>]+>/g, '').slice(xml.length / 50)), 'LED tanpa skor');
  const id = /<w:hyperlink r:id="(rId\d+)"[^>]*>(?:(?!<\/w:hyperlink>).)*SK Pendirian Prodi/.exec(h.xml)?.[1];
  assert.ok(id, 'tautan bukti di dokumen');
  assert.match(h.rels, new RegExp(`Id="${id}"[^>]*Target="https://example.org/sk\\?a=1&amp;b=2"[^>]*TargetMode="External"`));
  // XML tetap seimbang
  const buka = (h.xml.match(/<w:p(?:\s[^>]*?)?>/g) || []).filter(t => !t.endsWith('/>')).length;
  const tutup = (h.xml.match(/<\/w:p>/g) || []).length;
  assert.equal(buka, tutup);
  assert.equal(paragrafAtas(h.xml).length > paragrafAtas(xml).length, true);
});

// Cover, cover letter, chapters 1, 2, 4, 5 (owner 2026-11-25 "lengkapi LAMDEPILAR").
test('LAMDEPILAR LED front matter and chapters: site facts in, fillers out, logo wired', async () => {
  const zip = bacaZip(readFileSync(new URL('led-template.docx', LDP)));
  const xml = zip['word/document.xml'](), rels = zip['word/_rels/document.xml.rels']();
  const { BUTIR_MANUAL } = await import(new URL('butir-manual.js', LDP));
  const { UNSUR_BUTIR } = await import(new URL('unsur-butir.js', LDP));
  const narasi = { 'umum|identitas|Unit Pengelola Program Studi|1': 'Fakultas Uji', 'umum|identitas|Kota kedudukan perguruan tinggi|1': 'Jakarta' };
  const daftar = {
    dosen: [{ id: 1, nama: 'Dr. Ani', jabatan: 'lektor_kepala', aktif: true }],
    tim: [{ id: 9, dosen_id: 1, urutan: 1 }, { id: 10, nama: 'Budi & Rekan', jabatan: 'Tendik', urutan: 2, jenis: 'nondosen' }],
    mk: [{ kode: 'A1', kurikulum: 'K21' }, { kode: 'B1', kurikulum: 'K26' }],
    cpl: [{ kode: 'CPL2', kurikulum: 'K26', rumusan: 'Merancang <sistem>' }, { kode: 'CPL1', kurikulum: 'K26', rumusan: 'Menganalisis' },
          { kode: 'CPL9', kurikulum: 'K21', rumusan: 'Lama' }] };
  const C = { butirManual: BUTIR_MANUAL, unsurButir: UNSUR_BUTIR, bukti: () => [], D: { prodi: 'Keberlanjutan', institusi: 'Universitas Uji' },
    jenjang: 'Magister', narasi, daftar, ts: 2026, taDari: t => `${t - 1}/${t}`, instrumen: 'IAPS DEPILAR 1.0 Magister',
    kini: new Date('2026-11-25'), logo: { cx: 200, cy: 100 } };
  const h = isiKerangka(xml, rels, C);
  const teks = h.xml.replace(/<w:tab\/>/g, ' ').replace(/<[^>]+>/g, '');
  for (const s of ['Program Studi Magister Keberlanjutan', 'Fakultas Uji', 'Universitas Uji', 'Jakarta, November 2026',
    'Periode Akreditasi [isi: Maret/Juni/September dan tahun]', '[isi: judul Laporan Evaluasi Diri]', 'Jakarta, [isi: tanggal surat]', '[isi: pembuka surat pengantar', '[isi: penutup surat pengantar',
    'data TS 2025/2026 (jendela tiga tahun TS-2 s.d. TS: 2023/2024 s.d. 2025/2026)', 'IAPS DEPILAR 1.0 Magister',
    'Anggota tim penyusun: Dr. Ani (Lektor Kepala) dan Budi &amp; Rekan (Tendik).',
    'Capaian pembelajaran lulusan kurikulum K26:', 'CPL1: Menganalisis', 'CPL2: Merancang &lt;sistem&gt;', 'LKPS Tabel E.4.2',
    'Petunjuk templat: Uraian diupayakan tidak lebih 500 kata.'])
    assert.ok(teks.includes(s), s);
  assert.ok(teks.indexOf('CPL1: Menganalisis') < teks.indexOf('CPL2: Merancang'), 'CPL in code order');
  assert.ok(!teks.includes('CPL9') && !teks.includes('Template Laporan Evaluasi Diri') && !teks.includes('[contoh]'));
  // cover-letter table: header + this programme only
  const tbl = paragrafAtas(h.xml).find(p => p.xml.startsWith('<w:tbl') && /Usulan/.test(p.xml)).xml;
  assert.equal((tbl.match(/<w:tr[ >]/g) || []).length, 2);
  assert.match(tbl.replace(/<[^>]+>/g, ''), /KeberlanjutanMagisterStatus Terakreditasi/);
  // logo replaces the "Logo Perguruan Tinggi" box: 5 cm wide, aspect kept
  assert.equal(h.logo, true);
  assert.match(h.xml, /<a:blip r:embed="rIdLdpLogo"\/>/);
  assert.match(h.xml, /<wp:extent cx="1800000" cy="900000"\/>/);
  assert.ok(!teks.includes('Logo Perguruan Tinggi'));
  // XML stays balanced; parses
  const buka = (h.xml.match(/<w:p(?:\s[^>]*?)?>/g) || []).filter(t => !t.endsWith('/>')).length;
  assert.equal(buka, (h.xml.match(/<\/w:p>/g) || []).length);
  // without site data: placeholders, cover box kept
  const k = isiKerangka(xml, rels, { butirManual: BUTIR_MANUAL, unsurButir: UNSUR_BUTIR, bukti: () => [], D: {}, ts: 2026 });
  const tk = k.xml.replace(/<[^>]+>/g, '');
  assert.equal(k.logo, false);
  for (const s of ['Logo Perguruan Tinggi', '[isi: nama UPPS', '[isi: kota]', 'Anggota tim penyusun: [isi:', '[isi: rumusan CPL'])
    assert.ok(tk.includes(s), s);
  assert.equal(k.sisaPengisi, 0);
});

test('daftarKata: Indonesian list joining', () => {
  assert.equal(daftarKata(['A']), 'A');
  assert.equal(daftarKata(['A', 'B']), 'A dan B');
  assert.equal(daftarKata(['A', 'B', 'C']), 'A, B, dan C');
});
