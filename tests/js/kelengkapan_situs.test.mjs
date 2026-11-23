// Kelengkapan situs publik (pemilik 2026-11-21): site/kelengkapan-situs.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { periksaKelengkapan, ringkasKelengkapan } from '../../site/kelengkapan-situs.js';

const cari = (xs, id) => xs.find(x => x.id === id);

test('data kosong: semua bagian kosong, jadwal TA boleh kosong', () => {
  const xs = periksaKelengkapan({});
  assert.ok(xs.every(x => x.status === 'kosong'));
  const r = ringkasKelengkapan(xs);
  assert.equal(r.bolehKosong, 1);
  assert.equal(r.kosong, xs.length - 1);
  assert.equal(r.terisi + r.sebagian, 0);
});

test('status mengikuti isi data.json', () => {
  const D = {
    profil: { sambutan: 'Selamat datang', sejarah: '', pengelola: [{ jabatan: 'Ketua Program Studi', nama: 'A' }] },
    vmts: { ps: { visi: 'V', misi: 'M', tujuan: '', strategi: '' } },
    akreditasi_prodi: { peringkat: 'Baik Sekali', lembaga: 'LAM Teknik' },
    kurikulum: [{ kode: 'K26', cpl: [{ kode: 'A' }], profil: [{ kode: 'PL-1' }], mk: [{ cpl: ['A'] }, { cpl: [] }] }],
    dosen: [{ nama: 'A', foto: 'f.webp', sinta_id: '1', topik_keahlian: ['x'] }, { nama: 'B' }],
    situs: { laboratorium: ['Lab 1', 'Lab 2'], tagline: 'T', karier: [], pendaftaran: 'https://pmb', sosial: {} },
    laboratorium: [{ nama: 'Lab 1' }],
    alumni: { responden: 3, min: 5 },
    jadwal_ta: [{}],
  };
  const xs = periksaKelengkapan(D);
  assert.equal(cari(xs, 'sambutan').status, 'terisi');
  assert.equal(cari(xs, 'sejarah').status, 'kosong');
  assert.equal(cari(xs, 'pengelola').status, 'sebagian');
  assert.equal(cari(xs, 'vmts').status, 'sebagian');
  assert.equal(cari(xs, 'vmts').nilai, 'visi, misi');
  assert.equal(cari(xs, 'akreditasi').status, 'sebagian');            // tanpa SK dan tanggal berlaku
  assert.match(cari(xs, 'akreditasi').catatan, /nomor SK/);
  assert.equal(cari(xs, 'kurikulum').status, 'sebagian');
  assert.match(cari(xs, 'kurikulum').catatan, /1 MK belum punya CPL/);
  assert.equal(cari(xs, 'foto-dosen').nilai, '1 dari 2');
  assert.equal(cari(xs, 'foto-dosen').status, 'sebagian');
  assert.equal(cari(xs, 'laboratorium').status, 'sebagian');
  assert.equal(cari(xs, 'alumni').status, 'sebagian');
  assert.equal(cari(xs, 'jadwal-ta').status, 'terisi');
  assert.equal(cari(xs, 'tagline').status, 'sebagian');
  assert.equal(cari(xs, 'pendaftaran').status, 'terisi');
  assert.equal(cari(xs, 'instagram').status, 'kosong');
});

test('setiap tautan isian menunjuk berkas yang ada di site/ dan ada di menu', () => {
  const menu = readFileSync(new URL('../../site/menu.js', import.meta.url), 'utf8');
  const berkas = new Set(periksaKelengkapan({}).map(x => x.isi?.href).filter(Boolean).map(h => h.split('?')[0]));
  for (const f of berkas) {
    assert.ok(readFileSync(new URL(`../../site/${f}`, import.meta.url), 'utf8').length > 0, f);
    assert.ok(menu.includes(`'${f}`), `${f} tidak ada di menu.js`);
  }
  assert.ok(menu.includes("'kelengkapan-situs.html'"));
});
