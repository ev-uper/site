// apps-script/Code.gs kind 'rps_review_kabari' (120, pemilik 2026-11-19): email undangan reviewer dari rps_review_undangan.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

function muat({ undangan, kuota = 100, situs = 'https://contoh.github.io/cv-site/' } = {}){
  const terkirim = [], panggil = [];
  const ctx = {
    PropertiesService: { getScriptProperties: () => ({ getProperty: k => ({ MHS_SITUS: situs }[k] ?? null) }) },
    MailApp: { getRemainingDailyQuota: () => kuota, sendEmail: m => terkirim.push(m) },
    UrlFetchApp: { fetch: (url, o) => { panggil.push({ url, o });
      const isi = typeof undangan === 'function' ? undangan() : undangan;
      return { getResponseCode: () => (isi.message ? 400 : 200), getContentText: () => JSON.stringify(isi) }; } },
  };
  vm.createContext(ctx);
  vm.runInContext(readFileSync(new URL('../../apps-script/Code.gs', import.meta.url), 'utf8'), ctx);
  return { kabari: ctx.rpsReviewKabari_, terkirim, panggil };
}
const cfg = { url: 'https://x.supabase.co', key: 'kunci-publik' };
const U = { email: 'dewi@u.id', nama: 'Dr. Dewi', kurikulum: 'K26', kode_mk: '41301', nama_mk: 'Statika', tenggat: '2026-12-03', penunjuk: 'Dr. Kaprodi' };

test('email undangan: isi dari basis data, tautan ke RPS, balasan ke pengirim, token pengirim dipakai', () => {
  const { kabari, terkirim, panggil } = muat({ undangan: U });
  const r = kabari(cfg, { email: 'admin@u.id' }, { token: 'TOKEN-ADMIN', kurikulum: 'K26', kode: '41301', reviewer: 'r1', pengirim: 'Program Studi Teknik Contoh',
    ke: 'penyusup@luar.com' });   // alamat dari peramban diabaikan
  assert.deepEqual(JSON.parse(JSON.stringify(r)), { ok: true, ke: 'dewi@u.id', tenggat: '2026-12-03' });
  assert.equal(panggil[0].url, 'https://x.supabase.co/rest/v1/rpc/rps_review_undangan');
  assert.equal(panggil[0].o.headers.Authorization, 'Bearer TOKEN-ADMIN');
  assert.deepEqual(JSON.parse(panggil[0].o.payload), { p_kurikulum: 'K26', p_kode: '41301', p_reviewer: 'r1' });
  const m = terkirim[0];
  assert.equal(m.to, 'dewi@u.id');
  assert.equal(m.replyTo, 'admin@u.id');
  assert.equal(m.subject, 'Permohonan review RPS 41301 Statika');
  assert.match(m.body, /ditunjuk oleh Dr\. Kaprodi sebagai reviewer/);
  assert.match(m.body, /paling lambat 3 Desember 2026/);
  assert.match(m.body, /https:\/\/contoh\.github\.io\/cv-site\/rps\.html\?kur=K26&kode=41301/);
});

test('galat basis data diteruskan dan tidak ada email; kuota habis ditolak', () => {
  const a = muat({ undangan: { message: 'Email undangan reviewer dikirim Kaprodi aktif atau admin.' } });
  assert.throws(() => a.kabari(cfg, { email: 'x@u.id' }, { token: 't' }), /Kaprodi aktif atau admin/);
  assert.equal(a.terkirim.length, 0);
  const b = muat({ undangan: U, kuota: 0 });
  assert.throws(() => b.kabari(cfg, { email: 'x@u.id' }, { token: 't' }), /Kuota email hari ini habis/);
  assert.equal(b.terkirim.length, 0);
  const c = muat({ undangan: U, situs: '' });
  c.kabari(cfg, { email: 'x@u.id' }, { token: 't' });
  assert.doesNotMatch(c.terkirim[0].body, /rps\.html/);   // tanpa MHS_SITUS: tanpa tautan
});
