"""Profil CPL per mahasiswa (owner 2026-11-14; cpl/student_record.py, cpl/radar.py). Synthetic data only."""
import json
from pathlib import Path

import pytest

from cpl.archive import build_report
from cpl.config import validate_config
from cpl.final_grades import prepare_final
from cpl.radar import build_records, write_student_radar
from tests.test_final_grades import ROOT, cfg, tulis  # noqa: F401 (fixture)

SKALA = [{"min": 80, "letter": "A", "point": 4.0}, {"min": 45, "letter": "C", "point": 2.0},
         {"min": 0, "letter": "E", "point": 0.0}]


@pytest.fixture()
def dua_semester(cfg, tmp_path):
    ref = Path(cfg["final_grades"]["reference_dir"])
    with open(ref / "ref_mata_kuliah.csv", "a", encoding="utf-8") as f:
        f.write("41999,Gambar Teknik,2,1,K21,wajib\n")            # no CPL in the map: grades list only
    (ref / "lkps_prestasi_mahasiswa.csv").write_text(
        "nim,nama_kegiatan,penyelenggara,tingkat,capaian,tahun,status\n"
        "999922001,Lomba Jembatan,KemDikti,nasional,Juara 2,2025,terverifikasi\n"
        "999922001,Lomba Draf,X,nasional,Juara 1,2025,draf\n", encoding="utf-8")
    nilai = Path(cfg["paths"]["final_grades_dir"])
    tulis(nilai / "2025_ganjil", "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tertentu-CV1-2025.csv",
          [("999922001", [1, 1, 1, 1], 85.0), ("999922002", [1, 1, 1, 1], 60.0)])
    tulis(nilai / "2025_ganjil", "Nilai_Detail_Kelas_2026_Gambar Teknik-CV1-2025.csv",
          [("999922001", [1, 1, 1, 1], 30.0)])
    tulis(nilai / "2025_genap", "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2025.csv",
          [("999922001", [1, 1, 1, 1], 50.0), ("999922002", [1, 1, 1, 1], 70.0)])
    wali = tmp_path / "perwalian.csv"
    wali.write_text("nim;email_wali;nama_wali\n999922001;Wali.Satu@kampus.id;Dosen Satu\n", encoding="utf-8")
    cfg["paths"]["advisors_csv"] = str(wali)
    cfg["student_record"].update(grade_scale=SKALA, pass_min_point=2.0, gpa_retake="best", gpa_include_failed=True)
    fin = prepare_final(cfg, ROOT)
    return cfg, fin, build_report([], cfg, fin)


def test_grades_gpa_and_cumulative_cpl_by_semester(dua_semester):
    cfg, fin, rep = dua_semester
    gt = next(f for f in fin["files"] if "Gambar" in f.path.name)
    assert not gt.ok and gt.grades_ok                          # no CPL map, still on the grade list
    from cpl.radar import radar_data
    d = radar_data(rep, cfg, record=build_records(cfg, ROOT, fin["files"]))
    m = next(x for x in d["mahasiswa"] if x["nim"] == "999922001")
    assert [s["term"] for s in m["smt"]] == ["2025/2026 Ganjil", "2025/2026 Genap"]
    g1, g2 = m["smt"]
    assert [x["kode"] for x in g1["mk"]] == ["41203", "41999"] and g1["mk"][1]["huruf"] == "E"
    assert g1["ips"] == pytest.approx(2.4) and g1["sks_lulus"] == 3      # (4*3 + 0*2) / 5; E not passed
    assert g2["ips"] == pytest.approx(2.0) and g2["ipk"] == pytest.approx(2.25) and g2["sks_lulus"] == 6
    # Cumulative CPL j: Ganjil from 41203 only, Genap from both courses (best attempt each).
    assert g1["kum"]["j"] == pytest.approx(85.0) and g2["kum"]["j"] < 85.0
    assert g2["cpl"]["j"] == pytest.approx(50.0)               # Genap courses only
    assert m["wali"] == {"email": "wali.satu@kampus.id", "nama": "Dosen Satu"}
    assert [p["capaian"] for p in m["prestasi"]] == ["Juara 2"]      # only verified rows
    # Rapor (pemilik 2026-11-14): lulus per MK, rata-rata IPS angkatan, MK kurikulum dengan CPL-nya.
    assert [x["lulus"] for x in g1["mk"]] == [True, False]
    assert d["rata_ips"][f"K21|{m['angkatan']}"][g1["term_order"]] == pytest.approx(2.2)   # (2.4 + C 2.0) / 2
    mk = {x["kode"]: x for x in d["kurikulum"]["K21"]["mk"]}
    assert "j" in mk["41203"]["cpl"] and mk["41999"]["cpl"] == [] and mk["41999"]["sifat"] == "wajib"


def test_page_per_advisor_holds_only_their_students(dua_semester, tmp_path):
    cfg, fin, rep = dua_semester
    out = tmp_path / "laporan"
    p = write_student_radar(rep, cfg, out, record=build_records(cfg, ROOT, fin["files"]))
    semua = p.read_text(encoding="utf-8")
    assert "999922001" in semua and "999922002" in semua and "Memuat NIM" in semua
    w = (out / "perwalian" / "wali.satu.html").read_text(encoding="utf-8")
    d = json.loads(w.split("const D = ")[1].split("\n")[0].rstrip(";"))
    assert [m["nim"] for m in d["mahasiswa"]] == ["999922001"] and d["judul"] == "Perwalian Dosen Satu"
    assert "Resmi kelulusan" in w and "Resmi per semester" in w and "Rapor semester" in w and "Orang Tua/Wali" in w and "Rencana pencapaian CPL" in w


