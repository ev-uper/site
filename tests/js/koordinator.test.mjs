// Koordinator prodi (instal-lengkap.sql, pemilik 2026-11-17; site/koordinator.js, tugas-saya.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { aktifPada, bolehPengajuan, tabBoleh, labelJabatan } from '../../site/koordinator.js';
import { tugasSaya } from '../../site/tugas-saya.js';

const kini = new Date('2026-11-17T05:00:00Z');

test('penugasan aktif menurut periode', () => {
  const xs = aktifPada([{ jabatan: 'a', mulai: '2026-01-01' }, { jabatan: 'b', mulai: '2026-01-01', selesai: '2026-11-16' },
                        { jabatan: 'c', mulai: '2026-12-01' }, { jabatan: 'd', mulai: '2026-11-17', selesai: '2026-11-17' }], kini);
  assert.deepEqual(xs.map(x => x.jabatan), ['a', 'd']);
});

test('wewenang pengajuan per bidang; surat tetap admin', () => {
  const ta = { peran: 'dosen', koordinator: ['koordinator_ta'] }, pmb = { peran: 'dosen', koordinator: ['pembina_kemahasiswaan'] };
  assert.ok(bolehPengajuan(ta, 'ta') && !bolehPengajuan(ta, 'kp') && !bolehPengajuan(ta, 'surat'));
  assert.ok(bolehPengajuan(pmb, 'lomba') && bolehPengajuan(pmb, 'luaran') && !bolehPengajuan(pmb, 'ta'));
  assert.ok(bolehPengajuan({ peran: 'admin' }, 'surat'));
  assert.ok(!bolehPengajuan({ peran: 'dosen' }, 'kp'));
});

test('tab Data prodi per jabatan', () => {
  assert.equal(tabBoleh({ peran: 'admin' }), null);
  assert.deepEqual([...tabBoleh({ peran: 'dosen', koordinator: ['koordinator_ta'] })], ['jadwal_ta']);
  assert.deepEqual([...tabBoleh({ peran: 'dosen', koordinator: ['pembina_kemahasiswaan'] })].sort(), ['luaran', 'prestasi', 'publikasi']);
  // GKM (98): tab mutu Data prodi.
  assert.deepEqual([...tabBoleh({ peran: 'dosen', koordinator: ['gkm'] })].sort(), ['dokumen', 'kepuasan', 'revisi', 'spmi', 'standar', 'target', 'temuan']);
  assert.equal(tabBoleh({ peran: 'dosen' }).size, 0);
  assert.equal(labelJabatan('gkm'), 'Gugus kendali mutu (GKM)');
});

test('Tugas saya: tahap admin pengajuan untuk koordinator bidangnya', () => {
  const ps = [{ nama: 'A', jenis: 'kp', status: 'admin', diperbarui: '2026-11-16T00:00:00Z' },
              { nama: 'B', jenis: 'ta', status: 'admin', diperbarui: '2026-11-16T00:00:00Z' }];
  const t = tugasSaya({ saya: { id: 'x', peran: 'dosen', dtps: false, koordinator: ['koordinator_kp'] }, pengajuanMhs: ps }, kini)
    .find(x => x.jenis === 'pengajuan_mhs');
  assert.equal(t.rinci, 'A (KP)');
});
