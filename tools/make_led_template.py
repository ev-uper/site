#!/usr/bin/env python3
"""Build site/led-template.docx: our own LED template (owner 2026-11-04).

    python tools/make_led_template.py            -> site/led-template.docx

Follows the structure of the LAM Teknik LED template (cover, identity,
compilers, foreword, summary, contents, BAB I-IV, attachments; C.1-C.7 with
their sub-items) but with clean Word styles: Heading 1-7 with automatic
multilevel numbering (A. / C.1 / 1. / a) / i. / I.), a table of contents
field, LAM guidance in a grey "Petunjuk" box, roman page numbers for the
front matter and arabic from BAB I.

The outline (headings, LAM guidance, "disampaikan oleh pengusul" notes) is
data in tools/led_outline.json, transcribed from the LAM template. Heading
and guidance texts are the anchors site/led.js looks for when it fills the
draft, so change them there too if you change them here.

Standard library only.
"""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

AKAR = Path(__file__).resolve().parents[1]
KERANGKA = AKAR / "tools" / "led_outline.json"
KELUAR = AKAR / "site" / "led-template.docx"

# Page: A4 portrait; text width 9360 twip (site/led.js LEBAR uses it).
HALAMAN = dict(w=11906, h=16838, top=1418, bottom=1418, left=1440, right=1106, header=709, footer=709)
FONT = "Calibri"
NAVY, AKSEN, ABU, TEKS = "1F3864", "2E75B6", "7F7F7F", "262626"
PETUNJUK_ISI, PETUNJUK_GARIS = "F3F6FA", "9DB4D3"
LEBAR_TEKS = HALAMAN["w"] - HALAMAN["left"] - HALAMAN["right"]

W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')

# A LAM note applies to a Sarjana programme when it names "semua program"
# or "Sarjana" (not only "Sarjana Terapan").
BERLAKU = re.compile(r"semua program|\bSarjana\b(?!\s*Terapan)", re.I)


def x(t: str) -> str:
    return escape(t, {'"': "&quot;"})


# ------------------------------------------------------------------ runs
def r(t: str, b=False, i=False, sz=None, warna=None, caps=False) -> str:
    pr = ("<w:b/>" if b else "") + ("<w:i/>" if i else "") + ("<w:caps/>" if caps else "") + \
         (f'<w:color w:val="{warna}"/>' if warna else "") + \
         (f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>' if sz else "")
    return f'<w:r>{f"<w:rPr>{pr}</w:rPr>" if pr else ""}<w:t xml:space="preserve">{x(t)}</w:t></w:r>'


def p(isi: str = "", gaya: str | None = None, jc=None, before=None, after=None, extra="") -> str:
    pr = (f'<w:pStyle w:val="{gaya}"/>' if gaya else "") + extra + \
         (f'<w:spacing w:before="{before if before is not None else 0}" w:after="{after if after is not None else 0}"/>'
          if before is not None or after is not None else "") + \
         (f'<w:jc w:val="{jc}"/>' if jc else "")
    return f'<w:p>{f"<w:pPr>{pr}</w:pPr>" if pr else ""}{isi}</w:p>'


def judul(t: str, tingkat: int, nomor: bool = True, alt: bool = False, label: str | None = None) -> str:
    """Heading paragraph; numbering comes from the style (numId 1) unless
    alt (BAB III 1) 2) 3), numId 2) or a literal label (numId 0)."""
    num = ""
    if alt:
        num = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/></w:numPr>'
    elif label or not nomor:
        num = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr><w:ind w:left="0" w:firstLine="0"/>'
    teks = f"{label} {t}" if label else t
    return p(r(teks), f"Heading{tingkat}", extra=num)


def halaman_baru() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def sel(isi: str, w: int, fill=None, span=1, vmerge=None, valign=None) -> str:
    pr = f'<w:tcW w:w="{w}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{span}"/>' if span > 1 else "") + \
         ({"mulai": '<w:vMerge w:val="restart"/>', "lanjut": "<w:vMerge/>"}.get(vmerge, "")) + \
         (f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else "") + \
         (f'<w:vAlign w:val="{valign}"/>' if valign else "")
    return f"<w:tc><w:tcPr>{pr}</w:tcPr>{isi or p()}</w:tc>"


