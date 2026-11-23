// Peta keahlian dosen (owner 2026-11-11).
import test from 'node:test';
import assert from 'node:assert/strict';
import { normal, token, profilKeahlian, cariPakar, petaTopik, usulanTA } from '../../site/keahlian.js';

const D = {
  dosen: [
    { nama: 'Ani Hidro', slug: 'ani', kata_kunci: ['Banjir', 'Hidrologi', 'GSMaP'], bidang_keahlian: 'Sumber daya air; Hidrologi' },
    { nama: 'Budi Beton', slug: 'budi', kata_kunci: ['Beton pracetak'], bidang_keahlian: 'Struktur' },
    { nama: 'Cici Tanpa', slug: 'cici' },
  ],
  publikasi: [
    { judul: 'Prakiraan banjir dengan satelit', tahun: 2025, penulis: [{ slug: 'ani' }],
      topik: [{ t: 'Flood Risk Assessment', s: 'Water Science' }, { t: 'Precipitation Measurement' }] },
    { judul: 'Kuat tekan beton pracetak', tahun: 2024, penulis: [{ slug: 'budi' }, { slug: 'cici' }], topik: [{ t: 'Concrete Properties' }] },
    { judul: 'Banjir rob di pesisir', tahun: 2023, penulis: [{ slug: 'cici' }], topik: [{ t: 'Flood Risk Assessment' }] },
  ],
  kegiatan: [{ judul: 'Pendampingan desa tangguh banjir', tahun: 2026, kategori: 'pkm', penulis: [{ slug: 'ani' }] }],
  luaran_dosen: [{ judul: 'Buku Hidrologi Terapan', tahun: 2025, dosen: ['ani hidro'] }],
};
const P = profilKeahlian(D);

test('normalisation and tokens drop accents, case, short and common words', () => {
  assert.equal(normal('Évaluasi  Banjir-Rob!'), 'evaluasi banjir rob');
  assert.deepEqual(token('Analisis risiko banjir di DAS Ciliwung dan Cisadane'), ['risiko', 'banjir', 'das', 'ciliwung', 'cisadane']);
});

test('profiles join publications, activities and outputs by slug or name', () => {
  const ani = P.find(p => p.slug === 'ani');
  assert.deepEqual(ani.karya.map(k => k.jenis), ['pkm', 'publikasi', 'luaran']);
  assert.deepEqual(ani.bidang, ['Sumber daya air', 'Hidrologi']);
  assert.equal(ani.topik.get('Flood Risk Assessment'), 1);
  assert.equal(P.find(p => p.slug === 'cici').karya.length, 2);
});

test('search: own keywords outrank titles; exact phrase bonus; reasons and supporting works', () => {
  const r = cariPakar(P, 'banjir');
  assert.deepEqual(r.map(x => x.slug), ['ani', 'cici']);
  assert.deepEqual(r[0].alasan.kata, ['Banjir']);
  assert.ok(r[0].skor > r[1].skor);
  assert.ok(r[0].karya.includes('Prakiraan banjir dengan satelit'));
  assert.deepEqual(cariPakar(P, 'flood').map(x => x.slug), ['ani', 'cici']);       // OpenAlex topic (English)
  assert.deepEqual(cariPakar(P, 'beton pracetak')[0].alasan.kata, ['Beton pracetak']);
  assert.ok(cariPakar(P, 'beton pracetak')[0].skor >= 5 * 2 + 10);
  assert.deepEqual(cariPakar(P, 'analisis dan studi'), []);                          // common words only
  assert.deepEqual(cariPakar(P, 'banjir', { kecuali: ['ani'] }).map(x => x.slug), ['cici']);
});

test('topic map merges spellings, counts lecturers and flags single-holder topics', () => {
  const m = petaTopik(P);
  const flood = m.find(x => x.label === 'Flood Risk Assessment');
  assert.deepEqual(flood.dosen, ['Ani Hidro', 'Cici Tanpa']);
  assert.equal(flood.tunggal, false);
  const hid = m.filter(x => normal(x.label) === 'hidrologi');
  assert.equal(hid.length, 1);                                    // keyword and field of expertise merged
  assert.equal(m.find(x => x.label === 'Beton pracetak').tunggal, true);
  assert.equal(m[0].dosen.length >= m[m.length - 1].dosen.length, true);
});

test('thesis suggestions spread the load and mark titles without a match', () => {
  const { hasil, beban } = usulanTA(P, ['Banjir di DAS Ciliwung', 'Banjir rob Jakarta', 'Beton pracetak gedung', 'Pariwisata halal', ''],
    { pembimbing: 1, penguji: 1 });
  assert.equal(hasil.length, 4);
  assert.equal(hasil[0].pembimbing[0].nama, 'Ani Hidro');
  assert.equal(hasil[2].pembimbing[0].nama, 'Budi Beton');
  assert.equal(hasil[3].tanpa, true);
  assert.ok(beban.find(([n]) => n === 'Ani Hidro')[1] >= 2);
});

import { topikDari } from '../../site/impor-karya.js';
test('OpenAlex topics: at most three, compact form, nameless ones dropped', () => {
  const w = { topics: [
    { display_name: 'Flood Risk', score: 0.91234, subfield: { display_name: 'Water Science' }, field: { display_name: 'Env' } },
    { display_name: '' }, { display_name: 'B', score: 0.5 }, { display_name: 'C' }, { display_name: 'D' }] };
  assert.deepEqual(topikDari(w), [{ t: 'Flood Risk', s: 'Water Science', f: 'Env', n: 0.912 },
    { t: 'B', s: '', f: '', n: 0.5 }, { t: 'C', s: '', f: '', n: 0 }]);
  assert.deepEqual(topikDari(null), []);
});

