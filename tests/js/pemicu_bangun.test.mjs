// Build situs otomatis setelah data publik berubah (site/pemicu-bangun.js, pemilik 2026-11-19).
import test from 'node:test';
import assert from 'node:assert/strict';
import { pasangPemicuBangun } from '../../site/pemicu-bangun.js';

function klienTiruan(gagal = false){
  const builder = () => { const q = { eq: () => q, select: () => q, then: (ok, ng) => Promise.resolve({ data: [], error: gagal ? { message: 'x' } : null }).then(ok, ng) };
    return q; };
  return { from: () => ({ insert: builder, update: builder, upsert: builder, delete: builder, select: builder }), rpc: () => builder() };
}

test('pemicu build: tabel publik saja, hanya bila berhasil, simpan beruntun digabung, RPC persetujuan', async () => {
  let kirim = 0, tunda = [];
  const opsi = { kirim: () => { kirim++; }, jadwal: f => { tunda.push(f); return tunda.length; }, batal: id => { tunda[id - 1] = null; } };
  const jalankan = () => { tunda.filter(Boolean).forEach(f => f()); tunda = []; };
  const sb = pasangPemicuBangun(klienTiruan(), opsi);
  await sb.from('mk_rps').update({ a: 1 }).eq('id', 1);
  jalankan(); assert.equal(kirim, 0);                                   // bukan tabel publik
  await sb.from('lkps_bukti').update({ jenis: 'foto' }).eq('id', 1);
  await sb.from('karya').insert({ judul: 'x' }).select();
  jalankan(); assert.equal(kirim, 1);                                   // dua simpan beruntun = satu pemicu
  await sb.rpc('setujui_ajuan_prestasi', { p_id: 1 });
  await sb.rpc('rps_ajukan', {});
  jalankan(); assert.equal(kirim, 2);
  assert.equal(pasangPemicuBangun(sb, opsi), sb);                       // tidak dibungkus dua kali
  const gagal = pasangPemicuBangun(klienTiruan(true), opsi);
  await gagal.from('karya').update({}).eq('id', 1);
  jalankan(); assert.equal(kirim, 2);                                   // penulisan gagal tidak memicu
});