def tabel(lebar: list[int], baris: list[str], garis=True, header_rows=0) -> str:
    g = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="8EA9C8"/>'
                for s in ("top", "left", "bottom", "right", "insideH", "insideV")) if garis else \
        "".join(f'<w:{s} w:val="nil"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    rows = []
    for k, b in enumerate(baris):
        hdr = "<w:trPr><w:tblHeader/></w:trPr>" if k < header_rows else ""
        rows.append(f"<w:tr>{hdr}{b}</w:tr>")
    grid = "".join('<w:gridCol w:w="%d"/>' % w for w in lebar)
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{sum(lebar)}" w:type="dxa"/><w:tblBorders>{g}</w:tblBorders>'
            '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
            '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid>{"".join(rows)}</w:tbl>')


def ps(t: str, b=False, jc=None, sz=19, warna=None) -> str:
    """Paragraph inside a table cell."""
    return p(r(t, b=b, sz=sz, warna=warna), "Tabel", jc=jc)


KEPALA = "DCE6F1"


# --------------------------------------------------------- front matter
def sampul() -> str:
    garis = lambda pos: (f'<w:pBdr><w:{pos} w:val="single" w:sz="24" w:space="6" w:color="{NAVY}"/></w:pBdr>')
    out = [
        p(r("LAPORAN EVALUASI DIRI", b=True, sz=22, warna=AKSEN), jc="center", before=600, after=0),
        p(r("Halaman Muka", sz=18, warna=ABU), jc="center", after=600),
        p(r("Logo Perguruan Tinggi", i=True, warna=ABU), "KotakLogo", jc="center"),
        p(r("LAPORAN EVALUASI DIRI PROGRAM STUDI", b=True), "JudulSampul", extra=garis("top")),
        p(r("AKREDITASI PROGRAM STUDI", b=True), "JudulSampul2"),
        p(r("PROGRAM DAN NAMA PROGRAM STUDI", b=True), "IsiSampul", before=480),
        p(r("UNIVERSITAS/ INSTITUT/ SEKOLAH TINGGI/ POLITEKNIK/ AKADEMI/ AKADEMI KOMUNITAS", b=True), "IsiSampul"),
        p(r("....................................................."), "IsiSampul"),
        p(r("NAMA KOTA KEDUDUKAN PERGURUAN TINGGI", b=True), "IsiSampul", before=480),
        p(r("TAHUN ................", b=True), "IsiSampul", extra=garis("bottom")),
        p(r("Catatan: Kelengkapan isian setiap kriteria mengacu pada Pedoman Penyusunan Laporan Evaluasi Diri "
            "Program Studi", i=True, sz=18, warna=ABU), jc="center", before=1200),
    ]
    return "".join(out)


IDENTITAS = [
    "Perguruan Tinggi", "Unit Pengelola Program Studi", "Jenis Program", "Nama Program Studi", "Alamat",
    "Nomor Telepon", "E-Mail dan Website", "Nomor SK Pendirian PT 1)", "Tanggal SK Pendirian PT",
    "Pejabat Penandatangan SK Pendirian PT", "Nomor SK Pembukaan PS 2)", "Tanggal SK Pembukaan PS",
    "Pejabat Penandatangan SK Pembukaan PS", "Tahun Pertama Kali Menerima Mahasiswa",
    "Peringkat Terbaru Akreditasi PS", "Nomor SK Akreditasi Terakhir 3)",
]


