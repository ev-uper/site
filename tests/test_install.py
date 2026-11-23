"""install.py: repo name is a question with default cv-site (owner 2026-11-09)."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[1]
# cv-data keeps it in tools/, the template repository at its root.
BERKAS = next(p for p in (AKAR / "tools" / "install.py", AKAR / "install.py") if p.exists())
_spec = importlib.util.spec_from_file_location("install_situs", BERKAS)
inst = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inst)


def test_site_address_follows_org_and_repo():
    assert inst.alamat_situs("Prodi-Contoh", "cv-site") == "https://prodi-contoh.github.io/cv-site"
    assert inst.alamat_situs("prodi-contoh", "kinerja") == "https://prodi-contoh.github.io/kinerja"
    # <org>.github.io is served at the root
    assert inst.alamat_situs("Prodi-Contoh", "prodi-contoh.github.io") == "https://prodi-contoh.github.io"


def test_repo_name_rules():
    for ok in ("cv-site", "kinerja_prodi", "prodi.github.io", "a"):
        assert inst._repo(ok) == "", ok
    for salah in ("", "CV-Site", "cv site", "cv-site.git", "-awal", "a/b"):
        assert inst._repo(salah), salah


def test_repo_question_sits_after_org_and_defaults_to_cv_site():
    kunci = [k for k, _, _ in inst.ISIAN]
    assert kunci.index("nama_repo") == kunci.index("github_org") + 1
    assert inst.BAWAAN["nama_repo"] == "cv-site"


def test_ini_without_or_with_empty_repo_uses_default(tmp_path):
    dasar = next(p for p in (AKAR / "tools" / "isian.contoh.ini", AKAR / "isian.contoh.ini") if p.exists())
    teks = dasar.read_text(encoding="utf-8")
    for ganti in ("nama_repo =\n", ""):
        f = tmp_path / "isian.ini"
        f.write_text(re.sub(r"nama_repo = [^\n]*\n", ganti, teks), encoding="utf-8")
        assert inst.dari_ini(f)["nama_repo"] == "cv-site"


def test_config_url_is_replaced_whatever_the_old_repo(tmp_path):
    cfg = tmp_path / "config.yaml"
    for lama in ("https://ganti-org.github.io/cv-site", "https://x.github.io/kinerja", "https://x.github.io"):
        cfg.write_text(f"site_check:\n  url: {lama}\n  browser: edge\n", encoding="utf-8")
        inst.ganti(cfg, inst.POLA_URL, "url: " + inst.alamat_situs("prodi-contoh", "kinerja"))
        assert cfg.read_text(encoding="utf-8") == \
            "site_check:\n  url: https://prodi-contoh.github.io/kinerja\n  browser: edge\n"


# Paket situs (owner 2026-11-12): "akreditasi" switches optional modules off in site/config.js.
def test_package_lists_match_site_fitur_js():
    js = (AKAR / "site" / "fitur.js").read_text(encoding="utf-8")
    blok = re.search(r"export const PAKET = \{(.*?)\};", js, re.S).group(1)
    dari_js = {k: re.findall(r"'([a-z_]+)'", v) for k, v in re.findall(r"(\w+): \[([^\]]*)\]", blok)}
    assert dari_js == inst.PAKET


def test_package_defaults_to_full_and_rejects_unknown(tmp_path):
    dasar = next(p for p in (AKAR / "tools" / "isian.contoh.ini", AKAR / "isian.contoh.ini") if p.exists())
    teks = dasar.read_text(encoding="utf-8")
    f = tmp_path / "isian.ini"
    f.write_text(re.sub(r"paket = [^\n]*\n", "", teks), encoding="utf-8")
    assert inst.dari_ini(f)["paket"] == "lengkap"
    f.write_text(teks.replace("paket = lengkap", "paket = akreditasi"), encoding="utf-8")
    assert inst.dari_ini(f)["paket"] == "akreditasi"
    f.write_text(teks.replace("paket = lengkap", "paket = sebagian"), encoding="utf-8")
    with pytest.raises(SystemExit):
        inst.dari_ini(f)


def test_config_js_feature_line_is_found_and_rewritten(tmp_path):
    cfg = tmp_path / "config.js"
    cfg.write_text((AKAR / "site" / "config.js").read_text(encoding="utf-8"), encoding="utf-8")
    inst.ganti(cfg, inst.POLA_FITUR, "window.FITUR_MATI = ['rapat', 'sdgs'];")
    assert "window.FITUR_MATI = ['rapat', 'sdgs'];" in cfg.read_text(encoding="utf-8")
    inst.ganti(cfg, inst.POLA_FITUR, "window.FITUR_MATI = [];")     # back to full: also found
    assert cfg.read_text(encoding="utf-8").count("window.FITUR_MATI = [];") == 1
