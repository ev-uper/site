"""Pilih instrumen akreditasi: arahkan rujukan site/ ke site/instrumen/<id>/ (pemilik 2026-11-24).

Isi khusus instrumen (bobot, syarat, unsur, butir manual, ambang, nanti rumus
butir dan peta LKPS/LED) ada di site/instrumen/<id>/. Halaman dan modul umum di
site/ merujuknya lewat path yang memuat id, mis.

    export * from './instrumen/<id>/bobot.js';                      (pintu, site/bobot.js)
    export { BUTIR_MANUAL } from './instrumen/<id>/butir-manual.js'; (modul campuran)
    el.src = 'instrumen/<id>/ambang.js?v=' + Date.now();            (skrip klasik, monitoring.html)

Skrip ini membaca accreditation.instrument di config.yaml, memeriksa bahwa
folder instrumen itu punya semua berkas instrumen acuan (REFERENSI) dan
instrumen.json, bahwa tiap modul ES-nya mengekspor paling sedikit nama yang
diekspor modul acuan (diperiksa dengan Node), lalu mengganti <id> di semua
rujukan pada berkas .js/.html tingkat atas site/. Cap ?v= tidak disentuh.

    python tools/pilih_instrumen.py           ganti rujukan sesuai config
    python tools/pilih_instrumen.py --check   hanya periksa; kode 1 bila ada rujukan lain
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

AKAR = Path(__file__).resolve().parents[1]
SITE = AKAR / "site"

# Instrumen acuan kontrak: instrumen pertama yang lengkap dan teruji (bukan pilihan).
REFERENSI = "lam-teknik-s1"
ID_SAH = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Rujukan dalam kutip: './instrumen/<id>/x.js' atau 'instrumen/<id>/x.js', dengan/tanpa ?v=.
RUJUKAN = re.compile(r"""(['"](?:\./)?instrumen/)([a-z0-9]+(?:-[a-z0-9]+)*)(/[A-Za-z0-9_\-]+\.[a-z]+)""")
MODUL_ES = re.compile(r"^export\s", re.M)


class GalatInstrumen(Exception):
    pass


def baca_id(config: Path) -> str:
    cfg = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    nilai = (cfg.get("accreditation") or {}).get("instrument")
    if not isinstance(nilai, str) or not ID_SAH.match(nilai):
        raise GalatInstrumen(
            f"config.yaml accreditation.instrument: {nilai!r} tidak sah "
            "(huruf kecil/angka dipisah tanda minus, mis. lam-teknik-s1).")
    return nilai


def berkas_instrumen(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir() if p.is_file())


def periksa_folder(site: Path, ident: str) -> dict:
    folder = site / "instrumen" / ident
    if not folder.is_dir():
        ada = sorted(p.name for p in (site / "instrumen").iterdir() if p.is_dir())
        raise GalatInstrumen(
            f"config.yaml accreditation.instrument: folder site/instrumen/{ident}/ tidak ada. "
            f"Yang ada: {', '.join(ada) or '(kosong)'}.")
    info_path = folder / "instrumen.json"
    if not info_path.is_file():
        raise GalatInstrumen(f"site/instrumen/{ident}/instrumen.json tidak ada.")
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if info.get("id") != ident:
        raise GalatInstrumen(f"site/instrumen/{ident}/instrumen.json: id {info.get('id')!r} != {ident!r}.")
    perlu = berkas_instrumen(site / "instrumen" / REFERENSI)
    kurang = [m for m in perlu if not (folder / m).is_file()]
    if kurang:
        raise GalatInstrumen(f"site/instrumen/{ident}/ belum lengkap, tidak ada: {', '.join(kurang)}.")
    return info


def nama_ekspor(berkas: Path) -> set[str]:
    node = shutil.which("node")
    if not node:
        raise GalatInstrumen("node tidak ditemukan; diperlukan untuk memeriksa kontrak ekspor instrumen.")
    kode = ("const m = await import(process.argv[1]);"
            "console.log(JSON.stringify(Object.keys(m)));")
    r = subprocess.run([node, "--input-type=module", "-e", kode, berkas.resolve().as_uri()],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise GalatInstrumen(f"site/instrumen/{berkas.parent.name}/{berkas.name}: gagal dimuat Node:\n{r.stderr.strip()}")
    return set(json.loads(r.stdout))


def periksa_kontrak(site: Path, ident: str) -> None:
    """Tiap modul ES instrumen `ident` mengekspor semua nama modul acuan."""
    if ident == REFERENSI:
        return
    acuan_dir = site / "instrumen" / REFERENSI
    for m in berkas_instrumen(acuan_dir):
        acuan = acuan_dir / m
        if acuan.suffix != ".js" or not MODUL_ES.search(acuan.read_text(encoding="utf-8")):
            continue   # skrip klasik (ambang.js) dan data: cukup ada
        kurang = sorted(nama_ekspor(acuan) - nama_ekspor(site / "instrumen" / ident / m))
        if kurang:
            raise GalatInstrumen(
                f"site/instrumen/{ident}/{m} tidak mengekspor: {', '.join(kurang)} "
                f"(dipakai halaman; lihat site/instrumen/{REFERENSI}/{m}).")


def halaman(site: Path) -> list[Path]:
    return sorted(p for p in site.iterdir() if p.is_file() and p.suffix in (".js", ".html"))


def periksa_rujukan(site: Path, ident: str) -> None:
    """Tiap berkas yang dirujuk ada di folder instrumen terpilih."""
    hilang = []
    for p in halaman(site):
        for m in RUJUKAN.finditer(p.read_text(encoding="utf-8")):
            if not (site / "instrumen" / ident / m.group(3).lstrip("/")).is_file():
                hilang.append(f"site/{p.name} -> instrumen/{ident}{m.group(3)}")
    if hilang:
        raise GalatInstrumen("rujukan ke berkas instrumen yang tidak ada:\n    " + "\n    ".join(sorted(set(hilang))))


def rencana(site: Path, ident: str) -> dict[str, str]:
    """Berkas tingkat atas site/ yang merujuk instrumen lain, dengan isi barunya."""
    beda = {}
    for p in halaman(site):
        lama = p.read_text(encoding="utf-8")
        baru = RUJUKAN.sub(lambda m: m.group(1) + ident + m.group(3), lama)
        if baru != lama:
            beda[p.name] = baru
    return beda


def tulis(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".new")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="hanya periksa; kode 1 bila ada rujukan ke instrumen lain")
    ap.add_argument("--config", type=Path, default=AKAR / "config.yaml", help=argparse.SUPPRESS)
    ap.add_argument("--site", type=Path, default=SITE, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        ident = baca_id(a.config)
        info = periksa_folder(a.site, ident)
        periksa_kontrak(a.site, ident)
        periksa_rujukan(a.site, ident)
    except GalatInstrumen as e:
        print(f"  [GALAT] {e}", file=sys.stderr)
        return 2
    print(f"  Instrumen : {ident} ({info.get('lembaga')}, {info.get('kode')})")
    beda = rencana(a.site, ident)
    if not beda:
        print("  Semua rujukan site/ sudah ke instrumen ini.")
        return 0
    for n in sorted(beda):
        print(f"    {'merujuk instrumen lain' if a.check else 'diarahkan'} : site/{n}")
    if a.check:
        return 1
    for n, text in beda.items():
        tulis(a.site / n, text)
    print("  Jalankan stamp_versions.py (atau bangun-dan-push.bat) untuk cap ?v=.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