def identitas() -> str:
    lb = [3600, 300, LEBAR_TEKS - 3900]
    baris = [sel(ps(k, b=True), lb[0]) + sel(ps(":"), lb[1]) + sel(ps(""), lb[2]) for k in IDENTITAS]
    out = [judul("IDENTITAS PENGUSUL", 1),
           tabel(lb, baris, garis=False),
           p(r("Daftar Program Studi di Unit Pengelola Program Studi (UPPS)", b=True), "Keterangan", before=240)]
    w = [560, 1250, 1900, 1200, 1500, 1500, LEBAR_TEKS - 7910]
    h1 = (sel(ps("No.", True, "center"), w[0], KEPALA, vmerge="mulai", valign="center") +
          sel(ps("Jenis Program", True, "center"), w[1], KEPALA, vmerge="mulai", valign="center") +
          sel(ps("Nama Program Studi", True, "center"), w[2], KEPALA, vmerge="mulai", valign="center") +
          sel(ps("Akreditasi Program Studi", True, "center"), w[3] + w[4] + w[5], KEPALA, span=3) +
          sel(ps("Jumlah mahasiswa saat TS 4)", True, "center"), w[6], KEPALA, vmerge="mulai", valign="center"))
    h2 = (sel("", w[0], KEPALA, vmerge="lanjut") + sel("", w[1], KEPALA, vmerge="lanjut") +
          sel("", w[2], KEPALA, vmerge="lanjut") + sel(ps("Status/ Peringkat", True, "center"), w[3], KEPALA) +
          sel(ps("No. dan Tgl. SK", True, "center"), w[4], KEPALA) +
          sel(ps("Tgl. Kedaluwarsa", True, "center"), w[5], KEPALA) + sel("", w[6], KEPALA, vmerge="lanjut"))
    h3 = "".join(sel(ps(str(i + 1), jc="center", sz=16, warna=ABU), w[i], "F2F2F2") for i in range(7))
    isi = ["".join(sel(ps(n if k == 0 else "", jc="center" if k == 0 else None), w[k]) for k in range(7))
           for n in ("1", "2", "...")]
    jml = sel(ps("Jumlah", True, "center"), w[0] + w[1], span=2) + "".join(sel("", w[k]) for k in range(2, 7))
    out.append(tabel(w, [h1, h2, h3, *isi, jml], header_rows=3))
    out.append(p(r("Keterangan:", b=True, sz=18), "Keterangan", before=120))
    for t in ("1) Lampirkan salinan Surat Keputusan Pendirian Perguruan Tinggi.",
              "2) Lampirkan salinan Surat Keputusan Pembukaan Program Studi.",
              "3) Lampirkan salinan Surat Keputusan Akreditasi Program Studi terbaru.",
              "4) Diisi dengan jumlah mahasiswa aktif di masing-masing PS saat TS."):
        out.append(p(r(t, sz=18), "Keterangan"))
    return "".join(out)


def tim_penyusun() -> str:
    out = [halaman_baru(), judul("IDENTITAS TIM PENYUSUN", 1),
           p(r("LAPORAN EVALUASI DIRI PROGRAM STUDI", b=True, warna=NAVY), jc="center", after=240)]
    lb = [2200, 300, 4060, 2800]
    for n in range(1, 5):
        baris = []
        for k, label in enumerate(("Nama", "NIDN / NUPTK", "Jabatan", "Tanggal Pengisian")):
            nilai = "DD – MM – YYYY" if label == "Tanggal Pengisian" else ""
            ttd = sel(ps("Tanda Tangan:", sz=17, warna=ABU), lb[3], vmerge="mulai") if k == 0 else \
                sel("", lb[3], vmerge="lanjut")
            baris.append(sel(ps(label, b=True), lb[0], "F7F9FC") + sel(ps(":"), lb[1], "F7F9FC") +
                         sel(ps(nilai, warna=ABU if nilai else None), lb[2]) + ttd)
        out.append(p(r(f"Penyusun {n}", b=True, sz=18, warna=AKSEN), before=160, after=60))
        out.append(tabel(lb, baris))
    return "".join(out)


def bagian_isian(t: str, catatan: str) -> str:
    return halaman_baru() + judul(t, 1) + kotak([("n", catatan)])


