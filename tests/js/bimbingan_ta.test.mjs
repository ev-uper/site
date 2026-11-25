// Catatan bimbingan TA (pemilik 2026-11-25; site/bimbingan-ta.js, instal-lengkap.sql).
import test from 'node:test';
import assert from 'node:assert/strict';
import { sahBimbingan, statusBimbingan, periksaBimbingan, teksSyarat, hariSejak, labelCara } from '../../site/bimbingan-ta.js';

const kini = new Date('2026-11-25T03:00:00Z');   // 10.00 WIB
const hariLalu = n => new Date(+kini - n * 864e5).toISOString();

test('status: dikonfirmasi, dikembalikan, menunggu, otomatis setelah 14 hari (sama dengan ta_bimbingan_sah)', () => {
  assert.equal(statusBimbingan({ status: 'dikonfirmasi', konfirmasi_oleh: 'Adi' }, kini).label, 'Dikonfirmasi Adi');
  assert.equal(statusBimbingan({ status: 'dikembalikan' }, kini).kode, 'dikembalikan');
  const m = statusBimbingan({ status: 'menunggu', diajukan: hariLalu(3) }, kini);
  assert.deepEqual([m.kode, m.otomatisPada], ['menunggu', '2026-12-06']);
  assert.equal(statusBimbingan({ status: 'menunggu', diajukan: hariLalu(14) }, kini).kode, 'otomatis');
  assert.equal(sahBimbingan({ status: 'menunggu', diajukan: hariLalu(13.9) }, kini), false);
  assert.equal(sahBimbingan({ status: 'menunggu', diajukan: hariLalu(14) }, kini), true);
  assert.equal(sahBimbingan({ status: 'dikembalikan', diajukan: hariLalu(40) }, kini), false);
});

test('periksa isian: pembimbing, tanggal (bukan masa depan), cara, topik, arahan', () => {
  const pb = [{ id: 'a', nama: 'Adi', ke: 1 }];
  const sah = { tanggal: '2026-11-25', cara: 'daring', pembimbing: 'a', topik: 'Bab 3 metode', arahan: '' };
  assert.deepEqual(periksaBimbingan(sah, pb, kini), []);
  assert.match(periksaBimbingan(sah, [], kini)[0], /belum tercatat/);
  assert.match(periksaBimbingan({ ...sah, pembimbing: 'b' }, pb, kini)[0], /Pilih pembimbing/);
  assert.match(periksaBimbingan({ ...sah, tanggal: '2026-11-26' }, pb, kini)[0], /tidak boleh setelah hari ini/);
  assert.match(periksaBimbingan({ ...sah, tanggal: '2019-12-31' }, pb, kini)[0], /terlalu lama/);
  assert.match(periksaBimbingan({ ...sah, cara: 'telepon' }, pb, kini)[0], /tatap muka atau daring/);
  assert.match(periksaBimbingan({ ...sah, topik: 'abc' }, pb, kini)[0], /5–1000/);
  assert.match(periksaBimbingan({ ...sah, arahan: 'x'.repeat(2001) }, pb, kini)[0], /2000/);
});

test('teks syarat dan hari sejak bimbingan terakhir', () => {
  assert.equal(teksSyarat({ tahap: 'seminar_kemajuan', minimal: 4, terhitung: 3, sejak: '2026-11-01', cukup: false }),
    'Seminar kemajuan: 3 dari 4 bimbingan terkonfirmasi sejak 01-11-2026');
  assert.equal(teksSyarat({ tahap: 'seminar_proposal', minimal: 4, terhitung: 5, sejak: null, cukup: true }),
    'Seminar proposal: 5 dari 4 bimbingan terkonfirmasi (cukup)');
  assert.equal(teksSyarat({ tahap: 'sidang_akhir', minimal: 0 }), 'Sidang akhir: tanpa syarat jumlah bimbingan');
  assert.equal(hariSejak('2026-10-26', kini), 30);
  assert.equal(hariSejak(null, kini), null);
  assert.equal(labelCara('tatap_muka'), 'Tatap muka');
});

test('Tugas saya: konfirmasi catatan bimbingan; tenggat 14 hari sejak catatan tertua', async () => {
  const { tugasSaya } = await import('../../site/tugas-saya.js');
  const bimbinganTa = [{ nim: '1', nama: 'Ani', n: 2, tertua: hariLalu(10) }, { nim: '2', nama: 'Budi', n: 1, tertua: hariLalu(3) }];
  const t = tugasSaya({ saya: { id: 'x', nidn: '001', peran: 'dosen', dtps: false }, bimbinganTa }, kini).filter(x => x.jenis === 'bimbingan_ta');
  assert.deepEqual(t.map(x => [x.judul, x.rinci, x.href, x.hari]), [
    ['Konfirmasi 3 catatan bimbingan TA', 'Ani (2), Budi (1)', 'bimbingan-ta.html#menunggu-konfirmasi', 4]]);
});