import { bacaKataKunci } from '../../site/profil-dosen.js';
test('profile keywords: same tidying as rapikan_kata_kunci in patch 60', () => {
  assert.deepEqual(bacaKataKunci(' Banjir , banjir;;  beton   pracetak\nGSMaP '), ['Banjir', 'beton pracetak', 'GSMaP']);
  assert.equal(bacaKataKunci(' , ; '), null);
  assert.equal(bacaKataKunci(Array.from({ length: 14 }, (_, i) => 'k' + i).join(',')).length, 10);
  assert.deepEqual(bacaKataKunci('a'.repeat(61) + ', pendek'), ['pendek']);
});

// Daftar keahlian baku (patch 61, owner 2026-11-12).
import { daftarBaku, topikDariTeks, petaBaku, matriksBaku } from '../../site/keahlian.js';
const KB = { bidang: [{ kode: 'AIR', nama: 'Sumber Daya Air', nama_en: 'Water Resources' }, { kode: 'MAT', nama: 'Material', nama_en: 'Materials' },
                      { kode: 'GEO', nama: 'Geoteknik', nama_en: 'Geotechnical' }],
  topik: [{ kode: 'AIR02', bidang: 'AIR', nama: 'Banjir', nama_en: 'Floods', sinonim: ['genangan', 'inundation'], padanan: ['flood', 'floods', 'banjir'] },
          { kode: 'AIR06', bidang: 'AIR', nama: 'Teknik pantai', nama_en: 'Coastal engineering', sinonim: ['rob'], padanan: ['coastal', 'pesisir', 'rob'] },
          { kode: 'MAT01', bidang: 'MAT', nama: 'Teknologi beton', nama_en: 'Concrete technology', sinonim: [], padanan: ['concrete', 'beton'] },
          { kode: 'GEO03', bidang: 'GEO', nama: 'Stabilitas lereng', nama_en: 'Slope stability', sinonim: [], padanan: ['slope', 'lereng', 'landslide'] }] };
const DB = { ...D, keahlian_baku: KB, dosen: D.dosen.map(d => ({ ...d, topik_keahlian: { ani: ['AIR02', 'XXX'], budi: ['MAT01'], cici: [] }[d.slug] })) };
const B = daftarBaku(DB), PB = profilKeahlian(DB);

test('standard list: terms in both languages and synonyms map to one topic; whole words only', () => {
  assert.equal(daftarBaku(D), null);
  assert.deepEqual(topikDariTeks(B, 'Genangan di Jakarta'), ['AIR02']);
  assert.deepEqual(topikDariTeks(B, 'Flood risk of coastal cities'), ['AIR02', 'AIR06']);
  assert.deepEqual(topikDariTeks(B, 'Kuat tekan beton pracetak'), ['MAT01']);
  assert.deepEqual(topikDariTeks(B, 'Program robotika'), []);          // "rob" inside a word does not count
  assert.deepEqual(topikDariTeks(null, 'banjir'), []);
});

test('profiles carry chosen topics (unknown codes dropped) and topics derived from works and OpenAlex topics', () => {
  const ani = PB.find(p => p.slug === 'ani'), cici = PB.find(p => p.slug === 'cici');
  assert.deepEqual(ani.pilihan, ['AIR02']);
  assert.equal(ani.dariKarya.get('AIR02'), 2);                         // flood forecast paper + PkM banjir
  assert.equal(cici.dariKarya.get('AIR02'), 1);                        // "Banjir rob" ...
  assert.equal(cici.dariKarya.get('AIR06'), 1);                        // ... is also coastal (rob)
  assert.equal(cici.dariKarya.get('MAT01'), 1);                        // shared concrete paper with Budi
});

test('search with the standard list: English or synonym finds the topic; own choice ranks first', () => {
  const r = cariPakar(PB, 'genangan', { B });
  assert.deepEqual(r.map(x => x.slug), ['ani', 'cici']);
  assert.deepEqual(r[0].alasan.baku, ['Banjir']);
  assert.ok(r[0].skor >= 6 + 2 * 2);
  const beton = cariPakar(PB, 'concrete', { B });
  assert.equal(beton[0].slug, 'budi');                                 // chose MAT01
  assert.equal(usulanTA(PB, ['Inundation modelling'], { pembimbing: 1, penguji: 0, B }).hasil[0].pembimbing[0].nama, 'Ani Hidro');
});

test('standard map: chosen/works per topic, single-holder and empty topics, shared work counted once, CSV matrix', () => {
  const m = petaBaku(PB, B);
  const air02 = m.baris.find(r => r.kode === 'AIR02');
  assert.deepEqual(air02.pilih, ['Ani Hidro']);
  assert.deepEqual(air02.dosen, ['Ani Hidro', 'Cici Tanpa']);
  assert.equal(m.baris.find(r => r.kode === 'MAT01').nKarya, 1);       // one paper by Budi and Cici
  assert.equal(m.baris.find(r => r.kode === 'AIR06').tunggal, true);
  assert.equal(m.baris.find(r => r.kode === 'GEO03').kosong, true);
  assert.deepEqual(m.bidang.find(b => b.kode === 'GEO'), { kode: 'GEO', nama: 'Geoteknik', nama_en: 'Geotechnical', topik: 1, dosen: 0, nKarya: 0, tunggal: 0, kosong: 1 });
  const x = matriksBaku(PB, B);
  assert.deepEqual(x[0].slice(0, 4), ['Kode', 'Bidang', 'Topik', 'Topic']);
  const r = x.find(r => r[0] === 'AIR02');
  assert.deepEqual(r.slice(4, 7), ['P+2', '', '1']);                  // Ani chose + 2 works, Budi none, Cici 1 work
  assert.equal(petaBaku(PB, null), null);
});