def daftar_isi() -> str:
    return (halaman_baru() + judul("DAFTAR ISI", 1) +
            '<w:p><w:pPr><w:pStyle w:val="TOC1"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9350"/></w:tabs></w:pPr>'
            '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-4" \\h \\z \\u </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            f'{r("Klik kanan di sini lalu pilih Update Field (Perbarui Bidang) untuk menampilkan daftar isi.", i=True, warna=ABU)}'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


# ------------------------------------------------------------- body
def kotak(isi: list[tuple[str, str]], na: bool = False) -> str:
    """LAM guidance (p) and notes (n) as one grey box."""
    out = []
    for k, t in isi:
        out.append(p(r(t), "Petunjuk" if k == "p" else "PetunjukCatatan"))
    if na:
        out.append(p(r("Tidak berlaku untuk program Sarjana.", b=True), "PetunjukTidakBerlaku"))
    return "".join(out)


def tabel_tim(no: str, judul_t: str, kolom: list[str]) -> str:
    w = [600, 2400, 1900, 1900, LEBAR_TEKS - 6800]
    h = "".join(sel(ps(c, True, "center"), w[k], KEPALA, valign="center") for k, c in enumerate(kolom))
    isi = ["".join(sel(ps(n if k == 0 else "", jc="center" if k == 0 else None), w[k]) for k in range(5))
           for n in ("1", "2", "...")]
    return p(r(f"Tabel {no}. ", b=True) + r(judul_t), "Keterangan", before=160) + tabel(w, [h, *isi], header_rows=1)


def isi_utama(kerangka: list[dict]) -> str:
    out: list[str] = []
    antre: list[tuple[str, str]] = []

    def kosongkan():
        if not antre:
            return
        # One box per guidance+note group; a group whose note excludes
        # Sarjana is marked.
        grup: list[tuple[str, str]] = []
        for k, t in antre:
            grup.append((k, t))
            if k == "n":
                out.append(kotak(grup, na=not BERLAKU.search(t)))
                grup = []
        if grup:
            out.append(kotak(grup))
        antre.clear()

    pertama = True
    for e in kerangka:
        if e["k"] in ("p", "n"):
            antre.append((e["k"], e["t"]))
            continue
        kosongkan()
        if e["k"] == "tabel":
            no, t = re.match(r"Tabel (2\.\d)\.?\s*(.*?)\.?$", e["t"]).groups()
            kol = (["No.", "Nama Dosen", "NIP / NIDN / NUPTK", "Jabatan Dosen", "Deskripsi Kerja"] if no == "2.1" else
                   ["No.", "Nama Tenaga Kependidikan", "NIP / NUPTK", "Jabatan Tenaga Kependidikan", "Deskripsi Kerja"])
            out.append(tabel_tim(no, t, kol))
            continue
        if e["lvl"] == 1:
            if not pertama:
                out.append(halaman_baru())
            pertama = False
        out.append(judul(e["t"], e["lvl"], alt=e.get("alt", False), label=e.get("label")))
    kosongkan()
    return "".join(out)


# ---------------------------------------------------------- sections
def sect(jenis: str) -> str:
    h = HALAMAN
    ref = {"sampul": "", "depan": '<w:footerReference w:type="default" r:id="rIdFooterDepan"/>',
           "isi": '<w:headerReference w:type="default" r:id="rIdHeaderIsi"/>'
                  '<w:footerReference w:type="default" r:id="rIdFooterIsi"/>'}[jenis]
    nomor = {"sampul": "", "depan": '<w:pgNumType w:fmt="lowerRoman" w:start="1"/>',
             "isi": '<w:pgNumType w:fmt="decimal" w:start="1"/>'}[jenis]
    return (f'<w:sectPr>{ref}<w:type w:val="nextPage"/><w:pgSz w:w="{h["w"]}" w:h="{h["h"]}"/>'
            f'<w:pgMar w:top="{h["top"]}" w:right="{h["right"]}" w:bottom="{h["bottom"]}" w:left="{h["left"]}" '
            f'w:header="{h["header"]}" w:footer="{h["footer"]}" w:gutter="0"/>{nomor}'
            '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>')


def akhir_bagian(jenis: str) -> str:
    return f"<w:p><w:pPr>{sect(jenis)}</w:pPr></w:p>"


def dokumen(kerangka: list[dict]) -> str:
    body = (sampul() + akhir_bagian("sampul") +
            identitas() + tim_penyusun() +
            bagian_isian("KATA PENGANTAR", "(Diisi oleh pengusul dari program studi untuk semua program).") +
            bagian_isian("RINGKASAN EKSEKUTIF", "(Diisi oleh pengusul dari program studi untuk semua program).") +
            daftar_isi() + akhir_bagian("depan") +
            isi_utama(kerangka) + sect("isi"))
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W_NS}><w:body>{body}</w:body></w:document>'


