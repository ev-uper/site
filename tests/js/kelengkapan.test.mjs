// site/kelengkapan.js: LED checklist (owner 2026-11-05). Run: node --test tests/js/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { TAB_DATA, hitungKelompok, rekapKelengkapan, statusButir } from '../../site/kelengkapan.js';

const G = [{ id: 'A', pendek: 'A', kelompok: 'A. Tim', bagian: [{ lingkup: 'umum', kalimat: [{ id: 't', teks: '[isi: satu] dan [isi: dua].' }] }] },
           { id: 'B', pendek: 'B', kelompok: 'B. Luar', bagian: [{ lingkup: 'b1', kalimat: [{ id: 'k', teks: 'Tanpa kotak.' }] }] }];
const dasar = { kelompok: G, narasi: {}, tugas: {}, tim: [], dosen: [], jumlah: {}, dokumen: [], butirBukti: [], pengaturan: [], karya: [], karyaBukti: [], ts: 2026 };
const cari = (h, id, judul) => h.bagian.find(b => b.id === id).butir.find(x => x.judul === judul);

test('statusButir: tiga keadaan', () => {
  assert.deepEqual([statusButir(0, 3), statusButir(1, 3), statusButir(3, 3)], ['belum', 'sebagian', 'selesai']);
});

test('hitungKelompok: kotak berisi [..] sama dengan belum selesai, seperti Narasi LED', () => {
  assert.deepEqual(hitungKelompok(G[0], { 'umum|t|satu|1': 'isi', 'umum|t|dua|1': 'SK [nomor]' }), { ada: 1, n: 2 });
});

test('kelompok tanpa kotak dihitung selesai', () => {
  assert.equal(cari(rekapKelengkapan(dasar), 'narasi', 'B. Luar').status, 'selesai');
});

test('tim: deskripsi dan jabatan yang kurang disebut namanya', () => {
  const h = rekapKelengkapan({ ...dasar, dosen: [{ id: 'a', nama: 'Ani', nidn: '1', jabatan: 'lektor', email: 'a@x' }, { id: 'b', nama: 'Budi', nidn: '2', email: 'b@x' }],
    tim: [{ id: 1, urutan: 1, dosen_id: 'a', deskripsi: 'Ketua' }, { id: 2, urutan: 2, dosen_id: 'b' }], tugas: { A: 'a@x' } });
  assert.deepEqual(cari(h, 'tim', 'Deskripsi kerja anggota').kurang, ['Budi']);
  assert.deepEqual(cari(h, 'tim', 'Nomor dan jabatan anggota').kurang, ['Budi']);
  assert.deepEqual(cari(h, 'tim', 'Penanggung jawab bagian').kurang, ['B']);
  assert.equal(cari(h, 'narasi', 'A. Tim').ket, 'Penanggung jawab: Ani');
});

test('data prodi: kosong, terisi, dan tabel tak terbaca dibedakan', () => {
  const h = rekapKelengkapan({ ...dasar, jumlah: { lkps_vmts: 3, lkps_tendik: 0, lkps_kerjasama: null } });
  assert.equal(cari(h, 'data', 'VMTS').status, 'selesai');
  assert.match(cari(h, 'data', 'Tenaga kependidikan').ket, /^Belum diisi/);
  assert.equal(cari(h, 'data', 'Kerja sama').ket, 'Tidak terbaca');
  assert.equal(cari(h, 'data', 'VMTS').href, 'data-prodi.html?tab=vmts');
});

