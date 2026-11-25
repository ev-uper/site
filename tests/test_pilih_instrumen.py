"""pilih_instrumen: rujukan site/ -> site/instrumen/<id>/ (pemilik 2026-11-24).

Aturan yang diuji: rujukan di repo sesuai config.yaml; id/folder salah berbunyi
dan menyebut kuncinya; berganti instrumen mengganti id di semua rujukan (pintu,
modul campuran, skrip klasik di HTML) dan mempertahankan cap ?v=; instrumen
yang kurang berkas, kurang ekspor, atau tanpa berkas yang dirujuk ditolak.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR / "tools"))
import pilih_instrumen as pi  # noqa: E402

perlu_node = pytest.mark.skipif(not shutil.which("node"), reason="node tidak ada")
REF = pi.REFERENSI


def test_repo_references_match_config():
    assert pi.main(["--check"]) == 0


def test_every_instrument_folder_is_complete():
    for folder in sorted((AKAR / "site" / "instrumen").iterdir()):
        if folder.is_dir():
            pi.periksa_folder(AKAR / "site", folder.name)


def test_instrument_modules_import_nothing_from_site():
    """Modul instrumen tanpa impor ke site/: tidak ada impor melingkar (2026-11-24)."""
    for p in sorted((AKAR / "site" / "instrumen").rglob("*.js")):
        teks = p.read_text(encoding="utf-8")
        assert "from '../" not in teks and "import('../" not in teks, p.name


def salin_situs(tmp_path, ident=REF):
    site = tmp_path / "site"
    shutil.copytree(AKAR / "site" / "instrumen" / REF, site / "instrumen" / REF)
    (site / "bobot.js").write_text(f"export * from './instrumen/{REF}/bobot.js?v=2026-11-24-abc123';\n",
                                   encoding="utf-8")
    (site / "butir-manual.js").write_text(
        f"export {{ BUTIR_MANUAL }} from './instrumen/{REF}/butir-manual.js?v=2026-11-24-abc123';\n"
        "export const kunci = 1;\n", encoding="utf-8")
    (site / "monitoring.html").write_text(
        f"<script>el.src = 'instrumen/{REF}/ambang.js?v=' + Date.now();</script>\n", encoding="utf-8")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f"accreditation:\n  instrument: {ident}\n", encoding="utf-8")
    return site, cfg


def args(site, cfg, *extra):
    return [*extra, "--config", str(cfg), "--site", str(site)]


def buat_instrumen(site, ident, ganti=None):
    folder = site / "instrumen" / ident
    shutil.copytree(site / "instrumen" / REF, folder)
    (folder / "instrumen.json").write_text(json.dumps({"id": ident}), encoding="utf-8")
    for nama, (lama, baru) in (ganti or {}).items():
        p = folder / nama
        p.write_text(p.read_text(encoding="utf-8").replace(lama, baru), encoding="utf-8")
    return folder


def test_bad_id_names_the_key(tmp_path, capsys):
    site, cfg = salin_situs(tmp_path, "LAM Teknik")
    assert pi.main(args(site, cfg)) == 2
    assert "accreditation.instrument" in capsys.readouterr().err


def test_missing_folder_lists_existing(tmp_path, capsys):
    site, cfg = salin_situs(tmp_path, "lamemba-s2")
    assert pi.main(args(site, cfg)) == 2
    err = capsys.readouterr().err
    assert "site/instrumen/lamemba-s2/" in err and REF in err


def test_reference_instrument_is_a_no_op(tmp_path):
    site, cfg = salin_situs(tmp_path)
    assert pi.main(args(site, cfg, "--check")) == 0


@perlu_node
def test_switch_rewrites_every_reference_and_keeps_stamp(tmp_path):
    site, cfg = salin_situs(tmp_path, "contoh-s2")
    buat_instrumen(site, "contoh-s2")
    assert pi.main(args(site, cfg, "--check")) == 1
    assert pi.main(args(site, cfg)) == 0
    assert "'./instrumen/contoh-s2/bobot.js?v=2026-11-24-abc123'" in (site / "bobot.js").read_text(encoding="utf-8")
    assert "./instrumen/contoh-s2/butir-manual.js" in (site / "butir-manual.js").read_text(encoding="utf-8")
    assert "'instrumen/contoh-s2/ambang.js?v='" in (site / "monitoring.html").read_text(encoding="utf-8")
    assert pi.main(args(site, cfg, "--check")) == 0


@perlu_node
def test_missing_export_is_rejected(tmp_path, capsys):
    site, cfg = salin_situs(tmp_path, "contoh-s2")
    buat_instrumen(site, "contoh-s2", {"butir-manual.js": ("export const SEKSI_MANUAL", "const SEKSI_MANUAL")})
    assert pi.main(args(site, cfg)) == 2
    assert "SEKSI_MANUAL" in capsys.readouterr().err


def test_missing_classic_script_is_rejected(tmp_path, capsys):
    site, cfg = salin_situs(tmp_path, "contoh-s2")
    (buat_instrumen(site, "contoh-s2") / "ambang.js").unlink()
    assert pi.main(args(site, cfg)) == 2
    assert "ambang.js" in capsys.readouterr().err


def test_reference_to_unknown_file_is_rejected(tmp_path, capsys):
    site, cfg = salin_situs(tmp_path)
    (site / "x.js").write_text(f"export * from './instrumen/{REF}/tidak-ada.js';\n", encoding="utf-8")
    assert pi.main(args(site, cfg)) == 2
    assert "tidak-ada.js" in capsys.readouterr().err
