"""Estimated CPL from final course grades (owner 2026-11-13; cpl/final_grades.py). Synthetic data only."""
import json
from pathlib import Path

import pytest

from cpl.archive import build_report, summary
from cpl.config import load_config, validate_config
from cpl.final_grades import load_reference, norm_name, parse_name, prepare_final, shares

ROOT = Path(__file__).resolve().parents[1]
HEAD = 'No;NIM;Nama;"KUIS (KUIS) (20.00%)";"TUGAS (TUGAS) (20.00%)";"UTS (UTS) (30.00%)";"UAS (UAS) (30.00%)";"Nilai Akhir"'


@pytest.fixture()
def cfg(tmp_path):
    c = load_config(ROOT / "config.yaml")
    ref = tmp_path / "ref"
    ref.mkdir()
    (ref / "ref_mata_kuliah.csv").write_text(
        "kode,nama,sks,semester,kurikulum,sifat\n"
        "41212,Analisis Struktur Statis Tak Tentu,3,4,K21,wajib\n"
        "41203,Analisis Struktur Statis Tertentu,3,3,K21,wajib\n"
        "41107,Matematika Teknik I,3,2,K21,wajib\n"
        "41210,Mekanika Tanah I,2,4,K21,wajib\n"
        "10007,Cipta Karsa,2,8,K21,wajib\n"
        "41406,Metode Elemen Hingga,3,,K21,pilihan\n"
        "41212,MK lain di K26,2,5,K26,wajib\n", encoding="utf-8")
    (ref / "ref_mk_cpl.csv").write_text(
        "kurikulum,kode_mk,cpl,bobot\nK21,41212,f,\nK21,41212,g,\nK21,41212,j,\n"
        "K21,41203,j,2\nK21,41203,g,1\nK21,41406,j,\nK21,41107,g,\nK21,41210,j,\nK21,10007,d,\n", encoding="utf-8")
    nilai = tmp_path / "nilai"
    nilai.mkdir()
    c["paths"] = {"final_grades_dir": str(nilai)}
    c["final_grades"]["reference_dir"] = str(ref)
    c["final_grades"]["student_id_prefixes"] = ["9999"]
    return c


def tulis(folder, nama, baris, kepala=HEAD):
    komp = kepala.count("%")
    Path(folder).mkdir(parents=True, exist_ok=True)
    (Path(folder) / nama).write_text(kepala + "\n" + "\n".join(
        f'{i + 1};{nim};"Mhs {i}";' + ";".join(map(str, list(k)[:komp] + [na]))
        for i, (nim, k, na) in enumerate(baris)) + "\n", encoding="utf-8")


def test_name_parsing_variants():
    p = parse_name("Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2025")
    assert (p["a"], p["b"], p["n"], p["course"], p["class_name"], p["uk"]) == (2026, 2025, None, "Analisis Struktur Statis Tak Tentu", "CV4", False)
    p = parse_name("Nilai_Detail_Kelas_2026_Mekanika Tanah I UK -2025-2")
    assert (p["course"], p["class_name"], p["uk"], p["b"], p["n"]) == ("Mekanika Tanah I", "UK", True, 2025, 2)
    p = parse_name("Nilai_Detail_Kelas_2026_Kerja Praktik-Anto Contoh 2025-2")
    assert (p["course"], p["class_name"], p["n"]) == ("Kerja Praktik", "Anto Contoh", 2)
    p = parse_name("Nilai_Detail_Kelas_2026_Cipta Karsa-CV 2025-2")
    assert (p["course"], p["class_name"]) == ("Cipta Karsa", "CV")
    p = parse_name("Nilai_Detail_Kelas_2026_Cipta Karsa-CO-CV 2025-1")
    assert (p["course"], p["class_name"], p["n"]) == ("Cipta Karsa-CO", "CV", 1)
    p = parse_name("Nilai_Detail_Kelas_2026_Struktur Beton II-UK 2025-1")
    assert (p["course"], p["class_name"], p["uk"]) == ("Struktur Beton II", "UK", True)
    assert parse_name("rekap") is None


def test_name_normalisation_and_equal_or_weighted_shares(cfg):
    assert norm_name("Matematika Teknik I") == norm_name("matematika  teknik 1")
    _, peta = load_reference(cfg["final_grades"]["reference_dir"])
    s = shares(peta)
    assert [round(x, 3) for _, x in s[("K21", "41212")]] == [0.333, 0.333, 0.333]
    assert dict(s[("K21", "41203")]) == pytest.approx({"j": 2 / 3, "g": 1 / 3})


