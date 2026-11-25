// site/led-data.js: chart specs and tables for the LED draft (owner 2026-11-04).
// Fictitious data. Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { grafikButir, tabelGrafik, tabelTren, tabelPendukung } from '../../site/led-data.js';

const TS = 2026;
const D = {
  akreditasi: {
    kerjasama: [{ tahun: 2024, internasional: 1, nasional: 3, wilayah: 2 },
                { tahun: 2026, internasional: 0, nasional: 5, wilayah: 1 }],
    sumber_dana: [{ tahun: 2025, kategori: 'penelitian', luar_negeri: 1, dalam_negeri: 2, pt_mandiri: 4 }],
    publikasi_dtps: [{ tahun: 2026, na1: 1, na2: 2, na3: 0, na4: 3, nb1: 1, nb2: 0, nb3: 2 }],
    ta: [{ tahun_ts: 2026, mahasiswa_aktif: 250, mahasiswa_asing: 2, rerata_ipk: 3.214 }],
    kepuasan: [{ tahun_ts: 2026, aspek: 'etika', sangat_baik: 50, baik: 30, cukup: 20, kurang: 0 }],
  },
  prestasi_agregat: [{ tahun_ts: 2022, tingkat: 'internasional', jumlah: 1 },
                     { tahun_ts: 2026, tingkat: 'nasional', jumlah: 2 },
                     { tahun_ts: 2026, tingkat: 'wilayah_lokal', jumlah: 3 },
                     { tahun_ts: 2021, tingkat: 'nasional', jumlah: 9 }],      // outside 5 TS
  tracer: [{ tahun_lulus: 2024, lulusan: 30, terlacak: 12, waktu_tunggu_bulan: 4.25, sesuai_bidang: 8,
             kerja_wilayah: 2, kerja_nasional: 8, kerja_internasional: 1 }],
  dtps: { jumlah: 10, doktor: 7, jabatan: { lektor: 5, asisten_ahli: 2, guru_besar: 1, tanpa_jabatan: 2 } },
};

test('butir 6: cooperation by level over TS-2..TS, stacked', () => {
  const g = grafikButir('6', D, TS);
  assert.deepEqual(g.kategori, ['2023/2024', '2024/2025', '2025/2026']);
  assert.equal(g.mode, 'tumpuk');
  assert.deepEqual(g.seri.map(s => s.nilai), [[1, 0, 0], [3, 0, 5], [2, 0, 1]]);
});

test('butir 33: publications grouped into national, international, proceedings', () => {
  const g = grafikButir('33', D, TS);
  assert.deepEqual(g.seri.map(s => s.nilai[2]), [3, 3, 3]);   // na1+na2, na3+na4, nb1..nb3
});

test('butir 31: research by funding source; empty data gives no chart', () => {
  assert.deepEqual(grafikButir('31', D, TS).seri.map(s => s.nilai[1]), [4, 2, 1]);
  assert.equal(grafikButir('32', D, TS), null);               // no PkM rows
  assert.equal(grafikButir('34', D, TS), null);               // no outputs
  assert.equal(grafikButir('13', D, TS), null);               // butir without a chart
});

test('butir 43: achievements by level over 5 TS', () => {
  const g = grafikButir('43', D, TS);
  assert.equal(g.kategori.length, 5);
  assert.deepEqual(g.seri.map(s => s.nilai), [[1, 0, 0, 0, 0], [0, 0, 0, 0, 2], [0, 0, 0, 0, 3]]);
});

test('butir 49-52: tracer by graduation year, satisfaction by aspect', () => {
  assert.deepEqual(grafikButir('49', D, TS).seri[0].nilai, [4.25, 0]);
  assert.deepEqual(grafikButir('50', D, TS).seri.map(s => s.nilai[0]), [12, 8]);
  assert.deepEqual(grafikButir('51', D, TS).seri.map(s => s.nilai[0]), [2, 8, 1]);
  const k = grafikButir('52', D, TS);
  assert.equal(k.kategori.length, 7);
  assert.deepEqual(k.seri.map(s => s.nilai[0]), [50, 30, 20, 0]);
});