test('bukti butir: dari kunci lama atau tautan pustaka, seperti rekap bukti Skor', () => {
  const h = rekapKelengkapan({ ...dasar, pengaturan: [{ kunci: 'bukti_b1', nilai: 'https://x' }, { kunci: 'ndtt', nilai: null, keterangan: 'Butir 26' }],
    dokumen: [{ id: 9, jenis: 'statuta', tahun: 2023, url: 'https://y' }], butirBukti: [{ id: 1, butir: 2, dokumen_id: 9 }] });
  const b = cari(h, 'bukti', 'Butir yang punya bukti');
  assert.equal(b.ada, 2);
  assert.ok(!b.kurang.includes('Butir 1') && !b.kurang.includes('Butir 2'));
  // Butir kualitatif dari bukti per unsur (pemilik 2026-11-10): baris 'Isian angka butir' diganti.
  const u = cari(h, 'bukti', 'Unsur penilaian berbukti');
  assert.ok(u.n > 100 && u.ada === 0);
  assert.ok(u.kurang.includes('[Universitas] Butir 39 unsur 1: Kebijakan dan tata kelola K3L, termasuk komitmen memenuhi peraturan K3L'));
  const u2 = cari(rekapKelengkapan({ ...dasar, butirBukti: [{ id: 2, butir: 39, unsur: 1, judul: 'K3L', url: 'https://x' }] }),
    'bukti', 'Unsur penilaian berbukti');
  assert.equal(u2.ada, 1);
});

test('karya: yang ditolak tidak dihitung; berkas juga dianggap bukti', () => {
  const h = rekapKelengkapan({ ...dasar, karya: [{ id: 1, status: 'terverifikasi', bukti_url: 'u' }, { id: 2, status: 'diajukan' }, { id: 3, status: 'ditolak' }, { id: 4, status: 'terverifikasi' }],
    karyaBukti: [{ karya_id: 4 }] });
  assert.equal(cari(h, 'karya', 'Karya terverifikasi').n, 3);
  assert.equal(cari(h, 'karya', 'Karya terverifikasi').ada, 2);
  assert.equal(cari(h, 'karya', 'Karya dengan tautan bukti').ada, 2);
});

test('TAB_DATA sama dengan tab yang ada di data-prodi.html', () => {
  const html = readFileSync(new URL('../../site/data-prodi.html', import.meta.url), 'utf8');
  // Tab bertanda tanpaBukti (daftar keahlian baku patch 61; CPL, peta MK-CPL, korelasi patch 71; testimoni situs publik
  // patch 141; kalender akademik patch 148) bukan data LKPS/LED: tidak masuk Kelengkapan.
  const tanpa = new Set([...html.matchAll(/\{ id: '(\w+)',[^\n]*\n[^\n]*tanpaBukti: true/g)].map(m => m[1]));
  const tab = [...html.matchAll(/^  \{ id: '(\w+)', tabel: '(\w+)'/gm)].filter(m => !tanpa.has(m[1])).map(m => `${m[1]}|${m[2]}`).sort();
  assert.deepEqual([...tanpa].sort(), ['bidang_keahlian', 'cpl', 'kalender_akademik', 'korelasi_cpl', 'mk_cpl', 'profil_lulusan', 'testimoni', 'topik_keahlian']);
  assert.deepEqual(TAB_DATA.map(([id, t]) => `${id}|${t}`).sort(), tab);
});

// Tugas per pihak (owner 2026-11-11): missing elements grouped by responsible party.
import { tugasPerPihak } from '../../site/kelengkapan.js';
test('tugasPerPihak: missing elements per party, uploaded ones and RPS 1/4 excluded', () => {
  const t = tugasPerPihak([{ butir: 39, unsur: 1, url: 'https://x' }]);
  assert.ok(!t.U.some(x => x.no === 39 && x.n === 1));       // uploaded
  assert.ok(t.U.some(x => x.no === 39 && x.n === 4));        // still missing (Universitas)
  assert.ok(t.F.some(x => x.no === 39 && x.n === 2));        // UPPS
  assert.ok(!t.P.some(x => x.no === 15 && [1, 4].includes(x.n)));   // from course RPS
  assert.ok(t.P.some(x => x.no === 15 && x.n === 2));
  assert.ok(t.F.some(x => x.no === 1 && x.n === 1) && t.U.some(x => x.no === 1 && x.n === 1));  // two parties
  assert.deepEqual(Object.keys(t), ['U', 'F', 'P', 'S', 'D']);
});
