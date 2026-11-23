// CPMK dan RPS per MK (pemilik 2026-11-17, OBE O2; site/cpmk.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { uraiIndikator, cplMK, strukturKosong, tambahCpmk, hapusCpmk, tambahSub, hapusSub, tambahAsesmen, hapusAsesmen,
  gantiNamaAsesmen, aturBobot, jumlahBobot, dataTemplat, statusStruktur } from '../../site/cpmk.js';
import { periksaStruktur } from '../../site/templat-cpl.js';

test('indikator: daftar bernomor (K26), kode terpetakan (K21), kosong', () => {
  assert.deepEqual(uraiIndikator('1. Menunjukkan integritas 2. Menunjukkan sikap'), ['Menunjukkan integritas', 'Menunjukkan sikap']);
  assert.deepEqual(uraiIndikator('Satu kalimat'), ['Satu kalimat']);
  const refCpl = [{ kurikulum: 'K26', kode: 'B', rumusan: 'Etika', indikator: '1. Identifikasi 2. Tentukan', urutan: 2 },
                  { kurikulum: 'K26', kode: 'A', rumusan: 'Sikap', indikator: '1. Integritas', urutan: 1 },
                  { kurikulum: 'K21', kode: 'a', rumusan: 'Sains', indikator: null }, { kurikulum: 'K21', kode: 'c', rumusan: 'Desain', indikator: '' }];
  const peta = [{ kurikulum: 'K26', kode_mk: 'S1', cpl: 'B' }, { kurikulum: 'K26', kode_mk: 'S1', cpl: 'A' },
                { kurikulum: 'K21', kode_mk: 'T1', cpl: 'a', indikator: 'a-1, a-5' }, { kurikulum: 'K21', kode_mk: 'T1', cpl: 'c', indikator: null }];
  const k26 = cplMK(refCpl, peta, 'K26', 'S1');
  assert.deepEqual(k26.cpl.map(c => c.kode), ['A', 'B']);
  assert.deepEqual(k26.indikator, [{ kode: 'A1', cpl: 'A', teks: 'Integritas' }, { kode: 'B1', cpl: 'B', teks: 'Identifikasi' },
                                   { kode: 'B2', cpl: 'B', teks: 'Tentukan' }]);
  assert.deepEqual(cplMK(refCpl, peta, 'K21', 'T1').indikator, [{ kode: 'a1', cpl: 'a', teks: '' }, { kode: 'a5', cpl: 'a', teks: '' },
                                                                { kode: 'c1', cpl: 'c', teks: 'Desain' }]);
});

test('struktur: tambah, ganti nama, hapus menjaga bobot konsisten; lengkap = lolos periksa templat', () => {
  const d = strukturKosong();
  assert.equal(statusStruktur(d, []), 'kosong');
  const c1 = tambahCpmk(d), c2 = tambahCpmk(d);
  assert.deepEqual([c1, c2], ['CPMK-1', 'CPMK-2']);
  const s11 = tambahSub(d, c1), s21 = tambahSub(d, c2), s12 = tambahSub(d, c1);
  assert.deepEqual(d.sub.map(s => s.kode), ['Sub-CPMK-1-1', 'Sub-CPMK-1-2', 'Sub-CPMK-2-1']);   // urut menurut induk
  tambahAsesmen(d, ' Tugas  1 '); tambahAsesmen(d, 'UTS');
  assert.throws(() => tambahAsesmen(d, 'uts'), /sudah ada/);
  aturBobot(d.bobot[s11] = {}, 'Tugas 1', '10'); aturBobot(d.bobot[s12] = {}, 'UTS', '20,5'); aturBobot(d.bobot[s21] = {}, 'UTS', 30);
  aturBobot(d.bobot[s21], 'Tugas 1', '0');
  assert.deepEqual(jumlahBobot(d), { kolom: { 'Tugas 1': 10, UTS: 50.5 }, total: 60.5 });
  gantiNamaAsesmen(d, 'UTS', 'Ujian Tengah Semester');
  assert.deepEqual(d.bobot[s12], { 'Ujian Tengah Semester': 20.5 });
  d.cpmk.forEach((c, i) => { c.rumusan = 'Mampu ' + i; c.indikator = { A1: 1 }; });
  d.sub.forEach(s => { s.rumusan = 'Sub'; });
  const t = dataTemplat(d, { cpl: [{ kode: 'A', rumusan: 'Sikap' }], indikator: [{ kode: 'A1', cpl: 'A', teks: 'x' }] });
  assert.deepEqual(periksaStruktur(t), []);
  assert.equal(statusStruktur(d, periksaStruktur(t)), 'lengkap');
  hapusAsesmen(d, 'Tugas 1');
  assert.deepEqual(d.bobot[s11], {});
  assert.match(periksaStruktur(dataTemplat(d, t)).join(' '), /Sub-CPMK-1-1: belum punya bobot/);
  hapusCpmk(d, c1);
  assert.deepEqual(d.sub.map(s => s.kode), ['Sub-CPMK-2-1']);
  assert.ok(!(s11 in d.bobot) && !(s12 in d.bobot));
  hapusSub(d, s21);
  assert.deepEqual([d.sub, d.bobot], [[], {}]);
});

