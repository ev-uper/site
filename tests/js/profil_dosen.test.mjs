// site/profil-dosen.js: LKPS 4.a profile helpers (owner 2026-11-04). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { pendidikanTertinggi, teksPendidikan, tampil, sama, ISIAN_PROFIL, ISIAN_ADMIN, editorDaftar, htmlMkProdi, formLKPS, pasangEditor }
  from '../../site/profil-dosen.js';

const RW = [
  { jenjang: 'sarjana', program_studi: 'Teknik Contoh', perguruan_tinggi: 'Univ A' },
  { jenjang: 'magister_terapan', program_studi: 'Rekayasa', perguruan_tinggi: 'Univ B', bidang_ilmu: 'Air' },
];

test('highest degree from the education history', () => {
  assert.equal(pendidikanTertinggi(RW), 'S2');
  assert.equal(pendidikanTertinggi([...RW, { jenjang: 'doktor' }]), 'S3');
  assert.equal(pendidikanTertinggi([RW[0]]), null);
  assert.equal(pendidikanTertinggi(undefined), null);
});

test('LKPS cell text per level, applied programmes marked', () => {
  assert.equal(teksPendidikan(RW, 'sarjana'), 'Teknik Contoh, Univ A');
  assert.equal(teksPendidikan(RW, 'magister'), 'Rekayasa, Univ B (Air) [terapan]');
  assert.equal(teksPendidikan(RW, 'doktor'), '');
});

test('display and comparison for the change-request table', () => {
  assert.equal(tampil('kategori', 'industri'), 'Dosen Industri');
  assert.equal(tampil('riwayat_pendidikan', RW), 'Sarjana: Teknik Contoh, Univ A; Magister Terapan: Rekayasa, Univ B (Air)');
  assert.equal(tampil('sertifikat', []), '—');
  assert.equal(tampil('sesuai_kompetensi_inti', true), 'V');
  assert.ok(sama([], null) && sama(null, []) && sama(RW, JSON.parse(JSON.stringify(RW))));
  assert.ok(!sama(RW, RW.slice(0, 1)));
});

test('lecturers cannot request the assessment columns', () => {
  const dosen = new Set(ISIAN_PROFIL.map(([k]) => k));
  assert.ok(ISIAN_ADMIN.every(([k]) => !dosen.has(k)));
});

test('bukti ijazah/sertifikat: tanda di ringkasan dan sel Unggah di editor', () => {
  assert.equal(tampil('sertifikat', [{ jenis: 'profesi', bidang: 'IPM', url: 'https://x/lkd.html?f=1' }]), 'Profesi: IPM · ada bukti');
  assert.equal(tampil('riwayat_pendidikan', [{ jenjang: 'doktor', perguruan_tinggi: 'Univ C', url: 'https://x' }]), 'Doktor: Univ C · ada ijazah');
  const h = editorDaftar('ed_s', 'sertifikat', [{ jenis: 'kompetensi', bidang: 'BIM', url: 'https://a' }]);
  assert.match(h, /data-k="url" value="https:\/\/a"/);
  assert.match(h, /data-unggah/);
  assert.match(editorDaftar('ed_r', 'riwayat', []), /Tautan ijazah/);
});

test('MK diampu di prodi ini: daftar baca-saja, kosong, atau tidak tampil', () => {
  assert.match(htmlMkProdi([{ kode: 'SI2101', nama: 'Hidrologi', sks: 3 }]), /SI2101<\/code> Hidrologi · 3 sks/);
  assert.match(htmlMkProdi([]), /Belum ada/);
  assert.equal(htmlMkProdi(null), '');
  assert.doesNotMatch(formLKPS({}), /diampu di prodi ini/);
  assert.match(formLKPS({}, { mkProdi: [] }), /diampu di prodi ini \(0\)/);
});

test('pasangEditor berulang pada wadah yang sama tidak menggandakan pendengar (unggah ganda)', () => {
  const log = [], kelas = new Set();
  const akar = { classList: { toggle: (k, on) => (on ? kelas.add(k) : kelas.delete(k)) }, querySelectorAll: () => [],
                 addEventListener: t => log.push(t) };
  const u1 = async () => 'a', u2 = async () => 'b';
  pasangEditor(akar, { unggah: u1 }); pasangEditor(akar, { unggah: u1 }); pasangEditor(akar, { unggah: u2 });
  assert.deepEqual(log.sort(), ['change', 'click', 'input']);
  assert.equal(akar._unggahBukti, u2);                      // fungsi terbaru yang dipakai
  assert.ok(kelas.has('ed-bisa-unggah'));
  pasangEditor(akar, {});
  assert.ok(!kelas.has('ed-bisa-unggah') && akar._unggahBukti === null);
});

test('baris yang sudah bertautan menampilkan "Ganti berkas", baris kosong "Unggah"', () => {
  assert.match(editorDaftar('ed_r', 'riwayat', [{ jenjang: 'magister', url: 'https://x/lkd.html?f=1' }]), />Ganti berkas<input type="file" data-unggah hidden>/);
  assert.match(editorDaftar('ed_r', 'riwayat', [{ jenjang: 'magister' }]), />Unggah<input type="file" data-unggah hidden>/);
  assert.doesNotMatch(editorDaftar('ed_r', 'riwayat', [{ jenjang: 'magister' }]), /multiple/);
});
