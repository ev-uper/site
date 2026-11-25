// Minimal zip reader (central directory) for .docx/.xlsx parts in tests (2026-11-24).
// bacaZip(buffer) -> { 'word/document.xml': () => string, ... }
import { inflateRawSync } from 'node:zlib';

export function bacaZip(buf){
  const eocd = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  const n = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  const isi = {};
  for (let i = 0; i < n; i++) {
    const metode = buf.readUInt16LE(p + 10), ukuran = buf.readUInt32LE(p + 20);
    const nNama = buf.readUInt16LE(p + 28), nEkstra = buf.readUInt16LE(p + 30), nKom = buf.readUInt16LE(p + 32);
    const lokal = buf.readUInt32LE(p + 42);
    const nama = buf.toString('utf8', p + 46, p + 46 + nNama);
    const data0 = lokal + 30 + buf.readUInt16LE(lokal + 26) + buf.readUInt16LE(lokal + 28);
    const mentah = buf.subarray(data0, data0 + ukuran);
    isi[nama] = () => (metode === 8 ? inflateRawSync(mentah) : mentah).toString('utf8');
    p += 46 + nNama + nEkstra + nKom;
  }
  return isi;
}
