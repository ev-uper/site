"""Pemulihan cadangan (supabase_archive.py pulihkan / bandingkan), pemilik 2026-11-11.

Bagian PGlite butuh node + tools/node_modules (npm install --prefix tools); dilewati bila tidak ada.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import supabase_archive as sa

ROOT = Path(sa.__file__).resolve().parent
ADA_NODE = shutil.which("node") and (ROOT / "tools" / "node_modules").is_dir()
perlu_node = pytest.mark.skipif(not ADA_NODE, reason="node atau tools/node_modules tidak ada")

# Skema mini dengan semua hal yang menyulitkan pemulihan.
SKEMA = """
create table public.induk (
  id bigint generated always as identity primary key,
  nama text not null, catatan text not null default '', aktif boolean not null default true,
  dibuat timestamptz not null default now(), dana numeric(14,0), info jsonb, tag text[], sdgs smallint[],
  norm text generated always as (lower(nama)) stored,
  induk_id bigint references public.induk(id), ubah text);
create function public.paksa() returns trigger language plpgsql as $$ begin new.ubah := 'trigger'; return new; end $$;
create trigger paksa before insert or update on public.induk for each row execute function public.paksa();
alter table public.induk enable row level security;
create table public.anak (induk_id bigint not null references public.induk(id) on delete cascade,
  kode uuid not null, primary key (induk_id, kode));
