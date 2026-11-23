// Templat khusus akreditasi (pemilik 2026-11-23): ruang kerja akreditasi + kurikulum/CPL/RPS, tanpa situs publik,
// layanan mahasiswa, jadwal, rapat, hibah, kalender, pengingat, kepakaran, SDGs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';

globalThis.document ??= { querySelector: () => null, querySelectorAll: () => [], title: '' };
const { PAKET, MODUL_OPSIONAL, halamanAktif, fiturAktif } = await import('../../site/fitur.js');
const { halamanBoleh } = await import('../../site/menu.js');
globalThis.FITUR_MATI = [...PAKET.akreditasi];

test('accreditation package switches every optional module off, public site included', () => {
  assert.deepEqual([...PAKET.akreditasi].sort(), Object.keys(MODUL_OPSIONAL).sort());
  assert.equal(fiturAktif('publik'), false);
});

test('core accreditation and curriculum pages stay; public and operational pages go', () => {
  for (const h of ['skor.html', 'narasi-led.html', 'input-butir.html', 'data-prodi.html', 'kelola-dosen.html', 'verifikasi.html',
    'karya.html', 'profil.html', 'rps.html', 'cpmk.html', 'portofolio.html', 'kelas.html', 'monitoring.html', 'ruang-kerja.html',
    // tanpa login tetapi wajib hidup: kuesioner akreditasi, bukti privat untuk asesor, QR RPS
    'survei.html', 'lkd.html', 'verifikasi-rps.html', 'hasil-survei.html'])
    assert.ok(halamanAktif(h), h);
  for (const h of ['index.html', 'daftar.html', 'dosen.html', 'kurikulum.html', 'kinerja.html', 'pengajuan-mahasiswa.html',
    'rekap-ta.html', 'jadwal-kuliah.html', 'rapat.html', 'kabar-kegiatan.html', 'kelola-profil.html', 'kunjungan-situs.html'])
    assert.ok(!halamanAktif(h), h);
});

test('workspace menu of an admin lists no switched-off page', () => {
  const admin = { peran: 'admin', dtps: true, aktif: true, koordinator: ['kaprodi', 'gkm', 'dekan'] };
  const ada = halamanBoleh(admin).flatMap(m => m.halaman.map(h => h.href));
  assert.ok(ada.length > 20);
  for (const h of ada) assert.ok(halamanAktif(h), h);
  assert.ok(ada.includes('skor.html') && ada.includes('rps.html') && !ada.includes('jadwal-kuliah.html'));
});

test('kept pages that live in site/ exist', () => {
  for (const h of ['survei.html', 'lkd.html', 'verifikasi-rps.html', 'hasil-survei.html', 'privasi.html', 'ruang-kerja.html'])
    assert.ok(existsSync(new URL(`../../site/${h}`, import.meta.url)), h);
});

test('tasks of switched-off modules are not listed (Tugas saya)', async () => {
  const { tugasSaya } = await import('../../site/tugas-saya.js');
  const saya = { id: 'a', peran: 'admin', dtps: true, aktif: true, koordinator: [] };
  const xs = tugasSaya({ saya, karya: [], pengajuanMhs: [{ id: 1, status: 'admin', jenis: 'lomba', nama: 'Mhs', diperbarui: '2026-11-01' }] });
  assert.ok(!xs.some(x => String(x.href || '').startsWith('pengajuan-mahasiswa.html')));
});
