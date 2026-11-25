"""stamp_versions: one version on every local import (owner 2026-11-04).

Fictitious site in tmp_path. Rules under test: all local imports, classic
<script src> and VERSI share one version; re-running changes nothing;
editing any file gives a new version (stylesheets included); module pages get the load-error
banner once; external URLs are left alone.
"""
import datetime as dt

import stamp_versions as sv

DAY1 = dt.date(2026, 11, 4)
DAY2 = dt.date(2026, 11, 5)


def site(tmp_path):
    (tmp_path / "skor.html").write_text(
        '<link href="https://fonts.example.org/css2?family=X" rel="stylesheet">\n'
        '<link rel="stylesheet" href="kepala.css">\n'
        '<script src="config.js"></script>\n'
        '<script src="https://cdn.example.org/lib.js"></script>\n'
        '<script type="module">\n'
        "import { a } from './a.js?v=lama';\n"
        "import { x } from 'https://cdn.example.org/x.js';\n"
        "const VERSI = '2026-11-03w';\n"
        "const m = await import('./a.js');\n"
        "</script>\n", encoding="utf-8")
    (tmp_path / "a.js").write_text("import { b } from './b.js';\nexport const a = 1;\n",
                                   encoding="utf-8")
    (tmp_path / "b.js").write_text("export const b = 2;\n", encoding="utf-8")
    (tmp_path / "index.html").write_text("<p>tanpa modul</p>\n", encoding="utf-8")
    return tmp_path


def run(path, day=DAY1):
    version, changed = sv.plan(path, day)
    for name, text in changed.items():
        sv.write(path / name, text)
    return version, changed


def test_all_local_references_share_one_version(tmp_path):
    p = site(tmp_path)
    v, _ = run(p)
    skor = (p / "skor.html").read_text(encoding="utf-8")
    assert v.startswith("2026-11-04-")
    assert f'src="config.js?v={v}"' in skor
    assert f'href="kepala.css?v={v}"' in skor
    assert f"from './a.js?v={v}'" in skor
    assert f"import('./a.js?v={v}')" in skor
    assert f"const VERSI = '{v}'" in skor
    assert f"from './b.js?v={v}'" in (p / "a.js").read_text(encoding="utf-8")


def test_external_urls_untouched(tmp_path):
    p = site(tmp_path)
    run(p)
    skor = (p / "skor.html").read_text(encoding="utf-8")
    assert 'src="https://cdn.example.org/lib.js"' in skor
    assert 'href="https://fonts.example.org/css2?family=X"' in skor
    assert "from 'https://cdn.example.org/x.js'" in skor


def test_rerun_is_a_no_op_even_on_another_day(tmp_path):
    p = site(tmp_path)
    v1, _ = run(p)
    v2, changed = run(p, DAY2)
    assert v2 == v1
    assert changed == {}


def test_editing_a_module_gives_a_new_version(tmp_path):
    p = site(tmp_path)
    v1, _ = run(p)
    (p / "b.js").write_text("export const b = 3;\n", encoding="utf-8")
    v2, changed = run(p, DAY2)
    assert v2 != v1 and v2.startswith("2026-11-05-")
    assert {"skor.html", "a.js"} <= set(changed)


def test_banner_added_once_to_module_pages_only(tmp_path):
    p = site(tmp_path)
    run(p)
    run(p, DAY2)
    skor = (p / "skor.html").read_text(encoding="utf-8")
    assert skor.count("d.id = 'galat-muat'") == 1
    assert skor.index("galat-muat") < skor.index('<script type="module">')
    assert "galat-muat" not in (p / "index.html").read_text(encoding="utf-8")


def test_subfolder_modules_are_stamped_and_fingerprinted(tmp_path):
    """Instrument modules live in site/instrumen/<id>/ (owner 2026-11-24)."""
    p = site(tmp_path)
    v0, _ = run(p)
    sub = p / "instrumen" / "x"
    sub.mkdir(parents=True)
    (sub / "c.js").write_text("import { a } from '../../a.js';\nexport const c = 1;\n", encoding="utf-8")
    (p / "b.js").write_text("export * from './instrumen/x/c.js';\nexport const b = 2;\n", encoding="utf-8")
    v1, changed = run(p, DAY2)
    assert v1 != v0
    assert "instrumen/x/c.js" in changed
    assert f"from '../../a.js?v={v1}'" in (sub / "c.js").read_text(encoding="utf-8")
    assert f"from './instrumen/x/c.js?v={v1}'" in (p / "b.js").read_text(encoding="utf-8")
    # editing only the nested module moves the version too
    (sub / "c.js").write_text((sub / "c.js").read_text(encoding="utf-8").replace("c = 1", "c = 2"),
                              encoding="utf-8")
    v2, _ = run(p, DAY2)
    assert v2 != v1


def test_flat_site_version_unchanged_by_recursive_scan(tmp_path):
    """Keys of top-level files are the bare name, as before 2026-11-24."""
    p = site(tmp_path)
    files = {f.name: f.read_text(encoding="utf-8") for f in p.iterdir() if f.is_file()}
    v, _ = sv.plan(p, DAY1)
    assert v == f"{DAY1:%Y-%m-%d}-{sv.fingerprint({n: sv.add_banner(n, t) for n, t in files.items()})}"


def test_check_mode_reports_without_writing(tmp_path, capsys):
    p = site(tmp_path)
    before = (p / "skor.html").read_text(encoding="utf-8")
    assert sv.main(["--check", "--site", str(p)]) == 1
    assert (p / "skor.html").read_text(encoding="utf-8") == before
    assert sv.main(["--site", str(p)]) == 0
    assert sv.main(["--check", "--site", str(p)]) == 0
