// site/bkd.js and Tabel 4.c with non-DTPS lecturers (owner 2026-11-06).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { totalBkd, totalLebih, taSekarang, periksaBkd, diLuarRentang, ubahLangsung, pendidikanPS, pendidikanTotal } from '../../site/bkd.js';
import { petaDaftar } from '../../site/lkps.js';

// Bagian C sebuah LKD Genap: pendidikan 9,625 dipecah 7,125 + 2,5 kelas prodi lain.
const genap = { tahun_akademik: '2025/2026', semester: 'genap', sks_pendidikan: 7.125, sks_ps_lain_dalam: 2.5,
  sks_penelitian: 3.75, sks_pkm: 2, sks_penunjang: 0.5, sks_lebih_pendidikan: 9.625, sks_lebih_penunjang: 0.375 };

test('totals: SKS BKD covers the education split, SKS Lebih stays apart', () => {
  assert.equal(totalBkd(genap), 15.875);
  assert.equal(totalLebih(genap), 10);
  assert.ok(!diLuarRentang(genap));
  assert.ok(diLuarRentang({ sks_pendidikan: 11 }));
  assert.ok(diLuarRentang({ sks_pendidikan: 16.5 }));
});

test('taSekarang: September opens the next academic year', () => {
  assert.equal(taSekarang(new Date(2026, 7, 31)), '2025/2026');
  assert.equal(taSekarang(new Date(2026, 8, 1)), '2026/2027');
});

test('periksaBkd: LKD required for new entries only', () => {
  assert.deepEqual(periksaBkd(genap, true, true), []);
  assert.match(periksaBkd(genap, false, true).join(), /LKD/);
  assert.deepEqual(periksaBkd(genap, false, false), []);
  assert.match(periksaBkd({ ...genap, tahun_akademik: '2025/2027' }, true, true).join(), /Tahun akademik/);
  assert.match(periksaBkd({ ...genap, semester: '' }, true, true).join(), /Semester/);
  assert.match(periksaBkd({ ...genap, sks_pkm: -1 }, true, true).join(), /angka/);
  assert.match(periksaBkd({ ...genap, sks_pkm: NaN }, true, true).join(), /angka/);
  assert.match(periksaBkd({ tahun_akademik: '2025/2026', semester: 'genap' }, true, true).join(), /bagian C/);
});

test('ubahLangsung: only before verification', () => {
  assert.ok(ubahLangsung({ verifikasi: 'diajukan' }));
  assert.ok(ubahLangsung({ verifikasi: 'ditolak' }));
  assert.ok(!ubahLangsung({ verifikasi: 'terverifikasi' }));
});

test('4c: lecturers outside DTPS listed without V; SKS Lebih never counted', () => {
  const L = petaDaftar({ ts: 2026, prodi: 'Uji', D: { akreditasi: {} }, daftar: {
    dosen: [{ nama: 'Adi', nidn: '1', dtps: true, aktif: true, peran: 'dosen' },
            { nama: 'Tamu', nidn: '2', dtps: false, aktif: true, peran: 'dosen', kategori: 'tidak_tetap' },   // DTT (dosen-hitung.js)
            { nama: 'Staf', nidn: '3', dtps: false, aktif: true, peran: 'admin' },
            { nama: 'Asesor', nidn: '4', dtps: false, aktif: true, peran: 'asesor' }],
    bkd: [{ nidn: '1', tahun_akademik: '2025/2026', sks_pendidikan: 7, sks_ps_lain_dalam: 2, sks_penelitian: 3, sks_lebih_pendidikan: 9 },
          { nidn: '1', tahun_akademik: '2025/2026', sks_pendidikan: 8, sks_penelitian: 1 },
          { nidn: '2', tahun_akademik: '2025/2026', sks_pendidikan: 6 },
          { nidn: '4', tahun_akademik: '2025/2026', sks_pendidikan: 6 }] } });
  assert.deepEqual([L['4c'].B11, L['4c'].C11, L['4c'].D11, L['4c'].E11, L['4c'].G11], ['Adi', 'V', 15, 2, 4]);
  assert.deepEqual([L['4c'].B12, L['4c'].C12, L['4c'].D12], ['Tamu', undefined, 6]);
  assert.equal(L['4c'].B13, undefined, 'no BKD, assessor never listed');
});

test('education: total typed, this PS = total minus other PS; old rows show the total back', () => {
  assert.equal(pendidikanPS(9.625, 2.5, null), 7.125);
  assert.equal(pendidikanPS(9.625, null, null), 9.625);
  assert.equal(pendidikanPS(null, 2, null), null);
  assert.equal(pendidikanTotal(genap), 9.625);
  assert.equal(pendidikanTotal({ sks_pendidikan: 9 }), 9);
  assert.match(periksaBkd({ ...genap, sks_pendidikan: pendidikanPS(2, 2.5, null) }, true, true).join(), /melebihi total/);
});
