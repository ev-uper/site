"""run_jadwal.py + jadwal/ (rencana pemilik 2026-11-21, aturan pemilik 2026-11-22), data sintetis."""
import csv
import json
from pathlib import Path

import pytest

pytest.importorskip("highspy")

import run_jadwal  # noqa: E402
from jadwal.aturan import baca_aturan, menit  # noqa: E402
from jadwal.masukan import baca_masukan  # noqa: E402
from jadwal.model import durasi_slot, periksa, susun  # noqa: E402

ATURAN = {"schedule": {"minutes_per_sks": 50, "same_label_break_minutes": 30, "electives_no_overlap": True,
                       "blocked": [{"day": 5, "start": "11:30", "end": "13:00"}], "avoid": [{"day": "all", "start": "12:00", "end": "13:00"}],
                       "lecturer_daily_max_hours": 6,
                       "weights": {"avoid": 10, "lecturer_overload": 20, "dated_unavailability": 5, "earlier_start": 0.01},
                       "time_limit_seconds": 60}}
SLOT = [{"id": 100 + i, "mulai": f"{(420 + 30 * i) // 60:02d}:{(420 + 30 * i) % 60:02d}",
         "selesai": f"{(450 + 30 * i) // 60:02d}:{(450 + 30 * i) % 60:02d}"} for i in range(19)]   # 07:00-16:30


def kelas(i, kode, sks, paket, label, dosen, pilihan=False, jadwal=None):
    return {"id": i, "kurikulum": "K26", "kode_mk": kode, "nama_mk": f"MK {kode}", "sks": sks, "semester_paket": paket,
            "pilihan": pilihan, "kelas": label, "dosen": dosen, "jadwal": jadwal}


def masukan(tmp_path, kelas_, berhalangan=(), tanggal=(), hari=(1, 2, 3, 4, 5)):
    d = {"format": "jadwal-masukan-1", "tahun_akademik": "2026/2027", "semester": "Genap",
         "masa_kuliah": [{"mulai": "2027-02-01", "selesai": "2027-02-28"}], "libur": ["2027-02-17"], "hari": list(hari),
         "slot": SLOT, "dosen": [{"id": f"d{i}", "nama": f"Dosen {i}"} for i in range(1, 6)], "kelas": kelas_,
         "berhalangan": list(berhalangan), "berhalangan_tanggal": list(tanggal)}
    p = tmp_path / "jadwal_masukan_2026-2027_Genap.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return p


def contoh(tmp_path):
    k = [kelas(1, "SI201", 3, 2, "A", ["d1"]), kelas(2, "SI202", 2, 2, "A", ["d1"]), kelas(3, "SI203", 3, 2, "A", ["d2"]),
         kelas(4, "SI201", 3, 2, "B", ["d1"]), kelas(5, "SI202", 2, 2, "B", ["d3"]), kelas(6, "SI203", 3, 2, "B", ["d2", "d3"]),
         kelas(7, "SI401", 3, 4, "A", ["d4"]), kelas(8, "SI402", 2, 4, "A", ["d4"]),
         kelas(9, "SP01", 2, None, "A", ["d5"], pilihan=True), kelas(10, "SP02", 2, None, "A", ["d4"], pilihan=True),
         kelas(11, "SP03", 3, None, "A", ["d3"], pilihan=True),
         kelas(12, "SI403", 2, 4, "A", ["d5"], jadwal={"hari": 3, "mulai": "13:00", "selesai": "15:00", "kunci": True}),
         kelas(13, "SI404", 2, 4, "B", ["d5"], jadwal={"hari": 1, "mulai": "07:00", "selesai": "09:00", "kunci": False})]
    senin_d2 = [{"dosen": "d2", "hari": 1, "slot": s["id"]} for s in SLOT]                  # d2 berhalangan Senin seharian
    return masukan(tmp_path, k, senin_d2, [{"dosen": "d4", "tanggal": "2027-02-02", "slot": None}])


