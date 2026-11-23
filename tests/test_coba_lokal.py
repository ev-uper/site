"""Local trial with sample data (python coba_lokal.py; owner 2026-11-12).

The full run (copy site, bangun.py on a fake REST server, mock Supabase) needs the template's
supabase/instal-lengkap.sql and was checked by hand in paket/templat; these tests guard the
parts that can break silently: package lists, config validation, and that the sample data is
fictional and only names tables that exist.
"""
from __future__ import annotations

import importlib.util
import json
import re
from datetime import date
from pathlib import Path

import pytest

AKAR = Path(__file__).resolve().parents[1]


def _muat(nama, path):
    spec = importlib.util.spec_from_file_location(nama, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# cv-data: tools/...; repo templat: berkas yang sama di akar dan coba/ (make_package.py TAMBAH).
_ada = lambda *xs: next((AKAR / x for x in xs if (AKAR / x).is_file()), AKAR / xs[0])
coba = _muat("coba_lokal_uji", _ada("tools/coba_lokal.py", "coba_lokal.py"))
seed = _muat("seed_uji", _ada("tools/coba/seed.py", "coba/seed.py"))
inst = _muat("install_uji", _ada("tools/install.py", "install.py"))


def test_package_lists_match_installer():
    assert coba.PAKET == inst.PAKET


def test_port_comes_from_config_and_is_validated(tmp_path):
    assert 1024 <= coba.baca_config(AKAR / "config.yaml")["port"] <= 65535
    f = tmp_path / "config.yaml"
    for salah in ("coba_lokal:\n  port: 80\n", "coba_lokal:\n  port: '8790'\n", "lain: 1\n"):
        f.write_text(salah, encoding="utf-8")
        with pytest.raises(SystemExit):
            coba.baca_config(f)


def _data(tmp_path):
    sql = tmp_path / "instal-lengkap.sql"
    sql.write_text("INSERT INTO public.ref_kelompok_dana (kode, nama, urutan) VALUES ('pt', 'Perguruan tinggi', 1);\n", encoding="utf-8")
    return seed.buat(sql, date(2026, 11, 12))


def test_sample_data_is_fictional(tmp_path):
    d = _data(tmp_path)
    emails = {r["email"] for r in d["dosen"]}
    assert emails and all(e.endswith("@contoh.ac.id") for e in emails)
    teks = json.dumps(d, ensure_ascii=False)
    assert not re.search(r"pertamina|\buper\b|teknik sipil", teks, re.I)
    assert d["ref_kelompok_dana"] == [{"kode": "pt", "nama": "Perguruan tinggi", "urutan": 1}]


def test_sample_tables_exist_in_schema(tmp_path):
    dibuat = set()
    # cv-data: patch NN-*.sql; repo templat: satu berkas instal-lengkap.sql.
    for p in [*(AKAR / "supabase").glob("[0-9][0-9]*.sql"), *(AKAR / "supabase").glob("instal-lengkap.sql")]:
        dibuat |= set(re.findall(r"create\s+table\s+(?:if\s+not\s+exists\s+)?public\.([a-z0-9_]+)", p.read_text(encoding="utf-8"), re.I))
    tak_ada = sorted(set(_data(tmp_path)) - dibuat)
    assert not tak_ada, tak_ada


def test_new_module_samples_use_relative_dates(tmp_path):
    d = _data(tmp_path)
    t = d["rapat_tindak"][0]
    assert t["tenggat"] == "2026-11-09" and t["pj_dosen_id"] == d["dosen"][1]["id"]   # Adi: overdue item
    assert d["ami_temuan"][0]["pj_email"] == "adi@contoh.ac.id"


def test_trial_output_never_committed():
    assert "/coba-lokal/" in (AKAR / ".gitignore").read_text(encoding="utf-8")
    mp = AKAR / "tools" / "make_package.py"          # hanya di cv-data; repo templat tidak membawanya
    if mp.is_file():
        assert '"coba_lokal.py": ALAT / "coba_lokal.py"' in mp.read_text(encoding="utf-8")


def test_build_copy_has_no_secrets_or_archive(tmp_path):
    """bangun.py runs in a copy (2026-11-12): in the repo it would read rahasia.env (real Supabase)
    and overwrite arsip/, laporan-internal.html and the published data.json."""
    akar = tmp_path / "repo"
    for f, isi in {"bangun.py": "x", "site/index.html": "x", "rahasia.env": "RAHASIA", ".env.local": "RAHASIA",
                   ".cdsapirc": "RAHASIA", "arsip/prodi.sqlite": "x", "data-prodi.xlsx": "x", ".git/config": "x",
                   "laporan-internal.html": "x", "rahasia.env.contoh": "contoh", "tools/coba/seed.py": "x"}.items():
        (akar / f).parent.mkdir(parents=True, exist_ok=True)
        (akar / f).write_text(isi, encoding="utf-8")
    s = coba.salin_sumber(akar, tmp_path / "salinan")
    ada = sorted(str(p.relative_to(s)).replace("\\", "/") for p in s.rglob("*") if p.is_file())
    assert ada == ["bangun.py", "rahasia.env.contoh", "site/index.html", "tools/coba/seed.py"]
    assert "RAHASIA" not in "".join(p.read_text(encoding="utf-8") for p in s.rglob("*") if p.is_file())
