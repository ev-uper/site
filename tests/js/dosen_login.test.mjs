// site/dosen-login.js: email utama atau alternatif (instal-lengkap.sql). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { dosenLogin } from '../../site/dosen-login.js';

// sb tiruan: mencatat filter yang dipakai.
const sbTiruan = rpc => {
  const log = [];
  const q = { select: k => (log.push(['select', k]), q), eq: (c, v) => (log.push(['eq', c, v]), q),
    ilike: (c, v) => (log.push(['ilike', c, v]), q), maybeSingle: async () => ({ data: { id: 'X' }, error: null }) };
  return { log, rpc: async n => (log.push(['rpc', n]), rpc), from: t => (log.push(['from', t]), q) };
};
const sesi = { user: { email: 'nama@gmail.com' } };

test('patch 69 ada: dosen dicari menurut id dari id_dosen_login', async () => {
  const sb = sbTiruan({ data: 'uuid-1', error: null });
  assert.deepEqual(await dosenLogin(sb, sesi, 'id,nama'), { data: { id: 'X' }, error: null });
  assert.deepEqual(sb.log, [['rpc', 'id_dosen_login'], ['from', 'dosen'], ['select', 'id,nama'], ['eq', 'id', 'uuid-1']]);
});

test('email tidak terdaftar: data null tanpa kueri dosen', async () => {
  const sb = sbTiruan({ data: null, error: null });
  assert.deepEqual(await dosenLogin(sb, sesi), { data: null, error: null });
  assert.equal(sb.log.length, 1);
});

test('patch 69 belum dijalankan: kembali ke pencarian email login', async () => {
  const sb = sbTiruan({ data: null, error: { message: 'function id_dosen_login does not exist' } });
  await dosenLogin(sb, sesi, '*');
  assert.deepEqual(sb.log.slice(1), [['from', 'dosen'], ['select', '*'], ['ilike', 'email', 'nama@gmail.com']]);
});