def test_identity_semester_from_suffix_or_folder_and_filters(cfg):
    root = Path(cfg["paths"]["final_grades_dir"])
    d = root / "2025_genap"
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2025.csv",
          [("9999000001", [80, 80, 60, 50], 64.0), ("9999000002", [0, 0, 0, 0], 0.0), ("9999000003", [20, 10, 30, 40], 27.0),
           ("1013000001", [90, 90, 90, 90], 90.0)])
    # Ganjil 2025/2026 exports also carry 2026 first: the folder decides (seen 2026-11-13).
    tulis(root / "2024_ganjil", "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tertentu-CV1-2024.csv",
          [("9999000001", [90, 90, 90, 90], 90.0)])
    tulis(root / "lain", "Nilai_Detail_Kelas_2026_Cipta Karsa-CO-CV 2025-2.csv", [("9999000001", [1, 1, 1, 1], 70.0)])
    fin = prepare_final(cfg, ROOT)
    f = {x.identity["course_code"]: x for x in fin["files"]}
    assert all(x.ok for x in fin["files"]), [x.problems for x in fin["files"]]
    assert f["41212"].term == "2025/2026 Genap" and f["41212"].identity["class_name"] == "CV4"   # folder 2025_genap
    assert f["41203"].term == "2024/2025 Ganjil"                                                 # folder 2024_ganjil
    assert f["10007"].term == "2025/2026 Genap" and f["10007"].identity["class_name"] == "CV"    # suffix -2, "CO" dropped
    b = f["41212"]
    assert (b.excluded_zero, b.excluded_other, len(b.students)) == (1, 1, 2)
    assert len(fin["class_rows"]) == 6


def test_uk_capped_and_merged_into_regular_class(cfg):
    d = Path(cfg["paths"]["final_grades_dir"]) / "2025_genap"
    tulis(d, "Nilai_Detail_Kelas_2026_Mekanika Tanah I-CV4-2025.csv",
          [("9999000001", [10, 10, 10, 10], 30.0), ("9999000002", [80, 80, 80, 80], 80.0), ("9999000003", [0, 0, 0, 0], 0.0)])
    tulis(d, "Nilai_Detail_Kelas_2026_Mekanika Tanah I UK -2025-2.csv",
          [("9999000001", [], 85.0), ("9999000003", [], 60.0)], kepala="No;NIM;Nama;Nilai Akhir")
    fin = prepare_final(cfg, ROOT)
    reg = next(x for x in fin["files"] if not x.uk)
    uk = next(x for x in fin["files"] if x.uk)
    assert uk.ok and uk.merged_into and uk.capped == 2
    assert dict(reg.students) == {"9999000001": 45.0, "9999000002": 80.0, "9999000003": 45.0}
    rows = [r for r in fin["class_rows"]]
    assert len(rows) == 1 and (rows[0]["counted"], rows[0]["above_threshold"]) == (3, 3)
    assert set(fin["scores"]["file"]) == {reg.path.name}


def test_report_marks_estimates_and_weights_sks_share(cfg):
    d = Path(cfg["paths"]["final_grades_dir"])
    tulis(d / "2025_genap", "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2025.csv", [("9999000001", [1, 1, 1, 1], 40.0)])
    tulis(d / "2024_genap", "Nilai_Detail_Kelas_2025_Analisis Struktur Statis Tertentu-CV1-2024.csv", [("9999000001", [1, 1, 1, 1], 70.0)])
    fin = prepare_final(cfg, ROOT)
    rep = build_report([], cfg, fin)
    cum = rep["cpl_cumulative"].set_index("cpl")
    # CPL j: 41212 weight 3 x 1/3 = 1 (score 40), 41203 weight 3 x 2/3 = 2 (score 70) -> 60
    assert cum.loc["j", "mean_score"] == pytest.approx(60.0)
    assert cum.loc["f", "mean_score"] == pytest.approx(40.0)
    assert cum["estimate"].all()
    assert rep["coverage_courses"].set_index("course_code").loc["41107", "files"] == 0
    s = summary(rep, [], cfg, "2026-11-13T20:00:00+07:00", fin["files"])
    teks = json.dumps(s)
    assert "9999000001" not in teks and "estimasi" in s["aturan"]
    assert all(r["estimate"] is True for r in s["kumulatif"]) and s["berkas"][0]["jenis"] == "nilai_akhir"