def test_photo_is_shrunk_and_embedded(cfg, tmp_path):
    from PIL import Image
    from cpl.student_record import photo
    d = tmp_path / "foto"
    d.mkdir()
    Image.new("RGB", (1200, 1600), "white").save(d / "999922001.png")
    cfg["paths"]["photos_dir"] = str(d)
    uri = photo(cfg, "999922001")
    assert uri.startswith("data:image/jpeg;base64,") and len(uri) < 60_000
    assert photo(cfg, "999922009") == ""


def test_config_names_missing_gpa_rules_and_paths_inside_repo(cfg):
    base = [e for e in validate_config(cfg, ROOT) if not e.startswith(("paths.input_dir", "paths.output_dir"))]
    assert base == []                                        # config.yaml as shipped is valid
    cfg["student_record"].update(grade_scale=SKALA, pass_min_point=None, gpa_retake=None, gpa_include_failed=None)
    e = " | ".join(validate_config(cfg, ROOT))
    assert "student_record.pass_min_point" in e and "student_record.gpa_retake" in e and "gpa_include_failed" in e
    cfg["student_record"].update(degree_credits={"K21": "144"}, plan_max_courses=0)
    e = " | ".join(validate_config(cfg, ROOT))
    assert "student_record.degree_credits" in e and "student_record.plan_max_courses" in e
    cfg["paths"]["photos_dir"] = str(ROOT / "cadangan")
    assert any(x.startswith("paths.photos_dir") and "di dalam repo" in x for x in validate_config(cfg, ROOT))


def test_removed_course_leaves_student_record_but_not_programme_figures(dua_semester, tmp_path):
    """Owner 2026-11-14: an approved course removal leaves the grade list, GPA and the student's CPL;
    class, cumulative and cohort attainment keep every student."""
    from cpl.radar import radar_data
    from cpl.student_record import removals
    cfg, fin, rep = dua_semester
    hapus = tmp_path / "hapus_mk.csv"
    hapus.write_text("nim,kode_mk,tahun_akademik,semester,keterangan\n"
                     "999922001,41999,2025/2026,ganjil,SK 1\n"        # one term (case-insensitive)
                     "999922001,41212,,,SK 2\n"                       # every attempt
                     "999922001,41203,2025/2026,,salah isi\n", encoding="utf-8")   # incomplete: skipped
    cfg["paths"]["course_removals_csv"] = str(hapus)
    rm = removals(cfg)
    assert rm == {("999922001", "41999", "2025/2026 ganjil"), ("999922001", "41212", "")}
    rep2 = build_report([], cfg, fin, rm)
    d = radar_data(rep2, cfg, record=build_records(cfg, ROOT, fin["files"], rm))
    m = next(x for x in d["mahasiswa"] if x["nim"] == "999922001")
    assert [x["kode"] for s in m["smt"] for x in s["mk"]] == ["41203"]
    assert m["smt"][0]["ips"] == pytest.approx(4.0) and m["smt"][0]["sks_lulus"] == 3
    assert m["skor"]["j"] == pytest.approx(85.0)                       # 41212 (Genap, 50) no longer counts
    other = next(x for x in d["mahasiswa"] if x["nim"] == "999922002")
    assert [x["kode"] for s in other["smt"] for x in s["mk"]] == ["41203", "41212"]   # other student untouched
    for t in ("cpl_cumulative", "cohort_cpl", "class_attainment", "term_progress"):
        assert rep2[t].equals(rep[t]), t


def test_short_semester_after_even_term_and_own_block(dua_semester):
    """Owner 2026-11-14: semester pendek ("Pendek") comes after Genap, has its own block and IPS,
    and is not counted as a regular semester."""
    from cpl.radar import radar_data
    cfg, _, _ = dua_semester
    tulis(Path(cfg["paths"]["final_grades_dir"]) / "2025_pendek", "Nilai_Detail_Kelas_2026_Mekanika Tanah I-SP-2025.csv",
          [("999922001", [1, 1, 1, 1], 72.0)])
    fin = prepare_final(cfg, ROOT)
    sp = next(f for f in fin["files"] if "Mekanika" in f.path.name)
    assert sp.ok and sp.term == "2025/2026 Pendek" and sp.term_order == 20253
    d = radar_data(build_report([], cfg, fin), cfg, record=build_records(cfg, ROOT, fin["files"]))
    m = next(x for x in d["mahasiswa"] if x["nim"] == "999922001")
    assert [(s["term"], s["pendek"]) for s in m["smt"]] == [
        ("2025/2026 Ganjil", False), ("2025/2026 Genap", False), ("2025/2026 Pendek", True)]
    assert m["smt"][2]["ips"] == pytest.approx(2.0)                    # 72 = C in the test scale SKALA
    cfg["student_record"]["short_semesters"] = ["Antara"]
    assert any(e.startswith("student_record.short_semesters") for e in validate_config(cfg, ROOT))