def nomor_halaman() -> str:
    return ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>')


def kaki() -> str:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {W_NS}>'
            f'<w:p><w:pPr><w:pStyle w:val="Footer"/><w:jc w:val="center"/></w:pPr>{nomor_halaman()}</w:p></w:ftr>')


def kepala() -> str:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr {W_NS}>'
            f'<w:p><w:pPr><w:pStyle w:val="Header"/></w:pPr>{r("Laporan Evaluasi Diri Program Studi")}</w:p></w:hdr>')


# ------------------------------------------------------------ styles
def gaya_p(sid, nama, rpr="", ppr="", basis="Normal", berikut="Normal", ui=None, kunci=False) -> str:
    khusus = ' w:customStyle="1"' if kunci else ""
    prio = '<w:uiPriority w:val="%d"/>' % ui if ui is not None else ""
    return (f'<w:style w:type="paragraph" w:styleId="{sid}"{khusus}>'
            f'<w:name w:val="{nama}"/><w:basedOn w:val="{basis}"/><w:next w:val="{berikut}"/>'
            f'{prio}<w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>')


def rp(sz=None, b=False, i=False, warna=None, caps=False) -> str:
    return (("<w:b/><w:bCs/>" if b else "") + ("<w:i/><w:iCs/>" if i else "") + ("<w:caps/>" if caps else "") +
            (f'<w:color w:val="{warna}"/>' if warna else "") + (f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>' if sz else ""))


def gaya() -> str:
    kotak_pbdr = (f'<w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="{PETUNJUK_GARIS}"/></w:pBdr>'
                  f'<w:shd w:val="clear" w:color="auto" w:fill="{PETUNJUK_ISI}"/><w:ind w:left="170" w:right="0"/>')
    judul_ = lambda lvl, before, after, extra="": (
        f'<w:keepNext/><w:keepLines/>{extra}<w:spacing w:before="{before}" w:after="{after}"/>'
        f'<w:jc w:val="left"/><w:outlineLvl w:val="{lvl}"/>')
    num = lambda lvl: f'<w:numPr><w:ilvl w:val="{lvl}"/><w:numId w:val="1"/></w:numPr>'
    s = [
        f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}" w:cs="{FONT}"/>'
        f'<w:color w:val="{TEKS}"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="id-ID" w:eastAsia="en-US" w:bidi="ar-SA"/>'
        '</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/>'
        '</w:pPr></w:pPrDefault></w:docDefaults>',
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:jc w:val="both"/></w:pPr></w:style>',
        '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/>'
        '<w:uiPriority w:val="1"/><w:semiHidden/></w:style>',
        '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:semiHidden/>'
        '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>',
        '<w:style w:type="numbering" w:default="1" w:styleId="NoList"><w:name w:val="No List"/><w:semiHidden/></w:style>',
        gaya_p("Heading1", "heading 1", rp(30, True, warna=NAVY, caps=True),
               judul_(0, 0, 360, f'<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="6" w:color="{AKSEN}"/></w:pBdr>'
                      f'{num(0)}').replace('<w:jc w:val="left"/>', '<w:jc w:val="center"/>'), ui=9),
        gaya_p("Heading2", "heading 2", rp(26, True, warna=NAVY),
               num(1) + judul_(1, 360, 160) + '<w:ind w:left="454" w:hanging="454"/>', ui=9),
        gaya_p("Heading3", "heading 3", rp(25, True, warna="FFFFFF"),
               num(2) + judul_(2, 360, 200) + f'<w:shd w:val="clear" w:color="auto" w:fill="{NAVY}"/>'
               '<w:ind w:left="680" w:hanging="680"/>', ui=9),
        gaya_p("Heading4", "heading 4", rp(23, True, warna=AKSEN),
               num(3) + judul_(3, 280, 120) + '<w:ind w:left="397" w:hanging="397"/>', ui=9),
        gaya_p("Heading5", "heading 5", rp(22, True, warna=NAVY),
               num(4) + judul_(4, 220, 100) + '<w:ind w:left="397" w:hanging="397"/>', ui=9),
        gaya_p("Heading6", "heading 6", rp(22, True, warna=TEKS),
               num(5) + judul_(5, 200, 80) + '<w:ind w:left="454" w:hanging="454"/>', ui=9),
        gaya_p("Heading7", "heading 7", rp(22, True, True, warna=TEKS),
               num(6) + judul_(6, 160, 80) + '<w:ind w:left="454" w:hanging="454"/>', ui=9),
        gaya_p("Petunjuk", "Petunjuk LAM", rp(19, warna="404040"),
               kotak_pbdr + '<w:spacing w:before="0" w:after="0" w:line="252" w:lineRule="auto"/>', kunci=True),
        gaya_p("PetunjukCatatan", "Petunjuk LAM - catatan", rp(17, i=True, warna=ABU),
               kotak_pbdr + '<w:spacing w:before="0" w:after="160"/>', basis="Petunjuk", kunci=True),
        gaya_p("PetunjukTidakBerlaku", "Petunjuk LAM - tidak berlaku", rp(17, True, warna="C00000"),
               kotak_pbdr + '<w:spacing w:before="0" w:after="160"/>', basis="Petunjuk", kunci=True),
        gaya_p("Keterangan", "Keterangan", rp(19), '<w:spacing w:before="0" w:after="60"/><w:jc w:val="left"/>', kunci=True),
        gaya_p("Tabel", "Isi tabel", rp(19), '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
               '<w:jc w:val="left"/>', kunci=True),
        gaya_p("JudulSampul", "Judul sampul", rp(40, True, warna=NAVY),
               '<w:spacing w:before="600" w:after="60"/><w:jc w:val="center"/>', kunci=True),
        gaya_p("JudulSampul2", "Judul sampul 2", rp(28, True, warna=AKSEN),
               '<w:spacing w:before="0" w:after="240"/><w:jc w:val="center"/>', kunci=True),
        gaya_p("IsiSampul", "Isi sampul", rp(26, warna=NAVY),
               '<w:spacing w:before="0" w:after="80"/><w:jc w:val="center"/>', kunci=True),
        gaya_p("KotakLogo", "Kotak logo", rp(20),
               '<w:pBdr><w:top w:val="dashed" w:sz="6" w:space="24" w:color="A6A6A6"/>'
               '<w:left w:val="dashed" w:sz="6" w:space="24" w:color="A6A6A6"/>'
               '<w:bottom w:val="dashed" w:sz="6" w:space="24" w:color="A6A6A6"/>'
               '<w:right w:val="dashed" w:sz="6" w:space="24" w:color="A6A6A6"/></w:pBdr>'
               '<w:spacing w:before="480" w:after="480"/><w:ind w:left="3100" w:right="3100"/><w:jc w:val="center"/>',
               kunci=True),
        gaya_p("Header", "header", rp(16, warna=ABU),
               f'<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="4" w:color="{PETUNJUK_GARIS}"/></w:pBdr>'
               '<w:spacing w:after="0"/><w:jc w:val="right"/>', ui=99),
        gaya_p("Footer", "footer", rp(18, warna=ABU), '<w:spacing w:after="0"/><w:jc w:val="center"/>', ui=99),
        gaya_p("TOCHeading", "TOC Heading", rp(30, True, warna=NAVY), '<w:jc w:val="center"/>', basis="Heading1", ui=39),
    ]
    for n, (ind, b, before) in enumerate([(0, True, 120), (220, False, 40), (440, False, 20), (660, False, 0)], 1):
        s.append(gaya_p(f"TOC{n}", f"toc {n}", rp(21 if n > 1 else 22, b, warna=NAVY if n == 1 else None),
                        f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{LEBAR_TEKS - 10}"/></w:tabs>'
                        f'<w:spacing w:before="{before}" w:after="40"/><w:ind w:left="{ind}"/><w:jc w:val="left"/>', ui=39))
    s.append('<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:basedOn w:val="DefaultParagraphFont"/>'
             f'<w:uiPriority w:val="99"/><w:rPr><w:color w:val="{AKSEN}"/><w:u w:val="single"/></w:rPr></w:style>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:styles {W_NS}>{"".join(s)}</w:styles>')


def penomoran() -> str:
    def lvl(i, fmt, teks, gaya_id, ind=0, hanging=0):
        ps_ = '<w:pStyle w:val="%s"/>' % gaya_id if gaya_id else ""
        return (f'<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/>'
                f'{ps_}<w:lvlText w:val="{teks}"/><w:lvlJc w:val="left"/>'
                f'<w:pPr><w:ind w:left="{ind}" w:hanging="{hanging}"/></w:pPr></w:lvl>')
    a1 = ('<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="multilevel"/>' +
          lvl(0, "none", "", "Heading1") + lvl(1, "upperLetter", "%2.", "Heading2", 454, 454) +
          lvl(2, "decimal", "%2.%3", "Heading3", 680, 680) + lvl(3, "decimal", "%4.", "Heading4", 397, 397) +
          lvl(4, "lowerLetter", "%5)", "Heading5", 397, 397) + lvl(5, "lowerRoman", "%6.", "Heading6", 454, 454) +
          lvl(6, "upperRoman", "%7.", "Heading7", 454, 454) +
          "".join(lvl(i, "decimal", f"%{i + 1}.", None) for i in (7, 8)) + "</w:abstractNum>")
    a2 = ('<w:abstractNum w:abstractNumId="2"><w:multiLevelType w:val="singleLevel"/>' +
          lvl(0, "decimal", "%1)", None, 454, 454) + "</w:abstractNum>")
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:numbering {W_NS}>{a1}{a2}'
            '<w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num><w:num w:numId="2"><w:abstractNumId w:val="2"/></w:num>'
            '</w:numbering>')