def test_rejections_and_override_list(cfg):
    cfg["final_grades"]["course_aliases"] = {}   # this test checks rejection and daftar_berkas.csv without aliases
    d = Path(cfg["paths"]["final_grades_dir"])
    tulis(d / "2025_genap", "Nilai_Detail_Kelas_2026_Matematika Teknik-CV2-2025.csv", [("9999000001", [1, 1, 1, 1], 50)])
    tulis(d / "2027_ganjil", "Nilai_Detail_Kelas_2027_Matematika Teknik I-CV1-2027.csv", [("9999000001", [1, 1, 1, 1], 50)])
    tulis(d / "2025_genap", "Nilai_Detail_Kelas_2026_Mekanika Tanah I-CV4-2024.csv", [("9999000001", [1, 1, 1, 1], 50)])
    tulis(d, "Nilai_Detail_Kelas_2029_Metode Elemen Hingga-CV1-2025.csv", [("9999000001", [1, 1, 1, 1], 50)])
    tulis(d, "rekap.csv", [("9999000001", [1, 1, 1, 1], 50)])
    fin = prepare_final(cfg, ROOT)
    msg = {f.path.name: "; ".join(f.problems) for f in fin["files"]}
    assert "tidak ada di K21; isi kode_mk" in msg["Nilai_Detail_Kelas_2026_Matematika Teknik-CV2-2025.csv"]
    assert "tidak ada aturan kurikulum untuk 2027/2028" in msg["Nilai_Detail_Kelas_2027_Matematika Teknik I-CV1-2027.csv"]
    assert "semester tidak bisa dibaca" in msg["Nilai_Detail_Kelas_2029_Metode Elemen Hingga-CV1-2025.csv"]
    assert "nama berkas" in msg["rekap.csv"]
    assert "beda dengan nama folder" in msg["Nilai_Detail_Kelas_2026_Mekanika Tanah I-CV4-2024.csv"]
    # daftar_berkas.csv is read in every semester folder too.
    (d / "2025_genap" / "daftar_berkas.csv").write_text(
        "berkas;kode_mk\nNilai_Detail_Kelas_2026_Matematika Teknik-CV2-2025.csv;41107\n", encoding="utf-8")
    (d / "daftar_berkas.csv").write_text("berkas;kode_mk;kurikulum;tahun_akademik;semester;kelas\n"
                                         "Nilai_Detail_Kelas_2029_Metode Elemen Hingga-CV1-2025.csv;;;;Ganjil;\n"
                                         "rekap.csv;41107;K21;2023/2024;Genap;A\n", encoding="utf-8")
    fin = prepare_final(cfg, ROOT)
    ok = {f.path.name: f for f in fin["files"] if f.ok}
    assert ok["Nilai_Detail_Kelas_2026_Matematika Teknik-CV2-2025.csv"].term == "2025/2026 Genap"
    assert ok["Nilai_Detail_Kelas_2029_Metode Elemen Hingga-CV1-2025.csv"].term == "2025/2026 Ganjil"
    assert ok["rekap.csv"].identity["course_code"] == "41107"


def test_class_with_template_file_is_skipped(cfg):
    d = Path(cfg["paths"]["final_grades_dir"]) / "2025_genap"
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2025.csv", [("9999000001", [1, 1, 1, 1], 40.0)])

    class T:
        ok = True
        identity = {"curriculum": "K21", "course_code": "41212", "academic_year": "2025/2026", "semester": "Genap",
                    "class_name": "cv4"}
    fin = prepare_final(cfg, ROOT, [T()])
    assert "templat CPL rinci" in fin["files"][0].problems[0]


def test_config_validation(cfg):
    base = [e for e in validate_config(cfg, ROOT) if not e.startswith(("paths.input_dir", "paths.output_dir"))]
    assert base == []
    bad = {**cfg, "final_grades": {**cfg["final_grades"], "curriculum_by_year": [{"until": "2025", "curriculum": "K21"}],
                                   "exclude_all_zero": "ya", "course_weight": "sks", "student_id_prefixes": "1041",
                                   "uk_cap": 120}}
    e = " | ".join(validate_config(bad, ROOT))
    for k in ("curriculum_by_year[0]", "exclude_all_zero", "course_weight", "student_id_prefixes", "uk_cap"):
        assert k in e
    inside = {**cfg, "paths": {"final_grades_dir": str(ROOT / "cadangan")}}
    assert any("di dalam repo" in x for x in validate_config(inside, ROOT))


def test_empty_final_grade_with_zero_components_is_not_counted(cfg):
    d = Path(cfg["paths"]["final_grades_dir"]) / "2025_ganjil"
    d.mkdir(parents=True)
    (d / "Nilai_Detail_Kelas_2026_Cipta Karsa-CV1-2025.csv").write_text(
        HEAD + '\n1;9999000001;"A";80;80;80;80;80\n2;9999000002;"B";0;0;0;0;\n3;1013000001;"C";;;;;\n', encoding="utf-8")
    (d / "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tertentu-CV3-2025.csv").write_text(
        HEAD + '\n1;9999000001;"A";80;80;80;80;\n', encoding="utf-8")
    fin = prepare_final(cfg, ROOT)
    f = {x.identity["course_code"]: x for x in fin["files"]}
    assert f["10007"].ok and (f["10007"].excluded_zero, f["10007"].excluded_other, len(f["10007"].students)) == (1, 1, 1)
    assert "padahal komponen berisi nilai" in f["41203"].problems[0]


