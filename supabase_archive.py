"""Cadangan rutin, arsip tahunan, dan pemangkasan data lama Supabase.

    python supabase_archive.py backup                          # semua tabel -> cadangan/<tabel>.csv
    python supabase_archive.py archive                         # semua tabel -> arsip/<tanggal>/ + manifest + rencana hapus
    python supabase_archive.py prune arsip/2035-09-01          # tampilkan rencana hapus saja
    python supabase_archive.py prune arsip/2035-09-01 --hapus  # benar-benar menghapus dari Supabase
    python supabase_archive.py send cadangan                   # folder -> satu zip -> Drive prodi (repo publik)
    python supabase_archive.py pulihkan cadangan               # cadangan -> pulih/<nama>-<tanggal>/ (SQL untuk proyek baru)
    python supabase_archive.py backup --folder pulih/uji-balik # cadangkan ke folder lain (gladi pemulihan)
    python supabase_archive.py bandingkan cadangan pulih/uji-balik  # dua cadangan identik?

Daftar tabel dan aturan pemangkasan: config.yaml bagian supabase. Kunci:
env SUPABASE_URL dan SUPABASE_SERVICE_KEY (GitHub Secrets), atau rahasia.env
di folder ini (komputer build). Jadwal: .github/workflows/pemeliharaan.yml
(backup harian di repo prodi sejak 2026-11-20; templat prodi lain bulanan; archive tiap
1 September). prune selalu dijalankan pemilik.

Pengaman prune --hapus: arsip harus utuh (checksum cocok dengan manifest),
umurnya <= prune_max_archive_age_days, dan setiap baris yang akan dihapus
harus terbukti ada di arsip itu. Berkas di Google Drive tidak pernah disentuh.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from cpl.config import load_config

ROOT = Path(__file__).resolve().parent
PAGE = 1000          # Supabase/PostgREST returns at most 1000 rows per request
DELETE_BATCH = 100
# Satu sel bisa lebih dari batas bawaan csv (128 KB): cpl_ringkasan.ringkasan memuat JSON ringkasan
# CPL (423 KB di cadangan 2026-11-14). 2**31 - 1 = batas terbesar yang diterima di Windows (C long).
csv.field_size_limit(2**31 - 1)
SECRET_KEYS = ("SUPABASE_URL", "SUPABASE_SERVICE_KEY")


class Rest:
    """Minimal PostgREST client with the service key (bypasses RLS)."""

    def __init__(self, url, key):
        self.base = url.rstrip("/")
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    def _get(self, table, params, start, end):
        r = requests.get(f"{self.base}/rest/v1/{table}", params=params, timeout=60,
                         headers={**self.headers, "Range": f"{start}-{end}", "Prefer": "count=exact"})
        if r.status_code >= 300:
            raise RuntimeError(f"{table}: HTTP {r.status_code} {r.text[:200]}")
        total = r.headers.get("Content-Range", "*/*").rsplit("/", 1)[-1]
        return r.json(), (int(total) if total.isdigit() else None)

    def rows(self, table, order):
        """All rows, PAGE at a time, ordered; checks the count and that no row repeats."""
        out, start, total = [], 0, None
        while True:
            page, total = self._get(table, {"select": "*", "order": order}, start, start + PAGE - 1)
            out.extend(page)
            if len(page) < PAGE:
                break
            start += PAGE
        if total is not None and len(out) != total:
            raise RuntimeError(f"{table}: {len(out)} baris terambil, Supabase melaporkan {total}")
        if len({json.dumps(r, sort_keys=True) for r in out}) != len(out):
            raise RuntimeError(f"{table}: ada baris kembar; kolom urut '{order}' tidak unik, perbaiki di config.yaml")
        return out

    def delete_in(self, table, column, values):
        """Delete rows whose column is in values, in batches. Returns rows deleted."""
        deleted = 0
        values = list(values)
        for i in range(0, len(values), DELETE_BATCH):
            batch = values[i:i + DELETE_BATCH]
            quoted = ",".join('"' + str(v).replace('"', '\\"') + '"' for v in batch)
            r = requests.delete(f"{self.base}/rest/v1/{table}", params={column: f"in.({quoted})"},
                                headers={**self.headers, "Prefer": "return=representation"}, timeout=60)
            if r.status_code >= 300:
                raise RuntimeError(f"{table}: hapus gagal HTTP {r.status_code} {r.text[:200]}")
            deleted += len(r.json())
        return deleted


def read_secrets(root=ROOT):
    """SUPABASE_URL / SUPABASE_SERVICE_KEY from the environment, else from rahasia.env."""
    env = {k: os.environ.get(k, "").strip() for k in SECRET_KEYS}
    path = root / "rahasia.env"
    if not all(env.values()) and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() in env and not env[k.strip()]:
                    env[k.strip()] = v.strip().strip('"').strip("'")
    missing = [k for k, v in env.items() if not v or "xxxx" in v.lower()]
    if missing:
        raise SystemExit(f"Kunci belum diisi: {', '.join(missing)} (env atau rahasia.env)")
    return env


def validate_config(cfg):
    """Errors in the supabase section, each naming its key. Empty = valid."""
    err = []
    sb = cfg.get("supabase") or {}
    tables = sb.get("tables")
    if not isinstance(tables, dict) or not tables:
        return ["supabase.tables: harus pemetaan tabel -> kolom urut"]
    for t, order in tables.items():
        if not isinstance(order, str) or not order.strip():
            err.append(f"supabase.tables.{t}: kolom urut wajib diisi")
    for t, rule in (sb.get("retention") or {}).items():
        key = f"supabase.retention.{t}"
        if t not in tables:
            err.append(f"{key}: tabel tidak ada di supabase.tables")
        years = (rule or {}).get("years")
        if not isinstance(years, int) or isinstance(years, bool) or years < 1:
            err.append(f"{key}.years: harus bilangan bulat >= 1, didapat {years!r}")
        yf = (rule or {}).get("year_from") or {}
        for k in ("table", "key", "ref_key", "column"):
            if not yf.get(k):
                err.append(f"{key}.year_from.{k}: wajib diisi")
        if yf.get("table") and yf["table"] not in tables:
            err.append(f"{key}.year_from.table: {yf['table']} tidak ada di supabase.tables")
        for f in ("only_if_any", "only_if_empty"):
            v = (rule or {}).get(f)
            if v is not None and not (isinstance(v, list) and v and all(isinstance(c, str) and c for c in v)):
                err.append(f"{key}.{f}: harus daftar nama kolom yang tidak kosong, didapat {v!r}")
    age = sb.get("prune_max_archive_age_days")
    if not isinstance(age, int) or isinstance(age, bool) or not 1 <= age <= 90:
        err.append(f"supabase.prune_max_archive_age_days: harus bilangan bulat 1-90, didapat {age!r}")
    return err


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)


def to_csv(rows):
    """Rows (list of dict) -> UTF-8 CSV bytes; columns in first-seen order."""
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for r in rows:
        w.writerow([_cell(r.get(c)) for c in cols])
    return buf.getvalue().encode("utf-8")


def _row_keys_from_csv(data):
    """Set of rows from CSV bytes, each as a sorted tuple of (column, text)."""
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    return {tuple(sorted(r.items())) for r in reader}


def _row_key(row):
    return tuple(sorted((k, _cell(v)) for k, v in row.items()))


def fetch_all(client, cfg):
    return {t: client.rows(t, order) for t, order in cfg["supabase"]["tables"].items()}


def _year(v):
    """Year of a cell: an integer year (karya.tahun) or a date/timestamp text such as
    2026-11-16T08:00:00+00:00 (patch 78 dikirim, 2026-11-16). None when unknown."""
    s = str(v if v is not None else "").strip()
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    m = re.match(r"(\d{4})-\d{2}-\d{2}", s)
    return int(m.group(1)) if m else None


def _filled(v):
    return v is not None and str(v).strip() != ""


def _row_selected(rule, row):
    """Optional row filter of a retention rule (2026-11-16): only_if_any = at least one of the
    columns filled (survey answers with identity), only_if_empty = all of them empty (guest
    meeting attendees: dosen_id empty)."""
    if rule.get("only_if_any") and not any(_filled(row.get(c)) for c in rule["only_if_any"]):
        return False
    if rule.get("only_if_empty") and any(_filled(row.get(c)) for c in rule["only_if_empty"]):
        return False
    return True


def retention_plan(cfg, data, today):
    """Per table: rows older than its retention, grouped by the key column used for deleting."""
    plan = {}
    for table, rule in (cfg["supabase"].get("retention") or {}).items():
        yf = rule["year_from"]
        year_of = {}
        for ref in data[yf["table"]]:
            y = _year(ref.get(yf["column"])) if yf["ref_key"] in ref else None
            if y is not None:
                year_of[str(ref[yf["ref_key"]])] = y   # unknown year: never deleted
        cutoff = today.year - rule["years"]
        old = [r for r in data[table] if year_of.get(str(r.get(yf["key"])), cutoff) < cutoff
               and _row_selected(rule, r)]
        plan[table] = {"cutoff_year": cutoff, "years": rule["years"], "key": yf["key"],
                       "rows": old, "key_values": sorted({str(r[yf["key"]]) for r in old})}
    return plan


def backup(client, cfg, root=ROOT, folder=None):
    """Monthly: every configured table -> cadangan/<table>.csv (or folder). Returns {table: rows}."""
    out = Path(folder) if folder else root / "cadangan"
    out.mkdir(parents=True, exist_ok=True)
    counts, failed = {}, []
    for t, order in cfg["supabase"]["tables"].items():
        try:
            rows = client.rows(t, order)
        except Exception as e:
            failed.append(f"{t}: {e}")
            continue
        (out / f"{t}.csv").write_bytes(to_csv(rows))
        counts[t] = len(rows)
        print(f"  {t}: {len(rows)} baris")
    if failed:
        raise RuntimeError("cadangan gagal untuk: " + "; ".join(failed))
    return counts


def archive(client, cfg, root=ROOT, today=None):
    """Yearly: every table -> arsip/<date>/ with manifest.json and the deletion plan (no deletion)."""
    today = today or date.today()
    folder = root / "arsip" / today.isoformat()
    if folder.exists():
        raise RuntimeError(f"{folder} sudah ada; arsip tidak ditimpa")
    data = fetch_all(client, cfg)
    folder.mkdir(parents=True)
    manifest = {"created": today.isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "tables": {}, "retention": {}}
    for t, rows in data.items():
        blob = to_csv(rows)
        (folder / f"{t}.csv").write_bytes(blob)
        manifest["tables"][t] = {"file": f"{t}.csv", "rows": len(rows),
                                 "sha256": hashlib.sha256(blob).hexdigest()}
    plan = retention_plan(cfg, data, today)
    if plan:
        (folder / "rencana_hapus").mkdir()
    for t, p in plan.items():
        (folder / "rencana_hapus" / f"{t}.csv").write_bytes(to_csv(p["rows"]))
        manifest["retention"][t] = {k: p[k] for k in ("cutoff_year", "years", "key")} | \
            {"rows": len(p["rows"]), "key_count": len(p["key_values"])}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    for t, m in manifest["tables"].items():
        print(f"  {t}: {m['rows']} baris")
    for t, m in manifest["retention"].items():
        print(f"  rencana hapus {t}: {m['rows']} baris (tahun < {m['cutoff_year']})")
    print(f"  arsip: {folder}")
    return folder


def verify_archive(folder):
    """Manifest present and every CSV matches its checksum. Returns the manifest."""
    folder = Path(folder)
    mpath = folder / "manifest.json"
    if not mpath.is_file():
        raise RuntimeError(f"manifest.json tidak ada di {folder}")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    for t, m in manifest["tables"].items():
        f = folder / m["file"]
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != m["sha256"]:
            raise RuntimeError(f"arsip {t} tidak utuh (berkas hilang atau checksum berbeda): {f}")
    return manifest


def prune(client, cfg, folder, execute=False, today=None):
    """Show (default) or carry out the deletion plan, against live data, guarded by the archive."""
    today = today or date.today()
    folder = Path(folder)
    manifest = verify_archive(folder)
    age = (today - date.fromisoformat(manifest["created"])).days
    max_age = cfg["supabase"]["prune_max_archive_age_days"]
    if age > max_age:
        msg = f"arsip berumur {age} hari (> {max_age}); jalankan archive baru dulu"
        if execute:
            raise RuntimeError(msg)
        print(f"  PERINGATAN: {msg}")

    retention = cfg["supabase"].get("retention") or {}
    needed = set(retention) | {r["year_from"]["table"] for r in retention.values()}
    live = {t: client.rows(t, cfg["supabase"]["tables"][t]) for t in needed}
    plan = retention_plan(cfg, live, today)

    for t, p in plan.items():
        archived = _row_keys_from_csv((folder / f"{t}.csv").read_bytes())
        missing = [r for r in p["rows"] if _row_key(r) not in archived]
        if missing:
            raise RuntimeError(f"{t}: {len(missing)} baris yang akan dihapus belum ada di arsip {folder.name}; "
                               "jalankan archive baru dulu")
        print(f"  {t}: {len(p['rows'])} baris dari {len(p['key_values'])} {p['key']} "
              f"(tahun < {p['cutoff_year']}), semuanya ada di arsip")

    if not execute:
        print("  MODE PERIKSA: tidak ada yang dihapus. Tambahkan --hapus untuk menghapus.")
        return {t: 0 for t in plan}

    done = {}
    for t, p in plan.items():
        if not p["key_values"]:
            done[t] = 0
            continue
        n = client.delete_in(t, p["key"], p["key_values"])
        left = [r for r in client.rows(t, cfg["supabase"]["tables"][t])
                if str(r.get(p["key"])) in set(p["key_values"])]
        if left:
            raise RuntimeError(f"{t}: {len(left)} baris masih ada setelah dihapus")
        done[t] = n
        print(f"  {t}: {n} baris dihapus")
    log = {"date": today.isoformat(), "archive": folder.name,
           "deleted": {t: {"rows": done[t], "key": plan[t]["key"], "key_values": plan[t]["key_values"],
                           "cutoff_year": plan[t]["cutoff_year"]} for t in plan}}
    (folder / f"hapus_{today.isoformat()}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    return done


def upload_url(root=ROOT):
    """Web App address from site/config.js: the one place it is kept."""
    m = re.search(r"window\.UPLOAD_URL *= *'([^']*)'", (root / "site" / "config.js").read_text(encoding="utf-8"))
    return m.group(1).strip() if m else ""


def zip_folder(folder):
    """Every file under folder as zip bytes, paths relative to it."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(p for p in folder.rglob("*") if p.is_file()):
            z.write(f, f.relative_to(folder).as_posix())
    return out.getvalue()


