// Kelengkapan jadwal berhalangan (instal-lengkap.sql, pemilik 2026-11-21): site/jadwal-berhalangan.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import { tanggalSemester, semesterBerikut, wajibIsi, kelengkapanBerhalangan, penerimaBerhalangan } from '../../site/jadwal-berhalangan.js';

test('rentang semester dan semester berikutnya', () => {
  assert.deepEqual(tanggalSemester('2026/2027', 'Genap'), { dari: '2027-03-01', sampai: '2027-08-31' });
  assert.deepEqual(tanggalSemester('2027/2028', 'Ganjil'), { dari: '2027-09-01', sampai: '2028-02-29' });   // kabisat
  assert.deepEqual(tanggalSemester('2026/2027', 'Ganjil'), { dari: '2026-09-01', sampai: '2027-02-28' });
  assert.equal(tanggalSemester('2026', 'Ganjil'), null);
  assert.deepEqual(semesterBerikut({ ta: '2026/2027', sm: 'Ganjil' }), { ta: '2026/2027', sm: 'Genap' });
  assert.deepEqual(semesterBerikut({ ta: '2026/2027', sm: 'Genap' }), { ta: '2027/2028', sm: 'Ganjil' });
});

test('status per dosen: lengkap, diisi (mingguan/tanggal/rentang semester itu), belum; yang tidak wajib dilewati', () => {
  const dosen = [{ id: 'a', nama: 'Ani', email: 'a@u' }, { id: 'b', nama: 'Budi', email: 'b@u' }, { id: 'c', nama: 'Cici', email: 'c@u' },
    { id: 'd', nama: 'Dedi', email: '' }, { id: 'e', nama: 'Eko', email: 'e@u' }, { id: 'p', nama: 'Dekan', peran: 'pimpinan', email: 'p@u' },
    { id: 'x', nama: 'Asesor', peran: 'asesor' }, { id: 'z', nama: 'Lama', aktif: false }];
  const k = kelengkapanBerhalangan({ dosen, ta: '2026/2027', sm: 'Genap',
    mingguan: [{ dosen_id: 'b', tahun_akademik: '2026/2027', semester: 'Genap' }, { dosen_id: 'c', tahun_akademik: '2026/2027', semester: 'Ganjil' }],
    tanggalan: [{ dosen_id: 'd', tanggal: '2027-04-02' }, { dosen_id: 'c', tanggal: '2026-12-01' }],
    rentang: [{ dosen_id: 'e', mulai: '2027-02-20', selesai: '2027-03-05' }, { dosen_id: 'c', mulai: '2027-09-01', selesai: '2027-09-03' }],
    konfirmasi: [{ dosen_id: 'a', tahun_akademik: '2026/2027', semester: 'Genap', dikonfirmasi_pada: 't' },
                 { dosen_id: 'c', tahun_akademik: '2026/2027', semester: 'Ganjil' }] });
  assert.deepEqual(k.baris.map(x => [x.dosen.id, x.status]), [['c', 'belum'], ['b', 'diisi'], ['d', 'diisi'], ['e', 'diisi'], ['a', 'lengkap']]);
  assert.deepEqual(k.ringkas, { lengkap: 1, diisi: 3, belum: 1, n: 5 });
  assert.equal(k.baris.find(x => x.dosen.id === 'a').dikonfirmasi_pada, 't');
  assert.equal(wajibIsi({ aktif: true, peran: 'admin' }), true);
  const p = penerimaBerhalangan(k, { ta: '2026/2027', sm: 'Genap' });
  assert.deepEqual(p.map(x => x.email), ['c@u', 'b@u', 'e@u']);                  // Dedi tanpa email, Ani sudah lengkap
  assert.equal(p[0].rinci, '- Semester Genap 2026/2027: belum ada isian dan belum ditandai lengkap');
  assert.equal(p[1].rinci, '- Semester Genap 2026/2027: 1 isian, belum ditandai lengkap');
});
