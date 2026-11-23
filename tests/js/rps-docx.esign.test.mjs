// Pengesahan elektronik RPS di Word (116, pemilik 2026-11-19): QR, "a.n." bila diwakilkan admin, kolom Dekan, keterangan verifikasi.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { dokumenRps, buatRpsDocx } from '../../site/rps-docx.js';
import { modelRps, esignRps, rpsKosong } from '../../site/rps.js';

const AKAR = join(import.meta.dirname, '..', '..');
const mk = { kurikulum: 'K26', kode: '41302', nama: 'Fisika Dasar 1', sks: 3, semester: 1 };
const dosen = { a: { nama: 'Kaprodi', nama_gelar: 'Dr. Kaprodi, S.T.', nip: '1' }, adm: { nama: 'Admin Prodi', nip: '' }, d: { nama: 'Dekan', nama_gelar: 'Prof. Dekan', nip: '2' } };
const r = { sah_pada: '2026-11-19T03:00:00Z', kode_verifikasi: '0f8e2c1a-1111-4222-8333-444455556666', sah_oleh: 'adm', sah_atas_nama: 'a',
  tetap_pada: '2026-11-20T03:00:00Z', tetap_oleh: 'd', tetap_atas_nama: 'd' };
const log = [{ aksi: 'ajukan', waktu: '2026-11-18T03:00:00Z' }, { aksi: 'ajukan', waktu: '2026-11-21T03:00:00Z' }];

test('esignRps: diajukan sebelum pengesahan, diwakilkan admin, penetapan sendiri; null bila belum disahkan', () => {
  const e = esignRps(r, log, id => dosen[id], 'https://x/verifikasi-rps.html?k=0f8e');
  assert.deepEqual(e.diajukan, { waktu: '2026-11-18T03:00:00Z' });
  assert.deepEqual(e.sah, { waktu: r.sah_pada, oleh: 'Admin Prodi', diwakilkan: true, sebutan: '' });
  assert.deepEqual(e.tetap, { waktu: r.tetap_pada, oleh: 'Prof. Dekan', diwakilkan: false, sebutan: '' });
  assert.equal(esignRps({ status: 'draf' }, log, () => null, ''), null);
});

test('Word: sel tanda tangan elektronik, a.n. Ketua Program Studi, nama Dekan, QR dan keterangan verifikasi', { skip: !existsSync(join(AKAR, 'tools', 'node_modules', 'jszip')) && 'butuh: npm install --prefix tools' }, async () => {
  const esign = esignRps(r, log, id => dosen[id], 'https://x/verifikasi-rps.html?k=0f8e');
  const M = modelRps({ mk, rps: rpsKosong(mk), kaprodi: dosen.a, dekan: dosen.d, esign });
  const x = dokumenRps(M, { qr: true });
  for (const t of ['Diajukan elektronik, 18 November 2026', 'Disahkan elektronik, 19 November 2026', 'a.n. Ketua Program Studi; dilaksanakan oleh Admin Prodi',
    'Ditetapkan elektronik, 20 November 2026', 'Prof. Dekan', 'NIP 2', 'https://x/verifikasi-rps.html?k=0f8e', '(kode 0f8e2c1a)']) assert.ok(x.includes(t), t);
  assert.ok(!x.includes('a.n. Dekan'));                                  // Dekan menetapkan sendiri
  assert.equal((x.match(/r:embed="rIdQR"/g) || []).length, 2);           // QR di kolom Kaprodi dan Dekan
  const JSZip = createRequire(join(AKAR, 'tools', 'package.json'))('jszip');
  const buf = await buatRpsDocx(M, { JSZip, qr: new Uint8Array([137, 80, 78, 71]), type: 'nodebuffer' });
  const z = await JSZip.loadAsync(buf);
  assert.ok(z.file('word/media/qr.png'));
  assert.match(await z.file('word/_rels/document.xml.rels').async('string'), /rIdQR.*media\/qr\.png/);
  const tanpa = dokumenRps(modelRps({ mk, rps: rpsKosong(mk) }), {});   // RPS belum disahkan: sel kosong, tanpa QR/keterangan
  assert.ok(!tanpa.includes('elektronik') && !tanpa.includes('rIdQR'));
});

test('Word: tanggal dokumen semester + catatan waktu sistem; sebutan Pjs. Dekan (117)', () => {
  const esign = esignRps(r, log, id => dosen[id], 'https://x/v', { tanggal: '2026-09-02', sebutanDekan: 'Pjs. Dekan Fakultas Perencanaan Infrastruktur' });
  const x = dokumenRps(modelRps({ mk, rps: rpsKosong(mk), kaprodi: dosen.a, dekan: dosen.d, esign }), { qr: true });
  for (const t of ['Disahkan, 2 September 2026', 'Ditetapkan, 2 September 2026', '(pengesahan elektronik dicatat sistem 19 November 2026)',
    '(pengesahan elektronik dicatat sistem 20 November 2026)', 'Pjs. Dekan Fakultas Perencanaan Infrastruktur', 'a.n. Ketua Program Studi']) assert.ok(x.includes(t), t);
  assert.ok(!x.includes('Disahkan elektronik,'));
});
