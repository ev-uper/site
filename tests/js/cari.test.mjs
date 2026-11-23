// Site-wide search (owner 2026-11-12).
import test from 'node:test';
import assert from 'node:assert/strict';
import { normal, indeksHalaman, indeksButir, indeksPublik, cari, kelompokkan, kueriAman, cariSupabase } from '../../site/cari.js';
import { BUTIR_MANUAL } from '../../site/butir-manual.js';
import { BUTIR_DATA } from '../../site/butir-data.js';

const D = {
  dosen: [{ nama: 'Ani Wijaya', slug: 'ani-wijaya', bidang_keahlian: 'Hidrologi', kata_kunci: ['banjir'] },
          { nama: 'Budi Santoso', slug: 'budi-santoso', bidang_keahlian: 'Struktur' }],
  publikasi: [{ judul: 'Analisis Banjir Perkotaan', tahun: 2026, terbitan: 'Jurnal Teknik', doi: '10.1/abc',
                penulis: [{ nama: 'Ani Wijaya', slug: 'ani-wijaya' }], mitra: [{ nama: 'Balai Sungai Contoh' }] }],
  kegiatan: [{ judul: 'Pendampingan drainase desa', tahun: 2025, kategori: 'pkm', penulis: [{ nama: 'Budi Santoso' }], mitra: [{ nama: 'Desa Contoh' }] }],
  luaran_dosen: [{ judul: 'Buku Hidrologi Terapan', tahun: 2026, nama_bagian: 'Buku ber-ISBN', dosen: ['Ani Wijaya'] }],
  rekognisi: [{ nama_kegiatan: 'Invited speaker banjir', tahun: 2026, dosen: 'Budi Santoso' }],
};

test('normalising: case, accents, punctuation', () => {
  assert.equal(normal('  Café—Beton, Pracetak! '), 'cafe beton pracetak');
});

test('public index: lecturers, works with list links, outputs to lecturer page, partners counted', () => {
  const idx = indeksPublik(D);
  const r = cari(idx, 'banjir');
  assert.deepEqual(r.map(e => e.jenis + ':' + e.judul).slice(0, 2), ['karya:Analisis Banjir Perkotaan', 'karya:Invited speaker banjir']);
  assert.ok(r.some(e => e.jenis === 'dosen' && e.judul === 'Ani Wijaya'));     // keyword 'banjir'
  assert.equal(cari(idx, 'analisis banjir')[0].href, 'daftar.html?jenis=publikasi&q=Analisis%20Banjir%20Perkotaan');
  assert.equal(cari(idx, '10.1/abc')[0].judul, 'Analisis Banjir Perkotaan');       // DOI
  assert.equal(cari(idx, 'drainase')[0].href, 'daftar.html?jenis=pkm&q=Pendampingan%20drainase%20desa');
  assert.equal(cari(idx, 'buku hidrologi')[0].href, 'dosen/ani-wijaya.html');
  assert.equal(cari(idx, 'invited')[0].href, 'dosen/budi-santoso.html');
  const m = cari(idx, 'balai sungai').find(e => e.jenis === 'mitra');
  assert.equal(m.ket, '1 karya bersama');
});

test('optional public pages follow the switched-off modules', () => {
  const nyala = cari(indeksPublik(D), 'kepakaran'), mati = cari(indeksPublik(D, k => k !== 'kepakaran'), 'kepakaran');
  assert.ok(nyala.some(e => e.href === 'keahlian.html') && !mati.some(e => e.href === 'keahlian.html'));
});

test('60 accreditation items; exact item number ranks first', () => {
  const b = indeksButir(BUTIR_MANUAL, BUTIR_DATA);
  assert.equal(b.length, 60);
  assert.deepEqual(b.slice(0, 2).map(x => x.no), ['1', '2']);
  assert.equal(cari(b, '23')[0].href, 'skor.html#butir-23');
  assert.equal(cari(b, 'butir 6')[0].no, '6');
  // numbers match whole words: "23" is not every title containing "2023"
  const campur = [...b, ...indeksPublik({ publikasi: [{ judul: 'Studi kasus 2023', tahun: 2023 }] })];
  assert.deepEqual(cari(campur, '23').map(e => e.jenis), ['butir']);
  assert.equal(cari(campur, '2023')[0].judul, 'Studi kasus 2023');
});

