// Usulan penguji seminar/sidang TA (pemilik 2026-11-17; site/usulan-penguji.js memakai pembimbing.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { siapkan } from '../../site/pembimbing.js';
import { usulPenguji, bebanUji, tsDari } from '../../site/usulan-penguji.js';

const D = {
  keahlian_baku: { bidang: [{ kode: 'AIR', nama: 'Sumber daya air' }],
                   topik: [{ kode: 'AIR01', bidang: 'AIR', nama: 'Hidrologi banjir', sinonim: ['banjir'], padanan: ['flood'] }] },
  dosen: [
    { nama: 'Ani', slug: 'ani', topik_keahlian: ['AIR01'] },
    { nama: 'Budi', slug: 'budi', bidang_keahlian: 'Hidrologi dan banjir' },
    { nama: 'Cici', slug: 'cici', bidang_keahlian: 'Struktur beton' },
    { nama: 'Dodi', slug: 'dodi', bidang_keahlian: 'Banjir perkotaan' },
  ],
  publikasi: [{ judul: 'Flood forecasting in Ciliwung', tahun: 2025, penulis: [{ nama: 'Budi', slug: 'budi' }] }],
  kegiatan: [],
};
const DOSEN = [{ nidn: '1', nama: 'Ani' }, { nidn: '2', nama: 'Budi' }, { nidn: '3', nama: 'Cici' }];   // Dodi bukan calon penguji

test('TS dari tanggal: September membuka TS berikutnya', () => {
  assert.equal(tsDari('2026-08-31'), 2026);
  assert.equal(tsDari('2026-09-01'), 2027);
  assert.equal(tsDari(''), 0);
});

test('beban menguji per NIDN pada satu TS, tanpa jadwal batal', () => {
  const b = bebanUji([{ tanggal: '2026-10-01', penguji: ['2', '3'] }, { tanggal: '2026-11-01', penguji: ['2'] },
                      { tanggal: '2026-11-02', penguji: ['2'], status: 'batal' }, { tanggal: '2026-03-01', penguji: ['2'] }], 2027);
  assert.deepEqual([...b], [['2', 2], ['3', 1]]);
});

test('usulan cocok dengan judul, tanpa pembimbing dan tanpa dosen di luar daftar calon', () => {
  const m = siapkan(D);
  const xs = usulPenguji('Analisis banjir DAS Ciliwung', m, DOSEN, { kecuali: new Set(['1']), beban: new Map([['2', 4]]) });
  assert.deepEqual(xs.map(x => x.nama), ['Budi']);            // Ani pembimbing; Dodi bukan calon; Cici tidak cocok
  assert.equal(xs[0].beban, 4);
  assert.ok(xs[0].alasan.length >= 1);
  assert.deepEqual(usulPenguji('', m, DOSEN), []);
  assert.deepEqual(usulPenguji('Banjir', null, DOSEN), []);
});
