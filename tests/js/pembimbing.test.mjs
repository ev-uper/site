// Cari calon pembimbing TA (pemilik 2026-11-16; site/pembimbing.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { kata, topikDisebut, siapkan, cariPembimbing } from '../../site/pembimbing.js';

const D = {
  keahlian_baku: {
    bidang: [{ kode: 'AIR', nama: 'Sumber daya air' }],
    topik: [
      { kode: 'AIR02', bidang: 'AIR', nama: 'Banjir dan pengendaliannya', nama_en: 'Floods and flood control',
        sinonim: ['banjir', 'genangan'], padanan: ['flood', 'banjir', 'genangan', 'inundation'] },
      { kode: 'TRN05', bidang: 'TRN', nama: 'Perkerasan jalan', nama_en: 'Pavement', padanan: ['pavement', 'aspal', 'beton'] },
      { kode: 'MAT01', bidang: 'MAT', nama: 'Teknologi beton', nama_en: 'Concrete technology', padanan: ['beton', 'concrete'] },
    ],
  },
  dosen: [
    { nama: 'Ani Air', slug: 'ani-air', topik_keahlian: ['AIR02'] },
    { nama: 'Budi Jalan', slug: 'budi-jalan', topik_keahlian: ['TRN05'], bidang_keahlian: 'Rekayasa transportasi' },
    { nama: 'Cici Beton', slug: 'cici-beton' },
    { nama: 'Tamu', slug: null },
  ],
  publikasi: [
    { judul: 'Urban inundation mapping with a 2D model', tahun: 2026, penulis: [{ slug: 'cici-beton' }],
      topik: [{ t: 'Flood Risk Assessment and Management' }] },
    { judul: 'Self-compacting concrete with fly ash', tahun: 2025, penulis: [{ slug: 'cici-beton' }] },
    { judul: 'Kinerja simpang bersinyal', tahun: 2025, penulis: [{ slug: 'budi-jalan' }] },
  ],
  kegiatan: [{ judul: 'Sistem peringatan dini banjir', tahun: 2026, kategori: 'penelitian', penulis: [{ slug: 'ani-air' }] }],
};

test('common words and English plurals are normalised', () => {
  assert.deepEqual(kata('Analisis Pengaruh Floods terhadap jalan di Kota'), ['flood']);
});

test('a title names standard topics through their synonyms', () => {
  assert.deepEqual(topikDisebut('Pemetaan genangan di perumahan', D.keahlian_baku).map(t => t.kode), ['AIR02']);
});

test('only lecturers with a slug are candidates', () => {
  assert.deepEqual(siapkan(D).dosen.map(d => d.slug), ['ani-air', 'budi-jalan', 'cici-beton']);
});

test('a matching standard topic ranks first; synonyms bridge to English publications', () => {
  const { topik, hasil } = cariPembimbing('Pemetaan genangan di perumahan', siapkan(D));
  assert.deepEqual(topik.map(t => t.nama), ['Banjir dan pengendaliannya']);
  assert.deepEqual(hasil.map(h => h.slug), ['ani-air', 'cici-beton']);
  assert.deepEqual(hasil[0].alasan[0], { jenis: 'topik', label: 'Banjir dan pengendaliannya' });
  assert.equal(hasil[1].alasan[0].label, 'Urban inundation mapping with a 2D model');
});

test('synonym words do not make another topic of a lecturer match', () => {
  // "concrete" names MAT01; its added synonym "beton" must not pull in Budi through the TRN05 pavement topic.
  const { hasil } = cariPembimbing('Retak concrete akibat suhu', siapkan(D));
  assert.ok(!hasil.some(h => h.slug === 'budi-jalan'));
});

test('weak matches far below the best are dropped, and nothing matches empty words', () => {
  const { hasil } = cariPembimbing('Kinerja simpang bersinyal', siapkan(D));
  assert.deepEqual(hasil.map(h => h.slug), ['budi-jalan']);
  assert.deepEqual(cariPembimbing('analisis studi kasus', siapkan(D)).hasil, []);
});
