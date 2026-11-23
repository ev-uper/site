// Keluar otomatis admin (pemilik 2026-11-20): site/menu.js perluKeluarOtomatis dan pemasangannya.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
globalThis.document ??= { querySelector: () => null, querySelectorAll: () => [], title: '' };
const { perluKeluarOtomatis, KELUAR_OTOMATIS_JAM } = await import('../../site/menu.js');

test('keluar otomatis: lewat batas jam tanpa aktivitas', () => {
  const kini = Date.parse('2026-11-20T10:00:00Z'), jam = 3600e3;
  assert.equal(KELUAR_OTOMATIS_JAM, 2);
  assert.equal(perluKeluarOtomatis(kini - 1.5 * jam, kini), false);
  assert.equal(perluKeluarOtomatis(kini - 2 * jam - 1000, kini), true);
  assert.equal(perluKeluarOtomatis(0, kini), false);                 // belum ada catatan: tidak dikeluarkan
  assert.equal(perluKeluarOtomatis(kini - 3 * jam, kini, 4), false);  // batas lain
});

test('hanya admin; waktu login ikut dihitung; keluar lokal lalu ke layar masuk dengan keterangan', () => {
  const m = readFileSync(new URL('../../site/menu.js', import.meta.url), 'utf8');
  assert.match(m, /if \(u\.saya\.peran === 'admin'\) pasangKeluarOtomatis\(sb\);/);
  assert.match(m, /last_sign_in_at/);
  assert.match(m, /Math\.max\(x, masuk\)/);
  assert.match(m, /signOut\(\{ scope: 'local' \}\)[\s\S]*?ruang-kerja\.html\?habis=1/);
  assert.match(m, /title="Mengakhiri sesi akun ini di semua perangkat dan tab">Keluar</);
  const rk = readFileSync(new URL('../../site/ruang-kerja.html', import.meta.url), 'utf8');
  assert.match(rk, /q\.get\('habis'\)[\s\S]*?dikeluarkan otomatis/);
});