def test_identical_browser_copy_is_skipped(cfg):
    d = Path(cfg["paths"]["final_grades_dir"]) / "2024_ganjil"
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tertentu-CV3-2024.csv", [("9999000001", [1, 1, 1, 1], 70.0)])
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tertentu-CV3-2024 (1).csv", [("9999000001", [1, 1, 1, 1], 70.0)])
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2024.csv", [("9999000001", [1, 1, 1, 1], 70.0)])
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2024 (1).csv", [("9999000001", [1, 1, 1, 1], 50.0)])
    fin = prepare_final(cfg, ROOT)
    msg = {f.path.name: "; ".join(f.problems) for f in fin["files"]}
    assert msg["Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tertentu-CV3-2024.csv"] == ""
    assert "salinan unduhan ganda" in msg["Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tertentu-CV3-2024 (1).csv"]
    # different content: both flagged as the same class twice, the owner decides
    assert all("identitas kelas ganda" in v for k, v in msg.items() if "Tak Tentu" in k)


def test_course_alias_from_config(cfg):
    # Alias dipasang di sini (bukan bergantung pada alias prodi di config.yaml; templat prodi lain mengosongkannya).
    cfg["final_grades"]["course_aliases"] = {"K21": {"Matematika Teknik": "41107"}}
    d = Path(cfg["paths"]["final_grades_dir"]) / "2023_genap"
    tulis(d, "Nilai_Detail_Kelas_2026_Matematika Teknik-CV2 2023.csv", [("9999000001", [1, 1, 1, 1], 70.0)])
    fin = prepare_final(cfg, ROOT)
    f = fin["files"][0]
    assert f.ok and f.identity["course_code"] == "41107" and f.term == "2023/2024 Genap"
    assert "padanan nama" in f.notes[-1]
    bad = {**cfg, "final_grades": {**cfg["final_grades"], "course_aliases": {"K21": ["x"]}}}
    assert any("course_aliases" in e for e in validate_config(bad, ROOT))


def test_names_without_year_or_with_space_semester(cfg):
    p = parse_name("Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-UK- 2022 2")
    assert (p["course"], p["class_name"], p["uk"], p["b"], p["n"]) == ("Analisis Struktur Statis Tak Tentu", "UK", True, 2022, 2)
    p = parse_name("Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-UK CV")
    assert (p["course"], p["class_name"], p["uk"], p["b"]) == ("Analisis Struktur Statis Tak Tentu", "UK CV", True, None)
    d = Path(cfg["paths"]["final_grades_dir"]) / "2021_genap"
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-UK CV.csv", [("9999000001", [], 80.0)],
          kepala="No;NIM;Nama;Nilai Akhir")
    f = prepare_final(cfg, ROOT)["files"][0]
    assert f.ok and f.term == "2021/2022 Genap" and f.uk and f.students == [("9999000001", 45.0)]
    assert any("tahun dari nama folder" in n for n in f.notes)


def test_cohort_table_and_local_radar_page(cfg, tmp_path):
    from cpl.archive import cohort_of
    from cpl.radar import write_student_radar
    assert cohort_of("104122023", cfg) == 2022 and cohort_of("12", cfg) is None
    d = Path(cfg["paths"]["final_grades_dir"]) / "2025_genap"
    tulis(d, "Nilai_Detail_Kelas_2026_Analisis Struktur Statis Tak Tentu-CV4-2025.csv",
          [(f"999922{i:03d}", [1, 1, 1, 1], 40.0 + 10 * i) for i in range(6)] + [("999930001", [1, 1, 1, 1], 90.0)])
    fin = prepare_final(cfg, ROOT)
    rep = build_report([], cfg, fin)
    assert set(rep["cohort_cpl"]["cohort"]) == {2022, 2030}
    s = summary(rep, [], cfg, "2026-11-13T20:00:00+07:00", fin["files"])
    assert {r["cohort"] for r in s["angkatan"]} == {2022}              # cohort of 1 student left out (min_students 5)
    assert "999930001" not in json.dumps(s)
    p = write_student_radar(rep, cfg, tmp_path, {"999922000": "Mhs A"}, {("K21", "j"): "Rumusan j"})
    t = p.read_text(encoding="utf-8")
    assert "999922000" in t and "Mhs A" in t and "Rumusan j" in t and "Memuat NIM" in t
    assert "</" not in t.split("const D = ")[1].split("\n")[0]    # embedded JSON cannot close the script tag
