// Upload of CPL grade files through the site (owner 2026-11-11, option 2; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { VERSI_TEMPLAT, SEMESTER, bacaLembar, periksaBerkas, bacaCSVKelas, statusKelas, periodeKelas, penerimaBelumUnggah }
  from '../../site/nilai-cpl.js';

// Minimal SheetJS-shaped workbook: Sheets[name][A1].v (cached values).
function wb({ info = {}, periksa = {}, tanpaPeriksa = false } = {}){
  const I = { 'Kode MK': '41214', 'Nama MK': 'Pemrograman', 'SKS': 3, 'Semester': 'Ganjil', 'Tahun Akademik': '2026/2027', 'Kurikulum': 'K26',
    'Dosen Koordinator': 'X', 'Tanggal pengisian': '2026-11-11', 'Kelas': 'A', 'Versi templat': 'CPL-2026.10.09', ...info };
  const s = { Info: {}, Periksa: {} };
  Object.entries(I).forEach(([l, v], i) => { s.Info[`A${4 + i}`] = { v: l }; s.Info[`B${4 + i}`] = { v }; });
  for (let r = 8; r <= 20; r++) {
    s.Periksa[`A${r}`] = { v: `Pemeriksaan ${r}` };
    s.Periksa[`B${r}`] = { v: 0 };
    if (!tanpaPeriksa) s.Periksa[`C${r}`] = { v: periksa[r] ?? 'OK' };
  }
  return { Sheets: s };
}
const KELAS = { id: 1, tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: '41214', kelas: 'A' };

test('JS lists match config.yaml template_versions and semester_order', () => {
  const y = readFileSync(new URL('../../config.yaml', import.meta.url), 'utf8');
  const versi = y.match(/template_versions:\n((?:\s+- .+\n)+)/)[1].match(/- (\S+)/g).map(x => x.slice(2));
  assert.deepEqual(VERSI_TEMPLAT, versi);
  const sem = y.match(/semester_order:\n((?:\s+\w+: \d+\n)+)/)[1].match(/(\w+):/g).map(x => x.slice(0, -1));
  assert.deepEqual(SEMESTER, sem);
});

test('a filled, saved file for the right class passes', () => {
  assert.deepEqual(periksaBerkas(bacaLembar(wb()), KELAS), { ok: true, masalah: [] });
  assert.equal(periksaBerkas(bacaLembar(wb({ info: { Semester: 'ganjil', Kelas: ' a ' } })), KELAS).ok, true);   // case/space tolerant
});

test('wrong class identity, version, unsaved or failing Periksa rows are refused with reasons', () => {
  const r = periksaBerkas(bacaLembar(wb({ info: { 'Kode MK': '41299', 'Versi templat': 'CPL-lama' }, periksa: { 12: 'CEK' } })), KELAS);
  assert.equal(r.ok, false);
  assert.ok(r.masalah.some(m => /Versi templat/.test(m)));
  assert.ok(r.masalah.some(m => /Kode MK.*41299.*41214/.test(m)));
  assert.ok(r.masalah.some(m => /baris 12 belum OK/.test(m)));
  assert.match(periksaBerkas(bacaLembar(wb({ tanpaPeriksa: true })), KELAS).masalah.join(), /simpan ulang/);
  assert.match(periksaBerkas(bacaLembar({ Sheets: { Lain: {} } }), KELAS).masalah[0], /Bukan berkas/);
});

test('class CSV: semicolon or comma, header aliases, row errors and duplicates', () => {
  const ok = bacaCSVKelas('\uFEFFtahun_akademik;semester;kode_mk;nama_mk;kelas;email_dosen\n2026/2027;ganjil;41214;Pemrograman;A;Dosen@X.ac.id\n'
    + '2026/2027;Ganjil;41214;Pemrograman;A;dosen@x.ac.id\n2026-2027;Antara;;X;;bukan\n');
  assert.equal(ok.rows.length, 1);
  assert.deepEqual(ok.rows[0], { tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: '41214', nama_mk: 'Pemrograman', kelas: 'A', dosen_email: 'dosen@x.ac.id' });
  assert.equal(ok.galat.length, 2);
  assert.match(ok.galat[0], /ganda/);
  assert.match(ok.galat[1], /tahun_akademik.*semester.*kode_mk.*kelas.*email/);
  assert.equal(bacaCSVKelas('ta,semester,kode,kelas,email\n2026/2027,Genap,1,B,a@b.cd').rows.length, 1);
  assert.match(bacaCSVKelas('a;b\n1;2').galat[0], /Kolom tidak ada/);
});

test('status per class uses the latest upload; periods newest first; reminders grouped per lecturer', () => {
  const kelas = [{ ...KELAS }, { ...KELAS, id: 2, kode_mk: '41299', kelas: 'B', dosen_email: 'b@x.id' },
    { ...KELAS, id: 3, kode_mk: '41300', kelas: 'C', dosen_email: 'B@x.id', nama_mk: 'Hidrologi' }];
  kelas[0].dosen_email = 'a@x.id';
  const st = statusKelas(kelas, [{ kelas_id: 1, diunggah: '2026-11-01T00:00:00Z' }, { kelas_id: 1, diunggah: '2026-11-05T00:00:00Z' }]);
  assert.equal(st[0].versi, 2);
  assert.equal(st[0].terakhir.diunggah, '2026-11-05T00:00:00Z');
  assert.deepEqual(periodeKelas([{ tahun_akademik: '2025/2026', semester: 'Genap' }, { tahun_akademik: '2026/2027', semester: 'Ganjil' },
    { tahun_akademik: '2025/2026', semester: 'Ganjil' }]), ['2026/2027|Ganjil', '2025/2026|Genap', '2025/2026|Ganjil']);
  const p = penerimaBelumUnggah(st, new Map([['b@x.id', 'Budi']]));
  assert.equal(p.length, 1);
  assert.equal(p[0].nama, 'Budi');
  assert.equal(p[0].rinci.split('\n').length, 2);
});
