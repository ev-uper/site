// Capaian IKU/IKT otomatis dari data.json (owner 2026-11-11; instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { SUMBER_IKU, OPSI_SUMBER, hitungSumber, denganTambahan, muatTambahan, petunjukSumber } from '../../site/iku-otomatis.js';

const D = {
  dtps: { jumlah: 10, doktor: 7 },
  publikasi: [{ tahun_ts: 2026, sdgs: [6] }, { tahun_ts: 2026 }, { tahun_ts: 2025 }],
  kegiatan: [{ tahun_ts: 2026, kategori: 'penelitian', sdgs: [11] }, { tahun_ts: 2026, kategori: 'pkm' }],
  luaran_dosen: [{ tahun_ts: 2026, sdgs: [9] }],
  rekognisi: [{ tahun_ts: 2026 }, { tahun_ts: 2024 }],
  prestasi_agregat: [{ tahun_ts: 2026, jumlah: 3 }, { tahun_ts: 2026, jumlah: 2 }],
  akreditasi: { kerjasama: [{ tahun: 2026, internasional: 1, nasional: 2, wilayah: 3, tanpa_tingkat: 0 }] },
  tracer: [{ tahun_lulus: 2025, lulusan: 40, terlacak: 32, wt_kurang_3: 8, waktu_tunggu_bulan: 3.6, sesuai_bidang: 24 }],
};

test('every source has a unique id and a label', () => {
  assert.equal(new Set(SUMBER_IKU.map(s => s[0])).size, SUMBER_IKU.length);
  assert.equal(OPSI_SUMBER.length, SUMBER_IKU.length);
});

test('counts and ratios for the TS', () => {
  const v = id => hitungSumber(id, D, 2026)?.nilai;
  assert.equal(v('publikasi_jumlah'), 2);
  assert.equal(v('publikasi_per_dtps'), 0.2);
  assert.equal(v('penelitian_jumlah'), 1);
  assert.equal(v('pkm_jumlah'), 1);
  assert.equal(v('luaran_jumlah'), 1);
  assert.equal(v('karya_sdgs_jumlah'), 3);
  assert.equal(v('karya_sdgs_persen'), 60);       // 3 of 5 works in TS
  assert.equal(v('rekognisi_jumlah'), 1);
  assert.equal(v('prestasi_mhs_jumlah'), 5);
  assert.equal(v('kerjasama_jumlah'), 6);
  assert.equal(v('dtps_doktor_persen'), 70);
});

test('tracer uses graduates of TS-1', () => {
  const v = id => hitungSumber(id, D, 2026)?.nilai;
  assert.equal(v('tracer_wt_kurang_3'), 25);       // 8 / 32
  assert.equal(v('tracer_wt_rata'), 3.6);
  assert.equal(v('tracer_sesuai_bidang'), 75);
  assert.equal(v('tracer_terlacak'), 80);
  assert.equal(hitungSumber('tracer_wt_rata', D, 2025), null);   // no 2024 graduates
});

test('unknown source or missing data -> null', () => {
  assert.equal(hitungSumber('tidak_ada', D, 2026), null);
  assert.equal(hitungSumber('publikasi_jumlah', null, 2026), null);
  assert.equal(hitungSumber('publikasi_per_dtps', { publikasi: [] }, 2026), null);
});

test('DTPS Lektor ke atas (terkini) dan karya utama internasional 3 TS terakhir', () => {
  const X = { dtps: { jumlah: 10, jabatan: { guru_besar: 1, lektor_kepala: 1, lektor: 4, asisten_ahli: 2, tanpa_jabatan: 2 },
    karya_utama_rinci: [{ slug: 'a', tahun: 2027 }, { slug: 'a', tahun: 2026 }, { slug: 'b', tahun: 2025 },
                        { slug: 'c', tahun: 2024 }, { slug: 'd', tahun: 2018 }] } };
  const v = (id, ts) => hitungSumber(id, X, ts)?.nilai;
  assert.equal(v('dtps_lektor_persen', 2027), 60);
  assert.equal(v('dtps_karya_int_persen', 2027), 20);   // a, b (2025–2027)
  assert.equal(v('dtps_karya_int_persen', 2026), 30);   // a, b, c (2024–2026)
  assert.equal(hitungSumber('dtps_lektor_persen', { dtps: { jumlah: 10 } }, 2027), null);
});

test('SKS basic science (kurikulum) dan rerata EDOM tahun akademik TS dari data tambahan', () => {
  const T = { mk: [{ kode: 'MA1', sks: 3, basic_science: true }, { kode: 'FI1', sks: 4, basic_science: true },
                   { kode: 'KI1', sks: 2, basic_science: true, aktif: false }, { kode: 'SI1', sks: 3, basic_science: false }],
    edom: [{ tahun_akademik: '2025/2026', semester: 'Genap', ber_edom: 30, rerata_edom: 3.2 },
           { tahun_akademik: '2025/2026', semester: 'Ganjil', ber_edom: 10, rerata_edom: 2.8 },
           { tahun_akademik: '2024/2025', semester: 'Genap', ber_edom: 20, rerata_edom: 3.9 }] };
  const X = denganTambahan({ dtps: { jumlah: 10 } }, T);
  assert.equal(X.dtps.jumlah, 10);
  assert.equal(hitungSumber('sks_basic_science', X, 2026)?.nilai, 7);
  assert.equal(hitungSumber('edom_rata', X, 2026)?.nilai, 3.1);        // (3.2*30 + 2.8*10) / 40
  assert.equal(hitungSumber('edom_rata', X, 2027), null);              // belum ada EDOM 2026/2027
  assert.equal(hitungSumber('sks_basic_science', denganTambahan({}, { mk: [{ sks: 3 }], edom: null }), 2026), null);
  assert.equal(hitungSumber('edom_rata', { dtps: {} }, 2026), null);   // tanpa data tambahan
  assert.equal(denganTambahan(null, null), null);
});

test('muatTambahan: bagian yang gagal dibaca menjadi null', async () => {
  const sb = { from: () => ({ select: async () => ({ data: [{ sks: 3, basic_science: true }], error: null }) }),
               rpc: async () => ({ data: null, error: { message: 'Could not find the function' } }) };
  assert.deepEqual(await muatTambahan(sb), { mk: [{ sks: 3, basic_science: true }], edom: null });
});

test('petunjuk bila sumber terpasang tetapi datanya belum ada', () => {
  assert.match(petunjukSumber('sks_basic_science'), /^data belum ada: centang basic science/);
  assert.match(petunjukSumber('edom_rata'), /impor rekap EDOM/);
  assert.match(petunjukSumber('tracer_wt_rata'), /tracer study/);
  assert.match(petunjukSumber('publikasi_jumlah'), /data belum ada untuk TS ini/);
  assert.equal(petunjukSumber('tidak_ada'), '');
});