# ---------------------------------------------------------- package
def paket(doc: str) -> dict[str, str]:
    kini = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             f'<Relationship Id="rIdStyles" Type="{RT}styles" Target="styles.xml"/>'
             f'<Relationship Id="rIdNumbering" Type="{RT}numbering" Target="numbering.xml"/>'
             f'<Relationship Id="rIdSettings" Type="{RT}settings" Target="settings.xml"/>'
             f'<Relationship Id="rIdHeaderIsi" Type="{RT}header" Target="header1.xml"/>'
             f'<Relationship Id="rIdFooterDepan" Type="{RT}footer" Target="footer1.xml"/>'
             f'<Relationship Id="rIdFooterIsi" Type="{RT}footer" Target="footer2.xml"/>'
             '</Relationships>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings {W_NS}>'
                '<w:defaultTabStop w:val="720"/><w:characterSpacingControl w:val="doNotCompress"/>'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
                '</w:settings>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>Laporan Evaluasi Diri Program Studi</dc:title><dc:creator>cv-prodi</dc:creator>'
            '<cp:lastModifiedBy>cv-prodi</cp:lastModifiedBy>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{kini}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{kini}</dcterms:modified></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           '<Application>cv-prodi make_led_template.py</Application></Properties>')
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/_rels/document.xml.rels": drels,
            "word/document.xml": doc, "word/styles.xml": gaya(), "word/numbering.xml": penomoran(),
            "word/settings.xml": settings, "word/header1.xml": kepala(), "word/footer1.xml": kaki(),
            "word/footer2.xml": kaki(), "docProps/core.xml": core, "docProps/app.xml": app}


def main() -> None:
    kerangka = json.loads(KERANGKA.read_text(encoding="utf-8"))
    bagian = paket(dokumen(kerangka))
    tmp = KELUAR.with_suffix(".docx.new")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for nama in ["[Content_Types].xml", *[n for n in bagian if n != "[Content_Types].xml"]]:
            info = zipfile.ZipInfo(nama, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, bagian[nama].encode("utf-8"))
    tmp.replace(KELUAR)
    n = {k: sum(e["k"] == k for e in kerangka) for k in ("h", "p", "n")}
    print(f"{KELUAR.relative_to(AKAR)}: {n['h']} judul, {n['p']} petunjuk, {n['n']} catatan, "
          f"{KELUAR.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
