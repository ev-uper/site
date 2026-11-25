// Runs the butir formulas of site/skor.html in an isolated Node context,
// without a browser or Supabase (owner 2026-11-04: tests for scoring).
//
// The butir formulas are in site/instrumen/<id>/rumus-butir.js (irisan 3,
// owner 2026-11-24); the harness wires buatRumus() the way skor.html does.
// Helpers still inline in skor.html's <script type="module"> (IS, hitungMK, ...)
// are copied out of that script, so the tests run the exact code the site runs.
// Card builders are replaced by stubs: kartuButir(no, judul, isi, skor) returns the score.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import vm from 'node:vm';
// skor.html imports this from the module; the real one is passed in.
import { tkKepuasan } from '../../site/butir-manual.js';
import { cekPitaWT, adaTingkat, sesuaiTracer } from '../../site/tracer-skor.js';
import { karya4i, tautanPengutip } from '../../site/sitasi.js';
import { UNSUR, hitungUnsur, skorKunci, KUNCI_UNSUR, UNSUR_BUTIR, unsurAda } from '../../site/unsur-butir.js';
import { BUTIR_MANUAL } from '../../site/butir-manual.js';
import { bobotButir } from '../../site/bobot.js';
import { hitungTS, ampuPerTA } from '../../site/dosen-hitung.js';

// SKOR_HTML / RUMUS_JS point the harness at another copy (used to check that a
// broken formula makes the tests fail).
const SKOR = process.env.SKOR_HTML
  || fileURLToPath(new URL('../../site/skor.html', import.meta.url));
// Butir formulas computed from data moved to site/instrumen/<id>/rumus-butir.js
// (irisan 3, owner 2026-11-24); loaded through the door site/rumus-butir.js.
const { buatRumus, PEMBANTU_RUMUS } = await import(process.env.RUMUS_JS
  ? pathToFileURL(process.env.RUMUS_JS).href
  : new URL('../../site/rumus-butir.js', import.meta.url).href);

function moduleScript(html) {
  const m = html.match(/<script type="module">([\s\S]*?)<\/script>/);
  if (!m) throw new Error('skor.html: no module script');
  return m[1];
}

// Index just past the brace that closes the block opened at `open`.
// Skips strings, template literals (incl. nested ${...}), and comments.
function blockEnd(src, open) {
  let depth = 0;
  const tmpl = [];   // template nesting: brace depth at each `${`
  for (let i = open; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (c === '/' && n === '/') { i = src.indexOf('\n', i); continue; }
    if (c === '/' && n === '*') { i = src.indexOf('*/', i) + 1; continue; }
    if (c === "'" || c === '"') {
      for (i++; src[i] !== c; i++) if (src[i] === '\\') i++;
      continue;
    }
    if (c === '`' || (c === '}' && tmpl.length && tmpl[tmpl.length - 1] === depth)) {
      if (c === '}') tmpl.pop();
      for (i++; src[i] !== '`'; i++) {
        if (src[i] === '\\') { i++; continue; }
        if (src[i] === '$' && src[i + 1] === '{') { tmpl.push(depth); i++; break; }
      }
      continue;
    }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return i + 1;
  }
  throw new Error('unbalanced block');
}

function declaration(src, name) {
  const m = new RegExp(`^function ${name}\\(`, 'm').exec(src);
  if (!m) throw new Error(`skor.html: function ${name} not found`);
  return src.slice(m.index, blockEnd(src, src.indexOf('{', m.index)));
}

function constLine(src, name) {
  // up to the first line that ends with ';' (esc spans two lines)
  const m = new RegExp(`^const ${name} = [\\s\\S]*?;$`, 'm').exec(src);
  if (!m) throw new Error(`skor.html: const ${name} not found`);
  return m[0].replace(/^const /, 'var ');
}