test('tabelGrafik: header = categories, one row per series, total for stacked', () => {
  const t = tabelGrafik(grafikButir('6', D, TS));
  assert.deepEqual(t[0], ['', '2023/2024', '2024/2025', '2025/2026']);
  assert.deepEqual(t[t.length - 1], ['Jumlah', '6', '0', '6']);
  assert.deepEqual(tabelGrafik(grafikButir('42', D, TS))[1], ['Rerata IPK', '0,00', '0,00', '3,21']);
  assert.equal(tabelGrafik(grafikButir('52', D, TS)).at(-1)[0], 'Kurang');  // no total for %
});

test('tabelTren: scores per TS with change; null without data', () => {
  const angka = v => v.toFixed(2).replace('.', ',');
  const t = tabelTren('33', { 33: { 2024: 2.5, 2025: null, 2026: 3.25 } }, [2024, 2025, 2026], angka);
  assert.deepEqual(t[1], ['Skor butir', '2,50', '—', '3,25', '+0,75']);
  assert.equal(tabelTren('33', {}, [2024, 2025, 2026], angka), null);
});

test('tabelPendukung: DTPS profile for butir 26-28 only', () => {
  const p = tabelPendukung('27', D, TS);
  assert.deepEqual(p.baris[2], ['Berpendidikan S3', '7', '70%']);
  assert.deepEqual(p.baris.at(-1), ['Belum berjabatan akademik', '2', '20%']);
  assert.equal(tabelPendukung('33', D, TS), null);
});

// Narasi merujuk Gambar n dengan angka yang sama dengan grafiknya (pemilik 2026-11-23).
test('kalimatGrafik: time series sentence carries the chart numbers; other charts point to the data table', async () => {
  const { kalimatGrafik, BUTIR_GRAFIK } = await import('../../site/led-data.js');
  const tumpuk = { judul: 'Publikasi ilmiah DTPS', satuan: 'judul', mode: 'tumpuk', kategori: ['2024/2025', '2025/2026', '2026/2027'],
    seri: [{ nama: 'Jurnal nasional', nilai: [2, 3, 5] }, { nama: 'Jurnal internasional', nilai: [1, 0, 4] }, { nama: 'Prosiding', nilai: [0, 0, 0] }] };
  assert.equal(kalimatGrafik(tumpuk, 3), 'Gambar 3 menunjukkan publikasi ilmiah DTPS pada 2024/2025 s.d. 2026/2027 (judul): '
    + 'jurnal nasional 2, 3, 5; jurnal internasional 1, 0, 4; prosiding 0, 0, 0; jumlahnya 3, 3, 9.');
  const ipk = { judul: 'Rerata IPK lulusan per TS', satuan: 'IPK', mode: 'kelompok', desimal: 2, kategori: ['2025/2026', '2026/2027'],
    seri: [{ nama: 'Rerata IPK', nilai: [3.215, 3.4] }] };
  assert.equal(kalimatGrafik(ipk, 1), 'Gambar 1 menunjukkan rerata IPK lulusan per TS pada 2025/2026 s.d. 2026/2027 (IPK): rerata IPK 3,21, 3,40.');
  const kepuasan = { judul: 'Kepuasan pengguna lulusan, TS 2026/2027', satuan: '%', mode: 'tumpuk', kategori: ['Etika', 'Komunikasi'],
    seri: [{ nama: 'Sangat baik', nilai: [40, 30] }] };
  assert.equal(kalimatGrafik(kepuasan, 7), 'Gambar 7 menyajikan kepuasan pengguna lulusan, TS 2026/2027; angka lengkapnya ada pada Data Gambar 7.');
  const pkm = { judul: 'PkM DTPS yang melibatkan mahasiswa', satuan: 'judul', mode: 'kelompok', kategori: ['2025/2026', '2026/2027'],
    seri: [{ nama: 'Seluruh judul', nilai: [3, 2] }, { nama: 'Melibatkan mahasiswa', nilai: [0, 0] }] };
  assert.equal(kalimatGrafik(pkm, 2), 'Gambar 2 menunjukkan PkM DTPS yang melibatkan mahasiswa pada 2025/2026 s.d. 2026/2027 (judul): seluruh judul 3, 2; melibatkan mahasiswa 0, 0.');
  assert.ok(BUTIR_GRAFIK.includes('33') && BUTIR_GRAFIK.includes('52'));
});