def test_config_rules_validated_with_key_names():
    a, err = baca_aturan(ATURAN)
    assert a and not err and a.blocked[0].hari == 5 and a.avoid[0].hari is None
    salah = json.loads(json.dumps(ATURAN))
    salah["schedule"].update(minutes_per_sks=0, blocked=[{"day": 8, "start": "11:30", "end": "13:00"}], lecturer_daily_max_hours="6")
    salah["schedule"]["weights"].pop("avoid")
    _, err = baca_aturan(salah)
    assert any(e.startswith("schedule.minutes_per_sks") for e in err)
    assert any(e.startswith("schedule.blocked[0].day") for e in err)
    assert any(e.startswith("schedule.lecturer_daily_max_hours") for e in err)
    assert any(e.startswith("schedule.weights.avoid") for e in err)
    assert run_jadwal.periksa_config({**ATURAN, "paths": {}})[-1].startswith("paths.schedule_dir")
    assert baca_aturan({})[1] == ["schedule: bagian belum ada di config.yaml"]


def test_duration_rounds_sks_up_to_slots(tmp_path):
    a, _ = baca_aturan(ATURAN)
    m, _ = baca_masukan(contoh(tmp_path))
    by = {k.kode: k for k in m.kelas}
    assert durasi_slot(by["SI202"], a, 30) == 4      # 2 sks = 100 menit -> 2 jam (pemilik 2026-11-22)
    assert durasi_slot(by["SI201"], a, 30) == 5      # 3 sks = 150 menit -> 2,5 jam


def test_dated_unavailability_counts_lecture_dates_only(tmp_path):
    m, warn = baca_masukan(contoh(tmp_path))
    assert not warn
    assert m.bertanggal == {("d4", 2, None): 1}       # 2 Feb 2027 = Selasa, di masa kuliah
    assert m.pertemuan[3] == 3                        # Rabu Februari 2027: 3, 10, 24 (17 libur)
    assert ("d2", 1, 100) in m.berhalangan


def test_timetable_respects_every_hard_rule(tmp_path):
    a, _ = baca_aturan(ATURAN)
    m, _ = baca_masukan(contoh(tmp_path))
    h = susun(m, a)
    assert h.status == "optimal", h.pesan
    j = h.jadwal
    assert len(j) == 13
    cek = periksa(m, a, j)
    assert cek["wajib"] == []
    assert (j[12].hari, j[12].mulai, j[12].selesai) == (3, menit("13:00"), menit("15:00"))   # dikunci: tetap
    for kid in (3, 6):                                # d2 berhalangan Senin
        assert j[kid].hari != 1
    for p in j.values():                              # Jumat 11.30-13.00 kosong; jam 12-13 dihindari (masih cukup slot)
        assert not (p.hari == 5 and p.mulai < menit("13:00") and menit("11:30") < p.selesai)
        assert not (p.mulai < menit("13:00") and menit("12:00") < p.selesai)
    assert j[1].selesai - j[1].mulai == 150 and j[2].selesai - j[2].mulai == 120
    # kelas A semester 2 (1, 2, 3): tidak bentrok dan berjeda >= 30 menit pada hari yang sama
    xs = [j[i] for i in (1, 2, 3)]
    for i, p in enumerate(xs):
        for q in xs[i + 1:]:
            if p.hari == q.hari:
                assert max(q.mulai - p.selesai, p.mulai - q.selesai) >= 30
    # MK pilihan tidak saling bentrok
    ps = [j[i] for i in (9, 10, 11)]
    for i, p in enumerate(ps):
        for q in ps[i + 1:]:
            assert p.hari != q.hari or p.selesai <= q.mulai or q.selesai <= p.mulai


def test_class_without_any_valid_position_is_explained(tmp_path):
    a, _ = baca_aturan(ATURAN)
    semua = [{"dosen": "d1", "hari": h, "slot": s["id"]} for h in range(1, 6) for s in SLOT]
    m, _ = baca_masukan(masukan(tmp_path, [kelas(1, "SI201", 3, 2, "A", ["d1"])], semua))
    h = susun(m, a)
    assert h.status == "tidak_layak" and "berhalangan mingguan dosen (Dosen 1)" in h.tanpa_pilihan[0]


