// Statistik kunjungan situs publik (instal-lengkap.sql, pemilik 2026-11-21): site/kunjungan-publik.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
// Kecocokan dengan teks patch bernomor: hanya di repo sumber (repo prodi hanya punya instal-lengkap.sql hasil pg_dump,
// formatnya lain). Penanda repo sumber: tools/make_package.py (tidak ikut templat).
const SUMBER = existsSync(new URL('../../tools/make_package.py', import.meta.url));
const HANYA_SUMBER = { skip: !SUMBER && 'hanya di repo sumber (patch bernomor)' };
import { kategoriRujukan, namaHalaman, lewati, rekapKunjungan, catatKunjunganPublik, RUJUKAN, PERISTIWA } from '../../site/kunjungan-publik.js';

test('kategori asal dari referrer dan ?src', () => {
  const h = 'prodi.contoh.ac.id';
  assert.equal(kategoriRujukan('https://www.google.co.id/', h), 'google');
  assert.equal(kategoriRujukan('https://l.instagram.com/?u=x', h), 'instagram');
  assert.equal(kategoriRujukan('https://lm.facebook.com/l.php', h), 'facebook');
  assert.equal(kategoriRujukan('https://universitaspertamina.ac.id/prodi/teknik-sipil', h), 'kampus');
  assert.equal(kategoriRujukan('https://prodi.contoh.ac.id/situs/index.html', h), 'internal');
  assert.equal(kategoriRujukan('', h), 'langsung');
  assert.equal(kategoriRujukan('bukan url', h), 'langsung');
  assert.equal(kategoriRujukan('https://contoh.org/', h), 'lainnya');
  assert.equal(kategoriRujukan('', h, 'ig'), 'instagram');      // tautan dari kartu Instagram
  assert.equal(kategoriRujukan('https://www.google.com/', h, 'wa'), 'whatsapp');
});

test('nama halaman', () => {
  assert.equal(namaHalaman('/cv-site/'), 'index.html');
  assert.equal(namaHalaman('/cv-site/calon-mahasiswa.html'), 'calon-mahasiswa.html');
  assert.equal(namaHalaman('/cv-site/daftar.html', '?jenis=dosen&q=x'), 'daftar.html:dosen');
  assert.equal(namaHalaman('/cv-site/dosen/ani-lestari.html'), 'dosen/ani-lestari.html');
  assert.equal(namaHalaman('/'), 'index.html');
  assert.equal(namaHalaman('/cv-site/daftar.html', '?jenis=<script>'), 'daftar.html');
  // Mode latihan (pemilik 2026-11-24): terpisah dari halaman pengajuan sungguhan, juga dari tautan email tiruan.
  assert.equal(namaHalaman('/cv-site/pengajuan.html', '?latihan=1'), 'pengajuan.html:latihan');
  assert.equal(namaHalaman('/cv-site/pengajuan.html', '?dari=email-coba&latihan=1'), 'pengajuan.html:latihan');
  assert.equal(namaHalaman('/cv-site/pengajuan.html', '?jenis=kp&latihan=1'), 'pengajuan.html:kp:latihan');
});

test('perayap, peramban otomatis, dan situs lokal tidak dicatat', () => {
  assert.ok(lewati({ ua: 'Mozilla/5.0 (compatible; Googlebot/2.1)' }));
  assert.ok(lewati({ webdriver: true }));
  assert.ok(lewati({ host: 'localhost' }) && lewati({ host: 'cv.localhost' }));
  assert.ok(!lewati({ ua: 'Mozilla/5.0 (Linux; Android 14) Chrome/130', host: 'prodi.contoh.ac.id' }));
});

test('kirim: isi permintaan benar, dan tidak pernah melempar galat', () => {
  const kirim = [];
  const w = { SB_URL: 'https://x.supabase.co', SB_KEY: 'k', navigator: { userAgent: 'Mozilla/5.0 Chrome' },
    location: { hostname: 'prodi.contoh.ac.id', pathname: '/cv-site/calon-mahasiswa.html', search: '?src=ig' },
    document: { referrer: '' }, fetch: (u, o) => { kirim.push([u, JSON.parse(o.body)]); return Promise.resolve(); } };
  catatKunjunganPublik('lihat', w);
  catatKunjunganPublik('kuis_selesai', w);
  catatKunjunganPublik('bukan', w);                                  // peristiwa tak dikenal: diam
  assert.equal(kirim.length, 2);
  assert.match(kirim[0][0], /rpc\/catat_kunjungan_publik$/);
  assert.deepEqual(kirim[0][1], { p_halaman: 'calon-mahasiswa.html', p_rujukan: 'instagram', p_peristiwa: 'lihat' });
  assert.equal(kirim[1][1].p_rujukan, 'internal');
  assert.doesNotThrow(() => catatKunjunganPublik('lihat', { SB_URL: 'x', SB_KEY: 'k', fetch: () => { throw new Error('x'); } }));
});

test('rekap untuk halaman admin', () => {
  const r = rekapKunjungan([
    { t: '2026-11-22', h: 'calon-mahasiswa.html', r: 'instagram', p: 'lihat', n: 5 },
    { t: '2026-11-22', h: 'index.html', r: 'internal', p: 'lihat', n: 3 },
    { t: '2026-11-23', h: 'index.html', r: 'google', p: 'lihat', n: 2 },
    { t: '2026-11-23', h: 'calon-mahasiswa.html', r: 'internal', p: 'kuis_selesai', n: 4 },
    { t: '2026-11-23', h: 'index.html', r: 'internal', p: 'daftar_klik', n: 1 }]);
  assert.equal(r.kunjungan, 10); assert.equal(r.dariLuar, 7); assert.equal(r.kuis, 4); assert.equal(r.daftar, 1);
  assert.deepEqual(r.perRujukan, [['instagram', 5], ['google', 2]]);
  assert.deepEqual(r.perHalaman, [['calon-mahasiswa.html', 5], ['index.html', 5]]);
  assert.deepEqual(r.perHari, [['2026-11-22', 8], ['2026-11-23', 2]]);
});

test('daftar asal dan peristiwa sama dengan patch 142', HANYA_SUMBER, () => {
  const sql = readFileSync(new URL('../../supabase/instal-lengkap.sql', import.meta.url), 'utf8');
  for (const k of [...RUJUKAN, ...PERISTIWA]) assert.ok(sql.includes(`'${k}'`), k);
  const daftar = sql.match(/rujukan in \(([^)]*)\)/)[1].match(/'([a-z]+)'/g).map(s => s.slice(1, -1));
  assert.deepEqual(daftar.sort(), [...RUJUKAN].sort());
});
