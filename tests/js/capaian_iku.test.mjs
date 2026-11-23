// Ringkasan capaian IKU/IKT bersama Data prodi dan Monitoring (owner 2026-11-11).
import test from 'node:test';
import assert from 'node:assert/strict';
import { nilaiCapaian, denganOtomatis, tsTersedia, tsAwal, capaianTS, htmlCapaianIKU } from '../../site/capaian-iku.js';

test('status follows direction and the 80 % band', () => {
  assert.equal(nilaiCapaian({ target: 10, capaian: 10 }).status, 'tercapai');
  assert.equal(nilaiCapaian({ target: 10, capaian: 8 }).status, 'hampir');
  assert.equal(nilaiCapaian({ target: 10, capaian: 5 }).status, 'belum');
  assert.equal(nilaiCapaian({ target: 4, capaian: 5, arah: 'maksimal' }).status, 'hampir');
  assert.equal(nilaiCapaian({ target: 4, capaian: 3, arah: 'maksimal' }).status, 'tercapai');
  assert.equal(nilaiCapaian({ target: 10, capaian: null }).status, 'kosong');
});

test('sourced rows take the computed value only when data is loaded', () => {
  const r = { jenis: 'iku', nama: 'Publikasi', tahun_ts: 2026, target: 1, capaian: 0, sumber: 'publikasi_per_dtps' };
  const D = { dtps: { jumlah: 2 }, publikasi: [{ tahun_ts: 2026 }, { tahun_ts: 2026 }] };
  assert.equal(denganOtomatis(r, null), r);
  const h = denganOtomatis(r, D);
  assert.equal(h.capaian, 1);
  assert.ok(h._oto);
});

test('TS list, summary, and table rows', () => {
  const baris = [
    { jenis: 'iku', nama: 'A', tahun_ts: 2026, target: 10, capaian: 12, urutan: 2 },
    { jenis: 'iku', nama: 'B', tahun_ts: 2026, target: 10, capaian: null, urutan: 1 },
    { jenis: 'ikt', nama: 'C <x>', tahun_ts: 2026, target: 5, capaian: 1 },
    { jenis: 'iku', nama: 'a', tahun_ts: 2025, target: 10, capaian: 7 },
  ];
  assert.deepEqual(tsTersedia(baris), [2026, 2025]);
  const c = capaianTS(baris, null, 2026);
  assert.deepEqual(c.iku, { jumlah: 2, tercapai: 1, terisi: 1 });
  assert.deepEqual(c.kini.map(r => r.nama), ['B', 'A', 'C <x>']);
  const html = htmlCapaianIKU(baris, null, 2026, { kelasTabel: 'sp' });
  assert.match(html, /IKU: 1 dari 2 tercapai/);
  assert.match(html, /class="sp"/);
  assert.match(html, /C &lt;x&gt;/);
  assert.match(html, />7</);   // TS sebelumnya for indicator A (name match ignores case)
});

test('tsAwal: TS berjalan dulu, lalu TS lewat terbaru, lalu TS mendatang terdekat', () => {
  const nov2026 = new Date(2026, 10, 13), agu2026 = new Date(2026, 7, 31);
  const ada = [2031, 2030, 2029, 2028, 2027, 2026];
  assert.equal(tsAwal(ada, nov2026), 2027);          // 13 Nov 2026 = TS 2026/2027
  assert.equal(tsAwal(ada, agu2026), 2026);          // sebelum September masih TS 2025/2026
  assert.equal(tsAwal([2031, 2029, 2025], nov2026), 2025);
  assert.equal(tsAwal([2031, 2029], nov2026), 2029);
  assert.equal(tsAwal([], nov2026), null);
});
