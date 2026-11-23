"""Static public pages written at build time (owner 2026-11-16): one page per lecturer
(dosen/<slug>.html), sitemap.xml and robots.txt, from the same public dict as data.json.

Why static: search engines index text present in the HTML; the interactive pages build
their text with JavaScript after loading data.json. Called by bangun.py after data.json
is written. Only files carrying GENERATOR are ever replaced or removed in dosen/.
"""
from __future__ import annotations

import html
import json
import posixpath
import re
from pathlib import Path

GENERATOR = "bangun.py halaman_publik"
SINTA = "https://sinta.kemdiktisaintek.go.id/authors/profile/"
SCOPUS = "https://www.scopus.com/pages/authors/"
ORCID = "https://orcid.org/"
# Public pages listed in sitemap.xml besides the lecturer pages; module -> page per site/fitur.js.
HALAMAN = [("", None), ("profil-prodi.html", None), ("kurikulum.html", None), ("layanan-mahasiswa.html", None), ("kinerja.html", None), ("prestasi.html", None), ("kabar.html", None), ("galeri.html", None), ("biaya-beasiswa.html", None), ("tugas-akhir.html", None), ("kontak.html", None), ("laboratorium.html", None),
           ("daftar.html?jenis=dosen", None), ("daftar.html?jenis=publikasi", None),
           ("daftar.html?jenis=penelitian", None), ("daftar.html?jenis=pkm", None),
           ("kerja-sama.html", None), ("alumni.html", None), ("calon-mahasiswa.html", None), ("ekuivalensi-kurikulum.html", None), ("keahlian.html", "kepakaran"), ("sdgs.html", "sdgs"),
           ("kerja-praktik.html", None), ("pengajuan.html", None), ("hasil-survei.html", None),
           ("privasi.html", None), ("peta-situs.html", None), ("english.html", None)]
LOGO = [("logo-up.webp", "Universitas", 271, 200), ("logo-dekade.webp", "1 Dekade", 271, 200),
        ("logo-diktisaintek.webp", "Diktisaintek Berdampak", 397, 136)]
