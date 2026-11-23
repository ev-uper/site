// Simulasi data "bagaimana jika" (owner 2026-11-11).
import test from 'node:test';
import assert from 'node:assert/strict';
import { skenarioKosong, terapkanSkenario, uraiSkenario, bandingkan } from '../../site/simulasi-skor.js';

const S = {
  D: { dtps: { jumlah: 10, doktor: 7, jabatan: { lektor: 5, asisten_ahli: 2, guru_besar: 1, tanpa_jabatan: 2 },
               karya_utama_rinci: [{ slug: 'a', tahun: 2026 }, { slug: 'a', tahun: 2025 }, { slug: 'b', tahun: 2022 }] },
       akreditasi: { publikasi_dtps: [{ tahun: 2026, na4: 2, na1: 1 }], luaran_dtps: [],
                     sumber_dana: [{ tahun: 2026, kategori: 'pkm', dalam_negeri: 1 }],
                     kegiatan_mhs: [{ tahun: 2026, kategori: 'penelitian', total: 3, dengan_mahasiswa: 1 }],
                     rekognisi_dtps: [] } },
  DANA: [{ tahun: 2025, bulan: 10, kategori: 'penelitian', besaran_dana: 1 }],
  DOSEN_KAT: [{ kategori: 'tetap' }],
};
const asli = JSON.stringify(S);

test('empty scenario changes nothing and describes nothing', () => {
  const r = terapkanSkenario(S, skenarioKosong(), 2026);
  assert.deepEqual(uraiSkenario(skenarioKosong()), []);
  assert.deepEqual(r.D.dtps, S.D.dtps);
  assert.equal(JSON.stringify(S), asli);
});

test('promotions run bottom-up, so one lecturer can climb two steps; impossible ones are refused', () => {
  const sk = skenarioKosong();
  sk.naik['asisten_ahli>lektor'] = 2; sk.naik['lektor>lektor_kepala'] = 7;
  const r = terapkanSkenario(S, sk, 2026);
  assert.deepEqual(r.D.dtps.jabatan, { lektor: 0, asisten_ahli: 0, guru_besar: 1, tanpa_jabatan: 2, lektor_kepala: 7 });
  sk.naik['lektor>lektor_kepala'] = 8;
  assert.match(terapkanSkenario(S, sk, 2026).galat, /Hanya ada 7 DTPS Lektor/);
  const s3 = skenarioKosong(); s3.doktor = 4;
  assert.match(terapkanSkenario(S, s3, 2026).galat, /Hanya 3 DTPS yang belum S3/);
  assert.equal(JSON.stringify(S), asli);
});

test('new lecturers raise NDTPS, rank, doctorates, and the staff category list', () => {
  const sk = skenarioKosong();
  sk.baru = { n: 2, jabatan: 'lektor', doktor: true };
  const r = terapkanSkenario(S, sk, 2026);
  assert.equal(r.D.dtps.jumlah, 12); assert.equal(r.D.dtps.doktor, 9); assert.equal(r.D.dtps.jabatan.lektor, 7);
  assert.equal(r.DOSEN_KAT.filter(d => d.kategori === 'tetap').length, 3);
  assert.equal(terapkanSkenario({ ...S, DOSEN_KAT: null }, sk, 2026).DOSEN_KAT.length, 0);   // category not filled: left empty
});

test('publications and outputs are added to the TS row (created when missing)', () => {
  const sk = skenarioKosong();
  sk.publikasi.na4 = 3; sk.publikasi.nb3 = 1; sk.luaran.paten = 1; sk.luaran.bc = 2;
  const r = terapkanSkenario(S, sk, 2026);
  assert.deepEqual(r.D.akreditasi.publikasi_dtps[0], { tahun: 2026, na4: 5, na1: 1, na3: 0, na2: 0, nb3: 1, nb2: 0, nb1: 0 });
  assert.deepEqual(r.D.akreditasi.luaran_dtps, [{ tahun: 2026, paten: 1, ttg: 0, bc: 2, hki: 0, lainnya: 0 }]);
  assert.match(uraiSkenario(sk).join('; '), /3 Jurnal internasional bereputasi/);
});

test('activities: funding source rows, student involvement capped, money split per title in TS', () => {
  const sk = skenarioKosong();
  sk.kegiatan.penelitian = { luar_negeri: 1, dalam_negeri: 2, pt_mandiri: 0, dana: 300000000, mahasiswa: 9 };
  sk.kegiatan.pkm.dalam_negeri = 1;
  const r = terapkanSkenario(S, sk, 2026);
  const sd = r.D.akreditasi.sumber_dana;
  assert.deepEqual(sd.find(x => x.kategori === 'penelitian'), { tahun: 2026, kategori: 'penelitian', luar_negeri: 1, dalam_negeri: 2, pt_mandiri: 0, tanpa_sumber: 0 });
  assert.equal(sd.find(x => x.kategori === 'pkm').dalam_negeri, 2);
  assert.deepEqual(r.D.akreditasi.kegiatan_mhs.find(x => x.kategori === 'penelitian'), { tahun: 2026, kategori: 'penelitian', total: 6, dengan_mahasiswa: 4 });
  const baru = r.DANA.filter(x => x.simulasi && x.kategori === 'penelitian');
  assert.equal(baru.length, 3); assert.equal(baru[0].besaran_dana, 100000000);
  assert.ok(baru.every(x => x.tahun === 2026 && x.bulan === 1));   // TS = calendar year for months before September
  assert.match(uraiSkenario(sk).join('; '), /3 penelitian baru \(dana Rp300\.000\.000\), 3 melibatkan mahasiswa/);
});

test('main works and recognition add distinct lecturers, capped by NDTPS in the window', () => {
  const sk = skenarioKosong();
  sk.karya_utama = 3; sk.rekognisi = 2;
  const r = terapkanSkenario(S, sk, 2026);
  assert.equal(new Set(r.D.dtps.karya_utama_rinci.filter(x => x.tahun >= 2024).map(x => x.slug)).size, 4);
  assert.equal(r.D.akreditasi.rekognisi_dtps.length, 2);
  sk.karya_utama = 10;   // 'a' already counted in 2024-2026; 'b' (2022) is outside the window
  assert.match(terapkanSkenario(S, sk, 2026).galat, /Hanya 9 DTPS/);
});

test('comparison lists only changed items, largest weighted gain first', () => {
  const kini = { skorButir: { 1: { n: 2, ada: true }, 2: { n: 3, ada: true }, 3: { n: 0, ada: false } } };
  const sim = { skorButir: { 1: { n: 3, ada: true }, 2: { n: 3, ada: true }, 3: { n: 2, ada: true } } };
  const b = bandingkan(kini, sim, no => ({ 1: 1, 2: 5, 3: 2 })[no]);
  assert.deepEqual(b.map(x => [x.no, x.kini, x.sim, x.poin]), [['3', null, 2, 4], ['1', 2, 3, 1]]);
});
