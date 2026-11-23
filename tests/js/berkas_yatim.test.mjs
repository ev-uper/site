// Berkas tak terpakai (site/berkas-yatim.js): every table that can hold a Drive link must be read,
// or files still in use look unused and an admin may move them to the Trash (found 2026-11-13: dosen).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { TABEL_RUJUKAN } from '../../site/berkas-yatim.js';

const SQL = new URL('../../supabase/', import.meta.url);
const KOLOM_TAUTAN = /\b(url|[a-z_]*_url|tautan|bukti)\b\s+text|\bjsonb\b/;
// Tables whose link columns never hold files in the prodi Drive folder.
const BUKAN_BERKAS = new Set(['tautan_ami', 'survei', 'survei_jawaban', 'rapat', 'rapat_peserta', 'rapat_tindak',
  'evaluasi_mk', 'evaluasi_tindak', 'cpl_ringkasan', 'cpl_kelas', 'jejak', 'templat_email', 'potret_skor',
  'hibah_ajuan', 'hibah_tim', 'target_baku', 'target_dosen', 'spmi_standar', 'spmi_standar_revisi', 'ami_temuan',
  'ref_cpl', 'ref_mk_cpl', 'ref_cpl_korelasi', 'ref_bidang_keahlian', 'ref_topik_keahlian', 'ref_tema_peta_jalan',
  'karya_sitasi', 'led_narasi', 'led_penugasan', 'led_tim', 'ajuan_hapus', 'ref_kategori_publikasi']);

test('every table with a link column is read for references', () => {
  const tabel = new Map();
  for (const f of readdirSync(SQL).filter(f => /^\d\d.*\.sql$/.test(f))) {
    const t = readFileSync(new URL(f, SQL), 'utf8');
    for (const m of t.matchAll(/create table (?:if not exists )?public\.([a-z0-9_]+) \(([\s\S]*?)\n\);/g))
      tabel.set(m[1], (tabel.get(m[1]) || '') + m[2]);
  }
  const lupa = [...tabel].filter(([n, isi]) => /\b(url|[a-z_]*_url|tautan)\b\s+text/.test(isi)
    && !TABEL_RUJUKAN.includes(n) && !BUKAN_BERKAS.has(n)).map(([n]) => n);
  assert.deepEqual(lupa, [], `Tambahkan ke TABEL_RUJUKAN di berkas-yatim.js: ${lupa.join(', ')}`);
  for (const t of ['dosen', 'spmi_capaian', 'kegiatan', 'hibah_panggilan']) assert.ok(TABEL_RUJUKAN.includes(t), t);
});
