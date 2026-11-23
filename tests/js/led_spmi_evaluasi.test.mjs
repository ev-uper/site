// Draf LED butir 16 (evaluasi pembelajaran) dan 55 (siklus SPMI) dari data situs (pemilik 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { faktaNarasi, tabelPenjelas, rekapEvalTS, siklusSPMITS } from '../../site/led-isi.js';

const X = {
  rekapEval: [
    { tahun_akademik: '2025/2026', semester: 'Genap', jumlah: 10, ber_edom: 10, rerata_edom: 3.2, di_bawah_ambang: 2, bawah_bertindak: 2, rps_terisi: 9, tindak: 3, tindak_selesai: 1 },
    { tahun_akademik: '2025/2026', semester: 'Ganjil', jumlah: 12, ber_edom: 10, rerata_edom: 3.4, di_bawah_ambang: 1, bawah_bertindak: 0, rps_terisi: 12, tindak: 1, tindak_selesai: 1 },
    { tahun_akademik: '2021/2022', semester: 'Genap', jumlah: 5, ber_edom: 5, rerata_edom: 2.0, di_bawah_ambang: 5, bawah_bertindak: 0, rps_terisi: 0, tindak: 0, tindak_selesai: 0 }],
  standar: [{ id: 1, kode: 'A.01.01', lembar: 'Pendidikan', dipantau: true }, { id: 2, kode: 'O.02.10', lembar: 'Akreditasi Unggul LAMTEK', dipantau: true },
            { id: 3, kode: 'J.01.01', lembar: 'Perpustakaan', dipantau: false }],
  capaianStandar: [{ standar_id: 1, tahun_ts: 2026, status: 'tercapai' }, { standar_id: 2, tahun_ts: 2026, status: 'belum', rencana: 'x' },
                   { standar_id: 3, tahun_ts: 2026, status: 'belum' }, { standar_id: 1, tahun_ts: 2025, status: 'belum' }],
  revisiStandar: [{ standar_id: 2, tanggal: '2026-03-10', perubahan: 'Target 25 → 28 SKS', dasar: 'rtm' }, { standar_id: 1, tanggal: '2022-01-01', perubahan: 'lama', dasar: 'ami' }],
  temuan: [{ tahun_ts: 2026, status: 'ditutup' }, { tahun_ts: 2025, status: 'proses' }, { tahun_ts: 2020, status: 'terbuka' }],
};
const C = (daftar, ts = 2026) => ({ daftar, ts, dokumen: [] });

test('rekap evaluasi TS-2 s.d. TS, urut lama ke baru; ringkasan SPMI hanya butir dipantau', () => {
  assert.deepEqual(rekapEvalTS(X, 2026).map(r => `${r.tahun_akademik} ${r.semester}`), ['2025/2026 Ganjil', '2025/2026 Genap']);
  const s = siklusSPMITS(X, 2026);
  assert.deepEqual([s.dipantau, s.dinilai, s.tercapai, s.belum, s.revisi, s.temuan, s.ditutup], [2, 2, 1, 1, 1, 2, 1]);
  assert.equal(s.kode(2), 'O.02.10');
});

test('kalimat butir 16 dan 55 memakai data; rerata EDOM ditimbang jumlah EDOM terisi', () => {
  const P = faktaNarasi(C(X));
  assert.equal(P.pantauPembelajaran, 'setiap semester melalui evaluasi dosen oleh mahasiswa (EDOM), refleksi dosen pengampu atas kesesuaian '
    + 'pelaksanaan dengan RPS, dan capaian CPL kelas; pada 2023/2024 s.d. 2025/2026 tercatat 22 evaluasi mata kuliah dengan rerata EDOM 3,3, '
    + '3 di bawah ambang dan 2 di antaranya sudah ditindaklanjuti');
  assert.equal(P.siklusSPMI, ' pada 2 butir standar SPMI yang dipantau prodi; capaian 2 butir telah dinilai pada 2025/2026 (1 tercapai, '
    + '1 belum tercapai dan diberi rencana perbaikan); 1 perubahan standar tercatat pada 2023/2024 s.d. 2025/2026');
  assert.equal(P.efektivitasAMI, '2 temuan AMI pada 2023/2024 s.d. 2025/2026, 1 di antaranya telah ditutup setelah diverifikasi efektif');
});

test('tanpa data: teks kerangka lama persis (kunci saran tetap cocok)', () => {
  const P = faktaNarasi(C({}));
  assert.equal(P.pantauPembelajaran, '[isi: frekuensi] melalui [isi: instrumen, misalnya monitoring kesesuaian materi dengan RPS dan EDOM]');
  assert.equal(P.siklusSPMI, '');
  assert.equal(P.efektivitasAMI, '[isi: temuan AMI dan tindak lanjutnya]');
});

test('tabel butir 16 dan tabel tambahan butir 55', () => {
  const t16 = tabelPenjelas('16', C(X));
  assert.equal(t16.length, 1);
  assert.deepEqual(t16[0].baris[1], ['1', '2025/2026 Ganjil', '12', '3,4', '1', '0 dari 1', '12 dari 12', '1 dari 1']);
  const t55 = tabelPenjelas('55', C({ ...X, ppepp: [] }));
  assert.deepEqual(t55.map(t => t.judul), ['Capaian standar SPMI TS 2025/2026', 'Perubahan standar SPMI']);
  assert.deepEqual(t55[0].baris.slice(1), [['1', 'Pendidikan', '1', '1', '0', '0', '0'], ['2', 'Akreditasi Unggul LAMTEK', '1', '0', '1', '0', '0']]);
  assert.deepEqual(t55[1].baris[1], ['1', '10/03/2026', 'O.02.10', 'Target 25 → 28 SKS', 'Keputusan RTM']);
  assert.deepEqual(tabelPenjelas('16', C({})), []);
});
