// Tautan lain di profil dosen (instal-lengkap.sql, pemilik 2026-11-22).
import test from 'node:test';
import assert from 'node:assert/strict';
import { bacaTautanLain, teksTautanLain, tampil } from '../../site/profil-dosen.js';

test('extra links: "Label | https://..." per line; invalid lines reported; empty = null', () => {
  const r = bacaTautanLain('HESLab (Hydro-Environmental System Lab) | https://heslab.contoh.id\n\n  Scholar|https://s.id/u  \nhttp://x.id\nTanpa | ftp://x');
  assert.deepEqual(r.tautan, [{ label: 'HESLab (Hydro-Environmental System Lab)', url: 'https://heslab.contoh.id' },
    { label: 'Scholar', url: 'https://s.id/u' }]);
  assert.deepEqual(r.salah, ['http://x.id', 'Tanpa | ftp://x']);
  assert.deepEqual(bacaTautanLain('  \n '), { tautan: null, salah: [] });
  assert.equal(teksTautanLain(r.tautan), 'HESLab (Hydro-Environmental System Lab) | https://heslab.contoh.id\nScholar | https://s.id/u');
  assert.equal(tampil('tautan_lain', r.tautan), 'HESLab (Hydro-Environmental System Lab) (https://heslab.contoh.id); Scholar (https://s.id/u)');
  assert.equal(tampil('tautan_lain', null), '—');
});
