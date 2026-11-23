// site/panel-bukti.js: a stored document is linked, never recorded twice (owner 2026-11-05).
// Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { pilihanBukti, barisTaut } from '../../site/panel-bukti.js';

const DOK = [
  { id: 1, jenis: 'statuta', tahun: 2024, judul: '', url: 'u-statuta' },
  { id: 2, jenis: 'kebijakan_spmi', tahun: 2024, judul: '', url: 'u-spmi' },
  { id: 3, jenis: 'rps', tahun: 2025, judul: 'SI301', url: 'u-rps' },
  { id: 4, jenis: 'notulen', tahun: 2025, judul: 'Rapat', url: 'u-not' },
];
const nilai = xs => xs.map(x => x.nilai);

test('pilihanBukti: documents meant for this item come first', () => {
  const P = pilihanBukti('15', { dokumen: DOK, butirBukti: [] });
  assert.deepEqual(nilai(P.saran), ['d:3']);
  assert.ok(nilai(P.lain).includes('j:statuta') && nilai(P.lain).includes('d:4'));
  assert.equal(pilihanBukti('1', { dokumen: DOK, butirBukti: [] }).saran[0].nilai, 'j:statuta');
});

test('pilihanBukti: what is already linked here is not offered again, however it was linked', () => {
  const k = { dokumen: DOK, butirBukti: [
    { id: 1, butir: 1, jenis_dokumen: 'statuta' }, { id: 2, butir: 1, dokumen_id: 3 },
    { id: 3, butir: 1, dokumen_id: 2 }, { id: 4, butir: 1, url: 'u-not', judul: 'x' }] };
  const P = pilihanBukti('1', k), semua = nilai([...P.saran, ...P.lain]);
  for (const v of ['j:statuta', 'd:3', 'j:kebijakan_spmi', 'd:4']) assert.ok(!semua.includes(v), v);
});

test('pilihanBukti: a file uploaded at another item can be linked; library files are not repeated', () => {
  const k = { dokumen: DOK, butirBukti: [
    { id: 7, butir: 20, url: 'u-laporan', judul: 'Laporan AMI.pdf' }, { id: 8, butir: 21, url: 'u-laporan', judul: 'Laporan AMI.pdf' },
    { id: 9, butir: 22, url: 'u-rps', judul: 'RPS' }, { id: 10, butir: 5, url: 'u-sini', judul: 'Di sini' }] };
  assert.deepEqual(pilihanBukti('5', k).berkas, [{ nilai: 'u:7', label: 'Laporan AMI.pdf (butir 20)' }]);
});

test('barisTaut: link to a stored document becomes that document; already linked -> null', () => {
  const k = { dokumen: DOK, butirBukti: [{ id: 1, butir: 2, url: 'u-x' }, { id: 2, butir: 3, jenis_dokumen: 'statuta' }] };
  assert.deepEqual(barisTaut('2', k, { judul: 't', url: 'u-rps' }), { dokumen_id: 3 });
  assert.equal(barisTaut('2', k, { judul: 't', url: 'u-x' }), null);
  assert.equal(barisTaut('3', k, { judul: 't', url: 'u-statuta' }), null, 'covered by the type link');
  assert.deepEqual(barisTaut('2', k, { judul: 't', url: 'u-baru' }), { judul: 't', url: 'u-baru' });
  assert.equal(barisTaut('3', k, { dokumen_id: 1 }), null);
});
