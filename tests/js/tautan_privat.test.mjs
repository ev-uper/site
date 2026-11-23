// site/tautan-privat.js and the private list shared with Code.gs (owner 2026-11-06).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adalahPrivat, daftarLama, temuanPakai } from '../../site/tautan-privat.js';
import { JENIS_DOKUMEN, TABEL_PRIVAT, JENIS_KARYA_PRIVAT, JENIS_BUKTI_KARYA, teksAksesBukti } from '../../site/rencana-bukti.js';
import { bagianDocx } from '../../site/lkps-bukti.js';

const ID = 'abcdefghijklmnopqrstuvwxyz';
const drive = `https://drive.google.com/file/d/${ID}/view`;
const lkd = `https://s/lkd.html?f=${ID}`;

test('Code.gs and rencana-bukti.js list the same private types', () => {
  const gs = readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8');
  const daftar = gs.match(/var JENIS_PRIVAT = \[([\s\S]*?)\];/)[1].match(/'([a-z_0-9]+)'/g).map(s => s.slice(1, -1));
  const js = [...JENIS_DOKUMEN.filter(j => j.privat).map(j => j.id), ...TABEL_PRIVAT];
  assert.deepEqual([...daftar].sort(), [...js].sort());
  assert.equal(new Set(JENIS_DOKUMEN.map(j => j.id)).size, JENIS_DOKUMEN.length);
});

test('patch 40 allows every lecturer evidence type', () => {
  const sql = readFileSync(new URL('../../supabase/instal-lengkap.sql', import.meta.url), 'utf8');
  JENIS_BUKTI_KARYA.forEach(([id]) => assert.ok(sql.includes(`'${id}'`), id));
  JENIS_KARYA_PRIVAT.forEach(id => assert.ok(JENIS_BUKTI_KARYA.some(j => j[0] === id), id));
});

test('teksAksesBukti follows the chosen type', () => {
  JENIS_KARYA_PRIVAT.forEach(j => assert.match(teksAksesBukti(j), /privat/));
  assert.match(teksAksesBukti('naskah'), /siapa pun/);
  assert.doesNotMatch(teksAksesBukti('sk'), /siapa pun yang memegangnya/);
});

test('temuanPakai: a private upload never reuses a public link', () => {
  assert.equal(temuanPakai({ url: drive }, true), null);
  assert.deepEqual(temuanPakai({ url: lkd }, true), { url: lkd });
  assert.deepEqual(temuanPakai({ url: drive }, false), { url: drive });
  assert.equal(temuanPakai(null, true), null);
});

test('Data prodi: tabs of private tables suggest a private type first', () => {
  const dp = readFileSync(new URL('../../site/data-prodi.html', import.meta.url), 'utf8');
  const saran = dp.slice(dp.indexOf('const SARAN_DOK'), dp.indexOf('TABEL.forEach(T => { T.dok'));
  const privat = new Set(JENIS_DOKUMEN.filter(j => j.privat).map(j => j.id));
  for (const t of TABEL_PRIVAT) {
    const id = dp.match(new RegExp(`id: '(\\w+)', tabel: '${t}'`))[1];
    const pertama = saran.match(new RegExp(`\\b${id}: \\['(\\w+)'`))[1];
    assert.ok(privat.has(pertama), `${id}: ${pertama}`);
  }
});

test('adalahPrivat', () => {
  assert.ok(adalahPrivat(lkd));
  assert.ok(!adalahPrivat(drive));
  assert.ok(!adalahPrivat(null));
});

test('daftarLama: only private types still on a Drive file link', () => {
  const xs = daftarLama({
    dokumen: [{ id: 1, jenis: 'notulen', url: drive }, { id: 2, jenis: 'statuta', url: drive },
              { id: 3, jenis: 'laporan_ami', url: lkd }, { id: 4, jenis: 'notulen', url: 'https://drive.google.com/drive/folders/x' }],
    karyaBukti: [{ id: 5, jenis: 'sk', url: drive }, { id: 6, jenis: 'naskah', url: drive }, { id: 7, jenis: 'sk', url: 'https://doi.org/1' }],
    lkpsBukti: [{ id: 8, tabel: 'lkps_tendik', url: drive }, { id: 9, tabel: 'lkps_prasarana', url: drive }, { id: 10, tabel: 'lkps_tendik', url: null },
                { id: 11, tabel: 'lkps_prestasi_mahasiswa', jenis: 'surat_tugas', url: drive }, { id: 12, tabel: 'lkps_prestasi_mahasiswa', jenis: 'sertifikat', url: drive }] });
  assert.deepEqual(xs.map(x => [x.tabel, x.id]), [['dokumen', 1], ['karya_bukti', 5], ['lkps_bukti', 8], ['lkps_bukti', 11]]);
});

test('index: note under private links in any table, none under public links', () => {
  const baris = [{ nama: '7b', judul: '7.b', items: [{ item: 'Audit', tautan: [{ t: 'Laporan', url: lkd }] }] },
                 { nama: '1', judul: '1', items: [{ item: 'SK', tautan: [{ t: 'Dokumen', url: 'https://d/vmts' }] }] }];
  const xml = bagianDocx(baris, { ts: 2026, sandiLkd: 'rahasia-uji' }).bagian['word/document.xml'];
  assert.equal(xml.match(/rahasia-uji/g).length, 1);
  assert.match(bagianDocx(baris, { ts: 2026 }).bagian['word/document.xml'], /diberikan terpisah/);
});