def send(folder, root=ROOT, post=requests.post):
    """Repositories that are public keep no data: the zip goes to the Drive folder
    behind Apps Script kind 'cadangan' (apps-script/README.md)."""
    url = upload_url(root)
    token = os.environ.get("CADANGAN_TOKEN", "").strip()
    if not url:
        raise RuntimeError("window.UPLOAD_URL di site/config.js kosong; pasang Apps Script dulu")
    if not token:
        raise RuntimeError("env CADANGAN_TOKEN kosong (GitHub Secret CADANGAN_TOKEN)")
    if not any(p.is_file() for p in folder.rglob("*")):
        raise RuntimeError(f"folder {folder} kosong")
    data = zip_folder(folder)
    r = post(url, json={"kind": "cadangan", "cadangan_token": token, "name": f"{folder.name}.zip",
                        "data": base64.b64encode(data).decode("ascii")}, timeout=120)
    r.raise_for_status()
    hasil = r.json()
    if not hasil.get("ok"):
        raise RuntimeError(f"Apps Script menolak: {hasil.get('error')}")
    print(f"Terkirim ke Drive: {hasil.get('name')} ({len(data)} byte)")


# ---------------------------------------------------------------------------
# Pemulihan (pemilik 2026-11-11): cadangan CSV -> berkas SQL untuk SQL Editor
# proyek Supabase baru. Tidak memakai kunci; tidak menyentuh Supabase sendiri.
#
# Mengapa SQL, bukan REST: id identitas ('generated always') hanya bisa
# dipertahankan dengan OVERRIDING SYSTEM VALUE, trigger yang menurunkan atau
# menjaga kolom harus mati selama pemulihan, dan tipe kolom (jsonb, larik)
# dibaca dari katalog tujuan, bukan ditebak dari CSV.
# Sel kosong di CSV = NULL; untuk kolom teks NOT NULL dipakai '' (backup()
# menulis keduanya sebagai sel kosong).

