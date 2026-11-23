// Impor ekspor Google Scholar (BibTeX) menjadi draf (site/impor-karya.js, pemilik 2026-11-10).
// Data sintetis meniru ciri ekspor Google Scholar (nama dan judul contoh).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { bacaBibtex, rapiLatex, judulRapi, mirip, pilihCocok, pertamaDariBib, drafDariBib, cariJudul, ambilDoi, teksBatas } from '../../site/impor-karya.js';

test('batas harian OpenAlex (429) menjadi galat batas dengan perkiraan jam pulih', async () => {
  const jawab429 = async () => ({ status: 429, ok: false, headers: { get: k => (k === 'retry-after' ? '3600' : null) } });
  await assert.rejects(cariJudul('apa saja', jawab429), e => e.batas === true && e.tunggu === 3600);
  await assert.rejects(ambilDoi('10.1/x', jawab429), e => e.batas === true);
  const sekarang = new Date(2026, 10, 10, 16, 3);
  assert.equal(teksBatas({ tunggu: 53816 }, sekarang), 'Batas harian OpenAlex untuk jaringan ini habis; coba lagi sekitar pukul 06.59 besok.');
  assert.equal(teksBatas({ tunggu: 600 }, sekarang), 'Batas harian OpenAlex untuk jaringan ini habis; coba lagi sekitar pukul 16.13.');
  const ok = async () => ({ status: 200, ok: true, json: async () => ({ results: [{ title: 'x' }] }) });
  assert.deepEqual(await cariJudul('x', ok), [{ title: 'x' }]);
});

const BIB = `@article{contoh2020kajian,
  title={Kajian {Banjir} Kota Contoh},
  author={Contoh, Dosen and Lain, Rekan and others},
  journal={Jurnal Teknik Contoh},
  volume={12},
  number={5},
  pages={401--415},
  year={2020},
  publisher={Penerbit Contoh/Asosiasi~…}
}

@inproceedings{lain2023model,
  title={Model Hujan untuk I\\_283 Contoh},
  author={Lain, Rekan and Contoh, Dosen},
  booktitle={Prosiding Seminar Contoh},
  year={2023},
  organization={Panitia}
}

@phdthesis{contoh2018disertasi,
  title={Disertasi Contoh},
  author={Contoh, Dosen},
  year={2018},
  school={Universitas Contoh}
}

@article{tanpatahun,
  title={Artikel Tanpa Tahun},
  author={Contoh, Dosen}
}

@inproceedings{日本語2016,
  title={土地利用の変化と洪水},
  author={呉 and others},
  booktitle={研究発表会},
  year={2016}
}
`;

test('BibTeX dibaca: kurung bersarang, LaTeX, entri tanpa tahun, aksara non-Latin', () => {
  const e = bacaBibtex(BIB);
  assert.equal(e.length, 5);
  assert.deepEqual([e[0].jenis, e[0].title, e[0].journal, e[0].year, e[0].pages], ['article', 'Kajian Banjir Kota Contoh', 'Jurnal Teknik Contoh', '2020', '401–415']);
  assert.equal(e[0].publisher, 'Penerbit Contoh/Asosiasi …');
  assert.equal(e[1].title, 'Model Hujan untuk I_283 Contoh');
  assert.equal(e[2].school, 'Universitas Contoh');
  assert.equal(e[3].year, undefined);
  assert.equal(e[4].title, '土地利用の変化と洪水');
  assert.equal(rapiLatex('A \\& B'), 'A & B');
});

test('judul dibandingkan tanpa huruf besar dan tanda baca', () => {
  assert.equal(judulRapi('Jakarta’s 2020 Flood: A Case-Study'), 'jakarta s 2020 flood a case study');
  assert.equal(mirip('Effect of land subsidence on flood', 'EFFECT OF LAND SUBSIDENCE ON FLOOD.'), 1);
  assert.ok(mirip('Kajian efektivitas sumur resapan', 'Adaptation to future flooding') < 0.5);
});

test('kecocokan OpenAlex: judul sangat mirip dan tahun selisih paling banyak 1', () => {
  const e = { title: 'Kajian Banjir Kota Contoh', year: '2020' };
  const w = (title, publication_year) => ({ title, publication_year });
  assert.equal(pilihCocok(e, [w('Kajian banjir kota contoh', 2021)]).publication_year, 2021);
  assert.equal(pilihCocok(e, [w('Kajian banjir kota contoh', 2023)]), null);          // tahun terlalu jauh
  assert.equal(pilihCocok(e, [w('Kajian kekeringan kota lain', 2020)]), null);        // judul lain
  assert.equal(pilihCocok({ title: 'Kajian Banjir Kota Contoh' }, [w('Kajian Banjir Kota Contoh', 2010)]).publication_year, 2010);
});

test('peran dari BibTeX: penulis pertama bila nama keluarganya bagian nama dosen', () => {
  assert.equal(pertamaDariBib('Contoh, Dosen and Lain, Rekan', 'Dosen Contoh'), true);
  assert.equal(pertamaDariBib('Lain, Rekan and Contoh, Dosen', 'Dosen Contoh'), false);
  assert.equal(pertamaDariBib('Dosen Contoh and Rekan Lain', 'Dosen Contoh'), true);
  assert.equal(pertamaDariBib('', 'Dosen Contoh'), false);
});

test('draf dari BibTeX saja: jenis, centang bawaan, tanpa DOI dan sitasi', () => {
  const e = bacaBibtex(BIB);
  const d0 = drafDariBib(e[0], { namaSaya: 'Dosen Contoh' });
  assert.deepEqual(d0.karya, { kategori: 'publikasi', status: 'draf', judul: 'Kajian Banjir Kota Contoh', jenis: 'jurnal',
    tahun: 2020, bulan: null, nama_terbitan: 'Jurnal Teknik Contoh', doi: null, url: null,
    volume: '12', nomor: '5', halaman: '401–415' });
  assert.equal(d0.penulis.peran, 'penulis_pertama');
  assert.equal(d0.centang, true);
  assert.deepEqual(d0.sitasi, []);
  assert.ok(!('volume' in drafDariBib(e[1]).karya));      // prosiding tanpa volume
  assert.equal(drafDariBib(e[1]).karya.jenis, 'prosiding');
  assert.equal(drafDariBib(e[1]).karya.nama_terbitan, 'Prosiding Seminar Contoh');
  assert.equal(drafDariBib(e[2]).centang, false);          // disertasi
  assert.equal(drafDariBib(e[2]).karya.jenis, 'lainnya');
  assert.equal(drafDariBib(e[3]).centang, false);          // tanpa tahun
});
