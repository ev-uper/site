// Contoh halaman tautan pribadi (pemilik 2026-11-19; site/pengajuan-contoh.js, pengajuan.html?contoh=).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { CONTOH_PENGAJUAN, contohPengajuan } from '../../site/pengajuan-contoh.js';
import { jalurTahap, labelStatus, judulPengajuan, LABEL_BERKAS } from '../../site/pengajuan-mhs.js';

const kini = new Date('2026-11-19T10:00:00+07:00');
const kini_ = (p, t) => jalurTahap(p, t).find(x => x.keadaan === 'kini')?.label;

test('tiga contoh: bentuk sama dengan mhs_lihat, berkas berlabel', () => {
  assert.deepEqual(CONTOH_PENGAJUAN.map(c => c[0]), ['baru', 'diperiksa', 'selesai']);
  for (const [k] of CONTOH_PENGAJUAN) {
    const p = contohPengajuan(k, kini);
    for (const f of ['jenis', 'nim', 'nama', 'status', 'tahap', 'data', 'data_selesai', 'lain', 'berkas', 'riwayat']) assert.ok(f in p, `${k}.${f}`);
    p.berkas.forEach(b => assert.ok(LABEL_BERKAS[b.jenis], b.jenis));
    assert.equal(judulPengajuan(p), 'PT Contoh Konstruksi');
    assert.ok(labelStatus(p));
    p.riwayat.forEach(r => assert.ok(r.waktu <= kini.toISOString()));
  }
});

test('tahap tiap contoh', () => {
  const b = contohPengajuan('baru', kini), d = contohPengajuan('diperiksa', kini), s = contohPengajuan('selesai', kini);
  assert.equal(b.status, 'draf'); assert.equal(b.berkas.length, 0); assert.equal(b.boleh_ubah, true);
  assert.equal(d.status, 'admin'); assert.equal(d.boleh_ubah, false);
  assert.ok(jalurTahap(d, 'pengajuan').some(x => x.keadaan === 'selesai'));
  assert.ok(kini_(d, 'pengajuan'));
  assert.equal(s.jendela_selesai, true); assert.equal(s.data.jawaban_instansi, 'diterima');
});

test('kunci tak dikenal = contoh baru; data fiktif', () => {
  assert.equal(contohPengajuan('apa', kini).status, 'draf');
  const p = contohPengajuan('selesai', kini);
  assert.match(p.nama, /Contoh/); assert.match(p.pembimbing, /Contoh/); assert.match(p.email, /contoh\.ac\.id$/);
});

test('pengajuan.html: mode contoh dipasang sebelum layanan unggah diperiksa, tautan dari langkah 3', () => {
  const h = readFileSync(new URL('../../site/pengajuan.html', import.meta.url), 'utf8');
  assert.ok(h.indexOf('if (CONTOH) return halamanContoh();') < h.indexOf('if (!window.UPLOAD_URL)'));
  assert.match(h, /pengajuan\.html\?contoh=baru/);
  assert.match(h, /x\.disabled = true/);
});
