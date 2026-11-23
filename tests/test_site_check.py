"""run_site_check.py: page judgement and config validation, without a browser."""
from pathlib import Path

import yaml

from run_site_check import FAILED, LOCKED, OK, WARNING, judge, validate

TEXT = "Kinerja program studi dan rekap dosen tersedia di halaman ini untuk dibaca."


def test_clean_page_is_ok():
    assert judge({}, {"text": TEXT}, []) == (OK, [])


def test_login_page_is_not_an_error():
    assert judge({}, {"text": "Perlu masuk", "needLogin": True}, [])[0] == LOCKED


def test_guide_quoting_the_login_button_is_not_locked():
    assert judge({}, {"text": TEXT + " klik Kirim tautan masuk"}, [])[0] == OK


def test_failures():
    assert judge({}, {"text": TEXT, "banner": True}, [])[0] == FAILED
    assert judge({}, {"text": TEXT}, ["x.js 404"])[0] == FAILED
    assert judge({}, {"text": "  "}, [])[0] == FAILED
    status, notes = judge({"must_contain": ["Skor"]}, {"text": TEXT}, [])
    assert status == FAILED and "Skor" in notes[0]


def test_warnings():
    assert judge({}, {"text": TEXT + " nilai undefined"}, [])[0] == WARNING
    assert judge({}, {"text": TEXT, "overflow": 40}, [])[0] == WARNING
    assert judge({}, {"text": TEXT, "brokenImages": ["a.png"]}, [])[0] == WARNING


def test_words_inside_other_words_are_not_broken_text():
    assert judge({}, {"text": TEXT + " FiNaNce undefinedly"}, [])[0] == OK


def test_config_in_repo_is_valid():
    cfg = yaml.safe_load((Path(__file__).parents[1] / "config.yaml").read_text(encoding="utf-8"))
    assert validate(cfg, "D:/x", False) == []


def test_validate_names_the_key():
    cfg = yaml.safe_load((Path(__file__).parents[1] / "config.yaml").read_text(encoding="utf-8"))
    assert any("paths.site_check_dir" in e for e in validate(cfg, None, False))
    assert any("paths.site_check_profile" in e for e in validate(cfg, "D:/x", True))
    cfg["site_check"]["browser"] = "safari"
    assert any("site_check.browser" in e for e in validate(cfg, "D:/x", False))