test('workspace pages: menu entries, everyday words, tab shortcuts only when allowed', () => {
  const modul = [{ judul: 'Operasional', halaman: [{ href: 'rapat.html', judul: 'Rapat dan notulen', ket: 'Agenda' }] },
                 { judul: 'Data saya', halaman: [{ href: 'karya.html', judul: 'Karya dosen', ket: 'Publikasi' }] }];
  const idx = indeksHalaman(modul, h => h !== 'karya.html#bkd');
  assert.equal(cari(idx, 'notulen')[0].href, 'rapat.html');
  assert.equal(cari(idx, 'karya saya')[0].href, 'karya.html#saya');
  assert.ok(!cari(idx, 'bkd').some(e => e.href === 'karya.html#bkd'));
});

test('every word must match; at most six per kind; grouped in fixed order', () => {
  const idx = indeksPublik(D);
  assert.deepEqual(cari(idx, 'banjir struktur'), []);
  assert.deepEqual(cari(idx, '   '), []);
  const banyak = Array.from({ length: 9 }, (_, i) => ({ jenis: 'karya', judul: `Beton ${i}`, ket: '', href: '#', kunci: `beton ${i}`, kJudul: `beton ${i}` }));
  assert.equal(cari(banyak, 'beton').length, 6);
  const g = kelompokkan([...cari(idx, 'ani'), ...cari(indeksButir(BUTIR_MANUAL, BUTIR_DATA), '1')]);
  assert.deepEqual(g.map(x => x.jenis), ['butir', 'dosen', 'karya']);
});

test('database search: safe filter text, results re-checked locally, unreadable tables skipped', async () => {
  assert.equal(kueriAman('a,b(c)"d\'*e%'), 'a b c d e');
  const panggilan = [];
  const tabel = { dokumen: [{ id: 1, judul: 'SK Kurikulum 2024', jenis: 'kurikulum', tahun: 2024, url: 'https://drive/x' },
                            { id: 2, judul: 'Lain', jenis: 'statuta', tahun: 2023 }],
                  rapat: [{ id: 7, judul: 'Rapat kurikulum', tanggal: '2026-11-01' }],
                  rapat_tindak: [], ami_temuan: null };
  const sb = { from: t => { const q = { select: () => q, or: f => { panggilan.push([t, f]); return q; }, ilike: () => q, limit: () => q,
    then: (ok, no) => Promise.resolve(tabel[t] === null ? { error: { message: 'denied' } } : { data: tabel[t] }).then(ok, no) }; return q; } };
  const r = await cariSupabase(sb, 'kurikulum', { rapat: true, admin: false });
  assert.deepEqual(r.map(e => `${e.jenis}:${e.judul}`), ['rapat:Rapat kurikulum', 'dokumen:SK Kurikulum 2024']);
  assert.equal(r.find(e => e.jenis === 'dokumen').luar, true);
  assert.ok(panggilan.every(([, f]) => f.includes('*kurikulum*')));
  assert.deepEqual(await cariSupabase(sb, 'ku'), []);                                     // under 3 letters
  const tanpaRapat = await cariSupabase(sb, 'kurikulum', { rapat: false });
  assert.ok(!tanpaRapat.some(e => e.jenis === 'rapat'));
});