TINGKAT = {"internasional": "Internasional", "nasional": "Nasional", "wilayah_lokal": "Wilayah/lokal",
           "wilayah": "Wilayah", "lokal": "Lokal"}

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def versi_aset(site: Path) -> str:
    """Asset version stamp of the current build (stamp_versions.py writes ?v= into site/index.html)."""
    m = re.search(r"tema\.css\?v=([0-9A-Za-z-]+)", (site / "index.html").read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def fitur_mati(site: Path) -> set[str]:
    """Modules switched off in site/config.js (window.FITUR_MATI), so their pages stay out of the sitemap."""
    p = site / "config.js"
    m = re.search(r"FITUR_MATI\s*=\s*\[([^\]]*)\]", p.read_text(encoding="utf-8")) if p.is_file() else None
    return set(re.findall(r"['\"]([a-z_]+)['\"]", m.group(1))) if m else set()


def _punya(daftar, slug: str) -> bool:
    return any(isinstance(a, dict) and a.get("slug") == slug for a in daftar or [])


def _penulis(daftar, slug: str) -> str:
    out = []
    for a in daftar or []:
        nama = a.get("nama") if isinstance(a, dict) else a
        if not nama:
            continue
        if isinstance(a, dict) and a.get("slug") == slug:
            out.append(f"<b>{e(nama)}</b>")
        elif isinstance(a, dict) and a.get("slug"):
            out.append(f'<a href="{e(a["slug"])}.html">{e(nama)}</a>')
        else:
            out.append(e(nama))
    return ", ".join(out)


def _rinci_terbitan(p: dict) -> str:
    bag = [f"<i>{e(p['terbitan'])}</i>" if p.get("terbitan") else ""]
    if p.get("volume"):
        bag.append(f"Vol. {e(p['volume'])}" + (f" No. {e(p['nomor'])}" if p.get("nomor") else ""))
    if p.get("halaman"):
        bag.append(f"hlm. {e(p['halaman'])}")
    return ", ".join(b for b in bag if b)


def _topik(dosen: dict, baku: dict | None) -> list[str]:
    nama = {t["kode"]: t["nama"] for t in (baku or {}).get("topik", [])}
    return [nama[k] for k in dosen.get("topik_keahlian") or [] if k in nama]


def nama_dosen(D: dict, o: dict) -> str:
    """Name shown for a lecturer on public pages: nama_gelar (patch 111) when filled, else nama (owner 2026-11-19,
    2026-11-22: "tampilkan nama dengan gelar"). o = any dict with slug and/or nama (dosen, pembimbing, kepala, penulis)."""
    for d in D.get("dosen") or []:
        if d.get("nama_gelar") and ((o.get("slug") and d.get("slug") == o.get("slug")) or d.get("nama") == o.get("nama")):
            return d["nama_gelar"]
    return o.get("nama") or ""


def _bidang(dosen: dict, baku: dict | None) -> str:
    if dosen.get("bidang_keahlian"):
        return dosen["bidang_keahlian"]
    topik = {t["kode"]: t["bidang"] for t in (baku or {}).get("topik", [])}
    bidang = {b["kode"]: b["nama"] for b in (baku or {}).get("bidang", [])}
    kode = []
    for k in dosen.get("topik_keahlian") or []:
        if topik.get(k) and topik[k] not in kode:
            kode.append(topik[k])
    return " · ".join(bidang[k] for k in kode[:2] if k in bidang)


def rapi_indeks(v) -> str:
    """scopus_q3 -> Scopus Q3, sinta_2 -> SINTA 2 (stored codes of karya.indeksasi)."""
    nama = {"scopus": "Scopus", "sinta": "SINTA", "wos": "WoS", "doaj": "DOAJ", "garuda": "Garuda"}
    bag = str(v).split("_")
    return " ".join([nama.get(bag[0].lower(), bag[0].capitalize())] + [b.upper() for b in bag[1:]])


def inisial(nama: str) -> str:
    # Gelar belakang (setelah koma) dan gelar depan berakhiran titik (Dr., Ir., Prof.) tidak ikut.
    kata = [w for w in re.split(r"\s+", re.sub(r",.*$", "", nama)) if w[:1].isupper() and not w.endswith(".")]
    return "".join(w[0] for w in kata[:2]) or nama[:1].upper()


CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--biru-2)}
.lewati{position:absolute;left:-999px}.lewati:focus{left:8px;top:8px;background:#fff;padding:8px 12px;z-index:9}
.hero{background:var(--biru);color:#fff;border-bottom:4px solid var(--merah)}
.hero-in{max-width:1080px;margin:0 auto;padding:22px 20px 34px}
.atas{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.jejak{font-size:13px;color:var(--biru-m3);margin:14px 0 26px}
.jejak a{color:var(--biru-m3);text-decoration:none}.jejak a:hover{color:#fff;text-decoration:underline}
.profil{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
.avatar{width:112px;height:112px;border-radius:50%;flex:none;display:grid;place-items:center;background:#fff;color:var(--biru);
  font-family:var(--serif);font-size:40px;font-weight:700;box-shadow:0 0 0 5px rgba(255,255,255,.18)}
.avatar.foto{object-fit:cover;background:var(--biru-m8)}
.peran{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--biru-m2)}
h1{font-family:var(--serif);font-weight:700;font-size:clamp(28px,4.4vw,42px);line-height:1.1;margin:6px 0 8px;letter-spacing:-.01em}
.bidang{font-size:17px;color:var(--biru-m5)}
.bidang a{color:#fff;text-decoration:underline;text-underline-offset:3px}.bidang a:hover{color:var(--biru-m3)}
.tautan{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.tautan a{display:inline-flex;align-items:center;gap:6px;font-size:13.5px;font-weight:600;color:#fff;text-decoration:none;
  border:1px solid rgba(255,255,255,.45);padding:6px 12px;border-radius:2px}
.tautan a:hover{background:rgba(255,255,255,.12)}
.tautan a.utama{background:var(--aksen);border-color:var(--aksen);color:var(--biru-gelap)}
.angka{background:#fff;border-bottom:1px solid var(--line)}
.angka-in{max-width:1080px;margin:0 auto;display:grid;grid-template-columns:repeat(5,1fr)}
.angka div{padding:18px 20px;border-right:1px solid var(--line)}.angka div:last-child{border-right:0}
.angka b{display:block;font-family:var(--mono);font-size:28px;font-weight:400;color:var(--biru);line-height:1}
.angka span{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-top:8px}
main{max-width:1080px;margin:0 auto;padding:10px 20px 70px}
.topik{margin:28px 0 0}
.chip{display:inline-block;font-size:13px;padding:4px 10px;margin:0 6px 6px 0;border-radius:2px;background:var(--biru-m8);color:var(--biru)}
h2{font-family:var(--serif);font-size:24px;font-weight:700;color:var(--biru);margin:40px 0 4px;display:flex;align-items:baseline;gap:10px}
h2 small{font-family:var(--mono);font-size:12px;color:var(--muted);font-weight:400}
.garis{width:46px;height:3px;background:var(--aksen);margin:0 0 14px}
h3.tahun{font-family:var(--mono);font-size:12px;letter-spacing:.12em;color:var(--muted);margin:22px 0 4px;font-weight:500}
ol.karya{list-style:none;margin:0;padding:0}
ol.karya li{background:#fff;border:1px solid var(--line);border-left:3px solid var(--biru-3);padding:12px 16px;margin:8px 0;border-radius:2px}
ol.karya .judul{font-weight:600;color:var(--ink)}
ol.karya .judul a{color:var(--ink);text-decoration:none}ol.karya .judul a:hover{color:var(--biru-2);text-decoration:underline}
ol.karya .meta{font-size:13.5px;color:var(--muted);margin-top:3px}
ol.karya .meta a{color:var(--muted)}
.tag{display:inline-block;font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;padding:1px 6px;border-radius:2px;
  background:var(--biru-m8);color:var(--biru);margin-right:6px;vertical-align:1px}
.tag.int{background:var(--aksen);color:var(--biru-gelap)}
.tag.pkm{background:var(--merah-m3);color:var(--merah)}
.kosong{color:var(--muted);font-size:14px}
footer{background:var(--biru);color:var(--biru-m4);font-size:13.5px}
footer div{max-width:1080px;margin:0 auto;padding:26px 20px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
footer a{color:#fff;margin-right:14px}
@media (max-width:760px){.angka-in{grid-template-columns:repeat(3,1fr)}.angka div:nth-child(3){border-right:0}.avatar{width:84px;height:84px;font-size:30px}}
@media (max-width:420px){.angka-in{grid-template-columns:repeat(2,1fr)}.angka div{border-right:0}}
"""


def halaman_dosen(D: dict, dosen: dict, base_url: str, versi: str, logo: list | None = None) -> str:
    """Full HTML of one lecturer page; text is in the HTML, no script needed to read it."""
    slug, nama = dosen["slug"], dosen["nama"]
    tampil = dosen.get("nama_gelar") or nama   # nama dengan gelar bila diisi (pemilik 2026-11-19)
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    baku = D.get("keahlian_baku")
    bidang, topik = _bidang(dosen, baku), _topik(dosen, baku)
    # Kelompok keahlian dosen -> halaman bidang (pemilik 2026-11-22).
    kel = next((x for x in (D.get("situs") or {}).get("kelompok_keahlian") or [] if x.get("kode") == dosen.get("kelompok") and x.get("nama")), None)
    pub = sorted((p for p in D.get("publikasi", []) if _punya(p.get("penulis"), slug)),
                 key=lambda p: (-int(p.get("tahun") or 0), str(p.get("judul"))))
    keg = sorted((k for k in D.get("kegiatan", []) if _punya(k.get("penulis"), slug)),
                 key=lambda k: (-int(k.get("tahun") or 0), str(k.get("judul"))))
    rek = [r for r in D.get("rekognisi", []) if str(r.get("dosen") or "").strip() == nama]
    pres = sorted((x for x in D.get("prestasi", []) if any(b.get("slug") == slug for b in x.get("pembimbing", []))),
                  key=lambda x: (-int(x.get("tahun") or 0), str(x.get("kegiatan"))))
    lua = [l for l in D.get("luaran_dosen", []) if nama in (l.get("dosen") or [])]
    pen = [k for k in keg if k.get("kategori") == "penelitian"]
    pkm = [k for k in keg if k.get("kategori") == "pkm"]

    url = f"{base_url}/dosen/{slug}.html" if base_url else ""
    profil_luar = [(SINTA + dosen["sinta_id"], "SINTA") if dosen.get("sinta_id") else None,
                   (SCOPUS + dosen["scopus_id"], "Scopus") if dosen.get("scopus_id") else None,
                   (ORCID + dosen["orcid"], "ORCID") if dosen.get("orcid") else None]
    # Tautan lain dari Profil saya (patch 146, pemilik 2026-11-22), mis. laboratorium riset; hanya https.
    profil_luar += [(t["url"], t["label"]) for t in dosen.get("tautan") or []
                    if str(t.get("url") or "").startswith("https://") and t.get("label")]
    profil_luar = [x for x in profil_luar if x]
    ringkas = f"{nama}, dosen Program Studi {prodi}" + (f", {inst}" if inst else "") + "."
    if bidang:
        ringkas += f" Bidang: {bidang}."
    ringkas += f" {len(pub)} publikasi, {len(pen)} penelitian, {len(pkm)} pengabdian kepada masyarakat."
    ld = {"@context": "https://schema.org", "@type": "Person", "name": nama,
          "affiliation": {"@type": "Organization", "name": f"Program Studi {prodi}" + (f", {inst}" if inst else "")},
          **({"url": url} if url else {}), **({"knowsAbout": topik or [bidang]} if (topik or bidang) else {}),
          **({"sameAs": [u for u, _ in profil_luar]} if profil_luar else {})}

    def per_tahun(xs, baris):
        out, tahun = [], None
        for x in xs:
            if x.get("tahun") != tahun:
                if tahun is not None:
                    out.append("</ol>")
                tahun = x.get("tahun")
                out.append(f'<h3 class="tahun">{e(tahun)}</h3><ol class="karya">')
            out.append(baris(x))
        return "".join(out) + ("</ol>" if xs else "")

    def baris_pub(p):
        tautan = f"https://doi.org/{p['doi']}" if p.get("doi") else (p.get("url") or "")
        judul = f'<a href="{e(tautan)}" rel="noopener">{e(p["judul"])}</a>' if tautan else e(p["judul"])
        tag = f'<span class="tag{" int" if p.get("tingkat") == "internasional" else ""}">{e(TINGKAT.get(p.get("tingkat"), p.get("tingkat") or ""))}</span>' if p.get("tingkat") else ""
        idx = f' · {e(rapi_indeks(p["indeksasi"]))}' if p.get("indeksasi") else ""
        doi = f' · DOI {e(p["doi"])}' if p.get("doi") else ""
        terbit = _rinci_terbitan(p)
        return (f'<li><div class="judul">{tag}{judul}</div><div class="meta">{_penulis(p.get("penulis"), slug)}'
                f'{" · " + terbit if terbit else ""}{idx}{doi}</div></li>')

    def baris_keg(k):
        peran = next((a.get("peran") for a in k.get("penulis") or [] if isinstance(a, dict) and a.get("slug") == slug), "")
        mitra = ", ".join(m.get("nama", "") for m in k.get("mitra") or [] if isinstance(m, dict))
        meta = [x for x in (str(peran or "").capitalize(), k.get("skema"), TINGKAT.get(k.get("tingkat"), k.get("tingkat")),
                            f"Mitra: {mitra}" if mitra else "",
                            f"{k['mahasiswa']} mahasiswa terlibat" if k.get("mahasiswa") else "") if x]
        jenis = '<span class="tag pkm">Pengabdian</span>' if k.get("kategori") == "pkm" else '<span class="tag">Penelitian</span>'
        return f'<li><div class="judul">{jenis}{e(k["judul"])}</div><div class="meta">{" · ".join(e(x) for x in meta)}</div></li>'

    def bagian(id_, judul, xs, isi):
        if not xs:
            return ""
        return f'<section id="{id_}"><h2>{judul} <small>{len(xs)}</small></h2><div class="garis"></div>{isi}</section>'

    rek_html = "".join(f'<li><div class="judul">{e(str(r.get("nama_kegiatan") or "").strip())}</div><div class="meta">'
                       f'{e(str(r.get("bentuk") or "").replace("_", " ").capitalize())} · {e(TINGKAT.get(r.get("tingkat"), r.get("tingkat") or ""))} · {e(r.get("tahun"))}</div></li>'
                       for r in sorted(rek, key=lambda r: -int(r.get("tahun") or 0)))
    pres_html = "".join(f'<li><div class="judul"><span class="tag{" int" if x.get("tingkat") == "internasional" else ""}">'
                        f'{e(TINGKAT.get(x.get("tingkat"), x.get("tingkat") or ""))}</span>{e(x.get("capaian") or "Prestasi")} · {e(x.get("kegiatan"))}</div>'
                        f'<div class="meta">{e(nama_tim(x.get("mahasiswa")))} · {e(x.get("tahun"))}</div></li>'
                        for x in pres)
    lua_html = "".join(f'<li><div class="judul">{e(l.get("judul"))}</div><div class="meta">{e(l.get("nama_bagian") or "")} · {e(l.get("tahun"))}</div></li>'
                       for l in sorted(lua, key=lambda l: -int(l.get("tahun") or 0)))
    logo = "".join(f'<img src="../{f}{v}" alt="{e(a if i else (inst or a))}" width="{w}" height="{h}">' for i, (f, a, w, h) in enumerate(LOGO if logo is None else logo))
    angka = [(len(pub), "Publikasi"), (sum(1 for p in pub if p.get("tingkat") == "internasional"), "Internasional"),
             (len(pen), "Penelitian"), (len(pkm), "Pengabdian"), (len(rek) + len(lua), "Rekognisi & luaran")]

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>{e(tampil)} — Dosen Program Studi {e(prodi)}{" " + e(inst) if inst else ""}</title>
<meta name="description" content="{e(ringkas)}">
{f'<link rel="canonical" href="{e(url)}">' if url else ""}
<meta property="og:type" content="profile">
<meta property="og:title" content="{e(nama)} — Dosen {e(prodi)}">
<meta property="og:description" content="{e(ringkas)}">
{f'<meta property="og:url" content="{e(url)}">' if url else ""}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../tema.css{v}">
<style>{CSS}</style>
</head>
<body>
<a class="lewati" href="#isi">Lewati ke isi</a>
<div class="hero" role="region" aria-label="Pembuka halaman"><div class="hero-in">
  <div class="atas"><div class="logo-deret">{logo}</div></div>
  <nav class="jejak" aria-label="Jejak halaman"><a href="../index.html">Beranda</a> › <a href="../daftar.html?jenis=dosen">Dosen</a> › {e(tampil)}</nav>
  <div class="profil">
    {f'<img class="avatar foto" src="../{e(dosen["foto"])}{v}" alt="Foto {e(tampil)}" width="112" height="112">' if dosen.get("foto") else f'<div class="avatar" aria-hidden="true">{e(inisial(nama))}</div>'}
    <div>
      <div class="peran">Dosen · Program Studi {e(prodi)}</div>
      <h1>{e(tampil)}</h1>
      {f'<div class="bidang">{e(bidang)}</div>' if bidang else ""}
      {f'<div class="bidang">Kelompok keahlian: <a href="../{e(berkas_bidang(kel["nama"]))}">{e(kel["nama"])}</a></div>' if kel else ""}
      {f'<div class="bidang">Sedang tugas belajar · {e(dosen["tugas_belajar"])}</div>' if dosen.get("tugas_belajar") else ""}
      {f'<div class="bidang nip">NIP {e(dosen["nip"])}</div>' if dosen.get("nip") else ""}
      <div class="tautan">{"".join(f'<a href="{e(u)}" rel="noopener">{e(l)} ↗</a>' for u, l in profil_luar)}
        <a class="utama" href="../dosen.html?d={e(slug)}">Profil interaktif &rarr;</a></div>
    </div>
  </div>
</div></div>
<section class="angka" aria-label="Ringkasan karya"><div class="angka-in">{"".join(f"<div><b>{n}</b><span>{l}</span></div>" for n, l in angka)}</div></section>
<main id="isi">
  {f'<div class="topik">{"".join(f"<span class=chip>{e(t)}</span>" for t in topik)}</div>' if topik else ""}
  {bagian("publikasi", "Publikasi", pub, per_tahun(pub, baris_pub))}
  {bagian("penelitian", "Penelitian", pen, per_tahun(pen, baris_keg))}
  {bagian("pengabdian", "Pengabdian kepada masyarakat", pkm, per_tahun(pkm, baris_keg))}
  {bagian("prestasi", "Prestasi mahasiswa bimbingan", pres, f'<ol class="karya">{pres_html}</ol>')}
  {bagian("rekognisi", "Rekognisi", rek, f'<ol class="karya">{rek_html}</ol>')}
  {bagian("luaran", "Luaran lain", lua, f'<ol class="karya">{lua_html}</ol>')}
  {'' if (pub or keg or rek or lua or pres) else '<p class="kosong" style="margin-top:30px">Belum ada karya terverifikasi yang tercatat.</p>'}
</main>
<footer><div><span>Program Studi {e(prodi)}{", " + e(inst) if inst else ""} · data terverifikasi program studi, diperbarui {e(D.get("diperbarui") or "")}</span>
  <span><a href="../index.html">Beranda</a><a href="../kurikulum.html">Kurikulum</a><a href="../privasi.html">Kebijakan privasi</a></span></div></footer>
</body>
</html>
"""


def peta_situs(base_url: str, D: dict, mati: set[str]) -> str:
    ada_en = bool((D.get("situs") or {}).get("prodi_en"))   # english.html dibuat hanya bila nama Inggris diisi
    ada_galeri = len(foto_galeri(D)) >= GALERI_MIN_SITEMAP   # galeri tipis tidak didaftarkan ke mesin pencari
    alamat = [f"{base_url}/{p}" for p, modul in HALAMAN if modul not in mati and (p != "english.html" or ada_en)
              and (p != "galeri.html" or ada_galeri) and (p != "biaya-beasiswa.html" or (D.get("situs") or {}).get("biaya"))
              and (p != "tugas-akhir.html" or len(D.get("arsip_ta") or []) >= ARSIP_TA_MIN_SITEMAP)
              and (p != "kontak.html" or (D.get("situs") or {}).get("kontak"))]
    alamat += [f"{base_url}/{b['berkas']}" for b in info_bidang(D)]   # halaman per bidang (pemilik 2026-11-22)
    alamat += [f"{base_url}/{m['berkas']}" for m in info_mk(D)]       # halaman per mata kuliah (pemilik 2026-11-22)
    if ada_en:   # halaman mata kuliah berbahasa Inggris (pemilik 2026-11-22)
        alamat += [f"{base_url}/{m['berkas_en']}" for m in info_mk(D) if m.get("berkas_en")]
    alamat += [f"{base_url}/dosen/{d['slug']}.html" for d in D.get("dosen", []) if d.get("slug")]
    isi = "".join(f"  <url><loc>{e(u)}</loc></url>\n" for u in alamat)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{isi}</urlset>\n'


def alamat_situs(situs: Path, cfg: dict) -> str:
    """Base URL of the published site. A CNAME file in the published repository (GitHub Pages custom
    domain, e.g. a campus subdomain) wins, so the sitemap follows a domain change by itself
    (owner 2026-11-16); otherwise config.yaml public_site.base_url."""
    cname = situs / "CNAME"
    if cname.is_file():
        baris = cname.read_text(encoding="utf-8").strip().splitlines()
        nama = baris[0].strip().lower() if baris else ""
        if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", nama):
            return f"https://{nama}"
    return ((cfg.get("public_site") or {}).get("base_url") or "").rstrip("/")


GAMBAR_BAGIKAN = ("bagikan.png", 1200, 630)   # site/bagikan.png dari tools/kartu_bagikan.py (pemilik 2026-11-21)


# Ikon tab peramban (pemilik 2026-11-22: "munculkan logo universitas pertamina"): site/favicon.png dan
# site/apple-touch-icon.png dari tools/make_favicon.py; dipasang di setiap halaman yang dibangkitkan.
IKON_TAB = ('<link rel="icon" type="image/png" href="{a}favicon.png">\n'
            '<link rel="apple-touch-icon" href="{a}apple-touch-icon.png">\n'
            '<link rel="manifest" href="{a}manifest.webmanifest">\n')


def data_kerangka(D: dict) -> dict:
    """kerangka.json (pemilik 2026-11-22, situs lebih ringan): only what the page header and footer need (kerangka.js
    isiKerangka), a few KB instead of the full data.json. Pages that show data still read data.json themselves."""
    s = D.get("situs") or {}
    foto = sum(len(x.get("foto") or []) for k in ("kabar", "prestasi", "laboratorium") for x in D.get(k) or [])
    return {"prodi": D.get("prodi") or "", "institusi": D.get("institusi") or "", "diperbarui": D.get("diperbarui") or "",
            "akreditasi_prodi": D.get("akreditasi_prodi") or {},
            "situs": {k: s[k] for k in ("kontak", "berita", "pendaftaran", "prodi_en", "sosial", "biaya") if s.get(k)},
            "jumlah": {"kabar": len(D.get("kabar") or []), "foto": foto, "arsip_ta": len(D.get("arsip_ta") or [])}}


def manifes(D: dict, tema: str = "") -> dict:
    """manifest.webmanifest (pemilik 2026-11-22): add to the phone's home screen with the university emblem.
    tema = header colour from site/tema.css (--biru), so no colour is fixed in code."""
    prodi, inst = D.get("prodi") or "", D.get("institusi") or ""
    return {"name": " ".join(x for x in (f"Program Studi {prodi}".strip(), inst) if x), "short_name": prodi or "Prodi",
            "lang": "id", "start_url": "./", "scope": "./", "display": "standalone", "background_color": "#ffffff",
            **({"theme_color": tema} if tema else {}),
            "icons": [{"src": "favicon.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                      {"src": "apple-touch-icon.png", "sizes": "180x180", "type": "image/png"}]}


def halaman_404(D: dict, versi: str, base_url: str) -> str:
    """404.html (pemilik 2026-11-22): GitHub Pages shows it for any missing address. <base> = the site address so
    styles and links also work when the missing address is in a subfolder (e.g. dosen/nama-lama.html). The missing
    address is turned into a search suggestion; noindex."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    dasar = f'<base href="{e(base_url.rstrip("/"))}/">\n' if base_url else ""
    s = D.get("situs") or {}
    tautan = [("index.html", "Beranda"), ("kurikulum.html", "Kurikulum dan mata kuliah"), ("daftar.html?jenis=dosen", "Daftar dosen"),
              ("calon-mahasiswa.html", "Untuk calon mahasiswa"), ("layanan-mahasiswa.html", "Layanan mahasiswa"),
              *([("kontak.html", "Kontak")] if s.get("kontak") else []), ("peta-situs.html", "Peta situs: semua halaman")]
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{dasar}<meta name="generator" content="{GENERATOR}">
<meta name="robots" content="noindex">
<title>Halaman tidak ditemukan — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
main{{max-width:760px;margin:0 auto;padding:48px 20px 40px}}
.kode{{font-family:var(--mono);font-size:13px;letter-spacing:.14em;color:var(--muted)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,44px);color:var(--biru);margin:6px 0 8px;line-height:1.1}}
main form{{display:flex;gap:8px;margin:18px 0 26px}}
main input{{flex:1;font:inherit;font-size:16px;padding:10px 12px;border:1px solid var(--line);border-radius:2px}}
main button{{font:inherit;font-weight:600;padding:10px 18px;border:0;background:var(--biru);color:#fff;cursor:pointer}}
main ul{{list-style:none;margin:0;padding:0;background:#fff;border:1px solid var(--line)}}
main li a{{display:block;padding:10px 16px;border-top:1px solid var(--line);color:var(--biru-2);text-decoration:none}}
main li:first-child a{{border-top:0}}
main li a:hover{{background:var(--biru-m11,#eef3fb)}}
.ket{{color:var(--muted)}}
</style>
</head>
<body>
<main id="utama">
  <div class="kode">404</div>
  <h1>Halaman tidak ditemukan</h1>
  <p class="ket">Alamat <code id="alamat"></code> tidak ada di situs {nama_ps}. Mungkin halamannya sudah dipindah atau alamatnya
    salah ketik. Coba cari, atau buka salah satu halaman berikut.</p>
  <form id="cari404" role="search"><input id="kata404" type="search" aria-label="Cari di situs" placeholder="Cari dosen, mata kuliah, halaman…">
    <button type="submit">Cari</button></form>
  <ul>{"".join(f'<li><a href="{e(h)}">{e(j)}</a></li>' for h, j in tautan)}</ul>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: '' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
// Alamat yang dicari menjadi saran kata cari: bagian terakhir alamat tanpa .html, tanda hubung menjadi spasi.
const akhir = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
document.getElementById('alamat').textContent = location.pathname;
document.getElementById('kata404').value = akhir.replace(/\\.html?$/i, '').replace(/^(mk|course|bidang)-/, '').replace(/[-_]+/g, ' ').replace(/\\b\\d{{3,}}\\b/g, '').trim();
// Cari memakai panel cari di kepala halaman (kerangka.js). Kata yang tidak cocok dengan apa pun (mis. "lama" dari
// alamat lama) dibuang dulu, karena pencarian mewajibkan semua kata cocok (pemilik 2026-11-22).
let INDEKS = null;
async function rapikan(q) {{
  try {{
    if (!INDEKS) {{
      const [m, D] = await Promise.all([import('./cari.js{v}'), fetch('data.json', {{cache: 'no-cache'}}).then(r => r.json())]);
      INDEKS = {{ m, idx: m.indeksPublik(D, k => !(window.FITUR_MATI || []).includes(k)) }};
    }}
    // Kueri lengkap tanpa hasil: buang satu kata (dari belakang) sampai ada hasil. Menyaring per kata tidak cukup karena
    // pencarian mencocokkan potongan kata ("lama" ada di "alamat").
    const ada = ks => INDEKS.m.cari(INDEKS.idx, ks.join(' ')).length > 0;
    let kata = q.split(/\\s+/).filter(Boolean);
    while (kata.length > 1 && !ada(kata)) {{
      const i = [...kata.keys()].reverse().find(j => ada(kata.filter((_, n) => n !== j)));
      kata = i === undefined ? kata.slice(0, -1) : kata.filter((_, n) => n !== i);
    }}
    return ada(kata) ? kata.join(' ') : q;
  }} catch {{ return q; }}
}}
document.getElementById('cari404').addEventListener('submit', async ev => {{
  ev.preventDefault();
  const q = await rapikan(document.getElementById('kata404').value.trim());
  document.getElementById('kata404').value = q;
  document.querySelector('.kr-cari-buka')?.click();
  const kotak = document.getElementById('krCariKotak');
  if (kotak) {{ kotak.value = q; kotak.dispatchEvent(new Event('input')); }}
}});
</script>
</body>
</html>
"""


def pasang_ikon(teks: str, awalan: str = "") -> str:
    """Add the tab icon links before </head> unless the page already has one. awalan: '../' for pages in a subfolder."""
    if 'rel="icon"' in teks or "</head>" not in teks:
        return teks
    return teks.replace("</head>", IKON_TAB.format(a=awalan) + "</head>", 1)


def lengkapi_bagikan(teks: str, base_url: str, path: str, nama_situs: str, gambar: tuple | None = GAMBAR_BAGIKAN) -> str:
    """Pratinjau tautan (WhatsApp, Instagram, Facebook, LinkedIn; pemilik 2026-11-21): tambahkan tag Open Graph/Twitter
    yang belum ada di <head> dari judul og:title dan meta description halaman itu sendiri; og:image relatif dijadikan
    alamat lengkap (layanan pratinjau tidak mengikuti alamat relatif). Tanpa base_url halaman tidak diubah.
    gambar = (berkas relatif ke akar situs, lebar, tinggi) bila halaman belum punya og:image; None = tanpa gambar."""
    if not base_url or "</head>" not in teks:
        return teks
    kepala, sisa = teks.split("</head>", 1)
    ada = lambda pola: re.search(pola, kepala) is not None
    awal = base_url.rstrip("/") + "/"
    dir_halaman = path.rsplit("/", 1)[0] + "/" if "/" in path else ""
    def mutlak(m):
        u = html.unescape(m.group(2))
        if not re.match(r"^https?://", u):
            u = awal + posixpath.normpath(u.lstrip("/") if u.startswith("/") else dir_halaman + u).lstrip("./")
        return f'{m.group(1)}{e(u)}"'
    kepala = re.sub(r'(<meta property="og:image" content=")([^"]*)"', mutlak, kepala)
    m = re.search(r'<meta name="description" content="([^"]*)"', kepala)
    desk = m.group(1) if m else ""
    url = awal + path
    tambah = []
    if not ada(r'rel="canonical"'):
        tambah.append(f'<link rel="canonical" href="{e(url)}">')
    if not ada(r'property="og:type"'):
        tambah.append('<meta property="og:type" content="website">')
    if not ada(r'property="og:site_name"') and nama_situs:
        tambah.append(f'<meta property="og:site_name" content="{e(nama_situs)}">')
    if not ada(r'property="og:description"') and desk:
        tambah.append(f'<meta property="og:description" content="{desk}">')
    if not ada(r'property="og:url"'):
        tambah.append(f'<meta property="og:url" content="{e(url)}">')
    if not ada(r'property="og:locale"'):
        tambah.append('<meta property="og:locale" content="id_ID">')
    if not ada(r'property="og:image"') and gambar:
        tambah += [f'<meta property="og:image" content="{e(awal + gambar[0])}">',
                   f'<meta property="og:image:width" content="{gambar[1]}">', f'<meta property="og:image:height" content="{gambar[2]}">']
    if not ada(r'name="twitter:card"'):
        tambah.append(f'<meta name="twitter:card" content="{"summary_large_image" if ada(r"property=.og:image.") or gambar else "summary"}">')
    if not tambah:
        return kepala + "</head>" + sisa
    return kepala.rstrip("\n") + "\n" + "\n".join(tambah) + "\n</head>" + sisa


def ld_program(D: dict, base_url: str) -> dict:
    """Data terstruktur schema.org halaman calon mahasiswa (pemilik 2026-11-21): hanya fakta yang ada di data situs
    (nama prodi, institusi, tagline, lama studi dari semester kurikulum terbaru, akun media sosial resmi, pendaftaran)."""
    prodi, inst = D.get("prodi") or "", D.get("institusi") or ""
    s = D.get("situs") or {}
    kur = sorted(D.get("kurikulum") or [], key=lambda k: str(k.get("kode") or ""))
    smt = [m.get("semester") for m in (kur[-1].get("mk") or [])] if kur else []
    smt = [x for x in smt if isinstance(x, int) and 0 < x <= 16]
    sosial = s.get("sosial") or {}
    ld = {"@context": "https://schema.org", "@type": "EducationalOccupationalProgram",
          "name": f"Program Studi {prodi}".strip(), "inLanguage": "id"}
    if base_url:
        ld["url"] = f"{base_url.rstrip('/')}/calon-mahasiswa.html"
    if s.get("tagline"):
        ld["description"] = s["tagline"]
    if inst:
        ld["provider"] = {"@type": "CollegeOrUniversity", "name": inst}
    if smt and max(smt) % 2 == 0:
        ld["timeToComplete"] = f"P{max(smt) // 2}Y"
    akun = [sosial[k] for k in ("instagram", "youtube", "linkedin") if isinstance(sosial.get(k), str) and sosial[k].startswith("https://")]
    if akun:
        ld["sameAs"] = akun
    if s.get("pendaftaran"):
        ld["potentialAction"] = {"@type": "ApplyAction", "target": s["pendaftaran"]}
    return ld


def lengkapi_beranda(teks: str, D: dict, base_url: str) -> str:
    """index.html terbit (tulisan tangan di site/, disalin SESUDAH bangun.py): tag pratinjau beralamat lengkap dan url +
    sameAs (akun media sosial resmi dari data.json) di JSON-LD. Alamat dari alamat_situs(), jadi ikut bila domain pindah
    (CNAME). Dijalankan `python bangun.py --beranda <folder situs>` sesudah site/ disalin (pemilik 2026-11-21)."""
    if not base_url:
        return teks
    nama = " — ".join(x for x in (f"Program Studi {D.get('prodi') or ''}".strip(), D.get("institusi") or "") if x)
    teks = lengkapi_bagikan(teks, base_url, "", nama, None)
    sosial = (D.get("situs") or {}).get("sosial") or {}
    akun = [sosial[k] for k in ("instagram", "youtube", "linkedin") if isinstance(sosial.get(k), str) and sosial[k].startswith("https://")]

    def isi(m):
        try:
            ld = json.loads(m.group(2))
        except ValueError:
            return m.group(0)
        ld["url"] = base_url.rstrip("/") + "/"
        if akun:
            ld["sameAs"] = akun
        return m.group(1) + json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + m.group(3)
    return re.sub(r'(<script type="application/ld\+json">\s*)(\{.*?\})(\s*</script>)', isi, teks, count=1, flags=re.S)


def tulis_halaman_publik(situs: Path, D: dict, cfg: dict, site: Path) -> dict:
    """Write dosen/<slug>.html, sitemap.xml, robots.txt, peta-situs.html into the published folder."""
    base_url = alamat_situs(situs, cfg)
    versi = versi_aset(site)
    # Only logos present in site/ (the template package has logo.png instead of the three logos).
    logo = [x for x in LOGO if (site / x[0]).is_file()] or ([("logo.png", "Logo", 600, 300)] if (site / "logo.png").is_file() else [])
    folder = situs / "dosen"
    folder.mkdir(parents=True, exist_ok=True)
    baru = {}
    for d in D.get("dosen", []):
        if d.get("slug") and re.fullmatch(r"[a-z0-9-]+", d["slug"]):
            baru[f"{d['slug']}.html"] = halaman_dosen(D, d, base_url, versi, logo)
    dibuang = 0
    for p in folder.glob("*.html"):
        if p.name not in baru and GENERATOR in p.read_text(encoding="utf-8", errors="ignore")[:600]:
            p.unlink()
            dibuang += 1
    # Pratinjau tautan di media sosial (pemilik 2026-11-21): tag Open Graph lengkap, gambar beralamat lengkap.
    nama_situs = " — ".join(x for x in (f"Program Studi {D.get('prodi') or ''}".strip(), D.get("institusi") or "") if x)
    gambar = GAMBAR_BAGIKAN if (site / GAMBAR_BAGIKAN[0]).is_file() else None
    bagikan = lambda teks, path: lengkapi_bagikan(teks, base_url, path, nama_situs, gambar)
    for nama, isi in baru.items():
        (folder / nama).write_text(bagikan(pasang_ikon(isi, "../"), f"dosen/{nama}"), encoding="utf-8")
    calon = halaman_calon(D, versi)
    # Data terstruktur program studi untuk mesin pencari (pemilik 2026-11-21).
    ld = json.dumps(ld_program(D, base_url), ensure_ascii=False).replace("</", "<\\/")
    calon = calon.replace("</head>", f'<script type="application/ld+json">{ld}</script>\n</head>', 1)
    halaman = {
        "peta-situs.html": halaman_peta(D, fitur_mati(site), versi),
        "prestasi.html": halaman_prestasi(D, versi),
        "kabar.html": halaman_kabar(D, versi),
        # Galeri foto (pemilik 2026-11-22): dari foto kabar, prestasi, dan laboratorium yang sudah terbit.
        "galeri.html": halaman_galeri(D, versi),
        "laboratorium.html": halaman_laboratorium(D, versi),
        "kerja-sama.html": halaman_kerjasama(D, versi),
        "alumni.html": halaman_alumni(D, versi),
        # Halaman calon mahasiswa (pemilik 2026-11-20): dari data yang sudah ada; bagian tanpa data tidak tampil.
        "calon-mahasiswa.html": calon,
        # Bukan profil.html: nama itu milik halaman ruang kerja "Profil saya" di site/ (pemilik 2026-11-16).
        "profil-prodi.html": halaman_profil(D, versi),
    }
    # Ringkasan bahasa Inggris (pemilik 2026-11-21): hanya bila nama prodi bahasa Inggris diisi di config.
    if (D.get("situs") or {}).get("prodi_en"):
        halaman["english.html"] = halaman_english(D, versi)
    # Halaman per bidang keahlian (pemilik 2026-11-22); halaman bidang lama buatan pembangun (nama berubah) dibuang.
    semua_bidang = info_bidang(D)
    for b in semua_bidang:
        halaman[b["berkas"]] = halaman_bidang(D, b, semua_bidang, versi)
    # Halaman per mata kuliah kurikulum terbaru (pemilik 2026-11-22); halaman MK lama buatan pembangun dibuang.
    for m in info_mk(D):
        halaman[m["berkas"]] = halaman_mk(D, m, versi)
        # Kembaran berbahasa Inggris (pemilik 2026-11-22), hanya bila english.html dibuat.
        if (D.get("situs") or {}).get("prodi_en") and m.get("berkas_en"):
            halaman[m["berkas_en"]] = halaman_mk_en(D, m, versi)
    # Biaya dan beasiswa (pemilik 2026-11-22): hanya bila config memuat tautan resmi.
    if (D.get("situs") or {}).get("biaya"):
        halaman["biaya-beasiswa.html"] = halaman_biaya(D, versi)
    # Arsip judul TA (selalu, menu tampil bila ada isinya) dan Kontak (bila config memuat kontak), pemilik 2026-11-22.
    halaman["tugas-akhir.html"] = halaman_arsip_ta(D, versi)
    if (D.get("situs") or {}).get("kontak"):
        halaman["kontak.html"] = halaman_kontak(D, versi)
    # Halaman 404 sendiri (pemilik 2026-11-22); <base> memakai alamat situs bila diketahui.
    halaman["404.html"] = halaman_404(D, versi, base_url)
    # Umpan RSS (pemilik 2026-11-22): kabar.html dan prestasi.html menautkannya bila alamat situs diketahui.
    if base_url and (D.get("kabar") or D.get("prestasi")):
        (situs / "feed.xml").write_text(umpan_rss(D, base_url), encoding="utf-8")
        rss = f'<link rel="alternate" type="application/rss+xml" title="Kabar dan prestasi" href="feed.xml">\n</head>'
        for h in ("kabar.html", "prestasi.html"):
            halaman[h] = halaman[h].replace("</head>", rss, 1)
    for f in [*situs.glob("bidang-*.html"), *situs.glob("mk-*.html"), *situs.glob("course-*.html"), *situs.glob("biaya-beasiswa.html"),
              *situs.glob("kontak.html")]:
        if f.name not in halaman and GENERATOR in f.read_text(encoding="utf-8", errors="ignore")[:600]:
            f.unlink()
    for nama, isi in halaman.items():
        # 404.html tanpa tag bagikan (noindex, alamatnya berubah-ubah).
        (situs / nama).write_text(pasang_ikon(isi) if nama == "404.html" else bagikan(pasang_ikon(isi), nama), encoding="utf-8")
    # Situs lebih ringan (pemilik 2026-11-22): kerangka.json untuk kepala/kaki halaman; manifest untuk layar utama ponsel.
    (situs / "kerangka.json").write_text(json.dumps(data_kerangka(D), ensure_ascii=False), encoding="utf-8")
    m = re.search(r"--biru:\s*(#[0-9a-fA-F]{3,8})", (site / "tema.css").read_text(encoding="utf-8")) if (site / "tema.css").is_file() else None
    (situs / "manifest.webmanifest").write_text(json.dumps(manifes(D, m.group(1) if m else ""), ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    if base_url:
        (situs / "sitemap.xml").write_text(peta_situs(base_url, D, fitur_mati(site)), encoding="utf-8")
        (situs / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n", encoding="utf-8")
    return {"dosen": len(baru), "dibuang": dibuang, "sitemap": bool(base_url), "alamat": base_url}


# Human-readable site map (owner 2026-11-16), linked from the page footer.
# Same five groups as the header menu (site/kerangka.js MENU, owner 2026-11-19).
PETA = [
    ("Profil", [("index.html", "Beranda"), ("profil-prodi.html", "Profil program studi"),
                ("kurikulum.html", "Kurikulum dan capaian pembelajaran lulusan"), ("laboratorium.html", "Laboratorium"),
                ("kerja-sama.html", "Kerja sama"), ("kabar.html", "Kegiatan prodi"), ("galeri.html", "Galeri foto")]),
    ("Dosen dan riset", [("daftar.html?jenis=dosen", "Daftar dosen"), ("keahlian.html", "Kepakaran dosen"),
                         ("daftar.html?jenis=publikasi", "Publikasi"), ("daftar.html?jenis=penelitian", "Penelitian"),
                         ("daftar.html?jenis=pkm", "Pengabdian kepada masyarakat"), ("sdgs.html", "Kontribusi SDGs")]),
    ("Mahasiswa", [("calon-mahasiswa.html", "Untuk calon mahasiswa: bidang, perjalanan kuliah, prestasi, karier, pendaftaran"),
                   ("layanan-mahasiswa.html", "Layanan mahasiswa: pengumuman, jadwal, berkas, tanya-jawab"),
                   ("ekuivalensi-kurikulum.html", "Ekuivalensi kurikulum: padanan mata kuliah kurikulum lama ke baru"),
                   ("biaya-beasiswa.html", "Biaya dan beasiswa: tautan resmi universitas"),
                   ("tugas-akhir.html", "Arsip tugas akhir: judul per bidang keahlian"),
                   ("layanan-mahasiswa.html#kalender", "Kalender akademik"),
                   ("pengajuan.html", "Pengajuan KP, TA, lomba, luaran, kabar kegiatan, surat, yudisium"),
                   ("kerja-praktik.html", "Kerja praktik dan magang: alur, pengajuan, tempat KP"),
                   ("prestasi.html", "Prestasi mahasiswa"), ("alumni.html", "Alumni dan tracer study")]),
    ("Kinerja", [("kinerja.html", "Kinerja program studi"), ("hasil-survei.html", "Hasil survei kepuasan")]),
    ("Lainnya", [("kontak.html", "Kontak dan lokasi"), ("privasi.html", "Kebijakan privasi"), ("english.html", "English: programme overview")]),
]
MODUL_HALAMAN = {"keahlian.html": "kepakaran", "sdgs.html": "sdgs"}


def halaman_peta(D: dict, mati: set[str], versi: str) -> str:
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    kelompok = []
    for judul, xs in PETA:
        isi = "".join(f'<li><a href="{e(h)}">{e(t)}</a></li>' for h, t in xs if MODUL_HALAMAN.get(h) not in mati
                      and (h != "english.html" or (D.get("situs") or {}).get("prodi_en"))
                      and (h != "galeri.html" or foto_galeri(D))
                      and (h != "biaya-beasiswa.html" or (D.get("situs") or {}).get("biaya"))
                      and (h != "tugas-akhir.html" or D.get("arsip_ta"))
                      and (h != "kontak.html" or (D.get("situs") or {}).get("kontak"))
                      and (h != "layanan-mahasiswa.html#kalender" or D.get("kalender") or (D.get("situs") or {}).get("kalender_resmi")))
        kelompok.append(f"<section><h2>{e(judul)}</h2><ul>{isi}</ul></section>")
    bidang = "".join(f'<li><a href="{e(b["berkas"])}">{e(b["nama"])}</a></li>' for b in info_bidang(D))
    if bidang:
        kelompok.append(f"<section><h2>Bidang keahlian</h2><ul>{bidang}</ul></section>")
    dosen = "".join(f'<li><a href="dosen/{e(d["slug"])}.html">{e(nama_dosen(D, d))}</a></li>'
                    for d in sorted(D.get("dosen", []), key=lambda d: d.get("nama", "")) if d.get("slug"))
    if dosen:
        kelompok.append(f"<section><h2>Profil dosen</h2><ul>{dosen}</ul></section>")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Peta situs — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Daftar seluruh halaman situs {nama_ps}.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
main{{max-width:1080px;margin:0 auto;padding:36px 20px 20px}}
h1{{font-family:var(--serif);font-size:clamp(28px,4vw,40px);color:var(--biru);margin:0 0 6px}}
.ket{{color:var(--muted);margin:0 0 20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}}
section{{background:#fff;border:1px solid var(--line);border-top:3px solid var(--aksen);padding:16px 20px}}
h2{{font-family:var(--serif);font-size:19px;color:var(--biru);margin:0 0 8px}}
ul{{list-style:none;margin:0;padding:0}}
li{{padding:5px 0;border-bottom:1px solid var(--line-soft)}}
li:last-child{{border-bottom:0}}
a{{color:var(--biru-2);text-decoration:none}}
a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<main id="utama">
  <h1>Peta situs</h1>
  <p class="ket">Seluruh halaman situs {nama_ps}.</p>
  <div class="grid">{"".join(kelompok)}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: '' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""



# ---------------------------------------------------------------------------
# Prestasi mahasiswa di situs publik (pemilik 2026-11-16; instal-lengkap.sql).
# Verified achievements, not hidden by the admin. Student names only with consent
# (tampil_nama); NIM never. Photos: evidence of kind 'foto', copied from Drive at build.
# ---------------------------------------------------------------------------
FOTO_PER_PRESTASI = 3


def nama_tim(nama: list | None) -> str:
    """Student names on public pages (pemilik 2026-11-16): one name; two names joined with "dan";
    three or more as "first name dkk."; none (no consent) as "Tim mahasiswa"."""
    xs = [n for n in (nama or []) if n]
    if not xs:
        return "Tim mahasiswa"
    return xs[0] if len(xs) == 1 else f"{xs[0]} dan {xs[1]}" if len(xs) == 2 else f"{xs[0]} dkk."


def drive_id(url) -> str:
    """Google Drive file id from a sharing link (/d/<id>/ or id=<id>), or ''."""
    m = re.search(r"/d/([A-Za-z0-9_-]{20,})|[?&]id=([A-Za-z0-9_-]{20,})", str(url or ""))
    return (m.group(1) or m.group(2)) if m else ""


def prestasi_publik(rows: list[dict], bukti: list[dict], dosen: list[dict]) -> list[dict]:
    """Public achievements for data.json. rows: lkps_prestasi_mahasiswa; bukti: lkps_bukti;
    dosen: [{nidn, nama, slug}] (slug present only for lecturers with a public page)."""
    per_nidn = {str(d.get("nidn") or "").strip(): d for d in dosen if d.get("nidn")}
    foto = {}
    for b in bukti:
        if b.get("tabel") == "lkps_prestasi_mahasiswa" and b.get("jenis") == "foto" and drive_id(b.get("url")):
            foto.setdefault(b.get("baris_id"), []).append(drive_id(b.get("url")))
    out = []
    for r in rows:
        if r.get("status", "terverifikasi") != "terverifikasi" or r.get("sembunyikan_publik"):
            continue
        nama = [x.strip() for x in str(r.get("nama_mahasiswa") or "").split(";") if x.strip()] if r.get("tampil_nama") else []
        nidn = r.get("pembimbing") or []
        nidn = nidn if isinstance(nidn, list) else [x.strip() for x in str(nidn).split(";")]
        pemb = [{"nama": per_nidn[n]["nama"], **({"slug": per_nidn[n]["slug"]} if per_nidn[n].get("slug") else {})}
                for n in (str(x).strip() for x in nidn) if n in per_nidn]
        out.append({"id": r.get("id"), "kegiatan": (r.get("nama_kegiatan") or "").strip(),
                    "penyelenggara": (r.get("penyelenggara") or "").strip(), "bidang": r.get("bidang") or "",
                    "tingkat": r.get("tingkat") or "", "capaian": (r.get("capaian") or "").strip(),
                    "tahun": r.get("tahun"), "bulan": r.get("bulan"), "cerita": (r.get("cerita") or "").strip(),
                    "mahasiswa": nama, "pembimbing": pemb,
                    "_foto": list(dict.fromkeys(foto.get(r.get("id"), [])))[:FOTO_PER_PRESTASI]})
    out.sort(key=lambda x: (-int(x.get("tahun") or 0), -int(x.get("bulan") or 0), x["kegiatan"]))
    return out


def tempat_kp_publik(rows: list[dict]) -> list[dict]:
    """KP/internship placements for kerja-sama.html (owner 2026-11-17): approved KP and magang
    (pengajuan_mahasiswa jenis 'kp': status disetujui, or already in the completion stage), grouped
    by organisation name ignoring case and spacing. No student identity leaves this function.
    Year = completion start date, else planned start, else submission date."""
    per: dict[str, dict] = {}
    for r in rows or []:
        if r.get("jenis") != "kp":
            continue
        if not ((r.get("tahap") or "pengajuan") == "selesai" or r.get("status") == "disetujui"):
            continue
        d, sl = r.get("data") or {}, r.get("data_selesai") or {}
        nama = " ".join(str(d.get("instansi") or "").split())
        if not nama:
            continue
        # Kunci sama dengan nama_instansi_kunci() (105): tanpa titik/koma, spasi tunggal, tanpa beda huruf besar.
        kunci = " ".join(re.sub(r"[.,]", "", nama).split()).casefold()
        x = per.setdefault(kunci, {"instansi": nama, "kp": 0, "magang": 0, "bidang": [], "_tahun": set()})
        x["magang" if d.get("program") == "magang" else "kp"] += 1
        b = " ".join(str(d.get("bidang_kerja") or "").split())
        if b and b.casefold() not in {y.casefold() for y in x["bidang"]}:
            x["bidang"].append(b)
        th = str(sl.get("tanggal_mulai") or d.get("rencana_mulai") or r.get("dibuat") or "")[:4]
        if th.isdigit():
            x["_tahun"].add(int(th))
    out = []
    for x in per.values():
        th = sorted(x.pop("_tahun"))
        out.append({**x, "bidang": x["bidang"][:3], "tahun_awal": th[0] if th else None, "tahun_akhir": th[-1] if th else None})
    out.sort(key=lambda x: (-(x["kp"] + x["magang"]), x["instansi"].casefold()))
    return out


def persen_jawaban(xs: list, cocok: set) -> int | None:
    """Percentage (rounded) of answers [label, n] whose label (casefolded) is in cocok; None without answers."""
    tot = sum(k for _, k in xs)
    ya = sum(k for t, k in xs if str(t).casefold() in cocok)
    return round(100 * ya / tot) if tot else None


def alumni_ringkas(survei: list[dict], jawaban: list[dict], min_responden: int | None, hari_ini: str = "") -> dict:
    """Aggregate tracer-study answers (survei kelompok 'alumni', 55-patch) for alumni.html (owner 2026-11-17:
    aggregates only; no names, employers, or income). Answers are counted as written, so option labels are
    not duplicated here. Below min_responden (or when it is None) only the count is returned. 'isi' = public link of the open
    tracer survey (publik, not revoked, within its dates), if any."""
    alumni = {s.get("id"): s for s in survei or [] if s.get("kelompok") == "alumni"}
    js = [j.get("jawaban") or {} for j in jawaban or [] if j.get("survei_id") in alumni]
    buka = [s for s in alumni.values() if s.get("publik") and not s.get("dicabut") and s.get("token")
            and (not hari_ini or ((not s.get("mulai") or str(s["mulai"])[:10] <= hari_ini)
                                  and (not s.get("selesai") or str(s["selesai"])[:10] >= hari_ini)))]
    isi = {"judul": buka[-1].get("judul") or "Tracer study", "token": buka[-1]["token"]} if buka else None
    hasil = {"responden": len(js), "min": min_responden, **({"isi": isi} if isi else {})}
    if min_responden is None or len(js) < min_responden:
        return hasil

    # Urutan opsi dari survei alumni terbaru (mis. kesesuaian "Sangat erat" ... "Tidak sama sekali");
    # jawaban di luar opsi di belakang, menurut jumlah.
    terbaru = sorted(alumni.values(), key=lambda s: str(s.get("dibuat") or ""))
    opsi = {q.get("id"): [str(o).casefold() for o in q.get("opsi") or []]
            for s in terbaru for q in s.get("pertanyaan") or [] if isinstance(q, dict)}

    def hitung(k, atas=None):
        c: dict[str, list] = {}
        for j in js:
            v = " ".join(str(j.get(k) if j.get(k) is not None else "").split())
            if v:
                c.setdefault(v.casefold(), [v, 0])[1] += 1
        urut = [" ".join(o.split()) for o in opsi.get(k, [])]
        xs = sorted(c.values(), key=lambda x: (urut.index(x[0].casefold()) if x[0].casefold() in urut else len(urut), -x[1], x[0]))
        if atas and len(xs) > atas:
            xs = xs[:atas] + [["Lainnya", sum(n for _, n in xs[atas:])]]
        return xs

    def angka(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    # Label kompetensi dari teks pertanyaan f17_<k>_a survei alumni terbaru ("...: etika" -> "Etika").
    label = {}
    for s in terbaru:
        for q in s.get("pertanyaan") or []:
            m = re.fullmatch(r"f17_(\w+)_a", str(q.get("id") or ""))
            if m:
                label[m.group(1)] = str(q.get("teks") or m.group(1)).split(":")[-1].strip().capitalize()
    kompetensi = []
    for k, nama in label.items():
        a = [x for x in (angka(j.get(f"f17_{k}_a")) for j in js) if x is not None]
        b = [x for x in (angka(j.get(f"f17_{k}_b")) for j in js) if x is not None]
        if a or b:
            kompetensi.append({"nama": nama, "lulus": round(sum(a) / len(a), 2) if a else None,
                               "kerja": round(sum(b) / len(b), 2) if b else None})
    bulan = [x for x in (angka(j.get("bulan")) for j in js) if x is not None]
    th = {}
    for j in js:
        t = angka(j.get("tahun_lulus"))
        if t:
            th[int(t)] = th.get(int(t), 0) + 1
    return {**hasil, "per_tahun": sorted(([t, n] for t, n in th.items()), reverse=True),
            "status": hitung("status"), "kerja_6bulan": hitung("kerja_6bulan"),
            "waktu_tunggu_rerata": round(sum(bulan) / len(bulan), 1) if bulan else None,
            "kesesuaian": hitung("kesesuaian"), "tingkat": hitung("tingkat"),
            "jenis_instansi": hitung("jenis_instansi"), "provinsi": hitung("provinsi", atas=10),   # provinsi: tanpa opsi, urut jumlah
            "kompetensi": kompetensi}


def salin_foto_prestasi(situs: Path, prestasi: list[dict], ambil=None) -> dict:
    """Copy each achievement photo (Drive thumbnail, 1200 px) to <situs>/prestasi/<id>.jpg once,
    set x["foto"] to the relative paths that exist, drop "_foto", and remove photos no longer
    used. ambil(url) -> (content_type, bytes); default uses requests. A failed download leaves
    the card without that photo; the build continues."""
    return _salin(situs / "prestasi", "prestasi", prestasi, ambil)


def _salin(folder: Path, awalan: str, xs: list[dict], ambil=None, ukuran: str = "w1200") -> dict:
    if ambil is None:
        import requests

        def ambil(url):
            r = requests.get(url, timeout=25, allow_redirects=True)
            return (r.headers.get("Content-Type", "") if r.ok else ""), (r.content if r.ok else b"")
    folder.mkdir(parents=True, exist_ok=True)
    dipakai, baru, gagal = set(), 0, 0
    for x in xs:
        jalur = []
        for fid in x.pop("_foto", []):
            f = folder / f"{fid}.jpg"
            if not f.is_file():
                try:
                    jenis, isi = ambil(f"https://drive.google.com/thumbnail?id={fid}&sz={ukuran}")
                except Exception:
                    jenis, isi = "", b""
                if not jenis.startswith("image/") or len(isi) < 1000:
                    gagal += 1
                    continue
                f.write_bytes(isi)
                baru += 1
            dipakai.add(f.name)
            jalur.append(f"{awalan}/{f.name}")
        if jalur:
            x["foto"] = jalur
    dibuang = 0
    for f in folder.glob("*.jpg"):
        if f.name not in dipakai:
            f.unlink()
            dibuang += 1
    return {"baru": baru, "gagal": gagal, "dibuang": dibuang, "dipakai": len(dipakai)}


def halaman_prestasi(D: dict, versi: str) -> str:
    """Static prestasi.html: achievement cards per year, text in the HTML for search engines."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    xs = D.get("prestasi") or []
    jumlah = {t: sum(1 for x in xs if x.get("tingkat") == t) for t in ("internasional", "nasional", "wilayah_lokal")}

    def kartu(x):
        foto = x.get("foto") or []
        gambar = (f'<img src="{e(foto[0])}{v}" alt="Dokumentasi {e(x.get("kegiatan"))}" loading="lazy">' if foto
                  else '<div class="tanpa-foto" aria-hidden="true">&#127942;</div>')
        siapa = nama_tim(x.get("mahasiswa"))
        pemb = ", ".join(f'<a href="dosen/{e(b["slug"])}.html">{e(nama_dosen(D, b))}</a>' if b.get("slug") else e(nama_dosen(D, b))
                         for b in x.get("pembimbing") or [])
        lain = "".join(f'<img src="{e(f)}{v}" alt="" loading="lazy">' for f in foto[1:])
        cerita = f'<p>{e(x["cerita"])}</p>' if x.get("cerita") else ""
        lain = f'<div class="lain">{lain}</div>' if lain else ""
        tempat = f' · {e(x["penyelenggara"])}' if x.get("penyelenggara") else ""
        oleh = f" · Pembimbing: {pemb}" if pemb else ""
        kelas = " int" if x.get("tingkat") == "internasional" else ""
        return (f'<article class="kartu" id="prestasi-{e(x.get("id"))}">{gambar}<div class="isi">'
                f'<div class="meta"><span class="tag{kelas}">'
                f'{e(TINGKAT.get(x.get("tingkat"), x.get("tingkat") or ""))}</span>{e(x.get("tahun"))}</div>'
                f'<h3>{e(x.get("capaian") or "Prestasi")}</h3><div class="lomba">{e(x.get("kegiatan"))}{tempat}</div>'
                f'{cerita}<div class="siapa">{e(siapa)}{oleh}</div>{lain}</div></article>')

    tahun = sorted({x.get("tahun") for x in xs if x.get("tahun")}, reverse=True)
    isi = "".join(f'<section><h2>{e(t)}</h2><div class="grid">{"".join(kartu(x) for x in xs if x.get("tahun") == t)}</div></section>'
                  for t in tahun) or '<p class="kosong">Prestasi mahasiswa akan tampil di sini setelah diverifikasi program studi.</p>'
    angka = "".join(f"<div><b>{n}</b><span>{e(TINGKAT[t])}</span></div>" for t, n in jumlah.items() if n)
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Prestasi mahasiswa — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Prestasi mahasiswa {nama_ps}: {len(xs)} prestasi di tingkat wilayah, nasional, dan internasional.">
<meta property="og:title" content="Prestasi mahasiswa — {nama_ps}">
{f'<meta property="og:image" content="{e((xs[0].get("foto") or [""])[0])}">' if xs and xs[0].get("foto") else ""}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1180px;margin:0 auto;padding:40px 20px 34px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:640px}}
.angka{{display:flex;flex-wrap:wrap;gap:0;margin-top:22px}}
.angka div{{padding:10px 26px 4px 0;margin-right:26px;border-right:1px solid rgba(255,255,255,.18)}}
.angka div:last-child{{border-right:0}}
.angka b{{display:block;font-family:var(--mono);font-size:30px;font-weight:400;line-height:1}}
.angka span{{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--biru-m2)}}
main{{max-width:1180px;margin:0 auto;padding:10px 20px 20px}}
h2{{font-family:var(--serif);font-size:26px;color:var(--biru);margin:36px 0 14px;border-bottom:3px solid var(--aksen);display:inline-block;padding-bottom:2px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}}
.kartu{{background:#fff;border:1px solid var(--line);border-radius:2px;overflow:hidden;display:flex;flex-direction:column}}
.kartu>img,.tanpa-foto{{width:100%;aspect-ratio:16/10;object-fit:cover;background:var(--biru-m10);display:block}}
.tanpa-foto{{display:grid;place-items:center;font-size:44px;color:var(--biru-3)}}
.isi{{padding:16px 18px 18px}}
.meta{{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.tag{{display:inline-block;padding:1px 7px;border-radius:2px;background:var(--biru-m8);color:var(--biru);margin-right:8px}}
.tag.int{{background:var(--aksen);color:var(--biru-gelap)}}
h3{{font-family:var(--serif);font-size:21px;color:var(--biru);margin:8px 0 2px;line-height:1.2}}
.lomba{{font-weight:600}}
.isi p{{margin:8px 0 0;color:var(--ink)}}
.siapa{{margin-top:10px;font-size:13.5px;color:var(--muted)}}
.siapa a{{color:var(--biru-2)}}
.lain{{display:flex;gap:6px;margin-top:10px}}
.lain img{{width:72px;height:52px;object-fit:cover;border-radius:2px}}
.kosong{{color:var(--muted)}}
</style>
</head>
<body>
<main id="utama" style="padding:0;max-width:none">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Prestasi mahasiswa</h1>
    <p>Capaian mahasiswa dalam kompetisi dan kegiatan di tingkat wilayah, nasional, dan internasional.</p>
    {f'<div class="angka">{angka}</div>' if angka else ""}
  </div></div>
  <div style="max-width:1180px;margin:0 auto;padding:10px 20px 20px">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'mahasiswa' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""



# ---------------------------------------------------------------------------
# Kabar kegiatan (pemilik 2026-11-16; instal-lengkap.sql) dan status akreditasi.
# ---------------------------------------------------------------------------
JENIS_KABAR = {"kuliah_tamu": "Kuliah tamu", "kunjungan_lapangan": "Kuliah/kunjungan lapangan", "seminar": "Seminar",
               "penelitian": "Penelitian",   # patch 92
               "pengabdian": "Pengabdian kepada masyarakat", "kerja_praktik": "Kerja praktik", "kompetisi": "Kompetisi",
               "kerja_sama": "Kerja sama", "lainnya": "Kegiatan"}
FOTO_PER_KABAR = 6
PERINGKAT = {"unggul": "Unggul", "a": "A", "baik_sekali": "Baik Sekali", "b": "B", "baik": "Baik", "c": "C"}


def kabar_publik(rows: list[dict]) -> list[dict]:
    """Published activity news for data.json, newest first; photos as Drive ids in _foto."""
    out = []
    for r in rows:
        # Terbit saja; tampil_publik false (patch 88) = hanya bukti akreditasi, tidak dipublikasikan.
        if r.get("status") != "terbit" or r.get("tampil_publik") is False:
            continue
        ids = [drive_id(u) for u in r.get("foto") or []]
        out.append({"id": r.get("id"), "judul": (r.get("judul") or "").strip(), "tanggal": str(r.get("tanggal") or "")[:10],
                    "jenis": r.get("jenis") or "lainnya", "tempat": (r.get("tempat") or "").strip(),
                    "ringkasan": (r.get("ringkasan") or "").strip(), "tautan": r.get("tautan") or "",
                    "_foto": [i for i in dict.fromkeys(ids) if i][:FOTO_PER_KABAR]})
    out.sort(key=lambda x: (x["tanggal"], x["id"] or 0), reverse=True)
    return out


TAHAP_TA = {"seminar_proposal": "Seminar proposal", "seminar_kemajuan": "Seminar kemajuan", "sidang_akhir": "Sidang akhir"}


def jadwal_ta_publik(rows: list[dict], dosen: dict, hari_ini: str, mundur: int = 14, maju: int = 90) -> list[dict]:
    """Public TA seminar/defence schedule (instal-lengkap.sql, owner 2026-11-17) for Layanan mahasiswa.

    rows: jadwal_ta; dosen: NIDN -> {nama, slug}. Window: `mundur` days back to `maju` days ahead of hari_ini
    (YYYY-MM-DD). Cancelled and hidden rows are left out. No NIM ever; the student name only with tampil_nama,
    otherwise "Mahasiswa TA". Sorted by date then time."""
    from datetime import date, timedelta
    h = date.fromisoformat(hari_ini)
    awal, akhir = (h - timedelta(days=mundur)).isoformat(), (h + timedelta(days=maju)).isoformat()

    def orang(nidns):
        xs = nidns if isinstance(nidns, list) else [x.strip() for x in str(nidns or "").split(";")]
        return [{"nama": dosen[n]["nama"], **({"slug": dosen[n]["slug"]} if dosen[n].get("slug") else {})}
                for n in (str(x).strip() for x in xs) if n in dosen]

    out = []
    for r in rows:
        tgl = str(r.get("tanggal") or "")[:10]
        if not tgl or not (awal <= tgl <= akhir) or r.get("status") == "batal" or r.get("sembunyikan_publik") is True:
            continue
        nama = [x.strip() for x in str(r.get("nama_mahasiswa") or "").split(";") if x.strip()] if r.get("tampil_nama") else []
        out.append({"id": r.get("id"), "tahap": r.get("tahap"), "tahap_label": TAHAP_TA.get(r.get("tahap"), "TA"),
                    "tanggal": tgl, "jam": (r.get("jam") or "").strip(), "ruang": (r.get("ruang") or "").strip(),
                    "daring": bool(r.get("tautan_daring")), "judul": (r.get("judul") or "").strip(),
                    "mahasiswa": nama, "pembimbing": orang(r.get("pembimbing")), "penguji": orang(r.get("penguji")),
                    "status": r.get("status") or "terjadwal"})
    out.sort(key=lambda x: (x["tanggal"], x["jam"], x["id"] or 0))
    return out


def arsip_ta_publik(rows: list[dict], dosen_nidn: dict, dosen_publik: list[dict]) -> list[dict]:
    """Thesis title archive (owner 2026-11-22) from jadwal_ta: final defences (sidang_akhir) with status selesai, not
    hasil 'mengulang', not hidden. NEVER the student's name or NIM (owner: archive without names). bidang = the row's
    bidang (patch 149) or else the expertise group of the first supervisor. Newest first. dosen_nidn: NIDN ->
    {nama, slug}; dosen_publik: data.json dosen (slug, kelompok)."""
    kel = {d.get("slug"): d.get("kelompok") for d in dosen_publik or [] if d.get("slug")}
    out = []
    for r in rows or []:
        if (r.get("tahap") != "sidang_akhir" or r.get("status") != "selesai" or r.get("hasil") == "mengulang"
                or r.get("sembunyikan_publik") is True):
            continue
        judul, tgl = (r.get("judul") or "").strip(), str(r.get("tanggal") or "")[:10]
        if not judul or len(tgl) < 10:
            continue
        xs = r.get("pembimbing") if isinstance(r.get("pembimbing"), list) else str(r.get("pembimbing") or "").split(";")
        pemb = [{"nama": dosen_nidn[n]["nama"], **({"slug": dosen_nidn[n]["slug"]} if dosen_nidn[n].get("slug") else {})}
                for n in (str(x).strip() for x in xs) if n in dosen_nidn]
        bidang = str(r.get("bidang") or "").strip() or (kel.get(pemb[0].get("slug")) if pemb else None) or ""
        out.append({"id": r.get("id"), "judul": judul, "tahun": int(tgl[:4]), "bulan": int(tgl[5:7]),
                    **({"bidang": bidang} if bidang else {}), "pembimbing": pemb})
    out.sort(key=lambda x: (-x["tahun"], -x["bulan"], x["judul"]))
    return out


def akreditasi_publik(rows: list[dict], hari_ini: str, lembaga: str = "") -> dict:
    """Accreditation of this prodi (lkps_prodi_upps row with diakreditasi): grade, SK number and
    validity. Empty when absent, without a grade, or expired: the site never claims a lapsed status."""
    for r in rows:
        if not r.get("diakreditasi") or r.get("status_akreditasi") not in PERINGKAT:
            continue
        sampai = str(r.get("tanggal_kedaluwarsa") or "")[:10]
        if sampai and sampai < hari_ini:
            continue
        return {k: v for k, v in {"peringkat": PERINGKAT[r["status_akreditasi"]], "kode": r["status_akreditasi"],
                                  "nomor_sk": (r.get("nomor_sk") or "").strip(), "tanggal_sk": str(r.get("tanggal_sk") or "")[:10],
                                  "berlaku_sampai": sampai, "lembaga": (lembaga or "").strip()}.items() if v}
    return {}


def salin_foto_dosen(situs: Path, dosen: list[dict], ambil=None) -> dict:
    """Lecturer photos uploaded in Profil saya (instal-lengkap.sql; Drive id in d["_foto"]) to
    <situs>/foto-profil/<id>.jpg at 400 px, once; d["foto"] becomes that single path. A lecturer without
    an upload (or whose download failed) keeps the photo from site/foto-dosen/, if any. Own folder, so the
    cleanup of unused files never touches site/foto-dosen/ (pemilik 2026-11-16)."""
    hasil = _salin(situs / "foto-profil", "foto-profil", dosen, ambil, ukuran="w400")
    for d in dosen:
        if isinstance(d.get("foto"), list):
            d["foto"] = d["foto"][0]
    return hasil


def salin_foto(situs: Path, xs: list[dict], folder_nama: str, ambil=None) -> dict:
    """Copy Drive photos (x["_foto"]) of items to <situs>/<folder_nama>/<id>.jpg once; see salin_foto_prestasi."""
    return _salin(situs / folder_nama, folder_nama, xs, ambil)


def halaman_kabar(D: dict, versi: str) -> str:
    """Static kabar.html: published activity news, newest first, text in the HTML."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    berita = (D.get("situs") or {}).get("berita")
    bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
             "November", "Desember"]

    def tanggal(t):
        try:
            y, m, d = t.split("-")
            return f"{int(d)} {bulan[int(m)]} {y}"
        except (ValueError, IndexError):
            return e(t)

    def kartu(x):
        foto = x.get("foto") or []
        gambar = (f'<img src="{e(foto[0])}{v}" alt="{e(x["judul"])}" loading="lazy">' if foto else "")
        lain = "".join(f'<img src="{e(f)}{v}" alt="" loading="lazy">' for f in foto[1:])
        lain = f'<div class="lain">{lain}</div>' if lain else ""
        tempat = f" · {e(x['tempat'])}" if x.get("tempat") else ""
        tautan = f'<a class="lagi" href="{e(x["tautan"])}" rel="noopener">Selengkapnya &#8599;</a>' if x.get("tautan") else ""
        return (f'<article class="kartu" id="kabar-{e(x["id"])}">{gambar}<div class="isi">'
                f'<div class="meta"><span class="tag">{e(JENIS_KABAR.get(x["jenis"], "Kegiatan"))}</span>{tanggal(x["tanggal"])}{tempat}</div>'
                f'<h2>{e(x["judul"])}</h2><p>{e(x["ringkasan"])}</p>{lain}{tautan}</div></article>')

    xs = D.get("kabar") or []
    isi = "".join(kartu(x) for x in xs) or '<p class="kosong">Kegiatan program studi akan tampil di sini.</p>'
    ke_berita = (f'<p class="univ">Berita program studi juga dimuat di <a href="{e(berita)}" rel="noopener">laman berita '
                 f'universitas &#8599;</a>.</p>') if berita else ""
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Kegiatan prodi — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Kegiatan {nama_ps}: kuliah tamu, kunjungan lapangan, seminar, pengabdian kepada masyarakat, dan kerja sama.">
<meta property="og:title" content="Kegiatan prodi — {nama_ps}">
{f'<meta property="og:image" content="{e((xs[0].get("foto") or [""])[0])}">' if xs and xs[0].get("foto") else ""}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 34px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:640px}}
.daftar{{max-width:1080px;margin:0 auto;padding:24px 20px 20px;display:grid;gap:20px}}
.kartu{{background:#fff;border:1px solid var(--line);display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);overflow:hidden}}
.kartu:not(:has(> img)){{grid-template-columns:1fr}}
.kartu>img{{width:100%;height:100%;min-height:220px;object-fit:cover;display:block;background:var(--biru-m10)}}
.isi{{padding:20px 24px}}
.meta{{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.tag{{display:inline-block;padding:1px 7px;border-radius:2px;background:var(--aksen);color:var(--biru-gelap);margin-right:8px}}
h2{{font-family:var(--serif);font-size:23px;color:var(--biru);margin:8px 0 6px;line-height:1.2}}
.isi p{{margin:0;white-space:pre-line}}
.lain{{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}}
.lain img{{width:84px;height:60px;object-fit:cover;border-radius:2px}}
.lagi{{display:inline-block;margin-top:12px;font-weight:600;color:var(--biru-2);text-decoration:none}}
.univ{{max-width:1080px;margin:0 auto;padding:0 20px;color:var(--muted)}}
.kosong{{color:var(--muted)}}
@media(max-width:760px){{.kartu{{grid-template-columns:1fr}}.kartu>img{{min-height:0;aspect-ratio:16/10}}}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Kegiatan prodi</h1>
    <p>Kuliah tamu, kunjungan lapangan, seminar, pengabdian kepada masyarakat, kompetisi, dan kerja sama program studi.</p>
  </div></div>
  <div class="daftar">{isi}</div>
  {ke_berita}
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Halaman per bidang keahlian (pemilik 2026-11-22): bidang-<nama>.html, satu per kelompok keahlian di config.
# Isi hanya dari data: cakupan (config), MK pilihan (peminatan, patch 145), dosen (kelompok, patch 86), topik riset
# (topik keahlian dosen), penelitian/PkM dan publikasi dosen bidang itu, laboratorium pendukung (patch 147).
BIDANG_MAKS_KARYA = 6


def berkas_bidang(nama: str) -> str:
    """File name of an expertise-group page, e.g. 'Rekayasa Sumber Daya Air' -> 'bidang-rekayasa-sumber-daya-air.html'."""
    return "bidang-" + re.sub(r"[^a-z0-9]+", "-", str(nama).lower()).strip("-") + ".html"


def info_bidang(D: dict) -> list[dict]:
    """Per expertise group (config order): kode, nama, berkas, cakupan, riset (top-5 topic names by lecturer count),
    dosen [{nama, slug}], pilihan (elective course dicts with peminatan == kode, latest curriculum), publikasi and
    kegiatan whose authors include a lecturer of the group (newest first), lab (laboratories whose bidang lists the
    group, patch 147)."""
    s = D.get("situs") or {}
    baku = D.get("keahlian_baku") or {}
    cakupan = {b.get("kode"): b.get("cakupan") for b in baku.get("bidang") or []}
    cakupan |= {x["kode"]: x["cakupan"] for x in s.get("kelompok_keahlian") or [] if x.get("cakupan")}
    nama_topik = {t.get("kode"): t.get("nama") for t in baku.get("topik") or []}
    kur = sorted(D.get("kurikulum") or [], key=lambda k: str(k.get("kode") or ""))
    mk = (kur[-1].get("mk") if kur else None) or []
    semua_slug = {d.get("slug") for d in D.get("dosen") or [] if d.get("slug")}
    out = []
    for x in s.get("kelompok_keahlian") or []:
        if not x.get("nama"):
            continue
        ds = [d for d in D.get("dosen") or [] if d.get("kelompok") == x["kode"] and d.get("nama")]
        hitung: dict[str, int] = {}
        for d in ds:
            for t in dict.fromkeys(d.get("topik_keahlian") or []):
                if nama_topik.get(t):
                    hitung[nama_topik[t]] = hitung.get(nama_topik[t], 0) + 1
        slugs = {d.get("slug") for d in ds if d.get("slug")}

        # Karya milik bidang ini bila ketua/penulis pertama/korespondensinya dosen bidang ini (pemilik 2026-11-22: jangan
        # memasang riset bidang lain hanya karena dosen ini anggota); tanpa dosen prodi di peran utama: semua penulisnya.
        def milik(k):
            ps = [p for p in k.get("penulis") or [] if p.get("slug") in semua_slug]
            utama = [p for p in ps if p.get("peran") in ("ketua", "penulis_pertama") or p.get("korespondensi")]
            return any(p.get("slug") in slugs for p in (utama or ps))
        terbaru = lambda xs: sorted((k for k in xs if milik(k)), key=lambda k: (-int(k.get("tahun") or 0), str(k.get("judul") or "")))
        out.append({"kode": x["kode"], "nama": x["nama"], "berkas": berkas_bidang(x["nama"]),
                    "cakupan": cakupan.get(x["kode"]) or "",
                    "riset": [n for n, _ in sorted(hitung.items(), key=lambda y: (-y[1], y[0]))[:5]],
                    "dosen": [{"nama": nama_dosen(D, d), **({"slug": d["slug"]} if d.get("slug") else {})} for d in ds],
                    "pilihan": [m for m in mk if m.get("sifat") == "pilihan" and m.get("peminatan") == x["kode"]],
                    "publikasi": terbaru(D.get("publikasi") or []), "kegiatan": terbaru(D.get("kegiatan") or []),
                    "lab": [l for l in D.get("laboratorium") or [] if x["kode"] in (l.get("bidang") or [])],
                    # Arsip judul TA (pemilik 2026-11-22), terbaru dulu.
                    "ta": [t for t in D.get("arsip_ta") or [] if t.get("bidang") == x["kode"]]})
    return out


def halaman_bidang(D: dict, b: dict, semua: list[dict], versi: str) -> str:
    """Static bidang-<nama>.html for one expertise group (b from info_bidang); semua = all groups for the nav."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    jenis_keg = {"penelitian": "Penelitian", "pkm": "Pengabdian kepada masyarakat"}
    sks = lambda m: f"{float(m.get('sks') or 0):g}".replace(".", ",")
    bag = []
    if b["pilihan"]:
        aturan = (D.get("situs") or {}).get("aturan_pilihan") or ""
        bag.append('<section><h2>Mata kuliah pilihan bidang ini</h2><p class="ket">Diambil untuk mendalami bidang ini, '
                   f'selain mata kuliah wajib.{(" " + e(aturan)) if aturan else ""} <a href="kurikulum.html">Kurikulum lengkap</a>.</p><ul class="mk">'
                   + "".join(f'<li><span class="kode">{e(m.get("kode") or "")}</span>'
                             + (f'<a href="{e(m["berkas"])}">{e(m["nama"])}</a>' if m.get("berkas") else e(m["nama"]))
                             + f'<span class="sks">{sks(m)} sks</span></li>' for m in b["pilihan"]) + "</ul></section>")
    if b["dosen"]:
        bag.append('<section><h2>Dosen</h2><ul class="dosen">'
                   + "".join(f'<li><a href="dosen/{e(d["slug"])}.html">{e(d["nama"])}</a></li>' if d.get("slug")
                             else f'<li>{e(d["nama"])}</li>' for d in b["dosen"])
                   + "</ul>" + (f'<p><b>Topik riset dosen:</b> {e(", ".join(b["riset"]))}</p>' if b["riset"] else "") + "</section>")
    if b.get("ta"):
        bag.append('<section><h2>Tugas akhir terbaru</h2><ol class="karya">'
                   + "".join(f'<li><span class="tag">Tugas akhir · {e(t["tahun"])}</span>{e(t["judul"])}</li>' for t in b["ta"][:BIDANG_MAKS_KARYA])
                   + f'</ol><p class="ket">{len(b["ta"])} judul tugas akhir di bidang ini. '
                     f'<a href="tugas-akhir.html#bidang-{e(b["kode"].lower())}">Arsip tugas akhir</a></p></section>')
    if b.get("lab"):
        bag.append('<section><h2>Laboratorium pendukung</h2><ul class="dosen">'
                   + "".join(f'<li><a href="laboratorium.html#lab-{e(l["id"])}">{e(l["nama"])}</a></li>' for l in b["lab"])
                   + "</ul></section>")
    if b["kegiatan"]:
        bag.append(f'<section><h2>Penelitian dan pengabdian</h2><ol class="karya">'
                   + "".join(f'<li><span class="tag">{e(jenis_keg.get(k.get("kategori"), "Kegiatan"))} · {e(k.get("tahun") or "")}'
                             + (f' · melibatkan {e(k["mahasiswa"])} mahasiswa' if k.get("mahasiswa") else "")
                             + f'</span>{e(k.get("judul") or "")}</li>' for k in b["kegiatan"][:BIDANG_MAKS_KARYA]) + "</ol>"
                   + (f'<p class="ket">{len(b["kegiatan"])} kegiatan tercatat. <a href="daftar.html?jenis=penelitian">Semua penelitian</a></p>'
                      if len(b["kegiatan"]) > BIDANG_MAKS_KARYA else "") + "</section>")
    if b["publikasi"]:
        bag.append(f'<section><h2>Publikasi terbaru</h2><ol class="karya">'
                   + "".join(f'<li><span class="tag">{e(p.get("tahun") or "")}' + (f' · {e(p["terbitan"])}' if p.get("terbitan") else "")
                             + "</span>" + (f'<a href="{e(p["url"])}" rel="noopener">{e(p.get("judul") or "")}</a>'
                                            if str(p.get("url") or "").startswith("https://") else e(p.get("judul") or ""))
                             + "</li>" for p in b["publikasi"][:BIDANG_MAKS_KARYA]) + "</ol>"
                   + f'<p class="ket">{len(b["publikasi"])} publikasi dosen bidang ini tercatat. '
                     f'<a href="daftar.html?jenis=publikasi">Semua publikasi</a></p></section>')
    if not bag:
        bag.append('<p class="kosong">Rincian bidang ini sedang dilengkapi.</p>')
    kini = ' aria-current="page"'
    lain = "".join(f'<a href="{e(x["berkas"])}"{kini if x["kode"] == b["kode"] else ""}>{e(x["nama"])}</a>' for x in semua)
    deskripsi = (f'{b["nama"]} di {nama_ps}: ' + (f'{b["cakupan"]}. ' if b["cakupan"] else "")
                 + f'{len(b["pilihan"])} mata kuliah pilihan, {len(b["dosen"])} dosen.')
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>{e(b["nama"])} — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="{e(deskripsi)}">
<meta property="og:title" content="{e(b["nama"])} — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:960px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,46px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:680px}}
.angka{{display:flex;flex-wrap:wrap;gap:22px;margin-top:16px}}
.angka b{{display:block;font-family:var(--serif);font-size:28px;line-height:1}}
.angka span{{font-size:12.5px;color:var(--biru-m4)}}
nav.lain{{max-width:960px;margin:0 auto;padding:14px 20px 0;display:flex;flex-wrap:wrap;gap:6px}}
nav.lain a{{font-size:13px;padding:3px 10px;border:1px solid var(--line);background:#fff;color:var(--biru-2);text-decoration:none}}
nav.lain a[aria-current]{{background:var(--biru);border-color:var(--biru);color:#fff}}
.isi{{max-width:960px;margin:0 auto;padding:8px 20px 30px}}
h2{{font-family:var(--serif);font-size:23px;color:var(--biru);margin:24px 0 8px}}
.ket{{color:var(--muted)}}
ul.mk,ul.dosen{{list-style:none;padding:0;margin:0;background:#fff;border:1px solid var(--line)}}
ul.mk li,ul.dosen li{{display:flex;gap:10px;align-items:baseline;padding:8px 12px;border-top:1px solid var(--line)}}
ul.mk li:first-child,ul.dosen li:first-child{{border-top:0}}
.kode{{font-family:var(--mono);font-size:12px;color:var(--muted);min-width:46px}}
.sks{{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--muted);white-space:nowrap}}
ol.karya{{list-style:none;padding:0;margin:0;display:grid;gap:8px}}
ol.karya li{{background:#fff;border:1px solid var(--line);padding:10px 14px}}
.tag{{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
.ajak{{max-width:960px;margin:0 auto;padding:0 20px 34px;display:flex;flex-wrap:wrap;gap:10px}}
.ajak a{{padding:9px 16px;background:var(--aksen);color:var(--biru-gelap);font-weight:600;text-decoration:none}}
.kosong{{color:var(--muted)}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps} · Bidang keahlian</div>
    <h1>{e(b["nama"])}</h1>
    {f'<p>{e(b["cakupan"])}.</p>' if b["cakupan"] else ""}
    <div class="angka">{"".join(f"<div><b>{n}</b><span>{l}</span></div>" for n, l in ((len(b["pilihan"]), "mata kuliah pilihan"),
        (len(b["dosen"]), "dosen"), (len(b["kegiatan"]), "penelitian dan pengabdian"), (len(b["publikasi"]), "publikasi")) if n)}</div>
  </div></div>
  <nav class="lain" aria-label="Bidang keahlian lain">{lain}</nav>
  <div class="isi">{"".join(bag)}</div>
  <div class="ajak"><a href="calon-mahasiswa.html#kuis">Coba kuis minat bidang</a><a href="kurikulum.html">Kurikulum</a>
    <a href="keahlian.html">Kepakaran dosen</a></div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Halaman per mata kuliah (pemilik 2026-11-22): mk-<kode>-<nama>.html, hanya untuk kurikulum terbaru. Silabus hanya versi
# yang sudah disahkan Kaprodi (mk_silabus.sah, patch 129); draf dan catatan impor tidak pernah keluar. Pengampu tidak
# ditampilkan (berganti tiap semester; tetap kolom internal, lihat bangun.kurikulum_publik).
SILABUS_PUBLIK = ("nama_en", "tujuan", "tujuan_en", "deskripsi", "deskripsi_en", "prasyarat", "bersamaan", "pustaka")


def berkas_mk(kode: str, nama: str) -> str:
    """File name of a course page, e.g. ('41413', 'Hidrologi Terapan') -> 'mk-41413-hidrologi-terapan.html'."""
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return "-".join(x for x in ("mk", slug(kode), slug(nama)) if x) + ".html"


def berkas_mk_en(kode: str, nama_en: str) -> str:
    """English course page, e.g. ('41413', 'Advanced Hydrology') -> 'course-41413-advanced-hydrology.html'."""
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return "-".join(x for x in ("course", slug(kode), slug(nama_en)) if x) + ".html"


def lengkapi_mk_terbaru(kurikulum: list[dict], silabus: list[dict]) -> list[dict]:
    """Mark the courses of the newest curriculum (kurikulum[0], newest first as from bangun.kurikulum_publik) with
    berkas (their page) and, when the Kaprodi has approved one, silabus: the approved copy (sah) with allow-listed
    keys only, plus disahkan (date). silabus: mk_silabus rows {kurikulum, kode_mk, sah, sah_pada}. In place; returned."""
    if not kurikulum:
        return kurikulum
    k = kurikulum[0]
    sah: dict[str, dict] = {}
    for r in silabus or []:
        if str(r.get("kurikulum") or "").strip().upper() != str(k.get("kode") or "").upper() or not isinstance(r.get("sah"), dict):
            continue
        d = {f: str(r["sah"].get(f) or "").strip() for f in SILABUS_PUBLIK}
        d = {f: v for f, v in d.items() if v}
        if d:
            sah[str(r.get("kode_mk") or "").strip()] = {**d, **({"disahkan": str(r["sah_pada"])[:10]} if r.get("sah_pada") else {})}
    for m in k.get("mk") or []:
        if m.get("kode") and m.get("nama"):
            m["berkas"] = berkas_mk(m["kode"], m["nama"])
            m["berkas_en"] = berkas_mk_en(m["kode"], m.get("nama_en") or m["nama"])
            if str(m["kode"]).strip() in sah:
                m["silabus"] = sah[str(m["kode"]).strip()]
    return kurikulum


def info_mk(D: dict) -> list[dict]:
    """Courses that get a page: those marked by lengkapi_mk_terbaru (newest curriculum only)."""
    kur = D.get("kurikulum") or []
    return [m for m in (kur[0].get("mk") if kur else None) or [] if m.get("berkas")]


CSS_MK = """*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}
.kepala{background:var(--biru);color:#fff}
.kepala-in{max-width:900px;margin:0 auto;padding:36px 20px 28px}
.jejak{font-size:13px;color:var(--biru-m4)}
.jejak a{color:#fff}
.eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2);margin-top:12px}
h1{font-family:var(--serif);font-size:clamp(28px,4.4vw,42px);margin:6px 0 4px;line-height:1.1}
.en-nama{margin:0;color:var(--biru-m4);font-style:italic}
.isi{max-width:900px;margin:0 auto;padding:18px 20px 34px}
dl.fakta{display:grid;gap:6px;margin:0;background:#fff;border:1px solid var(--line);padding:14px 18px}
dl.fakta div{display:grid;grid-template-columns:150px 1fr;gap:12px}
dt{font-family:var(--mono);font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding-top:3px}
dd{margin:0}
dd a,.isi a{color:var(--biru-2)}
h2{font-family:var(--serif);font-size:22px;color:var(--biru);margin:24px 0 8px}
h3{font-size:16px;margin:12px 0 4px}
.teks p{margin:0 0 10px;max-width:760px}
.ket{color:var(--muted)}
ul.cpl,ul.daftar{list-style:none;padding:0;margin:0;background:#fff;border:1px solid var(--line)}
ul.cpl li,ul.daftar li{display:flex;gap:12px;align-items:baseline;padding:8px 12px;border-top:1px solid var(--line)}
ul.cpl li:first-child,ul.daftar li:first-child{border-top:0}
.kode{font-family:var(--mono);font-size:12px;color:var(--muted);min-width:34px}
.sks{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--muted);white-space:nowrap}
ol.pustaka{margin:0;padding-left:22px}
ol.pustaka li{margin:3px 0}
details.en{margin-top:22px;background:#fff;border:1px solid var(--line);padding:10px 16px}
details.en summary{cursor:pointer;font-weight:600;color:var(--biru)}
@media (max-width:560px){dl.fakta div{grid-template-columns:1fr;gap:0}}
.bahasa{margin:10px 0 0}
.bahasa a{color:#fff;font-size:13px;border:1px solid rgba(255,255,255,.5);padding:2px 10px;text-decoration:none}
.bahasa a:hover{background:rgba(255,255,255,.12)}
"""


def halaman_mk(D: dict, m: dict, versi: str) -> str:
    """Static mk-<kode>-<nama>.html for one course of the newest curriculum: identity (sks, semester and stage, wajib or
    pilihan, expertise group), CPL with wording, approved syllabus (Indonesian, English in a fold), laboratories that use
    it, and other courses of the same semester (or the same group for electives)."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    s = D.get("situs") or {}
    kur = (D.get("kurikulum") or [{}])[0]
    angka = lambda x: f"{float(x or 0):g}".replace(".", ",")
    paras = lambda t: "".join(f"<p>{e(x.strip())}</p>" for x in re.split(r"\n\s*\n", t) if x.strip())
    kel = {x["kode"]: x for x in [*(s.get("kelompok_keahlian") or []), *(s.get("peminatan_lain") or [])] if x.get("kode")}
    kk = {x.get("kode") for x in s.get("kelompok_keahlian") or []}
    sil = m.get("silabus") or {}
    nama_en = m.get("nama_en") or sil.get("nama_en") or ""
    pilihan = m.get("sifat") == "pilihan"

    b = m.get("bagian") or {}
    rinci = [f"{l} {angka(b[k])}" for k, l in (("kuliah", "kuliah"), ("seminar", "seminar"), ("praktikum", "praktikum")) if b.get(k)]
    fakta = [("Kode", e(m["kode"])),
             ("Beban", f'{angka(m.get("sks"))} sks' + (f' ({", ".join(rinci)})' if len(rinci) > 1 else ""))]
    if m.get("semester"):
        tahap = (s.get("tahap") or {}).get(str(m["semester"]))
        fakta.append(("Semester", f'{e(m["semester"])}' + (f" · {e(tahap)}" if tahap else "")))
    fakta.append(("Sifat", "Pilihan" if pilihan else "Wajib") if not m.get("capstone") else
                 ("Sifat", ("Pilihan" if pilihan else "Wajib") + " · capstone"))
    pem = kel.get(m.get("peminatan"))
    if pem:
        fakta.append(("Bidang", f'<a href="{e(berkas_bidang(pem["nama"]))}">{e(pem["nama"])}</a>' if pem["kode"] in kk
                      else e(pem["nama"])))
    if m.get("unit") == "universitas":
        fakta.append(("Penyelenggara", "Universitas (mata kuliah bersama)"))
    if kur.get("kode"):
        fakta.append(("Kurikulum", e(kur["kode"])))

    bag = []
    if sil.get("deskripsi"):
        bag.append(f'<section><h2>Deskripsi</h2><div class="teks">{paras(sil["deskripsi"])}</div></section>')
    if sil.get("tujuan"):
        bag.append(f'<section><h2>Tujuan</h2><div class="teks">{paras(sil["tujuan"])}</div></section>')
    cpl = {c.get("kode"): c for c in kur.get("cpl") or []}
    if m.get("cpl"):
        bag.append('<section><h2>Capaian pembelajaran lulusan yang didukung</h2><ul class="cpl">'
                   + "".join(f'<li><span class="kode">{e(c)}</span><span>{e((cpl.get(c) or {}).get("rumusan") or "")}</span></li>'
                             for c in m["cpl"])
                   + '</ul><p class="ket"><a href="kurikulum.html#cpl">Semua CPL</a></p></section>')
    syarat = [(l, sil[k]) for k, l in (("prasyarat", "Prasyarat"), ("bersamaan", "Diambil bersamaan dengan")) if sil.get(k)]
    if syarat:
        bag.append('<section><h2>Mata kuliah terkait</h2><dl class="fakta">'
                   + "".join(f"<div><dt>{l}</dt><dd>{e(t)}</dd></div>" for l, t in syarat) + "</dl></section>")
    pustaka = [x.strip() for x in str(sil.get("pustaka") or "").splitlines() if x.strip()]
    if pustaka:
        bag.append('<section><h2>Pustaka</h2><ol class="pustaka">' + "".join(f"<li>{e(x)}</li>" for x in pustaka) + "</ol></section>")
    if sil.get("deskripsi_en") or sil.get("tujuan_en"):
        bag.append('<details class="en" lang="en"><summary>In English</summary>'
                   + (f'<h3>Course description</h3><div class="teks">{paras(sil["deskripsi_en"])}</div>' if sil.get("deskripsi_en") else "")
                   + (f'<h3>Objectives</h3><div class="teks">{paras(sil["tujuan_en"])}</div>' if sil.get("tujuan_en") else "")
                   + "</details>")
    if sil:
        if sil.get("disahkan"):
            t = sil["disahkan"]
            bag.append(f'<p class="ket">Silabus disahkan Ketua Program Studi pada {int(t[8:10])} {BULAN_ID[int(t[5:7])]} {t[:4]}.</p>')
    else:
        bag.append('<p class="ket">Silabus lengkap mata kuliah ini tampil di sini setelah disahkan Ketua Program Studi.</p>')
    lab = [l for l in D.get("laboratorium") or [] if any(x.get("kode") == m["kode"] for x in l.get("mk") or [])]
    if lab:
        bag.append('<section><h2>Laboratorium</h2><ul class="daftar">'
                   + "".join(f'<li><a href="laboratorium.html#lab-{e(l["id"])}">{e(l["nama"])}</a></li>' for l in lab) + "</ul></section>")
    if pilihan:
        lain = [x for x in info_mk(D) if x is not m and x.get("sifat") == "pilihan" and x.get("peminatan") == m.get("peminatan")]
        judul_lain = f'Mata kuliah pilihan lain bidang {e(pem["nama"])}' if pem else "Mata kuliah pilihan lain"
    else:
        lain = [x for x in info_mk(D) if x is not m and m.get("semester") and x.get("semester") == m.get("semester")]
        judul_lain = f'Mata kuliah lain di semester {e(m.get("semester"))}'
    if lain:
        bag.append(f'<section><h2>{judul_lain}</h2><ul class="daftar">'
                   + "".join(f'<li><a href="{e(x["berkas"])}">{e(x["nama"])}</a><span class="sks">{angka(x.get("sks"))} sks</span></li>'
                             for x in lain) + "</ul></section>")

    teks_ld = sil.get("deskripsi") or ""
    deskripsi = (f'{m["nama"]} ({m["kode"]}), {angka(m.get("sks"))} sks, mata kuliah {"pilihan" if pilihan else "wajib"} '
                 f'{nama_ps}' + (f'. {teks_ld[:180].rsplit(" ", 1)[0]}…' if len(teks_ld) > 180 else (f". {teks_ld}" if teks_ld else "")))
    ld = {"@context": "https://schema.org", "@type": "Course", "name": m["nama"], "courseCode": m["kode"],
          **({"alternateName": nama_en} if nama_en else {}), **({"description": teks_ld[:500]} if teks_ld else {}),
          "provider": {"@type": "CollegeOrUniversity", "name": inst or f"Program Studi {prodi}"}}
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>{e(m["nama"])} — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="{e(deskripsi)}">
<meta property="og:title" content="{e(m["nama"])} — {nama_ps}">
<script type="application/ld+json">{ld_json}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
{CSS_MK}</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <nav class="jejak" aria-label="Jejak halaman"><a href="index.html">Beranda</a> › <a href="kurikulum.html">Kurikulum</a> › {e(m["nama"])}</nav>
    <div class="eyebrow">{nama_ps} · Mata kuliah</div>
    <h1>{e(m["nama"])}</h1>
    {f'<p class="en-nama" lang="en">{e(nama_en)}</p>' if nama_en else ""}
    {f'<p class="bahasa"><a href="{e(m["berkas_en"])}" lang="en" hreflang="en">English</a></p>' if s.get("prodi_en") and m.get("berkas_en") else ""}
  </div></div>
  <div class="isi">
    <dl class="fakta">{"".join(f"<div><dt>{l}</dt><dd>{x}</dd></div>" for l, x in fakta)}</dl>
    {"".join(bag)}
  </div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


BULAN_EN = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November", "December"]


def halaman_mk_en(D: dict, m: dict, versi: str) -> str:
    """Static course-<kode>-<name>.html, the English twin of halaman_mk (owner 2026-11-22): only made when
    programme_name_en is set (english.html exists). Same rules: approved syllabus only, no lecturers."""
    s = D.get("situs") or {}
    inst = D.get("institusi") or ""
    prog = f'{s.get("prodi_en") or D.get("prodi") or ""} Study Program'.strip()
    v = f"?v={e(versi)}" if versi else ""
    kur = (D.get("kurikulum") or [{}])[0]
    angka = lambda x: f"{float(x or 0):g}"
    paras = lambda t: "".join(f"<p>{e(x.strip())}</p>" for x in re.split(r"\n\s*\n", t) if x.strip())
    nm = lambda x: x.get("nama_en") or (x.get("silabus") or {}).get("nama_en") or x.get("nama") or ""
    kel = {x["kode"]: x for x in [*(s.get("kelompok_keahlian") or []), *(s.get("peminatan_lain") or [])] if x.get("kode")}
    sil = m.get("silabus") or {}
    pilihan = m.get("sifat") == "pilihan"
    b = m.get("bagian") or {}
    rinci = [f"{l} {angka(b[k])}" for k, l in (("kuliah", "lecture"), ("seminar", "seminar"), ("praktikum", "practicum")) if b.get(k)]
    fakta = [("Code", e(m["kode"])),
             ("Credits", f'{angka(m.get("sks"))} credits' + (f' ({", ".join(rinci)})' if len(rinci) > 1 else ""))]
    if m.get("semester"):
        fakta.append(("Semester", e(m["semester"])))
    fakta.append(("Type", ("Elective" if pilihan else "Compulsory") + (" · capstone" if m.get("capstone") else "")))
    pem = kel.get(m.get("peminatan"))
    if pem:
        fakta.append(("Expertise group", e(pem.get("nama_en") or pem["nama"])))
    if m.get("unit") == "universitas":
        fakta.append(("Offered by", "University (shared course)"))
    if kur.get("kode"):
        fakta.append(("Curriculum", e(kur["kode"])))
    bag = []
    if sil.get("deskripsi_en"):
        bag.append(f'<section><h2>Course description</h2><div class="teks">{paras(sil["deskripsi_en"])}</div></section>')
    if sil.get("tujuan_en"):
        bag.append(f'<section><h2>Objectives</h2><div class="teks">{paras(sil["tujuan_en"])}</div></section>')
    cpl = {c.get("kode"): c for c in kur.get("cpl") or []}
    if m.get("cpl"):
        bag.append('<section><h2>Programme learning outcomes supported</h2><ul class="cpl">'
                   + "".join(f'<li><span class="kode">{e(c)}</span><span>{e((cpl.get(c) or {}).get("rumusan_en") or (cpl.get(c) or {}).get("rumusan") or "")}</span></li>'
                             for c in m["cpl"]) + '</ul><p class="ket"><a href="english.html#outcomes">All learning outcomes</a></p></section>')
    syarat = [(l, sil[k]) for k, l in (("prasyarat", "Prerequisites"), ("bersamaan", "Co-requisites")) if sil.get(k)]
    if syarat:
        bag.append('<section><h2>Related courses</h2><dl class="fakta">'
                   + "".join(f"<div><dt>{l}</dt><dd>{e(t)}</dd></div>" for l, t in syarat) + "</dl></section>")
    pustaka = [x.strip() for x in str(sil.get("pustaka") or "").splitlines() if x.strip()]
    if pustaka:
        bag.append('<section><h2>References</h2><ol class="pustaka">' + "".join(f"<li>{e(x)}</li>" for x in pustaka) + "</ol></section>")
    if sil.get("disahkan"):
        t = sil["disahkan"]
        bag.append(f'<p class="ket">Syllabus approved by the Head of Study Program on {int(t[8:10])} {BULAN_EN[int(t[5:7])]} {t[:4]}.</p>')
    elif not sil:
        bag.append('<p class="ket">The full syllabus will appear here once approved by the Head of Study Program.</p>')
    lab = [l for l in D.get("laboratorium") or [] if any(x.get("kode") == m["kode"] for x in l.get("mk") or [])]
    if lab:
        bag.append('<section><h2>Laboratories</h2><ul class="daftar">'
                   + "".join(f'<li><a href="laboratorium.html#lab-{e(l["id"])}" hreflang="id">{e(l["nama"])}</a></li>' for l in lab) + "</ul></section>")
    if pilihan:
        lain = [x for x in info_mk(D) if x is not m and x.get("sifat") == "pilihan" and x.get("peminatan") == m.get("peminatan")]
        judul_lain = f'Other electives in {e(pem.get("nama_en") or pem["nama"])}' if pem else "Other electives"
    else:
        lain = [x for x in info_mk(D) if x is not m and m.get("semester") and x.get("semester") == m.get("semester")]
        judul_lain = f'Other courses in semester {e(m.get("semester"))}'
    if lain:
        bag.append(f'<section><h2>{judul_lain}</h2><ul class="daftar">'
                   + "".join(f'<li><a href="{e(x["berkas_en"])}">{e(nm(x))}</a><span class="sks">{angka(x.get("sks"))} credits</span></li>'
                             for x in lain if x.get("berkas_en")) + "</ul></section>")
    judul = nm(m)
    teks_ld = sil.get("deskripsi_en") or ""
    deskripsi = (f'{judul} ({m["kode"]}), {angka(m.get("sks"))} credits, {"elective" if pilihan else "compulsory"} course, {prog}'
                 + (f", {inst}" if inst else "") + (f'. {teks_ld[:180].rsplit(" ", 1)[0]}…' if len(teks_ld) > 180 else (f". {teks_ld}" if teks_ld else "")))
    ld = {"@context": "https://schema.org", "@type": "Course", "name": judul, "courseCode": m["kode"], "inLanguage": "en",
          **({"description": teks_ld[:500]} if teks_ld else {}),
          "provider": {"@type": "CollegeOrUniversity", "name": inst or prog}}
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>{e(judul)} — {e(prog)}{(" " + e(inst)) if inst else ""}</title>
<meta name="description" content="{e(deskripsi)}">
<meta property="og:title" content="{e(judul)} — {e(prog)}">
<script type="application/ld+json">{ld_json}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
{CSS_MK}</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <nav class="jejak" aria-label="Breadcrumb"><a href="index.html" hreflang="id">Home</a> › <a href="english.html">Programme overview</a> › {e(judul)}</nav>
    <div class="eyebrow">{e(prog)}{(", " + e(inst)) if inst else ""} · Course</div>
    <h1>{e(judul)}</h1>
    <p class="en-nama" lang="id">{e(m["nama"])}</p>
    <p class="bahasa"><a href="{e(m["berkas"])}" lang="id" hreflang="id">Bahasa Indonesia</a></p>
  </div></div>
  <div class="isi">
    <dl class="fakta">{"".join(f"<div><dt>{l}</dt><dd>{x}</dd></div>" for l, x in fakta)}</dl>
    {"".join(bag)}
  </div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Kalender akademik (instal-lengkap.sql, pemilik 2026-11-22): diisi admin di Data prodi, tampil di
# layanan-mahasiswa.html. Kegiatan yang sudah lewat lebih dari KALENDER_LEWAT_HARI hari tidak dimuat.
KALENDER_LEWAT_HARI = 60
KATEGORI_KALENDER = {"registrasi", "perkuliahan", "ujian", "tugas_akhir", "kerja_praktik", "yudisium", "libur", "lainnya"}


def kalender_publik(rows: list[dict], hari: str) -> list[dict]:
    """Academic calendar for data.json: rows with tampil true whose end (selesai, else mulai) is no more than
    KALENDER_LEWAT_HARI days before hari (YYYY-MM-DD, WIB); sorted by start date. Allow-listed keys only."""
    from datetime import date, timedelta
    batas = (date.fromisoformat(hari) - timedelta(days=KALENDER_LEWAT_HARI)).isoformat()
    out = []
    for r in rows or []:
        kegiatan, semester = str(r.get("kegiatan") or "").strip(), str(r.get("semester") or "").strip()
        if r.get("tampil") is False or not r.get("mulai") or not kegiatan or not semester:
            continue
        mulai = str(r["mulai"])[:10]
        selesai = str(r["selesai"])[:10] if r.get("selesai") else None
        if (selesai or mulai) < batas:
            continue
        kat = r.get("kategori") if r.get("kategori") in KATEGORI_KALENDER else "lainnya"
        out.append({"semester": semester, "kegiatan": kegiatan, "kategori": kat, "mulai": mulai,
                    **({"selesai": selesai} if selesai and selesai != mulai else {}),
                    **({"catatan": str(r["catatan"]).strip()} if str(r.get("catatan") or "").strip() else {})})
    out.sort(key=lambda x: (x["mulai"], x["kegiatan"]))
    return out


def halaman_biaya(D: dict, versi: str) -> str:
    """Static biaya-beasiswa.html (owner 2026-11-22): links to the university's official cost, admission, and
    scholarship pages from config public_site.costs_scholarships, without any figures (they change yearly)."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    s = D.get("situs") or {}
    host = lambda u: re.sub(r"^https://(www\.)?", "", u).split("/")[0]
    kartu = "".join(f'<a class="kartu" href="{e(x["url"])}" target="_blank" rel="noopener"><h2>{e(x["judul"])}</h2>'
                    + (f'<p>{e(x["ket"])}</p>' if x.get("ket") else "")
                    + f'<span class="host">{e(host(x["url"]))} ↗</span></a>' for x in s.get("biaya") or [])
    daftar = s.get("pendaftaran") or ""
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Biaya dan beasiswa — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Biaya pendidikan, pendaftaran, dan beasiswa untuk calon mahasiswa {nama_ps}: tautan ke halaman resmi universitas.">
<meta property="og:title" content="Biaya dan beasiswa — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:900px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,44px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:680px}}
.isi{{max-width:900px;margin:0 auto;padding:24px 20px 36px}}
.kisi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}}
a.kartu{{display:flex;flex-direction:column;background:#fff;border:1px solid var(--line);border-top:4px solid var(--aksen);padding:16px 18px;
  color:var(--ink);text-decoration:none}}
a.kartu:hover{{border-color:var(--biru)}}
a.kartu h2{{font-family:var(--serif);font-size:20px;color:var(--biru);margin:0 0 6px}}
a.kartu p{{margin:0 0 10px;color:var(--ink)}}
.host{{margin-top:auto;font-family:var(--mono);font-size:12px;color:var(--biru-2)}}
h2.sub{{font-family:var(--serif);font-size:22px;color:var(--biru);margin:28px 0 8px}}
.ket{{color:var(--muted)}}
.ajak{{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}}
.ajak a{{padding:9px 16px;background:var(--aksen);color:var(--biru-gelap);font-weight:600;text-decoration:none}}
.ajak a.lain{{background:#fff;border:1px solid var(--line);color:var(--biru)}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps} · Calon mahasiswa</div>
    <h1>Biaya dan beasiswa</h1>
    <p>Biaya pendidikan, jalur masuk, dan beasiswa ditetapkan universitas dan dapat berubah setiap tahun. Karena itu halaman ini
      tidak memuat angka; rinciannya ada di halaman resmi berikut.</p>
  </div></div>
  <div class="isi">
    <div class="kisi">{kartu}</div>
    <h2 class="sub">Masih ada pertanyaan?</h2>
    <p>Tanyakan kepada program studi tentang kuliah di {e(prodi)}, atau hubungi Penerimaan Mahasiswa Baru untuk biaya dan beasiswa.</p>
    <div class="ajak">{f'<a href="{e(daftar)}" target="_blank" rel="noopener">Daftar sekarang</a>' if daftar else ""}
      <a class="lain" href="layanan-mahasiswa.html#kirim">Tanya prodi</a><a class="lain" href="calon-mahasiswa.html">Untuk calon mahasiswa</a></div>
  </div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'mahasiswa' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Arsip judul tugas akhir (pemilik 2026-11-22): tugas-akhir.html, per bidang lalu per tahun; tanpa nama mahasiswa.
ARSIP_TA_MIN_SITEMAP = 5   # arsip masuk sitemap.xml mulai 5 judul (halaman tipis merugikan penilaian mesin pencari)


def halaman_arsip_ta(D: dict, versi: str) -> str:
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    s = D.get("situs") or {}
    xs = D.get("arsip_ta") or []
    kel = [*(s.get("kelompok_keahlian") or []), *(s.get("peminatan_lain") or [])]
    kk = {x.get("kode") for x in s.get("kelompok_keahlian") or []}
    kode_dikenal = {x.get("kode") for x in kel}
    grup = [(x["kode"], x["nama"]) for x in kel if any(t.get("bidang") == x["kode"] for t in xs)]
    if any(t.get("bidang") not in kode_dikenal for t in xs):
        grup.append(("", "Bidang lain"))

    def orang(o):
        return f'<a href="dosen/{e(o["slug"])}.html">{e(o["nama"])}</a>' if o.get("slug") else e(o["nama"])

    def butir(t):
        pemb = ", ".join(orang(o) for o in t.get("pembimbing") or [])
        return f'<li id="ta-{e(t["id"])}">{e(t["judul"])}' + (f"<span>Pembimbing: {pemb}</span>" if pemb else "") + "</li>"

    def daftar(ts):
        tahun = sorted({t["tahun"] for t in ts}, reverse=True)
        return "".join(f'<h3>{y}</h3><ol class="ta">' + "".join(butir(t) for t in ts if t["tahun"] == y) + "</ol>" for y in tahun)
    bag = []
    for kode, nama in grup:
        ts = [t for t in xs if (t.get("bidang") == kode if kode else t.get("bidang") not in kode_dikenal)]
        judul = f'<a href="{e(berkas_bidang(nama))}">{e(nama)}</a>' if kode in kk else e(nama)
        bag.append(f'<section id="bidang-{e(kode.lower() or "lain")}"><h2>{judul} <small>{len(ts)} judul</small></h2>{daftar(ts)}</section>')
    nav = ("<nav class=\"lompat\" aria-label=\"Bidang\">" + "".join(f'<a href="#bidang-{e(k.lower() or "lain")}">{e(n)}</a>' for k, n in grup)
           + "</nav>") if len(grup) > 1 else ""
    isi = "".join(bag) if xs else '<p class="kosong">Arsip judul tugas akhir akan tampil di sini setelah sidang akhir pertama dicatat.</p>'
    th = sorted({t["tahun"] for t in xs})
    rentang = (f"{th[0]}–{th[-1]}" if th[0] != th[-1] else str(th[0])) if th else ""
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Arsip tugas akhir — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Judul tugas akhir mahasiswa {nama_ps} per bidang keahlian{(" " + rentang) if rentang else ""}: {len(xs)} judul.">
<meta property="og:title" content="Arsip tugas akhir — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:960px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,44px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:680px}}
.lompat{{max-width:960px;margin:0 auto;padding:14px 20px 0;display:flex;flex-wrap:wrap;gap:6px}}
.lompat a{{font-size:13px;padding:3px 10px;border:1px solid var(--line);background:#fff;color:var(--biru-2);text-decoration:none}}
.isi{{max-width:960px;margin:0 auto;padding:8px 20px 34px}}
section{{scroll-margin-top:90px}}
h2{{font-family:var(--serif);font-size:23px;color:var(--biru);margin:26px 0 6px}}
h2 a{{color:inherit}}
h2 small{{font-family:var(--mono);font-size:12px;color:var(--muted);font-weight:400;margin-left:8px}}
h3{{font-family:var(--mono);font-size:12.5px;letter-spacing:.08em;color:var(--muted);margin:14px 0 6px}}
ol.ta{{list-style:none;padding:0;margin:0;background:#fff;border:1px solid var(--line)}}
ol.ta li{{padding:9px 14px;border-top:1px solid var(--line);scroll-margin-top:90px}}
ol.ta li:first-child{{border-top:0}}
ol.ta li:target{{background:var(--biru-m11,#eef3fb)}}
ol.ta span{{display:block;font-size:13px;color:var(--muted)}}
ol.ta a{{color:var(--biru-2)}}
.kosong{{color:var(--muted)}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps} · Mahasiswa</div>
    <h1>Arsip tugas akhir</h1>
    <p>Judul tugas akhir mahasiswa yang telah lulus sidang akhir, per bidang keahlian{(", " + rentang) if rentang else ""}.
      Nama mahasiswa tidak dicantumkan.</p>
  </div></div>
  {nav}
  <div class="isi">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'mahasiswa' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


def halaman_kontak(D: dict, versi: str) -> str:
    """Static kontak.html (owner 2026-11-22): address with a map link, phone, email, service hours (config
    public_site.contact), the Tanya prodi form, social media, and admission. Only made when a contact is set."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    s = D.get("situs") or {}
    k = s.get("kontak") or {}
    from urllib.parse import quote
    baris = []
    if k.get("address"):
        peta = "https://www.google.com/maps/search/?api=1&query=" + quote(k["address"])
        baris.append(("Alamat", f'{e(k["address"])}<br><a href="{e(peta)}" target="_blank" rel="noopener">Buka di peta ↗</a>'))
    if k.get("phone"):
        baris.append(("Telepon", f'<a href="tel:{e(re.sub(r"[^0-9+]", "", k["phone"].split("(")[0]))}">{e(k["phone"])}</a>'))
    if k.get("email"):
        baris.append(("Email", f'<a href="mailto:{e(k["email"])}">{e(k["email"])}</a>'))
    if k.get("hours"):
        baris.append(("Jam layanan", e(k["hours"])))
    sosial = {"instagram": "Instagram", "instagram_himpunan": "Instagram himpunan mahasiswa", "youtube": "YouTube", "linkedin": "LinkedIn"}
    sos = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(sosial.get(n, n))}</a></li>' for n, u in (s.get("sosial") or {}).items() if u)
    daftar = s.get("pendaftaran") or ""
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Kontak — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Kontak dan lokasi {nama_ps}: alamat, telepon, email, dan formulir pertanyaan.">
<meta property="og:title" content="Kontak — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:900px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,44px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:680px}}
.isi{{max-width:900px;margin:0 auto;padding:24px 20px 36px;display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:20px}}
.kotak{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--aksen);padding:16px 20px}}
dl{{margin:0;display:grid;gap:12px}}
dt{{font-family:var(--mono);font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
dd{{margin:2px 0 0}}
a{{color:var(--biru-2)}}
h2{{font-family:var(--serif);font-size:20px;color:var(--biru);margin:0 0 8px}}
ul{{margin:0;padding-left:18px}}
.tombol{{display:inline-block;margin-top:8px;padding:9px 16px;background:var(--aksen);color:var(--biru-gelap);font-weight:600;text-decoration:none}}
.ket{{color:var(--muted);font-size:14px}}
@media (max-width:700px){{.isi{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Kontak</h1>
    <p>Alamat, telepon, dan email, serta formulir untuk bertanya langsung kepada program studi.</p>
  </div></div>
  <div class="isi">
    <div class="kotak"><dl>{"".join(f"<div><dt>{l}</dt><dd>{x}</dd></div>" for l, x in baris)}</dl></div>
    <div>
      <div class="kotak"><h2>Bertanya kepada prodi</h2>
        <p>Pertanyaan tentang kuliah, tugas akhir, kerja praktik, atau layanan lain dijawab program studi.</p>
        <a class="tombol" href="layanan-mahasiswa.html#kirim">Tanya prodi</a></div>
      {f'<div class="kotak" style="margin-top:16px"><h2>Media sosial</h2><ul>{sos}</ul></div>' if sos else ""}
      {f'<div class="kotak" style="margin-top:16px"><h2>Calon mahasiswa</h2><p><a href="{e(daftar)}" target="_blank" rel="noopener">Pendaftaran mahasiswa baru ↗</a><br><a href="calon-mahasiswa.html">Untuk calon mahasiswa</a></p></div>' if daftar else ""}
    </div>
  </div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'kontak' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Umpan RSS kabar dan prestasi (pemilik 2026-11-22): feed.xml, hanya bila alamat situs diketahui (alamat lengkap wajib).
UMPAN_MAKS = 30


def umpan_rss(D: dict, base_url: str) -> str:
    from email.utils import format_datetime
    from datetime import datetime, timezone
    nama = " ".join(x for x in (f"Program Studi {D.get('prodi') or ''}".strip(), D.get("institusi") or "") if x)
    xs = []
    for k in D.get("kabar") or []:
        if k.get("judul") and len(str(k.get("tanggal") or "")) >= 10:
            xs.append((str(k["tanggal"])[:10], k["judul"], k.get("ringkasan") or "", f"kabar.html#kabar-{k.get('id')}", "Kegiatan prodi"))
    for p in D.get("prestasi") or []:
        if p.get("tahun"):
            judul = " — ".join(x for x in (p.get("capaian"), p.get("kegiatan")) if x)
            ket = ", ".join(str(x) for x in (p.get("tingkat") and f"tingkat {p['tingkat']}", p.get("penyelenggara")) if x)
            xs.append((f"{int(p['tahun']):04d}-{int(p.get('bulan') or 1):02d}-01", judul, ket, f"prestasi.html#prestasi-{p.get('id')}",
                       "Prestasi mahasiswa"))
    xs.sort(key=lambda x: x[0], reverse=True)
    tgl = lambda t: format_datetime(datetime.fromisoformat(t).replace(hour=8, tzinfo=timezone.utc))
    item = "".join(f"  <item><title>{e(j)}</title><link>{e(base_url)}/{e(u)}</link><guid>{e(base_url)}/{e(u)}</guid>"
                   f"<pubDate>{tgl(t)}</pubDate><category>{e(c)}</category>"
                   + (f"<description>{e(d)}</description>" if d else "") + "</item>\n" for t, j, d, u, c in xs[:UMPAN_MAKS])
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>\n'
            f"  <title>{e(nama)}: kabar dan prestasi</title>\n  <link>{e(base_url)}/</link>\n"
            f"  <description>Kegiatan prodi dan prestasi mahasiswa {e(nama)}.</description>\n  <language>id</language>\n"
            f'  <atom:link href="{e(base_url)}/feed.xml" rel="self" type="application/rss+xml"/>\n'
            + item + "</channel></rss>\n")


# Galeri foto (pemilik 2026-11-22): tanpa unggahan terpisah; foto diambil dari kabar kegiatan (termasuk kiriman
# mahasiswa yang sudah diverifikasi, patch 144), prestasi mahasiswa, dan laboratorium yang sudah tampil di situs.
GALERI_MIN_SITEMAP = 6   # galeri masuk sitemap.xml mulai 6 foto (halaman tipis merugikan penilaian mesin pencari)
GALERI_MIN_CALON = 3     # cuplikan "Suasana kegiatan" di calon-mahasiswa.html mulai 3 foto
BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
            "November", "Desember"]


def foto_galeri(D: dict) -> list[dict]:
    """Photos already published on the site, newest first: {src, judul, sumber, href, tahun, bulan}. Labs have no date
    and come last. Student names are not used (prestasi caption = capaian and kegiatan only)."""
    out = []
    for x in D.get("kabar") or []:
        t = str(x.get("tanggal") or "")
        th, bl = (int(t[:4]), int(t[5:7])) if re.match(r"\d{4}-\d{2}", t) else (0, 0)
        out += [{"src": f, "judul": x.get("judul") or "", "sumber": "Kegiatan prodi", "href": f"kabar.html#kabar-{x.get('id')}",
                 "tahun": th, "bulan": bl} for f in x.get("foto") or []]
    for x in D.get("prestasi") or []:
        judul = " — ".join(y for y in (x.get("capaian"), x.get("kegiatan")) if y)
        out += [{"src": f, "judul": judul, "sumber": "Prestasi mahasiswa", "href": f"prestasi.html#prestasi-{x.get('id')}",
                 "tahun": int(x.get("tahun") or 0), "bulan": int(x.get("bulan") or 0)} for f in x.get("foto") or []]
    for x in D.get("laboratorium") or []:
        out += [{"src": f, "judul": x.get("nama") or "", "sumber": "Laboratorium", "href": f"laboratorium.html#lab-{x.get('id')}",
                 "tahun": 0, "bulan": 0} for f in x.get("foto") or []]
    out = [f for f in out if f["src"]]
    out.sort(key=lambda f: (-f["tahun"], -f["bulan"]))   # stabil: urutan asal dalam bulan yang sama
    return out


def halaman_galeri(D: dict, versi: str) -> str:
    """Static galeri.html: photo grid per year (labs under "Fasilitas"), each photo links to its card."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    fs = foto_galeri(D)
    grup: dict = {}
    for f in fs:
        grup.setdefault(f["tahun"], []).append(f)

    def sel(f):
        kapan = f" · {BULAN_ID[f['bulan']]} {f['tahun']}" if f["bulan"] else (f" · {f['tahun']}" if f["tahun"] else "")
        return (f'<a class="foto" href="{e(f["href"])}"><img src="{e(f["src"])}{v}" alt="{e(f["judul"])}" loading="lazy">'
                f'<span><small>{e(f["sumber"])}{kapan}</small>{e(f["judul"])}</span></a>')
    isi = "".join(f'<section><h2>{e(th) if th else "Fasilitas"}</h2><div class="kisi">{"".join(sel(f) for f in xs)}</div></section>'
                  for th, xs in grup.items()) or (
        '<p class="kosong">Foto kegiatan program studi akan tampil di sini, diambil dari <a href="kabar.html">kegiatan prodi</a>, '
        '<a href="prestasi.html">prestasi mahasiswa</a>, dan <a href="laboratorium.html">laboratorium</a>.</p>')
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Galeri foto — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Foto kegiatan, prestasi mahasiswa, dan laboratorium {nama_ps}.">
<meta property="og:title" content="Galeri foto — {nama_ps}">
{f'<meta property="og:image" content="{e(fs[0]["src"])}">' if fs else ""}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 34px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:640px}}
.isi{{max-width:1080px;margin:0 auto;padding:24px 20px 28px}}
h2{{font-family:var(--serif);font-size:24px;color:var(--biru);margin:18px 0 10px}}
.kisi{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}}
.foto{{display:block;background:#fff;border:1px solid var(--line);color:var(--ink);text-decoration:none}}
.foto img{{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:var(--biru-m10)}}
.foto span{{display:block;padding:8px 10px 10px;font-size:14px;line-height:1.35}}
.foto small{{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:2px}}
.foto:hover span{{color:var(--biru-2)}}
.kosong{{color:var(--muted)}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Galeri foto</h1>
    <p>Suasana kegiatan, prestasi mahasiswa, dan fasilitas laboratorium. Klik foto untuk membaca ceritanya.</p>
  </div></div>
  <div class="isi">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Laboratorium (pemilik 2026-11-16; instal-lengkap.sql).
FOTO_PER_LAB = 6
JENIS_KARYA = {"penelitian": "Penelitian", "pkm": "Pengabdian"}


def laboratorium_publik(rows: list[dict], alat: list[dict], dosen: dict, kurikulum: list[dict],
                        kegiatan: dict) -> list[dict]:
    """Laboratories shown on laboratorium.html, by urutan then name; rows with tampil false are left out.
    alat: lkps_prasarana rows (LKPS 5.a), matched on prasarana name (lab.prasarana, else lab.nama);
    only tool name and number owned go public. dosen: NIDN -> {nama, slug}. kurikulum: data.json
    kurikulum (course names, first curriculum wins). kegiatan: karya id -> {judul, tahun, kategori,
    skema}, verified research/PkM only; ids not in it are left out. Photos as Drive ids in _foto."""
    nama_mk = {}
    for k in kurikulum or []:
        for m in k.get("mk") or []:
            nama_mk.setdefault(str(m.get("kode") or "").strip(), m.get("nama") or "")
    urut = lambda r: (r.get("urutan") if r.get("urutan") is not None else 100, str(r.get("nama") or r.get("alat") or ""))
    out = []
    for r in sorted(rows, key=urut):
        nama = (r.get("nama") or "").strip()
        if not nama or r.get("tampil") is False:
            continue
        ruang = (r.get("prasarana") or nama).strip().casefold()
        daftar_alat = [{"nama": a["alat"].strip(), **({"jumlah": a["jumlah_dimiliki"]} if a.get("jumlah_dimiliki") else {})}
                       for a in sorted(alat, key=urut)
                       if (a.get("prasarana") or "").strip().casefold() == ruang and (a.get("alat") or "").strip()]
        kepala = dosen.get(str(r.get("kepala_nidn") or "").strip())
        mk = [{"kode": k, "nama": nama_mk[k]} for k in dict.fromkeys(str(x).strip() for x in r.get("mata_kuliah") or [])
              if k in nama_mk]
        riset = [kegiatan[str(i)] for i in dict.fromkeys(r.get("penelitian") or []) if str(i) in kegiatan]
        riset.sort(key=lambda x: (-int(x.get("tahun") or 0), x.get("judul") or ""))
        ids = [drive_id(u) for u in r.get("foto") or []]
        out.append({"id": r.get("id"), "nama": nama, "ringkasan": (r.get("ringkasan") or "").strip(),
                    "kepala": ({"nama": kepala["nama"], **({"slug": kepala["slug"]} if kepala.get("slug") else {})}
                               if kepala else None),
                    "mk": mk, "alat": daftar_alat,
                    # Bidang keahlian (patch 147): kode kelompok; kode yang tidak ada di config diabaikan halaman.
                    "bidang": [str(b).strip() for b in r.get("bidang") or [] if str(b).strip()],
                    "layanan": [s.strip() for s in r.get("layanan") or [] if s and s.strip()],
                    "kontak": (r.get("kontak_layanan") or "").strip(),
                    "penelitian": [{"judul": x["judul"], "tahun": x.get("tahun"),
                                    "jenis": JENIS_KARYA.get(x.get("kategori"), "Kegiatan"),
                                    **({"skema": x["skema"]} if x.get("skema") else {})} for x in riset],
                    "_foto": [i for i in dict.fromkeys(ids) if i][:FOTO_PER_LAB]})
    return out


def halaman_laboratorium(D: dict, versi: str) -> str:
    """Static laboratorium.html: each laboratory with photos, coordinator, practicum courses, main
    equipment (LKPS 5.a), testing services, and related research; text in the HTML."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")

    def kontak(t):
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", t):
            return f'<a href="mailto:{e(t)}">{e(t)}</a>'
        return e(t)

    hal_mk = {m["kode"]: m["berkas"] for m in info_mk(D)}   # chip MK -> halaman MK (kurikulum terbaru)

    def bagian(x):
        foto = x.get("foto") or []
        galeri = ""
        if foto:
            kecil = "".join(f'<img src="{e(f)}{v}" alt="" loading="lazy">' for f in foto[1:])
            galeri = (f'<div class="galeri"><img class="utama" src="{e(foto[0])}{v}" alt="{e(x["nama"])}" loading="lazy">'
                      + (f'<div class="kecil">{kecil}</div>' if kecil else "") + "</div>")
        info = []
        if x.get("kepala"):
            k = x["kepala"]
            nm = f'<a href="dosen/{e(k["slug"])}.html">{e(nama_dosen(D, k))}</a>' if k.get("slug") else e(nama_dosen(D, k))
            info.append(f"<div><dt>Koordinator</dt><dd>{nm}</dd></div>")
        kk = {k.get("kode"): k for k in (D.get("situs") or {}).get("kelompok_keahlian") or [] if k.get("nama")}
        bid = [kk[b] for b in x.get("bidang") or [] if b in kk]
        if bid:
            info.append("<div><dt>Bidang keahlian</dt><dd>" + ", ".join(
                f'<a href="{e(berkas_bidang(k["nama"]))}">{e(k["nama"])}</a>' for k in bid) + "</dd></div>")
        if x.get("mk"):
            info.append("<div><dt>Mata kuliah praktikum</dt><dd>" + "".join(
                f'<a class="chip" href="{e(hal_mk.get(m["kode"], "kurikulum.html"))}">{e(m["nama"])}</a>' for m in x["mk"]) + "</dd></div>")
        blok = []
        if x.get("alat"):
            baris = "".join(f'<tr><td>{e(a["nama"])}</td><td class="n">{e(a.get("jumlah") or "")}</td></tr>' for a in x["alat"])
            blok.append(f'<div class="blok"><h3>Peralatan utama</h3><table><thead><tr><th>Alat</th><th class="n">Jumlah</th></tr>'
                        f"</thead><tbody>{baris}</tbody></table></div>")
        if x.get("layanan"):
            hubungi = f'<p class="hub">Permintaan pengujian: {kontak(x["kontak"])}</p>' if x.get("kontak") else ""
            blok.append('<div class="blok"><h3>Layanan pengujian</h3><ul>' + "".join(f"<li>{e(s)}</li>" for s in x["layanan"])
                        + f"</ul>{hubungi}</div>")
        if x.get("penelitian"):
            blok.append('<div class="blok"><h3>Penelitian dan pengabdian terkait</h3><ul class="riset">' + "".join(
                f'<li>{e(p["judul"])}<span>{e(p["jenis"])} · {e(p.get("tahun") or "")}'
                f'{" · " + e(p["skema"]) if p.get("skema") else ""}</span></li>' for p in x["penelitian"]) + "</ul></div>")
        return (f'<section class="lab" id="lab-{e(x["id"])}">{galeri}<div class="isi"><h2>{e(x["nama"])}</h2>'
                f'<p class="ringkas">{e(x["ringkasan"])}</p>'
                + (f'<dl>{"".join(info)}</dl>' if info else "")
                + (f'<div class="blok-grid">{"".join(blok)}</div>' if blok else "") + "</div></section>")

    xs = D.get("laboratorium") or []
    cadangan = (D.get("situs") or {}).get("laboratorium") or []
    if xs:
        isi = "".join(bagian(x) for x in xs)
    elif cadangan:
        isi = '<section class="lab"><div class="isi"><ul class="nama">' + "".join(f"<li>{e(n)}</li>" for n in cadangan) + "</ul></div></section>"
    else:
        isi = '<p class="kosong">Profil laboratorium program studi akan tampil di sini.</p>'
    loncat = ('<nav class="loncat" aria-label="Daftar laboratorium">' + "".join(
        f'<a href="#lab-{e(x["id"])}">{e(x["nama"])}</a>' for x in xs) + "</nav>") if len(xs) > 1 else ""
    gambar = next((x["foto"][0] for x in xs if x.get("foto")), "")
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Laboratorium — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Laboratorium {nama_ps}: fasilitas praktikum, peralatan utama, layanan pengujian, dan penelitian.">
<meta property="og:title" content="Laboratorium — {nama_ps}">
{f'<meta property="og:image" content="{e(gambar)}">' if gambar else ""}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 34px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:640px}}
.loncat{{max-width:1080px;margin:0 auto;padding:18px 20px 0;display:flex;flex-wrap:wrap;gap:8px}}
.loncat a{{padding:5px 12px;border:1px solid var(--line);background:#fff;color:var(--biru);text-decoration:none;font-weight:600;font-size:14px}}
.loncat a:hover{{border-color:var(--biru)}}
.daftar{{max-width:1080px;margin:0 auto;padding:22px 20px 40px;display:grid;gap:24px}}
.lab{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--aksen);overflow:hidden;scroll-margin-top:80px}}
.galeri{{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:4px;background:var(--biru-m10)}}
.galeri:not(:has(.kecil)){{grid-template-columns:1fr}}
.galeri .utama{{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}}
.galeri .kecil{{display:grid;gap:4px;grid-auto-rows:1fr}}
.galeri .kecil img{{width:100%;height:100%;object-fit:cover;display:block;min-height:0}}
.isi{{padding:22px 26px 26px}}
h2{{font-family:var(--serif);font-size:26px;color:var(--biru);margin:0 0 8px;line-height:1.2}}
.ringkas{{margin:0 0 14px;white-space:pre-line;max-width:820px}}
dl{{display:grid;gap:8px;margin:0 0 16px}}
dl div{{display:grid;grid-template-columns:190px 1fr;gap:12px}}
dt{{font-family:var(--mono);font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding-top:3px}}
dd{{margin:0}}
dd a{{color:var(--biru-2);font-weight:600}}
.chip{{display:inline-block;margin:0 6px 6px 0;padding:2px 9px;background:var(--biru-m10);color:var(--biru);font-weight:500 !important;
  text-decoration:none;font-size:14px}}
.blok-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px 26px;border-top:1px solid var(--line);padding-top:16px}}
h3{{font-size:16px;margin:0 0 8px;color:var(--ink)}}
table{{width:100%;border-collapse:collapse;font-size:14.5px}}
th{{text-align:left;font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:500;
  border-bottom:1px solid var(--line);padding:4px 0}}
td{{border-bottom:1px solid var(--line-soft);padding:5px 0}}
.n{{text-align:right;width:70px}}
ul{{margin:0;padding-left:18px}}
li{{margin:3px 0}}
.riset li span{{display:block;font-size:13px;color:var(--muted)}}
.hub{{margin:10px 0 0;font-size:14.5px}}
.nama li{{font-weight:600}}
.kosong{{color:var(--muted)}}
@media(max-width:700px){{dl div{{grid-template-columns:1fr;gap:2px}}.galeri{{grid-template-columns:1fr}}
  .galeri .kecil{{grid-template-columns:repeat(3,1fr);grid-auto-rows:auto}}.galeri .kecil img{{aspect-ratio:4/3}}.isi{{padding:18px}}}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Laboratorium</h1>
    <p>Fasilitas praktikum dan penelitian program studi: peralatan utama, mata kuliah praktikum, layanan pengujian, dan
      kegiatan riset yang memakainya.</p>
  </div></div>
  {loncat}
  <div class="daftar">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Kerja sama (pemilik 2026-11-16; instal-lengkap.sql). Menggantikan mitra.html (kini pengalih).
JENIS_KS = {"pendidikan": "Pendidikan", "penelitian": "Penelitian", "pkm": "Pengabdian kepada masyarakat"}
JENIS_KARYA_KS = {"publikasi": "Publikasi", "penelitian": "Penelitian", "pkm": "Pengabdian"}
URUT_TINGKAT = {"internasional": 0, "nasional": 1, "wilayah": 2, "wilayah_lokal": 2}


def kerjasama_publik(rows: list[dict], hari_ini: str) -> list[dict]:
    """Formal agreements (lkps_kerjasama) for kerja-sama.html: partner, kind, level, activity title,
    benefit, validity and whether still in force on hari_ini (YYYY-MM-DD). Rows marked
    sembunyikan_publik are left out; tautan_bukti and jenis_bukti never go public. In force first,
    then newest start."""
    out = []
    for r in rows:
        mitra = (r.get("mitra") or "").strip()
        if not mitra or r.get("sembunyikan_publik"):
            continue
        mulai = str(r.get("tanggal_mulai") or "")[:10] or (str(int(r["tahun_mulai"])) if r.get("tahun_mulai") else "")
        selesai = str(r.get("tanggal_selesai") or "")[:10] or (str(int(r["tahun_selesai"])) if r.get("tahun_selesai") else "")
        # Tanpa tanggal/tahun akhir: masih berlaku. Tahun saja: berlaku sampai akhir tahun itu.
        aktif = not selesai or (selesai >= hari_ini if len(selesai) == 10 else int(selesai) >= int(hari_ini[:4]))
        out.append({"id": r.get("id"), "mitra": mitra, "jenis": r.get("jenis") or "", "tingkat": r.get("tingkat") or "",
                    "kegiatan": (r.get("kegiatan") or "").strip(), "manfaat": (r.get("manfaat") or "").strip(),
                    "mulai": mulai, "selesai": selesai, "aktif": aktif})
    aktif = sorted([x for x in out if x["aktif"]], key=lambda x: x["mulai"], reverse=True)
    lalu = sorted([x for x in out if not x["aktif"]], key=lambda x: x["mulai"], reverse=True)
    return aktif + lalu


def mitra_karya(D: dict) -> list[dict]:
    """Partners named on publications, research and PkM (data.json mitra lists), grouped by name
    without case (as the old mitra.html did), with their joint works newest first; most works first."""
    peta = {}
    for x in [*(dict(p, kategori="publikasi") for p in D.get("publikasi") or []), *(D.get("kegiatan") or [])]:
        for m in x.get("mitra") or []:
            nama = (m.get("nama") or "").strip()
            if not nama:
                continue
            g = peta.setdefault(nama.casefold(), {"nama": nama, "tingkat": "", "negara": "", "karya": []})
            g["tingkat"] = g["tingkat"] or (m.get("tingkat") or "")
            g["negara"] = g["negara"] or (m.get("negara") or "").strip()
            g["karya"].append({"judul": x.get("judul") or "", "tahun": x.get("tahun"), "jenis": x.get("kategori") or ""})
    for g in peta.values():
        g["karya"].sort(key=lambda k: (-int(k.get("tahun") or 0), k["judul"]))
    return sorted(peta.values(), key=lambda g: (-len(g["karya"]), g["nama"].casefold()))


def halaman_kerjasama(D: dict, versi: str) -> str:
    """Static kerja-sama.html: formal agreements (in force first) and partners in research and
    community service grouped by level; text in the HTML."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    resmi = D.get("kerja_sama") or []
    karya = mitra_karya(D)

    def masa(x):
        def f(t):
            if len(t) == 10:
                y, m, d = t.split("-")
                return f"{int(d)}/{int(m)}/{y}"
            return t
        if x["mulai"] and x["selesai"]:
            return f"{f(x['mulai'])} – {f(x['selesai'])}"
        if x["mulai"]:
            return f"sejak {f(x['mulai'])}"
        return f"s.d. {f(x['selesai'])}" if x["selesai"] else ""

    def kartu_resmi(x):
        status = '<span class="st aktif">Berlaku</span>' if x["aktif"] else '<span class="st">Berakhir</span>'
        tag = "".join(f'<span class="tag">{e(t)}</span>' for t in
                      (JENIS_KS.get(x["jenis"], ""), TINGKAT.get(x["tingkat"], "")) if t)
        return (f'<article class="ks{"" if x["aktif"] else " lalu"}"><div class="ks-kepala"><h3>{e(x["mitra"])}</h3>{status}</div>'
                f'<div class="meta">{tag}<span>{e(masa(x))}</span></div>'
                + (f'<p class="keg">{e(x["kegiatan"])}</p>' if x["kegiatan"] else "")
                + (f'<p class="manfaat">{e(x["manfaat"])}</p>' if x["manfaat"] else "") + "</article>")

    def mitra(g):
        n = len(g["karya"])
        daftar = "".join(f'<li>{e(k["judul"])}<span>{e(JENIS_KARYA_KS.get(k["jenis"], "Karya"))} · {e(k.get("tahun") or "")}</span></li>'
                         for k in g["karya"])
        negara = f' · {e(g["negara"])}' if g["negara"] and g["negara"].casefold() != "indonesia" else ""
        return (f'<details class="mitra"><summary><b>{e(g["nama"])}</b><span>{n} karya bersama{negara}</span></summary>'
                f'<ul>{daftar}</ul></details>')

    kelompok = []
    for kode, judul in (("internasional", "Internasional"), ("nasional", "Nasional"), ("wilayah_lokal", "Wilayah dan lokal"), ("", "Lainnya")):
        xs = [g for g in karya if (g["tingkat"] if g["tingkat"] in URUT_TINGKAT else "") == kode
              or (kode == "wilayah_lokal" and g["tingkat"] == "wilayah")]
        if xs:
            kelompok.append(f'<h3 class="kel">{judul} <span>{len(xs)}</span></h3><div class="mitra-daftar">{"".join(mitra(g) for g in xs)}</div>')

    nama_semua = {g["nama"].casefold() for g in karya} | {x["mitra"].casefold() for x in resmi}
    intl = {g["nama"].casefold() for g in karya if g["tingkat"] == "internasional"} | \
           {x["mitra"].casefold() for x in resmi if x["tingkat"] == "internasional"}
    # Negara mitra luar negeri saja (pemilik 2026-11-17: Indonesia tidak dihitung; Jepang + Malaysia = 2).
    negara = {g["negara"].casefold() for g in karya if g["negara"] and g["negara"].casefold() != "indonesia"}
    # Angka kerja sama resmi hanya bila sudah ada yang diisi (bukan "0" selama tabelnya kosong).
    angka = [(len(nama_semua), "Institusi mitra"),
             *([(sum(1 for x in resmi if x["aktif"]), "Kerja sama resmi berlaku")] if resmi else []),
             (len(intl), "Mitra internasional"), (len(negara), "Negara")]
    ringkas = "".join(f"<div><b>{n}</b><span>{e(l)}</span></div>" for n, l in angka)
    bagian_resmi = (f'<section class="bag"><h2>Kerja sama resmi</h2><p class="ket">Nota kesepahaman, perjanjian kerja sama, '
                    f'dan implementasi kerja sama program studi di bidang pendidikan, penelitian, dan pengabdian.</p>'
                    f'<div class="ks-daftar">{"".join(kartu_resmi(x) for x in resmi)}</div></section>') if resmi else ""
    bagian_karya = (f'<section class="bag"><h2>Mitra dalam riset dan pengabdian</h2><p class="ket">Lembaga yang terlibat dalam '
                    f'publikasi, penelitian, dan pengabdian kepada masyarakat dosen program studi.</p>{"".join(kelompok)}</section>'
                    ) if karya else ""
    # Tempat KP dan magang (pemilik 2026-11-17): instansi, bidang, jumlah mahasiswa, tahun; tanpa nama mahasiswa.
    kp = D.get("tempat_kp") or []

    def baris_kp(x):
        th = (f'{x["tahun_awal"]}' + (f'–{x["tahun_akhir"]}' if x["tahun_akhir"] != x["tahun_awal"] else "")) if x.get("tahun_awal") else ""
        jumlah = " · ".join(t for t in ((f'{x["kp"]} KP' if x["kp"] else ""), (f'{x["magang"]} magang' if x["magang"] else "")) if t)
        return (f'<tr><td><b>{e(x["instansi"])}</b>' + (f'<span>{e(", ".join(x["bidang"]))}</span>' if x["bidang"] else "")
                + f'</td><td>{e(jumlah)}</td><td>{e(th)}</td></tr>')
    bagian_kp = (f'<section class="bag" id="tempat-kp"><h2>Tempat KP dan magang mahasiswa</h2><p class="ket">Instansi tempat mahasiswa '
                 f'menjalani kerja praktik dan magang yang disetujui program studi. Nama mahasiswa tidak ditampilkan.</p>'
                 f'<div class="gulir"><table class="kp"><thead><tr><th>Instansi dan bidang</th><th>Mahasiswa</th><th>Tahun</th></tr></thead>'
                 f'<tbody>{"".join(baris_kp(x) for x in kp)}</tbody></table></div></section>') if kp else ""
    isi = bagian_resmi + bagian_karya + bagian_kp or '<p class="kosong">Kerja sama program studi akan tampil di sini.</p>'
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Kerja sama — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Kerja sama {nama_ps} dengan perguruan tinggi, industri, dan pemerintah di bidang pendidikan, penelitian, dan pengabdian kepada masyarakat.">
<meta property="og:title" content="Kerja sama — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:660px}}
.ringkas{{max-width:1080px;margin:0 auto;padding:0 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0;
  transform:translateY(-1px)}}
.ringkas div{{background:var(--biru-gelap);color:#fff;padding:14px 18px;border-left:1px solid rgba(255,255,255,.15)}}
.ringkas b{{display:block;font-family:var(--serif);font-size:30px;line-height:1.1}}
.ringkas span{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--biru-m4)}}
.isi{{max-width:1080px;margin:0 auto;padding:10px 20px 50px}}
.bag{{margin-top:26px}}
h2{{font-family:var(--serif);font-size:28px;color:var(--biru);margin:0 0 4px}}
.ket{{color:var(--muted);margin:0 0 14px;max-width:760px}}
.ks-daftar{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}}
.ks{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--aksen);padding:16px 18px}}
.ks.lalu{{border-top-color:var(--line);opacity:.85}}
.ks-kepala{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}}
h3{{font-size:17px;margin:0;line-height:1.3}}
.st{{flex:none;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;padding:2px 7px;
  border:1px solid var(--line);color:var(--muted)}}
.st.aktif{{background:var(--biru);border-color:var(--biru);color:#fff}}
.meta{{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:8px 0 0;font-size:13px;color:var(--muted)}}
.tag{{padding:1px 7px;background:var(--biru-m10);color:var(--biru);font-size:12.5px}}
.keg{{margin:10px 0 0;font-weight:600}}
.manfaat{{margin:6px 0 0;color:var(--ink);white-space:pre-line}}
h3.kel{{font-family:var(--mono);font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:22px 0 8px;
  font-weight:500}}
h3.kel span{{color:var(--biru)}}
.mitra-daftar{{background:#fff;border:1px solid var(--line)}}
.mitra{{border-bottom:1px solid var(--line-soft)}}
.mitra:last-child{{border-bottom:0}}
.mitra summary{{cursor:pointer;padding:11px 16px;display:flex;justify-content:space-between;gap:12px;list-style:none}}
.mitra summary::-webkit-details-marker{{display:none}}
.mitra summary b{{font-weight:600}}
.mitra summary span{{flex:none;font-size:13px;color:var(--muted)}}
.mitra summary:hover b{{color:var(--biru)}}
.mitra ul{{margin:0;padding:0 16px 12px 34px;font-size:14.5px}}
.mitra li{{margin:4px 0}}
.mitra li span{{display:block;font-size:12.5px;color:var(--muted)}}
.kosong{{color:var(--muted)}}
.gulir{{overflow-x:auto}}
table.kp{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);font-size:14.5px}}
table.kp th{{text-align:left;font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
  font-weight:500;padding:9px 14px;border-bottom:1px solid var(--line)}}
table.kp td{{padding:9px 14px;border-bottom:1px solid var(--line-soft);vertical-align:top}}
table.kp td span{{display:block;font-size:12.5px;color:var(--muted)}}
table.kp td:not(:first-child){{white-space:nowrap}}
@media(max-width:760px){{.ringkas{{grid-template-columns:1fr 1fr}}.mitra summary{{flex-direction:column;gap:0}}}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Kerja sama</h1>
    <p>Kerja sama dengan perguruan tinggi, industri, dan pemerintah dalam pendidikan, penelitian, dan pengabdian kepada
      masyarakat.</p>
  </div></div>
  <div class="ringkas">{ringkas}</div>
  <div class="isi">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


# Profil program studi (pemilik 2026-11-16; instal-lengkap.sql).
# Label publik (huruf kecil dipakai di "Visi fakultas"); istilah UPPS tidak dikenal pembaca umum (2026-11-21).
LABEL_VMTS = {"ps": "Program studi", "upps": "Fakultas", "pt": "Universitas"}
BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
            "November", "Desember"]


def tanggal_id(t: str) -> str:
    """YYYY-MM-DD -> '1 Januari 2030'; other text unchanged."""
    try:
        y, m, d = str(t)[:10].split("-")
        return f"{int(d)} {BULAN_ID[int(m)]} {y}"
    except (ValueError, IndexError):
        return str(t or "")


def testimoni_publik(rows: list[dict]) -> list[dict]:
    """Testimonials for calon-mahasiswa.html (instal-lengkap.sql, owner 2026-11-21): only rows with a
    recorded consent date and tampil true; consent fields never leave this function. Order: urutan, id."""
    out = []
    for r in sorted(rows or [], key=lambda r: (r.get("urutan") if r.get("urutan") is not None else 100, r.get("id") or 0)):
        if not r.get("persetujuan_tanggal") or r.get("tampil") is False:
            continue
        nama, kutipan = str(r.get("nama") or "").strip(), " ".join(str(r.get("kutipan") or "").split())
        if not nama or not kutipan:
            continue
        x = {"nama": nama, "peran": r.get("peran") or "alumni", "kutipan": kutipan}
        for k in ("angkatan", "tahun_lulus"):
            if isinstance(r.get(k), int):
                x[k] = r[k]
        if str(r.get("pekerjaan") or "").strip():
            x["pekerjaan"] = str(r["pekerjaan"]).strip()
        out.append(x)
    return out


JABATAN_KAPRODI = "Ketua Program Studi"
_BARIS_KAPRODI = re.compile(r"^\s*(ketua\s+program\s+studi|ketua\s+prodi|kaprodi)\s*$", re.I)


def kaprodi_aktif(koordinator: list[dict], nidn_per_id: dict, hari: str) -> str | None:
    """NIDN of the head of programme on date hari (YYYY-MM-DD), from koordinator rows with
    jabatan 'kaprodi' (patch 97/100) whose mulai..selesai covers hari; empty selesai = still running.
    The latest start wins when assignments overlap. None when nobody is assigned (owner 2026-11-21:
    Ketua Program Studi and the welcome's signatory follow the assignment, so they change on the
    start date without anyone editing the profile)."""
    berlaku = [r for r in koordinator or []
               if r.get("jabatan") == "kaprodi" and str(r.get("mulai") or "")[:10] <= hari
               and (not r.get("selesai") or hari <= str(r["selesai"])[:10])]
    for r in sorted(berlaku, key=lambda r: str(r.get("mulai") or ""), reverse=True):
        n = str(nidn_per_id.get(str(r.get("dosen_id"))) or "").strip()
        if n:
            return n
    return None


def riwayat_kaprodi(koordinator: list[dict], orang_per_id: dict, hari: str) -> list[dict]:
    """Heads of programme over time (owner 2026-11-22: "historis perkembangan prodi"), oldest first, from koordinator
    rows with jabatan 'kaprodi' that have started by hari. Consecutive terms of the same lecturer (gap <= 1 day or
    overlapping) are merged. orang_per_id: dosen id -> {nama (with titles when filled), slug (only with a public page)}.
    selesai = end date of the (last) SK, None when the assignment has no end date; kini = in office on hari
    (owner 2026-11-22: the period is shown as SK start year - SK end year). Lecturers missing from orang_per_id are
    left out."""
    from datetime import date, timedelta
    xs = sorted((r for r in koordinator or [] if r.get("jabatan") == "kaprodi" and r.get("mulai")
                 and str(r["mulai"])[:10] <= hari and orang_per_id.get(str(r.get("dosen_id")))),
                key=lambda r: str(r["mulai"])[:10])
    out: list[dict] = []
    for r in xs:
        mulai, selesai = str(r["mulai"])[:10], (str(r["selesai"])[:10] if r.get("selesai") else None)
        if out and out[-1]["_id"] == str(r.get("dosen_id")) and (
                out[-1]["selesai"] is None
                or date.fromisoformat(mulai) <= date.fromisoformat(out[-1]["selesai"]) + timedelta(days=1)):
            if out[-1]["selesai"] is not None:
                out[-1]["selesai"] = None if selesai is None else max(selesai, out[-1]["selesai"])
            continue
        out.append({"_id": str(r.get("dosen_id")), **orang_per_id[str(r.get("dosen_id"))], "mulai": mulai, "selesai": selesai})
    for x in out:
        x.pop("_id")
        x["kini"] = x["selesai"] is None or x["selesai"] >= hari
    return out


def profil_publik(profil: list[dict], pengelola: list[dict], dosen: dict,
                  kaprodi_nidn: str | None = None, kaprodi_riwayat: list[dict] | None = None) -> dict:
    """Profile texts and management for profil-prodi.html. profil: profil_prodi rows (one, id 1);
    pengelola: pengelola_prodi rows; dosen: NIDN -> {nama, slug}. A lecturer is named from the
    roster (linked when the lecturer has a page); a non-lecturer by nama. Rows with neither are left out.
    kaprodi_nidn (kaprodi_aktif): when it names a listed lecturer, it heads the list as Ketua Program
    Studi (typed rows with that title are dropped) and signs the welcome instead of penyambut_nidn."""
    def orang(nidn, nama):
        d = dosen.get(str(nidn or "").strip())
        if d:
            return {"nama": d["nama"], **({"slug": d["slug"]} if d.get("slug") else {})}
        return {"nama": nama.strip()} if (nama or "").strip() else None

    p = (profil or [{}])[0]
    kaprodi = dosen.get(str(kaprodi_nidn or "").strip()) and orang(kaprodi_nidn, "")
    urut = sorted(pengelola, key=lambda r: (r.get("urutan") if r.get("urutan") is not None else 100, r.get("id") or 0))
    daftar = [{"jabatan": JABATAN_KAPRODI, **kaprodi}] if kaprodi else []
    for r in urut:
        if kaprodi and _BARIS_KAPRODI.match(r.get("jabatan") or ""):
            continue
        o = orang(r.get("nidn"), r.get("nama"))
        if o and (r.get("jabatan") or "").strip():
            daftar.append({"jabatan": r["jabatan"].strip(), **o})
    penyambut = (kaprodi or orang(p.get("penyambut_nidn"), "")) if p.get("sambutan") else None
    return {k: v for k, v in {"sejarah": (p.get("sejarah") or "").strip(), "sambutan": (p.get("sambutan") or "").strip(),
                              "penyambut": penyambut, "pengelola": daftar,
                              "kaprodi_riwayat": kaprodi_riwayat or []}.items() if v}


def halaman_profil(D: dict, versi: str) -> str:
    """Static profil-prodi.html (layout revised 2026-11-21, owner: "susunannya dibuat lebih bagus"):
    header with live figures, welcome (photo beside text), vision/mission/objectives, graduate profiles of
    the main curriculum, expertise groups and labs, history, accreditation in force, management, and a
    closing call to action. Empty parts are left out; nothing is written that the data does not hold."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    P = D.get("profil") or {}
    s = D.get("situs") or {}
    foto = {d.get("slug"): d.get("foto") for d in D.get("dosen") or [] if d.get("slug")}
    paras = lambda t: "".join(f"<p>{e(x.strip())}</p>" for x in re.split(r"\n\s*\n", t) if x.strip())

    def nama_orang(o, kelas=""):
        return (f'<a{kelas} href="dosen/{e(o["slug"])}.html">{e(nama_dosen(D, o))}</a>' if o.get("slug")
                else f"<span{kelas}>{e(nama_dosen(D, o))}</span>")

    def wajah(o):
        f = foto.get(o.get("slug"))
        if f:
            return f'<img src="{e(f)}{v}" alt="{e(o["nama"])}" loading="lazy">'
        return f'<span class="inisial" aria-hidden="true">{e(inisial(o["nama"]))}</span>'

    bagian, nav = [], []

    def tambah(id_, judul, isi, kelas=""):
        nav.append((id_, judul))
        bagian.append(f'<section class="bag{kelas}" id="{id_}"><h2>{judul}</h2>{isi}</section>')

    # Angka di kepala: hanya dari data yang ada (akreditasi, kurikulum, DTPS, kelompok keahlian, laboratorium).
    ak = D.get("akreditasi_prodi") or {}
    kur = (D.get("kurikulum") or [{}])[0]
    dtps = D.get("dtps") or {}
    kk = [x for x in s.get("kelompok_keahlian") or [] if (x or {}).get("nama")]
    lab = [x for x in s.get("laboratorium") or [] if str(x or "").strip()]
    angka = [(ak.get("peringkat"), "akreditasi"), (kur.get("kode"), "kurikulum berlaku"),
             (dtps.get("dosen_tetap") or dtps.get("jumlah"), "dosen tetap"), (dtps.get("doktor"), "bergelar doktor"),
             (len(kk) or None, "kelompok keahlian"), (len(lab) or None, "laboratorium")]
    blok_angka = "".join(f"<div><b>{e(x)}</b><span>{l}</span></div>" for x, l in angka if x)
    blok_angka = f'<div class="angka">{blok_angka}</div>' if blok_angka else ""

    if P.get("sambutan"):
        o = P.get("penyambut")
        jab = next((x["jabatan"] for x in P.get("pengelola") or [] if o and x["nama"] == o["nama"]), "")
        oleh = (f'<figure class="oleh">{wajah(o)}<figcaption>{nama_orang(o)}<small>{e(jab)}</small></figcaption></figure>'
                if o else "")
        tambah("sambutan", "Sambutan",
               f'<div class="sambutan{" berfoto" if o else ""}">{oleh}<div class="teks">{paras(P["sambutan"])}</div></div>')

    vm = D.get("vmts") or {}
    jenis = next((k for k in ("ps", "upps", "pt") if vm.get(k)), None)
    if jenis:
        x = vm[jenis]
        isi = (f'<div class="visi"><small>Visi {e(LABEL_VMTS[jenis].lower())}</small>{e(x["visi"])}</div>' if x.get("visi") else "")
        isi += '<div class="vm-grid">' + "".join(
            f'<div class="vm"><h3>{judul}</h3><div class="teks">{paras(x[k])}</div></div>' for k, judul in
            (("misi", "Misi"), ("tujuan", "Tujuan")) if x.get(k)) + "</div>"
        # Strategi biasanya jauh lebih panjang (K26: 9 butir dengan uraian), jadi dibuka-tutup di bawah kartu
        # misi dan tujuan supaya kartu tetap seimbang (pemilik 2026-11-21).
        if x.get("strategi"):
            butir = len(re.findall(r"(?m)^\s*\d+[.)]\s", x["strategi"]))
            isi += (f'<details class="strategi"><summary><h3>Strategi pencapaian{f" ({butir} butir)" if butir > 1 else ""}</h3>'
                    f'</summary><div class="teks">{paras(x["strategi"])}</div></details>')
        lain = [(k, vm[k]) for k in ("upps", "pt") if k != jenis and vm.get(k) and vm[k].get("visi")]
        isi += "".join(f'<details class="lain"><summary>Visi {e(LABEL_VMTS[k].lower())}</summary><p>{e(y["visi"])}</p></details>'
                       for k, y in lain)
        tambah("visi", "Visi, misi, dan tujuan", isi)

    if kur.get("profil"):
        def pl(p):
            uraian = f'<p>{e(p["deskripsi"])}</p>' if p.get("deskripsi") else ""
            return f'<div class="pl"><span class="kode">{e(p.get("kode") or "")}</span><b>{e(p["nama"])}</b>{uraian}</div>'
        kartu = "".join(pl(p) for p in kur["profil"])
        tambah("profil-lulusan", "Profil lulusan",
               f'<p class="ket">Peran yang disiapkan kurikulum {e(kur.get("kode") or "")} bagi lulusan. Rincian capaian pembelajaran '
               f'dan mata kuliah: <a href="kurikulum.html">Kurikulum</a>.</p><div class="pl-grid">{kartu}</div>')

    if kk or lab:
        kol = []
        if kk:
            kol.append('<div class="bidang"><h3>Kelompok keahlian</h3><ul>'
                       + "".join(f'<li><a href="{e(berkas_bidang(x["nama"]))}">{e(x["nama"])}</a></li>' for x in kk)
                       + '</ul><a class="lanjut" href="keahlian.html">Kepakaran dosen</a></div>')
        if lab:
            kol.append('<div class="bidang"><h3>Laboratorium</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in lab)
                       + '</ul><a class="lanjut" href="laboratorium.html">Fasilitas laboratorium</a></div>')
        tambah("bidang", "Bidang keahlian dan laboratorium", f'<div class="bidang-grid">{"".join(kol)}</div>')

    if P.get("sejarah"):
        tambah("sejarah", "Sejarah", f'<div class="teks sejarah">{paras(P["sejarah"])}</div>')
    # Ketua program studi dari masa ke masa (pemilik 2026-11-22), dari penugasan Kaprodi; terlama di atas.
    if P.get("kaprodi_riwayat"):
        # Periode = tahun awal SK - tahun akhir SK di penugasan (pemilik 2026-11-22); tanpa tanggal selesai: "sekarang".
        baris = "".join(f'<li><span class="urut">{i}</span><div>{nama_orang(o)}<small>{o["mulai"][:4]}–'
                        f'{o["selesai"][:4] if o.get("selesai") else "sekarang"}{" · menjabat" if o.get("kini") else ""}</small></div></li>'
                        for i, o in enumerate(P["kaprodi_riwayat"], 1))
        tambah("kaprodi", "Ketua program studi dari masa ke masa", f'<ol class="riwayat-kaprodi">{baris}</ol>')

    if ak.get("peringkat"):
        sampai = tanggal_id(ak.get("berlaku_sampai") or "")
        rinci = " · ".join(x for x in (e(ak.get("lembaga") or ""), f'SK {e(ak["nomor_sk"])}' if ak.get("nomor_sk") else "",
                                       f"berlaku s.d. {e(sampai)}" if sampai else "") if x)
        tambah("akreditasi", "Akreditasi", f'<div class="akr"><b>{e(ak["peringkat"])}</b><span>{rinci}</span></div>')

    if P.get("pengelola"):
        kartu = "".join(f'<div class="orang">{wajah(o)}<div><small>{e(o["jabatan"])}</small>{nama_orang(o, " class=n")}</div></div>'
                        for o in P["pengelola"])
        tambah("pengelola", "Pengelola program studi", f'<div class="orang-grid">{kartu}</div>')

    tagline = s.get("tagline") or ""
    loncat = ('<nav class="loncat" aria-label="Bagian profil"><div class="loncat-in">'
              + "".join(f'<a href="#{i}">{j}</a>' for i, j in nav) + "</div></nav>") if len(nav) > 1 else ""
    daftar_url = s.get("pendaftaran") or ""
    ajak = ('<section class="ajak"><div><h2>Kenali lebih jauh</h2><p>Kurikulum, dosen, dan kehidupan belajar di program studi.</p></div>'
            '<div class="ajak-tombol"><a href="kurikulum.html">Kurikulum</a><a href="daftar.html?jenis=dosen">Daftar dosen</a>'
            '<a href="calon-mahasiswa.html">Untuk calon mahasiswa</a>'
            + (f'<a class="utama" href="{e(daftar_url)}" rel="noopener">Daftar</a>' if daftar_url else "")
            + "</div></section>") if bagian else ""
    isi = "".join(bagian) or '<p class="kosong">Profil program studi akan tampil di sini.</p>'
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Profil — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Profil {nama_ps}: visi, misi, tujuan, profil lulusan, akreditasi, pengelola, dan sejarah.">
<meta property="og:title" content="Profil — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.65}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:680px;font-size:17px}}
.angka{{display:flex;flex-wrap:wrap;margin-top:24px}}
.angka div{{padding:10px 24px 4px 0;margin-right:24px;border-right:1px solid rgba(255,255,255,.18)}}
.angka div:last-child{{border-right:0;margin-right:0}}
.angka b{{display:block;font-family:var(--mono);font-size:26px;font-weight:400;line-height:1.1}}
.angka span{{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--biru-m2)}}
.loncat{{background:#fff;border-bottom:1px solid var(--line)}}
.loncat-in{{max-width:1080px;margin:0 auto;padding:0 20px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:thin}}
.loncat a{{flex:none;padding:12px 12px;color:var(--biru);text-decoration:none;font-weight:600;font-size:14px;border-bottom:3px solid transparent}}
.loncat a:hover{{border-bottom-color:var(--aksen)}}
.isi{{max-width:1080px;margin:0 auto;padding:6px 20px 30px}}
.bag{{margin-top:40px;scroll-margin-top:80px}}
h2{{font-family:var(--serif);font-size:28px;color:var(--biru);margin:0 0 14px;padding-bottom:6px;border-bottom:3px solid var(--aksen);
  display:table}}
h3{{font-size:16px;margin:0 0 6px;color:var(--biru)}}
.teks p{{margin:0 0 10px;max-width:760px}}
.sambutan{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--biru);padding:24px 28px}}
.sambutan.berfoto{{display:grid;grid-template-columns:180px 1fr;gap:28px;align-items:start}}
.oleh{{margin:0;text-align:center}}
.oleh img, .oleh .inisial{{width:140px;height:140px;margin:0 auto 10px;font-size:40px}}
.oleh a, .oleh span{{font-weight:600;color:var(--biru);text-decoration:none}}
.oleh small{{display:block;color:var(--muted);font-size:12px;font-family:var(--mono);letter-spacing:.06em;text-transform:uppercase;margin-top:2px}}
.visi{{background:var(--biru);color:#fff;padding:22px 26px;font-family:var(--serif);font-size:21px;line-height:1.4}}
.visi small{{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--biru-m4);margin-bottom:6px}}
.vm-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:12px}}
.vm{{background:#fff;border:1px solid var(--line);padding:16px 18px}}
.vm .teks p{{font-size:15px}}
details.strategi{{margin-top:12px;background:#fff;border:1px solid var(--line);border-left:4px solid var(--aksen);padding:0 18px}}
details.strategi summary{{cursor:pointer;padding:14px 0;list-style:none;display:flex;align-items:center;gap:10px}}
details.strategi summary::-webkit-details-marker{{display:none}}
details.strategi summary::before{{content:"+";font-family:var(--mono);font-size:20px;color:var(--biru);width:16px}}
details.strategi[open] summary::before{{content:"−"}}
details.strategi summary h3{{margin:0}}
details.strategi .teks{{padding-bottom:10px}}
details.strategi .teks p{{max-width:none;font-size:15px}}
details.lain{{margin-top:10px;background:#fff;border:1px solid var(--line);padding:8px 14px}}
details.lain summary{{cursor:pointer;font-weight:600;color:var(--biru)}}
details.lain p{{margin:6px 0 2px}}
.ket{{color:var(--muted);margin:0 0 12px}}
.pl-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
.pl{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--aksen);padding:14px 16px}}
.pl .kode{{display:inline-block;font-family:var(--mono);font-size:11px;font-weight:500;background:var(--biru);color:#fff;padding:2px 7px;margin:0 8px 6px 0}}
.pl b{{color:var(--biru);font-size:16px}}
.pl p{{margin:6px 0 0;font-size:14.5px}}
.bidang-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
.bidang{{background:#fff;border:1px solid var(--line);padding:16px 18px}}
.bidang ul{{margin:0 0 10px;padding-left:18px}}
.bidang li{{margin:2px 0}}
.lanjut{{font-weight:600;color:var(--biru);text-decoration:none}}
.lanjut::after{{content:" →"}}
.lanjut:hover{{text-decoration:underline}}
.sejarah{{border-left:3px solid var(--line);padding-left:20px}}
ol.riwayat-kaprodi{{list-style:none;margin:0;padding:0;display:grid;gap:8px;max-width:640px}}
ol.riwayat-kaprodi li{{display:flex;gap:14px;align-items:center;background:#fff;border:1px solid var(--line);padding:10px 16px}}
ol.riwayat-kaprodi .urut{{font-family:var(--serif);font-size:22px;color:var(--biru);min-width:22px}}
ol.riwayat-kaprodi small{{display:block;font-family:var(--mono);font-size:12px;color:var(--muted)}}
.akr{{display:inline-flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;background:#fff;border:1px solid var(--line);border-left:4px solid var(--aksen);padding:14px 20px}}
.akr b{{font-family:var(--serif);font-size:28px;color:var(--biru)}}
.akr span{{color:var(--muted)}}
.orang-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}}
.orang{{display:flex;gap:12px;align-items:center;background:#fff;border:1px solid var(--line);padding:12px 14px}}
.orang small{{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.orang .n{{font-weight:600;color:var(--biru);text-decoration:none}}
.orang a.n:hover{{text-decoration:underline}}
.orang img, .oleh img, .inisial{{flex:none;width:58px;height:58px;border-radius:50%;object-fit:cover;background:var(--biru-m10)}}
.oleh img, .oleh .inisial{{width:140px;height:140px}}
.inisial{{display:grid;place-items:center;font-family:var(--serif);font-weight:600;color:var(--biru);font-size:20px}}
.oleh .inisial{{font-size:44px}}
.ajak{{max-width:1080px;margin:46px auto 50px;padding:24px 28px;background:var(--biru);color:#fff;display:flex;flex-wrap:wrap;
  gap:16px 28px;align-items:center;justify-content:space-between}}
.ajak h2{{color:#fff;border-bottom-color:var(--aksen);font-size:24px;margin-bottom:6px}}
.ajak p{{margin:0;color:var(--biru-m4)}}
.ajak-tombol{{display:flex;flex-wrap:wrap;gap:8px}}
.ajak-tombol a{{padding:9px 16px;border:1px solid rgba(255,255,255,.5);color:#fff;text-decoration:none;font-weight:600;font-size:14.5px}}
.ajak-tombol a:hover{{border-color:#fff}}
.ajak-tombol a.utama{{background:#fff;color:var(--biru);border-color:#fff}}
.kosong{{color:var(--muted)}}
@media (max-width:1120px){{.ajak{{margin-left:20px;margin-right:20px}}}}
@media (max-width:640px){{
  .sambutan.berfoto{{grid-template-columns:1fr;gap:16px}}
  .sambutan{{padding:18px}}
  .oleh img, .oleh .inisial{{width:110px;height:110px}}
  .angka{{display:grid;grid-template-columns:1fr 1fr;gap:4px 16px}}
  .angka div{{padding:8px 0 4px;margin:0;border-right:0}}
  .angka b{{font-size:22px}}
  .ajak{{padding:20px}}
}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{e(inst) or "Profil"}</div>
    <h1>Program Studi {e(prodi)}</h1>
    {f"<p>{e(tagline)}</p>" if tagline else ""}
    {blok_angka}
  </div></div>
  {loncat}
  <div class="isi">{isi}</div>
  {ajak}
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


def halaman_alumni(D: dict, versi: str) -> str:
    """Static alumni.html (owner 2026-11-17): tracer table per graduation year (lkps_tracer_lulusan, data.json
    "tracer") and aggregate tracer-survey answers (data.json "alumni", alumni_ringkas). Aggregates only."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    a, tracer = D.get("alumni") or {}, D.get("tracer") or []
    n = a.get("responden", 0)

    persen = persen_jawaban

    def bilah(judul, xs):
        if not xs:
            return ""
        tot = sum(k for _, k in xs) or 1
        return (f'<div class="kotak"><h3>{e(judul)}</h3><ul class="bilah">'
                + "".join(f'<li><span class="l">{e(t)}</span><span class="b"><i style="width:{100 * k / tot:.0f}%"></i></span>'
                          f'<span class="n">{k}</span></li>' for t, k in xs) + "</ul></div>")

    def sel(x):
        return "—" if x is None else e(f"{x:g}".replace(".", ",") if isinstance(x, float) else x)

    def selisih(k):
        if k.get("lulus") is None or k.get("kerja") is None:
            return "—", ""
        d = round(k["kerja"] - k["lulus"], 2)
        return ("+" if d > 0 else "") + f"{d:g}".replace(".", ","), ("naik" if d >= 0.5 else "")

    angka = []
    lengkap = "status" in a
    if n:
        angka.append((n, "Alumni mengisi tracer"))
    if lengkap:
        p6 = persen(a.get("kerja_6bulan") or [], {"ya", "yes"})
        if p6 is not None:
            angka.append((f"{p6}%", "Bekerja ≤ 6 bulan"))
        if a.get("waktu_tunggu_rerata") is not None:
            angka.append((sel(float(a["waktu_tunggu_rerata"])), "Bulan waktu tunggu (rata-rata)"))
    ringkas = "".join(f"<div><b>{e(x)}</b><span>{e(l)}</span></div>" for x, l in angka)

    bag_tabel = ""
    if tracer:
        bag_tabel = ('<section class="bag"><h2>Lulusan per tahun</h2><p class="ket">Rekap tracer study per tahun lulus. '
                     'Sesuai bidang dan tingkat tempat kerja dihitung dari alumni yang bekerja atau berwirausaha.</p>'
                     '<div class="gulir"><table class="tb"><thead><tr><th>Tahun lulus</th><th>Lulusan</th><th>Terlacak</th>'
                     '<th>Waktu tunggu (bulan)</th><th>Sesuai bidang</th><th>Wilayah/lokal</th><th>Nasional</th><th>Internasional</th>'
                     '</tr></thead><tbody>'
                     + "".join(f'<tr><td>{e(t["tahun_lulus"])}</td><td>{sel(t.get("lulusan"))}</td><td>{sel(t.get("terlacak"))}</td>'
                               f'<td>{sel(t.get("waktu_tunggu_bulan"))}</td><td>{sel(t.get("sesuai_bidang"))}</td>'
                               f'<td>{sel(t.get("kerja_wilayah"))}</td><td>{sel(t.get("kerja_nasional"))}</td>'
                               f'<td>{sel(t.get("kerja_internasional"))}</td></tr>' for t in tracer)
                     + "</tbody></table></div></section>")
    bag_sebaran = ""
    if lengkap:
        kot = "".join(bilah(j, a.get(k)) for j, k in (("Status saat ini", "status"),
                                                      ("Kesesuaian bidang studi dengan pekerjaan", "kesesuaian"),
                                                      ("Tingkat tempat kerja", "tingkat"), ("Jenis instansi", "jenis_instansi"),
                                                      ("Provinsi tempat bekerja", "provinsi")))
        komp = a.get("kompetensi") or []
        tk = ('<div class="kotak lebar"><h3>Kompetensi: dikuasai saat lulus dan diperlukan di pekerjaan (skala 1–5)</h3>'
              '<p class="ket">Selisih = diperlukan di pekerjaan dikurangi dikuasai saat lulus; selisih positif menandai kompetensi yang perlu '
              'diperkuat dalam kurikulum.</p>'
              '<div class="gulir"><table class="tb"><thead><tr><th>Kompetensi</th><th>Saat lulus</th><th>Di pekerjaan</th><th>Selisih</th>'
              '</tr></thead><tbody>'
              + "".join(f'<tr><td>{e(k["nama"])}</td><td>{sel(k.get("lulus"))}</td><td>{sel(k.get("kerja"))}</td>'
                        f'<td class="{selisih(k)[1]}">{selisih(k)[0]}</td></tr>' for k in komp)
              + "</tbody></table></div></div>") if komp else ""
        bag_sebaran = (f'<section class="bag"><h2>Hasil tracer study</h2><p class="ket">Ringkasan jawaban {n} alumni. '
                       f'Nama alumni, tempat kerja, dan pendapatan tidak ditampilkan.</p><div class="kisi">{kot}{tk}</div></section>')
    elif n or a.get("isi"):
        bag_sebaran = (f'<section class="bag"><h2>Hasil tracer study</h2><p class="kosong">Ringkasan tampil setelah minimal '
                       f'{e(a.get("min") or 0)} alumni mengisi tracer study (sekarang {n}).</p></section>')
    ajak = (f'<section class="bag ajak"><h2>Anda alumni?</h2><p class="ket">Bantu kami memperbaiki pendidikan dengan mengisi '
            f'tracer study.</p><a class="tombol" href="survei.html?t={e(a["isi"]["token"])}">'
            f'Isi {e(a["isi"]["judul"])}</a></section>') if a.get("isi") else ""
    isi = bag_sebaran + bag_tabel + ajak or '<p class="kosong">Data alumni dan tracer study akan tampil di sini.</p>'
    blok_ringkas = f'<div class="ringkas">{ringkas}</div>' if ringkas else ""
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Alumni dan tracer study — {nama_ps.replace(', ', ' ', 1) if inst else nama_ps}</title>
<meta name="description" content="Alumni {nama_ps}: waktu tunggu kerja, kesesuaian bidang, tingkat tempat kerja, dan kompetensi lulusan dari tracer study.">
<meta property="og:title" content="Alumni dan tracer study — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:660px}}
.ringkas{{max-width:1080px;margin:0 auto;padding:0 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0}}
.ringkas div{{background:var(--biru-gelap);color:#fff;padding:14px 18px;border-left:1px solid rgba(255,255,255,.15)}}
.ringkas b{{display:block;font-family:var(--serif);font-size:30px;line-height:1.1}}
.ringkas span{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--biru-m4)}}
.isi{{max-width:1080px;margin:0 auto;padding:10px 20px 50px}}
.bag{{margin-top:26px}}
h2{{font-family:var(--serif);font-size:28px;color:var(--biru);margin:0 0 4px}}
h3{{font-size:15px;margin:0 0 10px;line-height:1.3}}
.ket{{color:var(--muted);margin:0 0 14px;max-width:760px}}
.kosong{{color:var(--muted)}}
.kisi{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}}
.kotak{{background:#fff;border:1px solid var(--line);padding:14px 16px}}
.kotak.lebar{{grid-column:1/-1}}
.bilah{{list-style:none;margin:0;padding:0;font-size:14px}}
.bilah li{{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(60px,1fr) 32px;gap:10px;align-items:center;margin:6px 0}}
.bilah .b{{height:8px;background:var(--biru-m10)}}
.bilah .b i{{display:block;height:100%;background:var(--biru);border-radius:0 4px 4px 0}}
.bilah .l{{overflow-wrap:anywhere}}
.bilah .n{{text-align:right;font-family:var(--mono);font-size:13px;color:var(--muted)}}
.gulir{{overflow-x:auto}}
table.tb{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);font-size:14.5px}}
table.tb th{{text-align:left;font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
  font-weight:500;padding:9px 12px;border-bottom:1px solid var(--line)}}
table.tb td{{padding:8px 12px;border-bottom:1px solid var(--line-soft)}}
table.tb td:not(:first-child),table.tb th:not(:first-child){{text-align:right}}
.kotak table.tb{{border:0}}
td.naik{{color:var(--biru);font-weight:700}}
.tombol{{display:inline-block;background:var(--biru);color:#fff;text-decoration:none;padding:10px 18px;font-weight:600}}
.tombol:hover{{background:var(--biru-gelap)}}
@media(max-width:760px){{.ringkas{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Alumni dan tracer study</h1>
    <p>Ke mana lulusan kami bekerja, seberapa cepat, dan seberapa sesuai dengan bidang studinya.</p>
  </div></div>
  {blok_ringkas}
  <div class="isi">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'mahasiswa' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""


def halaman_calon(D: dict, versi: str) -> str:
    """Static calon-mahasiswa.html (owner 2026-11-20): one page for prospective students built only from data already on the
    site (latest curriculum, expertise groups, labs, achievements, research with students, careers, tracer when enough
    respondents). Sections without data are left out; FAQ comes from config public_site.faq (owner fills it)."""
    prodi, inst = D.get("prodi") or "Program Studi", D.get("institusi") or ""
    v = f"?v={e(versi)}" if versi else ""
    nama_ps = f"Program Studi {e(prodi)}" + (f", {e(inst)}" if inst else "")
    s = D.get("situs") or {}
    daftar_url = s.get("pendaftaran") or ""
    kur = sorted(D.get("kurikulum") or [], key=lambda k: str(k.get("kode") or ""))
    k = kur[-1] if kur else {}
    mk = [m for m in k.get("mk") or [] if m.get("sifat") in ("wajib", "pilihan")]
    wajib = [m for m in mk if m.get("sifat") == "wajib" and isinstance(m.get("semester"), int)]
    pilihan = [m for m in mk if m.get("sifat") == "pilihan"]

    def angka(x):
        return f"{x:g}".replace(".", ",")

    def nama_mk(xs, n):
        return ", ".join(e(m["nama"]) for m in xs[:n]) + (", dan lainnya" if len(xs) > n else "")

    prodi_dulu = lambda xs: sorted(xs, key=lambda m: m.get("unit") == "universitas")   # MK prodi lebih dulu

    sks_wajib = sum(float(m.get("sks") or 0) for m in wajib)
    dtps = D.get("dtps") or {}
    prestasi = D.get("prestasi") or []

    ringkas = []
    if wajib:
        ringkas.append((angka(sks_wajib), f"sks wajib ({e(k.get('kode'))})"))
    if pilihan:
        ringkas.append((len(pilihan), "mata kuliah pilihan"))
    if dtps.get("dosen_tetap") or dtps.get("jumlah"):
        ringkas.append((dtps.get("dosen_tetap") or dtps["jumlah"], "dosen tetap"))
    if dtps.get("doktor"):
        ringkas.append((dtps["doktor"], "bergelar doktor"))
    if prestasi:
        ringkas.append((len(prestasi), "prestasi mahasiswa"))
    blok_ringkas = ('<div class="ringkas">' + "".join(f"<div><b>{e(x)}</b><span>{l}</span></div>" for x, l in ringkas)
                    + "</div>") if ringkas else ""

    bag = []
    # Terbaru dari prodi (2026-11-21, pemilik: soft selling "prodi yang hidup"): 4 hal terbaru dari prestasi, kabar,
    # penelitian/PkM, publikasi; paling banyak 2 per jenis. Urut tahun lalu bulan (prestasi/kabar punya bulan). Tanpa nama mahasiswa.
    BULAN = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    calon_baru = []
    for p in prestasi:
        calon_baru.append(((p.get("tahun") or 0, p.get("bulan") or 0), "Prestasi", f'{p.get("capaian") or ""} — {p.get("kegiatan") or ""}',
                           "prestasi.html"))
    for x in D.get("kabar") or []:
        t = str(x.get("tanggal") or "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
            calon_baru.append(((int(t[:4]), int(t[5:7])), "Kabar", x.get("judul") or "", "kabar.html"))
    for x in D.get("kegiatan") or []:
        calon_baru.append(((x.get("tahun") or 0, 0), {"pkm": "Pengabdian"}.get(x.get("kategori"), "Penelitian"), x.get("judul") or "",
                           "daftar.html?jenis=" + ("pkm" if x.get("kategori") == "pkm" else "penelitian")))
    for x in D.get("publikasi") or []:
        calon_baru.append(((x.get("tahun") or 0, 0), "Publikasi", x.get("judul") or "", "daftar.html?jenis=publikasi"))
    pilih_baru, per_jenis = [], {}
    for w, jenis, judul, href in sorted((c for c in calon_baru if c[2].strip(" —") and c[0][0]), key=lambda c: c[0], reverse=True):
        if per_jenis.get(jenis, 0) < 2 and len(pilih_baru) < 4:
            per_jenis[jenis] = per_jenis.get(jenis, 0) + 1
            pilih_baru.append((w, jenis, judul, href))
    if pilih_baru:
        bag.append('<section class="bag"><h2>Terbaru dari program studi</h2><div class="kisi baru">'
                   + "".join(f'<a class="kotak" href="{e(href)}"><span class="tag">{e(jenis)} · '
                             f'{e((BULAN[w[1]] + " ") if 0 < w[1] <= 12 else "")}{e(w[0])}</span><h3>{e(judul)}</h3></a>'
                             for w, jenis, judul, href in pilih_baru) + "</div></section>")
    # Bidang yang dipelajari: kelompok keahlian + cakupan bidang baku dengan kode sama.
    cakupan = {b.get("kode"): b.get("cakupan") for b in ((D.get("keahlian_baku") or {}).get("bidang") or [])}
    # Cakupan dari config prodi (expertise_groups.scope, disusun dari MK, pemilik 2026-11-21) menang atas bidang baku.
    cakupan |= {x["kode"]: x["cakupan"] for x in s.get("kelompok_keahlian") or [] if x.get("cakupan")}
    # Riset dosen per kelompok (pemilik 2026-11-21: "spesifik apa yang diajarkan dan penelitian para dosen", supaya calon
    # mahasiswa tidak berharap lebih): topik keahlian dosen di kelompok itu, urut jumlah dosen, maks. 5. Kosong = tidak tampil.
    nama_topik = {t.get("kode"): t.get("nama") for t in ((D.get("keahlian_baku") or {}).get("topik") or [])}
    riset_kk: dict[str, dict] = {}
    for d in D.get("dosen") or []:
        for t in dict.fromkeys(d.get("topik_keahlian") or []):
            if nama_topik.get(t) and d.get("kelompok"):
                riset_kk.setdefault(d["kelompok"], {}).setdefault(nama_topik[t], 0)
                riset_kk[d["kelompok"]][nama_topik[t]] += 1
    riset_kk = {k: [n for n, _ in sorted(v.items(), key=lambda x: (-x[1], x[0]))[:5]] for k, v in riset_kk.items()}
    kk = s.get("kelompok_keahlian") or []
    if kk:
        bag.append('<section class="bag"><h2>Bidang yang Anda pelajari</h2><p class="ket">Teknik sipil merancang, membangun, dan '
                   'merawat infrastruktur. Di program studi ini Anda mendalami bidang-bidang berikut, sesuai kelompok keahlian dosen: '
                   'yang diajarkan dalam mata kuliah saat ini dan yang sedang diteliti dosennya.'
                   '</p><div class="kisi">'
                   + "".join(f'<div class="kotak"><h3><a href="{e(berkas_bidang(x["nama"]))}">{e(x["nama"])}</a></h3>'
                             + (f'<p><b>Diajarkan:</b> {e(cakupan[x["kode"]])}</p>' if cakupan.get(x["kode"]) else "")
                             + (f'<p class="riset"><b>Riset dosen:</b> {e(", ".join(riset_kk[x["kode"]]))}</p>'
                                if riset_kk.get(x["kode"]) else "") + "</div>" for x in kk)
                   + "</div></section>")
    # Kuis minat (2026-11-21, pemilik: soft selling "keputusan yang dibuat sendiri"): soal dari config public_site.interest_quiz,
    # hasil = kelompok keahlian berskor tertinggi + cakupan + dosennya. Dihitung di peramban; jawaban tidak disimpan/dikirim.
    kuis = s.get("kuis") or []
    kk_kode = {x["kode"] for x in kk}
    if kuis and kk:
        info = [{"kode": x["kode"], "nama": x["nama"], "cakupan": cakupan.get(x["kode"]) or "", "berkas": berkas_bidang(x["nama"]),
                 "riset": ", ".join(riset_kk.get(x["kode"]) or []),
                 # MK pilihan bidang ini (patch 145, pemilik 2026-11-22).
                 "pilihan": [m["nama"] for m in pilihan if m.get("peminatan") == x["kode"] and m.get("nama")],
                 "dosen": [{"nama": nama_dosen(D, d), **({"slug": d["slug"]} if d.get("slug") else {})}
                           for d in D.get("dosen") or [] if d.get("kelompok") == x["kode"] and d.get("nama")]} for x in kk]
        soal = "".join(
            f'<fieldset class="soal"><legend>{i + 1}. {e(q["tanya"])}</legend>'
            + "".join(f'<label><input type="radio" name="q{i}" value="{e(",".join(g for g in o["kk"] if g in kk_kode))}"> '
                      f'{e(o["teks"])}</label>' for o in q["pilihan"]) + "</fieldset>"
            for i, q in enumerate(kuis))
        data_kuis = json.dumps(info, ensure_ascii=False).replace("</", "<\\/")
        bag.append('<section class="bag" id="kuis"><h2>Bidang mana yang cocok untukmu?</h2>'
                   f'<p class="ket">{len(kuis)} pertanyaan singkat tentang minatmu. Ini gambaran minat, bukan tes bakat. '
                   'Jawabanmu tidak disimpan dan tidak dikirim ke mana pun.</p>'
                   f'<form id="kuisForm" class="kuis">{soal}<button class="tombol" type="submit">Lihat hasil</button>'
                   '<span id="kuisPesan" class="ket"></span></form><div id="kuisHasil" aria-live="polite"></div>'
                   f'<script type="application/json" id="kuisData">{data_kuis}</script></section>')
    # Perjalanan semester (2026-11-21, pemilik: soft selling "membayangkan diri"): linimasa bertonggak. Tonggak dihitung dari
    # data kurikulum (praktikum, kerja praktik, capstone, tugas akhir, dasar sains), bukan ditulis tangan.
    if wajib:
        baris = []
        for smt in sorted({m["semester"] for m in wajib}):
            xs = [m for m in wajib if m["semester"] == smt]
            prodi_mk = [m for m in xs if m.get("unit") != "universitas"]
            nm = lambda m: str(m.get("nama") or "").lower()
            khusus = lambda m: m.get("capstone") or "kerja praktik" in nm(m) or "tugas akhir" in nm(m)   # punya tonggak sendiri
            prak = [m for m in prodi_mk if not khusus(m)
                    and (float((m.get("bagian") or {}).get("praktikum") or 0) > 0 or nm(m).startswith("praktikum"))]
            tonggak = []
            tahap = (s.get("tahap") or {}).get(str(smt))   # 2026-11-22 pemilik: tahap per dua semester dari config
            if not s.get("tahap") and (not prodi_mk or len(prodi_mk) * 2 < len(xs)):
                tonggak.append("Dasar sains dan umum")
            # 2026-11-22 pemilik: lencana praktikum dihapus; prak tetap dipakai agar MK praktikum tidak jadi nama inti.
            tonggak += ["Kerja praktik" for m in xs if "kerja praktik" in nm(m)][:1]
            tonggak += ["Proyek rancangan (capstone)" for m in xs if m.get("capstone")][:1]
            tonggak += ["Tugas akhir" for m in xs if "tugas akhir" in nm(m)][:1]
            if {"Kerja praktik", "Proyek rancangan (capstone)", "Tugas akhir"} & set(tonggak):
                tonggak = [t for t in tonggak if t != "Dasar sains dan umum"]   # MK umum di semester akhir bukan cirinya
            # Nama MK: yang ber-sks terbesar dulu (mis. Kalkulus 1 sebelum Bahasa Inggris 1).
            inti = sorted([m for m in prodi_mk if m not in prak] or prodi_mk or xs, key=lambda m: -float(m.get("sks") or 0))
            baris.append(f'<li><span class="titik" aria-hidden="true">{smt}</span><div>'
                         f'<div class="atas"><b>Semester {smt}</b><span class="sks">{angka(sum(float(m.get("sks") or 0) for m in xs))} sks</span>'
                         + (f'<span class="tg tahap">{e(tahap)}</span>' if tahap else "")
                         + "".join(f'<span class="tg">{e(t)}</span>' for t in tonggak)
                         + f'</div><p>{nama_mk(inti, 3)}</p></div></li>')
        pil = (f'<p class="ket">Selain mata kuliah wajib, tersedia {len(pilihan)} mata kuliah pilihan untuk mendalami minat Anda, '
               f'antara lain {nama_mk(pilihan, 4)}.</p>') if pilihan else ""
        # MK pilihan per bidang (instal-lengkap.sql, pemilik 2026-11-22): kartu per kelompok keahlian lalu
        # peminatan lain di config; MK tanpa peminatan tidak dikartukan. Tanpa peminatan sama sekali: kalimat di atas.
        kel = [*kk, *(s.get("peminatan_lain") or [])]
        grup = [(x, [m for m in pilihan if m.get("peminatan") == x["kode"]]) for x in kel]
        grup = [(x, ms) for x, ms in grup if ms]
        if grup:
            ada_hal = {y["kode"] for y in kk}
            kartu = "".join(f'<div class="kotak"><span class="tag">{len(ms)} mata kuliah</span><h3>'
                            + (f'<a href="{e(berkas_bidang(x["nama"]))}">{e(x["nama"])}</a>' if x["kode"] in ada_hal else e(x["nama"]))
                            + '</h3>'
                            f'<ul class="mk-pil">' + "".join(f"<li>{e(m['nama'])}</li>" for m in ms) + "</ul></div>"
                            for x, ms in grup)
            aturan = s.get("aturan_pilihan") or ""
            pil = (f'<h3 class="sub">Mata kuliah pilihan per bidang</h3><p class="ket">Selain mata kuliah wajib, tersedia '
                   f'{len(pilihan)} mata kuliah pilihan untuk mendalami satu bidang peminatan.'
                   f'{(" " + e(aturan)) if aturan else ""}</p><div class="kisi">{kartu}</div>')
        bag.append(f'<section class="bag"><h2>Perjalanan {max(m["semester"] for m in wajib)} semester</h2>'
                   f'<p class="ket">Kurikulum {e(k.get("kode"))}: dari dasar sains dan rekayasa, ke laboratorium dan bidang-bidang '
                   f'teknik sipil, lalu kerja praktik, proyek rancangan, dan tugas akhir. <a href="kurikulum.html">Lihat kurikulum lengkap</a>.</p>'
                   f'<ol class="jalan">{"".join(baris)}</ol>{pil}</section>')
    # Belajar langsung: laboratorium, praktikum, kerja praktik.
    lab = [x.get("nama") for x in D.get("laboratorium") or [] if x.get("nama")] or s.get("laboratorium") or []
    praktikum = [m for m in wajib if float((m.get("bagian") or {}).get("praktikum") or 0) > 0]
    kp = [m for m in wajib if "kerja praktik" in str(m.get("nama") or "").lower()]
    tempat = [t for t in D.get("tempat_kp") or [] if t.get("instansi") or t.get("nama")]
    isi_lab = []
    if lab:
        isi_lab.append('<div class="kotak"><h3>Laboratorium</h3><ul>' + "".join(f"<li>{e(x)}</li>" for x in lab)
                       + '</ul><p><a href="laboratorium.html">Fasilitas laboratorium</a></p></div>')
    if praktikum:
        isi_lab.append(f'<div class="kotak"><h3>Praktikum</h3><p>{len(praktikum)} mata kuliah wajib berpraktikum, antara lain '
                       f'{nama_mk(prodi_dulu(praktikum), 4)}.</p></div>')
    if kp:
        lokasi = ", ".join(e(t.get("instansi") or t.get("nama")) for t in tempat[:4])
        isi_lab.append(f'<div class="kotak"><h3>Kerja praktik</h3><p>Pengalaman kerja di proyek atau instansi pada semester '
                       f'{e(kp[0]["semester"])}' + (f", antara lain di {lokasi}" if lokasi else "")
                       + '.</p><p><a href="kerja-praktik.html">Tentang kerja praktik dan magang</a></p></div>')
    if isi_lab:
        bag.append('<section class="bag"><h2>Belajar langsung</h2><div class="kisi">' + "".join(isi_lab) + "</div></section>")
    # Prestasi mahasiswa (tanpa nama mahasiswa).
    if prestasi:
        terbaru = sorted(prestasi, key=lambda p: (-(p.get("tahun") or 0), -(p.get("bulan") or 0)))[:3]
        kartu = "".join(f'<div class="kotak"><span class="tag">{e(TINGKAT.get(p.get("tingkat"), p.get("tingkat") or ""))} · '
                        f'{e(p.get("tahun"))}</span><h3>{e(p.get("capaian"))} — {e(p.get("kegiatan"))}</h3>'
                        + (f'<p class="ket">{e(p.get("penyelenggara"))}</p>' if p.get("penyelenggara") else "") + "</div>"
                        for p in terbaru)
        bag.append(f'<section class="bag"><h2>Prestasi mahasiswa</h2><div class="kisi">{kartu}</div>'
                   f'<p><a href="prestasi.html">Semua {len(prestasi)} prestasi mahasiswa</a></p></section>')
    # Suasana kegiatan (pemilik 2026-11-22): 6 foto terbaru dari galeri, mulai GALERI_MIN_CALON foto.
    fs = foto_galeri(D)
    if len(fs) >= GALERI_MIN_CALON:
        sel = "".join(f'<a class="foto" href="{e(f["href"])}"><img src="{e(f["src"])}?v={e(versi)}" alt="{e(f["judul"])}" '
                      f'loading="lazy"><span>{e(f["judul"])}</span></a>' for f in fs[:6])
        bag.append(f'<section class="bag"><h2>Suasana kegiatan</h2><div class="galeri">{sel}</div>'
                   f'<p><a href="galeri.html">Semua {len(fs)} foto di galeri</a></p></section>')
    # Mahasiswa ikut riset (2026-11-21, pemilik: soft selling "bukti, bukan janji"): penelitian/PkM dosen yang melibatkan
    # mahasiswa (kegiatan.mahasiswa = jumlah) dan publikasi dengan penulis mahasiswa (publikasi.mahasiswa). Tanpa nama mahasiswa.
    keg_mhs = sorted([x for x in D.get("kegiatan") or [] if x.get("mahasiswa")], key=lambda x: -(x.get("tahun") or 0))
    pub_mhs = sorted([x for x in D.get("publikasi") or [] if x.get("mahasiswa")], key=lambda x: -(x.get("tahun") or 0))
    if keg_mhs or pub_mhs:
        jenis_keg = {"penelitian": "Penelitian", "pkm": "Pengabdian kepada masyarakat"}
        angka_riset = [(len(keg_mhs), "penelitian dan pengabdian melibatkan mahasiswa"),
                       (len(pub_mhs), "publikasi ditulis bersama mahasiswa")]
        kartu = "".join(f'<div class="kotak"><span class="tag">{e(jenis_keg.get(x.get("kategori"), "Kegiatan"))} · {e(x.get("tahun"))}'
                        f' · {e(x["mahasiswa"])} mahasiswa</span><h3>{e(x.get("judul"))}</h3>'
                        + (f'<p class="ket">{e(x["skema"])}</p>' if x.get("skema") else "") + "</div>" for x in keg_mhs[:2])
        kartu += "".join(f'<div class="kotak"><span class="tag">Publikasi · {e(x.get("tahun"))}</span><h3>{e(x.get("judul"))}</h3>'
                         + (f'<p class="ket">{e(x["terbitan"])}</p>' if x.get("terbitan") else "") + "</div>" for x in pub_mhs[:1])
        bag.append('<section class="bag"><h2>Mahasiswa ikut riset</h2><p class="ket">Mahasiswa ikut serta dalam penelitian dan '
                   'pengabdian dosen, dan ikut menulis publikasinya.</p>'
                   '<div class="ringkas-riset">' + "".join(f"<div><b>{n}</b><span>{l}</span></div>" for n, l in angka_riset if n)
                   + f'</div><div class="kisi">{kartu}</div><p><a href="daftar.html?jenis=penelitian">Penelitian</a> · '
                   '<a href="daftar.html?jenis=pkm">Pengabdian</a> · <a href="daftar.html?jenis=publikasi">Publikasi</a></p></section>')
    # Testimoni (instal-lengkap.sql, pemilik 2026-11-21): hanya yang persetujuannya dicatat (testimoni_publik).
    testi = D.get("testimoni") or []
    if testi:
        def siapa(t):
            if t.get("peran") == "mahasiswa":
                ket = f'Mahasiswa{" angkatan " + str(t["angkatan"]) if t.get("angkatan") else ""}'
            else:
                ket = f'Alumni{" " + str(t["tahun_lulus"]) if t.get("tahun_lulus") else ""}'
            return " · ".join(x for x in (ket, t.get("pekerjaan") or "") if x)
        bag.append('<section class="bag"><h2>Kata alumni dan mahasiswa</h2><div class="kisi testi">'
                   + "".join(f'<figure class="kotak"><blockquote>{e(t["kutipan"])}</blockquote><figcaption>'
                             f'<span class="inisial" aria-hidden="true">{e(inisial(t["nama"]))}</span>'
                             f'<span><b>{e(t["nama"])}</b><small>{e(siapa(t))}</small></span></figcaption></figure>'
                             for t in testi[:6]) + "</div></section>")
    # Lulusan: prospek karier + tracer bila cukup responden.
    a = D.get("alumni") or {}
    karier = s.get("karier") or []
    cukup = a.get("responden", 0) >= (a.get("min") or 1) and bool(a.get("status"))
    if karier or cukup:
        tr = ""
        if cukup:
            # 2026-11-22 (pemilik): angka utama tracer; hanya agregat, tanpa nama instansi (keputusan 2026-11-17).
            fig = []
            p6 = persen_jawaban(a.get("kerja_6bulan") or [], {"ya", "yes"})
            if p6 is not None:
                fig.append((f"{p6}%", "bekerja dalam 6 bulan setelah lulus"))
            if a.get("waktu_tunggu_rerata") is not None:
                fig.append((angka(float(a["waktu_tunggu_rerata"])), "bulan waktu tunggu kerja (rata-rata)"))
            jenis = a.get("jenis_instansi") or []
            tot = sum(n for _, n in jenis)
            sebar = ", ".join(f"{e(t)} {round(100 * n / tot)}%" for t, n in jenis[:4] if t != "Lainnya") if tot else ""
            tr = ((f'<div class="angka-alumni">' + "".join(f"<div><b>{e(x)}</b><span>{e(l)}</span></div>" for x, l in fig)
                   + "</div>" if fig else "")
                  + (f'<p>Tempat kerja alumni menurut jenis instansi: {sebar}.</p>' if sebar else "")
                  + f'<p class="ket">Dari {e(a["responden"])} alumni yang mengisi tracer study. '
                  f'<a href="alumni.html">Hasil tracer study lengkap</a></p>')
        bag.append('<section class="bag"><h2>Setelah lulus</h2>'
                   + ('<p class="ket">Prospek karier lulusan:</p><ul class="karier">' + "".join(f"<li>{e(x)}</li>" for x in karier)
                      + "</ul>" if karier else "") + tr + "</section>")
    # Untuk orang tua dan wali (2026-11-21, pemilik: soft selling "mengurangi ragu"): hanya dari data (akreditasi, DTPS,
    # MK K3, karier); biaya dan beasiswa dirujuk ke PMB.
    akr = D.get("akreditasi_prodi") or {}
    k3 = [m for m in wajib if re.search(r"\bK3\b|keselamatan", str(m.get("nama") or ""), re.I)]
    ortu = []
    if akr.get("peringkat"):
        ortu.append(("Mutu yang diakui", f'Terakreditasi {e(akr["peringkat"])}' + (f' oleh {e(akr["lembaga"])}' if akr.get("lembaga") else "") + "."))
    if dtps.get("dosen_tetap") or dtps.get("jumlah"):
        ortu.append(("Dosen", f'{e(dtps.get("dosen_tetap") or dtps["jumlah"])} dosen tetap' + (f', {e(dtps["doktor"])} di antaranya bergelar doktor' if dtps.get("doktor") else "") + "."))
    if k3:
        ortu.append(("Keselamatan", f"Keselamatan dan kesehatan kerja (K3) dipelajari dalam mata kuliah wajib {nama_mk(k3, 2)}."))
    if karier:
        ortu.append(("Setelah lulus", "Lulusan disiapkan untuk berkarier antara lain sebagai " + ", ".join(e(x).lower() for x in karier[:3]) + "."))
    ortu.append(("Biaya dan beasiswa", "Biaya pendidikan, jalur masuk, dan beasiswa diatur Penerimaan Mahasiswa Baru universitas"
                 + (' (<a href="biaya-beasiswa.html">tautan resmi biaya dan beasiswa</a>)' if s.get("biaya")
                    else f' (<a href="{e(daftar_url)}" target="_blank" rel="noopener">laman PMB</a>)' if daftar_url else "") + "."))
    ortu.append(("Bertanya langsung", 'Kirim pertanyaan kepada program studi lewat <a href="layanan-mahasiswa.html#kirim">Tanya prodi</a>.'))
    if len(ortu) > 2:
        bag.append('<section class="bag" id="orang-tua"><h2>Untuk orang tua dan wali</h2><div class="kisi">'
                   + "".join(f'<div class="kotak"><h3>{j}</h3><p>{t}</p></div>' for j, t in ortu) + "</div></section>")
    # Pertanyaan umum (config public_site.faq).
    faq = s.get("faq") or []
    if faq:
        bag.append('<section class="bag"><h2>Pertanyaan umum</h2>'
                   + "".join(f'<details class="faq"><summary>{e(q["tanya"])}</summary>'
                             + "".join(f"<p>{e(p)}</p>" for p in str(q["jawab"]).split("\n") if p.strip()) + "</details>"
                             for q in faq) + "</section>")
    tombol = (f'<a class="tombol" href="{e(daftar_url)}" target="_blank" rel="noopener">Daftar di PMB {e(inst) or "universitas"}</a>'
              if daftar_url else "")
    ajak = ('<section class="bag ajak"><h2>Tertarik bergabung?</h2><p class="ket">Pendaftaran mahasiswa baru diselenggarakan '
            'universitas. Ada pertanyaan tentang program studi? Kirim lewat <a href="layanan-mahasiswa.html#kirim">Tanya prodi</a>.'
            f'</p>{tombol}</section>')
    isi = "".join(bag) + ajak
    judul_tab = nama_ps.replace(", ", " ", 1) if inst else nama_ps
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>Untuk calon mahasiswa — {judul_tab}</title>
<meta name="description" content="Kuliah di {nama_ps}: bidang yang dipelajari, perjalanan semester, laboratorium, prestasi mahasiswa, prospek karier, dan pendaftaran.">
<meta property="og:title" content="Untuk calon mahasiswa — {nama_ps}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.6}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0 0 16px;color:var(--biru-m4);max-width:660px}}
.kepala .tombol{{background:#fff;color:var(--biru)}}
.kepala .tombol.garis{{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.6);margin-left:8px}}
.ringkas{{max-width:1080px;margin:0 auto;padding:0 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0}}
.ringkas div{{background:var(--biru-gelap);color:#fff;padding:14px 18px;border-left:1px solid rgba(255,255,255,.15)}}
.ringkas b{{display:block;font-family:var(--serif);font-size:30px;line-height:1.1}}
.ringkas span{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--biru-m4)}}
.isi{{max-width:1080px;margin:0 auto;padding:10px 20px 50px}}
.bag{{margin-top:30px}}
h2{{font-family:var(--serif);font-size:28px;color:var(--biru);margin:0 0 4px}}
h3{{font-size:15.5px;margin:0 0 8px;line-height:1.3}}
.ket{{color:var(--muted);margin:0 0 14px;max-width:760px}}
.kisi{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}}
.kotak{{background:#fff;border:1px solid var(--line);padding:14px 16px;border-top:3px solid var(--biru)}}
.kotak p{{margin:0 0 6px}} .kotak ul{{margin:0 0 6px;padding-left:18px}}
.tag{{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
ol.jalan{{list-style:none;margin:6px 0 0;padding:0;position:relative}}
ol.jalan::before{{content:"";position:absolute;left:19px;top:8px;bottom:8px;width:3px;background:var(--biru-m10)}}
ol.jalan li{{position:relative;display:grid;grid-template-columns:40px 1fr;gap:14px;padding:8px 0}}
ol.jalan .titik{{z-index:1;width:40px;height:40px;border-radius:50%;background:var(--biru);color:#fff;display:grid;place-items:center;
  font-family:var(--serif);font-weight:600;font-size:18px}}
ol.jalan .atas{{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin-top:2px}}
ol.jalan .atas b{{color:var(--biru);font-size:16px}}
ol.jalan .sks{{font-family:var(--mono);font-size:12.5px;color:var(--muted)}}
ol.jalan .tg{{font-size:12px;font-weight:600;padding:1px 8px;background:#fff;border:1px solid var(--aksen);color:var(--ink)}}
ol.jalan .tg.tahap{{background:var(--aksen);border-color:var(--aksen)}}
h3.sub{{font-family:var(--serif);font-size:20px;margin:22px 0 4px}}
ul.mk-pil{{margin:6px 0 0;padding-left:18px}} ul.mk-pil li{{margin:2px 0}}
.galeri{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}}
.galeri .foto{{display:block;background:#fff;border:1px solid var(--line);color:var(--ink);text-decoration:none;font-size:13.5px;line-height:1.3}}
.galeri img{{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:var(--biru-m10)}}
.galeri span{{display:block;padding:6px 8px 8px}}
.angka-alumni{{display:flex;flex-wrap:wrap;gap:12px;margin:10px 0}}
.angka-alumni div{{background:#fff;border:1px solid var(--line);padding:10px 14px;min-width:150px}}
.angka-alumni b{{display:block;font-family:var(--serif);font-size:26px;color:var(--biru)}}
.angka-alumni span{{font-size:13px;color:var(--muted)}}
ol.jalan p{{margin:4px 0 0;color:var(--muted);font-size:14.5px}}
.ringkas-riset{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 14px}}
.ringkas-riset div{{background:var(--biru);color:#fff;padding:12px 18px;min-width:220px}}
.ringkas-riset b{{display:block;font-family:var(--serif);font-size:30px;line-height:1.1}}
.ringkas-riset span{{font-size:13px;color:var(--biru-m4)}}
.kisi.baru{{grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}}
.kotak p.riset{{color:var(--muted);font-size:14.5px}}
form.kuis{{background:#fff;border:1px solid var(--line);border-top:3px solid var(--aksen);padding:16px 18px}}
fieldset.soal{{border:0;padding:0;margin:0 0 16px}}
fieldset.soal legend{{font-weight:600;padding:0;margin-bottom:6px}}
fieldset.soal label{{display:flex;gap:10px;align-items:flex-start;padding:6px 8px;cursor:pointer;border:1px solid transparent}}
fieldset.soal label:hover{{border-color:var(--line);background:var(--bg)}}
fieldset.soal input{{margin-top:5px;accent-color:var(--biru)}}
#kuisPesan{{margin-left:12px}}
#kuisHasil .hasil{{margin-top:14px;background:var(--biru);color:#fff;padding:18px 22px}}
#kuisHasil .hasil h3{{font-family:var(--serif);font-size:24px;margin:2px 0 6px}}
#kuisHasil .hasil small{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--biru-m4)}}
#kuisHasil .hasil p{{margin:4px 0;color:var(--biru-m4)}}
#kuisHasil .hasil a{{color:#fff}}
.kisi.testi figure{{margin:0;display:flex;flex-direction:column;justify-content:space-between}}
.kisi.testi blockquote{{margin:0 0 12px;font-family:var(--serif);font-size:17px;line-height:1.45}}
.kisi.testi blockquote::before{{content:"\\201C";color:var(--aksen);font-size:34px;line-height:0;vertical-align:-12px;margin-right:4px}}
.kisi.testi figcaption{{display:flex;gap:10px;align-items:center}}
.kisi.testi .inisial{{flex:none;width:42px;height:42px;border-radius:50%;background:var(--biru-m10);color:var(--biru);display:grid;
  place-items:center;font-family:var(--serif);font-weight:600}}
.kisi.testi small{{display:block;color:var(--muted);font-size:13px}}
.kisi.baru a.kotak{{text-decoration:none;color:var(--ink);display:block;border-top-color:var(--aksen)}}
.kisi.baru a.kotak:hover h3{{color:var(--biru);text-decoration:underline}}
.kisi.baru h3{{font-size:15px;margin:6px 0 0}}
ul.karier{{columns:2 260px;padding-left:18px}}
details.faq{{background:#fff;border:1px solid var(--line);padding:10px 14px;margin:8px 0}}
details.faq summary{{font-weight:600;cursor:pointer}}
details.faq p{{margin:8px 0 0}}
.tombol{{display:inline-block;background:var(--biru);color:#fff;text-decoration:none;padding:10px 18px;font-weight:600}}
.tombol:hover{{opacity:.9}}
.ajak{{background:#fff;border:1px solid var(--line);padding:18px 20px}}
@media(max-width:760px){{.ringkas{{grid-template-columns:1fr 1fr}} .ringkas-riset div{{min-width:0;flex:1 1 140px}}
  .kepala .tombol.garis{{margin:8px 0 0}}}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{nama_ps}</div>
    <h1>Untuk calon mahasiswa</h1>
    <p>{e(s.get("tagline") or "")}</p>
    {tombol}<a class="tombol garis" href="kurikulum.html">Lihat kurikulum</a>
  </div></div>
  {blok_ringkas}
  <div class="isi">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka, catatKunjunganPublik }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'mahasiswa' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
// Kuis minat: skor per kelompok keahlian dari pilihan; tidak ada yang disimpan atau dikirim.
const kuis = document.getElementById('kuisForm');
if (kuis) {{
  const KK = JSON.parse(document.getElementById('kuisData').textContent);
  const esc = t => String(t ?? '').replace(/[&<>"']/g, c => ({{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }}[c]));
  kuis.addEventListener('submit', ev => {{
    ev.preventDefault();
    const soal = kuis.querySelectorAll('fieldset.soal');
    const dipilih = [...soal].map(f => f.querySelector('input:checked')).filter(Boolean);
    const pesan = document.getElementById('kuisPesan');
    if (dipilih.length < soal.length) {{ pesan.textContent = `Jawab semua pertanyaan dulu (${{dipilih.length}} dari ${{soal.length}}).`; return; }}
    pesan.textContent = '';
    const skor = {{}};
    dipilih.forEach(i => i.value.split(',').filter(Boolean).forEach(k => {{ skor[k] = (skor[k] || 0) + 1; }}));
    const maks = Math.max(0, ...Object.values(skor));
    const menang = KK.filter(x => skor[x.kode] === maks && maks > 0);
    document.getElementById('kuisHasil').innerHTML = menang.map(x => `<div class="hasil">
      <small>${{menang.length > 1 ? 'Salah satu bidang yang cocok' : 'Bidang yang paling cocok'}} · ${{maks}} dari ${{soal.length}} jawaban</small>
      <h3>${{esc(x.nama)}}</h3>${{x.cakupan ? `<p><b>Diajarkan:</b> ${{esc(x.cakupan)}}</p>` : ''}}
      ${{x.riset ? `<p><b>Riset dosen:</b> ${{esc(x.riset)}}</p>` : ''}}
      ${{(x.pilihan || []).length ? `<p><b>Mata kuliah pilihan:</b> ${{esc(x.pilihan.join(', '))}}</p>` : ''}}
      ${{x.dosen.length ? `<p>Dosen bidang ini: ${{x.dosen.map(d => d.slug ? `<a href="dosen/${{esc(d.slug)}}.html">${{esc(d.nama)}}</a>` : esc(d.nama)).join(', ')}}</p>` : ''}}
      <p><a href="${{esc(x.berkas)}}">Selengkapnya tentang bidang ini</a> · <a href="keahlian.html">Kepakaran dosen</a> · <a href="kurikulum.html">Mata kuliah</a></p></div>`).join('');
    catatKunjunganPublik('kuis_selesai');
    document.getElementById('kuisHasil').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }});
}}
</script>
</body>
</html>
"""


# English overview page (owner 2026-11-21): one page for international readers (IABEE, partners, foreign
# applicants), built only from data that exists in English; Indonesian is the fallback per item.
PERINGKAT_EN = {"unggul": "Excellent", "baik sekali": "Very Good", "baik": "Good"}


def halaman_english(D: dict, versi: str) -> str:
    """Static english.html: key figures, accreditation, graduate profiles, programme learning outcomes (CPL rumusan_en),
    curriculum by semester (nama_en, else the Indonesian name), expertise groups (name_en/scope_en) with lecturers,
    admission. Sections without data are left out."""
    s, inst = D.get("situs") or {}, D.get("institusi") or ""
    prog = f'{s.get("prodi_en") or D.get("prodi") or ""} Study Program'.strip()   # config public_site.programme_name_en
    v = f"?v={e(versi)}" if versi else ""
    kur = sorted(D.get("kurikulum") or [], key=lambda k: str(k.get("kode") or ""))
    k = kur[-1] if kur else {}
    mk = k.get("mk") or []
    wajib = [m for m in mk if m.get("sifat") == "wajib" and isinstance(m.get("semester"), int)]
    pilihan = [m for m in mk if m.get("sifat") == "pilihan"]
    nm = lambda m: m.get("nama_en") or m.get("nama") or ""
    # Nama MK bertaut ke halaman mata kuliah berbahasa Inggris (pemilik 2026-11-22) bila ada.
    tautan = lambda m: f'<a href="{e(m["berkas_en"])}">{e(nm(m))}</a>' if m.get("berkas_en") else e(nm(m))
    angka = lambda x: f"{x:g}"
    dtps, akr = D.get("dtps") or {}, D.get("akreditasi_prodi") or {}
    peringkat = PERINGKAT_EN.get(str(akr.get("peringkat") or "").strip().lower(), akr.get("peringkat") or "")
    fig = []
    if peringkat:
        fig.append((peringkat, "accreditation"))
    if wajib:
        fig += [(angka(sum(float(m.get("sks") or 0) for m in wajib)), "compulsory credits"),
                (str(max(m["semester"] for m in wajib)), "semesters")]
    if pilihan:
        fig.append((str(len(pilihan)), "elective courses"))
    if dtps.get("dosen_tetap") or dtps.get("jumlah"):
        fig.append((str(dtps.get("dosen_tetap") or dtps["jumlah"]), "full-time lecturers"))
    if dtps.get("doktor"):
        fig.append((str(dtps["doktor"]), "with a doctorate"))
    blok_fig = ('<div class="angka">' + "".join(f"<div><b>{e(a)}</b><span>{l}</span></div>" for a, l in fig) + "</div>") if fig else ""
    bag = []
    # About.
    tentang = []
    if wajib:
        tentang.append(f'The {e(prog)}{f" at {e(inst)}" if inst else ""} is a bachelor programme of '
                       f'{max(m["semester"] for m in wajib)} semesters'
                       + (f' leading to the degree {e(s["gelar"])}.' if s.get("gelar") else "."))
    if peringkat:
        tentang.append(f'It is accredited <b>{e(peringkat)}</b> ({e(akr["peringkat"])})'
                       + (f' by {e(akr["lembaga"])}' if akr.get("lembaga") else "") + ".")
    if tentang:
        bag.append(("about", "About the programme", "<p>" + " ".join(tentang) + "</p>"))
    # Graduate profiles.
    if k.get("profil"):
        bag.append(("profiles", "Graduate profiles", '<div class="kisi">' + "".join(
            f'<div class="kotak"><span class="kode">{e(p.get("kode") or "")}</span><b>{e(p.get("nama_en") or p.get("nama"))}</b></div>'
            for p in k["profil"]) + "</div>"))
    # Programme learning outcomes.
    cpl = [c for c in k.get("cpl") or [] if c.get("rumusan_en")]
    if cpl:
        bag.append(("outcomes", f"Programme learning outcomes ({e(k.get('kode') or '')})",
                    '<ol class="plo">' + "".join(f'<li><span class="kode">PLO {e(c["kode"])}</span>{e(c["rumusan_en"])}</li>' for c in cpl)
                    + "</ol>"))
    # Curriculum by semester.
    if wajib:
        baris = "".join(
            f'<li><b>Semester {smt}</b><span class="sks">{angka(sum(float(m.get("sks") or 0) for m in wajib if m["semester"] == smt))} credits</span>'
            f'<p>{"; ".join(tautan(m) for m in wajib if m["semester"] == smt)}</p></li>'
            for smt in sorted({m["semester"] for m in wajib}))
        pil = (f'<p class="ket">Elective courses ({len(pilihan)}): {"; ".join(tautan(m) for m in pilihan)}.</p>') if pilihan else ""
        bag.append(("curriculum", f"Curriculum {e(k.get('kode') or '')}", f'<ol class="smt">{baris}</ol>{pil}'
                    '<p class="ket">Course names follow the official curriculum document; courses without an English name are listed in Indonesian.</p>'))
    # Expertise groups.
    kk = s.get("kelompok_keahlian") or []
    if kk:
        def dosen_kk(kode):
            xs = [d for d in D.get("dosen") or [] if d.get("kelompok") == kode and d.get("nama")]
            return ", ".join(f'<a href="dosen/{e(d["slug"])}.html">{e(nama_dosen(D, d))}</a>' if d.get("slug") else e(nama_dosen(D, d)) for d in xs)
        bag.append(("expertise", "Areas of expertise", '<div class="kisi">' + "".join(
            f'<div class="kotak"><b>{e(x.get("nama_en") or x["nama"])}</b>'
            + (f'<p>{e(x["cakupan_en"])}</p>' if x.get("cakupan_en") else "")
            + (f'<p class="ket">Lecturers: {dosen_kk(x["kode"])}</p>' if dosen_kk(x["kode"]) else "") + "</div>" for x in kk) + "</div>"))
    # Admission and further pages.
    daftar = s.get("pendaftaran") or ""
    bag.append(("admission", "Admission and more information",
                '<p>Admission is managed by the university'
                + (f' (<a href="{e(daftar)}" target="_blank" rel="noopener">admission site</a>)' if daftar else "")
                + '. More information, in Indonesian: <a href="calon-mahasiswa.html">prospective students</a>, '
                '<a href="kurikulum.html">full curriculum</a>, <a href="daftar.html?jenis=dosen">lecturers</a>, '
                '<a href="daftar.html?jenis=publikasi">publications</a>, <a href="laboratorium.html">laboratories</a>.</p>'))
    nav = "".join(f'<a href="#{i}">{j}</a>' for i, j, _ in bag)
    isi = "".join(f'<section class="bag" id="{i}"><h2>{j}</h2>{h}</section>' for i, j, h in bag)
    tagline = s.get("tagline_en") or ""
    judul_inst = f" — {e(inst)}" if inst else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{GENERATOR}">
<title>{e(prog)}{judul_inst}</title>
<meta name="description" content="{e(prog)}{judul_inst}: accreditation, graduate profiles, programme learning outcomes, curriculum, areas of expertise, and admission.">
<meta property="og:title" content="{e(prog)}{judul_inst}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="tema.css{v}">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15.5px;line-height:1.65}}
.kepala{{background:var(--biru);color:#fff}}
.kepala-in{{max-width:1080px;margin:0 auto;padding:40px 20px 30px}}
.eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--biru-m2)}}
h1{{font-family:var(--serif);font-size:clamp(30px,4.6vw,48px);margin:8px 0 6px;line-height:1.08}}
.kepala p{{margin:0;color:var(--biru-m4);max-width:680px;font-size:17px}}
.angka{{display:flex;flex-wrap:wrap;margin-top:24px}}
.angka div{{padding:10px 24px 4px 0;margin-right:24px;border-right:1px solid rgba(255,255,255,.18)}}
.angka div:last-child{{border-right:0;margin-right:0}}
.angka b{{display:block;font-family:var(--mono);font-size:26px;font-weight:400;line-height:1.1}}
.angka span{{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--biru-m2)}}
.loncat{{background:#fff;border-bottom:1px solid var(--line)}}
.loncat-in{{max-width:1080px;margin:0 auto;padding:0 20px;display:flex;gap:4px;overflow-x:auto;scrollbar-width:thin}}
.loncat a{{flex:none;padding:12px;color:var(--biru);text-decoration:none;font-weight:600;font-size:14px;border-bottom:3px solid transparent}}
.loncat a:hover{{border-bottom-color:var(--aksen)}}
.isi{{max-width:1080px;margin:0 auto;padding:6px 20px 50px}}
.bag{{margin-top:36px;scroll-margin-top:80px}}
h2{{font-family:var(--serif);font-size:28px;color:var(--biru);margin:0 0 14px;padding-bottom:6px;border-bottom:3px solid var(--aksen);display:table}}
.ket{{color:var(--muted)}}
.kisi{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
.kotak{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--aksen);padding:14px 16px}}
.kotak b{{color:var(--biru)}} .kotak p{{margin:6px 0 0;font-size:14.5px}}
.kode{{display:inline-block;font-family:var(--mono);font-size:11px;background:var(--biru);color:#fff;padding:2px 7px;margin-right:8px}}
ol.plo{{list-style:none;padding:0;margin:0;display:grid;gap:8px}}
ol.plo li{{background:#fff;border:1px solid var(--line);padding:10px 14px}}
ol.smt{{list-style:none;padding:0;margin:0;border-left:3px solid var(--biru-m10)}}
ol.smt li{{padding:8px 0 8px 16px}}
ol.smt b{{color:var(--biru)}} ol.smt .sks{{font-family:var(--mono);font-size:12.5px;color:var(--muted);margin-left:10px}}
ol.smt p{{margin:2px 0 0;color:var(--muted);font-size:14.5px}}
@media (max-width:640px){{.angka{{display:grid;grid-template-columns:1fr 1fr;gap:4px 16px}} .angka div{{padding:8px 0 4px;margin:0;border-right:0}}}}
</style>
</head>
<body>
<main id="utama">
  <div class="kepala" role="region" aria-label="Pembuka halaman"><div class="kepala-in">
    <div class="eyebrow">{e(inst) or "Study program"}</div>
    <h1>{e(prog)}</h1>
    {f"<p>{e(tagline)}</p>" if tagline else ""}
    {blok_fig}
  </div></div>
  <nav class="loncat" aria-label="Sections"><div class="loncat-in">{nav}</div></nav>
  <div class="isi">{isi}</div>
</main>
<script src="config.js{v}"></script>
<script type="module">
import {{ pasangKerangka, isiKerangka }} from './kerangka.js{v}';
pasangKerangka({{ aktif: 'profil' }});
fetch('kerangka.json', {{cache: 'no-cache'}}).then(r => r.json()).then(isiKerangka).catch(() => {{}});
</script>
</body>
</html>
"""
