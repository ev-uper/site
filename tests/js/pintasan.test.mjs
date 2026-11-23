// Ruang kerja tahap 3 (pemilik 2026-11-20): kelompok menu baru dan pintasan per peran/jabatan (site/menu.js).
import test from 'node:test';
import assert from 'node:assert/strict';
globalThis.document ??= { querySelector: () => null, querySelectorAll: () => [], title: '' };
const { MODUL, PINTASAN, pintasanUntuk, halamanBoleh } = await import('../../site/menu.js');

const dosen = { peran: 'dosen', aktif: true, koordinator: [] };
const daftar = s => pintasanUntuk(s).map(g => [g.label, g.halaman.map(h => h.href)]);

test('kelompok menu tahap 3: Pembelajaran dipecah, Pengelolaan terpisah', () => {
  const judul = MODUL.map(m => m.judul);
  for (const j of ['Data saya', 'Mata kuliah saya', 'Kurikulum dan CPL prodi', 'Kemahasiswaan', 'Kegiatan', 'Pengelolaan'])
    assert.ok(judul.includes(j), j);
  for (const j of ['Pembelajaran dan CPL', 'Admin prodi', 'Kegiatan dan laboratorium']) assert.ok(!judul.includes(j), j);
  const di = href => MODUL.filter(m => m.halaman.some(h => h.href === href)).map(m => m.judul);
  assert.deepEqual(di('rps.html'), ['Mata kuliah saya']);
  assert.deepEqual(di('rps-kurikulum.html'), ['Kurikulum dan CPL prodi']);
  assert.deepEqual(di('target.html'), ['Data saya']);
  assert.deepEqual(di('kelola-laboratorium.html'), ['Pengelolaan']);
  // Satu halaman satu kelompok (menu dan pencarian tidak dobel).
  const semua = MODUL.flatMap(m => m.halaman.map(h => h.href));
  assert.equal(new Set(semua).size, semua.length);
});

test('semua pintasan menunjuk halaman di MODUL', () => {
  const ada = new Set(MODUL.flatMap(m => m.halaman.map(h => h.href)));
  for (const p of PINTASAN) for (const h of p.href) assert.ok(ada.has(h), `${p.label}: ${h}`);
});

test('pintasan dosen biasa, koordinator KP, GKM, admin, asesor; tanpa pengulangan', () => {
  assert.deepEqual(daftar(dosen), [['Dosen', ['profil.html', 'karya.html', 'rps.html', 'nilai-cpl.html', 'pengajuan-mahasiswa.html', 'kalender.html', 'jadwal-berhalangan.html']]]);
  const kp = daftar({ ...dosen, koordinator: ['koordinator_kp'] });
  assert.deepEqual(kp[0], ['Koordinator KP/Magang', ['pengajuan-mahasiswa.html', 'rekap-kp.html', 'kelola-layanan-mahasiswa.html']]);
  assert.ok(!kp[1][1].includes('pengajuan-mahasiswa.html'));   // sudah di kelompok jabatan
  const gkm = daftar({ ...dosen, koordinator: ['gkm'] });
  assert.equal(gkm[0][0], 'Gugus kendali mutu (GKM)'); assert.ok(gkm[0][1].includes('mutu-data.html'));
  const adm = daftar({ peran: 'admin', aktif: true, koordinator: [] });
  assert.equal(adm[0][0], 'Admin prodi'); assert.ok(adm[0][1].includes('verifikasi.html'));
  const as = daftar({ peran: 'asesor', koordinator: [] });
  assert.deepEqual(as.map(g => g[0]), ['Asesor']);
  assert.ok(!as[0][1].includes('pengajuan-mahasiswa.html'));
  for (const s of [dosen, { peran: 'admin', koordinator: ['gkm', 'kaprodi', 'koordinator_kp'] }]) {
    const hs = pintasanUntuk(s).flatMap(g => g.halaman.map(h => h.href));
    assert.equal(new Set(hs).size, hs.length);
    const boleh = new Set(halamanBoleh(s).flatMap(m => m.halaman.map(h => h.href)));
    hs.forEach(h => assert.ok(boleh.has(h), h));
  }
});