def test_overfull_label_group_is_infeasible_with_hint(tmp_path):
    a, _ = baca_aturan(ATURAN)
    k = [kelas(i, f"SX{i:02d}", 3, 2, "A", [f"d{1 + i % 5}"]) for i in range(1, 22)]   # 21 x 2,5 jam + jeda > 1 hari x 5
    m, _ = baca_masukan(masukan(tmp_path, k, hari=(1,)))
    h = susun(m, a)
    assert h.status == "tidak_layak" and not h.jadwal
    from jadwal.model import saran_tidak_layak
    assert any("kelas A semester 2 K26" in s for s in saran_tidak_layak(m, a))


def test_bad_input_file_messages(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"format": "lain"}', encoding="utf-8")
    assert "bukan berkas masukan" in baca_masukan(p)[1][0]
    d = json.loads(contoh(tmp_path).read_text(encoding="utf-8"))
    d["slot"][0]["selesai"] = "08:00"
    p.write_text(json.dumps(d), encoding="utf-8")
    assert "slot sama panjang" in baca_masukan(p)[1][0]


def test_runner_end_to_end_writes_import_excel_report(tmp_path, monkeypatch):
    f = contoh(tmp_path)
    out = tmp_path / "hasil"
    assert run_jadwal.main(["--masukan", str(f), "--keluar", str(out), "--batas-waktu", "60"]) == 0
    csvf = out / "hasil_jadwal_2026-2027_Genap.csv"
    rows = list(csv.DictReader(csvf.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    assert len(rows) == 13 and list(rows[0])[:4] == ["kelas_id", "hari", "mulai", "selesai"]
    assert (out / "jadwal_2026-2027_Genap.xlsx").is_file()
    lap = (out / "laporan_jadwal.txt").read_text(encoding="utf-8")
    assert "Hasil: optimal" in lap and "Pelanggaran wajib: 0" in lap and "50 menit per sks" in lap
    assert (out / "run_jadwal.log").is_file()


def test_site_input_file_is_read_by_the_runner(tmp_path):
    """Berkas masukan dari jadwal-kuliah.js (masukanPenjadwalan) dibaca jadwal/masukan.py dan tersusun (format sama)."""
    import os
    import shutil
    import subprocess
    if not shutil.which("node"):
        pytest.skip("node tidak ada")
    js = (Path(__file__).resolve().parents[1] / "site" / "jadwal-kuliah.js").as_uri()
    keluar = tmp_path / "jadwal_masukan_2026-2027_Genap.json"
    skrip = f"""
import {{ masukanPenjadwalan }} from '{js}';
import {{ writeFileSync }} from 'node:fs';
const slot = Array.from({{ length: 19 }}, (_, i) => ({{ id: 100 + i, mulai: `${{String(7 + Math.floor(i / 2)).padStart(2, '0')}}:${{i % 2 ? '30' : '00'}}:00`,
  selesai: `${{String(7 + Math.floor((i + 1) / 2)).padStart(2, '0')}}:${{(i + 1) % 2 ? '30' : '00'}}:00`, aktif: true }}));
const m = masukanPenjadwalan({{ ta: '2026/2027', sm: 'Genap', slot, hari: [1, 2, 3, 4, 5],
  mk: [{{ kurikulum: 'K26', kode: 'SI201', nama: 'Statika', sks: 3, semester: 2, sifat: 'wajib' }},
       {{ kurikulum: 'K26', kode: 'SI202', nama: 'Hidrologi', sks: 2, semester: 2, sifat: 'wajib' }},
       {{ kurikulum: 'K26', kode: 'SP01', nama: 'Pilihan', sks: 2, semester: null, sifat: 'pilihan' }}],
  kelas: [{{ id: 1, kurikulum: 'K26', kode_mk: 'SI201', kelas: 'A' }}, {{ id: 2, kurikulum: 'K26', kode_mk: 'SI202', kelas: 'A' }},
          {{ id: 3, kurikulum: 'K26', kode_mk: 'SP01', kelas: 'A' }}],
  kd: [{{ kelas_id: 1, dosen_id: 'u1', urutan: 0 }}, {{ kelas_id: 2, dosen_id: 'u1', urutan: 0 }}, {{ kelas_id: 3, dosen_id: 'u2', urutan: 0 }}],
  dosen: [{{ id: 'u1', nama: 'Satu' }}, {{ id: 'u2', nama: 'Dua' }}],
  jadwal: [{{ kelas_id: 3, hari: 4, mulai: '13:00:00', selesai: '15:00:00', kunci: true }}],
  berhalangan: [{{ dosen_id: 'u1', hari: 1, slot_id: 100 }}],
  rentang: [{{ dosen_id: 'u1', mulai: '2027-02-01', selesai: '2027-02-28', hari: [2], slot_ids: null }}],
  masa: [{{ mulai: '2027-02-01', selesai: '2027-02-28' }}], libur: [] }});
writeFileSync(process.env.KELUAR_UJI, JSON.stringify(m));
"""
    r = subprocess.run(["node", "--input-type=module", "-e", skrip], capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "KELUAR_UJI": str(keluar)})
    assert r.returncode == 0, r.stderr
    m, warn = baca_masukan(keluar)
    assert m is not None, warn
    assert m.bertanggal == {("u1", 2, None): 4}          # rentang Selasa sepanjang hari: 4 Selasa di Februari 2027
    assert [k.tetap for k in m.kelas if k.id == 3] == [(4, menit("13:00"), menit("15:00"))]
    a, _ = baca_aturan(ATURAN)
    h = susun(m, a)
    assert h.status == "optimal" and periksa(m, a, h.jadwal)["wajib"] == []
    assert all(p.hari != 2 for k, p in h.jadwal.items() if k in (1, 2))   # Selasa dihindari (bertanggal, tiap minggu)


def test_mku_and_faculty_times_are_fixed_and_respected(tmp_path):
    """MKU (universitas) dan MK fakultas: jadwal ditetapkan lebih dulu, per kelas paralel (pemilik 2026-11-22)."""
    a, _ = baca_aturan(ATURAN)
    k = [kelas(1, "MKU1", 2, 2, "A", [], jadwal={"hari": 1, "mulai": "07:00", "selesai": "08:40", "kunci": False}),
         kelas(2, "FAK1", 3, 2, "A", []),                                    # fakultas, belum berjadwal -> dilewati
         kelas(3, "SI201", 3, 2, "A", ["d1"]), kelas(4, "SI202", 2, 2, "A", ["d2"]), kelas(5, "SI203", 3, 2, "B", ["d3"])]
    k[0]["penyelenggara"], k[1]["penyelenggara"] = "universitas", "fakultas"
    # hanya Senin, supaya kelas A semester 2 harus berbagi hari dengan MKU
    m, warn = baca_masukan(masukan(tmp_path, k, hari=(1,)))
    assert [x.kode for x in m.kelas] == ["MKU1", "SI201", "SI202", "SI203"]
    assert any("FAK1 A: MK fakultas belum berjadwal" in w for w in warn)
    assert not any("belum ada dosen" in w for w in warn)                     # MKU tanpa dosen prodi: bukan peringatan
    h = susun(m, a)
    assert h.status == "optimal", h.pesan
    j = h.jadwal
    assert (j[1].hari, j[1].mulai, j[1].selesai) == (1, menit("07:00"), menit("08:40"))   # tetap walau tidak dicentang kunci
    for kid in (3, 4):                                                       # kelas A: tidak bentrok + jeda >= 30 menit dari MKU
        assert j[kid].mulai >= menit("08:40") + 30 or j[kid].selesai + 30 <= menit("07:00")
    assert periksa(m, a, j)["wajib"] == []