// Functions still in skor.html; the butir formulas come from buatRumus() below.
const FUNCTIONS = [
  'IS',
  // Butir 9, 18, 19 dari Data prodi (pemilik 2026-11-10).
  'sksMK', 'hitungMK', 'hitungBOP', 'hitungDosen',
  // Butir 20, 22, 24 dari bukti per unsur (pemilik 2026-11-10).
  'unsurButir', 'catatanUnsur',
  // Butir 15 unsur 1/4 dari RPS mata kuliah (pemilik 2026-11-10).
  'rpsMK', 'unsurRPS', 'buktiEfektif',
  // Langkah tercepat (pemilik 2026-11-11).
  'skorDariUnsur', 'langkahTercepat',
];
const CONSTS = ['esc', 'f2', 'taDari', 'JENIS_BOP'];

// Stubs keep only the number; the HTML of the cards is not under test.
const STUBS = `
  function kartuButir(no, judul, isi, skor) { return skor; }
  function kartuManualKosong() { return null; }
  function rincianButir() { return ''; }
  function tabelNA() { return ''; }
`;

// Helpers skor.html imports from site/ modules and passes to buatRumus().
const IMPOR_RUMUS = { cekPitaWT, adaTingkat, sesuaiTracer, karya4i, tautanPengutip };

export function loadFormulas() {
  const src = moduleScript(readFileSync(SKOR, 'utf8'));
  const code = [
    ...CONSTS.map(n => constLine(src, n)),
    ...FUNCTIONS.map(n => declaration(src, n)),
    STUBS,
  ].join('\n');
  // DANA: nominal funding rows that skor.html loads behind RLS (butir 10-11).
  // P_DATA: rows for the card data lists (data-butir.js); null = not loaded, as before login.
  // KARYA_SITASI: publikasi + sitasi per tahun (butir 36); null = not loaded, as before login.
  // MK_DATA, DANA_PRODI, MHS_TA: Data prodi for butir 9, 18, 19; null = not loaded.
  const ctx = vm.createContext({ D: null, TS: null, PENG: {}, DANA: [], P_DATA: null, KARYA_SITASI: null,
    MK_DATA: null, DANA_PRODI: null, MHS_TA: null, DOSEN_KAT: null, PETA_JALAN: null, UNSUR_BUKTI: null, TINJAU: null,
    AMPU: new Map(), hitungTS, ampuPerTA,   // 154: mengampu per TA (kosong = syarat mengampu tidak diterapkan)
    tkKepuasan, cekPitaWT, adaTingkat, sesuaiTracer, karya4i, tautanPengutip, UNSUR, hitungUnsur, skorKunci, KUNCI_UNSUR, UNSUR_BUTIR, unsurAda, BUTIR_MANUAL, bobotButir });
  vm.runInContext(code, ctx, { filename: 'skor.html (extracted)' });
  // Same wiring as skor.html: page state read at each call, helpers looked up in
  // the context (so stubs and extracted functions are the ones used).
  const lokal = PEMBANTU_RUMUS.filter(n => !(n in IMPOR_RUMUS));
  const rumus = buatRumus({
    keadaan: () => ({ D: ctx.D, TS: ctx.TS, DANA: ctx.DANA, KARYA_SITASI: ctx.KARYA_SITASI, P_DATA: ctx.P_DATA }),
    ...Object.fromEntries(lokal.map(n => [n, (...a) => ctx[n](...a)])),
    ...IMPOR_RUMUS,
  });
  Object.assign(ctx, rumus.fungsi);
  ctx.daftarRumus = rumus.daftar;
  // run(fn, {D, TS, PENG, DANA}, ...args) sets the page globals, then calls
  // fn(...args) (args as in render() of skor.html, e.g. butirDana(9, ...)).
  ctx.run = (name, state, ...args) => {
    Object.assign(ctx, { PENG: {}, DANA: [], KARYA_SITASI: null, MK_DATA: null, DANA_PRODI: null, MHS_TA: null,
      DOSEN_KAT: null, PETA_JALAN: null, UNSUR_BUKTI: null, TINJAU: null, AMPU: new Map(), ...state });
    return ctx[name](...args);
  };
  return ctx;
}