test('public index: expertise groups, courses, labs, achievements, news, titled lecturer names (owner 2026-11-22)', () => {
  const P = {
    situs: { kelompok_keahlian: [{ kode: 'AIR', nama: 'Rekayasa Sumber Daya Air', berkas: 'bidang-rekayasa-sumber-daya-air.html', cakupan: 'Hidrologi' }],
             peminatan_lain: [{ kode: 'UMUM', nama: 'Sipil umum' }] },
    kurikulum: [{ kode: 'K26', mk: [
      { kode: '41413', nama: 'Hidrologi Lanjut', sks: 3, sifat: 'pilihan', peminatan: 'AIR', nama_en: 'Advanced Hydrology', berkas: 'mk-41413-hidrologi-lanjut.html' },
      { kode: '41301', nama: 'Geologi Dasar', sks: 2, semester: 2, sifat: 'wajib', berkas: 'mk-41301-geologi-dasar.html' }] },
      { kode: 'K21', mk: [{ kode: '40001', nama: 'Mekanika Lama', sks: 3 }] }],
    dosen: [{ nama: 'Ani', nama_gelar: 'Dr. Ani, S.T.', slug: 'ani' }],
    laboratorium: [{ id: 7, nama: 'Lab Hidraulika', ringkasan: 'Praktikum hidraulika.', layanan: ['Uji debit'], alat: [{ nama: 'Flume' }], mk: [], bidang: ['AIR'] }],
    prestasi: [{ id: 3, capaian: 'Juara 1', kegiatan: 'Lomba Jembatan', tahun: 2026, tingkat: 'nasional', mahasiswa: [{ nama: 'Citra' }] }],
    kabar: [{ id: 9, judul: 'Kunjungan ke bendungan', tanggal: '2026-11-01', ringkasan: 'Mahasiswa mengunjungi bendungan.' }],
  };
  const idx = indeksPublik(P);
  const pertama = q => cari(idx, q)[0];
  assert.equal(pertama('hidrologi lanjut').href, 'mk-41413-hidrologi-lanjut.html');
  assert.equal(pertama('hidrologi lanjut').ket, '41413 · 3 sks · Pilihan Rekayasa Sumber Daya Air');
  assert.equal(pertama('advanced hydrology').jenis, 'mk');
  assert.equal(pertama('41301').ket, '41301 · 2 sks · Semester 2');
  assert.equal(cari(idx, 'mekanika lama').length, 0);                     // kurikulum lama tanpa halaman
  assert.equal(pertama('sumber daya air').href, 'bidang-rekayasa-sumber-daya-air.html');
  assert.equal(pertama('ani').judul, 'Dr. Ani, S.T.');
  assert.equal(pertama('flume').href, 'laboratorium.html#lab-7');
  assert.equal(pertama('jembatan').href, 'prestasi.html#prestasi-3');
  assert.equal(pertama('bendungan').href, 'kabar.html#kabar-9');
  assert.ok(cari(idx, 'kurikulum').some(e => e.href === 'kurikulum.html'));
  assert.ok(cari(idx, 'kabar kegiatan').some(e => e.href === 'kabar.html'));
  assert.ok(!cari(indeksPublik({}), 'kabar kegiatan').some(e => e.href === 'kabar.html'));   // tanpa kabar: halaman tidak ditawarkan
  assert.deepEqual(kelompokkan(cari(idx, 'hidrologi')).map(g => g.jenis), ['bidang', 'mk']);
});

test('public index: thesis archive and contact page (owner 2026-11-22)', () => {
  const P = { situs: { kelompok_keahlian: [{ kode: 'AIR', nama: 'Sumber Daya Air' }], kontak: { email: 'info@contoh.ac.id' } },
              arsip_ta: [{ id: 4, judul: 'Analisis banjir Ciliwung', tahun: 2026, bidang: 'AIR', pembimbing: [{ nama: 'Dr. Ani' }] }] };
  const r = cari(indeksPublik(P), 'ciliwung')[0];
  assert.deepEqual([r.jenis, r.href, r.ket], ['ta', 'tugas-akhir.html#ta-4', 'Tugas akhir · 2026 · Sumber Daya Air']);
  assert.ok(cari(indeksPublik(P), 'dr ani').some(e => e.jenis === 'ta'));           // pembimbing ikut dicari
  assert.ok(cari(indeksPublik(P), 'arsip tugas akhir').some(e => e.href === 'tugas-akhir.html'));
  assert.ok(cari(indeksPublik(P), 'alamat').some(e => e.href === 'kontak.html'));
  assert.ok(!cari(indeksPublik({}), 'alamat').some(e => e.href === 'kontak.html'));
});

test('kerangka: header summary (kerangka.json) is not used as the search index (owner 2026-11-22)', () => {
  // kerangka.json punya 'jumlah' dan tanpa dosen/karya; indeks dari ringkasan ini kosong, jadi kerangka.js mengambil data.json.
  const ringkas = { prodi: 'Teknik Contoh', situs: {}, jumlah: { kabar: 0, foto: 0, arsip_ta: 0 } };
  assert.equal(indeksPublik(ringkas).filter(e => e.jenis !== 'halaman').length, 0);
});
