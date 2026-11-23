// Dasbor operasional koordinator prodi (pemilik 2026-11-17; site/dasbor.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { ringkasDasbor, penanggungJawab } from '../../site/dasbor.js';

const kini = new Date('2026-11-17T05:00:00Z');

test('penanggung jawab: kosong, tanpa SK, segera berakhir', () => {
  assert.deepEqual(penanggungJawab([], 'gkm', kini), { nama: [], peringatan: ['Gugus kendali mutu (GKM) belum ditetapkan'] });
  const k = [{ jabatan: 'koordinator_ta', mulai: '2026-01-01', selesai: '2026-12-01', dosen: { nama: 'Budi' } }];
  const p = penanggungJawab(k, 'koordinator_ta', kini);
  assert.deepEqual(p.nama, ['Budi']);
  assert.deepEqual(p.peringatan, ['SK Budi belum dicatat', 'penugasan Budi berakhir 2026-12-01']);
});

test('antrean dan keterlambatan per bidang', () => {
  const d = {
    koordinator: [{ jabatan: 'koordinator_kp', mulai: '2026-01-01', nomor_sk: 'SK/1', dosen: { nama: 'Adi' } }],
    pengajuan: [{ jenis: 'kp', status: 'admin', diperbarui: '2026-11-01T00:00:00Z' }, { jenis: 'kp', status: 'admin', diperbarui: '2026-11-16T00:00:00Z' },
                { jenis: 'ta', status: 'admin', diperbarui: '2026-11-16T00:00:00Z' }, { jenis: 'surat', status: 'admin', diperbarui: '2026-11-17T00:00:00Z' }],
    jadwal: [{ status: 'terjadwal', tanggal: '2026-11-20' }, { status: 'selesai', hasil: 'lulus_revisi', batas_revisi: '2026-11-10', tanggal: '2026-10-01' }],
    temuan: [{ status: 'terbuka', tenggat: '2026-11-01' }, { status: 'ditutup', tenggat: '2026-01-01' }],
    tindak: [{ status: 'terbuka', tenggat: '2026-12-01' }], karya: [{ status: 'diajukan' }], kabar: [],
  };
  const r = ringkasDasbor(d, kini), cari = (b, l) => r.find(x => x.bidang === b).item.find(i => i.label === l);
  assert.deepEqual(cari('Kerja Praktik/Magang', 'Pengajuan menunggu koordinator').n, 2);
  assert.equal(cari('Kerja Praktik/Magang', 'Pengajuan menunggu koordinator').lewat, 1);          // > 7 hari
  assert.equal(cari('Tugas Akhir', 'Seminar/sidang 14 hari ke depan').n, 1);
  assert.equal(cari('Tugas Akhir', 'Revisi belum selesai').lewat, 1);
  assert.equal(cari('Mutu dan akreditasi', 'Temuan AMI belum selesai').lewat, 1);
  assert.equal(cari('Administrasi prodi', 'Permohonan surat mahasiswa').n, 1);
  assert.deepEqual(r.find(x => x.bidang === 'Kerja Praktik/Magang').pj, { nama: ['Adi'], peringatan: [] });
  assert.deepEqual(r.find(x => x.bidang === 'Mutu dan akreditasi').pj.peringatan, ['Gugus kendali mutu (GKM) belum ditetapkan']);
});

test('O1: evaluasi pembelajaran di bidang Mutu dan akreditasi', () => {
  const r = ringkasDasbor({ perluTL: [{}, {}], tanpaBaris: [{}], tindakEval: [{ status: 'terbuka', tenggat: '2026-11-01' }, { status: 'selesai' }] }, kini);
  const m = r.find(x => x.bidang === 'Mutu dan akreditasi').item, cari = l => m.find(i => i.label.startsWith(l));
  assert.deepEqual([cari('Evaluasi pembelajaran perlu').n, cari('Evaluasi pembelajaran perlu').lewat], [2, 2]);
  assert.equal(cari('MK dengan CPL').n, 1);
  assert.deepEqual([cari('Tindak lanjut evaluasi').n, cari('Tindak lanjut evaluasi').lewat], [1, 1]);
});

test('beban bimbingan (109): TA dibanding dosen se-KK, KP/uji/lomba dibanding semua, tanda kuota', async () => {
  const { ringkasBeban } = await import('../../site/dasbor.js');
  const kk = [{ kode: 'STR', nama: 'Struktur' }, { kode: 'AIR', nama: 'Air' }];
  const r = (nama, kk, o = {}) => ({ dosen_id: nama, nama, kk, kp: 0, kp_selesai: 0, kp_kuota: null, ta: 0, ta_lulus: 0, uji: 0, lomba: 0, ...o });
  const B = ringkasBeban([r('Ani', 'AIR', { ta: 8 }), r('Budi', 'AIR', { ta: 6 }), r('Cici', 'STR', { ta: 1, kp: 9, kp_kuota: 5 }),
    r('Dedi', 'STR', { ta: 1, kp: 5, kp_kuota: 5 }), r('Eko', 'STR', { ta: 6 }), r('Fani', 'XXX', { ta: 0 })], kk);
  assert.deepEqual(B.baris.map(x => [x.nama, x.kk]), [['Cici', 'STR'], ['Dedi', 'STR'], ['Eko', 'STR'], ['Ani', 'AIR'], ['Budi', 'AIR'], ['Fani', '']]);
  const t = Object.fromEntries(B.baris.map(x => [x.nama, x]));
  // TA 8 di AIR (rata 7) tidak tinggi; TA 6 di STR (rata 2,7) tinggi.
  assert.equal(t.Ani.tinggi.ta, false); assert.equal(t.Eko.tinggi.ta, true);
  assert.equal(t.Cici.tinggi.kp, true); assert.equal(t.Cici.kuota, 'lebih'); assert.equal(t.Dedi.kuota, 'penuh'); assert.equal(t.Eko.kuota, '');
  assert.deepEqual(B.kelompok.map(g => [g.kode, g.n, g.rata_ta]), [['STR', 3, 2.7], ['AIR', 2, 7], ['', 1, 3.7]]);
  assert.equal(B.rata.kp, 2.3);
});

test('kesehatan sistem (125): label, kelas, dan waktu relatif', async () => {
  const { ringkasKesehatan, lalu } = await import('../../site/dasbor.js');
  const kini = new Date('2026-11-23T03:00:00Z');
  assert.equal(lalu('2026-11-23T02:30:00Z', kini), '30 menit lalu');
  assert.equal(lalu('2026-11-22T03:00:00Z', kini), '24 jam lalu');
  assert.equal(lalu('2026-11-19T03:00:00Z', kini), '4 hari lalu');
  assert.equal(lalu(null, kini), '—');
  const k = ringkasKesehatan({ perlu_dicek: 1, basis_data_mb: 12.3, butir: [
    { kunci: 'cadangan', label: 'Cadangan', waktu: '2026-11-23T02:00:00Z', status: 'baik' },
    { kunci: 'hitung_cpl', label: 'Hitung CPL', waktu: null, status: 'belum_ada' },
    { kunci: 'situs_terbit', label: 'Terbit', waktu: null, status: 'info' }] }, kini);
  assert.deepEqual(k.butir.map(b => [b.teks, b.kelas, b.kapan]), [['Baik', 'ok', '1 jam lalu'], ['Belum pernah melapor', 'awas', '—'], ['Info', 'info', '—']]);
  assert.equal(k.perlu, 1); assert.equal(k.mb, 12.3);
  assert.deepEqual(ringkasKesehatan(null).butir, []);
});