insert into public.induk (nama) values ('isi bawaan skema');
"""
# Baris seperti jawaban REST Supabase (bentuk yang ditulis backup()).
INDUK = [
    {"id": 5, "nama": "Anak Dulu", "catatan": "", "aktif": False, "dibuat": "2026-11-03T12:34:56.123456+00:00",
     "dana": 75500000, "info": {"b": [1, 2], "a": "x"}, "tag": ["a,b", "c \"kutip\""], "sdgs": [6, 13],
     "norm": "anak dulu", "induk_id": 9, "ubah": "asli"},
    {"id": 9, "nama": "Induk", "catatan": "ada", "aktif": True, "dibuat": "2026-01-01T00:00:00+00:00",
     "dana": None, "info": "teks biasa", "tag": None, "sdgs": [], "norm": "induk", "induk_id": None, "ubah": None},
]
ANAK = [{"induk_id": 5, "kode": "00000000-0000-4000-8000-000000000001"}]


def _folder(tmp_path, tabel):
    f = tmp_path / "cadangan"
    f.mkdir()
    for t, rows in tabel.items():
        (f / f"{t}.csv").write_bytes(sa.to_csv(rows))
    return f


def test_read_backup_empty_cell_is_null_and_missing_table_stops(tmp_path):
    f = _folder(tmp_path, {"induk": INDUK, "anak": ANAK})
    d = sa.read_backup(f, ["induk", "anak"])
    kol, baris = d["induk"]
    assert baris[0][kol.index("catatan")] is None and baris[0][kol.index("aktif")] == "false"
    assert json.loads(baris[0][kol.index("info")]) == {"a": "x", "b": [1, 2]}
    with pytest.raises(RuntimeError, match="tidak lengkap.*lain"):
        sa.read_backup(f, ["induk", "lain"])


def test_read_backup_keeps_crlf_inside_cells(tmp_path):
    """Teks yang ditempel dari Windows berisi CRLF; pemulihan harus mengembalikannya persis (lkps_vmts 2026-11-21)."""
    f = _folder(tmp_path, {"vm": [{"jenis": "ps", "misi": "1. Satu.\r\n\r\n2. Dua.\nTiga"}]})
    kol, baris = sa.read_backup(f, ["vm"])["vm"]
    assert baris[0][kol.index("misi")] == "1. Satu.\r\n\r\n2. Dua.\nTiga"


def test_restore_sql_is_one_block_and_check_lists_every_table(tmp_path):
    d = sa.read_backup(_folder(tmp_path, {"induk": INDUK, "anak": ANAK}), ["induk", "anak"])
    s = sa.restore_sql(d, "cadangan", "2026-11-11")
    assert s.count("do $blok$") == 1 and "overriding system value" in s and "disable trigger user" in s
    assert "2 tabel, 3 baris" in s
    c = sa.check_sql(d)
    assert "('induk', 2, (select count(*) from public.induk))" in c and "('anak', 1," in c


def test_compare_folders(tmp_path, capsys):
    a = _folder(tmp_path, {"induk": INDUK, "anak": ANAK})
    b = tmp_path / "b"
    shutil.copytree(a, b)
    assert sa.bandingkan(a, b) == 0
    (b / "anak.csv").write_bytes(sa.to_csv([]))
    assert sa.bandingkan(a, b) == 1
    assert "anak: BEDA — 1 baris hanya di cadangan, 0 baris hanya di b" in capsys.readouterr().out
    # Newer schema (a patch added a column after the backup): compared on the backup's columns.
    (b / "anak.csv").write_bytes(sa.to_csv([dict(r, kolom_baru=None) for r in ANAK]))
    assert sa.bandingkan(a, b) == 0
    assert "anak: identik (1 baris); kolom baru di b tidak dibandingkan: kolom_baru" in capsys.readouterr().out
    # A column of the backup missing from the restored copy is lost data.
    (b / "anak.csv").write_bytes(sa.to_csv([{"induk_id": 5} ]))
    assert sa.bandingkan(a, b) == 1
    assert "anak: BEDA — kolom tidak ada di b: kode" in capsys.readouterr().out


def test_pulihkan_writes_four_files_from_install_sql_and_never_overwrites(tmp_path, capsys):
    """Template repo: no patch files, so the schema is supabase/instal-lengkap.sql."""
    from datetime import date
    root = tmp_path / "repo"
    (root / "supabase").mkdir(parents=True)
    (root / "supabase" / "instal-lengkap.sql").write_text(SKEMA, encoding="utf-8")
    f = _folder(tmp_path, {"induk": INDUK, "anak": ANAK, "usang": []})
    cfg = {"supabase": {"tables": {"induk": "id", "anak": "induk_id,kode"}}}
    out = sa.pulihkan(cfg, f, root=root, today=date(2026, 11, 11))
    assert out == root / "pulih" / "cadangan-2026-11-11"
    assert sorted(p.name for p in out.iterdir()) == ["1-skema.sql", "2-data.sql", "3-periksa.sql", "LANGKAH.md"]
    # tools/make_package.py RUJUKAN_PATCH rewrites patch-like names to instal-lengkap.sql in the template.
    import re
    assert not any(re.search(r"\b\d\d[a-z]?-(?:patch|skema|lengkapi)[a-z0-9-]*\.sql", p.name) for p in out.iterdir())
    assert (out / "1-skema.sql").read_text(encoding="utf-8") == SKEMA
    assert "2 tabel, 3 baris" in (out / "LANGKAH.md").read_text(encoding="utf-8")
    assert "dilewati (tidak ada di config.yaml supabase.tables): usang" in capsys.readouterr().out
    with pytest.raises(RuntimeError, match="sudah ada"):
        sa.pulihkan(cfg, f, root=root, today=date(2026, 11, 11))


def _jalankan(tmp_path, skema, data):
    sk, dt, pr, out = (tmp_path / n for n in ("01.sql", "02.sql", "03.sql", "hasil.json"))
    sk.write_text(skema, encoding="utf-8")
    dt.write_text(sa.restore_sql(data), encoding="utf-8")
    pr.write_text(sa.check_sql(data), encoding="utf-8")
    r = subprocess.run(["node", str(ROOT / "tools" / "uji_pulihkan.mjs"), str(sk), str(dt), str(pr), str(out)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(out.read_text(encoding="utf-8"))


@perlu_node
def test_round_trip_keeps_ids_types_and_values_without_superuser(tmp_path):
    f = _folder(tmp_path, {"induk": INDUK, "anak": ANAK})
    h = _jalankan(tmp_path, SKEMA, sa.read_backup(f, ["induk", "anak"]))
    assert all(p["hasil"] == "cocok" for p in h["periksa"]), h["periksa"]
    for t in ("induk", "anak"):   # what backup() would write again equals the source
        assert {sa._row_key(r) for r in h["tabel"][t]} == sa._row_keys_from_csv((f / f"{t}.csv").read_bytes()), t
    assert h["urutan"]["induk"] == 9                       # next id is 10, no clash
    assert [r["ubah"] for r in sorted(h["tabel"]["induk"], key=lambda r: r["id"])] == ["asli", None]   # trigger off


@perlu_node
def test_orphan_reference_rolls_everything_back(tmp_path):
    rusak = [dict(INDUK[0], induk_id=77), INDUK[1]]
    data = sa.read_backup(_folder(tmp_path, {"induk": rusak, "anak": ANAK}), ["induk", "anak"])
    (tmp_path / "01.sql").write_text(SKEMA, encoding="utf-8")
    (tmp_path / "02.sql").write_text(sa.restore_sql(data), encoding="utf-8")
    (tmp_path / "03.sql").write_text("select 'induk' tabel, count(*)::int n, 'x' hasil from public.induk", encoding="utf-8")
    r = subprocess.run(["node", str(ROOT / "tools" / "uji_pulihkan.mjs")] + [str(tmp_path / n) for n in
                       ("01.sql", "02.sql", "03.sql", "h.json")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode != 0 and "induk_induk_id_fkey" in r.stderr


@perlu_node
def test_newer_table_outside_backup_must_be_empty(tmp_path):
    """A patch newer than the backup adds a table referencing a restored one (e.g. rapat -> dosen)."""
    data = sa.read_backup(_folder(tmp_path, {"induk": INDUK, "anak": ANAK}), ["induk", "anak"])
    baru = SKEMA + "create table public.catatan (id bigint primary key, induk_id bigint references public.induk(id));\n"
    h = _jalankan(tmp_path, baru, data)                       # empty newer table: restore proceeds
    assert all(p["hasil"] == "cocok" for p in h["periksa"])
    isi = baru + "insert into public.catatan values (1, (select min(id) from public.induk));\n"
    with pytest.raises(AssertionError, match="Tabel di luar cadangan berisi data.*catatan"):
        _jalankan(tmp_path, isi, data)


@perlu_node
def test_backup_column_missing_in_target_stops(tmp_path):
    lebih = [dict(r, kolom_baru="x") for r in INDUK]
    data = sa.read_backup(_folder(tmp_path, {"induk": lebih, "anak": ANAK}), ["induk", "anak"])
    with pytest.raises(AssertionError, match="induk.kolom_baru"):
        _jalankan(tmp_path, SKEMA, data)


@perlu_node
@pytest.mark.skipif(not (ROOT / "cadangan" / "dosen.csv").is_file(), reason="tidak ada cadangan (repo templat)")
def test_real_backup_round_trip(tmp_path):
    """Gladi penuh: skema dari semua patch + cadangan/ asli; tiap baris kembali persis."""
    from cpl.config import load_config
    cfg = load_config(ROOT / "config.yaml")
    # Tables added after the last backup (a newer patch) have no CSV yet; restore what the backup holds.
    tabel = [t for t in cfg["supabase"]["tables"] if (ROOT / "cadangan" / f"{t}.csv").is_file()]
    assert len(tabel) >= len(cfg["supabase"]["tables"]) - 5
    data = sa.read_backup(ROOT / "cadangan", tabel)
    h = _jalankan(tmp_path, sa.full_schema(ROOT).decode("utf-8"), data)
    assert [p for p in h["periksa"] if p["hasil"] != "cocok"] == []
    # Compared on the backup's columns: patches newer than the backup add (empty) columns.
    # Numbers are compared as numbers: the backup writes REST JSON numbers through Python (3.00 -> "3.0"),
    # the restored database prints "3"; same value (pengaturan.ambang_edom, patch 68, 2026-11-12).
    from decimal import Decimal
    import re
    # Inside JSON too: the backup keeps 1.0, the restored jsonb prints 1 (cpl_ringkasan, O4 run 2026-11-18).
    import json
    def seragam(v):
        if re.fullmatch(r"-?\d+(\.\d+)?", v):
            return f"{Decimal(v).normalize():f}"
        if v[:1] in "{[":
            try:
                return json.dumps(json.loads(v, parse_int=float, parse_float=float), sort_keys=True)
            except ValueError:
                return v
        return v
    baris = lambda xs: {tuple((k, seragam(v)) for k, v in r) for r in xs}
    beda = []
    for t, rows in h["tabel"].items():
        f = (ROOT / "cadangan" / f"{t}.csv").read_bytes()
        kolom = set(sa._kolom_csv(f))
        if baris({tuple(x for x in sa._row_key(r) if x[0] in kolom) for r in rows}) != baris(sa._row_keys_from_csv(f)):
            beda.append(t)
    assert beda == []
