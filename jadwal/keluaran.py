"""Outputs of run_jadwal.py: import CSV for the site, Excel workbook, and a text report."""
from __future__ import annotations

import csv
from pathlib import Path

from .aturan import HARI, Aturan, jam, ringkas
from .masukan import Masukan
from .model import Hasil, Pilihan

KOLOM_IMPOR = ["kelas_id", "hari", "mulai", "selesai", "nama_hari", "kurikulum", "kode_mk", "nama_mk", "kelas", "sks",
               "semester_paket", "dosen"]


def baris_jadwal(m: Masukan, jadwal: dict[int, Pilihan]) -> list[dict]:
    """One row per class, ordered by day, start, curriculum, code, class."""
    kelas = {k.id: k for k in m.kelas}
    out = []
    for kid, p in jadwal.items():
        k = kelas[kid]
        out.append({"kelas_id": kid, "hari": p.hari, "mulai": jam(p.mulai), "selesai": jam(p.selesai), "nama_hari": HARI[p.hari],
                    "kurikulum": k.kurikulum, "kode_mk": k.kode, "nama_mk": k.nama, "kelas": k.label,
                    "sks": f"{k.sks:g}", "semester_paket": "pilihan" if k.pilihan else (k.paket or ""),
                    "dosen": " | ".join(m.nama_dosen(d) for d in k.dosen), "kunci": bool(k.tetap)})
    return sorted(out, key=lambda r: (r["hari"], r["mulai"], r["kurikulum"], r["kode_mk"], r["kelas"]))


def tulis_csv(path: Path, rows: list[dict]) -> None:
    """Semicolon CSV with BOM (opens in Excel); the site reads kelas_id, hari, mulai, selesai."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KOLOM_IMPOR, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def tulis_excel(path: Path, m: Masukan, rows: list[dict], cek: dict[str, list[str]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Jadwal"
    kepala = ["Hari", "Mulai", "Selesai", "Kurikulum", "Kode", "Mata kuliah", "Kelas", "sks", "Semester", "Dosen", "Dikunci"]
    ws.append(kepala)
    for r in rows:
        ws.append([r["nama_hari"], r["mulai"], r["selesai"], r["kurikulum"], r["kode_mk"], r["nama_mk"], r["kelas"],
                   float(r["sks"]), r["semester_paket"], r["dosen"], "ya" if r["kunci"] else ""])
    for c, lebar in zip("ABCDEFGHIJK", (9, 7, 8, 10, 10, 38, 7, 5, 10, 48, 8)):
        ws.column_dimensions[c].width = lebar
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"

    # Grid per day: rows = slots, columns = days, cell = classes running in that slot.
    g = wb.create_sheet("Per hari")
    g.append(["Jam"] + [HARI[h] for h in m.hari])
    biru = PatternFill("solid", fgColor="DCE7F5")
    for s in m.slot:
        isi = []
        for h in m.hari:
            xs = [f"{r['kode_mk']} {r['kelas']}" for r in rows if r["hari"] == h and r["mulai"] <= jam(s.mulai) < r["selesai"]]
            isi.append("\n".join(xs))
        g.append([f"{jam(s.mulai)}-{jam(s.selesai)}"] + isi)
    for row in g.iter_rows(min_row=2):
        for c in row[1:]:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if c.value:
                c.fill = biru
    g.column_dimensions["A"].width = 12
    for i in range(len(m.hari)):
        g.column_dimensions[chr(ord("B") + i)].width = 22
    for c in g[1]:
        c.font = Font(bold=True)

    d = wb.create_sheet("Per dosen")
    d.append(["Dosen", "Hari", "Mulai", "Selesai", "Kode", "Mata kuliah", "Kelas"])
    per = []
    kelas = {k.id: k for k in m.kelas}
    for r in rows:
        for dosen in kelas[r["kelas_id"]].dosen:
            per.append([m.nama_dosen(dosen), r["nama_hari"], r["mulai"], r["selesai"], r["kode_mk"], r["nama_mk"], r["kelas"], r["hari"]])
    for x in sorted(per, key=lambda t: (t[0], t[7], t[2])):
        d.append(x[:7])
    for c, lebar in zip("ABCDEFG", (40, 9, 7, 8, 10, 38, 7)):
        d.column_dimensions[c].width = lebar
    for c in d[1]:
        c.font = Font(bold=True)

    n = wb.create_sheet("Catatan")
    n.append(["Jenis", "Catatan"])
    for jenis, xs in (("wajib", cek["wajib"]), ("anjuran", cek["anjuran"])):
        for x in xs:
            n.append([jenis, x])
    if n.max_row == 1:
        n.append(["-", "Tidak ada pelanggaran wajib maupun anjuran."])
    n.column_dimensions["A"].width = 10
    n.column_dimensions["B"].width = 110
    wb.save(path)


def laporan(m: Masukan, a: Aturan, h: Hasil, cek: dict[str, list[str]] | None, peringatan: list[str],
            saran: list[str]) -> str:
    out = [f"Jadwal kuliah {m.semester} {m.tahun_akademik}", "",
           f"Kelas: {len(m.kelas)} ({sum(1 for k in m.kelas if k.tetap)} dikunci di situs) · hari {', '.join(HARI[x] for x in m.hari)}"
           f" · {len(m.slot)} slot {m.slot[0].selesai - m.slot[0].mulai} menit ({jam(m.slot[0].mulai)}-{jam(m.slot[-1].selesai)})", "",
           "Aturan:", *[f"  {x}" for x in ringkas(a)], "",
           f"Hasil: {h.status} — {h.pesan}"]
    if h.tanpa_pilihan:
        out += ["", "Kelas tanpa posisi sah:", *[f"  - {x}" for x in h.tanpa_pilihan]]
    if saran:
        out += ["", "Kemungkinan penyebab (beban lebih dari 60% slot bebas):", *[f"  - {x}" for x in saran]]
    if cek is not None:
        out += ["", f"Pelanggaran wajib: {len(cek['wajib'])}", *[f"  - {x}" for x in cek["wajib"]],
                "", f"Pelanggaran anjuran: {len(cek['anjuran'])}", *[f"  - {x}" for x in cek["anjuran"]]]
    if peringatan:
        out += ["", "Peringatan masukan:", *[f"  - {x}" for x in peringatan]]
    return "\n".join(out) + "\n"
