"""Cap versi pada semua impor lokal di site/ (pemilik 2026-11-04).

GitHub Pages menyajikan berkas dengan max-age 600, jadi browser bisa
mencampur halaman baru dengan modul lama dari cache. Tanpa ekspor yang
dicari, modul gagal diam-diam dan halaman kosong (kejadian 03j,
2026-11-03). Karena itu setiap impor lokal membawa ?v=<versi> yang sama:

    from './x.js?v=V'    import('./x.js?v=V')    <script src="x.js?v=V">
    <link href="x.css?v=V">

dan `const VERSI = 'V'` (label versi di skor.html) ikut V.

V = <tanggal>-<sidik isi>, sidik dihitung dari semua .html/.js di site/ (termasuk subfolder)
dengan cap versinya dibuang. Selama isi tidak berubah, V tetap: menjalankan
skrip ini berulang kali tidak mengubah berkas. Isi berubah -> V baru, jadi
browser mengambil semua modul baru sekaligus.

Halaman bermodul yang belum punya pesan galat muat (#galat-muat) diberi
BANNER, supaya galat tampil sebagai pesan, bukan halaman kosong.

Dijalankan otomatis oleh install.py dan workflow Bangun situs. Manual:
    python stamp_versions.py            cap berkas di site/
    python stamp_versions.py --check    hanya laporkan; kode 1 bila belum dicap
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent / "site"

BANNER = """<script>
// Galat saat memuat skrip (mis. modul lama dari cache bercampur dengan
// halaman baru) ditampilkan sebagai pesan, bukan halaman kosong.
addEventListener('error', function (e) {
  if (document.getElementById('galat-muat')) return;
  var d = document.createElement('div');
  d.id = 'galat-muat';
  d.style.cssText = 'margin:16px;padding:12px 14px;border:1px solid var(--merah);' +
    'background:var(--merah-m3);color:var(--ink);font:14px/1.5 system-ui,sans-serif';
  d.textContent = 'Halaman gagal dimuat: ' + (e.message || 'galat skrip') +
    '. Tekan Ctrl+Shift+R untuk memuat ulang tanpa cache; bila tetap muncul, kirim pesan ini ke admin.';
  document.body.insertBefore(d, document.body.firstChild);
});
</script>
"""

# from './x.js'  /  import('./x.js')  (kutip tunggal, seperti seluruh site/).
# Sejak 2026-11-24 juga subfolder dan naik folder: './instrumen/<id>/x.js',
# '../../x.js' (modul instrumen di site/instrumen/<id>/, pemilik 2026-11-24).
IMPORT = re.compile(
    r"""(from\s+|import\()'((?:\./|(?:\.\./)+)(?:[A-Za-z0-9_\-]+/)*[A-Za-z0-9_\-]+\.js)(?:\?v=[^']*)?'""")
# <script src="x.js">  (berkas lokal saja: tanpa garis miring atau skema)
SCRIPT_SRC = re.compile(r"""(<script\b[^>]*\bsrc=")([A-Za-z0-9_\-]+\.js)(?:\?v=[^"]*)?(")""")
# <link rel="stylesheet" href="x.css">  (kepala.css, 2026-11-04)
LINK_HREF = re.compile(r"""(<link\b[^>]*\bhref=")([A-Za-z0-9_\-]+\.css)(?:\?v=[^"]*)?(")""")
VERSI = re.compile(r"const VERSI = '[^']*'")
MODULE_TAG = '<script type="module">'


def stamp(text: str, version: str) -> str:
    """Set every local import and VERSI in one file to `version`."""
    text = IMPORT.sub(lambda m: f"{m.group(1)}'{m.group(2)}?v={version}'", text)
    for pola in (SCRIPT_SRC, LINK_HREF):
        text = pola.sub(lambda m: f"{m.group(1)}{m.group(2)}?v={version}{m.group(3)}", text)
    return VERSI.sub(f"const VERSI = '{version}'", text)


def add_banner(name: str, text: str) -> str:
    """Insert BANNER before the first module script of a page that lacks it."""
    if not name.endswith(".html") or MODULE_TAG not in text:
        return text
    if 'id="galat-muat"' in text or "getElementById('galat-muat')" in text:
        return text
    i = text.index(MODULE_TAG)
    return text[:i] + BANNER + text[i:]


def fingerprint(files: dict[str, str]) -> str:
    """Hash of all files with their version stamps removed."""
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode())
        h.update(b"\0")
        h.update(stamp(files[name], "").encode())
        h.update(b"\0")
    return h.hexdigest()[:6]


def current_version(files: dict[str, str]) -> str | None:
    for text in files.values():
        m = re.search(r"const VERSI = '([^']*)'", text)
        if m:
            return m.group(1)
    return None


def plan(site: Path, today: dt.date) -> tuple[str, dict[str, str]]:
    """Return the version and the files whose content would change.

    Keys are paths relative to site/ ('a.js', 'instrumen/lam-teknik-s1/b.js');
    top-level keys equal the bare name, so adding subfolders does not shift
    the fingerprint of an unchanged flat site."""
    old = {p.relative_to(site).as_posix(): p.read_text(encoding="utf-8")
           for p in sorted(site.rglob("*")) if p.is_file() and p.suffix in (".html", ".js", ".css")}
    with_banner = {n: add_banner(n, t) for n, t in old.items()}
    fp = fingerprint(with_banner)
    cur = current_version(old)
    version = cur if cur and cur.endswith("-" + fp) else f"{today:%Y-%m-%d}-{fp}"
    new = {n: stamp(t, version) for n, t in with_banner.items()}
    return version, {n: t for n, t in new.items() if t != old[n]}


def write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".new")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="hanya laporkan; kode 1 bila ada berkas yang belum dicap")
    ap.add_argument("--site", type=Path, default=SITE, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    version, changed = plan(a.site, dt.date.today())
    print(f"  Versi halaman : {version}")
    if not changed:
        print("  Cap versi sudah sesuai; tidak ada berkas yang diubah.")
        return 0
    for name in sorted(changed):
        print(f"    {'perlu dicap' if a.check else 'dicap'} : {name}")
    if a.check:
        return 1
    for name, text in changed.items():
        write(a.site / name, text)
    print(f"  {len(changed)} berkas dicap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