test('versi data struktur CPMK tetap 1 (constraint 102; tidak tersentuh stamp_versions)', async () => {
  const { strukturKosong, VERSI_DATA } = await import('../../site/cpmk.js');
  assert.equal(VERSI_DATA, '1');
  assert.equal(strukturKosong().versi, '1');
});

test('hitung bobot otomatis (cara Simulator Pemetaan Sub-CPMK UP, pemilik 2026-11-19)', async () => {
  const { hitungOtomatis, hitungAwal, normalisasi } = await import('../../site/cpmk.js');
  assert.deepEqual(normalisasi([15, 30, 25, 30]), [15, 30, 25, 30]);
  assert.deepEqual(normalisasi([0, 0]), [50, 50]);
  const d = { sub: [{ kode: 'S1' }, { kode: 'S2' }, { kode: 'S3' }], asesmen: [{ nama: 'Kuis 1' }, { nama: 'Tugas 1' }, { nama: 'UTS' }, { nama: 'UAS' }], bobot: {},
    hitung: { mode: 'otomatis', prioritas: 'asesmen', bulat: 1, asesmen: { 'Kuis 1': 15, 'Tugas 1': 30, UTS: 25, UAS: 30 }, sub: { S1: 30, S2: 30, S3: 40 },
      sel: { S1: ['Kuis 1', 'Tugas 1', 'UTS'], S2: ['Tugas 1', 'UTS'], S3: ['Tugas 1', 'UAS'] } } };
  const h = hitungOtomatis(d);
  const jml = Object.values(h.bobot).flatMap(b => Object.values(b)).reduce((a, b) => a + b, 0);
  assert.equal(jml, 100);
  for (const v of Object.values(h.bobot).flatMap(b => Object.values(b))) assert.equal(v, Math.round(v));   // pembulatan 1%
  assert.deepEqual(h.colSum, [15, 30, 25, 30]);                                                             // prioritas asesmen tepat
  assert.ok(h.simpang <= 1);
  assert.deepEqual(h.belumDiukur, []);
  d.hitung.sel.S3 = [];
  assert.deepEqual(hitungOtomatis(d).belumDiukur, ['S3']);
  const d2 = { sub: [{ kode: 'A' }, { kode: 'B' }], asesmen: [{ nama: 'T' }, { nama: 'U' }], bobot: { A: { T: 20, U: 30 }, B: { U: 50 } } };
  const awal = hitungAwal(d2);
  assert.deepEqual(awal.sel, { A: ['T', 'U'], B: ['U'] });
  assert.deepEqual(hitungOtomatis({ ...d2, hitung: awal }).bobot, { A: { T: 20, U: 30 }, B: { U: 50 } });   // bobot lama dipertahankan
});

test('aturan komposisi: reguler UTS+UAS dan Penugasan ≥ 20%, praktikum Laporan Akhir, kulminasi bebas', async () => {
  const { periksaKomposisi, jenisKuliah, kelompokAsesmen } = await import('../../site/rps.js');
  assert.equal(jenisKuliah({ sks: 3, sks_praktikum: 0 }), 'reguler');
  assert.equal(jenisKuliah({ sks: 1, sks_praktikum: 1 }), 'praktikum');
  assert.equal(jenisKuliah({ sks: 4, capstone: true }), 'kulminasi');
  assert.equal(kelompokAsesmen({ nama: 'Tugas 1' }), 'penugasan');
  assert.equal(kelompokAsesmen({ nama: 'Kuis 1' }), 'ujian');
  assert.equal(kelompokAsesmen({ nama: 'Kuis 1', kelompok: 'penugasan' }), 'penugasan');
  const S = (bobot, asesmen) => ({ sub: [{ kode: 'S1' }], asesmen, bobot: { S1: bobot } });
  const baik = S({ 'Tugas 1': 20, UTS: 40, UAS: 40 }, [{ nama: 'Tugas 1' }, { nama: 'UTS' }, { nama: 'UAS' }]);
  assert.deepEqual(periksaKomposisi({ struktur: baik, mk: { sks: 3 } }), []);
  const kurang = S({ 'Tugas 1': 10, UTS: 90 }, [{ nama: 'Tugas 1' }, { nama: 'UTS' }]);
  const p = periksaKomposisi({ struktur: kurang, mk: { sks: 3 } }).map(x => x.pesan).join(' | ');
  assert.match(p, /UTS dan UAS/); assert.match(p, /Penugasan 10%/);
  assert.match(periksaKomposisi({ struktur: S({ Laporan: 100 }, [{ nama: 'Laporan' }]), mk: { sks: 1, sks_praktikum: 1 } })[0].pesan, /Laporan Akhir/);
  assert.deepEqual(periksaKomposisi({ struktur: S({ 'Laporan Akhir': 100 }, [{ nama: 'Laporan Akhir' }]), mk: { sks: 1, sks_praktikum: 1 } }), []);
  assert.deepEqual(periksaKomposisi({ struktur: S({ Sidang: 100 }, [{ nama: 'Sidang' }]), mk: { sks: 4, capstone: true } }), []);
});
