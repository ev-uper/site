"""Day and start time for every class: a 0-1 integer program solved with highspy (HiGHS).

One binary variable per (class, day, start slot) that already satisfies the rules that need no comparison with other
classes: the class fits in contiguous slots of that day, avoids the blocked windows (config schedule.blocked) and every
weekly unavailability of its lecturers. A locked class (kunci on the site) gets only its own time.
Hard constraints between classes, "at most one class per slot" for each:
  * lecturer (team teaching: every lecturer of the class);
  * curriculum + semester paket + class label (owner 2026-11-22), occupation stretched by the minimum break so two such
    classes on one day are at least schedule.same_label_break_minutes apart;
  * curriculum electives, when schedule.electives_no_overlap (owner 2026-11-22).
Costs (recommendations, config schedule.weights): slots inside schedule.avoid windows, lecturer slots per day above
schedule.lecturer_daily_max_hours, lecture dates hit by dated unavailability, and a tiny tie-breaker for earlier starts.
Rooms are not placed: the university assigns them and the prodi fills them in on the site (owner 2026-11-22).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .aturan import HARI, Aturan, jam
from .masukan import Kelas, Masukan


@dataclass(frozen=True)
class Pilihan:
    """One candidate placement of a class."""
    hari: int
    mulai: int           # minutes after midnight
    selesai: int
    slot: tuple[int, ...]    # indices into Masukan.slot covered by the class
    biaya: float


@dataclass
class Hasil:
    status: str                       # optimal | batas_waktu | tidak_layak | galat
    pesan: str
    jadwal: dict[int, Pilihan] = field(default_factory=dict)      # class id -> placement
    tanpa_pilihan: list[str] = field(default_factory=list)        # classes with no possible placement, with reasons
    biaya: float | None = None


def durasi_slot(k: Kelas, a: Aturan, panjang_slot: int) -> int:
    """Number of slots of one weekly meeting: sks x minutes per sks, rounded up (owner 2026-11-22)."""
    return max(1, math.ceil(k.sks * a.minutes_per_sks / panjang_slot - 1e-9))


def _slot_kena(m: Masukan, mulai: int, selesai: int) -> tuple[int, ...]:
    return tuple(i for i, s in enumerate(m.slot) if s.mulai < selesai and mulai < s.selesai)


def biaya_pilihan(k: Kelas, hari: int, idx: tuple[int, ...], m: Masukan, a: Aturan) -> float:
    """Recommendation cost of one placement, without the per-day lecturer load (that one needs all classes)."""
    w = a.weights
    hindar = sum(1 for i in idx for j in a.avoid if j.kena(hari, m.slot[i].mulai, m.slot[i].selesai))
    tanggal = 0
    for d in k.dosen:
        tanggal += m.bertanggal.get((d, hari, None), 0) * (1 if idx else 0)
        tanggal += sum(m.bertanggal.get((d, hari, m.slot[i].id), 0) for i in idx)
    return w.get("avoid", 0) * hindar + w.get("dated_unavailability", 0) * tanggal + w.get("earlier_start", 0) * (idx[0] if idx else 0)


def pilihan_kelas(k: Kelas, m: Masukan, a: Aturan) -> tuple[list[Pilihan], str]:
    """Every allowed placement of class k, and when there is none, a reason in Indonesian."""
    if k.tetap:
        h, mu, se = k.tetap
        idx = _slot_kena(m, mu, se)
        return [Pilihan(h, mu, se, idx, biaya_pilihan(k, h, idx, m, a))], ""
    panjang = m.slot[0].selesai - m.slot[0].mulai
    n = durasi_slot(k, a, panjang)
    if n > len(m.slot):
        return [], f"butuh {n} slot berturut-turut, slot aktif hanya {len(m.slot)}"
    out, alasan = [], {"blok": 0, "berhalangan": 0, "putus": 0}
    for h in m.hari:
        for i in range(len(m.slot) - n + 1):
            idx = tuple(range(i, i + n))
            if any(m.slot[j].selesai != m.slot[j + 1].mulai for j in idx[:-1]):
                alasan["putus"] += 1
                continue
            mu, se = m.slot[idx[0]].mulai, m.slot[idx[-1]].selesai
            if any(b.kena(h, mu, se) for b in a.blocked):
                alasan["blok"] += 1
                continue
            if any((d, h, m.slot[j].id) in m.berhalangan for d in k.dosen for j in idx):
                alasan["berhalangan"] += 1
                continue
            out.append(Pilihan(h, mu, se, idx, biaya_pilihan(k, h, idx, m, a)))
    if out:
        return out, ""
    return [], (f"tidak ada {n} slot berturut-turut yang bebas: {alasan['berhalangan']} posisi kena berhalangan mingguan dosen "
                f"({', '.join(m.nama_dosen(d) for d in k.dosen) or 'tanpa dosen'}), {alasan['blok']} kena jam wajib kosong, "
                f"{alasan['putus']} melewati jeda antar slot")


def kelompok(k: Kelas, a: Aturan) -> list[tuple[tuple, int]]:
    """Resources of class k as (key, extra slots after the end that the resource stays busy)."""
    out = [(("dosen", d), 0) for d in k.dosen]
    if k.pilihan:
        if a.electives_no_overlap:
            out.append((("pilihan", k.kurikulum), 0))
    elif k.paket is not None:
        out.append((("label", k.kurikulum, k.paket, k.label.strip().upper()), -1))   # -1 = use the break
    return out


def susun(m: Masukan, a: Aturan) -> Hasil:
    import highspy

    panjang = m.slot[0].selesai - m.slot[0].mulai
    jeda = math.ceil(a.same_label_break_minutes / panjang) if a.same_label_break_minutes else 0
    calon: dict[int, list[Pilihan]] = {}
    tanpa = []
    for k in m.kelas:
        ps, alasan = pilihan_kelas(k, m, a)
        if not ps:
            tanpa.append(f"{k.teks()} ({k.nama}): {alasan}")
        calon[k.id] = ps
    if tanpa:
        return Hasil("tidak_layak", "Ada kelas yang tidak punya posisi sah sama sekali; perbaiki dulu.", tanpa_pilihan=tanpa)

    # Columns: x(class, placement) then, when a daily maximum is set, over(lecturer, day) >= 0.
    kolom: list[tuple[int, Pilihan]] = [(k.id, p) for k in m.kelas for p in calon[k.id]]
    biaya = [p.biaya for _, p in kolom]
    baris_lo, baris_hi = [], []
    isi: list[list[tuple[int, float]]] = [[] for _ in kolom]      # per column: (row, coefficient)

    def baris(lo, hi):
        baris_lo.append(lo)
        baris_hi.append(hi)
        return len(baris_lo) - 1

    inf = highspy.kHighsInf
    per_kelas: dict[int, list[int]] = {}
    for c, (kid, _) in enumerate(kolom):
        per_kelas.setdefault(kid, []).append(c)
    for kid, cs in per_kelas.items():
        r = baris(1, 1)                               # every class exactly once a week
        for c in cs:
            isi[c].append((r, 1.0))
    kelas = {k.id: k for k in m.kelas}
    pakai: dict[tuple, list[int]] = {}               # (resource, day, slot index) -> columns
    for c, (kid, p) in enumerate(kolom):
        for kunci, tambah in kelompok(kelas[kid], a):
            ext = jeda if tambah < 0 else tambah
            akhir = min(len(m.slot) - 1, p.slot[-1] + ext) if p.slot else -1
            for i in range(p.slot[0], akhir + 1) if p.slot else []:
                pakai.setdefault((kunci, p.hari, i), []).append(c)
    for cs in pakai.values():
        if len(cs) > 1:
            r = baris(-inf, 1)
            for c in cs:
                isi[c].append((r, 1.0))
    lebih = []                                        # (lecturer, day) of the overload columns
    if a.lecturer_daily_max_hours is not None:
        maks = a.lecturer_daily_max_hours * 60 / panjang
        beban: dict[tuple[str, int], list[int]] = {}
        for c, (kid, p) in enumerate(kolom):
            for d in kelas[kid].dosen:
                beban.setdefault((d, p.hari), []).append(c)
        for (d, h), cs in beban.items():
            if sum(len(kolom[c][1].slot) for c in cs) <= maks:
                continue                                 # cannot exceed the maximum: no row needed
            r = baris(-inf, maks)
            for c in cs:
                isi[c].append((r, float(len(kolom[c][1].slot))))
            lebih.append((d, h, r))
    n_x = len(kolom)
    for d, h, r in lebih:
        isi.append([(r, -1.0)])
        biaya.append(a.weights.get("lecturer_overload", 0))

    lp = highspy.HighsLp()
    n = len(isi)
    lp.num_col_ = n
    lp.num_row_ = len(baris_lo)
    lp.col_cost_ = np.array(biaya, dtype=float)
    lp.col_lower_ = np.zeros(n)
    lp.col_upper_ = np.array([1.0] * n_x + [inf] * (n - n_x))
    lp.row_lower_ = np.array(baris_lo, dtype=float)
    lp.row_upper_ = np.array(baris_hi, dtype=float)
    start, index, value = [0], [], []
    for col in isi:
        for r, v in sorted(col):
            index.append(r)
            value.append(v)
        start.append(len(index))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = np.array(start, dtype=np.int32)
    lp.a_matrix_.index_ = np.array(index, dtype=np.int32)
    lp.a_matrix_.value_ = np.array(value, dtype=float)
    lp.integrality_ = [highspy.HighsVarType.kInteger] * n_x + [highspy.HighsVarType.kContinuous] * (n - n_x)
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", float(a.time_limit_seconds))
    h.setOptionValue("random_seed", 0)
    h.passModel(lp)
    h.run()
    st = h.getModelStatus()
    layak = h.getInfo().primal_solution_status == 2
    if st == highspy.HighsModelStatus.kOptimal:
        status = "optimal"
    elif st == highspy.HighsModelStatus.kTimeLimit and layak:
        status = "batas_waktu"
    elif st == highspy.HighsModelStatus.kInfeasible:
        return Hasil("tidak_layak", "Tidak ada jadwal yang memenuhi semua aturan wajib (bentrok dosen, label kelas, "
                     "MK pilihan, jam wajib kosong, berhalangan mingguan). Lihat saran di laporan.")
    else:
        return Hasil("galat", f"Pemecah berhenti tanpa jadwal: {h.modelStatusToString(st)}")
    x = h.getSolution().col_value
    jadwal = {kid: p for c, (kid, p) in enumerate(kolom) if x[c] > 0.5}
    pesan = "Jadwal optimal." if status == "optimal" else (
        f"Batas waktu {a.time_limit_seconds} detik habis; dipakai jadwal terbaik yang ditemukan (sah, mungkin belum optimal).")
    return Hasil(status, pesan, jadwal, biaya=float(h.getInfo().objective_function_value))


def periksa(m: Masukan, a: Aturan, jadwal: dict[int, Pilihan]) -> dict[str, list[str]]:
    """Independent check of a finished timetable. 'wajib' should be empty unless a locked class breaks a rule."""
    kelas = {k.id: k for k in m.kelas}
    panjang = m.slot[0].selesai - m.slot[0].mulai
    wajib, anjuran = [], []
    for kid, p in jadwal.items():
        k = kelas[kid]
        w = f"{k.teks()} {HARI[p.hari]} {jam(p.mulai)}-{jam(p.selesai)}"
        for b in a.blocked:
            if b.kena(p.hari, p.mulai, p.selesai):
                wajib.append(f"{w}: kena jam wajib kosong {b.teks()}")
        for d in k.dosen:
            if any((d, p.hari, m.slot[i].id) in m.berhalangan for i in p.slot):
                wajib.append(f"{w}: {m.nama_dosen(d)} berhalangan mingguan")
        for j in a.avoid:
            if j.kena(p.hari, p.mulai, p.selesai):
                anjuran.append(f"{w}: memakai jam yang dihindari {j.teks()}")
        kena = sum(m.bertanggal.get((d, p.hari, None), 0) + sum(m.bertanggal.get((d, p.hari, m.slot[i].id), 0) for i in p.slot)
                   for d in k.dosen)
        if kena:
            anjuran.append(f"{w}: {kena} pertemuan kena berhalangan bertanggal dosen")
        if not k.tetap and len(p.slot) != durasi_slot(k, a, panjang):
            wajib.append(f"{w}: lama tidak sesuai sks")
    ids = sorted(jadwal)
    for i, x in enumerate(ids):
        for y in ids[i + 1:]:
            p, q, kx, ky = jadwal[x], jadwal[y], kelas[x], kelas[y]
            if p.hari != q.hari:
                continue
            tumpang = p.mulai < q.selesai and q.mulai < p.selesai
            pasangan = f"{kx.teks()} dan {ky.teks()} ({HARI[p.hari]})"
            sama = set(kx.dosen) & set(ky.dosen)
            if tumpang and sama:
                wajib.append(f"{pasangan}: dosen bentrok ({', '.join(m.nama_dosen(d) for d in sama)})")
            if (not kx.pilihan and not ky.pilihan and kx.paket is not None and kx.paket == ky.paket
                    and kx.kurikulum == ky.kurikulum and kx.label.strip().upper() == ky.label.strip().upper()):
                jarak = max(q.mulai - p.selesai, p.mulai - q.selesai)
                if jarak < a.same_label_break_minutes:
                    wajib.append(f"{pasangan}: kelas {kx.label} semester {kx.paket} "
                                 + ("bentrok" if tumpang else f"hanya berjeda {jarak} menit"))
            if a.electives_no_overlap and kx.pilihan and ky.pilihan and kx.kurikulum == ky.kurikulum and tumpang:
                wajib.append(f"{pasangan}: MK pilihan {kx.kurikulum} bentrok")
    if a.lecturer_daily_max_hours is not None:
        beban: dict[tuple[str, int], int] = {}
        for kid, p in jadwal.items():
            for d in kelas[kid].dosen:
                beban[(d, p.hari)] = beban.get((d, p.hari), 0) + (p.selesai - p.mulai)
        for (d, h), mnt in sorted(beban.items(), key=lambda t: (m.nama_dosen(t[0][0]), t[0][1])):
            if mnt > a.lecturer_daily_max_hours * 60:
                anjuran.append(f"{m.nama_dosen(d)} {HARI[h]}: mengajar {mnt / 60:g} jam (anjuran maks {a.lecturer_daily_max_hours:g})")
    return {"wajib": wajib, "anjuran": anjuran}


def saran_tidak_layak(m: Masukan, a: Aturan) -> list[str]:
    """Simple capacity checks to explain an infeasible model: weekly load per lecturer and per label group."""
    panjang = m.slot[0].selesai - m.slot[0].mulai
    tersedia = len(m.hari) * len(m.slot)
    out = []
    beban: dict[tuple, int] = {}
    for k in m.kelas:
        n = durasi_slot(k, a, panjang)
        for kunci, _ in kelompok(k, a):
            beban[kunci] = beban.get(kunci, 0) + n
    for kunci, n in sorted(beban.items(), key=lambda t: -t[1]):
        if kunci[0] == "dosen":
            bebas = tersedia - sum(1 for d, _, _ in m.berhalangan if d == kunci[1])
            if n > 0.6 * bebas:
                out.append(f"{m.nama_dosen(kunci[1])}: {n} slot kuliah per minggu, slot bebas {bebas}")
        elif n > 0.6 * tersedia:
            nama = f"kelas {kunci[3]} semester {kunci[2]} {kunci[1]}" if kunci[0] == "label" else f"MK pilihan {kunci[1]}"
            out.append(f"{nama}: {n} slot per minggu dari {tersedia} slot tersedia")
    return out or ["Tidak ada beban yang jelas berlebih; periksa jam wajib kosong dan berhalangan mingguan dosen yang mengajar "
                   "kelas berlabel sama."]
