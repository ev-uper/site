// Portofolio MK (pemilik 2026-11-17, OBE O3; site/portofolio.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { daftarSemester, mkSemester, kelengkapan, persen, komponenUntuk, labelBerkas } from '../../site/portofolio.js';

test('semester dan MK per semester (kurikulum terbaru yang memuat kode)', () => {
  const kelas = [{ id: 1, tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: 'si101', kelas: 'B', dosen_email: 'a@u.id' },
                 { id: 2, tahun_akademik: '2026/2027', semester: 'Ganjil', kode_mk: 'SI101', kelas: 'A', dosen_email: 'b@u.id' },
                 { id: 3, tahun_akademik: '2025/2026', semester: 'Genap', kode_mk: 'SI102', kelas: 'A' }];
  const mk = [{ kurikulum: 'K21', kode: 'SI101', nama: 'Lama' }, { kurikulum: 'K26', kode: 'SI101', nama: 'Statika' },
              { kurikulum: 'K26', kode: 'SI109', nama: 'Hidrologi' }];
  const berkas = [{ tahun_akademik: '2026/2027', semester: 'Ganjil', kurikulum: 'K26', kode_mk: 'SI109', kelas: 'C', komponen: 'bap' }];
  assert.deepEqual(daftarSemester([...kelas, ...berkas], { ta: '2026/2027', sm: 'Genap' }).map(s => `${s.ta} ${s.sm}`),
                   ['2026/2027 Genap', '2026/2027 Ganjil', '2025/2026 Genap']);
  const xs = mkSemester(kelas, berkas, mk, '2026/2027', 'Ganjil');
  assert.deepEqual(xs.map(x => [x.kurikulum, x.kode, x.nama, x.kelas.map(k => k.kelas)]),
                   [['K26', 'SI101', 'Statika', ['A', 'B']], ['K26', 'SI109', 'Hidrologi', ['C']]]);
});

test('kelengkapan: tingkat MK per butir asesmen, tingkat kelas, otomatis', () => {
  const berkas = [{ komponen: 'materi', kelas: null }, { komponen: 'soal', kelas: null, asesmen: 'UTS' },
                  { komponen: 'rubrik', kelas: null, asesmen: 'UTS' }, { komponen: 'soal', kelas: null, asesmen: 'Tugas 1' },
                  { komponen: 'contoh_tinggi', kelas: 'A', asesmen: 'UTS' }, { komponen: 'presensi', kelas: 'A' }, { komponen: 'bap', kelas: 'B' }];
  const k = kelengkapan({ rps: true, cpmkLengkap: false, refleksi: true, asesmen: ['Tugas 1', 'UTS'], berkas,
                          kelas: [{ kelas: 'A', nilai: true }, { kelas: 'B', nilai: false }] });
  assert.deepEqual(k.mk.filter(x => !x.ada).map(x => x.label), ['CPMK, butir asesmen, dan bobot lengkap', 'Kunci atau rubrik: Tugas 1']);
  assert.deepEqual(k.kelas[0].item.filter(x => !x.ada).map(x => x.label), ['Contoh jawaban nilai sedang', 'Contoh jawaban nilai rendah', 'Berita acara perkuliahan (BAP)']);
  assert.deepEqual([k.ada, k.total, persen(k)], [10, 20, 50]);   // MK 6/8, kelas A 3/6, kelas B 1/6
  assert.deepEqual(komponenUntuk('mk'), ['materi', 'soal', 'kunci', 'rubrik', 'lainnya']);
  assert.equal(labelBerkas({ komponen: 'soal', asesmen: 'UTS' }), 'Soal / lembar tugas (UTS)');
});

test('rubrik di RPS memenuhi komponen kunci atau rubrik (pemilik 2026-11-19)', async () => {
  const { kelengkapan } = await import('../../site/portofolio.js');
  const k = kelengkapan({ asesmen: ['Tugas 1', 'Kuis 1'], berkas: [], kelas: [], rubrikRps: new Set(['Tugas 1']) });
  const it = k.mk.filter(x => x.komponen === 'kunci');
  assert.deepEqual(it.map(x => [x.label, x.ada]), [['Kunci atau rubrik: Tugas 1 (rubrik di RPS)', true], ['Kunci atau rubrik: Kuis 1', false]]);
});