def urut_patch(paths):
    """Patch files in run order: by the leading number, not alphabetically (2026-11-17: 100-*.sql sorted
    before 11-*.sql and ran before the tables it alters existed)."""
    return sorted(paths, key=lambda p: (int(re.match(r"\d+", Path(p).name).group()), Path(p).name))


def full_schema(root=ROOT):
    """Clean install SQL: from supabase/NN-*.sql via tools/make_full_schema.mjs (cv-data),
    or supabase/instal-lengkap.sql where the patches are not kept (template repo)."""
    patches = urut_patch((root / "supabase").glob("[0-9][0-9]*.sql"))
    if not patches:
        f = root / "supabase" / "instal-lengkap.sql"
        if not f.is_file():
            raise RuntimeError("tidak ada patch supabase/NN-*.sql maupun supabase/instal-lengkap.sql")
        return f.read_bytes()
    tools = root / "tools"
    if not (tools / "node_modules").is_dir():
        raise RuntimeError("Jalankan dulu: npm install --prefix tools")
    import hashlib
    import subprocess
    import tempfile
    gabung = b"\n".join(p.read_bytes() for p in patches)
    # Cache (2026-11-17: tiap putaran pytest membangun skema ini beberapa kali, ±20 detik sekali): kunci = isi semua
    # patch + kedua alat pembangun, jadi skema dibangun ulang hanya bila salah satunya berubah. Hasilnya identik.
    kunci = hashlib.sha256(gabung + (tools / "make_full_schema.mjs").read_bytes()
                           + (tools / "supabase-tiruan.mjs").read_bytes()).hexdigest()[:24]
    cache = Path(tempfile.gettempdir()) / "cv-data-skema" / f"{kunci}.sql"
    if cache.is_file():
        return cache.read_bytes()
    with tempfile.TemporaryDirectory() as t:
        masuk, keluar = Path(t) / "patch.sql", Path(t) / "lengkap.sql"
        masuk.write_bytes(gabung)
        r = subprocess.run(["node", str(tools / "make_full_schema.mjs"), str(masuk), str(keluar)],
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            raise RuntimeError(f"skema gabungan gagal:\n{r.stderr[-2000:]}")
        print(f"  {r.stdout.strip()}")
        hasil = keluar.read_bytes()
    try:
        cache.parent.mkdir(exist_ok=True)
        cache.with_suffix(".tmp").write_bytes(hasil)
        cache.with_suffix(".tmp").replace(cache)
    except OSError:
        pass   # cache gagal ditulis: tetap jalan tanpa cache
    return hasil


def read_backup(folder, tables):
    """{table: (columns, rows)} for the configured tables; rows are lists of str or None."""
    folder = Path(folder)
    if not folder.is_dir():
        raise RuntimeError(f"folder cadangan tidak ada: {folder}")
    if (folder / "manifest.json").is_file():
        verify_archive(folder)
    missing = [t for t in tables if not (folder / f"{t}.csv").is_file()]
    if missing:
        raise RuntimeError(f"cadangan tidak lengkap, CSV tidak ada: {', '.join(missing)}")
    out = {}
    for t in tables:
        # Dibaca sebagai bytes: read_text() mengubah CRLF di DALAM isian menjadi LF, sehingga teks yang ditempel
        # dari Windows (mis. lkps_vmts, 2026-11-21) tidak pulih persis.
        rows = list(csv.reader(io.StringIO((folder / f"{t}.csv").read_bytes().decode("utf-8"), newline="")))
        cols = rows[0] if rows else []
        out[t] = (cols, [[None if c == "" else c for c in r] for r in rows[1:]])
    return out


RESTORE_SQL = """-- =====================================================================
--  Pemulihan data dari cadangan {sumber} (dibuat {dibuat} oleh supabase_archive.py pulihkan).
--  Jalankan di SQL Editor proyek tujuan SETELAH 1-skema.sql. Satu transaksi:
--  bila ada yang gagal, tidak ada yang berubah. Tabel di bawah DIKOSONGKAN dulu.
--  {n_tabel} tabel, {n_baris} baris. Memuat data pribadi: jangan dibagikan.
-- =====================================================================
create or replace function pg_temp.cv_json(x text) returns jsonb language plpgsql as $f$
begin return x::jsonb; exception when others then return to_jsonb(x); end $f$;

do $blok$
declare
  d jsonb := {tag}{data}{tag}::jsonb;
  tabel text[];
  rel regclass[];
  fks jsonb;
  fk record;
  t text;
  r regclass;
  kolom text;
  hilang text;
  isi jsonb;
  n bigint;
  s record;
  kosong boolean;   -- di langkah 2: true = tabel di luar cadangan itu BERISI data
begin
  select array_agg(k order by k) into tabel from jsonb_object_keys(d) k;
  select string_agg(x, ', ') into hilang from unnest(tabel) x where to_regclass('public.' || quote_ident(x)) is null;
  if hilang is not null then
    raise exception 'Tabel tidak ada di proyek tujuan: %. Jalankan 1-skema.sql dulu.', hilang;
  end if;
  select array_agg(('public.' || quote_ident(x))::regclass) into rel from unnest(tabel) x;
  -- Kolom cadangan yang tidak ada di tujuan = data hilang: berhenti.
  select string_agg(x || '.' || c, ', ') into hilang
    from unnest(tabel) x, jsonb_array_elements_text(d -> x -> 'kolom') c
    where not exists (select 1 from pg_attribute a where a.attrelid = ('public.' || quote_ident(x))::regclass
                      and a.attname = c and a.attnum > 0 and not a.attisdropped);
  if hilang is not null then
    raise exception 'Kolom cadangan tidak ada di proyek tujuan (datanya akan hilang): %', hilang;
  end if;

  -- 1. Lepas rujukan antartabel; dipasang lagi di langkah 5 (sekaligus memeriksa keutuhannya).
  select coalesce(jsonb_agg(jsonb_build_object('tbl', c.conrelid::regclass::text, 'nama', c.conname,
           'def', pg_get_constraintdef(c.oid))), '[]') into fks
    from pg_constraint c where c.contype = 'f' and c.conrelid = any(rel) and c.confrelid = any(rel);
  for fk in select * from jsonb_to_recordset(fks) as x(tbl text, nama text, def text) loop
    execute format('alter table %s drop constraint %I', fk.tbl, fk.nama);
  end loop;

  -- 2. Kosongkan; matikan trigger buatan (penurunan kolom, penjaga) selama pemulihan.
  --    Tabel di luar cadangan (patch yang lebih baru dari cadangan) yang merujuk tabel ini boleh
  --    ikut dikosongkan (CASCADE) hanya bila memang kosong; bila berisi, berhenti agar tidak terhapus.
  hilang := null;
  for r in select distinct c.conrelid::regclass from pg_constraint c
           where c.contype = 'f' and c.confrelid = any(rel) and not (c.conrelid = any(rel)) loop
    execute format('select exists (select 1 from %s)', r) into kosong;
    if kosong then hilang := concat_ws(', ', hilang, r::text); end if;
  end loop;
  if hilang is not null then
    raise exception 'Tabel di luar cadangan berisi data dan merujuk tabel yang dipulihkan: %. Pulihkan ke proyek baru.', hilang;
  end if;
  execute 'truncate table ' || array_to_string(rel::text[], ', ') || ' cascade';
  foreach r in array rel loop
    execute format('alter table %s disable trigger user', r);
  end loop;

  -- 3. Isi. Tipe dari katalog: jsonb/json/larik diurai, teks NOT NULL kosong = ''.
  foreach t in array tabel loop
    r := ('public.' || quote_ident(t))::regclass;
    select string_agg(quote_ident(a.attname), ', ' order by a.attnum) into kolom
      from pg_attribute a
      where a.attrelid = r and a.attnum > 0 and not a.attisdropped and a.attgenerated = ''
        and a.attname in (select jsonb_array_elements_text(d -> t -> 'kolom'));
    select coalesce(jsonb_agg((
        select jsonb_object_agg(k.c,
          case when b.v is null or b.v = 'null'::jsonb then
                 case when a.attnotnull and a.atttypid in ('text'::regtype, 'varchar'::regtype)
                      then to_jsonb(''::text) else 'null'::jsonb end
               when a.atttypid in ('json'::regtype, 'jsonb'::regtype) or y.typcategory = 'A'
                 then pg_temp.cv_json(b.v #>> '{{}}')
               else b.v end)
        from jsonb_array_elements_text(d -> t -> 'kolom') with ordinality k(c, i)
        join pg_attribute a on a.attrelid = r and a.attname = k.c and not a.attisdropped and a.attgenerated = ''
        join pg_type y on y.oid = a.atttypid
        cross join lateral (select baris -> (k.i::int - 1) v) b)), '[]')
      into isi from jsonb_array_elements(d -> t -> 'baris') baris;
    if kolom is not null and jsonb_array_length(isi) > 0 then
      execute format('insert into %s (%s) overriding system value select %s from jsonb_populate_recordset(null::%s, $1)',
                     r, kolom, kolom, r) using isi;
      get diagnostics n = row_count;
    else
      n := 0;
    end if;
    if n <> jsonb_array_length(d -> t -> 'baris') then
      raise exception '%: % baris masuk, cadangan berisi %', t, n, jsonb_array_length(d -> t -> 'baris');
    end if;
  end loop;

  -- 4. Nyalakan trigger lagi.
  foreach r in array rel loop
    execute format('alter table %s enable trigger user', r);
  end loop;

  -- 5. Pasang rujukan antartabel lagi; gagal bila ada rujukan yatim.
  for fk in select * from jsonb_to_recordset(fks) as x(tbl text, nama text, def text) loop
    execute format('alter table %s add constraint %I %s', fk.tbl, fk.nama, fk.def);
  end loop;

  -- 6. Penghitung id lanjut dari nilai terbesar.
  for s in select a.attrelid::regclass tbl, a.attname kol, pg_get_serial_sequence(a.attrelid::regclass::text, a.attname) seq
           from pg_attribute a where a.attrelid = any(rel) and a.attnum > 0 and not a.attisdropped
             and pg_get_serial_sequence(a.attrelid::regclass::text, a.attname) is not null loop
    execute format('select setval(%L, coalesce((select max(%I) from %s), 1), (select max(%I) from %s) is not null)',
                   s.seq, s.kol, s.tbl, s.kol, s.tbl);
  end loop;
  raise notice 'Pemulihan selesai: % tabel.', array_length(tabel, 1);
end $blok$;
"""


def restore_sql(data, sumber="cadangan", dibuat=None):
    """Data SQL (one DO block, one transaction) from read_backup() output."""
    blob = json.dumps({t: {"kolom": c, "baris": r} for t, (c, r) in data.items()},
                      ensure_ascii=False, separators=(",", ":"))
    tag = "$cvdata$"
    if tag in blob:
        raise RuntimeError("isi cadangan memuat penanda $cvdata$; ganti penanda di restore_sql")
    return RESTORE_SQL.format(sumber=sumber, dibuat=dibuat or date.today().isoformat(), tag=tag, data=blob,
                              n_tabel=len(data), n_baris=sum(len(r) for _, r in data.values()))


def check_sql(data):
    """One query: rows per table in the backup vs in the database; must all say 'cocok'."""
    q = ",\n  ".join(f"('{t}', {len(r)}, (select count(*) from public.{t}))" for t, (_, r) in data.items())
    return ("-- Periksa hasil pemulihan: semua baris harus 'cocok'. Yang tidak cocok tampil paling atas.\n"
            f"select tabel, cadangan, pulih, case when cadangan = pulih then 'cocok' else 'BEDA' end as hasil\n"
            f"from (values\n  {q}\n) v(tabel, cadangan, pulih)\norder by (cadangan = pulih), tabel;\n")


LANGKAH = """# Uji pemulihan cadangan — {nama}

Dibuat {dibuat} dari `{sumber}` ({n_tabel} tabel, {n_baris} baris). Folder ini memuat
**data pribadi** (nama, email, NIM): jangan dibagikan, jangan di-commit (`/pulih/` ada di .gitignore).
Hapus folder ini setelah selesai.

## Gladi (proyek uji, data asli tidak disentuh)
1. Supabase > New project, nama mis. `cv-uji-pulih`, region sama. Bila Supabase menolak karena batas
   proyek paket gratis, jeda (pause) dulu proyek lain yang tidak dipakai.
2. Proyek uji > SQL Editor > jalankan isi `1-skema.sql`, lalu `2-data.sql`, lalu `3-periksa.sql`.
   Semua baris hasil `3-periksa.sql` harus `cocok`.
3. Bukti terkuat (bulat-balik): cadangkan proyek uji ke folder lain lalu bandingkan dengan sumbernya.
   Di PowerShell, folder cv-data, isi kunci proyek UJI (Settings > API) untuk jendela ini saja:
       $env:SUPABASE_URL = "https://<proyek-uji>.supabase.co"
       $env:SUPABASE_SERVICE_KEY = "<service_role proyek uji>"
       python supabase_archive.py backup --folder pulih/uji-balik
       python supabase_archive.py bandingkan {sumber} pulih/uji-balik
   Pastikan baris `proyek:` yang tercetak menyebut alamat proyek UJI (bukan proyek utama); tanpa kunci di
   jendela ini perintah backup --folder menolak berjalan.
   Hasil yang diharapkan: semua tabel `identik`. Tutup jendela PowerShell sesudahnya.
4. Hapus proyek uji (Settings > General > Delete project) dan folder `pulih/`.

## Pemulihan sungguhan (proyek utama hilang atau rusak)
Langkah 1-2 di atas pada proyek baru, lalu arahkan semuanya ke proyek baru:
- `site/config.js`: `SB_URL` dan `SB_KEY` (kunci publishable proyek baru);
- GitHub > Settings > Secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`;
- Apps Script > Project Settings > Script Properties: `SUPABASE_URL`, `SUPABASE_KEY`, lalu deploy versi baru;
- Supabase > Authentication > URL Configuration: Site URL dan Redirect URL alamat situs;
- `rahasia.env` di komputer build.
Akun login tidak ikut dipulihkan: dosen cukup masuk lagi dengan email yang sama (tabel `dosen`).
Berkas bukti ada di Google Drive prodi, bukan di Supabase, jadi tidak perlu dipulihkan.
"""


def pulihkan(cfg, folder, root=ROOT, today=None):
    """Write pulih/<folder>-<date>/ with 1-skema.sql, 2-data.sql, 3-periksa.sql, LANGKAH.md."""
    today = today or date.today()
    folder = Path(folder)
    data = read_backup(folder, list(cfg["supabase"]["tables"]))
    lain = sorted(p.stem for p in folder.glob("*.csv") if p.stem not in data)
    out = root / "pulih" / f"{folder.name}-{today.isoformat()}"
    if out.exists():
        raise RuntimeError(f"{out} sudah ada; tidak ditimpa")
    skema = full_schema(root)
    out.mkdir(parents=True)
    n = sum(len(r) for _, r in data.values())
    (out / "1-skema.sql").write_bytes(skema)
    (out / "2-data.sql").write_text(restore_sql(data, folder.name, today.isoformat()), encoding="utf-8")
    (out / "3-periksa.sql").write_text(check_sql(data), encoding="utf-8")
    (out / "LANGKAH.md").write_text(LANGKAH.format(nama=out.name, dibuat=today.isoformat(), sumber=folder.name,
                                                   n_tabel=len(data), n_baris=n), encoding="utf-8")
    print(f"  {len(data)} tabel, {n} baris -> {out}")
    if lain:
        print(f"  dilewati (tidak ada di config.yaml supabase.tables): {', '.join(lain)}")
    return out


def _baris_kolom(data, kolom):
    """CSV rows as sorted (column, text) tuples, restricted to `kolom`."""
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    return {tuple(sorted((k, v) for k, v in r.items() if k in kolom)) for r in reader}


def _kolom_csv(data):
    return next(csv.reader(io.StringIO(data.decode("utf-8"))), [])


def bandingkan(a, b):
    """Compare two backup folders row by row (order-free), on the columns of `a`.
    A column of `a` missing in `b` is lost data (differs); a column only in `b` comes from a
    newer schema (e.g. a backup older than a patch) and is only reported.
    Returns the number of tables that differ."""
    a, b = Path(a), Path(b)
    beda = 0
    for f in sorted(a.glob("*.csv")):
        g = b / f.name
        if not g.is_file():
            print(f"  {f.stem}: TIDAK ADA di {b}")
            beda += 1
            continue
        fa, fb = f.read_bytes(), g.read_bytes()
        ka, kb = _kolom_csv(fa), _kolom_csv(fb)
        # Tabel tanpa baris ditulis tanpa kepala kolom (to_csv([])): bukan kolom hilang.
        hilang = [k for k in ka if k not in kb] if kb else []
        tambah = [k for k in kb if k not in ka]
        x, y = _baris_kolom(fa, set(ka)), _baris_kolom(fb, set(ka))
        catatan = f"; kolom baru di {b.name} tidak dibandingkan: {', '.join(tambah)}" if tambah else ""
        if hilang:
            beda += 1
            print(f"  {f.stem}: BEDA — kolom tidak ada di {b.name}: {', '.join(hilang)}")
        elif x == y:
            print(f"  {f.stem}: identik ({len(x)} baris){catatan}")
        else:
            beda += 1
            print(f"  {f.stem}: BEDA — {len(x - y)} baris hanya di {a.name}, {len(y - x)} baris hanya di {b.name}{catatan}")
    for g in sorted(b.glob("*.csv")):
        if not (a / g.name).is_file():
            print(f"  {g.stem}: hanya ada di {b}")
            beda += 1
    print(f"  {'SEMUA IDENTIK' if not beda else f'{beda} tabel berbeda'}")
    return beda


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    ba = sub.add_parser("backup", help="semua tabel -> cadangan/<tabel>.csv")
    ba.add_argument("--folder", type=Path, help="folder lain selain cadangan/, mis. pulih/uji-balik (gladi pemulihan)")
    pu = sub.add_parser("pulihkan", help="cadangan -> pulih/<nama>-<tanggal>/ berisi SQL untuk proyek Supabase baru")
    pu.add_argument("folder", type=Path, nargs="?", default=Path("cadangan"), help="folder cadangan atau arsip (bawaan: cadangan)")
    bd = sub.add_parser("bandingkan", help="bandingkan dua folder cadangan baris demi baris")
    bd.add_argument("a", type=Path)
    bd.add_argument("b", type=Path)
    sub.add_parser("archive", help="semua tabel -> arsip/<tanggal>/ + manifest + rencana hapus")
    pr = sub.add_parser("prune", help="tampilkan atau jalankan rencana hapus")
    pr.add_argument("folder", type=Path, help="folder arsip, mis. arsip/2035-09-01")
    pr.add_argument("--hapus", action="store_true", help="benar-benar menghapus dari Supabase")
    se = sub.add_parser("send", help="folder -> satu zip -> Google Drive prodi lewat Apps Script")
    se.add_argument("folder", type=Path, help="mis. cadangan atau arsip")
    a = p.parse_args(argv)

    if a.cmd == "send":   # needs no Supabase key
        try:
            send(a.folder if a.folder.is_absolute() else ROOT / a.folder)
        except (RuntimeError, requests.RequestException, ValueError) as e:
            print(f"GAGAL: {e}", file=sys.stderr)
            return 1
        return 0

    absolut = lambda f: f if f.is_absolute() else ROOT / f
    if a.cmd == "bandingkan":   # needs neither config nor key
        print(f"supabase_archive bandingkan: {a.a} dengan {a.b}")
        return 1 if bandingkan(absolut(a.a), absolut(a.b)) else 0

    cfg = load_config(ROOT / "config.yaml")
    errors = validate_config(cfg)
    if errors:
        print("Config tidak sah:", *[f"  - {e}" for e in errors], sep="\n", file=sys.stderr)
        return 2
    if a.cmd == "pulihkan":     # needs no Supabase key
        print(f"supabase_archive pulihkan: {a.folder}")
        try:
            pulihkan(cfg, absolut(a.folder))
        except RuntimeError as e:
            print(f"GAGAL: {e}", file=sys.stderr)
            return 1
        return 0
    # Gladi pemulihan (2026-11-12): backup --folder harus memakai kunci proyek UJI dari variabel lingkungan.
    # Tanpa itu read_secrets jatuh ke rahasia.env (proyek utama) dan "bandingkan" memberi bukti palsu.
    dari_env = all(os.environ.get(k, "").strip() for k in SECRET_KEYS)
    if a.cmd == "backup" and a.folder and not dari_env:
        print("GAGAL: backup --folder (gladi) memerlukan $env:SUPABASE_URL dan $env:SUPABASE_SERVICE_KEY proyek uji\n"
              "di jendela PowerShell ini; tanpa itu yang dicadangkan proyek utama dari rahasia.env.", file=sys.stderr)
        return 2
    secrets = read_secrets()
    client = Rest(secrets["SUPABASE_URL"], secrets["SUPABASE_SERVICE_KEY"])
    host = secrets["SUPABASE_URL"].split("//")[-1].split("/")[0]
    print(f"  proyek: {host} ({'variabel lingkungan' if dari_env else 'rahasia.env'})")
    print(f"supabase_archive {a.cmd}: {len(cfg['supabase']['tables'])} tabel "
          f"({', '.join(cfg['supabase']['tables'])})")
    try:
        if a.cmd == "backup":
            if a.folder:
                print(f"  ke folder {a.folder} (bukan cadangan/)")
            backup(client, cfg, folder=absolut(a.folder) if a.folder else None)
        elif a.cmd == "archive":
            archive(client, cfg)
        else:
            folder = a.folder if a.folder.is_absolute() else ROOT / a.folder
            prune(client, cfg, folder, execute=a.hapus)
    except RuntimeError as e:
        print(f"GAGAL: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
