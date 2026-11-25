-- =====================================================================
--  INSTAL-LENGKAP.SQL: seluruh tabel situs dalam satu berkas.
--
--  Jalankan SEKALI di SQL Editor Supabase pada proyek KOSONG. Berkas ini
--  tidak menghapus apa pun: kalau tabelnya sudah ada, ia berhenti dengan
--  galat "already exists" dan data tetap aman.
--
--  Dibuat otomatis oleh tools/make_full_schema.mjs. Jangan disunting tangan.
-- =====================================================================

create extension if not exists "pgcrypto" with schema extensions;

SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;

CREATE FUNCTION public._terapkan_karya(k uuid, d jsonb) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  boleh constant text[] := array['judul', 'kategori', 'jenis', 'tahun', 'bulan',
    'induk_id', 'nama_terbitan', 'tingkat', 'indeksasi', 'doi', 'url', 'skema_kode',
    'nama_pemberi_dana', 'besaran_dana', 'keterangan', 'sub_jenis', 'mata_kuliah',
    'kerjasama_id', 'tkt', 'nomor_tkt', 'jumlah_sitasi', 'tema_id', 'keterlibatan_mhs',
    'bukti_integrasi', 'sesuai_rps', 'manfaat_ks', 'mulai_ks', 'selesai_ks', 'jenis_bukti_ks',
    'sdgs', 'volume', 'nomor', 'halaman'];
  r     public.karya;
  kat   text;
  kolom text[];
begin
  select kategori into kat from public.karya where id = k;
  if kat is null then raise exception 'Karya tidak ditemukan.'; end if;

  if d ? 'karya' then
    r := jsonb_populate_record(null::public.karya, d -> 'karya');
    select array_agg(x) into kolom
      from jsonb_object_keys(d -> 'karya') x where x = any(boleh);
    -- Kategori hanya boleh bertukar antara penelitian dan PkM (satu form).
    if 'kategori' = any(kolom) and not (kat in ('penelitian', 'pkm')
        and r.kategori in ('penelitian', 'pkm')) then
      raise exception 'Kategori hanya bisa diubah antara penelitian dan PkM.';
    end if;
    if kolom is not null then
      execute format('update public.karya set %s where id = $2',
        (select string_agg(format('%1$I = ($1).%1$I', c), ', ') from unnest(kolom) c))
        using r, k;
    end if;
  end if;

  if d ? 'penulis' then
    if jsonb_array_length(d -> 'penulis') < 1 then
      raise exception 'Karya harus punya sedikitnya satu penulis dari prodi.';
    end if;
    delete from public.karya_penulis where karya_id = k;
    insert into public.karya_penulis (karya_id, dosen_id, peran, korespondensi, ditambahkan_sendiri)
      select k, x.dosen_id, coalesce(x.peran, 'anggota'), coalesce(x.korespondensi, false), false
      from jsonb_to_recordset(d -> 'penulis') as x(dosen_id uuid, peran text, korespondensi boolean);
  end if;

  if d ? 'mitra' then
    delete from public.karya_mitra where karya_id = k;
    insert into public.karya_mitra (karya_id, institusi, tingkat, negara)
      select k, x.institusi, x.tingkat, nullif(trim(x.negara), '')
      from jsonb_to_recordset(d -> 'mitra') as x(institusi text, tingkat text, negara text);
  end if;

  if d ? 'mahasiswa' then
    delete from public.karya_mahasiswa where karya_id = k;
    insert into public.karya_mahasiswa (karya_id, nim, nama, peran, korespondensi)
      select k, x.nim, x.nama, coalesce(x.peran, 'anggota'), coalesce(x.korespondensi, false)
      from jsonb_to_recordset(d -> 'mahasiswa') as x(nim text, nama text, peran text, korespondensi boolean);
  end if;
end $_$;

CREATE FUNCTION public.ajukan_karya(k uuid) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  r public.karya;
begin
  select * into r from public.karya where id = k;
  if not found then raise exception 'Karya tidak ditemukan.'; end if;
  if r.status <> 'draf' then raise exception 'Hanya draf yang bisa diajukan.'; end if;
  if not (r.dilaporkan_oleh = public.me() or public.penulis_karya(k)) then
    raise exception 'Hanya penulis karya ini yang bisa mengajukannya.';
  end if;
  if r.tingkat is null then raise exception 'Lengkapi tingkat karya sebelum diajukan.'; end if;
  update public.karya set status = 'diajukan', catatan = null where id = k;
end $$;

CREATE FUNCTION public.akses_masuk_ditutup() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.dosen d
    where not d.boleh_masuk
      and (lower(d.email) = lower(auth.jwt() ->> 'email')
           or lower(d.email_alternatif) = lower(auth.jwt() ->> 'email')))
$$;

CREATE FUNCTION public.ami_buka(p_token text) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select jsonb_build_object(
    'judul', t.judul, 'mode', t.mode, 'periode', t.periode, 'akhir', t.akhir,
    'ts_iku', t.ts_iku, 'sampai', t.sampai,
    'iku', coalesce((select jsonb_agg(jsonb_build_object(
        'jenis', k.jenis, 'nama', k.nama, 'butir', k.butir, 'satuan', k.satuan,
        'arah', k.arah, 'target', k.target, 'capaian', k.capaian,
        'tahun_ts', k.tahun_ts, 'sumber', k.sumber, 'urutan', k.urutan))
      from public.lkps_target_kinerja k), '[]'::jsonb),
    'temuan', coalesce((select jsonb_agg(jsonb_build_object(
        'id', a.id, 'siklus', a.siklus, 'tahun_ts', a.tahun_ts, 'tanggal_audit', a.tanggal_audit,
        'kode', a.kode, 'standar', a.standar, 'butir', a.butir, 'kategori', a.kategori,
        'uraian', a.uraian, 'akar_masalah', a.akar_masalah, 'rencana', a.rencana,
        'pihak', a.pihak, 'pj_nama', a.pj_nama, 'tenggat', a.tenggat, 'status', a.status,
        'tanggal_selesai', a.tanggal_selesai, 'verifikasi', a.verifikasi))
      from public.ami_temuan a), '[]'::jsonb),
    'bukti_temuan', coalesce((select jsonb_agg(jsonb_build_object(
        'baris_id', b.baris_id, 'judul', b.judul, 'url', b.url))
      from public.lkps_bukti b where b.tabel = 'ami_temuan'), '[]'::jsonb),
    'cpl', (select jsonb_build_object('dibuat', c.dibuat, 'diunggah', c.diunggah, 'catatan', c.catatan, 'data', c.data)
      from public.cpl_ringkasan c order by c.diunggah desc, c.id desc limit 1),
    'korelasi', coalesce((select jsonb_agg(jsonb_build_object(
        'kurikulum_asal', r.kurikulum_asal, 'cpl_asal', r.cpl_asal,
        'kurikulum_tujuan', r.kurikulum_tujuan, 'cpl_tujuan', r.cpl_tujuan,
        'tingkat', r.tingkat, 'status', r.status))
      from public.ref_cpl_korelasi r), '[]'::jsonb))
  from public.tautan_ami t
  where length(coalesce(p_token, '')) >= 32
    and t.token = p_token and not t.dicabut and t.sampai > now()
$$;

CREATE FUNCTION public.ami_portofolio(p_token text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not exists (select 1 from public.tautan_ami t where t.token = p_token and not t.dicabut and t.sampai > now()) then
    raise exception 'Tautan AMI tidak berlaku.'; end if;
  return jsonb_build_object(
    'berkas', coalesce((select jsonb_agg(jsonb_build_object('id', b.id, 'tahun_akademik', b.tahun_akademik, 'semester', b.semester,
        'kurikulum', b.kurikulum, 'kode_mk', b.kode_mk, 'kelas', b.kelas, 'komponen', b.komponen, 'asesmen', b.asesmen,
        'nama_berkas', b.nama_berkas, 'diunggah', b.diunggah) order by b.id)
      from public.portofolio_berkas b where public.ami_portofolio_cakup(p_token, b.tahun_akademik)), '[]'::jsonb),
    'kelas', coalesce((select jsonb_agg(jsonb_build_object('id', k.id, 'tahun_akademik', k.tahun_akademik, 'semester', k.semester,
        'kode_mk', k.kode_mk, 'nama_mk', k.nama_mk, 'kelas', k.kelas,
        'nilai', exists (select 1 from public.cpl_berkas c where c.kelas_id = k.id)))
      from public.cpl_kelas k where public.ami_portofolio_cakup(p_token, k.tahun_akademik)), '[]'::jsonb),
    'mk', coalesce((select jsonb_agg(jsonb_build_object('kurikulum', m.kurikulum, 'kode', m.kode, 'nama', m.nama,
        'rps_url', m.rps_url, 'rps_9_komponen', m.rps_9_komponen, 'struktur', s.data))
      from public.ref_mata_kuliah m left join public.mk_struktur s on s.kurikulum = m.kurikulum and s.kode_mk = m.kode
      where m.aktif is not false), '[]'::jsonb),
    'evaluasi', coalesce((select jsonb_agg(jsonb_build_object('tahun_akademik', e.tahun_akademik, 'semester', e.semester,
        'kode_mk', e.kode_mk, 'refleksi', e.rps_sesuai is not null,
        'tindak', (select count(*) from public.evaluasi_tindak t where t.evaluasi_id = e.id)))
      from public.evaluasi_mk e where public.ami_portofolio_cakup(p_token, e.tahun_akademik)), '[]'::jsonb));
end $$;

CREATE FUNCTION public.ami_portofolio_cakup(p_token text, p_ta text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
  select exists (select 1 from public.tautan_ami t where t.token = p_token and not t.dicabut and t.sampai > now() and (
    t.periode = 'semua'
    or (t.periode ~ '^\d{4}$' and (split_part(p_ta, '/', 2)::int = t.periode::int
                                   or (t.mode = 'kal' and split_part(p_ta, '/', 1)::int = t.periode::int)))
    or (t.periode = 'ts3' and split_part(p_ta, '/', 2)::int between
          coalesce(t.akhir, extract(year from now())::int + (extract(month from now()) >= 9)::int) - 2
          and coalesce(t.akhir, extract(year from now())::int + (extract(month from now()) >= 9)::int))))
$_$;

CREATE FUNCTION public.ami_portofolio_url(p_token text, p_id bigint) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare b public.portofolio_berkas;
begin
  select * into b from public.portofolio_berkas where id = p_id;
  if b.id is null or not public.ami_portofolio_cakup(p_token, b.tahun_akademik) then
    raise exception 'Berkas tidak termasuk tautan AMI ini, atau tautannya tidak berlaku.'; end if;
  return b.url;
end $$;

CREATE FUNCTION public.asesor_aktif() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from dosen d where d.id = me() and d.peran = 'asesor' and d.aktif)
$$;

CREATE FUNCTION public.atur_foto_profil(u text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare v text := nullif(btrim(coalesce(u, '')), '');
begin
  if public.me() is null then raise exception 'Belum masuk sebagai dosen terdaftar.'; end if;
  if v is not null and v !~* '^https://drive\.google\.com/\S+$' then
    raise exception 'Foto harus berupa tautan Google Drive.';
  end if;
  update public.dosen set foto_url = v where id = public.me();
end $_$;

CREATE FUNCTION public.atur_nama_gelar(p text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v text := nullif(regexp_replace(btrim(coalesce(p, '')), '\s+', ' ', 'g'), '');
begin
  if public.me() is null then raise exception 'Belum masuk sebagai dosen terdaftar.'; end if;
  if v is not null and length(v) not between 3 and 200 then raise exception 'Nama dengan gelar 3 sampai 200 huruf.'; end if;
  update public.dosen set nama_gelar = v where id = public.me();
end $$;

CREATE FUNCTION public.atur_nip_nuptk(p_nip text, p_nuptk text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  n text := nullif(regexp_replace(btrim(coalesce(p_nip, '')), '\s+', ' ', 'g'), '');
  u text := nullif(regexp_replace(btrim(coalesce(p_nuptk, '')), '\s+', ' ', 'g'), '');
  pola constant text := '^[0-9A-Za-z][0-9A-Za-z ./-]{1,38}[0-9A-Za-z]$';
begin
  if public.me() is null then raise exception 'Belum masuk sebagai dosen terdaftar.'; end if;
  if n is not null and n !~ pola then
    raise exception 'NIP: 3–40 karakter berupa angka, huruf, spasi, titik, garis miring, atau tanda hubung.';
  end if;
  if u is not null and u !~ pola then
    raise exception 'NUPTK: 3–40 karakter berupa angka, huruf, spasi, titik, garis miring, atau tanda hubung.';
  end if;
  update public.dosen set nip = n, nuptk = u, diubah_pada = now() where id = public.me();
end $_$;

CREATE FUNCTION public.beban_bimbingan(p_ts integer) RETURNS TABLE(dosen_id uuid, nama text, kk text, kp integer, kp_selesai integer, kp_kuota integer, ta integer, ta_lulus integer, uji integer, lomba integer)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with d as (
    select x.id, x.nama, ds.kelompok_keahlian as kk, nullif(btrim(ds.nidn), '') as nidn
      from pembimbing_pilihan() x join dosen ds on ds.id = x.id
     where me() is not null),
  kp as (
    select p.pembimbing_id as id, count(*)::int as n,
           (count(*) filter (where p.tahap = 'selesai' and p.status = 'disetujui'))::int as selesai
      from pengajuan_mahasiswa p
     where p.jenis = 'kp' and p.status not in ('draf', 'ditolak') and ts_dari(kp_tanggal_acuan(p)) = p_ts
     group by p.pembimbing_id),
  ta_mhs as (
    select d.id, coalesce(nullif(btrim(p.nim), ''), lower(btrim(p.nama))) as m
      from pengajuan_mahasiswa p join d on d.id = p.pembimbing_id or d.id::text = p.data ->> 'pembimbing_2'
     where p.jenis = 'ta' and p.status not in ('draf', 'ditolak')
       and ts_dari((p.dibuat at time zone 'Asia/Jakarta')::date) = p_ts
    union
    select d.id, coalesce(nullif(btrim(j.nim), ''), lower(btrim(j.nama_mahasiswa)))
      from jadwal_ta j join d on d.nidn = any(j.pembimbing)
     where j.status <> 'batal' and ts_dari(j.tanggal) = p_ts),
  lulus as (
    select d.id, count(distinct coalesce(nullif(btrim(j.nim), ''), lower(btrim(j.nama_mahasiswa))))::int as n
      from jadwal_ta j join d on d.nidn = any(j.pembimbing)
     where j.tahap = 'sidang_akhir' and j.hasil in ('lulus', 'lulus_revisi') and j.status <> 'batal' and ts_dari(j.tanggal) = p_ts
     group by d.id),
  uji as (
    select d.id, count(*)::int as n
      from jadwal_ta j join d on d.nidn = any(j.penguji)
     where j.status <> 'batal' and ts_dari(j.tanggal) = p_ts
     group by d.id),
  lomba as (
    select d.id, count(*)::int as n
      from lkps_prestasi_mahasiswa r join d on d.nidn = any(r.pembimbing)
     where r.status <> 'ditolak' and r.tahun + case when coalesce(r.bulan, 1) >= 9 then 1 else 0 end = p_ts
     group by d.id)
  select d.id, d.nama, d.kk,
         coalesce(kp.n, 0), coalesce(kp.selesai, 0),
         coalesce((select k.kuota from kp_kuota k where k.ts = p_ts and k.dosen_id = d.id),
                  (select k.kuota from kp_kuota k where k.ts = p_ts and k.dosen_id is null)),
         (select count(distinct t.m)::int from ta_mhs t where t.id = d.id),
         coalesce(lulus.n, 0), coalesce(uji.n, 0), coalesce(lomba.n, 0)
    from d
    left join kp on kp.id = d.id
    left join lulus on lulus.id = d.id
    left join uji on uji.id = d.id
    left join lomba on lomba.id = d.id
   order by d.nama
$$;

CREATE FUNCTION public.berhalangan_rentang_cek() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if new.slot_ids is not null then
    new.slot_ids := (select array_agg(distinct s order by s) from unnest(new.slot_ids) s);
    if exists (select 1 from unnest(new.slot_ids) s where not exists (select 1 from jadwal_slot j where j.id = s)) then
      raise exception 'Slot jam tidak dikenal; muat ulang halaman.'; end if;
  end if;
  if new.hari is not null then new.hari := (select array_agg(distinct h order by h) from unnest(new.hari) h); end if;
  new.diperbarui := now();
  return new;
end $$;

CREATE FUNCTION public.berhalangan_rentang_slot_hapus() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  -- Urutan penting: rentang yang hanya berisi slot ini dihapus dulu, supaya array_remove tidak menghasilkan daftar kosong
  -- (melanggar batas 1-30 slot dan tidak boleh menjadi "sepanjang hari").
  delete from dosen_berhalangan_rentang where slot_ids = array[old.id];
  update dosen_berhalangan_rentang set slot_ids = array_remove(slot_ids, old.id) where old.id = any(slot_ids);
  return old;
end $$;

CREATE FUNCTION public.bersihkan_jejak() RETURNS integer
    LANGUAGE plpgsql
    SET search_path TO 'public'
    AS $$
declare n integer;
begin
  delete from public.jejak where waktu < now() - interval '3 years';
  get diagnostics n = row_count;
  return n;
end $$;

CREATE FUNCTION public.bkd_milik(p bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.lkps_bkd b where b.id = p and b.nidn = public.nidn_saya())
$$;

CREATE FUNCTION public.boleh_email_alt() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select is_admin() or koordinator_aktif('koordinator_kp') or koordinator_aktif('koordinator_ta')
      or koordinator_aktif('pembina_kemahasiswaan')
$$;

CREATE FUNCTION public.boleh_hibah() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.dosen d
    where lower(d.email) = public.email_saya()
      and d.aktif and d.peran <> 'asesor')
$$;

CREATE FUNCTION public.boleh_mk(p_kurikulum text, p_kode text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.is_admin() or public.boleh_mutu()
    or exists (select 1 from public.ref_mata_kuliah m join public.dosen d on d.id = public.me()
               where m.kurikulum = p_kurikulum and m.kode = p_kode and d.nidn = any(m.pengampu))
    or exists (select 1 from public.cpl_kelas k
               where upper(k.kode_mk) = upper(p_kode) and public.me() is not null
                 and lower(k.dosen_email) = lower(auth.jwt() ->> 'email')
                 and (k.tahun_akademik, k.semester) = (select c.tahun_akademik, c.semester from public.cpl_kelas c
                   order by c.tahun_akademik desc, case c.semester when 'Genap' then 2 else 1 end desc limit 1))
    or public.mengajar_mk(p_kurikulum, p_kode)
$$;

CREATE FUNCTION public.boleh_mutu() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select is_admin() or koordinator_aktif('gkm')
$$;

CREATE FUNCTION public.boleh_narasi() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.dosen d
    where lower(d.email) = lower(auth.jwt() ->> 'email') and d.aktif
      and (d.peran = 'admin' or (d.tim_penyusun and d.peran <> 'asesor')))
    or public.koordinator_aktif('gkm')
$$;

CREATE FUNCTION public.boleh_pengajuan(p_jenis text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select is_admin() or case p_jenis
    when 'ta' then koordinator_aktif('koordinator_ta')
    when 'kp' then koordinator_aktif('koordinator_kp')
    when 'lomba' then koordinator_aktif('pembina_kemahasiswaan')
    when 'luaran' then koordinator_aktif('pembina_kemahasiswaan')
    when 'kabar' then koordinator_aktif('pembina_kemahasiswaan')
    else false end
$$;

CREATE FUNCTION public.boleh_portofolio_baca(p_ta text, p_sm text, p_kur text, p_kode text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.boleh_mk(p_kur, p_kode) or public.lihat_semua_hibah() or public.pengampu_kelas_mk(p_ta, p_sm, p_kode, null)
    or exists (select 1 from public.dosen d where d.id = public.me() and d.peran = 'asesor' and d.aktif)
$$;

CREATE FUNCTION public.boleh_portofolio_tulis(p_ta text, p_sm text, p_kur text, p_kode text, p_kelas text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when p_kelas is null
    then public.boleh_mk(p_kur, p_kode) or public.pengampu_kelas_mk(p_ta, p_sm, p_kode, null)
    else public.is_admin() or public.boleh_mutu() or public.pengampu_kelas_mk(p_ta, p_sm, p_kode, p_kelas)
      or exists (select 1 from public.ref_mata_kuliah m join public.dosen d on d.id = public.me()
                 where m.kurikulum = p_kur and m.kode = p_kode and d.nidn = any(m.pengampu)) end
$$;

CREATE FUNCTION public.boleh_rps(p_kurikulum text, p_kode text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.me() is not null and (
    exists (select 1 from public.ref_mata_kuliah m join public.dosen d on d.id = public.me()
             where m.kurikulum = p_kurikulum and m.kode = p_kode and d.nidn = any(m.pengampu))
    or exists (select 1 from public.cpl_kelas k
               where upper(k.kode_mk) = upper(p_kode)
                 and lower(k.dosen_email) = lower(auth.jwt() ->> 'email')
                 and (k.tahun_akademik, k.semester) = (select c.tahun_akademik, c.semester from public.cpl_kelas c
                   order by c.tahun_akademik desc, case c.semester when 'Genap' then 2 else 1 end desc limit 1))
    or public.mengajar_mk(p_kurikulum, p_kode))
$$;

CREATE FUNCTION public.boleh_silabus() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.is_admin() or exists (select 1 from public.dosen d where d.id = public.me() and d.aktif and d.peran <> 'asesor')
$$;

CREATE FUNCTION public.boleh_tabel(p_tabel text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select is_admin() or case
    when p_tabel = 'jadwal_ta' then koordinator_aktif('koordinator_ta')
    when p_tabel in ('lkps_prestasi_mahasiswa', 'lkps_publikasi_mahasiswa', 'lkps_luaran_mahasiswa')
      then koordinator_aktif('pembina_kemahasiswaan')
    when p_tabel in ('lkps_spmi_ppepp', 'lkps_target_kinerja', 'lkps_kepuasan_pengguna', 'ami_temuan', 'spmi_standar',
                     'spmi_standar_revisi', 'dokumen')
      then koordinator_aktif('gkm')
    else false end
$$;

CREATE FUNCTION public.cari_sha256(h text) RETURNS TABLE(sumber text, id bigint, url text, keterangan text, dokumen_id bigint)
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
#variable_conflict use_column
begin
  if public.me() is null then raise exception 'Belum masuk.'; end if;
  if h is null or h !~ '^[0-9a-f]{64}$' then return; end if;
  return query
    select t.sumber, t.id, t.url, t.keterangan, t.dokumen_id from (
      select 1 as urut, 'dokumen'::text as sumber, d.id, d.url,
             d.jenis || ' ' || d.tahun || case when d.judul <> '' then ' ' || d.judul else '' end as keterangan,
             d.id as dokumen_id
        from public.dokumen d where d.sha256 = h
      union all
      select 2, 'butir_bukti', b.id, b.url, 'butir ' || b.butir, null::bigint
        from public.butir_bukti b where b.sha256 = h and b.url is not null
      union all
      select 3, 'lkps_bukti', l.id, l.url, l.tabel, null::bigint
        from public.lkps_bukti l where l.sha256 = h and l.url is not null
      union all
      select 4, 'karya_bukti', kb.id, kb.url, coalesce(k.judul, ''), null::bigint
        from public.karya_bukti kb left join public.karya k on k.id = kb.karya_id
       where kb.sha256 = h
    ) t order by t.urut, t.id;
end $_$;

CREATE FUNCTION public.cari_waktu_rapat(p_peserta uuid[], p_dari date, p_sampai date, p_kecuali bigint DEFAULT NULL::bigint) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_nama boolean := pengatur_jadwal(); v jsonb;
begin
  if me() is null then raise exception 'Masuk sebagai dosen terdaftar dulu.'; end if;
  if p_dari is null or p_sampai is null or p_sampai < p_dari or p_sampai - p_dari > 31 then
    raise exception 'Rentang tanggal 1-32 hari.'; end if;
  if coalesce(cardinality(p_peserta), 0) not between 1 and 60 then raise exception 'Pilih 1-60 peserta dosen.'; end if;
  with tgl as (
    select g::date as t from generate_series(p_dari, p_sampai, interval '1 day') g
     where extract(isodow from g)::smallint in (select hari from jadwal_hari)),
  sl as (select id, mulai, selesai from jadwal_slot where aktif),
  sibuk as (
    select b.dosen_id, tgl.t, b.slot_id
      from dosen_berhalangan b
      join tgl on extract(isodow from tgl.t)::smallint = b.hari
      join sl on sl.id = b.slot_id
      cross join lateral semester_tanggal(tgl.t) s
     where b.dosen_id = any(p_peserta) and b.tahun_akademik = s.ta and b.semester = s.sm
    union all
    select x.dosen_id, x.tanggal, sl.id
      from dosen_berhalangan_tgl x join tgl on tgl.t = x.tanggal join sl on x.slot_id is null or sl.id = x.slot_id
     where x.dosen_id = any(p_peserta)
    union all
    select r.dosen_id, tgl.t, sl.id
      from dosen_berhalangan_rentang r join tgl on tgl.t between r.mulai and r.selesai
      join sl on r.slot_ids is null or sl.id = any(r.slot_ids)
     where r.dosen_id = any(p_peserta) and (r.hari is null or extract(isodow from tgl.t)::smallint = any(r.hari))
    union all
    select p.dosen_id, ra.tanggal, sl.id
      from rapat ra join rapat_peserta p on p.rapat_id = ra.id join tgl on tgl.t = ra.tanggal
      join sl on ra.mulai is not null and ra.selesai is not null and sl.mulai < ra.selesai and sl.selesai > ra.mulai
     where p.dosen_id = any(p_peserta) and ra.id is distinct from p_kecuali
    union all
    -- 152: jadwal kuliah yang sudah disahkan (150), pada tanggal masa kuliah semesternya.
    select kd.dosen_id, tgl.t, sl.id
      from jadwal_kuliah j
      join kelas_kuliah k on k.id = j.kelas_id
      join kelas_dosen kd on kd.kelas_id = k.id
      join tgl on extract(isodow from tgl.t)::smallint = j.hari
      cross join lateral semester_tanggal(tgl.t) s
      join sl on sl.mulai < j.selesai and sl.selesai > j.mulai
     where kd.dosen_id = any(p_peserta) and k.tahun_akademik = s.ta and k.semester = s.sm
       and jadwal_periode_sah(k.tahun_akademik, k.semester) and masa_kuliah_tanggal(tgl.t, s.ta, s.sm))
  select jsonb_build_object('nama', v_nama, 'sibuk', coalesce(jsonb_agg(
           jsonb_build_object('tanggal', z.t, 'slot_id', z.slot_id, 'n', z.n)
           || case when v_nama then jsonb_build_object('dosen', z.d) else '{}'::jsonb end order by z.t, z.slot_id), '[]'::jsonb))
    into v
    from (select t, slot_id, count(distinct dosen_id)::int as n, to_jsonb(array_agg(distinct dosen_id)) as d from sibuk group by t, slot_id) z;
  return v;
end $$;

CREATE FUNCTION public.catat_aktif() RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  update dosen set terakhir_aktif = now() where id = me()
$$;

CREATE FUNCTION public.catat_jejak() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  lama   jsonb := case when tg_op <> 'INSERT' then to_jsonb(old) end;
  baru   jsonb := case when tg_op <> 'DELETE' then to_jsonb(new) end;
  r      jsonb := coalesce(baru, lama);
  abaikan constant text[] := array['diperbarui', 'diubah_pada', 'dibuat', 'dibuat_pada', 'judul_norm',
                                   'topik', 'jumlah_sitasi', 'sumber_sitasi', 'sitasi_diambil', 'sha256'];
  beda   jsonb := '{}'::jsonb;
  k      text;
  kunci  text;
  j      jsonb;
begin
  if tg_op = 'UPDATE' then
    for k in select jsonb_object_keys(baru) loop
      if not (k = any(abaikan)) and (lama -> k) is distinct from (baru -> k) then
        beda := beda || jsonb_build_object(k, jsonb_build_array(lama -> k, baru -> k));
      end if;
    end loop;
    if beda = '{}'::jsonb then return null; end if;
  end if;
  select string_agg(r ->> a.attname, '|' order by array_position(i.indkey::int2[], a.attnum))
    into kunci
    from pg_index i join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
   where i.indrelid = tg_relid and i.indisprimary;
  begin j := auth.jwt(); exception when others then j := null; end;
  insert into public.jejak (tabel, baris, aksi, oleh, ubah, isi)
  values (tg_table_name, kunci,
          case tg_op when 'INSERT' then 'tambah' when 'UPDATE' then 'ubah' else 'hapus' end,
          lower(coalesce(nullif(j ->> 'email', ''), 'sistem (' || coalesce(nullif(j ->> 'role', ''), session_user::text) || ')')),
          case when tg_op = 'UPDATE' then beda end,
          case tg_op when 'INSERT' then baru when 'DELETE' then lama end);
  return null;
end $$;

CREATE FUNCTION public.catat_kunjungan(p_halaman text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare v_hari date := (now() at time zone 'Asia/Jakarta')::date; v_hal text := lower(btrim(coalesce(p_halaman, '')));
begin
  if public.me() is null or v_hal !~ '^[a-z0-9._-]{1,80}$' then return; end if;
  insert into pemakaian_halaman (tanggal, halaman, dosen_id, peran, jabatan)
  select v_hari, v_hal, d.id, d.peran,
         coalesce((select array_agg(distinct k.jabatan order by k.jabatan) from koordinator k where k.dosen_id = d.id
                     and k.mulai <= v_hari and (k.selesai is null or k.selesai >= v_hari)), '{}')
    from dosen d where d.id = public.me()
  on conflict (tanggal, halaman, dosen_id) do update set n = pemakaian_halaman.n + 1;
  if random() < 0.01 then delete from pemakaian_halaman where tanggal < v_hari - 180; end if;
end $_$;

CREATE FUNCTION public.catat_kunjungan_publik(p_halaman text, p_rujukan text, p_peristiwa text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  v_hari date := (now() at time zone 'Asia/Jakarta')::date;
  v_hal text := lower(btrim(coalesce(p_halaman, '')));
  v_ruj text := lower(btrim(coalesce(p_rujukan, '')));
  v_per text := lower(btrim(coalesce(p_peristiwa, '')));
begin
  if v_hal !~ '^[a-z0-9._/:-]{1,100}$'
     or v_ruj not in ('langsung', 'internal', 'google', 'bing', 'instagram', 'facebook', 'whatsapp', 'linkedin', 'youtube',
                      'tiktok', 'x', 'kampus', 'lainnya')
     or v_per not in ('lihat', 'kuis_selesai', 'daftar_klik') then
    return;
  end if;
  insert into kunjungan_publik (tanggal, halaman, rujukan, peristiwa) values (v_hari, v_hal, v_ruj, v_per)
  on conflict (tanggal, halaman, rujukan, peristiwa) do update set n = kunjungan_publik.n + 1
    where kunjungan_publik.n < 100000;
  if random() < 0.005 then delete from kunjungan_publik where tanggal < v_hari - 400; end if;
end $_$;

CREATE FUNCTION public.catat_openalex(d jsonb) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare n integer;
begin
  if not public.is_admin() then
    raise exception 'Mencatat ID OpenAlex khusus admin.';
  end if;
  update public.karya k set openalex_id = x.oa
    from jsonb_to_recordset(d) as x(id uuid, oa text)
   where k.id = x.id and k.status <> 'draf' and x.oa ~ '^W[0-9]+$'
     and k.openalex_id is distinct from x.oa;
  get diagnostics n = row_count;
  return n;
end $_$;

CREATE FUNCTION public.catat_terbitan(d jsonb) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare n integer;
begin
  if not public.is_admin() then
    raise exception 'Mencatat volume, nomor, dan halaman khusus admin.';
  end if;
  with baru as (
    select k.id,
           coalesce(nullif(trim(k.volume), ''),  nullif(left(trim(x.volume), 40), ''))  as v,
           coalesce(nullif(trim(k.nomor), ''),   nullif(left(trim(x.nomor), 40), ''))   as n,
           coalesce(nullif(trim(k.halaman), ''), nullif(left(trim(x.halaman), 40), '')) as h
      from public.karya k
      join jsonb_to_recordset(d) as x(id uuid, volume text, nomor text, halaman text) on x.id = k.id
     where k.kategori = 'publikasi' and k.status <> 'draf')
  update public.karya k set volume = b.v, nomor = b.n, halaman = b.h
    from baru b
   where k.id = b.id
     and (k.volume is distinct from b.v or k.nomor is distinct from b.n or k.halaman is distinct from b.h);
  get diagnostics n = row_count;
  return n;
end $$;

CREATE FUNCTION public.catat_topik(d jsonb) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare n integer;
begin
  if not public.is_admin() then
    raise exception 'Mencatat topik khusus admin.';
  end if;
  update public.karya k set topik = x.topik
    from jsonb_to_recordset(d) as x(id uuid, topik jsonb)
   where k.id = x.id and k.status <> 'draf' and jsonb_typeof(x.topik) = 'array'
     and k.topik is distinct from x.topik;
  get diagnostics n = row_count;
  return n;
end $$;

CREATE FUNCTION public.cpl_belum_semester() RETURNS TABLE(tahun_akademik text, semester text, kode_mk text, belum text[])
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with r as (select data from public.cpl_ringkasan order by diunggah desc, id desc limit 1),
  k as (select x, regexp_match(coalesce(x ->> 'term', ''), '(\d{4})\s*/\s*(\d{4})\s*(ganjil|genap)', 'i') m
        from r, jsonb_array_elements(case when jsonb_typeof(r.data -> 'kelas') = 'array' then r.data -> 'kelas' else '[]'::jsonb end) x)
  select k.m[1] || '/' || k.m[2], initcap(lower(k.m[3])), upper(k.x ->> 'course_code'),
         array_agg(distinct (k.x ->> 'cpl') || ' kelas ' || (k.x ->> 'class_name'))
  from k
  where k.m is not null and k.x ->> 'status' = 'BELUM' and coalesce(k.x ->> 'course_code', '') <> ''
  group by 1, 2, 3
$$;

CREATE FUNCTION public.cpl_belum_tanpa_evaluasi() RETURNS TABLE(tahun_akademik text, semester text, kode_mk text, belum text[])
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select c.tahun_akademik, c.semester, c.kode_mk, c.belum
  from public.cpl_belum_semester() c
  where (public.lihat_semua_hibah() or public.boleh_mutu())
    and not exists (select 1 from public.evaluasi_mk e where e.tahun_akademik = c.tahun_akademik and e.semester = c.semester
                      and upper(e.kode_mk) = c.kode_mk)
  order by c.tahun_akademik desc, c.semester desc, c.kode_mk
$$;

CREATE FUNCTION public.cpl_kelas_milik(p_kelas bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.cpl_kelas k
                 where k.id = p_kelas and public.me() is not null
                   and lower(k.dosen_email) = public.email_saya())
$$;

CREATE FUNCTION public.dokumen_mahasiswa() RETURNS TABLE(id bigint, jenis text, tahun integer, judul text, nomor text, tanggal date, berlaku_sampai date, url text, diperbarui timestamp with time zone)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select d.id, d.jenis, d.tahun, d.judul, d.nomor, d.tanggal, d.berlaku_sampai, d.url, d.diperbarui
    from public.dokumen d
   where d.untuk_mahasiswa
     and d.url !~* 'lkd\.html'
     and (d.berlaku_sampai is null or d.berlaku_sampai >= current_date)
   order by d.diperbarui desc
   limit 500;
$$;

CREATE FUNCTION public.dosen_mengampu(p_ta text) RETURNS TABLE(dosen_id uuid, sumber text)
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if me() is null then raise exception 'Masuk sebagai pengguna terdaftar dulu.'; end if;
  return query
    select distinct kd.dosen_id, 'kelas'::text from kelas_dosen kd join kelas_kuliah k on k.id = kd.kelas_id where k.tahun_akademik = p_ta
    union
    select a.dosen_id, 'manual'::text from dosen_ampu_ts a where a.tahun_akademik = p_ta;
end $$;

CREATE FUNCTION public.email_saya() RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with cocok as (
    select lower(d.email) as email, d.boleh_masuk from public.dosen d
     where lower(d.email) = lower(auth.jwt() ->> 'email')
        or lower(d.email_alternatif) = lower(auth.jwt() ->> 'email')
     -- coalesce: email kosong -> false (DESC menaruh NULL paling depan)
     order by coalesce(lower(d.email) = lower(auth.jwt() ->> 'email'), false) desc, d.aktif desc
     limit 1)
  select case when exists (select 1 from cocok)
              then (select case when c.boleh_masuk then c.email end from cocok c)
              else lower(auth.jwt() ->> 'email') end
$$;

CREATE FUNCTION public.evaluasi_perlu_tl() RETURNS TABLE(evaluasi_id bigint, dosen_id uuid, tahun_akademik text, semester text, kode_mk text, nama_mk text, alasan text[])
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with amb as (select coalesce((select nilai::numeric from public.pengaturan where kunci = 'ambang_edom'), 3.00) a),
  c as (select * from public.cpl_belum_semester())
  select e.id, e.dosen_id, e.tahun_akademik, e.semester, e.kode_mk, e.nama_mk,
         array_remove(array[
           case when e.edom is not null and e.edom < amb.a then
             'EDOM ' || replace(to_char(e.edom, 'FM0.00'), '.', ',') || ' di bawah ' || replace(to_char(amb.a, 'FM0.00'), '.', ',') end,
           case when c.belum is not null then 'CPL belum tercapai: ' || array_to_string(c.belum, ', ') end,
           case when e.rps_sesuai = 'tidak' then 'pelaksanaan tidak sesuai RPS' end], null)
  from public.evaluasi_mk e cross join amb
  left join c on c.tahun_akademik = e.tahun_akademik and c.semester = e.semester and c.kode_mk = upper(e.kode_mk)
  where (e.dosen_id = public.me() or public.lihat_semua_hibah() or public.boleh_mutu())
    and not exists (select 1 from public.evaluasi_tindak t where t.evaluasi_id = e.id)
    and ((e.edom is not null and e.edom < amb.a) or c.belum is not null or e.rps_sesuai = 'tidak')
  order by e.tahun_akademik desc, e.semester desc, e.kode_mk
$$;

CREATE FUNCTION public.hanya_baca() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.dosen d
    where lower(d.email) = public.email_saya() and d.aktif
      and d.peran = 'pimpinan' and not coalesce(d.dtps, false))
$$;

CREATE FUNCTION public.hapus_bukti_awal(k uuid) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare lama text;
begin
  if not (public.is_admin() or public.penulis_karya(k)) then
    raise exception 'Hanya penulis karya ini atau admin yang boleh menghapus buktinya.';
  end if;
  select bukti_url into lama from public.karya where id = k;
  if not found then raise exception 'Karya tidak ditemukan.'; end if;
  if lama is not null then
    update public.karya set bukti_url = null where id = k;
  end if;
  return lama;
end $$;

CREATE FUNCTION public.hapus_bukti_prestasi() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  delete from public.lkps_bukti where tabel = 'lkps_prestasi_mahasiswa' and baris_id = old.id;
  return old;
end $$;

CREATE FUNCTION public.hari_libur_antara(p_dari date, p_sampai date) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if p_dari is null or p_sampai is null or p_sampai < p_dari or p_sampai - p_dari > 400 then
    raise exception 'Rentang tanggal hari libur 1-400 hari.';
  end if;
  return coalesce((select jsonb_agg(jsonb_build_object('tanggal', h.tanggal, 'nama', h.nama, 'jenis', h.jenis) order by h.tanggal)
                     from public.hari_libur h where h.tanggal between p_dari and p_sampai), '[]'::jsonb);
end $$;

CREATE FUNCTION public.hibah_rekap() RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when public.me() is null then '[]'::jsonb else coalesce((
    select jsonb_agg(jsonb_build_object(
      'tahun', x.tahun_usulan, 'kategori', x.kategori, 'skema', x.skema, 'kelompok', x.kelompok,
      'status', x.status, 'n', x.n, 'dana_usulan', x.du, 'dana_disetujui', x.dd)
      order by x.tahun_usulan, x.kategori, x.skema, x.status)
    from (select h.tahun_usulan, h.kategori, coalesce(r.nama, 'Belum dipilih') skema,
                 coalesce(k.nama, '') kelompok, h.status,
                 count(*)::int n, coalesce(sum(h.dana_usulan), 0) du, coalesce(sum(h.dana_disetujui), 0) dd
          from public.hibah_ajuan h
          left join public.ref_skema_dana r on r.kode = h.skema_kode
          left join public.ref_kelompok_dana k on k.kode = r.kelompok
          group by 1, 2, 3, 4, 5) x), '[]'::jsonb) end
$$;

CREATE FUNCTION public.id_dosen_login() RETURNS uuid
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select d.id from public.dosen d where lower(d.email) = public.email_saya() limit 1
$$;

CREATE FUNCTION public.insentif_ajukan(p_judul text, p_ids bigint[], p_catatan text DEFAULT NULL::text) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_id bigint; n int;
begin
  if not pengelola_insentif() then raise exception 'Pengajuan ke fakultas dibuat admin prodi atau Kaprodi aktif.'; end if;
  if coalesce(cardinality(p_ids), 0) = 0 then raise exception 'Pilih minimal satu klaim.'; end if;
  select count(*) into n from insentif_publikasi where id = any(p_ids) and status <> 'siap';
  if n > 0 or (select count(*) from insentif_publikasi where id = any(p_ids)) <> cardinality(p_ids) then
    raise exception 'Hanya klaim berstatus siap yang bisa diajukan.'; end if;
  insert into insentif_pengajuan (judul, catatan) values (btrim(p_judul), nullif(btrim(coalesce(p_catatan, '')), '')) returning id into v_id;
  update insentif_publikasi set status = 'diajukan', pengajuan_id = v_id, diperbarui = now(), oleh = me() where id = any(p_ids);
  return v_id;
end $$;

CREATE FUNCTION public.insentif_batal(p_karya uuid) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare i record;
begin
  select * into i from insentif_publikasi where karya_id = p_karya;
  if i.id is null then return; end if;
  if i.pengklaim_id <> me() and not pengelola_insentif() then raise exception 'Hanya pengklaim yang bisa membatalkan.'; end if;
  if i.status not in ('diklaim', 'dikembalikan') then
    raise exception 'Klaim berstatus % tidak bisa dibatalkan; hubungi admin prodi.', i.status; end if;
  delete from insentif_publikasi where id = i.id;
end $$;

CREATE FUNCTION public.insentif_berkas_kurang(p_karya uuid) RETURNS text[]
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce(array_agg(j order by o), '{}') from unnest(array['naskah', 'indeksasi', 'loa', 'pernyataan']) with ordinality x(j, o)
   where not exists (select 1 from karya_bukti b where b.karya_id = p_karya and b.jenis = x.j)
$$;

CREATE FUNCTION public.insentif_hasil(p_ids bigint[], p_status text, p_catatan text DEFAULT NULL::text) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare n int;
begin
  if not pengelola_insentif() then raise exception 'Hasil pengajuan dicatat admin prodi atau Kaprodi aktif.'; end if;
  if p_status not in ('disetujui', 'ditolak', 'cair', 'siap') then raise exception 'Status hasil tidak dikenal: %.', p_status; end if;
  -- Asal yang sah: diajukan -> disetujui | ditolak | siap (ditarik dari pengajuan); disetujui -> cair.
  select count(*) into n from insentif_publikasi where id = any(p_ids)
     and not ((status = 'diajukan' and p_status in ('disetujui', 'ditolak', 'siap')) or (status = 'disetujui' and p_status = 'cair'));
  if n > 0 then raise exception 'Ada klaim yang statusnya tidak bisa diubah menjadi %.', p_status; end if;
  update insentif_publikasi set status = p_status, pengajuan_id = case when p_status = 'siap' then null else pengajuan_id end,
         catatan = coalesce(nullif(btrim(coalesce(p_catatan, '')), ''), catatan), diperbarui = now(), oleh = me()
   where id = any(p_ids);
  get diagnostics n = row_count;
  return n;
end $$;

CREATE FUNCTION public.insentif_klaim(p_karya uuid) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare k record; i record; v_id bigint; v_tahun int := extract(year from now() at time zone 'Asia/Jakarta')::int;
begin
  if me() is null then raise exception 'Masuk dulu.'; end if;
  select id, kategori, tahun, status into k from karya where id = p_karya;
  if k.id is null then raise exception 'Publikasi tidak ditemukan.'; end if;
  if not penulis_karya(p_karya) then raise exception 'Hanya penulis publikasi ini yang bisa mengklaim insentif.'; end if;
  if k.kategori <> 'publikasi' then raise exception 'Insentif hanya untuk publikasi.'; end if;
  if k.tahun <> v_tahun then raise exception 'Insentif hanya untuk publikasi terbit tahun % (publikasi ini %).', v_tahun, k.tahun; end if;
  if k.status = 'ditolak' then raise exception 'Publikasi ini ditolak verifikasi; perbaiki dulu.'; end if;
  select * into i from insentif_publikasi where karya_id = p_karya;
  if i.id is not null then
    if i.pengklaim_id <> me() then raise exception 'Publikasi ini sudah diklaim penulis lain (satu klaim per publikasi).'; end if;
    if i.status <> 'dikembalikan' then return i.id; end if;
    update insentif_publikasi set status = 'diklaim', diperbarui = now(), oleh = me() where id = i.id;
    return i.id;
  end if;
  insert into insentif_publikasi (karya_id, pengklaim_id, oleh) values (p_karya, me(), me()) returning id into v_id;
  return v_id;
end $$;

CREATE FUNCTION public.insentif_periksa(p_id bigint, p_status text, p_catatan text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare i record; k record; v_kurang text[];
begin
  if not pengelola_insentif() then raise exception 'Klaim insentif diperiksa admin prodi atau Kaprodi aktif.'; end if;
  select * into i from insentif_publikasi where id = p_id;
  if i.id is null then raise exception 'Klaim tidak ditemukan.'; end if;
  if i.status not in ('diklaim', 'dikembalikan', 'siap') then raise exception 'Klaim berstatus % tidak diperiksa lagi.', i.status; end if;
  if p_status = 'dikembalikan' then
    if coalesce(btrim(p_catatan), '') = '' then raise exception 'Tulis catatan: apa yang perlu diperbaiki dosen.'; end if;
  elsif p_status = 'siap' then
    select status into k from karya where id = i.karya_id;
    if k.status <> 'terverifikasi' then raise exception 'Verifikasi publikasinya dulu (status sekarang: %).', k.status; end if;
    v_kurang := insentif_berkas_kurang(i.karya_id);
    if cardinality(v_kurang) > 0 then raise exception 'Berkas belum lengkap: %.', array_to_string(v_kurang, ', '); end if;
  else raise exception 'Status pemeriksaan harus siap atau dikembalikan.';
  end if;
  update insentif_publikasi set status = p_status, catatan = nullif(btrim(coalesce(p_catatan, '')), ''), diperbarui = now(), oleh = me()
   where id = p_id;
end $$;

CREATE FUNCTION public.is_admin() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.dosen d
    where lower(d.email) = public.email_saya()
      and d.aktif and d.peran = 'admin')
$$;

CREATE FUNCTION public.isi_sha256(p jsonb) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  x jsonb; u text; h text; n integer := 0; m integer;
begin
  if not public.is_admin() then raise exception 'Hanya admin.'; end if;
  for x in select * from jsonb_array_elements(coalesce(p, '[]'::jsonb)) loop
    u := x ->> 'url'; h := x ->> 'sha256';
    if u is null or h is null or h !~ '^[0-9a-f]{64}$' then continue; end if;
    update public.dokumen     set sha256 = h where url = u and sha256 is distinct from h; get diagnostics m = row_count; n := n + m;
    update public.butir_bukti set sha256 = h where url = u and sha256 is distinct from h; get diagnostics m = row_count; n := n + m;
    update public.karya_bukti set sha256 = h where url = u and sha256 is distinct from h; get diagnostics m = row_count; n := n + m;
    update public.lkps_bukti  set sha256 = h where url = u and sha256 is distinct from h; get diagnostics m = row_count; n := n + m;
  end loop;
  return n;
end $_$;

CREATE FUNCTION public.jadwal_berhalangan_rekap(p_ta text, p_semester text, p_dari date DEFAULT NULL::date, p_sampai date DEFAULT NULL::date) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when public.me() is null then null else jsonb_build_object(
    'mingguan', (select coalesce(jsonb_agg(jsonb_build_object('hari', hari, 'slot_id', slot_id, 'n', n)), '[]'::jsonb) from (
        select b.hari, b.slot_id, count(distinct b.dosen_id) n from dosen_berhalangan b join dosen d on d.id = b.dosen_id and d.aktif
         where b.tahun_akademik = p_ta and b.semester = p_semester group by b.hari, b.slot_id) x),
    'tanggal', (select coalesce(jsonb_agg(jsonb_build_object('tanggal', tanggal, 'slot_id', slot_id, 'n', n)), '[]'::jsonb) from (
        select u.tanggal, u.slot_id, count(distinct u.dosen_id) n from (
            select t.dosen_id, t.tanggal, t.slot_id from dosen_berhalangan_tgl t
             where p_dari is not null and t.tanggal between p_dari and coalesce(p_sampai, p_dari + 60)
            union all
            select r.dosen_id, g.tg::date, s.slot_id
              from dosen_berhalangan_rentang r
              cross join lateral generate_series(greatest(r.mulai, p_dari), least(r.selesai, coalesce(p_sampai, p_dari + 60)), interval '1 day') g(tg)
              left join lateral unnest(r.slot_ids) s(slot_id) on true
             where p_dari is not null and (r.hari is null or extract(isodow from g.tg)::smallint = any(r.hari))) u
          join dosen d on d.id = u.dosen_id and d.aktif
         group by u.tanggal, u.slot_id) y)) end
$$;

CREATE FUNCTION public.jadwal_impor(p_ta text, p_semester text, p_baris jsonb, p_ganti boolean DEFAULT false) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare b jsonb; no int := 0; masuk int := 0; berkunci int := 0; dihapus int := 0; galat text[] := '{}'; ids bigint[] := '{}';
  v_kelas bigint; v_hari smallint; v_mulai time; v_selesai time; ket text;
begin
  if not pengatur_kelas() then raise exception 'Jadwal kuliah disusun admin atau Kaprodi aktif.'; end if;
  if jadwal_periode_sah(p_ta, p_semester) then
    raise exception 'Jadwal % % sudah disahkan Kaprodi. Minta Kaprodi membuka kembali sebelum mengimpor.', p_semester, p_ta; end if;
  if jsonb_typeof(p_baris) <> 'array' then raise exception 'Isi impor harus daftar jadwal.'; end if;
  if jsonb_array_length(p_baris) > 2000 then raise exception 'Paling banyak 2000 baris sekali impor.'; end if;
  for b in select * from jsonb_array_elements(p_baris) loop
    no := no + 1;
    ket := format('Baris %s (kelas %s)', no, b ->> 'kelas_id');
    begin
      v_kelas := (b ->> 'kelas_id')::bigint; v_hari := (b ->> 'hari')::smallint;
      v_mulai := (b ->> 'mulai')::time; v_selesai := (b ->> 'selesai')::time;
    exception when others then galat := galat || format('%s: isian tidak terbaca.', ket); continue;
    end;
    if not exists (select 1 from kelas_kuliah where id = v_kelas and tahun_akademik = p_ta and semester = p_semester) then
      galat := galat || format('%s: kelas tidak ada di %s %s.', ket, p_semester, p_ta); continue; end if;
    if v_hari is null or v_hari not between 1 and 7 or v_mulai is null or v_selesai is null or v_selesai <= v_mulai then
      galat := galat || format('%s: hari 1-7 dan jam selesai sesudah jam mulai.', ket); continue; end if;
    ids := ids || v_kelas;
    if exists (select 1 from jadwal_kuliah where kelas_id = v_kelas and kunci) then berkunci := berkunci + 1; continue; end if;
    insert into jadwal_kuliah (kelas_id, hari, mulai, selesai, oleh) values (v_kelas, v_hari, v_mulai, v_selesai, auth.jwt() ->> 'email')
    on conflict (kelas_id) do update set hari = excluded.hari, mulai = excluded.mulai, selesai = excluded.selesai,
      oleh = excluded.oleh, diperbarui = now();
    masuk := masuk + 1;
  end loop;
  if p_ganti then
    delete from jadwal_kuliah j using kelas_kuliah k
     where k.id = j.kelas_id and k.tahun_akademik = p_ta and k.semester = p_semester and not j.kunci and not (j.kelas_id = any(ids));
    get diagnostics dihapus = row_count;
  end if;
  return jsonb_build_object('masuk', masuk, 'berkunci', berkunci, 'dihapus', dihapus, 'galat', to_jsonb(galat));
end $$;

CREATE FUNCTION public.jadwal_periode_sah(p_ta text, p_semester text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from jadwal_kuliah_sah where tahun_akademik = p_ta and semester = p_semester)
$$;

CREATE FUNCTION public.jadwal_sahkan(p_ta text, p_semester text, p_sah boolean) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare n_kelas int; n_tanpa int; bentrok text;
begin
  if not koordinator_aktif('kaprodi') then raise exception 'Jadwal kuliah disahkan Kaprodi aktif.'; end if;
  if not p_sah then
    delete from jadwal_kuliah_sah where tahun_akademik = p_ta and semester = p_semester;
    return jsonb_build_object('sah', false);
  end if;
  select count(*), count(*) filter (where j.kelas_id is null) into n_kelas, n_tanpa
    from kelas_kuliah k left join jadwal_kuliah j on j.kelas_id = k.id where k.tahun_akademik = p_ta and k.semester = p_semester;
  if n_kelas = 0 then raise exception 'Belum ada kelas % %.', p_semester, p_ta; end if;
  if n_tanpa > 0 then raise exception '% dari % kelas % % belum berjadwal.', n_tanpa, n_kelas, p_semester, p_ta; end if;
  select string_agg(distinct format('%s (%s %s dan %s %s)', d.nama, ka.kode_mk, ka.kelas, kb.kode_mk, kb.kelas), '; ') into bentrok
    from jadwal_kuliah a join kelas_kuliah ka on ka.id = a.kelas_id
    join kelas_dosen da on da.kelas_id = a.kelas_id
    join jadwal_kuliah b on b.hari = a.hari and b.kelas_id > a.kelas_id and a.mulai < b.selesai and b.mulai < a.selesai
    join kelas_kuliah kb on kb.id = b.kelas_id and kb.tahun_akademik = ka.tahun_akademik and kb.semester = ka.semester
    join kelas_dosen db on db.kelas_id = b.kelas_id and db.dosen_id = da.dosen_id
    join dosen d on d.id = da.dosen_id
   where ka.tahun_akademik = p_ta and ka.semester = p_semester;
  if bentrok is not null then raise exception 'Dosen bentrok: %.', bentrok; end if;
  insert into jadwal_kuliah_sah (tahun_akademik, semester, sah_oleh) values (p_ta, p_semester, auth.jwt() ->> 'email')
  on conflict (tahun_akademik, semester) do update set sah_oleh = excluded.sah_oleh, sah_pada = now();
  return jsonb_build_object('sah', true, 'kelas', n_kelas);
end $$;

CREATE FUNCTION public.jadwal_simpan(p jsonb) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_kelas bigint := nullif(p ->> 'kelas_id', '')::bigint; k kelas_kuliah; j jadwal_kuliah; v_sah boolean;
  v_hari smallint := nullif(p ->> 'hari', '')::smallint; v_mulai time := nullif(p ->> 'mulai', '')::time;
  v_selesai time := nullif(p ->> 'selesai', '')::time; v_ruang text := nullif(btrim(coalesce(p ->> 'ruang', '')), '');
begin
  if not pengatur_kelas() then raise exception 'Jadwal kuliah disusun admin atau Kaprodi aktif.'; end if;
  select * into k from kelas_kuliah where id = v_kelas;
  if not found then raise exception 'Kelas tidak ditemukan.'; end if;
  select * into j from jadwal_kuliah where kelas_id = v_kelas;
  v_sah := jadwal_periode_sah(k.tahun_akademik, k.semester);
  if v_sah and (j.kelas_id is null or v_hari is distinct from j.hari or v_mulai is distinct from j.mulai
                or v_selesai is distinct from j.selesai) then
    raise exception 'Jadwal % % sudah disahkan Kaprodi: hari dan jam terkunci (ruang tetap boleh diisi). Minta Kaprodi membuka kembali.',
      k.semester, k.tahun_akademik;
  end if;
  if v_hari is null then
    delete from jadwal_kuliah where kelas_id = v_kelas;
    return jsonb_build_object('kelas_id', v_kelas, 'hapus', true);
  end if;
  if v_mulai is null or v_selesai is null or v_selesai <= v_mulai then
    raise exception 'Kelas % %: jam selesai harus sesudah jam mulai.', k.kode_mk, k.kelas; end if;
  insert into jadwal_kuliah (kelas_id, hari, mulai, selesai, ruang, kunci, oleh)
  values (v_kelas, v_hari, v_mulai, v_selesai, v_ruang, coalesce((p ->> 'kunci')::boolean, false), auth.jwt() ->> 'email')
  on conflict (kelas_id) do update set hari = excluded.hari, mulai = excluded.mulai, selesai = excluded.selesai, ruang = excluded.ruang,
    kunci = case when p ? 'kunci' then excluded.kunci else jadwal_kuliah.kunci end, oleh = excluded.oleh, diperbarui = now();
  return jsonb_build_object('kelas_id', v_kelas, 'hapus', false);
end $$;

CREATE FUNCTION public.jaga_email_alternatif() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  new.email_alternatif := nullif(lower(trim(coalesce(new.email_alternatif, ''))), '');
  if new.email_alternatif is not null then
    if new.email_alternatif = lower(new.email) then
      raise exception 'Email alternatif sama dengan email utama.';
    end if;
    if exists (select 1 from public.dosen d where d.id <> new.id
               and (lower(d.email) = new.email_alternatif or lower(d.email_alternatif) = new.email_alternatif)) then
      raise exception 'Email alternatif % sudah dipakai dosen lain.', new.email_alternatif;
    end if;
  end if;
  if exists (select 1 from public.dosen d where d.id <> new.id and lower(d.email_alternatif) = lower(new.email)) then
    raise exception 'Email % sudah menjadi email alternatif dosen lain.', new.email;
  end if;
  return new;
end $$;

CREATE FUNCTION public.jaga_evaluasi_mk() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public'
    AS $$
begin
  if public.boleh_mutu() then return new; end if;
  if (new.tahun_akademik, new.semester, new.kode_mk, new.nama_mk, new.dosen_id, new.edom, new.edom_responden)
     is distinct from (old.tahun_akademik, old.semester, old.kode_mk, old.nama_mk, old.dosen_id, old.edom, old.edom_responden) then
    raise exception 'Hanya admin atau GKM yang mengubah mata kuliah, dosen, dan angka EDOM.';
  end if;
  return new;
end $$;

CREATE FUNCTION public.jaga_hanya_baca() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if public.hanya_baca() then
    -- Penetapan oleh Dekan aktif (116, 134; keputusan pemilik 2026-11-19/21).
    if tg_table_name in ('mk_rps', 'mk_rps_pengesahan', 'mk_padanan_sah') and public.koordinator_aktif('dekan') then
      if tg_level = 'STATEMENT' then return null; end if;
      return case when tg_op = 'DELETE' then old else new end;
    end if;
    -- catat_aktif (123): pimpinan boleh memperbarui terakhir_aktif miliknya saja.
    if tg_level = 'ROW' and tg_table_name = 'dosen' and tg_op = 'UPDATE'
       and (to_jsonb(new) - 'terakhir_aktif') = (to_jsonb(old) - 'terakhir_aktif') then
      return new;
    end if;
    raise exception 'Akun pimpinan hanya untuk melihat (hanya-baca).' using errcode = '42501';
  end if;
  if tg_level = 'STATEMENT' then return null; end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;

CREATE FUNCTION public.jaga_hibah_ajuan() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public'
    AS $$
begin
  new.dibuat_oleh := old.dibuat_oleh;
  new.dibuat := old.dibuat;
  new.diperbarui := now();
  return new;
end $$;

CREATE FUNCTION public.jaga_kegiatan() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public'
    AS $$
begin
  new.dibuat := old.dibuat;
  new.diperbarui := now();
  return new;
end $$;

CREATE FUNCTION public.jaga_mk_rps() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if current_setting('rps.fungsi', true) = '1' then return new; end if;   -- rps_ajukan / rps_putuskan / rps_tetapkan
  if tg_op = 'INSERT' then
    new.revisi := 0; new.sah := null; new.sah_pada := null; new.sah_oleh := null; new.sah_atas_nama := null;
    new.tetap_pada := null; new.tetap_oleh := null; new.tetap_atas_nama := null; new.kode_verifikasi := null;
  else
    new.revisi := old.revisi; new.sah := old.sah; new.sah_pada := old.sah_pada; new.sah_oleh := old.sah_oleh; new.sah_atas_nama := old.sah_atas_nama;
    new.tetap_pada := old.tetap_pada; new.tetap_oleh := old.tetap_oleh; new.tetap_atas_nama := old.tetap_atas_nama;
    new.kode_verifikasi := old.kode_verifikasi;
  end if;
  return new;
end $$;

CREATE FUNCTION public.jaga_mk_rps_tinjauan() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if current_setting('tinjauan.fungsi', true) = '1' then return new; end if;
  if tg_op = 'INSERT' then
    if public.term_urut(new.tahun_akademik, new.semester) < coalesce((select nilai from pengaturan where kunci = 'tinjauan_rps_mulai'), 0) then
      raise exception 'Tinjauan RPS dimulai dari semester yang ditetapkan admin (pengaturan tinjauan_rps_mulai); semester ini sebelum itu.'; end if;
    if not tinjauan_nilai_ada(new.kurikulum, new.kode_mk, new.tahun_akademik, new.semester) then
      raise exception 'Nilai akhir MK ini untuk semester ini belum ada di ringkasan CPL; tinjauan dibuka setelah nilai akhir keluar.'; end if;
    new.status := 'draf'; new.rps_dasar := null; new.disetujui_pada := null; new.disetujui_oleh := null;
  else
    new.kurikulum := old.kurikulum; new.kode_mk := old.kode_mk; new.tahun_akademik := old.tahun_akademik; new.semester := old.semester;
    new.status := 'draf'; new.rps_dasar := old.rps_dasar; new.disetujui_pada := old.disetujui_pada; new.disetujui_oleh := old.disetujui_oleh;
  end if;
  new.oleh := coalesce(auth.jwt() ->> 'email', new.oleh);
  new.diperbarui := now();
  return new;
end $$;

CREATE FUNCTION public.jaga_rapat() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public'
    AS $$
begin
  new.dibuat_oleh := old.dibuat_oleh;
  new.dibuat := old.dibuat;
  new.diperbarui := now();
  return new;
end $$;

CREATE FUNCTION public.jejak_mk_rps() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if tg_op = 'UPDATE' and new.data is not distinct from old.data then return new; end if;
  new.oleh := coalesce(auth.jwt() ->> 'email', new.oleh);
  new.diperbarui := now();
  insert into public.mk_rps_riwayat (kurikulum, kode_mk, data, status, oleh) values (new.kurikulum, new.kode_mk, new.data, new.status, new.oleh);
  return new;
end $$;

CREATE FUNCTION public.jejak_mk_struktur() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  new.oleh := coalesce(auth.jwt() ->> 'email', new.oleh);
  new.diperbarui := now();
  insert into public.mk_struktur_riwayat (kurikulum, kode_mk, data, oleh) values (new.kurikulum, new.kode_mk, new.data, new.oleh);
  return new;
end $$;

CREATE FUNCTION public.jejak_portofolio() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  new.oleh := coalesce(auth.jwt() ->> 'email', new.oleh);
  new.diunggah := now();
  return new;
end $$;

CREATE FUNCTION public.jumlah_rujukan(u text) RETURNS integer
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare n integer;
begin
  if public.me() is null then raise exception 'Belum masuk.'; end if;
  select (select count(*) from public.dokumen     where url = u)
       + (select count(*) from public.butir_bukti where url = u)
       + (select count(*) from public.karya_bukti where url = u)
       + (select count(*) from public.lkps_bukti  where url = u)
       + (select count(*) from public.karya       where bukti_url = u)
    into n;
  return n;
end $$;

CREATE FUNCTION public.keamanan_antrean(p_kunci text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  return jsonb_build_object(
    'peringatan', (select coalesce(jsonb_agg(jsonb_build_object('id', id, 'waktu', waktu, 'jenis', jenis, 'oleh', oleh, 'rinci', rinci)
                     order by id), '[]'::jsonb) from (select * from peringatan_keamanan where dikirim is null order by id limit 100) q),
    'admin', (select coalesce(jsonb_agg(distinct lower(d.email)), '[]'::jsonb) from dosen d
               where d.peran = 'admin' and coalesce(d.email, '') like '%@%'));
end;
$$;

CREATE FUNCTION public.keamanan_tandai(p_kunci text, p_ids bigint[]) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare n int;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  update peringatan_keamanan set dikirim = now() where id = any(p_ids) and dikirim is null;
  get diagnostics n = row_count;
  return n;
end;
$$;

CREATE FUNCTION public.kelas_impor(p_ta text, p_semester text, p_baris jsonb, p_ganti boolean DEFAULT false) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare b jsonb; s text; v_dosen jsonb; v_id uuid; masuk int := 0; dihapus int := 0; galat text[] := '{}'; kunci text[] := '{}';
  no int := 0; ket text;
begin
  if not pengatur_kelas() then raise exception 'Kelas disusun admin atau Kaprodi aktif.'; end if;
  if jsonb_typeof(p_baris) <> 'array' then raise exception 'Isi impor harus daftar kelas.'; end if;
  if jsonb_array_length(p_baris) > 1000 then raise exception 'Paling banyak 1000 kelas sekali impor.'; end if;
  for b in select * from jsonb_array_elements(p_baris) loop
    no := no + 1;
    ket := format('Baris %s (%s %s)', no, b ->> 'kode_mk', b ->> 'kelas');
    if not exists (select 1 from ref_mata_kuliah where kurikulum = b ->> 'kurikulum' and kode = b ->> 'kode_mk') then
      galat := galat || format('%s: MK tidak ada di %s.', ket, b ->> 'kurikulum'); continue; end if;
    v_dosen := '[]'::jsonb;
    for s in select jsonb_array_elements_text(coalesce(b -> 'dosen', '[]'::jsonb)) loop
      select id into v_id from dosen where (nidn = btrim(s) or lower(email) = lower(btrim(s))) and aktif limit 1;
      if v_id is null then galat := galat || format('%s: dosen "%s" tidak terdaftar/aktif.', ket, s); v_dosen := null; exit; end if;
      v_dosen := v_dosen || jsonb_build_array(jsonb_build_object('dosen_id', v_id,
                   'peran', case when jsonb_array_length(v_dosen) = 0 then 'koordinator' else 'anggota' end));
    end loop;
    if v_dosen is null then continue; end if;
    begin
      perform kelas_simpan(b || jsonb_build_object('tahun_akademik', p_ta, 'semester', p_semester, 'dosen', v_dosen, 'id', null));
      masuk := masuk + 1;
      kunci := kunci || (b ->> 'kurikulum' || '|' || (b ->> 'kode_mk') || '|' || btrim(b ->> 'kelas'));
    exception when others then galat := galat || format('%s: %s', ket, sqlerrm);
    end;
  end loop;
  if p_ganti then
    delete from kelas_kuliah k where k.tahun_akademik = p_ta and k.semester = p_semester
      and not (k.kurikulum || '|' || k.kode_mk || '|' || k.kelas = any(kunci));
    get diagnostics dihapus = row_count;
  end if;
  return jsonb_build_object('masuk', masuk, 'dihapus', dihapus, 'galat', to_jsonb(galat));
end $$;

CREATE FUNCTION public.kelas_ke_cpl(p_ta text, p_semester text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r record; n int := 0; bentrok text[] := '{}'; tanpa text[] := '{}';
begin
  if not pengatur_kelas() then raise exception 'Kelas disusun admin atau Kaprodi aktif.'; end if;
  for r in
    select k.kode_mk, k.kelas, min(m.nama) as nama, count(*) as n, min(d.email) as email
      from kelas_kuliah k
      join ref_mata_kuliah m on m.kurikulum = k.kurikulum and m.kode = k.kode_mk
      left join kelas_dosen kd on kd.kelas_id = k.id and kd.peran = 'koordinator'
      left join dosen d on d.id = kd.dosen_id
     where k.tahun_akademik = p_ta and k.semester = p_semester
     group by k.kode_mk, k.kelas
  loop
    if r.n > 1 then bentrok := bentrok || (r.kode_mk || ' ' || r.kelas); continue; end if;
    if r.email is null then tanpa := tanpa || (r.kode_mk || ' ' || r.kelas); continue; end if;
    insert into cpl_kelas (tahun_akademik, semester, kode_mk, nama_mk, kelas, dosen_email, oleh)
    values (p_ta, p_semester, r.kode_mk, left(r.nama, 150), r.kelas, lower(r.email), auth.jwt() ->> 'email')
    on conflict (tahun_akademik, semester, kode_mk, kelas) do update
      set nama_mk = excluded.nama_mk, dosen_email = excluded.dosen_email, oleh = excluded.oleh;
    n := n + 1;
  end loop;
  return jsonb_build_object('disalin', n, 'bentrok_kurikulum', to_jsonb(bentrok), 'tanpa_koordinator', to_jsonb(tanpa));
end $$;

CREATE FUNCTION public.kelas_simpan(p jsonb) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_id bigint := nullif(p ->> 'id', '')::bigint; d jsonb; n_koor int; i int := 0; v_unit text; n_dosen int;
begin
  if not pengatur_kelas() then raise exception 'Kelas disusun admin atau Kaprodi aktif.'; end if;
  if jsonb_typeof(coalesce(p -> 'dosen', 'null')) <> 'array' then
    raise exception 'Kelas % %: daftar dosen harus berupa daftar.', p ->> 'kode_mk', p ->> 'kelas'; end if;
  select unit_penyelenggara into v_unit from ref_mata_kuliah where kurikulum = p ->> 'kurikulum' and kode = p ->> 'kode_mk';
  n_dosen := jsonb_array_length(p -> 'dosen');
  if n_dosen = 0 and coalesce(v_unit, 'prodi') not in ('universitas', 'fakultas') then
    raise exception 'Kelas % %: pilih minimal satu dosen.', p ->> 'kode_mk', p ->> 'kelas'; end if;
  if n_dosen > 0 then
    select count(*) into n_koor from jsonb_array_elements(p -> 'dosen') x where x ->> 'peran' = 'koordinator';
    if n_koor <> 1 then raise exception 'Kelas % %: tetapkan tepat satu koordinator kelas.', p ->> 'kode_mk', p ->> 'kelas'; end if;
  end if;
  if v_id is null then
    insert into kelas_kuliah (tahun_akademik, semester, kurikulum, kode_mk, kelas, kapasitas, angkatan, catatan, oleh)
    values (p ->> 'tahun_akademik', p ->> 'semester', p ->> 'kurikulum', p ->> 'kode_mk', btrim(p ->> 'kelas'),
            nullif(p ->> 'kapasitas', '')::int, nullif(btrim(coalesce(p ->> 'angkatan', '')), ''),
            nullif(btrim(coalesce(p ->> 'catatan', '')), ''), auth.jwt() ->> 'email')
    on conflict (tahun_akademik, semester, kurikulum, kode_mk, kelas) do update
      set kapasitas = excluded.kapasitas, angkatan = excluded.angkatan, catatan = excluded.catatan, oleh = excluded.oleh, diperbarui = now()
    returning id into v_id;
  else
    update kelas_kuliah set kelas = btrim(p ->> 'kelas'), kapasitas = nullif(p ->> 'kapasitas', '')::int,
           angkatan = nullif(btrim(coalesce(p ->> 'angkatan', '')), ''), catatan = nullif(btrim(coalesce(p ->> 'catatan', '')), ''),
           oleh = auth.jwt() ->> 'email', diperbarui = now()
     where id = v_id;
    if not found then raise exception 'Kelas tidak ditemukan.'; end if;
  end if;
  delete from kelas_dosen where kelas_id = v_id;
  for d in select * from jsonb_array_elements(p -> 'dosen') loop
    if not exists (select 1 from dosen where id = (d ->> 'dosen_id')::uuid) then raise exception 'Dosen tidak dikenal.'; end if;
    insert into kelas_dosen (kelas_id, dosen_id, peran, pertemuan, urutan)
    values (v_id, (d ->> 'dosen_id')::uuid, coalesce(d ->> 'peran', 'anggota'), nullif(d ->> 'pertemuan', '')::int, i)
    on conflict (kelas_id, dosen_id) do nothing;
    i := i + 1;
  end loop;
  return v_id;
end $$;

CREATE FUNCTION public.kepala_lab_dari(p_lab bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from koordinator k where k.dosen_id = me() and k.jabatan = 'kepala_lab' and k.laboratorium_id = p_lab
                   and k.mulai <= current_date and (k.selesai is null or k.selesai >= current_date))
$$;

CREATE FUNCTION public.kirim_masukan_mahasiswa(p_jenis text, p_isi text, p_nama text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_jebakan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  v_isi   text := btrim(coalesce(p_isi, ''));
  v_nama  text := nullif(btrim(coalesce(p_nama, '')), '');
  v_email text := nullif(lower(btrim(coalesce(p_email, ''))), '');
begin
  -- Kolom jebakan tidak terlihat oleh manusia; bila terisi, pura-pura berhasil.
  if coalesce(btrim(p_jebakan), '') <> '' then return 'ok'; end if;
  if p_jenis not in ('tanya', 'masukan') then raise exception 'Jenis kiriman tidak dikenal.'; end if;
  if length(v_isi) < 10 then raise exception 'Isi terlalu pendek (minimal 10 huruf).'; end if;
  if length(v_isi) > 3000 then raise exception 'Isi terlalu panjang (maksimal 3000 huruf).'; end if;
  if v_nama is not null and length(v_nama) > 120 then raise exception 'Nama terlalu panjang.'; end if;
  if v_email is not null and (length(v_email) > 200 or v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$') then
    raise exception 'Alamat email tidak sah.';
  end if;
  if exists (select 1 from masukan_mahasiswa m
              where m.isi = v_isi and m.dikirim > now() - interval '24 hours') then
    raise exception 'Kiriman yang sama sudah diterima.';
  end if;
  if (select count(*) from masukan_mahasiswa m where m.dikirim > now() - interval '1 hour') >= 60 then
    raise exception 'Terlalu banyak kiriman saat ini. Coba lagi satu jam lagi.';
  end if;
  insert into masukan_mahasiswa (jenis, isi, nama, email) values (p_jenis, v_isi, v_nama, v_email);
  return 'ok';
end;
$_$;

CREATE FUNCTION public.koordinator_aktif(p_jabatan text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from koordinator k where k.dosen_id = me() and k.jabatan = p_jabatan
                   and k.mulai <= current_date and (k.selesai is null or k.selesai >= current_date))
$$;

CREATE FUNCTION public.kp_atur_kuota(p_ts integer, p_dosen uuid, p_kuota integer) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not boleh_pengajuan('kp') then raise exception 'Kuota diatur koordinator KP atau admin.'; end if;
  if p_ts is null or p_ts < 2000 or p_ts > 2100 then raise exception 'TS tidak sah.'; end if;
  if p_kuota is not null and (p_kuota < 0 or p_kuota > 100) then raise exception 'Kuota 0 sampai 100.'; end if;
  delete from kp_kuota where ts = p_ts and dosen_id is not distinct from p_dosen;
  if p_kuota is not null then insert into kp_kuota (ts, dosen_id, kuota) values (p_ts, p_dosen, p_kuota); end if;
  return 'ok';
end;
$$;

CREATE FUNCTION public.kp_bakukan_instansi(p_id bigint, p_baru text, p_semua boolean DEFAULT false) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_baru text := regexp_replace(btrim(coalesce(p_baru, '')), '\s+', ' ', 'g'); v_lama text; n int := 0; r record;
begin
  if not boleh_pengajuan('kp') then raise exception 'Membakukan nama instansi khusus koordinator KP atau admin prodi.'; end if;
  if length(v_baru) < 2 or length(v_baru) > 300 then raise exception 'Nama instansi 2-300 karakter.'; end if;
  select data ->> 'instansi' into v_lama from pengajuan_mahasiswa where id = p_id and jenis = 'kp';
  if not found then raise exception 'Pengajuan KP tidak ditemukan.'; end if;
  for r in select id, data from pengajuan_mahasiswa
            where jenis = 'kp' and status <> 'draf'
              and (id = p_id or (coalesce(p_semua, false) and nama_instansi_kunci(data ->> 'instansi') = nama_instansi_kunci(v_lama)))
              and (data ->> 'instansi') is distinct from v_baru loop
    update pengajuan_mahasiswa
       set data = jsonb_set(case when r.data ? 'instansi_asli' then r.data
                                 else r.data || jsonb_build_object('instansi_asli', coalesce(r.data ->> 'instansi', '')) end,
                            '{instansi}', to_jsonb(v_baru)),
           diperbarui = now()
     where id = r.id;
    n := n + 1;
  end loop;
  return n;
end;
$$;

CREATE FUNCTION public.kp_beban(p_ts integer) RETURNS TABLE(dosen_id uuid, nama text, kuota integer, kuota_sendiri boolean, beban integer)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select d.id, d.nama,
         coalesce(k.kuota, b.kuota), k.kuota is not null,
         (select count(*)::int from pengajuan_mahasiswa p
           where p.jenis = 'kp' and p.pembimbing_id = d.id and p.status not in ('draf', 'ditolak')
             and ts_dari(kp_tanggal_acuan(p)) = p_ts)
    from pembimbing_pilihan() d
    left join kp_kuota k on k.ts = p_ts and k.dosen_id = d.id
    left join kp_kuota b on b.ts = p_ts and b.dosen_id is null
   where me() is not null
   order by d.nama
$$;

CREATE FUNCTION public.kp_instansi_keputusan_rapikan() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public'
    AS $$
begin
  new.nama := regexp_replace(btrim(new.nama), '\s+', ' ', 'g');
  new.kunci := nama_instansi_kunci(new.nama);
  new.oleh := coalesce(nullif(auth.jwt() ->> 'email', ''), new.oleh);
  new.diperbarui := now();
  return new;
end;
$$;

CREATE FUNCTION public.kp_pelaksanaan_mitra() RETURNS TABLE(kerjasama_id bigint, tahun integer, kp integer, magang integer)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select k.id, t.tahun,
         (count(*) filter (where coalesce(p.data ->> 'program', 'kp') <> 'magang'))::int,
         (count(*) filter (where p.data ->> 'program' = 'magang'))::int
    from lkps_kerjasama k
    join pengajuan_mahasiswa p on p.jenis = 'kp' and p.tahap = 'selesai' and p.status = 'disetujui'
                              and nama_instansi_kunci(p.data ->> 'instansi') = nama_instansi_kunci(k.mitra)
    cross join lateral (select coalesce(
        (regexp_match(coalesce(p.data_selesai ->> 'tanggal_mulai', ''), '^(\d{4})'))[1],
        (regexp_match(coalesce(p.data ->> 'rencana_mulai', ''), '^(\d{4})'))[1],
        to_char(p.dibuat, 'YYYY'))::int as tahun) t
   where me() is not null
   group by k.id, t.tahun
   order by k.id, t.tahun
$$;

CREATE FUNCTION public.kp_rekap_baris() RETURNS TABLE(id bigint, instansi text, program text, status text, tahap text, mulai text, dibuat timestamp with time zone, pembimbing_id uuid, jawaban text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select p.id, p.data ->> 'instansi', coalesce(nullif(p.data ->> 'program', ''), 'kp'), p.status, p.tahap,
         coalesce(nullif(p.data_selesai ->> 'tanggal_mulai', ''), nullif(p.data ->> 'tanggal_mulai', ''), nullif(p.data ->> 'rencana_mulai', '')),
         p.dibuat, p.pembimbing_id, nullif(p.data ->> 'jawaban_instansi', '')
    from pengajuan_mahasiswa p
   where p.jenis = 'kp' and p.status <> 'draf' and me() is not null
   order by p.id
$$;

CREATE TABLE public.pengajuan_mahasiswa (
    id bigint NOT NULL,
    jenis text NOT NULL,
    nim text NOT NULL,
    nama text NOT NULL,
    email text NOT NULL,
    pembimbing_id uuid,
    data jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text DEFAULT 'draf'::text NOT NULL,
    token_hash text NOT NULL,
    tautan_dikirim timestamp with time zone DEFAULT now() NOT NULL,
    prestasi_id bigint,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    tahap text DEFAULT 'pengajuan'::text NOT NULL,
    data_selesai jsonb DEFAULT '{}'::jsonb NOT NULL,
    luaran_id bigint,
    pemeriksa_dikabari text,
    pemeriksa_antre timestamp with time zone,
    kabar_id bigint,
    CONSTRAINT pengajuan_mahasiswa_data_check CHECK (((jsonb_typeof(data) = 'object'::text) AND (length((data)::text) <= 8000))),
    CONSTRAINT pengajuan_mahasiswa_email_check CHECK ((email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text)),
    CONSTRAINT pengajuan_mahasiswa_jenis_check CHECK ((jenis = ANY (ARRAY['kp'::text, 'lomba'::text, 'surat'::text, 'ta'::text, 'luaran'::text, 'yudisium'::text, 'kabar'::text]))),
    CONSTRAINT pengajuan_mahasiswa_nama_check CHECK (((length(btrim(nama)) >= 2) AND (length(btrim(nama)) <= 120))),
    CONSTRAINT pengajuan_mahasiswa_nim_check CHECK ((nim ~ '^[0-9]{6,15}$'::text)),
    CONSTRAINT pengajuan_mahasiswa_status_check CHECK ((status = ANY (ARRAY['draf'::text, 'pembimbing'::text, 'admin'::text, 'disetujui'::text, 'dikembalikan'::text, 'ditolak'::text, 'dibatalkan'::text]))),
    CONSTRAINT pengajuan_mahasiswa_tahap_check CHECK (((tahap = ANY (ARRAY['pengajuan'::text, 'selesai'::text])) AND ((tahap = 'pengajuan'::text) OR (jenis = 'kp'::text)) AND (jsonb_typeof(data_selesai) = 'object'::text) AND (length((data_selesai)::text) <= 8000)))
);

CREATE FUNCTION public.kp_tanggal_acuan(p public.pengajuan_mahasiswa) RETURNS date
    LANGUAGE sql STABLE
    SET search_path TO 'public'
    AS $_$
  select coalesce(
    case when coalesce(p.data_selesai ->> 'tanggal_mulai', '') ~ '^\d{4}-\d{2}-\d{2}$' then (p.data_selesai ->> 'tanggal_mulai')::date end,
    case when coalesce(p.data ->> 'tanggal_mulai', '') ~ '^\d{4}-\d{2}-\d{2}$' then (p.data ->> 'tanggal_mulai')::date end,
    case when coalesce(p.data ->> 'rencana_mulai', '') ~ '^\d{4}-\d{2}-\d{2}$' then (p.data ->> 'rencana_mulai')::date end,
    (p.dibuat at time zone 'Asia/Jakarta')::date)
$_$;

CREATE FUNCTION public.kp_tetapkan_pembimbing(p_id bigint, p_dosen uuid) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_lama text; v_baru text; v_oleh text;
begin
  if not boleh_pengajuan('kp') then raise exception 'Pembimbing KP ditetapkan koordinator KP atau admin.'; end if;
  select * into p from pengajuan_mahasiswa where id = p_id for update;
  if p.id is null or p.jenis <> 'kp' then raise exception 'Pengajuan KP tidak ditemukan.'; end if;
  if p.status in ('draf', 'ditolak') or (p.tahap = 'selesai' and p.status = 'disetujui') then
    raise exception 'Pembimbing hanya bisa ditetapkan pada KP yang sedang diproses.'; end if;
  if not exists (select 1 from pembimbing_pilihan() x where x.id = p_dosen) then raise exception 'Pilih dosen dari daftar.'; end if;
  if p.pembimbing_id = p_dosen then return 'tetap'; end if;
  select nama into v_lama from dosen where id = p.pembimbing_id;
  select nama into v_baru from dosen where id = p_dosen;
  select nama into v_oleh from dosen where id = me();
  update pengajuan_mahasiswa set pembimbing_id = p_dosen, diperbarui = now() where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, p.status, coalesce(v_oleh, 'prodi') || ' (koordinator/admin)',
          'Dosen pembimbing ditetapkan: ' || v_baru || coalesce(' (sebelumnya ' || v_lama || ')', ''), p.tahap);
  return 'diganti';
end;
$$;

CREATE FUNCTION public.kp_tolak_boleh(p_pengajuan bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select boleh_pengajuan('kp') or exists (select 1 from pengajuan_mahasiswa p where p.id = p_pengajuan and p.pembimbing_id = me())
$$;

CREATE FUNCTION public.kp_tolak_rekap() RETURNS TABLE(instansi text, n integer, terakhir timestamp with time zone)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select min(t.instansi), count(*)::int, max(t.dibuat)
    from kp_tolak_instansi t
   where me() is not null
   group by nama_instansi_kunci(t.instansi)
   order by count(*) desc, min(t.instansi)
$$;

CREATE FUNCTION public.kunjungan_publik_rekap(p_hari integer DEFAULT 90) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_dari date := (now() at time zone 'Asia/Jakarta')::date - greatest(1, least(coalesce(p_hari, 90), 400));
begin
  if not is_admin() then raise exception 'Rekap kunjungan hanya untuk admin.'; end if;
  return jsonb_build_object('dari', v_dari, 'mulai_catat', (select min(tanggal) from kunjungan_publik),
    'baris', (select coalesce(jsonb_agg(jsonb_build_object('t', tanggal, 'h', halaman, 'r', rujukan, 'p', peristiwa, 'n', n)
                                         order by tanggal, halaman), '[]'::jsonb)
                from kunjungan_publik where tanggal >= v_dari));
end $$;

CREATE FUNCTION public.lihat_semua_hibah() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.dosen d
    where lower(d.email) = public.email_saya()
      and d.aktif and d.peran in ('admin', 'pimpinan'))
$$;

CREATE FUNCTION public.masa_kuliah_tanggal(p_t date, p_ta text, p_sm text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select not exists (select 1 from hari_libur h where h.tanggal = p_t)
     and case when exists (select 1 from kalender_akademik k where k.kategori = 'perkuliahan'
                            and lower(regexp_replace(btrim(k.semester), '\s+', ' ', 'g')) = lower(p_sm || ' ' || p_ta))
              then exists (select 1 from kalender_akademik k where k.kategori = 'perkuliahan'
                            and lower(regexp_replace(btrim(k.semester), '\s+', ' ', 'g')) = lower(p_sm || ' ' || p_ta)
                            and p_t between k.mulai and coalesce(k.selesai, k.mulai))
              else true end
$$;

CREATE FUNCTION public.masukkan_pustaka(p_url text, p_jenis text, p_tahun integer, p_judul text, p_sha256 text, p_nama text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  d bigint; ada boolean := false; u text;
begin
  if not public.is_admin() then raise exception 'Hanya admin.'; end if;
  p_judul := coalesce(trim(p_judul), '');
  if p_sha256 is not null and p_sha256 !~ '^[0-9a-f]{64}$' then p_sha256 := null; end if;

  if p_sha256 is not null then
    select id into d from public.dokumen where sha256 = p_sha256 order by id limit 1;
    ada := d is not null;
  end if;
  if d is null then
    select id, url into d, u from public.dokumen where jenis = p_jenis and tahun = p_tahun and judul = p_judul;
    if d is not null and u <> p_url then
      raise exception 'Pustaka sudah punya dokumen % % "%" dengan berkas lain; ganti judulnya.', p_jenis, p_tahun, p_judul;
    end if;
  end if;
  if d is null then
    insert into public.dokumen (jenis, tahun, judul, url, nama_berkas, sha256, diunggah_oleh)
    values (p_jenis, p_tahun, p_judul, p_url, nullif(p_nama, ''), p_sha256,
            (select email from public.dosen where id = public.me()))
    returning id into d;
  end if;

  delete from public.lkps_bukti a where a.url = p_url and exists (
    select 1 from public.lkps_bukti b where b.dokumen_id = d and b.tabel = a.tabel and b.baris_id = a.baris_id);
  update public.lkps_bukti set dokumen_id = d, url = null, sha256 = null where url = p_url;
  delete from public.butir_bukti a where a.url = p_url and exists (
    select 1 from public.butir_bukti b where b.dokumen_id = d and b.butir = a.butir);
  update public.butir_bukti set dokumen_id = d, url = null, sha256 = null where url = p_url;
  return jsonb_build_object('dokumen_id', d, 'sudah_ada', ada);
end $_$;

CREATE FUNCTION public.me() RETURNS uuid
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select d.id from public.dosen d
  where lower(d.email) = public.email_saya() and d.aktif limit 1
$$;

CREATE FUNCTION public.mengajar_kelas(p_ta text, p_sm text, p_kode text, p_kelas text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.me() is not null and exists (
    select 1 from public.kelas_kuliah k join public.kelas_dosen kd on kd.kelas_id = k.id and kd.dosen_id = public.me()
     where k.tahun_akademik = p_ta and k.semester = p_sm and upper(k.kode_mk) = upper(p_kode)
       and (p_kelas is null or k.kelas = p_kelas))
$$;

CREATE FUNCTION public.mengajar_mk(p_kurikulum text, p_kode text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.me() is not null and exists (
    select 1 from public.kelas_kuliah k join public.kelas_dosen kd on kd.kelas_id = k.id and kd.dosen_id = public.me()
     where k.kurikulum = p_kurikulum and k.kode_mk = p_kode
       and public.semester_urut(k.tahun_akademik, k.semester) >= public.semester_kini_urut())
$$;

CREATE FUNCTION public.mhs_batal(p_token text, p_alasan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_alasan text := left(btrim(coalesce(p_alasan, '')), 300);
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if p.status = 'dibatalkan' then return 'dibatalkan'; end if;
  if coalesce(p.tahap, 'pengajuan') <> 'pengajuan' or p.status not in ('draf', 'dikembalikan') then
    raise exception 'Pengajuan yang sedang diperiksa atau sudah diputuskan tidak bisa dibatalkan sendiri. Minta pemeriksa mengembalikannya dulu, atau hubungi admin prodi.'; end if;
  update pengajuan_mahasiswa set status = 'dibatalkan', diperbarui = now() where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, 'dibatalkan', 'mahasiswa', 'Dibatalkan mahasiswa' || case when v_alasan <> '' then ': ' || v_alasan else '' end || '.', 'pengajuan');
  return 'dibatalkan';
end;
$$;

CREATE FUNCTION public.mhs_berkas(p_kunci text, p_token text, p_berkas bigint, p_buang boolean DEFAULT false) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; b pengajuan_berkas;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  select * into b from pengajuan_berkas where id = p_berkas and pengajuan_id = p.id;
  if b.id is null then raise exception 'Berkas tidak ditemukan.'; end if;
  if p_buang then
    if not mhs_boleh(p) or b.oleh <> 'mahasiswa' or (p.status = 'disetujui' and b.jenis = 'surat_permohonan') then
      raise exception 'Berkas ini tidak bisa dibuang.'; end if;
    delete from pengajuan_berkas where id = b.id;
    if b.tautan then return ''; end if;
  elsif b.tautan then
    raise exception 'Berkas ini berupa tautan Google Drive; buka tautannya langsung.';
  end if;
  return b.url;
end;
$$;

CREATE FUNCTION public.mhs_bimbingan(p_token text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku. Minta tautan baru di halaman pengajuan.'; end if;
  if p.jenis <> 'ta' then raise exception 'Catatan bimbingan ada di pengajuan TA.'; end if;
  return jsonb_build_object(
    'hari_otomatis', 14,
    'pembimbing', (select coalesce(jsonb_agg(jsonb_build_object('id', x.id, 'nama', x.nama, 'ke', x.ke) order by x.ke), '[]'::jsonb)
                     from ta_pembimbing_nim(p.nim) x),
    'catatan', (select coalesce(jsonb_agg(jsonb_build_object('id', b.id, 'tanggal', b.tanggal, 'cara', b.cara, 'pembimbing_id', b.pembimbing_id,
                  'pembimbing', (select d.nama from dosen d where d.id = b.pembimbing_id), 'topik', b.topik, 'arahan', b.arahan,
                  'status', b.status, 'sah', ta_bimbingan_sah(b.status, b.diajukan), 'catatan_pembimbing', b.catatan_pembimbing,
                  'konfirmasi_oleh', b.konfirmasi_oleh, 'konfirmasi_pada', b.konfirmasi_pada, 'diajukan', b.diajukan,
                  'lampiran_nama', b.lampiran_nama, 'ada_lampiran', b.lampiran_url is not null, 'lampiran_dihapus', b.lampiran_dihapus)
                  order by b.tanggal desc, b.id desc), '[]'::jsonb)
                  from ta_bimbingan b where upper(btrim(b.nim)) = upper(btrim(p.nim))),
    'syarat', (select jsonb_agg(ta_syarat_bimbingan_hitung(p.nim, t.tahap) order by t.urut)
                 from (values ('seminar_proposal', 1), ('seminar_kemajuan', 2), ('sidang_akhir', 3)) t(tahap, urut)));
end;
$$;

CREATE FUNCTION public.mhs_bimbingan_hapus(p_token text, p_id bigint) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; b ta_bimbingan;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku. Minta tautan baru di halaman pengajuan.'; end if;
  select * into b from ta_bimbingan x where x.id = p_id and upper(btrim(x.nim)) = upper(btrim(p.nim)) for update;
  if b.id is null then raise exception 'Catatan bimbingan tidak ditemukan.'; end if;
  if ta_bimbingan_sah(b.status, b.diajukan) then raise exception 'Catatan yang sudah terkonfirmasi tidak bisa dihapus.'; end if;
  delete from ta_bimbingan where id = b.id;
  return 'dihapus';
end;
$$;

CREATE FUNCTION public.mhs_bimbingan_lampiran(p_kunci text, p_token text, p_id bigint, p_nama text, p_url text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare p pengajuan_mahasiswa; b ta_bimbingan;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku. Minta tautan baru di halaman pengajuan.'; end if;
  select * into b from ta_bimbingan x where x.id = p_id and upper(btrim(x.nim)) = upper(btrim(p.nim)) for update;
  if b.id is null then raise exception 'Catatan bimbingan tidak ditemukan.'; end if;
  if ta_bimbingan_sah(b.status, b.diajukan) then raise exception 'Catatan yang sudah terkonfirmasi tidak bisa diberi lampiran.'; end if;
  if coalesce(p_url, '') !~ '^https://(drive|docs)\.google\.com/\S+$' then raise exception 'Tautan lampiran tidak sah.'; end if;
  update ta_bimbingan set lampiran_nama = left(btrim(coalesce(p_nama, 'lampiran')), 200), lampiran_url = p_url, lampiran_dihapus = null,
         diperbarui = now()
   where id = b.id;
  return b.lampiran_url;
end;
$_$;

CREATE FUNCTION public.mhs_bimbingan_lampiran_url(p_kunci text, p_token text, p_id bigint) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_url text;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku. Minta tautan baru di halaman pengajuan.'; end if;
  select x.lampiran_url into v_url from ta_bimbingan x where x.id = p_id and upper(btrim(x.nim)) = upper(btrim(p.nim));
  if v_url is null then raise exception 'Lampiran tidak ada (atau sudah dihapus 30 hari setelah lulus).'; end if;
  return v_url;
end;
$$;

CREATE FUNCTION public.mhs_bimbingan_simpan(p_token text, p_id bigint, p_tanggal date, p_cara text, p_pembimbing uuid, p_topik text, p_arahan text) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; b ta_bimbingan; v_id bigint; v_topik text := btrim(coalesce(p_topik, '')); v_arahan text := btrim(coalesce(p_arahan, ''));
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku. Minta tautan baru di halaman pengajuan.'; end if;
  if p.jenis <> 'ta' then raise exception 'Catatan bimbingan ada di pengajuan TA.'; end if;
  if not exists (select 1 from ta_pembimbing_nim(p.nim)) then
    raise exception 'Pembimbing TA Anda belum tercatat; ajukan pembimbing TA dulu.'; end if;
  if p_pembimbing is null or not exists (select 1 from ta_pembimbing_nim(p.nim) x where x.id = p_pembimbing) then
    raise exception 'Pilih pembimbing yang membimbing.'; end if;
  if p_tanggal is null or p_tanggal > (now() at time zone 'Asia/Jakarta')::date then
    raise exception 'Isi tanggal bimbingan (tidak boleh setelah hari ini).'; end if;
  if p_tanggal < date '2020-01-01' then raise exception 'Tanggal bimbingan terlalu lama.'; end if;
  if p_cara is null or p_cara not in ('tatap_muka', 'daring') then raise exception 'Pilih cara bimbingan: tatap muka atau daring.'; end if;
  if length(v_topik) not between 5 and 1000 then raise exception 'Tulis topik yang dibahas (5–1000 huruf).'; end if;
  if length(v_arahan) > 2000 then raise exception 'Arahan paling banyak 2000 huruf.'; end if;
  if p_id is null then
    if (select count(*) from ta_bimbingan x where upper(btrim(x.nim)) = upper(btrim(p.nim))) >= 300 then
      raise exception 'Paling banyak 300 catatan bimbingan per mahasiswa.'; end if;
    insert into ta_bimbingan (nim, nama, tanggal, cara, pembimbing_id, topik, arahan)
    values (upper(btrim(p.nim)), p.nama, p_tanggal, p_cara, p_pembimbing, v_topik, v_arahan) returning id into v_id;
    return v_id;
  end if;
  select * into b from ta_bimbingan x where x.id = p_id and upper(btrim(x.nim)) = upper(btrim(p.nim)) for update;
  if b.id is null then raise exception 'Catatan bimbingan tidak ditemukan.'; end if;
  if ta_bimbingan_sah(b.status, b.diajukan) then raise exception 'Catatan yang sudah terkonfirmasi tidak bisa diubah.'; end if;
  update ta_bimbingan set tanggal = p_tanggal, cara = p_cara, pembimbing_id = p_pembimbing, topik = v_topik, arahan = v_arahan,
         status = 'menunggu', diajukan = now(), diperbarui = now()
   where id = b.id;
  return b.id;
end;
$$;

CREATE FUNCTION public.mhs_boleh(p public.pengajuan_mahasiswa) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    SET search_path TO 'public'
    AS $$
  select p.status in ('draf', 'dikembalikan') or (p.jenis = 'kp' and p.tahap = 'pengajuan' and p.status = 'disetujui')
$$;

CREATE FUNCTION public.mhs_buat(p_kunci text, p_jenis text, p_nim text, p_nama text, p_email text, p_pembimbing uuid, p_data jsonb) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_token text := mhs_token_baru(); v_id bigint; tanpa boolean := p_jenis in ('surat', 'yudisium');
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  if p_jenis not in ('kp', 'lomba', 'surat', 'ta', 'luaran', 'yudisium', 'kabar') then raise exception 'Jenis pengajuan tidak dikenal.'; end if;
  if not tanpa and not (p_jenis = 'kabar' and p_pembimbing is null)
     and not exists (select 1 from pembimbing_pilihan() x where x.id = p_pembimbing) then
    raise exception 'Pilih dosen pembimbing dari daftar.'; end if;
  if (select count(*) from pengajuan_mahasiswa where nim = btrim(p_nim) and dibuat > now() - interval '24 hours') >= 5 then
    raise exception 'NIM ini sudah membuat 5 pengajuan dalam 24 jam. Gunakan tautan di email kampus Anda.'; end if;
  if p_jenis = 'kp' and exists (select 1 from pengajuan_mahasiswa where nim = btrim(p_nim) and jenis = 'kp'
       and status not in ('ditolak', 'dibatalkan') and not (tahap = 'selesai' and status = 'disetujui')) then
    raise exception 'NIM ini masih punya KP yang dalam proses; satu mahasiswa hanya satu KP aktif. Bila surat pengantar ditolak instansi, buka tautan pengajuan itu dan laporkan di "Jawaban instansi" (ditolak); sesudah itu pengajuan baru bisa dibuat. Tautan hilang? Minta tautan baru.'; end if;
  if p_jenis = 'yudisium' and exists (select 1 from pengajuan_mahasiswa where nim = btrim(p_nim) and jenis = 'yudisium' and status not in ('ditolak', 'dibatalkan')) then
    raise exception 'NIM ini sudah punya pengajuan berkas yudisium. Buka tautannya dari email kampus; tautan hilang? Minta tautan baru.'; end if;
  if (select count(*) from pengajuan_mahasiswa where dibuat > now() - interval '1 hour') >= 60 then
    raise exception 'Terlalu banyak pengajuan saat ini. Coba lagi satu jam lagi.'; end if;
  insert into pengajuan_mahasiswa (jenis, nim, nama, email, pembimbing_id, data, token_hash)
  values (p_jenis, btrim(p_nim), btrim(p_nama), lower(btrim(p_email)), case when tanpa then null else p_pembimbing end,
          mhs_rapikan(p_jenis, p_data), encode(extensions.digest(v_token, 'sha256'), 'hex'))
  returning id into v_id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh) values (v_id, 'draf', 'mahasiswa');
  return v_token;
end;
$$;

CREATE FUNCTION public.mhs_cari(p_token text) RETURNS public.pengajuan_mahasiswa
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select p.* from pengajuan_mahasiswa p
   where length(coalesce(p_token, '')) >= 32
     and p.token_hash = encode(extensions.digest(p_token, 'sha256'), 'hex')
$$;

CREATE FUNCTION public.mhs_catat_berkas(p_kunci text, p_token text, p_jenis text, p_nama text, p_url text) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_id bigint; v_maks int;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if not mhs_boleh(p) then raise exception 'Pengajuan sedang diperiksa; berkas tidak bisa diubah.'; end if;
  if p_jenis in ('surat_pengantar', 'surat_jadi') then raise exception 'Surat dari prodi diunggah admin.'; end if;
  if p_jenis = 'nilai_lapangan' then
    raise exception 'Nilai pembimbing lapangan diunggah dosen pembimbing, koordinator KP, atau admin prodi.'; end if;
  if not mhs_jenis_berkas_sah(p, p_jenis) then raise exception 'Jenis berkas tidak dikenal untuk pengajuan ini.'; end if;
  if p.status = 'disetujui' and p_jenis = 'surat_permohonan' then raise exception 'Surat permohonan sudah diperiksa.'; end if;
  v_maks := case when p.jenis = 'yudisium' then 40 else 20 end;
  if (select count(*) from pengajuan_berkas where pengajuan_id = p.id) >= v_maks then
    raise exception 'Paling banyak % berkas per pengajuan.', v_maks; end if;
  insert into pengajuan_berkas (pengajuan_id, jenis, nama, url) values (p.id, p_jenis, left(coalesce(p_nama, ''), 200), p_url)
  returning id into v_id;
  update pengajuan_mahasiswa set diperbarui = now() where id = p.id;
  return v_id;
end;
$$;

CREATE FUNCTION public.mhs_cek(p_kunci text, p_token text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku. Minta tautan baru di halaman pengajuan.'; end if;
  return jsonb_build_object('id', p.id, 'jenis', p.jenis, 'nim', p.nim, 'nama', p.nama, 'status', p.status, 'tahap', p.tahap,
    'tahun', extract(year from p.dibuat)::int, 'boleh_ubah', mhs_boleh(p),
    'berkas', (select count(*) from pengajuan_berkas b where b.pengajuan_id = p.id));
end;
$$;

CREATE FUNCTION public.mhs_email_alt_jejak() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if tg_op = 'DELETE' then
    if old.email is not null then
      insert into mhs_email_alt_riwayat (nim, email, aksi, oleh)
      values (old.nim, old.email, 'dicabut', coalesce(nullif(auth.jwt() ->> 'email', ''), 'sistem'));
    end if;
    return old;
  end if;
  if new.email is distinct from (case when tg_op = 'UPDATE' then old.email end) then
    insert into mhs_email_alt_riwayat (nim, email, aksi, oleh)
    values (new.nim, coalesce(new.email, case when tg_op = 'UPDATE' then old.email end),
            case when new.email is null then 'dicabut' else 'aktif' end, new.oleh);
  end if;
  return new;
end;
$$;

CREATE FUNCTION public.mhs_email_alt_konfirmasi(p_kunci text, p_token text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r mhs_email_alt;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  select * into r from mhs_email_alt
   where calon_hash = encode(extensions.digest(btrim(coalesce(p_token, '')), 'sha256'), 'hex') for update;
  if r.nim is null or r.calon is null then raise exception 'Tautan konfirmasi tidak berlaku. Minta lagi di halaman pengajuan.'; end if;
  if r.calon_dikirim < now() - interval '2 days' then
    raise exception 'Tautan konfirmasi sudah kedaluwarsa (2 hari). Minta lagi di halaman pengajuan.'; end if;
  update mhs_email_alt set email = calon, calon = null, calon_hash = null, calon_dikirim = null,
         oleh = 'mahasiswa (konfirmasi email kampus)'
   where nim = r.nim;
  return jsonb_build_object('nim', r.nim, 'email', r.calon);
end;
$$;

CREATE FUNCTION public.mhs_email_alt_minta(p_kunci text, p_nim text, p_email text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare v_nim text := btrim(coalesce(p_nim, '')); v_email text := lower(btrim(coalesce(p_email, ''))); t text; r mhs_email_alt;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  if v_nim !~ '^[0-9]{6,15}$' then raise exception 'NIM harus angka 6-15 digit.'; end if;
  if v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' or length(v_email) > 120 then raise exception 'Alamat email alternatif tidak sah.'; end if;
  select * into r from mhs_email_alt where nim = v_nim;
  if r.calon_dikirim > now() - interval '10 minutes' then
    raise exception 'Tautan konfirmasi baru saja dikirim. Periksa email kampus Anda atau coba lagi 10 menit lagi.'; end if;
  if r.email = v_email then raise exception 'Email itu sudah menjadi email alternatif Anda.'; end if;
  t := mhs_token_baru();
  insert into mhs_email_alt (nim, calon, calon_hash, calon_dikirim, oleh)
  values (v_nim, v_email, encode(extensions.digest(t, 'sha256'), 'hex'), now(), 'mahasiswa')
  on conflict (nim) do update set calon = excluded.calon, calon_hash = excluded.calon_hash,
    calon_dikirim = excluded.calon_dikirim;
  insert into mhs_email_alt_riwayat (nim, email, aksi, oleh) values (v_nim, v_email, 'diminta', 'mahasiswa');
  return t;
end;
$_$;

CREATE FUNCTION public.mhs_email_alt_rapikan() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_oleh text := nullif(auth.jwt() ->> 'email', '');
begin
  new.email := nullif(lower(btrim(coalesce(new.email, ''))), '');
  new.calon := nullif(lower(btrim(coalesce(new.calon, ''))), '');
  if v_oleh is not null then
    new.oleh := v_oleh;
    if new.email is not null then new.calon := null; new.calon_hash := null; new.calon_dikirim := null; end if;
  end if;
  new.diperbarui := now();
  return new;
end;
$$;

CREATE FUNCTION public.mhs_email_alt_tujuan(p_kunci text, p_nim text) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  return (select email from mhs_email_alt where nim = btrim(coalesce(p_nim, '')));
end;
$$;

CREATE FUNCTION public.mhs_jendela_selesai(p public.pengajuan_mahasiswa) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    SET search_path TO 'public'
    AS $$
  select coalesce(p.jenis = 'kp' and ((p.tahap = 'pengajuan' and p.status = 'disetujui') or (p.tahap = 'selesai' and p.status = 'dikembalikan')
    or (p.tahap = 'pengajuan' and p.status in ('draf', 'dikembalikan') and coalesce(p.data ->> 'susulan', '') = 'selesai')), false)
$$;

CREATE FUNCTION public.mhs_jenis_berkas_sah(p public.pengajuan_mahasiswa, p_jenis text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when p.jenis = 'yudisium' then exists (select 1 from yudisium_berkas y where y.kode = p_jenis and y.aktif)
              when p_jenis ~ '^ta_' then p.jenis = 'ta' and exists (select 1 from ta_berkas t where t.kode = p_jenis and t.aktif)
              else p_jenis !~ '^yud_' end
$$;

CREATE FUNCTION public.mhs_judul(p_jenis text, p_data jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE
    SET search_path TO 'public'
    AS $$
  select case p_jenis
    when 'kp' then coalesce(nullif(p_data ->> 'instansi', ''), 'KP')
    when 'lomba' then coalesce(nullif(p_data ->> 'nama_kegiatan', ''), 'Lomba')
    when 'ta' then coalesce(nullif(p_data ->> 'judul', ''), 'Tugas Akhir')
    when 'luaran' then coalesce(nullif(p_data ->> 'judul', ''), 'Publikasi/luaran')
    when 'yudisium' then 'Berkas yudisium'
    when 'kabar' then coalesce(nullif(p_data ->> 'judul', ''), 'Kabar kegiatan')
    else case p_data ->> 'jenis_surat' when 'aktif_kuliah' then 'Surat keterangan aktif kuliah'
           when 'izin_penelitian' then 'Surat izin penelitian' when 'rekomendasi' then 'Surat rekomendasi' else 'Surat' end
  end
$$;

CREATE FUNCTION public.mhs_kirim(p_token text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; wajib text := ''; v_ke text := 'pembimbing'; v_tetap pengajuan_mahasiswa; v_kurang text;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if p.tahap <> 'pengajuan' or p.status not in ('draf', 'dikembalikan') then raise exception 'Pengajuan sudah dikirim.'; end if;
  if p.jenis = 'kp' then
    if coalesce(p.data ->> 'instansi', '') = '' then raise exception 'Isi nama instansi tujuan KP.'; end if;
    if p.data ->> 'susulan' = 'selesai' then
      raise exception 'KP yang sudah selesai dikirim dengan tombol Kirim laporan selesai.'; end if;
    -- 107: langsung ke koordinator KP/admin; surat permohonan, atau surat balasan bila sudah diterima instansi.
    if not exists (select 1 from pengajuan_berkas where pengajuan_id = p.id and jenis in ('surat_permohonan', 'surat_balasan')) then
      raise exception 'Unggah surat permohonan KP dulu (atau surat balasan instansi bila Anda sudah diterima).'; end if;
    v_ke := 'admin';
  elsif p.jenis = 'lomba' then
    if coalesce(p.data ->> 'nama_kegiatan', '') = '' or coalesce(p.data ->> 'tingkat', '') = ''
       or coalesce(p.data ->> 'bidang', '') = '' or coalesce(p.data ->> 'tanggal', '') = '' then
      raise exception 'Lengkapi nama kegiatan, tingkat, bidang, dan tanggal lomba.'; end if;
    wajib := 'laporan_lomba';
  elsif p.jenis = 'ta' and p.data ->> 'tahap_ta' = 'penetapan_pembimbing' then
    -- 110: sekali di awal; langsung ke koordinator TA/admin. Pembimbing 1 harus KK sama atau berdekatan.
    if coalesce(p.data ->> 'kk_ta', '') = '' or length(coalesce(p.data ->> 'judul', '')) < 3 then
      raise exception 'Pilih kelompok keahlian TA dan tulis judul awal.'; end if;
    if not ta_kk_cocok(p.data ->> 'kk_ta', (select d.kelompok_keahlian from dosen d where d.id = p.pembimbing_id)) then
      raise exception 'Pembimbing 1 harus dari kelompok keahlian TA Anda atau yang berdekatan; pilih dari daftar.'; end if;
    if exists (select 1 from pengajuan_mahasiswa o where o.nim = p.nim and o.id <> p.id and o.jenis = 'ta'
                 and o.data ->> 'tahap_ta' = 'penetapan_pembimbing' and o.status in ('pembimbing', 'admin')) then
      raise exception 'Masih ada pengajuan pembimbing TA Anda yang sedang diperiksa koordinator TA.'; end if;
    v_ke := 'admin';
  elsif p.jenis = 'ta' then
    if coalesce(p.data ->> 'tahap_ta', '') = '' or length(coalesce(p.data ->> 'judul', '')) < 3 then
      raise exception 'Pilih tahap TA dan tulis judulnya.'; end if;
    wajib := 'naskah_ta';
    -- 110: bila pembimbing TA sudah ditetapkan koordinator, seminar/sidang memakai pembimbing itu.
    select * into v_tetap from pengajuan_mahasiswa o where o.nim = p.nim and o.jenis = 'ta'
       and o.data ->> 'tahap_ta' = 'penetapan_pembimbing' and o.status = 'disetujui' order by o.diperbarui desc, o.id desc limit 1;
    if v_tetap.id is not null then
      update pengajuan_mahasiswa set pembimbing_id = v_tetap.pembimbing_id,
             data = (data - 'pembimbing_2') || jsonb_strip_nulls(jsonb_build_object('pembimbing_2', nullif(v_tetap.data ->> 'pembimbing_2', '')))
       where id = p.id;
    end if;
  elsif p.jenis = 'luaran' then
    if coalesce(p.data ->> 'kategori', '') = '' or length(coalesce(p.data ->> 'judul', '')) < 3 or coalesce(p.data ->> 'tahun', '') = '' then
      raise exception 'Pilih kategori, tulis judul, dan isi tahun.'; end if;
    if p.data ->> 'kategori' = 'publikasi' and coalesce(p.data ->> 'jenis_pub', '') = '' then raise exception 'Pilih jenis publikasi.'; end if;
    if p.data ->> 'kategori' = 'luaran' and coalesce(p.data ->> 'jenis_luaran', '') = '' then raise exception 'Pilih jenis luaran.'; end if;
    wajib := 'bukti_luaran';
  elsif p.jenis = 'yudisium' then
    -- 122: semua berkas wajib (yudisium_berkas aktif) ada, diunggah atau tautan; langsung ke admin prodi.
    select string_agg(y.label, ', ' order by y.urut, y.kode) into v_kurang
      from yudisium_berkas y
     where y.aktif and y.wajib and not exists (select 1 from pengajuan_berkas b where b.pengajuan_id = p.id and b.jenis = y.kode);
    if v_kurang is not null then raise exception 'Berkas wajib belum lengkap: %.', v_kurang; end if;
    v_ke := 'admin';
  elsif p.jenis = 'kabar' then
    -- 144: batas bawah = kabar_kegiatan (judul >= 3, ringkasan >= 20 huruf); satu persetujuan di tahap 'pembimbing'.
    if length(coalesce(p.data ->> 'judul', '')) < 3 or coalesce(p.data ->> 'tanggal', '') = ''
       or length(coalesce(p.data ->> 'ringkasan', '')) < 20 then
      raise exception 'Lengkapi judul, tanggal kegiatan, dan ringkasan (minimal 20 huruf).'; end if;
    wajib := 'foto';
  else
    if coalesce(p.data ->> 'jenis_surat', '') = '' or length(coalesce(p.data ->> 'keperluan', '')) < 5 then
      raise exception 'Pilih jenis surat dan tulis keperluannya.'; end if;
    if p.data ->> 'jenis_surat' in ('izin_penelitian', 'rekomendasi') and coalesce(p.data ->> 'tujuan_surat', '') = '' then
      raise exception 'Tulis tujuan surat (kepada siapa).'; end if;
    if p.data ->> 'jenis_surat' = 'izin_penelitian' and coalesce(p.data ->> 'judul_penelitian', '') = '' then
      raise exception 'Tulis judul penelitian.'; end if;
    v_ke := 'admin';
  end if;
  if wajib <> '' and not exists (select 1 from pengajuan_berkas where pengajuan_id = p.id and jenis = wajib) then
    raise exception 'Unggah berkas wajib dulu: %.', case wajib when 'naskah_ta' then 'naskah TA' when 'bukti_luaran' then 'bukti publikasi/luaran'
                                                    when 'foto' then 'foto kegiatan'
                                                    else replace(wajib, '_', ' ') end; end if;
  update pengajuan_mahasiswa set status = v_ke, diperbarui = now() where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, tahap) values (p.id, v_ke, 'mahasiswa', 'pengajuan');
  return v_ke;
end;
$$;

CREATE FUNCTION public.mhs_kirim_selesai(p_token text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; d jsonb; j text;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if not mhs_jendela_selesai(p) then raise exception 'Laporan selesai KP sudah dikirim atau belum bisa dikirim.'; end if;
  if p.tahap = 'pengajuan' and (coalesce(p.data ->> 'instansi', '') = '' or p.pembimbing_id is null) then
    raise exception 'Isi nama instansi dan pilih dosen pembimbing KP.'; end if;
  d := p.data_selesai;
  if coalesce(d ->> 'tanggal_mulai', '') = '' or coalesce(d ->> 'tanggal_selesai', '') = ''
     or coalesce(d ->> 'pembimbing_lapangan', '') = '' or length(coalesce(d ->> 'ringkasan', '')) < 30 then
    raise exception 'Lengkapi tanggal mulai dan selesai, pembimbing lapangan, dan ringkasan kegiatan (minimal 30 huruf).'; end if;
  foreach j in array array['laporan_kp', 'surat_selesai'] loop
    if not exists (select 1 from pengajuan_berkas where pengajuan_id = p.id and jenis = j) then
      raise exception 'Unggah berkas wajib dulu: %.', case j when 'laporan_kp' then 'laporan KP' else 'surat keterangan selesai' end; end if;
  end loop;
  update pengajuan_mahasiswa set tahap = 'selesai', status = 'pembimbing', diperbarui = now() where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, tahap) values (p.id, 'pembimbing', 'mahasiswa', 'selesai');
  return 'pembimbing';
end;
$$;

CREATE FUNCTION public.mhs_kunci_sah(p_kunci text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce(length(p_kunci) >= 32 and p_kunci = (select kunci from layanan_kunci where id = 1), false)
$$;

CREATE FUNCTION public.mhs_kunci_tahap(p public.pengajuan_mahasiswa) RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce(p.tahap, 'pengajuan') || ':' || p.status || ':'
    || coalesce((select max(r.id) from pengajuan_riwayat r where r.pengajuan_id = p.id and r.status = p.status)::text, '0')
$$;

CREATE FUNCTION public.mhs_lihat(p_token text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku. Minta tautan baru di halaman pengajuan.'; end if;
  return jsonb_build_object(
    'id', p.id, 'jenis', p.jenis, 'nim', p.nim, 'nama', p.nama, 'email', p.email, 'status', p.status, 'tahap', p.tahap,
    'data', p.data, 'data_selesai', p.data_selesai, 'boleh_ubah', mhs_boleh(p), 'jendela_selesai', mhs_jendela_selesai(p),
    'pembimbing_id', p.pembimbing_id, 'pembimbing', (select d.nama from dosen d where d.id = p.pembimbing_id),
    'pembimbing_2', (select d.nama from dosen d where d.id::text = p.data ->> 'pembimbing_2'),
    'dibuat', p.dibuat, 'diperbarui', p.diperbarui,
    -- 110: pembimbing TA yang sudah ditetapkan koordinator (dipakai seminar/sidang).
    'penetapan_ta', (select jsonb_build_object('id', o.id, 'kk_ta', o.data ->> 'kk_ta', 'judul', o.data ->> 'judul',
                       'pembimbing', (select d.nama from dosen d where d.id = o.pembimbing_id),
                       'pembimbing_2', (select d.nama from dosen d where d.id::text = o.data ->> 'pembimbing_2'), 'waktu', o.diperbarui)
                       from pengajuan_mahasiswa o where o.nim = p.nim and o.jenis = 'ta' and o.data ->> 'tahap_ta' = 'penetapan_pembimbing'
                        and o.status = 'disetujui' order by o.diperbarui desc, o.id desc limit 1),
    'jadwal', (select jsonb_build_object('tanggal', j.tanggal, 'jam', j.jam, 'ruang', j.ruang, 'tautan_daring', j.tautan_daring,
                 'status', j.status, 'penguji', (select coalesce(jsonb_agg(d.nama order by d.nama), '[]'::jsonb) from dosen d where d.nidn = any(j.penguji)),
                 'penguji_luar', j.penguji_luar, 'hasil', j.hasil, 'batas_revisi', j.batas_revisi, 'catatan_revisi', j.catatan_revisi,
                 'revisi_selesai', j.revisi_selesai)
                 from jadwal_ta j where j.pengajuan_id = p.id),
    'berkas', (select coalesce(jsonb_agg(jsonb_build_object('id', b.id, 'jenis', b.jenis, 'nama', b.nama,
                 'oleh', case when b.oleh = 'mahasiswa' then 'mahasiswa' else 'prodi' end, 'dibuat', b.dibuat, 'tautan', b.tautan)
                 || case when b.tautan then jsonb_build_object('url', b.url) else '{}'::jsonb end order by b.id), '[]'::jsonb)
                 from pengajuan_berkas b where b.pengajuan_id = p.id),
    'riwayat', (select coalesce(jsonb_agg(jsonb_build_object('status', r.status, 'tahap', r.tahap, 'oleh', r.oleh,
                 'catatan', r.catatan, 'waktu', r.waktu) order by r.waktu, r.id), '[]'::jsonb)
                 from pengajuan_riwayat r where r.pengajuan_id = p.id),
    'lain', (select coalesce(jsonb_agg(jsonb_build_object('id', o.id, 'jenis', o.jenis, 'status', o.status, 'tahap', o.tahap,
                 'judul', mhs_judul(o.jenis, o.data), 'dibuat', o.dibuat, 'diperbarui', o.diperbarui) order by o.dibuat desc), '[]'::jsonb)
                 from pengajuan_mahasiswa o where o.nim = p.nim and o.id <> p.id));
end;
$$;

CREATE FUNCTION public.mhs_pemeriksa(p_kunci text, p_id bigint, p_jam1 integer DEFAULT 60, p_jam24 integer DEFAULT 1440) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  p pengajuan_mahasiswa; v_jab text; v_penerima jsonb; v_tingkat int; v_masuk timestamptz;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  select * into p from pengajuan_mahasiswa where id = p_id;
  if p.id is null then raise exception 'Pengajuan tidak ditemukan.'; end if;
  v_tingkat := mhs_tingkat_tempo(p, p_jam1, p_jam24);
  if v_tingkat = 0 then return jsonb_build_object('perlu', false); end if;
  v_masuk := mhs_waktu_tahap(p);

  v_jab := case p.jenis when 'kp' then 'koordinator_kp' when 'ta' then 'koordinator_ta'
                        when 'lomba' then 'pembina_kemahasiswaan' when 'luaran' then 'pembina_kemahasiswaan'
                        when 'kabar' then 'pembina_kemahasiswaan' end;
  with aktif as (
    select d.nama, d.email, d.terakhir_aktif from koordinator k join dosen d on d.id = k.dosen_id
     where k.jabatan = v_jab and k.mulai <= current_date and (k.selesai is null or k.selesai >= current_date)
  ), calon as (
    select d.nama, d.email, d.terakhir_aktif from dosen d where p.status = 'pembimbing' and d.id = p.pembimbing_id
    union
    select a.nama, a.email, a.terakhir_aktif from aktif a where p.status = 'pembimbing' and p.jenis in ('lomba', 'kabar')
    union
    select d.nama, d.email, d.terakhir_aktif from dosen d where p.status = 'pembimbing' and p.jenis = 'kabar' and p.pembimbing_id is null
       and d.peran = 'admin' and not exists (select 1 from aktif)
    union
    select a.nama, a.email, a.terakhir_aktif from aktif a where p.status = 'admin'
    union
    select d.nama, d.email, d.terakhir_aktif from dosen d where p.status = 'admin' and d.peran = 'admin' and not exists (select 1 from aktif)
  )
  select coalesce(jsonb_agg(distinct jsonb_build_object('nama', c.nama, 'email', lower(c.email))), '[]'::jsonb) into v_penerima
    from calon c
   where coalesce(c.email, '') like '%@%'
     -- kabar 1 jam: hanya yang belum membuka ruang kerja sejak pengajuan masuk tahap ini
     and (v_tingkat = 24 or c.terakhir_aktif is null or c.terakhir_aktif < v_masuk);

  return jsonb_build_object('perlu', true, 'tingkat', v_tingkat, 'kunci_tahap', mhs_kunci_tahap(p), 'masuk', v_masuk,
    'id', p.id, 'jenis', p.jenis, 'tahap', coalesce(p.tahap, 'pengajuan'), 'status', p.status, 'nim', p.nim, 'nama', p.nama,
    'judul', mhs_judul(p.jenis, p.data), 'penerima', v_penerima);
end;
$$;

CREATE FUNCTION public.mhs_pemeriksa_antrean(p_kunci text, p_jam1 integer DEFAULT 60, p_jam24 integer DEFAULT 1440) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  return (select coalesce(jsonb_agg(q.id order by q.id), '[]'::jsonb) from (
    select p.id from pengajuan_mahasiswa p
     where p.status in ('pembimbing', 'admin') and mhs_tingkat_tempo(p, p_jam1, p_jam24) > 0
     order by p.id limit 200) q);
end;
$$;

CREATE FUNCTION public.mhs_pemeriksa_tandai(p_kunci text, p_id bigint, p_kunci_tahap text, p_tingkat integer) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  if p_tingkat not in (1, 24) then raise exception 'Tingkat tidak dikenal.'; end if;
  select * into p from pengajuan_mahasiswa where id = p_id for update;
  if p.id is null or mhs_kunci_tahap(p) is distinct from p_kunci_tahap then return 'diabaikan'; end if;
  if mhs_tingkat_kabar(p) >= p_tingkat then return 'sudah'; end if;
  update pengajuan_mahasiswa set pemeriksa_dikabari = p_kunci_tahap || '#' || p_tingkat, pemeriksa_antre = null where id = p.id;
  return 'tercatat';
end;
$$;

CREATE FUNCTION public.mhs_pratinjau_admin(p_id bigint) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  p pengajuan_mahasiswa; t text := mhs_token_baru(); h text; v_lihat jsonb; v_periksa jsonb := '[]'::jsonb;
  v_pesan text; a record;
begin
  select * into p from pengajuan_mahasiswa where id = p_id;
  if p.id is null then raise exception 'Pengajuan tidak ditemukan.'; end if;
  if not boleh_pengajuan(p.jenis) then raise exception 'Pratinjau pengajuan khusus admin prodi atau koordinator bidangnya.'; end if;
  h := encode(extensions.digest(t, 'sha256'), 'hex');

  -- Tampilan mahasiswa (mhs_lihat asli).
  begin
    update pengajuan_mahasiswa set token_hash = h where id = p.id;
    v_lihat := mhs_lihat(t);
    raise exception '__pratinjau_batal__';
  exception when others then
    if sqlerrm <> '__pratinjau_batal__' then raise; end if;
  end;

  -- Pemeriksaan tombol yang tampil bagi mahasiswa pada keadaan ini (sama dengan pengajuan.html):
  --   Kirim untuk diperiksa: tahap pengajuan, draf/dikembalikan, bukan KP susulan selesai (mhs_kirim);
  --   Kirim laporan selesai: jendela laporan selesai KP terbuka DAN formulirnya tampil (pengajuan.html bukaSelesai: KP susulan
  --   selesai, tahap selesai, atau mahasiswa sudah melaporkan diterima instansi) (mhs_kirim_selesai).
  for a in select * from (values
      ('kirim', 'Kirim untuk diperiksa',
        p.tahap = 'pengajuan' and p.status in ('draf', 'dikembalikan') and coalesce(p.data ->> 'susulan', '') <> 'selesai'),
      ('kirim_selesai', 'Kirim laporan selesai', mhs_jendela_selesai(p) and (coalesce(p.data ->> 'susulan', '') = 'selesai'
        or p.tahap = 'selesai' or coalesce(p.data ->> 'jawaban_instansi', '') = 'diterima'))) x(aksi, label, tampil) where tampil loop
    v_pesan := null;
    begin
      update pengajuan_mahasiswa set token_hash = h where id = p.id;
      if a.aksi = 'kirim' then perform mhs_kirim(t); else perform mhs_kirim_selesai(t); end if;
      raise exception '__pratinjau_lolos__';
    exception when others then
      v_pesan := case when sqlerrm = '__pratinjau_lolos__' then null else sqlerrm end;
    end;
    v_periksa := v_periksa || jsonb_build_object('aksi', a.aksi, 'label', a.label, 'lolos', v_pesan is null, 'pesan', v_pesan);
  end loop;

  return jsonb_build_object('lihat', v_lihat, 'periksa', v_periksa);
end;
$$;

CREATE FUNCTION public.mhs_rapikan(p_jenis text, p_data jsonb) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    SET search_path TO 'public'
    AS $_$
declare
  k text; v jsonb; out jsonb := '{}'::jsonb;
  boleh text[] := case p_jenis
    when 'kp' then array['instansi', 'alamat_instansi', 'bidang_kerja', 'rencana_mulai', 'rencana_selesai', 'kontak_instansi', 'program', 'susulan']
    when 'surat' then array['jenis_surat', 'keperluan', 'tujuan_surat', 'alamat_tujuan', 'judul_penelitian', 'lokasi', 'waktu_pelaksanaan']
    when 'ta' then array['tahap_ta', 'judul', 'pembimbing_2', 'tampil_nama', 'kk_ta']
    when 'luaran' then array['kategori', 'judul', 'tahun', 'bulan', 'anggota', 'bersama_dosen', 'jenis_pub', 'tingkat', 'indeksasi',
                             'terbitan', 'doi_url', 'jenis_luaran', 'nomor', 'status_hki', 'tkt']
    -- 122: yudisium = judul TA dan catatan untuk admin (keduanya opsional).
    when 'yudisium' then array['judul', 'catatan']
    -- 144: kabar kegiatan (kolom kabar_kegiatan, patch 81).
    when 'kabar' then array['judul', 'tanggal', 'jenis_kegiatan', 'tempat', 'ringkasan', 'tautan']
    else array['nama_kegiatan', 'penyelenggara', 'tingkat', 'bidang', 'capaian', 'tanggal', 'anggota', 'tampil_nama', 'cerita'] end;
begin
  for k, v in select * from jsonb_each(coalesce(p_data, '{}'::jsonb)) loop
    continue when not (k = any(boleh));
    if k = 'anggota' then
      if jsonb_typeof(v) = 'array' then
        out := out || jsonb_build_object(k, (select coalesce(jsonb_agg(jsonb_build_object(
                 'nim', left(btrim(coalesce(x ->> 'nim', '')), 15), 'nama', left(btrim(coalesce(x ->> 'nama', '')), 120))), '[]'::jsonb)
               from (select x from jsonb_array_elements(v) x where btrim(coalesce(x ->> 'nama', '')) <> '' limit 10) a));
      end if;
    elsif k in ('tampil_nama', 'bersama_dosen') then
      out := out || jsonb_build_object(k, coalesce((v #>> '{}')::boolean, false));
    else
      out := out || jsonb_build_object(k, left(btrim(coalesce(v #>> '{}', '')),
               -- 144: batas kabar = batas kolom kabar_kegiatan (ringkasan 1200, judul dan tempat 200).
               case when p_jenis = 'kabar' and k = 'ringkasan' then 1200 when p_jenis = 'kabar' and k in ('judul', 'tempat') then 200
                    when k in ('cerita', 'keperluan', 'catatan') then 600 when k = 'judul' then 400 else 300 end));
    end if;
  end loop;
  if p_jenis = 'lomba' then
    if coalesce(out ->> 'tingkat', '') not in ('', 'internasional', 'nasional', 'wilayah_lokal') then
      raise exception 'Tingkat lomba tidak dikenal.'; end if;
    if coalesce(out ->> 'bidang', '') not in ('', 'akademik', 'non_akademik') then
      raise exception 'Bidang lomba tidak dikenal.'; end if;
  end if;
  if p_jenis = 'kp' and coalesce(out ->> 'program', '') not in ('', 'kp', 'magang') then
    raise exception 'Program KP tidak dikenal (kp atau magang).'; end if;
  -- 107: hanya 'selesai' (lapor selesai KP); nilai lama 'berjalan' dibuang (pengajuan KP biasa).
  if p_jenis = 'kp' and out ->> 'susulan' = 'berjalan' then out := out - 'susulan'; end if;
  if p_jenis = 'kp' and coalesce(out ->> 'susulan', '') not in ('', 'selesai') then
    raise exception 'Keadaan KP tidak dikenal (hanya selesai).'; end if;
  if p_jenis = 'surat' and coalesce(out ->> 'jenis_surat', '') not in ('', 'aktif_kuliah', 'izin_penelitian', 'rekomendasi') then
    raise exception 'Jenis surat tidak dikenal.'; end if;
  if p_jenis = 'ta' then
    if coalesce(out ->> 'tahap_ta', '') not in ('', 'penetapan_pembimbing', 'seminar_proposal', 'seminar_kemajuan', 'sidang_akhir') then
      raise exception 'Tahap TA tidak dikenal.'; end if;
    -- 110: kelompok keahlian topik TA (kode KK, config.yaml public_site.expertise_groups).
    if coalesce(out ->> 'kk_ta', '') !~ '^([A-Z0-9]{2,12})?$' then raise exception 'Kelompok keahlian TA tidak dikenal.'; end if;
    if coalesce(out ->> 'pembimbing_2', '') <> ''
       and not exists (select 1 from pembimbing_pilihan() x where x.id::text = out ->> 'pembimbing_2') then
      raise exception 'Pilih pembimbing 2 dari daftar.'; end if;
  end if;
  if p_jenis = 'luaran' then
    if coalesce(out ->> 'kategori', '') not in ('', 'publikasi', 'luaran') then raise exception 'Kategori tidak dikenal.'; end if;
    if coalesce(out ->> 'jenis_pub', '') not in ('', 'jurnal', 'prosiding', 'buku', 'lainnya') then raise exception 'Jenis publikasi tidak dikenal.'; end if;
    if coalesce(out ->> 'tingkat', '') not in ('', 'internasional', 'nasional', 'wilayah') then raise exception 'Tingkat tidak dikenal.'; end if;
    if coalesce(out ->> 'indeksasi', '') not in ('', 'scopus', 'wos', 'bereputasi', 'sinta', 'tidak_terindeks') then
      raise exception 'Indeksasi tidak dikenal.'; end if;
    if coalesce(out ->> 'jenis_luaran', '') not in ('', 'paten', 'paten_sederhana', 'hak_cipta', 'desain_industri', 'merek', 'ttg',
                                                   'produk', 'buku_isbn', 'book_chapter') then raise exception 'Jenis luaran tidak dikenal.'; end if;
    if coalesce(out ->> 'status_hki', '') not in ('', 'registered', 'granted', 'komersial') then raise exception 'Status paten tidak dikenal.'; end if;
    if coalesce(out ->> 'tkt', '') !~ '^([1-9])?$' then raise exception 'TKT harus 1-9.'; end if;
    if coalesce(out ->> 'tahun', '') !~ '^(\d{4})?$' then raise exception 'Tahun harus 4 angka.'; end if;
    if coalesce(out ->> 'bulan', '') !~ '^([1-9]|1[0-2])?$' then raise exception 'Bulan harus 1-12.'; end if;
    if coalesce(out ->> 'doi_url', '') <> '' and (out ->> 'doi_url') !~* '^https?://\S+$' then
      raise exception 'DOI/URL harus diawali https://'; end if;
  end if;
  -- 144: jenis kegiatan = kabar_kegiatan_jenis_check (patch 81; 'penelitian' dari patch 92 khusus dosen).
  if p_jenis = 'kabar' then
    if coalesce(out ->> 'jenis_kegiatan', '') not in ('', 'kuliah_tamu', 'kunjungan_lapangan', 'seminar', 'pengabdian', 'kerja_praktik',
                                                     'kompetisi', 'kerja_sama', 'lainnya') then
      raise exception 'Jenis kegiatan tidak dikenal.'; end if;
    if coalesce(out ->> 'tautan', '') <> '' and (out ->> 'tautan') !~* '^https?://\S+$' then
      raise exception 'Tautan harus diawali https://'; end if;
  end if;
  foreach k in array array['tanggal', 'rencana_mulai', 'rencana_selesai'] loop
    if coalesce(out ->> k, '') <> '' and (out ->> k) !~ '^\d{4}-\d{2}-\d{2}$' then
      raise exception 'Tanggal harus berbentuk YYYY-MM-DD.'; end if;
  end loop;
  return out;
end;
$_$;

CREATE FUNCTION public.mhs_rapikan_selesai(p_data jsonb) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    SET search_path TO 'public'
    AS $_$
declare k text; v jsonb; out jsonb := '{}'::jsonb;
  boleh text[] := array['tanggal_mulai', 'tanggal_selesai', 'pembimbing_lapangan', 'jabatan_lapangan', 'kontak_lapangan',
                        'divisi', 'ringkasan'];
begin
  for k, v in select * from jsonb_each(coalesce(p_data, '{}'::jsonb)) loop
    continue when not (k = any(boleh));
    out := out || jsonb_build_object(k, left(btrim(coalesce(v #>> '{}', '')), case when k = 'ringkasan' then 3000 else 300 end));
  end loop;
  foreach k in array array['tanggal_mulai', 'tanggal_selesai'] loop
    if coalesce(out ->> k, '') <> '' and (out ->> k) !~ '^\d{4}-\d{2}-\d{2}$' then
      raise exception 'Tanggal harus berbentuk YYYY-MM-DD.'; end if;
  end loop;
  if coalesce(out ->> 'tanggal_mulai', '') <> '' and coalesce(out ->> 'tanggal_selesai', '') <> ''
     and (out ->> 'tanggal_selesai') < (out ->> 'tanggal_mulai') then
    raise exception 'Tanggal selesai tidak boleh sebelum tanggal mulai.'; end if;
  return out;
end;
$_$;

CREATE FUNCTION public.mhs_tautan_berkas(p_token text, p_jenis text, p_nama text, p_url text) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare p pengajuan_mahasiswa; v_id bigint; v_url text := btrim(coalesce(p_url, ''));
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if p.jenis <> 'yudisium' then raise exception 'Tautan berkas hanya untuk berkas yudisium.'; end if;
  if not mhs_boleh(p) then raise exception 'Pengajuan sedang diperiksa; berkas tidak bisa diubah.'; end if;
  if not mhs_jenis_berkas_sah(p, p_jenis) then raise exception 'Jenis berkas tidak dikenal untuk pengajuan ini.'; end if;
  if length(v_url) > 500 or v_url !~ '^https://(drive|docs)\.google\.com/\S+$' then
    raise exception 'Tempelkan tautan Google Drive (diawali https://drive.google.com/ atau https://docs.google.com/).'; end if;
  if (select count(*) from pengajuan_berkas where pengajuan_id = p.id) >= 40 then
    raise exception 'Paling banyak 40 berkas per pengajuan.'; end if;
  insert into pengajuan_berkas (pengajuan_id, jenis, nama, url, tautan)
  values (p.id, p_jenis, left(coalesce(nullif(btrim(p_nama), ''), 'Tautan Google Drive'), 200), v_url, true)
  returning id into v_id;
  update pengajuan_mahasiswa set diperbarui = now() where id = p.id;
  return v_id;
end;
$_$;

CREATE FUNCTION public.mhs_tautan_id(p_kunci text, p_id bigint) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t text := mhs_token_baru();
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  update pengajuan_mahasiswa set token_hash = encode(extensions.digest(t, 'sha256'), 'hex'), tautan_dikirim = now()
   where id = p_id;
  if not found then raise exception 'Pengajuan tidak ditemukan.'; end if;
  return t;
end;
$$;

CREATE FUNCTION public.mhs_tautan_ulang(p_kunci text, p_nim text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r record; t text; out jsonb := '[]'::jsonb;
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  if exists (select 1 from pengajuan_mahasiswa where nim = btrim(p_nim) and tautan_dikirim > now() - interval '10 minutes') then
    raise exception 'Tautan baru saja dikirim. Periksa email kampus Anda atau coba lagi 10 menit lagi.'; end if;
  for r in select id, jenis, email, data from pengajuan_mahasiswa
            where nim = btrim(p_nim) and dibuat > now() - interval '2 years' order by id desc limit 10 loop
    t := mhs_token_baru();
    update pengajuan_mahasiswa set token_hash = encode(extensions.digest(t, 'sha256'), 'hex'), tautan_dikirim = now()
     where id = r.id;
    out := out || jsonb_build_object('id', r.id, 'jenis', r.jenis, 'email', r.email, 'token', t, 'judul', mhs_judul(r.jenis, r.data));
  end loop;
  return out;
end;
$$;

CREATE FUNCTION public.mhs_terima_instansi(p_token text, p_mulai text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare p pengajuan_mahasiswa; v_mulai text := btrim(coalesce(p_mulai, ''));
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if p.jenis <> 'kp' or p.tahap <> 'pengajuan' or p.status <> 'disetujui' then
    raise exception 'Hanya untuk pengajuan KP yang surat pengantarnya sudah terbit.'; end if;
  if v_mulai !~ '^\d{4}-\d{2}-\d{2}$' then raise exception 'Isi tanggal mulai KP.'; end if;
  if not exists (select 1 from pengajuan_berkas where pengajuan_id = p.id and jenis = 'surat_balasan') then
    raise exception 'Unggah surat balasan (penerimaan) dari instansi dulu.'; end if;
  update pengajuan_mahasiswa set diperbarui = now(),
         data = data || jsonb_build_object('jawaban_instansi', 'diterima', 'tanggal_mulai', v_mulai,
                                           'tanggal_jawaban', to_char(now() at time zone 'Asia/Jakarta', 'YYYY-MM-DD'))
   where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, 'disetujui', 'mahasiswa', left('Diterima instansi ' || coalesce(p.data ->> 'instansi', '') || '; mulai KP ' || v_mulai || '.', 600),
          'pengajuan');
  return 'diterima';
end;
$_$;

CREATE FUNCTION public.mhs_tingkat_kabar(p public.pengajuan_mahasiswa) RETURNS integer
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when p.pemeriksa_dikabari is null then 0
              when p.pemeriksa_dikabari = mhs_kunci_tahap(p) or p.pemeriksa_dikabari = mhs_kunci_tahap(p) || '#24' then 24
              when p.pemeriksa_dikabari = mhs_kunci_tahap(p) || '#1' then 1
              else 0 end
$$;

CREATE FUNCTION public.mhs_tingkat_tempo(p public.pengajuan_mahasiswa, p_jam1 integer, p_jam24 integer) RETURNS integer
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when p.status not in ('pembimbing', 'admin') then 0
              when mhs_tingkat_kabar(p) < 24 and mhs_waktu_tahap(p) <= now() - make_interval(mins => greatest(p_jam24, 0)) then 24
              when mhs_tingkat_kabar(p) = 0 and mhs_waktu_tahap(p) <= now() - make_interval(mins => greatest(p_jam1, 0)) then 1
              else 0 end
$$;

CREATE FUNCTION public.mhs_token_baru() RETURNS text
    LANGUAGE sql
    SET search_path TO 'public'
    AS $$
  select encode(extensions.gen_random_bytes(24), 'hex')
$$;

CREATE FUNCTION public.mhs_tolak_instansi(p_token text, p_alasan text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_alasan text := left(btrim(coalesce(p_alasan, '')), 300); v_ins text;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if p.jenis <> 'kp' or p.tahap <> 'pengajuan' or p.status <> 'disetujui' then
    raise exception 'Hanya untuk pengajuan KP yang surat pengantarnya sudah terbit.'; end if;
  if length(v_alasan) < 5 then raise exception 'Tulis alasan singkat penolakan dari instansi.'; end if;
  v_ins := coalesce(nullif(btrim(p.data ->> 'instansi'), ''), '(tanpa nama)');
  insert into kp_tolak_instansi (pengajuan_id, instansi, alasan) values (p.id, v_ins, v_alasan);
  update pengajuan_mahasiswa set status = 'ditolak', diperbarui = now(),
         data = data || jsonb_build_object('jawaban_instansi', 'ditolak', 'alasan_instansi', v_alasan,
                                           'tanggal_jawaban', to_char(now() at time zone 'Asia/Jakarta', 'YYYY-MM-DD'))
   where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, 'ditolak', 'mahasiswa', left('Ditolak instansi ' || v_ins || ': ' || v_alasan || '. Pengajuan ditutup; mahasiswa membuat pengajuan baru.', 600),
          'pengajuan');
  return 'ditolak';
end;
$$;

CREATE FUNCTION public.mhs_ubah(p_token text, p_nama text, p_pembimbing uuid, p_data jsonb) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; tanpa boolean;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if p.tahap <> 'pengajuan' or p.status not in ('draf', 'dikembalikan') then
    raise exception 'Pengajuan sedang diperiksa atau sudah disetujui; isian tidak bisa diubah.'; end if;
  tanpa := p.jenis in ('surat', 'yudisium');
  -- 144: kabar boleh tanpa dosen pendamping; bila diisi harus dari daftar.
  if not tanpa and not (p.jenis = 'kabar' and p_pembimbing is null)
     and not exists (select 1 from pembimbing_pilihan() x where x.id = p_pembimbing) then
    raise exception 'Pilih dosen pembimbing dari daftar.'; end if;
  update pengajuan_mahasiswa set nama = btrim(p_nama), pembimbing_id = case when tanpa then null else p_pembimbing end,
         data = mhs_rapikan(p.jenis, p_data), diperbarui = now() where id = p.id;
  return 'ok';
end;
$$;

CREATE FUNCTION public.mhs_ubah_selesai(p_token text, p_data jsonb) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa;
begin
  p := mhs_cari(p_token);
  if p.id is null then raise exception 'Tautan tidak berlaku.'; end if;
  if not mhs_jendela_selesai(p) then raise exception 'Laporan selesai KP belum bisa atau tidak bisa diubah sekarang.'; end if;
  update pengajuan_mahasiswa set data_selesai = mhs_rapikan_selesai(p_data), diperbarui = now() where id = p.id;
  return 'ok';
end;
$$;

CREATE FUNCTION public.mhs_waktu_tahap(p public.pengajuan_mahasiswa) RETURNS timestamp with time zone
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce((select r.waktu from pengajuan_riwayat r where r.pengajuan_id = p.id and r.status = p.status order by r.id desc limit 1),
                  p.diperbarui)
$$;

CREATE FUNCTION public.mk_atur_pengampu(p_kurikulum text, p_kode text, p_nidn text[]) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare x text; v_lama text;
begin
  if not (public.is_admin() or public.koordinator_aktif('kaprodi')) then
    raise exception 'Koordinator dan tim MK ditetapkan Kaprodi aktif atau admin prodi.'; end if;
  foreach x in array coalesce(p_nidn, '{}') loop
    if not exists (select 1 from public.dosen where nidn = x) then raise exception 'NIDN % bukan dosen terdaftar.', x; end if;
  end loop;
  select koordinator_nidn into v_lama from public.ref_mata_kuliah where kurikulum = p_kurikulum and kode = p_kode;
  update public.ref_mata_kuliah set pengampu = coalesce(p_nidn, '{}'),
         koordinator_nidn = case when v_lama = any(coalesce(p_nidn, '{}')) then v_lama else (coalesce(p_nidn, '{}'))[1] end,
         oleh = coalesce(auth.jwt() ->> 'email', oleh), diperbarui = now()
   where kurikulum = p_kurikulum and kode = p_kode;
  if not found then raise exception 'Mata kuliah tidak ditemukan.'; end if;
end $$;

CREATE FUNCTION public.mk_atur_tim(p_kurikulum text, p_kode text, p_koordinator text, p_tim text[]) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_koor text := nullif(btrim(coalesce(p_koordinator, '')), ''); v_tim text[]; x text;
begin
  if not (public.is_admin() or public.koordinator_aktif('kaprodi')) then
    raise exception 'Koordinator dan tim MK ditetapkan Kaprodi aktif atau admin prodi.'; end if;
  v_tim := array(select distinct btrim(t) from unnest(coalesce(p_tim, '{}')) t where btrim(t) <> '' and btrim(t) <> coalesce(v_koor, ''));
  if v_koor is null and cardinality(v_tim) > 0 then raise exception 'Pilih koordinator MK lebih dulu.'; end if;
  foreach x in array (case when v_koor is null then v_tim else array_prepend(v_koor, v_tim) end) loop
    if not exists (select 1 from public.dosen where nidn = x) then raise exception 'NIDN % bukan dosen terdaftar.', x; end if;
  end loop;
  update public.ref_mata_kuliah
     set pengampu = case when v_koor is null then '{}' else array_prepend(v_koor, v_tim) end,
         koordinator_nidn = v_koor, oleh = coalesce(auth.jwt() ->> 'email', oleh), diperbarui = now()
   where kurikulum = p_kurikulum and kode = p_kode;
  if not found then raise exception 'Mata kuliah tidak ditemukan.'; end if;
end $$;

CREATE FUNCTION public.mk_boleh_saya() RETURNS TABLE(kurikulum text, kode_mk text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select m.kurikulum, m.kode from public.ref_mata_kuliah m where public.boleh_mk(m.kurikulum, m.kode)
$$;

CREATE FUNCTION public.mk_simpan_rps(p_kurikulum text, p_kode text, p_url text, p_9_komponen boolean) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
begin
  if not public.boleh_mk(p_kurikulum, p_kode) then
    raise exception 'RPS diisi koordinator/pengampu mata kuliah ini, GKM, atau admin prodi.'; end if;
  if coalesce(p_url, '') <> '' and p_url !~* '^https://\S+$' then raise exception 'Tautan RPS harus diawali https://'; end if;
  update public.ref_mata_kuliah
     set rps_url = nullif(btrim(coalesce(p_url, '')), ''), rps_ada = (nullif(btrim(coalesce(p_url, '')), '') is not null),
         rps_9_komponen = p_9_komponen, oleh = coalesce(auth.jwt() ->> 'email', oleh), diperbarui = now()
   where kurikulum = p_kurikulum and kode = p_kode;
  if not found then raise exception 'Mata kuliah tidak ditemukan.'; end if;
end $_$;

CREATE FUNCTION public.nama_instansi_kunci(p text) RETURNS text
    LANGUAGE sql IMMUTABLE
    SET search_path TO 'public'
    AS $$
  select lower(regexp_replace(regexp_replace(btrim(coalesce(p, '')), '[.,]', '', 'g'), '\s+', ' ', 'g'))
$$;

CREATE FUNCTION public.nidn_saya() RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select d.nidn from public.dosen d where d.id = public.me()
$$;

CREATE FUNCTION public.padanan_berubah() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  declare v_lama text := coalesce(new.kurikulum_lama, old.kurikulum_lama); s record;
  begin
    for s in update mk_padanan_sah set status = 'draf', usulan = null, diperbarui = now()
              where kurikulum_lama = v_lama and status <> 'draf' returning kurikulum_lama, kurikulum_baru, revisi loop
      perform padanan_catat(s.kurikulum_lama, s.kurikulum_baru, 'berubah', 'Padanan disunting; perlu disahkan dan ditetapkan lagi.', s.revisi);
    end loop;
    return null;
  end $$;

CREATE FUNCTION public.padanan_catat(p_lama text, p_baru text, p_aksi text, p_catatan text, p_revisi integer) RETURNS void
    LANGUAGE sql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
    insert into mk_padanan_sah_log (kurikulum_lama, kurikulum_baru, aksi, oleh_id, oleh_nama, catatan, revisi)
    values (p_lama, p_baru, p_aksi, me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), left(p_catatan, 2000), p_revisi)
  $$;

CREATE FUNCTION public.padanan_kembalikan(p_lama text, p_baru text, p_catatan text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  declare r mk_padanan_sah; v_catatan text := nullif(btrim(coalesce(p_catatan, '')), '');
  begin
    if not (koordinator_aktif('kaprodi') or koordinator_aktif('dekan')) then
      raise exception 'Dikembalikan oleh Kaprodi atau Dekan aktif.'; end if;
    if v_catatan is null then raise exception 'Tulis catatan perbaikan untuk admin.'; end if;
    select * into r from mk_padanan_sah where kurikulum_lama = p_lama and kurikulum_baru = p_baru for update;
    if r.status is distinct from 'disahkan' then raise exception 'Hanya isi yang sedang menunggu penetapan yang bisa dikembalikan.'; end if;
    update mk_padanan_sah set status = 'draf', usulan = null, catatan = left(v_catatan, 2000), diperbarui = now()
     where kurikulum_lama = p_lama and kurikulum_baru = p_baru;
    perform padanan_catat(p_lama, p_baru, 'kembalikan', v_catatan, r.revisi);
    return 'draf';
  end $$;

CREATE FUNCTION public.padanan_sahkan(p_lama text, p_baru text, p_catatan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  declare r mk_padanan_sah; v_belum text[];
  begin
    if not koordinator_aktif('kaprodi') then raise exception 'Tabel ekuivalensi disahkan Kaprodi aktif (Penugasan koordinator).'; end if;
    if p_lama is null or p_baru is null or p_lama = p_baru then raise exception 'Pilih kurikulum lama dan baru yang berbeda.'; end if;
    select array_agg(m.kode order by m.kode) into v_belum from ref_mata_kuliah m
     where m.kurikulum = p_lama and not exists (select 1 from ref_mk_padanan p where p.kurikulum_lama = p_lama and p.kode_lama = m.kode
       and (p.kurikulum_baru = p_baru or p.tidak_berlanjut));
    if not exists (select 1 from ref_mata_kuliah where kurikulum = p_lama) then raise exception 'MK % belum ada.', p_lama; end if;
    if v_belum is not null then
      raise exception '% MK % belum punya baris padanan (isi padanan atau TIDAK_BERLANJUT): %', cardinality(v_belum), p_lama,
        array_to_string(v_belum[1:10], ', ') || case when cardinality(v_belum) > 10 then ', …' else '' end; end if;
    insert into mk_padanan_sah (kurikulum_lama, kurikulum_baru) values (p_lama, p_baru) on conflict do nothing;
    select * into r from mk_padanan_sah where kurikulum_lama = p_lama and kurikulum_baru = p_baru for update;
    if r.status = 'disahkan' then raise exception 'Sudah disahkan, menunggu penetapan Dekan.'; end if;
    if r.status = 'ditetapkan' then raise exception 'Sudah ditetapkan Dekan; sunting padanan dulu bila ada perubahan.'; end if;
    update mk_padanan_sah set status = 'disahkan', usulan = padanan_salinan(p_lama, p_baru), sah_pada = now(), sah_oleh = me(),
           sah_nama = (select coalesce(nama_gelar, nama) from dosen where id = me()), catatan = null, diperbarui = now()
     where kurikulum_lama = p_lama and kurikulum_baru = p_baru;
    perform padanan_catat(p_lama, p_baru, 'sahkan', nullif(btrim(coalesce(p_catatan, '')), ''), r.revisi);
    return 'disahkan';
  end $$;

CREATE FUNCTION public.padanan_salinan(p_lama text, p_baru text) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
    select jsonb_build_object(
      'kurikulum_lama', p_lama, 'kurikulum_baru', p_baru,
      'mk_lama', coalesce((select jsonb_agg(jsonb_build_object('kode', m.kode, 'nama', m.nama, 'sks', m.sks, 'semester', m.semester,
          'sifat', m.sifat) order by m.semester nulls last, m.kode) from ref_mata_kuliah m where m.kurikulum = p_lama), '[]'::jsonb),
      'mk_baru', coalesce((select jsonb_agg(jsonb_build_object('kode', m.kode, 'nama', m.nama, 'sks', m.sks, 'semester', m.semester,
          'sifat', m.sifat) order by m.semester nulls last, m.kode) from ref_mata_kuliah m where m.kurikulum = p_baru), '[]'::jsonb),
      'padanan', coalesce((select jsonb_agg(jsonb_build_object('kode_lama', p.kode_lama, 'kode_baru', p.kode_baru, 'model', p.model,
          'tidak_berlanjut', p.tidak_berlanjut, 'catatan', p.catatan) order by p.kode_lama, p.kode_baru nulls first)
        from ref_mk_padanan p where p.kurikulum_lama = p_lama and (p.kurikulum_baru = p_baru or p.tidak_berlanjut)), '[]'::jsonb))
  $$;

CREATE FUNCTION public.padanan_tetapkan(p_lama text, p_baru text, p_catatan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  declare r mk_padanan_sah;
  begin
    if not koordinator_aktif('dekan') then raise exception 'Tabel ekuivalensi ditetapkan Dekan aktif (Penugasan koordinator).'; end if;
    select * into r from mk_padanan_sah where kurikulum_lama = p_lama and kurikulum_baru = p_baru for update;
    if r.status is distinct from 'disahkan' then raise exception 'Belum disahkan Kaprodi.'; end if;
    update mk_padanan_sah set status = 'ditetapkan', tetap_pada = now(), tetap_oleh = me(),
           tetap_nama = (select coalesce(nama_gelar, nama) from dosen where id = me()), revisi = r.revisi + 1,
           terbit = r.usulan || jsonb_build_object('revisi', r.revisi + 1,
             'disahkan', jsonb_build_object('nama', r.sah_nama, 'pada', r.sah_pada),
             'ditetapkan', jsonb_build_object('nama', (select coalesce(nama_gelar, nama) from dosen where id = me()), 'pada', now())),
           terbit_pada = now(), diperbarui = now()
     where kurikulum_lama = p_lama and kurikulum_baru = p_baru;
    perform padanan_catat(p_lama, p_baru, 'tetapkan', nullif(btrim(coalesce(p_catatan, '')), ''), r.revisi + 1);
    return 'ditetapkan';
  end $$;

CREATE FUNCTION public.pasang_jaga_hanya_baca() RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r record; n integer := 0;
begin
  for r in select c.relname from pg_class c join pg_namespace s on s.oid = c.relnamespace
            where s.nspname = 'public' and c.relkind in ('r', 'p') and c.relname not in ('pemakaian_halaman', 'jejak')
              and not c.relispartition loop
    execute format('drop trigger if exists jaga_hanya_baca on public.%I', r.relname);
    if r.relname = 'dosen' then
      execute format('create trigger jaga_hanya_baca before insert or update or delete on public.%I '
                     'for each row execute function public.jaga_hanya_baca()', r.relname);
    else
      execute format('create trigger jaga_hanya_baca before insert or update or delete or truncate on public.%I '
                     'for each statement execute function public.jaga_hanya_baca()', r.relname);
    end if;
    n := n + 1;
  end loop;
  return n;
end $$;

CREATE FUNCTION public.pasang_jejak() RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t text; n integer := 0;
begin
  for t in select c.relname from pg_class c join pg_namespace s on s.oid = c.relnamespace
            where s.nspname = 'public' and c.relkind = 'r'
              and (c.relname = any(array['karya', 'karya_penulis', 'karya_bukti', 'karya_mitra', 'karya_mahasiswa',
                                         'dosen', 'butir_bukti', 'dokumen', 'pengaturan', 'led_narasi', 'led_penugasan',
                                         'led_tim', 'ami_temuan', 'cpl_kelas', 'cpl_berkas', 'cpl_ringkasan'])
                   or c.relname like 'lkps\_%' or c.relname like 'ref\_%')
  loop
    execute format('drop trigger if exists catat_jejak on public.%I', t);
    execute format('create trigger catat_jejak after insert or update or delete on public.%I '
                   'for each row execute function public.catat_jejak()', t);
    n := n + 1;
  end loop;
  return n;
end $$;

CREATE FUNCTION public.pasang_jejak_evaluasi() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t text;
begin
  foreach t in array array['evaluasi_mk', 'evaluasi_tindak'] loop
    execute format('drop trigger if exists catat_jejak on public.%I', t);
    execute format('create trigger catat_jejak after insert or update or delete on public.%I '
                   'for each row execute function public.catat_jejak()', t);
  end loop;
end $$;

CREATE FUNCTION public.pasang_jejak_spmi() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t text;
begin
  foreach t in array array['spmi_standar', 'spmi_capaian', 'spmi_standar_revisi'] loop
    execute format('drop trigger if exists catat_jejak on public.%I', t);
    execute format('create trigger catat_jejak after insert or update or delete on public.%I '
                   'for each row execute function public.catat_jejak()', t);
  end loop;
end $$;

CREATE FUNCTION public.pasang_jejak_target() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t text;
begin
  foreach t in array array['target_baku', 'target_dosen'] loop
    execute format('drop trigger if exists catat_jejak on public.%I', t);
    execute format('create trigger catat_jejak after insert or update or delete on public.%I '
                   'for each row execute function public.catat_jejak()', t);
  end loop;
end $$;

CREATE FUNCTION public.pejabat_aktif(p_jabatan text) RETURNS uuid
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select k.dosen_id from koordinator k
   where k.jabatan = p_jabatan and k.mulai <= current_date and (k.selesai is null or k.selesai >= current_date)
   order by k.mulai desc limit 1
$$;

CREATE FUNCTION public.pemakaian_rekap(p_hari integer DEFAULT 60) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_dari date := (now() at time zone 'Asia/Jakarta')::date - greatest(1, least(coalesce(p_hari, 60), 180));
begin
  if not is_admin() then raise exception 'Rekap pemakaian hanya untuk admin.'; end if;
  return jsonb_build_object('dari', v_dari, 'mulai_catat', (select min(tanggal) from pemakaian_halaman),
    'halaman', (select coalesce(jsonb_agg(x order by x->>'halaman'), '[]'::jsonb) from (
      select jsonb_build_object('halaman', p.halaman, 'kunjungan', sum(p.n), 'pengguna', count(distinct p.dosen_id),
        'hari', count(distinct p.tanggal), 'terakhir', max(p.tanggal),
        'peran', (select jsonb_object_agg(q.peran, q.u) from (select coalesce(p2.peran, '-') peran, count(distinct p2.dosen_id) u
                    from pemakaian_halaman p2 where p2.halaman = p.halaman and p2.tanggal >= v_dari group by 1) q),
        'jabatan', (select coalesce(jsonb_object_agg(q.j, q.u), '{}'::jsonb) from (select j, count(distinct p3.dosen_id) u
                    from pemakaian_halaman p3, unnest(p3.jabatan) j where p3.halaman = p.halaman and p3.tanggal >= v_dari group by j) q)) x
      from pemakaian_halaman p where p.tanggal >= v_dari group by p.halaman) z),
    'pengguna_aktif', (select count(distinct dosen_id) from pemakaian_halaman where tanggal >= v_dari));
end $$;

CREATE FUNCTION public.pembimbing_pilihan() RETURNS TABLE(id uuid, nama text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select d.id, d.nama from dosen d
   where d.aktif and d.peran <> 'asesor' and (d.dtps or d.kategori is not null) and d.tugas_belajar is null
   order by d.nama
$$;

CREATE FUNCTION public.pembimbing_pilihan_ta() RETURNS TABLE(id uuid, nama text, kk text, kk_cocok text[])
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select x.id, x.nama, d.kelompok_keahlian,
         case when d.kelompok_keahlian is null then '{}'::text[] else
           array(select d.kelompok_keahlian union
                 select case when k.kk_a = d.kelompok_keahlian then k.kk_b else k.kk_a end from ta_kk_dekat k
                  where d.kelompok_keahlian in (k.kk_a, k.kk_b) order by 1) end
    from pembimbing_pilihan() x join dosen d on d.id = x.id
   order by x.nama
$$;

CREATE FUNCTION public.pengajuan_batalkan(p_id bigint, p_alasan text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_alasan text := left(btrim(coalesce(p_alasan, '')), 300); v_nama text;
begin
  select * into p from pengajuan_mahasiswa where id = p_id;
  if p.id is null then raise exception 'Pengajuan tidak ditemukan.'; end if;
  if not boleh_pengajuan(p.jenis) then raise exception 'Pembatalan oleh prodi khusus admin prodi atau koordinator bidangnya.'; end if;
  if v_alasan = '' then raise exception 'Tulis alasan pembatalan (mis. permintaan mahasiswa: salah jalur).'; end if;
  if p.status = 'dibatalkan' then return 'dibatalkan'; end if;
  if p.status in ('ditolak') or (p.status = 'disetujui' and coalesce(p.tahap, 'pengajuan') = 'selesai')
     or (p.status = 'disetujui' and p.jenis <> 'kp') then
    raise exception 'Pengajuan yang sudah diputuskan tidak dibatalkan.'; end if;
  select nama into v_nama from dosen where id = me();
  update pengajuan_mahasiswa set status = 'dibatalkan', diperbarui = now() where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, 'dibatalkan', coalesce(v_nama, 'admin prodi'), 'Dibatalkan prodi atas permintaan: ' || v_alasan || '.', coalesce(p.tahap, 'pengajuan'));
  return 'dibatalkan';
end;
$$;

CREATE FUNCTION public.pengajuan_catat_berkas(p_id bigint, p_jenis text, p_nama text, p_url text) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_id bigint; saya uuid := me();
begin
  select * into p from pengajuan_mahasiswa where id = p_id;
  if p.id is null then raise exception 'Pengajuan tidak ditemukan.'; end if;
  if not (boleh_pengajuan(p.jenis) or (p_jenis not in ('surat_pengantar', 'surat_jadi') and coalesce(p.pembimbing_id = saya, false))) then
    raise exception 'Surat dari prodi diunggah koordinator bidangnya atau admin.'; end if;
  insert into pengajuan_berkas (pengajuan_id, jenis, nama, url, oleh)
  values (p.id, p_jenis, left(coalesce(p_nama, ''), 200), p_url, coalesce((select email from dosen where id = saya), 'prodi'))
  returning id into v_id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, p.status, coalesce((select nama from dosen where id = saya), 'prodi'),
          'Mengunggah ' || replace(p_jenis, '_', ' ') || case when p_nama <> '' then ': ' || p_nama else '' end, p.tahap);
  return v_id;
end;
$$;

CREATE FUNCTION public.pengajuan_jadwalkan(p_id bigint, p_tanggal date, p_jam text, p_ruang text, p_tautan text, p_penguji text[], p_penguji_luar text DEFAULT NULL::text) RETURNS bigint
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_j bigint; v_pb text[]; v_nama text;
begin
  if not boleh_pengajuan('ta') then raise exception 'Menjadwalkan khusus koordinator TA atau admin.'; end if;
  select * into p from pengajuan_mahasiswa where id = p_id for update;
  if p.id is null or p.jenis <> 'ta' then raise exception 'Pengajuan TA tidak ditemukan.'; end if;
  if p.status <> 'admin' then raise exception 'Pengajuan belum disetujui pembimbing atau sudah dijadwalkan.'; end if;
  if p_tanggal is null then raise exception 'Isi tanggal.'; end if;
  if cardinality(coalesce(p_penguji, '{}')) = 0 and coalesce(btrim(p_penguji_luar), '') = '' then
    raise exception 'Tetapkan minimal satu penguji.'; end if;
  v_pb := array_remove(array[(select nidn from dosen where id = p.pembimbing_id),
                             (select nidn from dosen where id::text = p.data ->> 'pembimbing_2')], null);
  select id into v_j from jadwal_ta where pengajuan_id = p.id;
  if v_j is null then
    insert into jadwal_ta (pengajuan_id, tahap, nama_mahasiswa, nim, judul, pembimbing, penguji, penguji_luar, tanggal, jam, ruang,
                           tautan_daring, status, tampil_nama, oleh)
    values (p.id, p.data ->> 'tahap_ta', p.nama, p.nim, p.data ->> 'judul', v_pb, coalesce(p_penguji, '{}'),
            nullif(btrim(coalesce(p_penguji_luar, '')), ''), p_tanggal, nullif(btrim(coalesce(p_jam, '')), ''),
            nullif(btrim(coalesce(p_ruang, '')), ''), nullif(btrim(coalesce(p_tautan, '')), ''), 'terjadwal',
            coalesce((p.data ->> 'tampil_nama')::boolean, false), (select email from dosen where id = me()))
    returning id into v_j;
  else
    update jadwal_ta set tanggal = p_tanggal, jam = nullif(btrim(coalesce(p_jam, '')), ''), ruang = nullif(btrim(coalesce(p_ruang, '')), ''),
           tautan_daring = nullif(btrim(coalesce(p_tautan, '')), ''), penguji = coalesce(p_penguji, '{}'),
           penguji_luar = nullif(btrim(coalesce(p_penguji_luar, '')), ''), status = 'terjadwal', diperbarui = now()
     where id = v_j;
  end if;
  select nama into v_nama from dosen where id = me();
  update pengajuan_mahasiswa set status = 'disetujui', diperbarui = now() where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, 'disetujui', coalesce(v_nama, 'prodi'), 'Dijadwalkan ' || to_char(p_tanggal, 'DD-MM-YYYY')
          || coalesce(' ' || nullif(btrim(p_jam), ''), '') || coalesce(', ' || nullif(btrim(p_ruang), ''), ''), 'pengajuan');
  return v_j;
end;
$$;

CREATE FUNCTION public.pengajuan_putuskan(p_id bigint, p_aksi text, p_catatan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  p pengajuan_mahasiswa; saya uuid := me(); adm boolean; v_nama text; v_baru text;
  v_catatan text := nullif(btrim(coalesce(p_catatan, '')), ''); v_pres bigint; v_nidn text; v_tabel text; v_nm text; v_nim text; v_url text;
begin
  if saya is null then raise exception 'Perlu masuk.'; end if;
  select * into p from pengajuan_mahasiswa where id = p_id for update;
  if p.id is null then raise exception 'Pengajuan tidak ditemukan.'; end if;
  adm := boleh_pengajuan(p.jenis);
  select nama into v_nama from dosen where id = saya;
  if p.status = 'pembimbing' then
    -- 144: coalesce: kabar boleh tanpa dosen pendamping (pembimbing_id null); null = saya tidak boleh lolos sebagai "bukan false".
    if not (adm or coalesce(p.pembimbing_id = saya, false)) then raise exception 'Hanya dosen pembimbing, koordinator, atau admin.'; end if;
  elsif p.status = 'admin' then
    if not adm then raise exception 'Tahap ini diputuskan koordinator bidangnya atau admin.'; end if;
  else
    raise exception 'Pengajuan tidak sedang menunggu pemeriksaan.';
  end if;
  if p_aksi in ('kembalikan', 'tolak') and v_catatan is null then raise exception 'Tulis catatan untuk mahasiswa.'; end if;
  if p_aksi = 'tolak' and not adm then raise exception 'Menolak khusus koordinator/admin; pembimbing mengembalikan dengan catatan.'; end if;
  v_baru := case p_aksi when 'kembalikan' then 'dikembalikan' when 'tolak' then 'ditolak'
                        -- 108: lomba = satu persetujuan (pembimbing, pembina kemahasiswaan, atau admin; siapa pun lebih dulu).
                        -- 144: kabar juga (dosen pendamping bila dipilih, pembina kemahasiswaan, atau admin).
                        when 'setujui' then case when p.status = 'pembimbing' and p.jenis not in ('lomba', 'kabar') then 'admin' else 'disetujui' end end;
  if v_baru is null then raise exception 'Aksi tidak dikenal.'; end if;
  if v_baru = 'disetujui' and p.jenis = 'surat'
     and not exists (select 1 from pengajuan_berkas where pengajuan_id = p.id and jenis = 'surat_jadi') then
    raise exception 'Unggah surat yang sudah ditandatangani dulu.'; end if;
  if v_baru = 'disetujui' and p.jenis = 'ta' and coalesce(p.data ->> 'tahap_ta', '') <> 'penetapan_pembimbing' then
    raise exception 'Seminar/sidang TA disetujui dengan mengisi jadwal (Jadwalkan).'; end if;
  -- 110: pembimbing 1 di luar KK TA hanya bila ditetapkan koordinator dengan alasan (ta_tetapkan_pembimbing).
  if v_baru = 'disetujui' and p.data ->> 'tahap_ta' = 'penetapan_pembimbing'
     and not ta_kk_cocok(p.data ->> 'kk_ta', (select d.kelompok_keahlian from dosen d where d.id = p.pembimbing_id))
     and coalesce(p.data ->> 'alasan_luar_kk', '') = '' then
    raise exception 'Pembimbing 1 di luar kelompok keahlian TA: tetapkan pembimbing dengan alasan dulu.'; end if;

  if v_baru = 'disetujui' and p.jenis = 'lomba' and p.prestasi_id is null then
    select nidn into v_nidn from dosen where id = p.pembimbing_id;
    insert into lkps_prestasi_mahasiswa (nama_mahasiswa, nim, nama_kegiatan, penyelenggara, bidang, bulan, tingkat, capaian,
                                         tahun, pembimbing, status, tampil_nama, cerita, oleh)
    select string_agg(a.nama, '; ' order by a.n), string_agg(nullif(a.nim, ''), '; ' order by a.n),
           p.data ->> 'nama_kegiatan', nullif(p.data ->> 'penyelenggara', ''), p.data ->> 'bidang',
           extract(month from (p.data ->> 'tanggal')::date)::smallint, p.data ->> 'tingkat', nullif(p.data ->> 'capaian', ''),
           extract(year from (p.data ->> 'tanggal')::date)::int,
           case when v_nidn is null then '{}'::text[] else array[v_nidn] end, 'terverifikasi',
           coalesce((p.data ->> 'tampil_nama')::boolean, false), nullif(p.data ->> 'cerita', ''),
           'pengajuan mahasiswa #' || p.id
      from (select 0 as n, p.nim as nim, p.nama as nama
            union all
            select o.n, x ->> 'nim', x ->> 'nama'
              from jsonb_array_elements(coalesce(p.data -> 'anggota', '[]'::jsonb)) with ordinality as o(x, n)
             where coalesce(x ->> 'nim', '') <> p.nim) a
    returning id into v_pres;
    insert into lkps_bukti (tabel, baris_id, judul, url, oleh, jenis)
    select 'lkps_prestasi_mahasiswa', v_pres, coalesce(nullif(b.nama, ''), b.jenis), b.url, 'pengajuan mahasiswa #' || p.id,
           case when b.jenis in ('foto', 'sertifikat', 'surat_tugas') then b.jenis else 'lainnya' end   -- lkps_bukti_jenis_check (38)
      from pengajuan_berkas b where b.pengajuan_id = p.id;
    update pengajuan_mahasiswa set prestasi_id = v_pres where id = p.id;
  end if;

  if v_baru = 'disetujui' and p.jenis = 'luaran' and p.luaran_id is null then
    if coalesce((p.data ->> 'bersama_dosen')::boolean, false) then
      v_catatan := coalesce(v_catatan || ' ', '') || '(Ditulis bersama dosen: dicatat lewat karya dosen, tidak masuk tabel mahasiswa.)';
    else
      select string_agg(a.nama, '; ' order by a.n), string_agg(nullif(a.nim, ''), '; ' order by a.n) into v_nm, v_nim
        from (select 0 as n, p.nim as nim, p.nama as nama
              union all
              select o.n, x ->> 'nim', x ->> 'nama'
                from jsonb_array_elements(coalesce(p.data -> 'anggota', '[]'::jsonb)) with ordinality as o(x, n)
               where coalesce(x ->> 'nim', '') <> p.nim) a;
      v_url := nullif(p.data ->> 'doi_url', '');
      if p.data ->> 'kategori' = 'publikasi' then
        v_tabel := 'lkps_publikasi_mahasiswa';
        insert into lkps_publikasi_mahasiswa (tahun, judul, nama_mahasiswa, nim, jenis, tingkat, indeksasi, bulan, bukti_url, oleh)
        values ((p.data ->> 'tahun')::int, p.data ->> 'judul', v_nm, v_nim, p.data ->> 'jenis_pub', nullif(p.data ->> 'tingkat', ''),
                nullif(p.data ->> 'indeksasi', ''), nullif(p.data ->> 'bulan', '')::smallint, v_url, 'pengajuan mahasiswa #' || p.id)
        returning id into v_pres;
      else
        v_tabel := 'lkps_luaran_mahasiswa';
        insert into lkps_luaran_mahasiswa (tahun, bulan, jenis, judul, nama_mahasiswa, nim, bukti_url, status_hki, nomor, tkt, oleh)
        values ((p.data ->> 'tahun')::int, nullif(p.data ->> 'bulan', '')::smallint, p.data ->> 'jenis_luaran', p.data ->> 'judul',
                v_nm, v_nim, v_url, nullif(p.data ->> 'status_hki', ''), nullif(p.data ->> 'nomor', ''), nullif(p.data ->> 'tkt', '')::int,
                'pengajuan mahasiswa #' || p.id)
        returning id into v_pres;
      end if;
      insert into lkps_bukti (tabel, baris_id, judul, url, oleh)
      select v_tabel, v_pres, coalesce(nullif(b.nama, ''), b.jenis), b.url, 'pengajuan mahasiswa #' || p.id
        from pengajuan_berkas b where b.pengajuan_id = p.id;
      update pengajuan_mahasiswa set luaran_id = v_pres where id = p.id;
    end if;
  end if;

  -- 144: kabar kegiatan mahasiswa langsung terbit (beranda dan kabar.html); foto = berkas foto, maks. 6 (urut unggahan).
  if v_baru = 'disetujui' and p.jenis = 'kabar' and p.kabar_id is null then
    insert into kabar_kegiatan (judul, tanggal, jenis, tempat, ringkasan, tautan, foto, status, catatan, dilaporkan_oleh, oleh)
    values (left(btrim(p.data ->> 'judul'), 200), (p.data ->> 'tanggal')::date, coalesce(nullif(p.data ->> 'jenis_kegiatan', ''), 'lainnya'),
            nullif(left(btrim(coalesce(p.data ->> 'tempat', '')), 200), ''), left(btrim(p.data ->> 'ringkasan'), 1200),
            nullif(btrim(coalesce(p.data ->> 'tautan', '')), ''),
            coalesce((select array_agg(f.url order by f.id) from (select b.id, b.url from pengajuan_berkas b
                        where b.pengajuan_id = p.id and b.jenis = 'foto' order by b.id limit 6) f), '{}'::text[]),
            'terbit', left('Dari pengajuan mahasiswa #' || p.id || ', diverifikasi ' || coalesce(v_nama, 'prodi') || '.', 1000),
            null, 'pengajuan mahasiswa #' || p.id)
    returning id into v_pres;
    update pengajuan_mahasiswa set kabar_id = v_pres where id = p.id;
  end if;

  update pengajuan_mahasiswa set status = v_baru, diperbarui = now() where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, v_baru, coalesce(v_nama, 'prodi') || case when adm and p.status = 'pembimbing' and p.pembimbing_id is distinct from saya
                                                     then case when p.jenis in ('lomba', 'kabar') then ' (pembina kemahasiswaan/admin)' else ' (koordinator/admin)' end
                                                     else '' end, v_catatan, p.tahap);
  return v_baru;
end;
$$;

CREATE FUNCTION public.pengampu_evaluasi(e bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.evaluasi_mk where id = e and dosen_id = public.me());
$$;

CREATE FUNCTION public.pengampu_kelas_mk(p_ta text, p_sm text, p_kode text, p_kelas text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.me() is not null and (exists (select 1 from public.cpl_kelas k
    where k.tahun_akademik = p_ta and k.semester = p_sm and upper(k.kode_mk) = upper(p_kode)
      and (p_kelas is null or k.kelas = p_kelas) and lower(k.dosen_email) = lower(auth.jwt() ->> 'email'))
    or public.mengajar_kelas(p_ta, p_sm, p_kode, p_kelas))
$$;

CREATE FUNCTION public.pengatur_jadwal() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.is_admin() or public.koordinator_aktif('kaprodi') or public.koordinator_aktif('koordinator_ta')
      or public.koordinator_aktif('koordinator_kp')
$$;

CREATE FUNCTION public.pengatur_kelas() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.is_admin() or public.koordinator_aktif('kaprodi')
$$;

CREATE FUNCTION public.pengelola_insentif() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select is_admin() or koordinator_aktif('kaprodi')
$$;

CREATE FUNCTION public.pengumuman_mahasiswa_aktif() RETURNS TABLE(id bigint, judul text, isi text, berlaku_sampai date, diperbarui timestamp with time zone)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select p.id, p.judul, p.isi, p.berlaku_sampai, p.diperbarui
    from public.pengumuman_mahasiswa p
   where p.berlaku_sampai is null or p.berlaku_sampai >= current_date
   order by p.diperbarui desc
   limit 200;
$$;

CREATE FUNCTION public.penulis_karya(k uuid) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.karya_penulis kp
    where kp.karya_id = k and kp.dosen_id = public.me())
$$;

CREATE FUNCTION public.perbarui_tindak_lanjut(p_id bigint, p_status text, p_catatan text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t public.rapat_tindak;
begin
  select * into t from public.rapat_tindak where id = p_id;
  if not found then raise exception 'Tindak lanjut tidak ditemukan.'; end if;
  if not (t.pj_dosen_id = public.me() or public.rapat_editor(t.rapat_id)) then
    raise exception 'Hanya PJ atau pencatat rapat yang bisa memperbarui tindak lanjut ini.';
  end if;
  if p_status not in ('terbuka', 'proses', 'selesai', 'batal') then raise exception 'Status tidak sah.'; end if;
  update public.rapat_tindak set status = p_status,
    catatan = coalesce(nullif(trim(p_catatan), ''), catatan),
    tanggal_selesai = case when p_status = 'selesai' then coalesce(tanggal_selesai, current_date) else null end,
    diperbarui = now()
  where id = p_id;
end $$;

CREATE FUNCTION public.periksa_induk() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare kat text;
begin
  if new.induk_id is null then return new; end if;
  if new.induk_id = new.id then
    raise exception 'Karya tidak boleh menunjuk dirinya sendiri sebagai induk.';
  end if;
  select kategori into kat from public.karya where id = new.induk_id;
  if kat is null or kat not in ('penelitian', 'pkm') then
    raise exception 'Induk harus kegiatan penelitian atau PkM.';
  end if;
  return new;
end $$;

CREATE FUNCTION public.periksa_keamanan() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  isi jsonb := new.isi; v_n int; v_nama text;
begin
  if new.tabel = 'dosen' then
    v_nama := coalesce(isi ->> 'nama', (new.ubah -> 'nama' ->> 1), new.baris);
    if new.aksi = 'tambah' and coalesce(isi ->> 'peran', 'dosen') <> 'dosen' then
      insert into peringatan_keamanan (jenis, oleh, rinci)
      values ('akun_baru', new.oleh, format('Akun baru %s (%s) berperan %s.', isi ->> 'nama', isi ->> 'email', isi ->> 'peran'));
    elsif new.aksi = 'hapus' then
      insert into peringatan_keamanan (jenis, oleh, rinci)
      values ('akun_dihapus', new.oleh, format('Akun %s (%s, peran %s) dihapus.', isi ->> 'nama', isi ->> 'email', isi ->> 'peran'));
    elsif new.aksi = 'ubah' then
      select nama into v_nama from dosen where id::text = new.baris;
      if new.ubah ? 'peran' then
        insert into peringatan_keamanan (jenis, oleh, rinci)
        values ('peran', new.oleh, format('Peran %s berubah dari %s menjadi %s.', coalesce(v_nama, new.baris),
                new.ubah -> 'peran' ->> 0, new.ubah -> 'peran' ->> 1));
      end if;
      if new.ubah ? 'email' then
        insert into peringatan_keamanan (jenis, oleh, rinci)
        values ('email', new.oleh, format('Email login %s berubah dari %s menjadi %s.', coalesce(v_nama, new.baris),
                new.ubah -> 'email' ->> 0, new.ubah -> 'email' ->> 1));
      end if;
    end if;
  elsif new.tabel = 'koordinator' then
    select nama into v_nama from dosen where id::text = coalesce(isi ->> 'dosen_id',
      (select k.dosen_id::text from koordinator k where k.id::text = new.baris));
    insert into peringatan_keamanan (jenis, oleh, rinci)
    values ('koordinator', new.oleh, format('Penugasan koordinator %s: %s%s.',
            case new.aksi when 'tambah' then 'ditambah' when 'hapus' then 'dihapus' else 'diubah' end,
            coalesce(v_nama, 'dosen'), coalesce(' sebagai ' || coalesce(isi ->> 'jabatan',
              (select k.jabatan from koordinator k where k.id::text = new.baris)), '')));
  end if;

  if new.aksi = 'hapus' then
    select count(*) into v_n from jejak where oleh = new.oleh and aksi = 'hapus' and waktu > now() - interval '1 hour';
    if v_n >= 20 and not exists (select 1 from peringatan_keamanan where jenis = 'hapus_massal' and oleh = new.oleh
                                   and waktu > now() - interval '1 hour') then
      insert into peringatan_keamanan (jenis, oleh, rinci)
      values ('hapus_massal', new.oleh, format('%s baris dihapus dalam 1 jam terakhir oleh pelaku yang sama (terakhir di tabel %s).',
              v_n, new.tabel));
    end if;
  end if;
  return null;
end $$;

CREATE FUNCTION public.portofolio_ringkas() RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select jsonb_build_object(
    'kelas', coalesce((select jsonb_agg(jsonb_build_object('id', k.id, 'tahun_akademik', k.tahun_akademik, 'semester', k.semester,
        'kode_mk', k.kode_mk, 'kelas', k.kelas, 'dosen_email', k.dosen_email,
        'nilai', exists (select 1 from public.cpl_berkas c where c.kelas_id = k.id)))
      from public.cpl_kelas k
      where exists (select 1 from public.ref_mata_kuliah m where upper(m.kode) = upper(k.kode_mk)
                      and public.boleh_portofolio_baca(k.tahun_akademik, k.semester, m.kurikulum, m.kode))), '[]'::jsonb),
    'evaluasi', coalesce((select jsonb_agg(jsonb_build_object('tahun_akademik', e.tahun_akademik, 'semester', e.semester,
        'kode_mk', e.kode_mk, 'refleksi', e.rps_sesuai is not null))
      from public.evaluasi_mk e
      where exists (select 1 from public.ref_mata_kuliah m where upper(m.kode) = upper(e.kode_mk)
                      and public.boleh_portofolio_baca(e.tahun_akademik, e.semester, m.kurikulum, m.kode))), '[]'::jsonb))
$$;

CREATE FUNCTION public.portofolio_url(p_id bigint) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare b public.portofolio_berkas;
begin
  select * into b from public.portofolio_berkas where id = p_id;
  if b.id is null or not public.boleh_portofolio_baca(b.tahun_akademik, b.semester, b.kurikulum, b.kode_mk) then
    raise exception 'Berkas portofolio tidak ditemukan atau Anda tidak berhak membukanya.'; end if;
  return b.url;
end $$;

CREATE FUNCTION public.prestasi_belum_verifikasi(p bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.lkps_prestasi_mahasiswa r
    where r.id = p and r.status <> 'terverifikasi')
$$;

CREATE FUNCTION public.prestasi_milik(p bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.lkps_prestasi_mahasiswa r
    where r.id = p and (r.dilaporkan_oleh = public.me() or public.nidn_saya() = any(r.pembimbing)))
$$;

CREATE FUNCTION public.prestasi_mirip(p_tahun integer) RETURNS TABLE(id bigint, nama_kegiatan text, capaian text, tingkat text, status text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select r.id, r.nama_kegiatan, r.capaian, r.tingkat, r.status
    from public.lkps_prestasi_mahasiswa r
   where public.me() is not null and r.tahun = p_tahun and r.status <> 'ditolak'
$$;

CREATE FUNCTION public.rapat_baca(r bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.me() is not null and exists (select 1 from public.rapat x where x.id = r and (
    not x.terbatas or x.dibuat_oleh = public.me() or public.lihat_semua_hibah()
    or exists (select 1 from public.rapat_peserta p where p.rapat_id = r and p.dosen_id = public.me())
    or exists (select 1 from public.rapat_tindak t where t.rapat_id = r and t.pj_dosen_id = public.me())))
$$;

CREATE FUNCTION public.rapat_buka_hadir(p_token text) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select jsonb_build_object('judul', r.judul, 'tanggal', r.tanggal, 'tempat', r.tempat, 'sampai', r.hadir_sampai,
    'jumlah', (select count(*) from public.rapat_peserta p where p.rapat_id = r.id and p.hadir),
    'dosen', coalesce((select jsonb_agg(jsonb_build_object('id', d.id, 'nama', d.nama) order by d.nama)
       from public.dosen d where d.aktif and d.peran <> 'asesor'), '[]'::jsonb),
    'sudah', coalesce((select jsonb_agg(p.dosen_id) from public.rapat_peserta p
       where p.rapat_id = r.id and p.dosen_id is not null and p.hadir), '[]'::jsonb))
  from public.rapat r
  where length(coalesce(p_token, '')) >= 32 and r.token_hadir = p_token and r.hadir_sampai > now()
$$;

CREATE FUNCTION public.rapat_editor(r bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.is_admin() or exists (select 1 from public.rapat x where x.id = r and x.dibuat_oleh = public.me())
$$;

CREATE FUNCTION public.rapat_hadir(p_token text, p_dosen uuid, p_nama text, p_instansi text, p_klien uuid) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  r public.rapat;
  d public.dosen;
  n text := trim(coalesce(p_nama, ''));
begin
  select * into r from public.rapat
   where length(coalesce(p_token, '')) >= 32 and token_hadir = p_token and hadir_sampai > now();
  if not found then raise exception 'Daftar hadir rapat ini tidak sedang dibuka.'; end if;
  if (select count(*) from public.rapat_peserta where rapat_id = r.id) >= 300 then
    raise exception 'Daftar hadir sudah penuh.';
  end if;
  if p_dosen is not null then
    select * into d from public.dosen where id = p_dosen and aktif and peran <> 'asesor';
    if not found then raise exception 'Nama dosen tidak dikenal.'; end if;
    if exists (select 1 from public.rapat_peserta where rapat_id = r.id and dosen_id = d.id) then
      update public.rapat_peserta set hadir = true where rapat_id = r.id and dosen_id = d.id;
      return 'sudah';
    end if;
    insert into public.rapat_peserta (rapat_id, dosen_id, nama, cara, klien)
      values (r.id, d.id, d.nama, 'daring', null);
    return 'tercatat';
  end if;
  if length(n) < 2 or length(n) > 120 then raise exception 'Isi nama lengkap.'; end if;
  if p_klien is not null and exists (select 1 from public.rapat_peserta where rapat_id = r.id and klien = p_klien) then
    return 'sudah';
  end if;
  if exists (select 1 from public.rapat_peserta where rapat_id = r.id and dosen_id is null and lower(nama) = lower(n)) then
    return 'sudah';
  end if;
  insert into public.rapat_peserta (rapat_id, nama, instansi, cara, klien)
    values (r.id, n, nullif(trim(coalesce(p_instansi, '')), ''), 'daring', p_klien);
  return 'tercatat';
end $$;

CREATE FUNCTION public.rapat_isi(p_id bigint) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when public.rapat_isi_boleh(p_id)
    then jsonb_build_object('boleh', true, 'pembahasan', (select pembahasan from public.rapat where id = p_id))
    else jsonb_build_object('boleh', false, 'pembahasan', null) end
$$;

CREATE FUNCTION public.rapat_isi_boleh(r bigint) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.rapat_baca(r) and exists (select 1 from public.rapat x where x.id = r and (
    x.status = 'final' or x.dibuat_oleh = public.me() or public.lihat_semua_hibah()
    or exists (select 1 from public.rapat_peserta p where p.rapat_id = r and p.dosen_id = public.me())
    or exists (select 1 from public.rapat_tindak t where t.rapat_id = r and t.pj_dosen_id = public.me())))
$$;

CREATE FUNCTION public.rapikan_kata_kunci(j jsonb) RETURNS text[]
    LANGUAGE plpgsql IMMUTABLE
    SET search_path TO 'public'
    AS $$
declare
  x text;
  hasil text[] := '{}';
begin
  if j is null or jsonb_typeof(j) <> 'array' then return null; end if;
  for x in select regexp_replace(trim(v), '\s+', ' ', 'g') from jsonb_array_elements_text(j) v loop
    if x <> '' and length(x) <= 60
       and not exists (select 1 from unnest(hasil) o where lower(o) = lower(x)) then
      hasil := hasil || x;
    end if;
    exit when cardinality(hasil) >= 10;
  end loop;
  return nullif(hasil, '{}');
end $$;

CREATE FUNCTION public.rapikan_tautan_lain(x jsonb) RETURNS jsonb
    LANGUAGE sql IMMUTABLE
    SET search_path TO 'public'
    AS $_$
  select case when jsonb_typeof(x) <> 'array' then null else (
    select nullif(coalesce(jsonb_agg(jsonb_build_object('label', t.label, 'url', t.url) order by t.n), '[]'::jsonb), '[]'::jsonb)
    from (
      select n, left(trim(e ->> 'label'), 60) as label, trim(e ->> 'url') as url
      from jsonb_array_elements(x) with ordinality as a(e, n)
      where jsonb_typeof(e) = 'object'
        and length(trim(coalesce(e ->> 'label', ''))) > 0
        and trim(coalesce(e ->> 'url', '')) ~ '^https://[^[:space:]]+$'
        and length(trim(e ->> 'url')) <= 500
      order by n limit 5
    ) t) end
$_$;

CREATE FUNCTION public.rapikan_topik_keahlian(j jsonb) RETURNS text[]
    LANGUAGE plpgsql STABLE
    SET search_path TO 'public'
    AS $$
declare
  x text;
  hasil text[] := '{}';
begin
  if j is null or jsonb_typeof(j) <> 'array' then return null; end if;
  for x in select upper(trim(v)) from jsonb_array_elements_text(j) v loop
    if not (x = any(hasil))
       and exists (select 1 from public.ref_topik_keahlian t where t.kode = x and t.aktif) then
      hasil := hasil || x;
    end if;
    exit when cardinality(hasil) >= 15;
  end loop;
  return nullif(hasil, '{}');
end $$;

CREATE FUNCTION public.rbk_prodi() RETURNS TABLE(tahun_akademik text, rbk numeric, rbk_lebih numeric, n_dosen integer, n_lengkap integer)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with per as (
    select b.tahun_akademik as ta, b.nidn, count(*) as n,
      sum(coalesce(b.sks_pendidikan, 0) + coalesce(b.sks_ps_lain_dalam, 0) + coalesce(b.sks_ps_lain_luar, 0)
        + coalesce(b.sks_penelitian, 0) + coalesce(b.sks_pkm, 0) + coalesce(b.sks_penunjang, 0)) as sks,
      sum(coalesce(b.sks_lebih_pendidikan, 0) + coalesce(b.sks_lebih_penelitian, 0)
        + coalesce(b.sks_lebih_pkm, 0) + coalesce(b.sks_lebih_penunjang, 0)) as lebih
    from public.lkps_bkd b join public.dosen d on d.nidn = b.nidn
    where public.me() is not null and d.dtps and d.peran <> 'asesor' and b.verifikasi = 'terverifikasi'
    group by 1, 2)
  select p.ta, round(avg(p.sks / 2), 4), round(avg((p.sks + p.lebih) / 2), 4),
         count(*)::int, (count(*) filter (where p.n = 2))::int
  from per p group by 1
$$;

CREATE FUNCTION public.rekap_evaluasi() RETURNS TABLE(tahun_akademik text, semester text, jumlah integer, ber_edom integer, rerata_edom numeric, di_bawah_ambang integer, bawah_bertindak integer, rps_terisi integer, tindak integer, tindak_selesai integer)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with amb as (select coalesce((select nilai::numeric from public.pengaturan where kunci = 'ambang_edom'), 3.00) a)
  select e.tahun_akademik, e.semester, count(*)::int, count(e.edom)::int, round(avg(e.edom), 2),
         count(*) filter (where e.edom < (select a from amb))::int,
         count(*) filter (where e.edom < (select a from amb)
           and exists (select 1 from public.evaluasi_tindak t where t.evaluasi_id = e.id))::int,
         count(e.rps_sesuai)::int,
         coalesce(sum((select count(*) from public.evaluasi_tindak t where t.evaluasi_id = e.id)), 0)::int,
         coalesce(sum((select count(*) from public.evaluasi_tindak t where t.evaluasi_id = e.id and t.status = 'selesai')), 0)::int
  from public.evaluasi_mk e
  where public.me() is not null
  group by 1, 2 order by 1 desc, 2 desc;
$$;

CREATE FUNCTION public.rps_ajukan(p_kurikulum text, p_kode text, p_catatan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r mk_rps; v_catatan text := nullif(btrim(coalesce(p_catatan, '')), '');
begin
  if not boleh_rps(p_kurikulum, p_kode) then raise exception 'RPS diajukan koordinator MK atau dosen pengampu MK ini.'; end if;
  select * into r from mk_rps where kurikulum = p_kurikulum and kode_mk = p_kode for update;
  if r.kode_mk is null then raise exception 'Simpan RPS dulu.'; end if;
  if r.status = 'diajukan' then raise exception 'RPS sudah diajukan; menunggu pemeriksaan Kaprodi.'; end if;
  if r.status = 'disahkan' then raise exception 'RPS sudah disahkan dan belum diubah.'; end if;
  if r.revisi > 0 and v_catatan is null then raise exception 'Tulis ringkasan perubahan (masuk daftar revisi RPS).'; end if;
  perform set_config('rps.fungsi', '1', true);
  update mk_rps set status = 'diajukan' where kurikulum = p_kurikulum and kode_mk = p_kode;
  insert into mk_rps_pengesahan (kurikulum, kode_mk, aksi, oleh_id, oleh_nama, catatan, revisi)
  values (p_kurikulum, p_kode, 'ajukan', me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), left(v_catatan, 2000), r.revisi);
  return 'diajukan';
end $$;

CREATE FUNCTION public.rps_b_berubah() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if tg_op = 'UPDATE' and new.data is not distinct from old.data then return null; end if;
  update mk_rps set status = 'draf'
   where kurikulum = new.kurikulum and kode_mk = new.kode_mk and status = 'disahkan'
     and (sah -> 'struktur') is distinct from new.data;
  return null;
end $$;

CREATE FUNCTION public.rps_boleh_saya() RETURNS TABLE(kurikulum text, kode_mk text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select m.kurikulum, m.kode from public.ref_mata_kuliah m where public.boleh_rps(m.kurikulum, m.kode)
$$;

CREATE FUNCTION public.rps_dokumen(p_kode uuid) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select jsonb_build_object(
    'mk', (select jsonb_build_object('kurikulum', m.kurikulum, 'kode', m.kode, 'nama', m.nama, 'sks', m.sks, 'sks_kuliah', m.sks_kuliah,
             'sks_praktikum', m.sks_praktikum, 'semester', m.semester, 'sifat', m.sifat, 'capstone', m.capstone)
           from ref_mata_kuliah m where m.kurikulum = r.kurikulum and m.kode = r.kode_mk),
    'rps', jsonb_build_object('status', r.status, 'revisi', r.revisi, 'sah', r.sah, 'sah_pada', r.sah_pada, 'sah_oleh', r.sah_oleh,
             'sah_atas_nama', r.sah_atas_nama, 'tetap_pada', r.tetap_pada, 'tetap_oleh', r.tetap_oleh, 'tetap_atas_nama', r.tetap_atas_nama,
             'kode_verifikasi', r.kode_verifikasi),
    'log', (select coalesce(jsonb_agg(jsonb_build_object('aksi', l.aksi, 'waktu', l.waktu, 'oleh_id', l.oleh_id, 'oleh_nama', l.oleh_nama,
             'catatan', l.catatan, 'revisi', l.revisi) order by l.id), '[]'::jsonb)
           from mk_rps_pengesahan l where l.kurikulum = r.kurikulum and l.kode_mk = r.kode_mk and l.aksi in ('ajukan', 'sahkan', 'tetapkan')
             and l.waktu <= coalesce(r.tetap_pada, r.sah_pada)),
    'dosen', (select coalesce(jsonb_agg(jsonb_build_object('id', d.id, 'nama', d.nama, 'nama_gelar', d.nama_gelar, 'nip', d.nip)), '[]'::jsonb)
           from dosen d where d.id::text in (r.sah -> 'rps' ->> 'pengembang', r.sah_oleh::text, r.sah_atas_nama::text, r.tetap_oleh::text,
             r.tetap_atas_nama::text)),
    'cpl', (select coalesce(jsonb_agg(jsonb_build_object('kurikulum', c.kurikulum, 'kode', c.kode, 'rumusan', c.rumusan, 'indikator', c.indikator,
             'urutan', c.urutan)), '[]'::jsonb) from ref_cpl c where c.kurikulum = r.kurikulum),
    'peta_cpl', (select coalesce(jsonb_agg(jsonb_build_object('kurikulum', p.kurikulum, 'kode_mk', p.kode_mk, 'cpl', p.cpl, 'indikator', p.indikator)),
             '[]'::jsonb) from ref_mk_cpl p where p.kurikulum = r.kurikulum and p.kode_mk = r.kode_mk),
    'sebutan', jsonb_build_object('kaprodi', sebutan_pada(r.sah_atas_nama, 'kaprodi', r.sah_pada),
             'dekan', case when r.tetap_pada is null then null else sebutan_pada(r.tetap_atas_nama, 'dekan', r.tetap_pada) end),
    'tanggal', jsonb_build_object('ganjil', (select nilai from pengaturan where kunci = 'rps_tanggal_ganjil'),
             'genap', (select nilai from pengaturan where kunci = 'rps_tanggal_genap')),
    'dekan_aktif', pejabat_aktif('dekan') is not null)
  from mk_rps r where r.kode_verifikasi = p_kode and r.sah is not null
$$;

CREATE FUNCTION public.rps_pasang_tautan(p_kurikulum text, p_kode text, p_situs text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare r mk_rps;
begin
  if not (koordinator_aktif('kaprodi') or koordinator_aktif('dekan') or is_admin()) then
    raise exception 'Tautan dokumen RPS dipasang Kaprodi, Dekan, atau admin.'; end if;
  if coalesce(p_situs, '') !~ '^https://\S+/$' then raise exception 'Alamat situs tidak sah (harus https://.../).'; end if;
  select * into r from mk_rps where kurikulum = p_kurikulum and kode_mk = p_kode;
  if r.kode_mk is null or r.status <> 'disahkan' or r.kode_verifikasi is null then return 'belum_disahkan'; end if;
  if r.tetap_pada is null and pejabat_aktif('dekan') is not null then return 'menunggu_dekan'; end if;
  update ref_mata_kuliah set rps_url = p_situs || 'verifikasi-rps.html?k=' || r.kode_verifikasi, rps_ada = true,
         oleh = coalesce(auth.jwt() ->> 'email', oleh), diperbarui = now()
   where kurikulum = p_kurikulum and kode = p_kode;
  return 'terpasang';
end $_$;

CREATE FUNCTION public.rps_putuskan(p_kurikulum text, p_kode text, p_aksi text, p_catatan text DEFAULT NULL::text, p_url text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare r mk_rps; v_catatan text := nullif(btrim(coalesce(p_catatan, '')), ''); v_url text := nullif(btrim(coalesce(p_url, '')), '');
  v_sendiri boolean; v_kaprodi uuid := pejabat_aktif('kaprodi');
begin
  if not (koordinator_aktif('kaprodi') or is_admin()) then
    raise exception 'RPS diperiksa dan disahkan Kaprodi aktif atau admin atas nama Kaprodi (Penugasan koordinator).'; end if;
  if v_kaprodi is null then raise exception 'Kaprodi aktif belum ditetapkan (Admin › Penugasan koordinator).'; end if;
  select * into r from mk_rps where kurikulum = p_kurikulum and kode_mk = p_kode for update;
  if r.kode_mk is null or r.status <> 'diajukan' then raise exception 'RPS tidak sedang diajukan.'; end if;
  if p_aksi not in ('sahkan', 'kembalikan') then raise exception 'Aksi tidak dikenal.'; end if;
  if p_aksi = 'kembalikan' and v_catatan is null then raise exception 'Tulis catatan untuk dosen.'; end if;
  if v_url is not null and v_url !~* '^https://\S+$' then raise exception 'Tautan RPS harus diawali https://'; end if;
  -- 114: Kaprodi yang juga penyusun ditandai (dihitung terhadap Kaprodi tercantum, bukan pelaku admin).
  --      Kaprodi sendiri: boleh_rps (koordinator MK/pengampu, sama dengan 114); admin a.n.: pengampu MK memuat NIDN Kaprodi.
  v_sendiri := case when me() = v_kaprodi then boleh_rps(p_kurikulum, p_kode)
                    else coalesce((select (m.pengampu @> array[(select nidn from dosen where id = v_kaprodi)]) from ref_mata_kuliah m
                                    where m.kurikulum = p_kurikulum and m.kode = p_kode), false) end
            or coalesce((select l.oleh_id = v_kaprodi from mk_rps_pengesahan l
                          where l.kurikulum = p_kurikulum and l.kode_mk = p_kode and l.aksi = 'ajukan' order by l.id desc limit 1), false);
  perform set_config('rps.fungsi', '1', true);
  if p_aksi = 'kembalikan' then
    update mk_rps set status = 'dikembalikan' where kurikulum = p_kurikulum and kode_mk = p_kode;
  else
    update mk_rps set status = 'disahkan', revisi = r.revisi + 1, sah_pada = now(), sah_oleh = me(), sah_atas_nama = v_kaprodi,
           tetap_pada = null, tetap_oleh = null, tetap_atas_nama = null, kode_verifikasi = gen_random_uuid(),
           sah = jsonb_build_object('rps', r.data, 'struktur', (select s.data from mk_struktur s where s.kurikulum = p_kurikulum and s.kode_mk = p_kode),
                               'kaprodi_penyusun', v_sendiri)
     where kurikulum = p_kurikulum and kode_mk = p_kode;
    update ref_mata_kuliah set rps_ada = true, rps_9_komponen = true,
           oleh = coalesce(auth.jwt() ->> 'email', oleh), diperbarui = now()
     where kurikulum = p_kurikulum and kode = p_kode;
  end if;
  insert into mk_rps_pengesahan (kurikulum, kode_mk, aksi, oleh_id, oleh_nama, catatan, revisi, penyusun_sendiri, atas_nama_id, atas_nama_nama)
  values (p_kurikulum, p_kode, p_aksi, me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), left(v_catatan, 2000),
          case when p_aksi = 'sahkan' then r.revisi + 1 else r.revisi end, p_aksi = 'sahkan' and v_sendiri,
          v_kaprodi, (select coalesce(nama_gelar, nama) from dosen where id = v_kaprodi));
  return case when p_aksi = 'sahkan' then 'disahkan' else 'dikembalikan' end;
end $_$;

CREATE FUNCTION public.rps_review_batal(p_kurikulum text, p_kode text, p_dosen uuid) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not (koordinator_aktif('kaprodi') or is_admin()) then
    raise exception 'Penunjukan reviewer diubah Kaprodi aktif atau admin.'; end if;
  if exists (select 1 from mk_rps_review where kurikulum = p_kurikulum and kode_mk = p_kode and reviewer_id = p_dosen
               and kirim_pada is not null) then
    raise exception 'Review sudah dikirim; penunjukan tidak dapat dibatalkan.'; end if;
  delete from mk_rps_review where kurikulum = p_kurikulum and kode_mk = p_kode and reviewer_id = p_dosen;
  return 'dibatalkan';
end $$;

CREATE FUNCTION public.rps_review_hari() RETURNS integer
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce((select nilai::int from pengaturan where kunci = 'rps_review_hari' and nilai > 0 and nilai <= 365), 14)
$$;

CREATE FUNCTION public.rps_review_mk(p_kurikulum text, p_kode text) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when me() is null then '[]'::jsonb else coalesce(jsonb_agg(jsonb_build_object(
      'reviewer_id', v.reviewer_id, 'nama', coalesce(d.nama_gelar, d.nama), 'saya', v.reviewer_id = me(),
      'ditunjuk_pada', v.ditunjuk_pada, 'kirim_pada', v.kirim_pada, 'diperbarui', v.diperbarui, 'revisi', v.revisi,
      'dikabari_pada', v.dikabari_pada,
      'tenggat', ((v.ditunjuk_pada at time zone 'Asia/Jakarta')::date + rps_review_hari())::text,
      'sama', v.sidik is not null and v.sidik = (select md5(r.data::text) from mk_rps r where r.kurikulum = v.kurikulum and r.kode_mk = v.kode_mk),
      'kesimpulan', case when v.kirim_pada is not null or v.reviewer_id = me() then v.kesimpulan end,
      'skor', case when v.kirim_pada is not null or v.reviewer_id = me() then v.skor end,
      'catatan', case when v.kirim_pada is not null or v.reviewer_id = me() then v.catatan end,
      'umum', case when v.kirim_pada is not null or v.reviewer_id = me() then v.umum end,
      'tanggapan', case when v.kirim_pada is not null then v.tanggapan end,
      'tanggapan_umum', case when v.kirim_pada is not null then v.tanggapan_umum end,
      'tanggapan_pada', v.tanggapan_pada,
      'tanggapan_oleh', (select coalesce(t.nama_gelar, t.nama) from dosen t where t.id = v.tanggapan_oleh))
      order by v.ditunjuk_pada), '[]'::jsonb) end
    from mk_rps_review v join dosen d on d.id = v.reviewer_id
   where v.kurikulum = p_kurikulum and v.kode_mk = p_kode
$$;

CREATE FUNCTION public.rps_review_rekap() RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when me() is null then '[]'::jsonb else coalesce((select jsonb_agg(jsonb_build_object(
      'kurikulum', x.kurikulum, 'kode_mk', x.kode_mk, 'ditunjuk', x.n, 'terkirim', x.k, 'kesimpulan', x.kes, 'rerata', x.rr, 'ditanggapi', x.t))
    from (select v.kurikulum, v.kode_mk, count(*) as n, count(v.kirim_pada) as k,
                 coalesce(jsonb_agg(v.kesimpulan) filter (where v.kirim_pada is not null), '[]'::jsonb) as kes,
                 round(avg((select avg(e.value::numeric) from jsonb_each_text(v.skor) e)) filter (where v.kirim_pada is not null), 2) as rr,
                 count(*) filter (where v.kirim_pada is not null and v.tanggapan_pada >= v.kirim_pada) as t
            from mk_rps_review v group by v.kurikulum, v.kode_mk) x), '[]'::jsonb) end
$$;

CREATE FUNCTION public.rps_review_simpan(p_kurikulum text, p_kode text, p_skor jsonb, p_catatan jsonb, p_umum text, p_kesimpulan text, p_kirim boolean) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r mk_rps;
begin
  if not exists (select 1 from mk_rps_review where kurikulum = p_kurikulum and kode_mk = p_kode and reviewer_id = me()) then
    raise exception 'Anda tidak ditunjuk sebagai reviewer RPS ini.'; end if;
  if jsonb_typeof(coalesce(p_skor, '{}')) <> 'object' or exists (select 1 from jsonb_each(coalesce(p_skor, '{}')) e
       where jsonb_typeof(e.value) <> 'number' or (e.value)::text not in ('1', '2', '3', '4')) then
    raise exception 'Skor tiap butir harus 1, 2, 3, atau 4.'; end if;
  if jsonb_typeof(coalesce(p_catatan, '{}')) <> 'object' or exists (select 1 from jsonb_each(coalesce(p_catatan, '{}')) e
       where jsonb_typeof(e.value) <> 'string') then
    raise exception 'Catatan per butir harus teks.'; end if;
  select * into r from mk_rps where kurikulum = p_kurikulum and kode_mk = p_kode;
  if p_kirim then
    if r.kode_mk is null then raise exception 'RPS MK ini belum diisi; belum ada yang direview.'; end if;
    if p_kesimpulan is null then raise exception 'Pilih kesimpulan review sebelum mengirim.'; end if;
    if coalesce(p_skor, '{}') = '{}'::jsonb then raise exception 'Isi skor butir penilaian sebelum mengirim.'; end if;
  end if;
  update mk_rps_review set skor = coalesce(p_skor, '{}'), catatan = coalesce(p_catatan, '{}'), umum = nullif(btrim(p_umum), ''),
         kesimpulan = p_kesimpulan, diperbarui = now(),
         kirim_pada = case when p_kirim then now() else kirim_pada end,
         revisi = case when p_kirim then r.revisi else revisi end,
         sidik = case when p_kirim then md5(r.data::text) else sidik end
   where kurikulum = p_kurikulum and kode_mk = p_kode and reviewer_id = me();
  return case when p_kirim then 'dikirim' else 'disimpan' end;
end $$;

CREATE FUNCTION public.rps_review_tanggapi(p_kurikulum text, p_kode text, p_reviewer uuid, p_tanggapan jsonb, p_umum text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not boleh_rps(p_kurikulum, p_kode) then
    raise exception 'Review ditanggapi dosen penyusun RPS ini (koordinator MK atau dosen pengampu).'; end if;
  if not exists (select 1 from mk_rps_review where kurikulum = p_kurikulum and kode_mk = p_kode and reviewer_id = p_reviewer
                   and kirim_pada is not null) then
    raise exception 'Review ini belum dikirim reviewer.'; end if;
  if jsonb_typeof(coalesce(p_tanggapan, '{}')) <> 'object' or exists (select 1 from jsonb_each(coalesce(p_tanggapan, '{}')) e
       where jsonb_typeof(e.value) <> 'object'
          or coalesce(e.value ->> 'status', '') not in ('diperbaiki', 'sebagian', 'tidak_diubah')
          or jsonb_typeof(coalesce(e.value -> 'teks', '""')) <> 'string') then
    raise exception 'Tanggapan tiap butir: status diperbaiki, sebagian, atau tidak_diubah, dengan uraian teks.'; end if;
  update mk_rps_review set tanggapan = coalesce(p_tanggapan, '{}'), tanggapan_umum = nullif(btrim(p_umum), ''),
         tanggapan_pada = now(), tanggapan_oleh = me()
   where kurikulum = p_kurikulum and kode_mk = p_kode and reviewer_id = p_reviewer;
  return 'ditanggapi';
end $$;

CREATE FUNCTION public.rps_review_tunjuk(p_kurikulum text, p_kode text, p_dosen uuid) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not (koordinator_aktif('kaprodi') or is_admin()) then
    raise exception 'Reviewer RPS ditunjuk Kaprodi aktif atau admin.'; end if;
  if not exists (select 1 from ref_mata_kuliah where kurikulum = p_kurikulum and kode = p_kode) then
    raise exception 'Mata kuliah % % tidak ada.', p_kurikulum, p_kode; end if;
  if not exists (select 1 from dosen where id = p_dosen) then raise exception 'Dosen tidak dikenal.'; end if;
  if exists (select 1 from mk_rps where kurikulum = p_kurikulum and kode_mk = p_kode and data ->> 'pengembang' = p_dosen::text) then
    raise exception 'Dosen pengembang RPS ini tidak dapat menjadi reviewernya.'; end if;
  insert into mk_rps_review (kurikulum, kode_mk, reviewer_id, ditunjuk_oleh)
  values (p_kurikulum, p_kode, p_dosen, me()) on conflict (kurikulum, kode_mk, reviewer_id) do nothing;
  return 'ditunjuk';
end $$;

CREATE FUNCTION public.rps_review_undangan(p_kurikulum text, p_kode text, p_reviewer uuid) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v mk_rps_review; d dosen; nm text;
begin
  if not (koordinator_aktif('kaprodi') or is_admin()) then
    raise exception 'Email undangan reviewer dikirim Kaprodi aktif atau admin.'; end if;
  select * into v from mk_rps_review where kurikulum = p_kurikulum and kode_mk = p_kode and reviewer_id = p_reviewer;
  if v.id is null then raise exception 'Dosen ini tidak ditunjuk sebagai reviewer RPS ini.'; end if;
  if v.kirim_pada is not null then raise exception 'Review sudah dikirim; undangan tidak perlu dikirim lagi.'; end if;
  select * into d from dosen where id = p_reviewer;
  if coalesce(btrim(d.email), '') = '' then raise exception 'Reviewer belum punya email di data dosen.'; end if;
  select m.nama into nm from ref_mata_kuliah m where m.kurikulum = p_kurikulum and m.kode = p_kode;
  update mk_rps_review set dikabari_pada = now() where id = v.id;
  return jsonb_build_object('email', d.email, 'nama', coalesce(d.nama_gelar, d.nama), 'kurikulum', p_kurikulum, 'kode_mk', p_kode,
    'nama_mk', nm, 'tenggat', ((v.ditunjuk_pada at time zone 'Asia/Jakarta')::date + rps_review_hari())::text,
    'penunjuk', (select coalesce(x.nama_gelar, x.nama) from dosen x where x.id = me()));
end $$;

CREATE FUNCTION public.rps_tetapkan(p_kurikulum text, p_kode text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r mk_rps; v_dekan uuid := pejabat_aktif('dekan');
begin
  if not (koordinator_aktif('dekan') or is_admin()) then
    raise exception 'RPS ditetapkan Dekan aktif atau admin atas nama Dekan (Penugasan koordinator).'; end if;
  if v_dekan is null then raise exception 'Dekan aktif belum ditetapkan (Admin › Penugasan koordinator).'; end if;
  select * into r from mk_rps where kurikulum = p_kurikulum and kode_mk = p_kode for update;
  if r.kode_mk is null or r.status <> 'disahkan' then raise exception 'RPS belum disahkan Kaprodi.'; end if;
  if r.tetap_pada is not null then raise exception 'RPS ini sudah ditetapkan.'; end if;
  perform set_config('rps.fungsi', '1', true);
  update mk_rps set tetap_pada = now(), tetap_oleh = me(), tetap_atas_nama = v_dekan,
         kode_verifikasi = coalesce(kode_verifikasi, gen_random_uuid())
   where kurikulum = p_kurikulum and kode_mk = p_kode;
  insert into mk_rps_pengesahan (kurikulum, kode_mk, aksi, oleh_id, oleh_nama, revisi, atas_nama_id, atas_nama_nama)
  values (p_kurikulum, p_kode, 'tetapkan', me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), r.revisi,
          v_dekan, (select coalesce(nama_gelar, nama) from dosen where id = v_dekan));
  return 'ditetapkan';
end $$;

CREATE FUNCTION public.rps_unggah_ttd(p_kurikulum text, p_kode text, p_url text, p_nama text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare r mk_rps; v_url text := nullif(btrim(coalesce(p_url, '')), '');
begin
  if not (boleh_rps(p_kurikulum, p_kode) or is_admin()) then
    raise exception 'RPS bertanda tangan Dekan diunggah koordinator MK, dosen pengampu MK ini, atau admin prodi.'; end if;
  if v_url is null or v_url !~* '^https://\S+$' then raise exception 'Tautan berkas harus diawali https://'; end if;
  if not exists (select 1 from ref_mata_kuliah where kurikulum = p_kurikulum and kode = p_kode) then raise exception 'Mata kuliah tidak ditemukan.'; end if;
  select * into r from mk_rps where kurikulum = p_kurikulum and kode_mk = p_kode;
  if r.kode_mk is not null and r.revisi = 0 then raise exception 'RPS di situs belum disahkan Kaprodi; unggah setelah disahkan dan ditandatangani Dekan.'; end if;
  insert into mk_rps_ttd (kurikulum, kode_mk, url, nama, revisi, oleh)
  values (p_kurikulum, p_kode, v_url, left(nullif(btrim(coalesce(p_nama, '')), ''), 200), r.revisi, auth.jwt() ->> 'email');
  update ref_mata_kuliah set rps_url = v_url, rps_ada = true, oleh = coalesce(auth.jwt() ->> 'email', oleh), diperbarui = now()
   where kurikulum = p_kurikulum and kode = p_kode;
  return 'ok';
end $_$;

CREATE FUNCTION public.rps_verifikasi(p_kode uuid) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce((
    select jsonb_build_object(
      'ditemukan', true, 'kurikulum', r.kurikulum, 'kode_mk', r.kode_mk,
      'nama_mk', (select m.nama from ref_mata_kuliah m where m.kurikulum = r.kurikulum and m.kode = r.kode_mk),
      'revisi', r.revisi, 'status', r.status, 'berlaku', r.status = 'disahkan',
      'sidik', md5(coalesce(r.sah::text, '')),
      'diajukan', (select jsonb_build_object('nama', l.oleh_nama, 'waktu', l.waktu) from mk_rps_pengesahan l
                    where l.kurikulum = r.kurikulum and l.kode_mk = r.kode_mk and l.aksi = 'ajukan' and l.waktu <= r.sah_pada
                    order by l.id desc limit 1),
      'disahkan', jsonb_build_object('waktu', r.sah_pada,
                    'atas_nama', (select coalesce(d.nama_gelar, d.nama) from dosen d where d.id = r.sah_atas_nama),
                    'sebutan', sebutan_pada(r.sah_atas_nama, 'kaprodi', r.sah_pada),
                    'oleh', (select coalesce(d.nama_gelar, d.nama) from dosen d where d.id = r.sah_oleh),
                    'diwakilkan', r.sah_oleh is distinct from r.sah_atas_nama),
      'ditetapkan', case when r.tetap_pada is null then null else jsonb_build_object('waktu', r.tetap_pada,
                    'atas_nama', (select coalesce(d.nama_gelar, d.nama) from dosen d where d.id = r.tetap_atas_nama),
                    'sebutan', sebutan_pada(r.tetap_atas_nama, 'dekan', r.tetap_pada),
                    'oleh', (select coalesce(d.nama_gelar, d.nama) from dosen d where d.id = r.tetap_oleh),
                    'diwakilkan', r.tetap_oleh is distinct from r.tetap_atas_nama) end)
      from mk_rps r where r.kode_verifikasi = p_kode), jsonb_build_object('ditemukan', false))
$$;

CREATE FUNCTION public.satukan_berkas(simpan text, buang text[]) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  k bigint; d bigint; n integer := 0; m integer;
begin
  if not public.is_admin() then raise exception 'Hanya admin.'; end if;
  if simpan is null or simpan !~* '^https?://' then raise exception 'Tautan yang dipertahankan tidak sah.'; end if;
  buang := array_remove(coalesce(buang, '{}'), simpan);
  if cardinality(buang) = 0 then return 0; end if;

  -- Catatan pustaka yang dipertahankan: yang sudah memakai `simpan`, yang paling lama.
  select id into k from public.dokumen where url = simpan order by id limit 1;
  for d in select id from public.dokumen
            where (url = any(buang) or url = simpan) and id is distinct from k order by id loop
    if k is null then
      update public.dokumen set url = simpan where id = d;
      k := d; n := n + 1;
      continue;
    end if;
    delete from public.lkps_bukti a where a.dokumen_id = d and exists (
      select 1 from public.lkps_bukti b where b.dokumen_id = k and b.tabel = a.tabel and b.baris_id = a.baris_id);
    update public.lkps_bukti set dokumen_id = k where dokumen_id = d;
    delete from public.butir_bukti a where a.dokumen_id = d and exists (
      select 1 from public.butir_bukti b where b.dokumen_id = k and b.butir = a.butir);
    update public.butir_bukti set dokumen_id = k where dokumen_id = d;
    update public.lkps_spmi_ppepp set dokumen_id = k             where dokumen_id = d;
    update public.lkps_spmi_ppepp set audit_dokumen_id = k       where audit_dokumen_id = d;
    update public.lkps_spmi_ppepp set rtm_dokumen_id = k         where rtm_dokumen_id = d;
    update public.lkps_spmi_ppepp set peningkatan_dokumen_id = k where peningkatan_dokumen_id = d;
    delete from public.dokumen where id = d;
    n := n + 1;
  end loop;

  update public.butir_bukti set url = simpan where url = any(buang); get diagnostics m = row_count; n := n + m;
  update public.karya_bukti set url = simpan where url = any(buang); get diagnostics m = row_count; n := n + m;
  update public.lkps_bukti  set url = simpan where url = any(buang); get diagnostics m = row_count; n := n + m;
  update public.karya set bukti_url = simpan where bukti_url = any(buang); get diagnostics m = row_count; n := n + m;
  return n;
end $$;

CREATE FUNCTION public.saya_dtps() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce((select d.dtps from public.dosen d where d.id = public.me()), false)
$$;

CREATE FUNCTION public.sebutan_pada(p_dosen uuid, p_jabatan text, p_waktu timestamp with time zone) RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select nullif(btrim(k.sebutan), '') from koordinator k
   where k.dosen_id = p_dosen and k.jabatan = p_jabatan and k.mulai <= p_waktu::date and (k.selesai is null or k.selesai >= p_waktu::date)
   order by k.mulai desc limit 1
$$;

CREATE FUNCTION public.semester_akhir(p_ts integer, p_sm text) RETURNS date
    LANGUAGE sql IMMUTABLE
    AS $$
  select case p_sm when 'Ganjil' then make_date(p_ts, 3, 1) when 'Genap' then make_date(p_ts, 9, 1) end
$$;

CREATE FUNCTION public.semester_awal(p_ts integer, p_sm text) RETURNS date
    LANGUAGE sql IMMUTABLE
    AS $$
  select case p_sm when 'Ganjil' then make_date(p_ts - 1, 9, 1) when 'Genap' then make_date(p_ts, 3, 1) end
$$;

CREATE FUNCTION public.semester_kini_urut() RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  select case when extract(month from current_date) >= 9 then extract(year from current_date)::int * 10 + 1
              when extract(month from current_date) <= 2 then (extract(year from current_date)::int - 1) * 10 + 1
              else (extract(year from current_date)::int - 1) * 10 + 2 end
$$;

CREATE FUNCTION public.semester_tanggal(d date) RETURNS TABLE(ta text, sm text)
    LANGUAGE sql IMMUTABLE
    AS $$
  select case when extract(month from d) >= 9 then extract(year from d)::int || '/' || (extract(year from d)::int + 1)
              else (extract(year from d)::int - 1) || '/' || extract(year from d)::int end,
         case when extract(month from d) >= 9 or extract(month from d) <= 2 then 'Ganjil' else 'Genap' end
$$;

CREATE FUNCTION public.semester_urut(p_ta text, p_sm text) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $$
  select split_part(p_ta, '/', 1)::int * 10 + case p_sm when 'Ganjil' then 1 when 'Genap' then 2 else 3 end
$$;

CREATE FUNCTION public.setujui_ajuan_bkd(a bigint) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  boleh constant text[] := array['sks_pendidikan', 'sks_ps_lain_dalam', 'sks_ps_lain_luar', 'sks_penelitian',
    'sks_pkm', 'sks_penunjang', 'sks_lebih_pendidikan', 'sks_lebih_penelitian', 'sks_lebih_pkm',
    'sks_lebih_penunjang', 'bukti_url'];
  aj    public.ajuan_bkd;
  r     public.lkps_bkd;
  kolom text[];
begin
  if not public.is_admin() then raise exception 'Hanya admin.'; end if;
  select * into aj from public.ajuan_bkd where id = a and status = 'menunggu';
  if not found then raise exception 'Ajuan tidak ditemukan atau sudah diputuskan.'; end if;
  r := jsonb_populate_record(null::public.lkps_bkd, aj.data);
  select array_agg(x) into kolom from jsonb_object_keys(aj.data) x where x = any(boleh);
  if kolom is not null then
    execute format('update public.lkps_bkd set %s, diperbarui = now() where id = $2',
      (select string_agg(format('%1$I = ($1).%1$I', c), ', ') from unnest(kolom) c))
      using r, aj.bkd_id;
  end if;
  delete from public.ajuan_bkd where id = a;
end $_$;

CREATE FUNCTION public.setujui_ajuan_prestasi(a bigint) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  boleh constant text[] := array['nama_mahasiswa', 'nim', 'nama_kegiatan', 'penyelenggara',
    'bidang', 'bulan', 'tingkat', 'capaian', 'tahun', 'pembimbing', 'tampil_nama', 'cerita'];
  aj    public.ajuan_prestasi;
  r     public.lkps_prestasi_mahasiswa;
  kolom text[];
begin
  if not public.is_admin() then raise exception 'Hanya admin.'; end if;
  select * into aj from public.ajuan_prestasi where id = a and status = 'menunggu';
  if not found then raise exception 'Ajuan tidak ditemukan atau sudah diputuskan.'; end if;

  if aj.hapus then
    delete from public.lkps_prestasi_mahasiswa where id = aj.prestasi_id;   -- bukti dan ajuan ikut terhapus
    return;
  end if;

  r := jsonb_populate_record(null::public.lkps_prestasi_mahasiswa, aj.data);
  select array_agg(x) into kolom from jsonb_object_keys(aj.data) x where x = any(boleh);
  if kolom is not null then
    execute format('update public.lkps_prestasi_mahasiswa set %s, diperbarui = now() where id = $2',
      (select string_agg(format('%1$I = ($1).%1$I', c), ', ') from unnest(kolom) c))
      using r, aj.prestasi_id;
  end if;
  delete from public.ajuan_prestasi where id = a;
end $_$;

CREATE FUNCTION public.setujui_ajuan_ubah(a bigint) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  aj public.ajuan_ubah;
  d  jsonb;
begin
  if not public.is_admin() then raise exception 'Hanya admin.'; end if;
  select * into aj from public.ajuan_ubah where id = a and status = 'menunggu';
  if not found then raise exception 'Ajuan tidak ditemukan atau sudah diputuskan.'; end if;

  if aj.jenis = 'karya' then
    perform public._terapkan_karya(aj.karya_id, aj.data);
  else
    d := aj.data;
    if d ? 'nama' and length(trim(coalesce(d ->> 'nama', ''))) = 0 then
      raise exception 'Nama tidak boleh kosong.';
    end if;
    if d ? 'riwayat_pendidikan' and jsonb_typeof(d -> 'riwayat_pendidikan') <> 'array' then
      raise exception 'Riwayat pendidikan tidak sah.';
    end if;
    if d ? 'sertifikat' and jsonb_typeof(d -> 'sertifikat') <> 'array' then
      raise exception 'Daftar sertifikat tidak sah.';
    end if;
    if d ? 'kata_kunci' and jsonb_typeof(d -> 'kata_kunci') not in ('array', 'null') then
      raise exception 'Kata kunci keahlian tidak sah.';
    end if;
    if d ? 'topik_keahlian' and jsonb_typeof(d -> 'topik_keahlian') not in ('array', 'null') then
      raise exception 'Topik keahlian tidak sah.';
    end if;
    -- 146: tautan lain
    if d ? 'tautan_lain' and jsonb_typeof(d -> 'tautan_lain') not in ('array', 'null') then
      raise exception 'Tautan lain tidak sah.';
    end if;
    update public.dosen set
      nama       = case when d ? 'nama'       then trim(d ->> 'nama')                 else nama       end,
      sinta_id   = case when d ? 'sinta_id'   then nullif(trim(d ->> 'sinta_id'), '')  else sinta_id   end,
      scopus_id  = case when d ? 'scopus_id'  then nullif(trim(d ->> 'scopus_id'), '') else scopus_id  end,
      orcid      = case when d ? 'orcid'      then nullif(trim(d ->> 'orcid'), '')     else orcid      end,
      pendidikan = case when d ? 'pendidikan' then nullif(d ->> 'pendidikan', '')      else pendidikan end,
      jabatan    = case when d ? 'jabatan'    then nullif(d ->> 'jabatan', '')         else jabatan    end,
      riwayat_pendidikan = case when d ? 'riwayat_pendidikan' then d -> 'riwayat_pendidikan' else riwayat_pendidikan end,
      bidang_keahlian = case when d ? 'bidang_keahlian' then nullif(trim(d ->> 'bidang_keahlian'), '') else bidang_keahlian end,
      perusahaan   = case when d ? 'perusahaan'   then nullif(trim(d ->> 'perusahaan'), '')   else perusahaan   end,
      nomor_serdos = case when d ? 'nomor_serdos' then nullif(trim(d ->> 'nomor_serdos'), '') else nomor_serdos end,
      sertifikat   = case when d ? 'sertifikat'   then d -> 'sertifikat'                      else sertifikat   end,
      skip         = case when d ? 'skip'         then nullif(d ->> 'skip', '')               else skip         end,
      stri         = case when d ? 'stri'         then nullif(trim(d ->> 'stri'), '')         else stri         end,
      mk_ps_lain   = case when d ? 'mk_ps_lain'   then nullif(trim(d ->> 'mk_ps_lain'), '')   else mk_ps_lain   end,
      kata_kunci   = case when d ? 'kata_kunci'   then public.rapikan_kata_kunci(d -> 'kata_kunci')   else kata_kunci   end,
      topik_keahlian = case when d ? 'topik_keahlian' then public.rapikan_topik_keahlian(d -> 'topik_keahlian') else topik_keahlian end,
      email_alternatif = case when d ? 'email_alternatif' then nullif(trim(d ->> 'email_alternatif'), '') else email_alternatif end,
      tautan_lain  = case when d ? 'tautan_lain'  then public.rapikan_tautan_lain(d -> 'tautan_lain') else tautan_lain end,   -- 146
      diubah_pada = now()
    where id = aj.dosen_id;
  end if;

  delete from public.ajuan_ubah where id = a;
end $$;

CREATE FUNCTION public.silabus_ajukan(p_kurikulum text, p_kode text, p_catatan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r mk_silabus; v_catatan text := nullif(btrim(coalesce(p_catatan, '')), ''); kurang text[];
begin
  if not boleh_silabus() then raise exception 'Silabus diajukan dosen aktif yang terdaftar.'; end if;
  select * into r from mk_silabus where kurikulum = p_kurikulum and kode_mk = p_kode for update;
  if r.kode_mk is null then raise exception 'Simpan silabus dulu.'; end if;
  if r.status = 'diajukan' then raise exception 'Silabus sudah diajukan; menunggu Kaprodi.'; end if;
  if r.status = 'disahkan' then raise exception 'Silabus sudah disahkan dan belum diubah.'; end if;
  select array_agg(n order by o) into kurang from (values (1, 'nama_en', 'nama MK (Inggris)'), (2, 'tujuan', 'tujuan umum'),
      (3, 'tujuan_en', 'tujuan umum (Inggris)'), (4, 'deskripsi', 'deskripsi'), (5, 'deskripsi_en', 'deskripsi (Inggris)'),
      (6, 'pustaka', 'pustaka')) t(o, k, n)
   where coalesce(r.data ->> k, '') = '';
  if kurang is not null then raise exception 'Lengkapi dulu: %.', array_to_string(kurang, ', '); end if;
  if coalesce(r.data ->> 'catatan_impor', '') <> '' then
    raise exception 'Periksa isi awal hasil impor, lalu hapus catatan impor sebelum diajukan.'; end if;
  if r.revisi > 0 and v_catatan is null then raise exception 'Tulis ringkasan perubahan dari versi yang disahkan.'; end if;
  update mk_silabus set status = 'diajukan', diperbarui = now() where kurikulum = p_kurikulum and kode_mk = p_kode;
  insert into mk_silabus_log (kurikulum, kode_mk, aksi, oleh_id, oleh_nama, catatan, revisi)
  values (p_kurikulum, p_kode, 'ajukan', me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), left(v_catatan, 2000), r.revisi);
  return 'diajukan';
end $$;

CREATE FUNCTION public.silabus_impor(p_kurikulum text, p_baris jsonb) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare b jsonb; v_kode text; masuk int := 0; ada int := 0; tidak text[] := '{}';
begin
  if not is_admin() then raise exception 'Impor silabus hanya oleh admin.'; end if;
  if p_baris is null or jsonb_typeof(p_baris) <> 'array' then raise exception 'Isi impor harus daftar silabus.'; end if;
  if jsonb_array_length(p_baris) > 300 then raise exception 'Paling banyak 300 silabus sekali impor.'; end if;
  for b in select * from jsonb_array_elements(p_baris) loop
    v_kode := btrim(coalesce(b ->> 'kode', ''));
    if not exists (select 1 from ref_mata_kuliah where kurikulum = p_kurikulum and kode = v_kode) then
      tidak := tidak || v_kode; continue; end if;
    if exists (select 1 from mk_silabus where kurikulum = p_kurikulum and kode_mk = v_kode) then ada := ada + 1; continue; end if;
    insert into mk_silabus (kurikulum, kode_mk, data, status, oleh) values (p_kurikulum, v_kode, silabus_rapikan(b -> 'data'), 'draf', auth.jwt() ->> 'email');
    insert into mk_silabus_log (kurikulum, kode_mk, aksi, oleh_id, oleh_nama, catatan)
    values (p_kurikulum, v_kode, 'impor', me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), left(b -> 'data' ->> 'catatan_impor', 2000));
    masuk := masuk + 1;
  end loop;
  return jsonb_build_object('masuk', masuk, 'sudah_ada', ada, 'tidak_ada', to_jsonb(tidak));
end $$;

CREATE FUNCTION public.silabus_putuskan(p_kurikulum text, p_kode text, p_aksi text, p_catatan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r mk_silabus; v_catatan text := nullif(btrim(coalesce(p_catatan, '')), '');
begin
  if not koordinator_aktif('kaprodi') then raise exception 'Silabus disahkan Kaprodi aktif (Penugasan koordinator).'; end if;
  if p_aksi not in ('sahkan', 'kembalikan') then raise exception 'Aksi tidak dikenal.'; end if;
  select * into r from mk_silabus where kurikulum = p_kurikulum and kode_mk = p_kode for update;
  if r.kode_mk is null or r.status <> 'diajukan' then raise exception 'Silabus tidak sedang diajukan.'; end if;
  if p_aksi = 'kembalikan' and v_catatan is null then raise exception 'Tulis catatan untuk penyusun.'; end if;
  if p_aksi = 'kembalikan' then
    update mk_silabus set status = 'dikembalikan', diperbarui = now() where kurikulum = p_kurikulum and kode_mk = p_kode;
  else
    update mk_silabus set status = 'disahkan', revisi = r.revisi + 1, sah = r.data, sah_pada = now(), sah_oleh = me(), diperbarui = now()
     where kurikulum = p_kurikulum and kode_mk = p_kode;
  end if;
  insert into mk_silabus_log (kurikulum, kode_mk, aksi, oleh_id, oleh_nama, catatan, revisi)
  values (p_kurikulum, p_kode, p_aksi, me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), left(v_catatan, 2000),
          case when p_aksi = 'sahkan' then r.revisi + 1 else r.revisi end);
  return case when p_aksi = 'sahkan' then 'disahkan' else 'dikembalikan' end;
end $$;

CREATE FUNCTION public.silabus_rapikan(p jsonb) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    SET search_path TO 'public'
    AS $$
declare k text; batas int; v text; hasil jsonb := jsonb_build_object('versi', '1');
begin
  if p is null or jsonb_typeof(p) <> 'object' then raise exception 'Isian silabus tidak sah.'; end if;
  for k, batas in select * from (values ('nama_en', 200), ('tujuan', 4000), ('tujuan_en', 4000), ('deskripsi', 8000),
      ('deskripsi_en', 8000), ('prasyarat', 500), ('bersamaan', 500), ('pustaka', 8000), ('catatan_impor', 2000)) t(k, b) loop
    v := btrim(coalesce(p ->> k, ''));
    if length(v) > batas then raise exception 'Silabus: % paling panjang % karakter.', k, batas; end if;
    hasil := hasil || jsonb_build_object(k, v);
  end loop;
  return hasil;
end $$;

CREATE FUNCTION public.silabus_simpan(p_kurikulum text, p_kode text, p_data jsonb) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r mk_silabus; d jsonb := silabus_rapikan(p_data);
begin
  if not boleh_silabus() then raise exception 'Silabus diisi dosen aktif yang terdaftar.'; end if;
  if not exists (select 1 from ref_mata_kuliah where kurikulum = p_kurikulum and kode = p_kode) then
    raise exception 'Mata kuliah % % tidak ada.', p_kurikulum, p_kode; end if;
  select * into r from mk_silabus where kurikulum = p_kurikulum and kode_mk = p_kode for update;
  if r.kode_mk is not null and r.status = 'diajukan' then raise exception 'Silabus sedang diajukan; tunggu keputusan Kaprodi.'; end if;
  if r.kode_mk is not null and r.data = d then return r.status; end if;   -- tidak berubah
  insert into mk_silabus (kurikulum, kode_mk, data, status, oleh, diperbarui)
  values (p_kurikulum, p_kode, d, 'draf', auth.jwt() ->> 'email', now())
  on conflict (kurikulum, kode_mk) do update
    set data = excluded.data, status = 'draf', oleh = excluded.oleh, diperbarui = now();
  return 'draf';
end $$;

CREATE FUNCTION public.sinkron_tim_penyusun() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if tg_op <> 'INSERT' and old.dosen_id is not null then
    update public.dosen set tim_penyusun = false where id = old.dosen_id;
  end if;
  if tg_op <> 'DELETE' and new.dosen_id is not null then
    update public.dosen set tim_penyusun = true where id = new.dosen_id;
  end if;
  return null;
end $$;

CREATE FUNCTION public.sistem_kesehatan() RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not (is_admin() or exists (select 1 from dosen d where d.id = me() and d.peran = 'pimpinan')) then
    raise exception 'Khusus admin dan pimpinan.'; end if;
  return sistem_periksa();
end;
$$;

CREATE FUNCTION public.sistem_kesehatan_kunci(p_kunci text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  return sistem_periksa() || jsonb_build_object('admin', (select coalesce(jsonb_agg(distinct lower(d.email)), '[]'::jsonb)
    from dosen d where d.peran = 'admin' and coalesce(d.email, '') like '%@%'));
end;
$$;

CREATE FUNCTION public.sistem_lapor(p_kunci text, p_status text, p_ok boolean, p_isi jsonb DEFAULT '{}'::jsonb) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  if p_status not in ('apps_script', 'ringkasan_mingguan', 'cadangan_drive') then raise exception 'Status tidak dikenal.'; end if;
  insert into status_sistem (kunci, waktu, ok, isi) values (p_status, now(), coalesce(p_ok, true), coalesce(p_isi, '{}'::jsonb))
  on conflict (kunci) do update set waktu = excluded.waktu, ok = excluded.ok, isi = excluded.isi;
  return 'ok';
end;
$$;

CREATE FUNCTION public.sistem_periksa() RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  hasil jsonb := '[]'::jsonb; r record; s status_sistem; v_status text; v_rinci text; v_kuota int; v_pakai numeric; v_batas numeric;
  v_batas_db_mb constant numeric := 500;        -- paket gratis Supabase, per proyek
  v_batas_storage_mb constant numeric := 1024;  -- paket gratis Supabase, 1 GB
  v_ambang constant numeric := 0.5;             -- perlu dicek mulai 50%
  v_db_mb numeric; v_st_mb numeric; v_besar text;
begin
  for r in select * from (values
      ('bangun_situs', 'Bangun situs (tiap jam)', interval '2 hours'),
      ('situs_terbit', 'Situs terakhir terbit (hanya bila ada perubahan)', null::interval),
      ('cadangan', 'Cadangan basis data (harian)', interval '26 hours'),
      ('jaga_hidup', 'Jaga-hidup Supabase (tiap 3 hari)', interval '4 days'),
      ('hitung_cpl', 'Hitung CPL (harian)', interval '26 hours'),
      ('apps_script', 'Pemicu Apps Script (tiap jam)', interval '2 hours'),
      ('cadangan_drive', 'Cadangan berkas Drive ke komputer prodi', interval '8 days')) as t(kunci, label, batas)
  loop
    select * into s from status_sistem where kunci = r.kunci;
    v_rinci := null;
    if s.kunci is null then v_status := case when r.batas is null then 'info' else 'belum_ada' end;
    elsif not s.ok then v_status := 'gagal';
    elsif r.batas is null then v_status := 'info';
    elsif s.waktu < now() - r.batas then v_status := 'terlambat';
    else v_status := 'baik';
    end if;
    if r.kunci = 'apps_script' and s.kunci is not null then
      v_kuota := nullif(s.isi ->> 'kuota_email', '')::int;
      v_pakai := nullif(s.isi ->> 'drive_terpakai', '')::numeric;
      v_batas := nullif(s.isi ->> 'drive_batas', '')::numeric;
      v_rinci := concat_ws(' · ',
        case when v_kuota is not null then 'sisa kuota email hari ini ' || v_kuota end,
        case when v_pakai is not null and v_batas > 0 then 'Drive ' || round(v_pakai / v_batas * 100) || '% ('
          || round(v_pakai / 1073741824, 1) || ' dari ' || round(v_batas / 1073741824, 1) || ' GB)' end);
      if v_status = 'baik' and ((v_kuota is not null and v_kuota < 20) or (v_pakai is not null and v_batas > 0 and v_pakai / v_batas > 0.9)) then
        v_status := 'perlu_dicek'; end if;
    elsif r.kunci = 'cadangan_drive' and s.kunci is not null then
      v_rinci := concat_ws(' · ', (s.isi ->> 'berkas') || ' berkas', (s.isi ->> 'megabita') || ' MB',
        case when coalesce((s.isi ->> 'baru')::int, 0) + coalesce((s.isi ->> 'berubah')::int, 0) > 0
          then 'baru/berubah ' || (coalesce((s.isi ->> 'baru')::int, 0) + coalesce((s.isi ->> 'berubah')::int, 0)) end,
        case when coalesce((s.isi ->> 'hilang')::int, 0) > 0 then 'hilang dari Drive ' || (s.isi ->> 'hilang') end,
        case when coalesce((s.isi ->> 'gagal')::int, 0) > 0 then 'gagal ' || (s.isi ->> 'gagal') end);
    elsif r.kunci = 'bangun_situs' and s.kunci is not null then
      v_rinci := case when s.isi ->> 'terbit' = 'ya' then 'terbit pada jalan terakhir' else 'tanpa perubahan pada jalan terakhir' end;
    end if;
    hasil := hasil || jsonb_build_object('kunci', r.kunci, 'label', r.label, 'waktu', s.waktu, 'status', v_status, 'rinci', v_rinci);
  end loop;

  -- 170: kapasitas paket.
  v_db_mb := round(pg_database_size(current_database()) / 1048576.0, 1);
  select relname || ' ' || round(pg_total_relation_size(relid) / 1048576.0, 1) || ' MB' into v_besar
    from pg_statio_user_tables where schemaname = 'public' order by pg_total_relation_size(relid) desc limit 1;
  hasil := hasil || jsonb_build_object('kunci', 'kapasitas_basis_data', 'label', 'Ukuran basis data (paket gratis ' || v_batas_db_mb || ' MB)',
    'waktu', now(), 'status', case when v_db_mb >= v_batas_db_mb * v_ambang then 'perlu_dicek' else 'baik' end,
    'rinci', concat_ws(' · ', v_db_mb || ' MB dari ' || v_batas_db_mb || ' MB (' || round(v_db_mb / v_batas_db_mb * 100) || '%)',
      case when v_besar is not null then 'tabel terbesar ' || v_besar end));
  if not exists (select 1 from pg_attribute where attrelid = to_regclass('storage.objects') and attname = 'metadata' and not attisdropped) then
    hasil := hasil || jsonb_build_object('kunci', 'kapasitas_storage', 'label', 'Storage berkas (paket gratis 1 GB)',
      'waktu', now(), 'status', 'info', 'rinci', 'skema storage tidak ada');
  else
    execute 'select round(coalesce(sum((metadata ->> ''size'')::bigint), 0) / 1048576.0, 1) from storage.objects' into v_st_mb;
    hasil := hasil || jsonb_build_object('kunci', 'kapasitas_storage', 'label', 'Storage berkas (paket gratis 1 GB)',
      'waktu', now(), 'status', case when v_st_mb >= v_batas_storage_mb * v_ambang then 'perlu_dicek' else 'baik' end,
      'rinci', v_st_mb || ' MB dari ' || v_batas_storage_mb || ' MB (' || round(v_st_mb / v_batas_storage_mb * 100) || '%)');
  end if;

  return jsonb_build_object('dibuat', now(), 'butir', hasil,
    'perlu_dicek', (select count(*) from jsonb_array_elements(hasil) x where x ->> 'status' not in ('baik', 'info')),
    'basis_data_mb', v_db_mb,
    'ringkasan_terakhir', (select waktu from status_sistem where kunci = 'ringkasan_mingguan'));
end;
$$;

CREATE FUNCTION public.survei_buka(p_token text) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select jsonb_build_object('judul', s.judul, 'judul_en', s.judul_en, 'kelompok', s.kelompok, 'tahun_ts', s.tahun_ts,
    'mulai', s.mulai, 'selesai', s.selesai, 'pengantar', s.pengantar, 'pengantar_en', s.pengantar_en,
    'pertanyaan', s.pertanyaan, 'identitas', s.identitas,
    'buka', (now() at time zone 'Asia/Jakarta')::date between s.mulai and s.selesai)
  from public.survei s
  where length(coalesce(p_token, '')) >= 32 and s.token = p_token and not s.dicabut
$$;

CREATE FUNCTION public.survei_kirim(p_token text, p_klien uuid, p_jawaban jsonb, p_identitas jsonb DEFAULT NULL::jsonb) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare
  s public.survei;
  q jsonb;
  v jsonb;
  jenis text;
  wajib boolean;
  aktif boolean;
  sy jsonb;
  judul text;
  hari date := (now() at time zone 'Asia/Jakarta')::date;
  nm text := nullif(btrim(coalesce(p_identitas->>'nama', '')), '');
  ni text := nullif(btrim(coalesce(p_identitas->>'nim', '')), '');
  em text := nullif(btrim(coalesce(p_identitas->>'email', '')), '');
begin
  select * into s from public.survei where length(coalesce(p_token, '')) >= 32 and token = p_token;
  if not found or s.dicabut or hari < s.mulai or hari > s.selesai then
    raise exception 'Survei ini tidak sedang dibuka.';
  end if;
  if p_klien is null or p_jawaban is null or jsonb_typeof(p_jawaban) <> 'object'
     or pg_column_size(p_jawaban) > 20000 then
    raise exception 'Isian tidak sah.';
  end if;
  if exists (select 1 from jsonb_object_keys(p_jawaban) k
             where not exists (select 1 from jsonb_array_elements(s.pertanyaan) x where x->>'id' = k)) then
    raise exception 'Isian memuat pertanyaan yang tidak ada.';
  end if;
  for q in select * from jsonb_array_elements(s.pertanyaan) loop
    jenis := coalesce(q->>'jenis', 'skala');
    judul := left(coalesce(q->>'teks', q->>'id'), 80);
    v := p_jawaban -> (q->>'id');
    if v = 'null'::jsonb then v := null; end if;
    sy := q->'syarat';
    aktif := sy is null or jsonb_typeof(sy) <> 'object' or coalesce((p_jawaban ->> (sy->>'q')) in
      (select jsonb_array_elements_text(coalesce(sy->'nilai', '[]'::jsonb))), false);
    wajib := coalesce((q->>'wajib')::boolean, jenis in ('skala', 'pilihan'));
    if not aktif then
      if v is not null then raise exception 'Pertanyaan "%" tidak berlaku untuk jawaban Anda sebelumnya.', judul; end if;
      continue;
    end if;
    if v is null or (jenis = 'centang' and jsonb_typeof(v) = 'array' and jsonb_array_length(v) = 0) then
      if wajib then raise exception 'Pertanyaan wajib belum dijawab: %', judul; end if;
      continue;
    end if;
    if jenis = 'skala' then
      if jsonb_typeof(v) <> 'number' or (v #>> '{}') not in ('1', '2', '3', '4') then
        raise exception 'Jawaban "%" harus 1–4.', judul;
      end if;
    elsif jenis = 'pilihan' then
      if jsonb_typeof(v) <> 'string' or not exists
         (select 1 from jsonb_array_elements_text(coalesce(q->'opsi', '[]'::jsonb)) o where o = v #>> '{}') then
        raise exception 'Pilihan untuk "%" tidak dikenal.', judul;
      end if;
    elsif jenis = 'centang' then
      if jsonb_typeof(v) <> 'array' or exists (select 1 from jsonb_array_elements(v) x
           where jsonb_typeof(x) <> 'string' or not exists
             (select 1 from jsonb_array_elements_text(coalesce(q->'opsi', '[]'::jsonb)) o where o = x #>> '{}')) then
        raise exception 'Pilihan untuk "%" tidak dikenal.', judul;
      end if;
    elsif jenis = 'angka' then
      if jsonb_typeof(v) <> 'number'
         or (q->>'min' is not null and (v #>> '{}')::numeric < (q->>'min')::numeric)
         or (q->>'max' is not null and (v #>> '{}')::numeric > (q->>'max')::numeric) then
        raise exception 'Angka untuk "%" di luar rentang.', judul;
      end if;
    elsif jenis = 'singkat' then
      if jsonb_typeof(v) <> 'string' or length(v #>> '{}') > 200 then
        raise exception 'Isian "%" paling panjang 200 karakter.', judul;
      end if;
    else
      if jsonb_typeof(v) <> 'string' or length(v #>> '{}') > 2000 then
        raise exception 'Isian "%" paling panjang 2000 karakter.', judul;
      end if;
    end if;
  end loop;
  if s.identitas = 'tidak' then
    nm := null; ni := null; em := null;
  elsif s.identitas = 'wajib' and (nm is null or (ni is null and em is null)) then
    raise exception 'Isi nama serta NIM atau email.';
  end if;
  if length(nm) > 120 or length(ni) > 30 or length(em) > 120
     or (em is not null and em !~* '^[^@\s]+@[^@\s]+\.[^@\s]+$') then
    raise exception 'Identitas tidak sah (periksa panjang isian dan alamat email).';
  end if;
  insert into public.survei_jawaban (survei_id, klien, jawaban, nama, nim, email)
    values (s.id, p_klien, p_jawaban, nm, ni, em);
  return true;
exception when unique_violation then
  raise exception 'Survei ini sudah Anda isi dari perangkat ini. Terima kasih.';
end
$_$;

CREATE FUNCTION public.survei_rekap() RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce(jsonb_agg(x order by (x->>'mulai') desc, (x->>'id')::bigint desc), '[]'::jsonb) from (
    select s.rekap_terbit || jsonb_build_object('id', s.id, 'judul', s.judul, 'kelompok', s.kelompok, 'tahun_ts', s.tahun_ts,
      'mulai', s.mulai, 'selesai', s.selesai, 'terbit_pada', s.terbit_pada) x
    from public.survei s
    where s.publik and s.rekap_terbit is not null and s.mulai <= (now() at time zone 'Asia/Jakarta')::date) z
$$;

CREATE FUNCTION public.survei_rekap_hitung(p_id bigint) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select jsonb_build_object(
      'n', (select count(*) from public.survei_jawaban j where j.survei_id = s.id),
      'pertanyaan', (select coalesce(jsonb_agg(jsonb_build_object('id', p->>'id', 'aspek', p->>'aspek', 'teks', p->>'teks',
                       'jenis', coalesce(p->>'jenis', 'skala'), 'opsi', p->'opsi')), '[]'::jsonb)
                     from jsonb_array_elements(s.pertanyaan) p
                     where coalesce(p->>'jenis', 'skala') in ('skala', 'pilihan', 'centang', 'angka')),
      'hitung', (select coalesce(jsonb_object_agg(t.k, t.arr), '{}'::jsonb) from (
          select e.key k, jsonb_build_array(
            count(*) filter (where e.value #>> '{}' = '1'), count(*) filter (where e.value #>> '{}' = '2'),
            count(*) filter (where e.value #>> '{}' = '3'), count(*) filter (where e.value #>> '{}' = '4')) arr
          from public.survei_jawaban j, jsonb_each(j.jawaban) e
          where j.survei_id = s.id and jsonb_typeof(e.value) = 'number'
            and e.key in (select p->>'id' from jsonb_array_elements(s.pertanyaan) p where coalesce(p->>'jenis', 'skala') = 'skala')
          group by e.key) t),
      'opsi', (select coalesce(jsonb_object_agg(u.k, u.o), '{}'::jsonb) from (
          select w.k, jsonb_object_agg(w.val, w.c) o from (
            select e.key k, v.val, count(*) c
            from public.survei_jawaban j, jsonb_each(j.jawaban) e,
              lateral (select e.value #>> '{}' val where jsonb_typeof(e.value) = 'string'
                       union all
                       select a from jsonb_array_elements_text(case when jsonb_typeof(e.value) = 'array' then e.value else '[]'::jsonb end) a) v
            where j.survei_id = s.id
              and e.key in (select p->>'id' from jsonb_array_elements(s.pertanyaan) p where p->>'jenis' in ('pilihan', 'centang'))
            group by e.key, v.val) w group by w.k) u),
      'angka', (select coalesce(jsonb_object_agg(t.k, t.arr), '{}'::jsonb) from (
          select e.key k, jsonb_build_array(count(*), round(avg((e.value #>> '{}')::numeric), 2)) arr
          from public.survei_jawaban j, jsonb_each(j.jawaban) e
          where j.survei_id = s.id and jsonb_typeof(e.value) = 'number'
            and e.key in (select p->>'id' from jsonb_array_elements(s.pertanyaan) p where p->>'jenis' = 'angka')
          group by e.key) t))
  from public.survei s where s.id = p_id
$$;

CREATE FUNCTION public.survei_tarik_terbit(p_id bigint) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not (is_admin() or boleh_mutu()) then raise exception 'Rekap survei ditarik admin atau GKM.'; end if;
  update survei set rekap_terbit = null, terbit_pada = null, terbit_oleh = null where id = p_id;
end $$;

CREATE FUNCTION public.survei_terbitkan(p_id bigint) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare r jsonb;
begin
  if not (is_admin() or boleh_mutu()) then raise exception 'Rekap survei diterbitkan admin atau GKM.'; end if;
  r := survei_rekap_hitung(p_id);
  if r is null then raise exception 'Survei tidak ada.'; end if;
  update survei set rekap_terbit = r, terbit_pada = now(), terbit_oleh = auth.jwt() ->> 'email' where id = p_id;
  return (r ->> 'n')::int;
end $$;

CREATE FUNCTION public.ta_arsip_boleh(p_nim text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select ta_bimbingan_boleh(p_nim) or exists (
    select 1 from jadwal_ta t, dosen d
     where upper(btrim(coalesce(t.nim, ''))) = upper(btrim(p_nim)) and d.id = me() and d.nidn is not null and d.nidn = any(t.pembimbing))
$$;

CREATE FUNCTION public.ta_arsip_catat(p_nim text, p_url text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $_$
declare v_nim text := upper(btrim(coalesce(p_nim, ''))); v_nama text; v_oleh text; v_lama text;
begin
  if not boleh_pengajuan('ta') then raise exception 'Arsip TA disimpan koordinator TA atau admin.'; end if;
  if ta_lulus_ta(v_nim) is null then raise exception 'Mahasiswa % belum lulus sidang akhir (atau revisinya belum selesai).', v_nim; end if;
  if coalesce(p_url, '') !~ '^https://(drive|docs)\.google\.com/\S+$' then raise exception 'Tautan arsip harus tautan Google Drive.'; end if;
  select t.nama_mahasiswa into v_nama from jadwal_ta t
   where upper(btrim(coalesce(t.nim, ''))) = v_nim and t.tahap = 'sidang_akhir' order by t.tanggal desc limit 1;
  select nama into v_oleh from dosen where id = me();
  select url into v_lama from ta_arsip where nim = v_nim;
  insert into ta_arsip (nim, nama, url, oleh) values (v_nim, v_nama, p_url, v_oleh)
  on conflict (nim) do update set nama = excluded.nama, url = excluded.url, oleh = excluded.oleh, dibuat = now();
  return v_lama;
end;
$_$;

CREATE FUNCTION public.ta_arsip_siap() RETURNS TABLE(nim text, nama text, judul text, lulus date, arsip_url text, arsip_dibuat timestamp with time zone, arsip_oleh text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with s as (
    select upper(btrim(t.nim)) as nim, (array_agg(t.nama_mahasiswa order by t.tanggal desc))[1] as nama,
           (array_agg(t.judul order by t.tanggal desc))[1] as judul
      from jadwal_ta t
     where t.nim is not null and t.tahap = 'sidang_akhir' and t.status = 'selesai'
       and (t.hasil = 'lulus' or (t.hasil = 'lulus_revisi' and t.revisi_selesai is not null))
     group by 1)
  select s.nim, s.nama, s.judul, ta_lulus_ta(s.nim), a.url, a.dibuat, a.oleh
    from s left join ta_arsip a on a.nim = s.nim
   where boleh_pengajuan('ta')
   order by 4 desc, 2
$$;

CREATE FUNCTION public.ta_arsip_url(p_nim text) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_url text;
begin
  if not ta_arsip_boleh(p_nim) then raise exception 'Arsip TA dibuka koordinator TA, admin, atau pembimbingnya.'; end if;
  select url into v_url from ta_arsip where nim = upper(btrim(p_nim));
  if v_url is null then raise exception 'Arsip TA mahasiswa ini belum disimpan.'; end if;
  return v_url;
end;
$$;

CREATE FUNCTION public.ta_atur_kuota(p_ts integer, p_sm text, p_dosen uuid, p_kuota integer) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not boleh_pengajuan('ta') then raise exception 'Kuota TA diatur koordinator TA atau admin.'; end if;
  if p_ts is null or p_ts < 2000 or p_ts > 2100 then raise exception 'TS tidak sah.'; end if;
  if p_sm is null or p_sm not in ('Ganjil', 'Genap') then raise exception 'Semester harus Ganjil atau Genap.'; end if;
  if p_kuota is not null and (p_kuota < 0 or p_kuota > 100) then raise exception 'Kuota 0 sampai 100.'; end if;
  delete from ta_kuota where ts = p_ts and semester = p_sm and dosen_id is not distinct from p_dosen;
  if p_kuota is not null then insert into ta_kuota (ts, semester, dosen_id, kuota) values (p_ts, p_sm, p_dosen, p_kuota); end if;
  return 'ok';
end;
$$;

CREATE FUNCTION public.ta_ba_buka(p_jadwal bigint, p_alasan text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare j jadwal_ta; v_alasan text := btrim(coalesce(p_alasan, '')); v_oleh text;
begin
  if not boleh_tabel('jadwal_ta') then raise exception 'Berita acara dibuka kembali oleh koordinator TA atau admin.'; end if;
  if length(v_alasan) not between 5 and 500 then raise exception 'Tulis alasan membuka kembali (5–500 huruf).'; end if;
  select * into j from jadwal_ta where id = p_jadwal for update;
  if j.id is null then raise exception 'Jadwal seminar/sidang tidak ditemukan.'; end if;
  if j.ba_ditetapkan is null then raise exception 'Berita acara seminar ini belum ditetapkan.'; end if;
  select nama into v_oleh from dosen where id = me();
  update jadwal_ta set ba_ditetapkan = null, ba_oleh = null, nilai_akhir = null, hasil = null, revisi_selesai = null,
         siup_diunggah = null, siup_oleh = null,
         ba_dibuka = to_char(now() at time zone 'Asia/Jakarta', 'YYYY-MM-DD HH24:MI') || ' WIB, ' || coalesce(v_oleh, '?') || ': ' || v_alasan,
         oleh = v_oleh, diperbarui = now()
   where id = j.id;
  return 'dibuka';
end;
$$;

CREATE FUNCTION public.ta_ba_tetapkan(p_jadwal bigint, p_hasil text DEFAULT NULL::text, p_batas_revisi date DEFAULT NULL::date, p_catatan_revisi text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare j jadwal_ta; r ta_rubrik; h jsonb; v_akhir numeric; v_hasil text; v_oleh text;
  angka constant text := 'FM990.00';
begin
  if not boleh_tabel('jadwal_ta') then raise exception 'Berita acara ditetapkan koordinator TA atau admin.'; end if;
  select * into j from jadwal_ta where id = p_jadwal for update;
  if j.id is null then raise exception 'Jadwal seminar/sidang tidak ditemukan.'; end if;
  if j.ba_ditetapkan is not null then raise exception 'Berita acara seminar ini sudah ditetapkan.'; end if;
  if j.status not in ('terjadwal', 'selesai') then
    raise exception 'Seminar/sidang ini berstatus %; ubah statusnya dulu di Data prodi.', j.status; end if;
  if not exists (select 1 from ta_nilai where jadwal_id = j.id) then raise exception 'Belum ada nilai untuk seminar ini.'; end if;
  h := ta_nilai_hitung(j.id);
  if jsonb_array_length(h -> 'kurang') > 0 then
    raise exception 'Nilai belum lengkap: % belum menilai.',
      (select string_agg((x ->> 'nama') || case when x ->> 'bagian' = 'bimbingan' then ' (proses bimbingan)' else '' end, ', ')
         from jsonb_array_elements(h -> 'kurang') x); end if;
  select * into r from ta_rubrik where id = (h ->> 'rubrik_id')::bigint;
  v_akhir := (h ->> 'nilai_akhir')::numeric;
  if v_akhir < r.batas_lulus then
    if coalesce(p_hasil, 'mengulang') <> 'mengulang' then
      raise exception 'Nilai akhir % di bawah batas lulus %: hasilnya mengulang.',
        replace(to_char(v_akhir, angka), '.', ','), replace(to_char(r.batas_lulus, angka), '.', ','); end if;
    v_hasil := 'mengulang';
  else
    if p_hasil is null or p_hasil not in ('lulus', 'lulus_revisi') then
      raise exception 'Nilai akhir % mencapai batas lulus %: pilih lulus atau lulus dengan revisi.',
        replace(to_char(v_akhir, angka), '.', ','), replace(to_char(r.batas_lulus, angka), '.', ','); end if;
    v_hasil := p_hasil;
  end if;
  if v_hasil = 'lulus_revisi' then
    if p_batas_revisi is null then raise exception 'Isi tenggat revisi.'; end if;
    if p_batas_revisi < j.tanggal then raise exception 'Tenggat revisi tidak boleh sebelum tanggal seminar.'; end if;
  end if;
  if length(coalesce(p_catatan_revisi, '')) > 2000 then raise exception 'Catatan revisi paling banyak 2000 huruf.'; end if;
  select nama into v_oleh from dosen where id = me();
  update jadwal_ta set status = 'selesai', hasil = v_hasil, nilai_akhir = v_akhir, rubrik_id = r.id,
         ba_ditetapkan = now(), ba_oleh = v_oleh, oleh = v_oleh, diperbarui = now(),
         batas_revisi = case when v_hasil = 'lulus_revisi' then p_batas_revisi end,
         catatan_revisi = case when v_hasil = 'lulus_revisi' then nullif(btrim(coalesce(p_catatan_revisi, '')), '') end,
         revisi_selesai = case when v_hasil = 'lulus_revisi' then revisi_selesai end
   where id = j.id;
  return v_hasil;
end;
$$;

CREATE FUNCTION public.ta_beban(p_ts integer, p_sm text) RETURNS TABLE(dosen_id uuid, nama text, kk text, kuota integer, kuota_sendiri boolean, beban integer, dibimbing integer)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select d.id, d.nama, ds.kelompok_keahlian,
         coalesce(k.kuota, b.kuota), k.kuota is not null,
         (select count(*)::int from pengajuan_mahasiswa p
           where p.jenis = 'ta' and p.data ->> 'tahap_ta' = 'penetapan_pembimbing'
             and coalesce(nullif(p.data ->> 'pembimbing_awal', ''), p.pembimbing_id::text) = d.id::text
             and p.status not in ('draf', 'ditolak')
             and (p.dibuat at time zone 'Asia/Jakarta')::date >= semester_awal(p_ts, p_sm)
             and (p.dibuat at time zone 'Asia/Jakarta')::date < semester_akhir(p_ts, p_sm)),
         (select count(distinct upper(btrim(p.nim)))::int from pengajuan_mahasiswa p
           where p.jenis = 'ta' and p.data ->> 'tahap_ta' = 'penetapan_pembimbing' and p.pembimbing_id = d.id
             and p.status not in ('draf', 'ditolak')
             and (p.dibuat at time zone 'Asia/Jakarta')::date < semester_awal(p_ts, p_sm)
             and ta_lulus_ta(p.nim) is null)
    from pembimbing_pilihan() d
    join dosen ds on ds.id = d.id
    left join ta_kuota k on k.ts = p_ts and k.semester = p_sm and k.dosen_id = d.id
    left join ta_kuota b on b.ts = p_ts and b.semester = p_sm and b.dosen_id is null
   where me() is not null and p_sm in ('Ganjil', 'Genap')
   order by d.nama
$$;

CREATE FUNCTION public.ta_berkas_daftar() RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce(jsonb_agg(jsonb_build_object('tahap', tahap, 'kode', kode, 'label', label, 'keterangan', keterangan, 'wajib', wajib)
                            order by tahap, urut, kode), '[]'::jsonb)
    from ta_berkas where aktif
$$;

CREATE FUNCTION public.ta_bimbingan_boleh(p_nim text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select boleh_pengajuan('ta') or exists (select 1 from ta_pembimbing_nim(p_nim) x where x.id = me())
$$;

CREATE FUNCTION public.ta_bimbingan_konfirmasi(p_ids bigint[], p_setuju boolean, p_catatan text DEFAULT NULL::text) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare b ta_bimbingan; v_nama text; v_n int := 0; v_catatan text := nullif(btrim(coalesce(p_catatan, '')), '');
begin
  select nama into v_nama from dosen where id = me();
  if v_nama is null then raise exception 'Masuk sebagai dosen terdaftar dulu.'; end if;
  if p_setuju is null then raise exception 'Pilih konfirmasi atau kembalikan.'; end if;
  if not p_setuju and length(coalesce(v_catatan, '')) < 3 then raise exception 'Tulis alasan mengembalikan (minimal 3 huruf).'; end if;
  if length(coalesce(v_catatan, '')) > 1000 then raise exception 'Catatan paling banyak 1000 huruf.'; end if;
  for b in select * from ta_bimbingan where id = any(coalesce(p_ids, '{}')) order by id for update loop
    if not ta_bimbingan_boleh(b.nim) then
      raise exception 'Catatan bimbingan % dikonfirmasi pembimbingnya, koordinator TA, atau admin.', b.nama; end if;
    update ta_bimbingan set status = case when p_setuju then 'dikonfirmasi' else 'dikembalikan' end,
           catatan_pembimbing = v_catatan, konfirmasi_oleh = v_nama, konfirmasi_pada = now(), diperbarui = now()
     where id = b.id;
    v_n := v_n + 1;
  end loop;
  if v_n = 0 then raise exception 'Pilih catatan bimbingan dulu.'; end if;
  return v_n;
end;
$$;

CREATE FUNCTION public.ta_bimbingan_menunggu() RETURNS TABLE(nim text, nama text, n integer, tertua timestamp with time zone)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select upper(btrim(b.nim)), (array_agg(b.nama order by b.id desc))[1], count(*)::int, min(b.diajukan)
    from ta_bimbingan b
   where b.status = 'menunggu' and not ta_bimbingan_sah(b.status, b.diajukan)
     and exists (select 1 from ta_pembimbing_nim(b.nim) x where x.id = me())
   group by 1 order by 4
$$;

CREATE FUNCTION public.ta_bimbingan_rekap() RETURNS TABLE(nim text, nama text, pembimbing text, sah integer, menunggu integer, dikembalikan integer, terakhir date, tahap_lulus text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with m as (
    select upper(btrim(o.nim)) as nim, o.nama, o.diperbarui as waktu from pengajuan_mahasiswa o
     where o.jenis = 'ta' and o.status not in ('draf', 'ditolak', 'dibatalkan')
    union all
    select upper(btrim(b.nim)), b.nama, b.dibuat from ta_bimbingan b),
  u as (select m.nim, (array_agg(m.nama order by m.waktu desc))[1] as nama from m group by m.nim)
  select u.nim, u.nama,
    (select string_agg(x.nama, ', ' order by x.ke) from ta_pembimbing_nim(u.nim) x),
    (select count(*) from ta_bimbingan b where upper(btrim(b.nim)) = u.nim and ta_bimbingan_sah(b.status, b.diajukan))::int,
    (select count(*) from ta_bimbingan b where upper(btrim(b.nim)) = u.nim and b.status = 'menunggu' and not ta_bimbingan_sah(b.status, b.diajukan))::int,
    (select count(*) from ta_bimbingan b where upper(btrim(b.nim)) = u.nim and b.status = 'dikembalikan')::int,
    (select max(b.tanggal) from ta_bimbingan b where upper(btrim(b.nim)) = u.nim),
    (select t.tahap from jadwal_ta t where upper(btrim(coalesce(t.nim, ''))) = u.nim and t.status = 'selesai' and t.hasil in ('lulus', 'lulus_revisi')
      order by case t.tahap when 'sidang_akhir' then 3 when 'seminar_kemajuan' then 2 else 1 end desc limit 1)
  from u
  where boleh_pengajuan('ta') or exists (select 1 from ta_pembimbing_nim(u.nim) x where x.id = me())
  order by 2
$$;

CREATE FUNCTION public.ta_bimbingan_sah(p_status text, p_diajukan timestamp with time zone) RETURNS boolean
    LANGUAGE sql STABLE
    SET search_path TO 'public'
    AS $$
  select p_status = 'dikonfirmasi' or (p_status = 'menunggu' and p_diajukan <= now() - interval '14 days')
$$;

CREATE FUNCTION public.ta_ganti_pembimbing(p_id bigint, p_dosen uuid, p_dosen2 uuid, p_judul text, p_alasan text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_lama text; v_lama2 text; v_baru text; v_dua text; v_oleh text; v_cocok boolean; v_n int;
        v_alasan text := nullif(btrim(coalesce(p_alasan, '')), ''); v_judul text := nullif(btrim(coalesce(p_judul, '')), '');
begin
  if not boleh_pengajuan('ta') then raise exception 'Pembimbing TA diganti koordinator TA atau admin.'; end if;
  select * into p from pengajuan_mahasiswa where id = p_id for update;
  if p.id is null or p.jenis <> 'ta' or coalesce(p.data ->> 'tahap_ta', '') <> 'penetapan_pembimbing' then
    raise exception 'Pengajuan pembimbing TA tidak ditemukan.'; end if;
  if p.status <> 'disetujui' then
    raise exception 'Ganti pembimbing hanya pada penetapan yang sudah disahkan; sebelum itu pakai Tetapkan pembimbing.'; end if;
  if v_alasan is null or length(v_alasan) < 5 then raise exception 'Tulis alasan penggantian (bimbingan dibatalkan).'; end if;
  if v_judul is not null and length(v_judul) < 3 then raise exception 'Judul terlalu pendek.'; end if;
  if not exists (select 1 from pembimbing_pilihan() x where x.id = p_dosen) then raise exception 'Pilih pembimbing 1 dari daftar.'; end if;
  if p_dosen2 is not null and not exists (select 1 from pembimbing_pilihan() x where x.id = p_dosen2) then
    raise exception 'Pilih pembimbing 2 dari daftar.'; end if;
  if p_dosen2 = p_dosen then raise exception 'Pembimbing 2 harus berbeda dari pembimbing 1.'; end if;
  if p.pembimbing_id = p_dosen and (p.data ->> 'pembimbing_2') is not distinct from p_dosen2::text
     and (v_judul is null or v_judul = p.data ->> 'judul') then raise exception 'Pembimbing dan judul tidak berubah.'; end if;
  v_cocok := ta_kk_cocok(p.data ->> 'kk_ta', (select d.kelompok_keahlian from dosen d where d.id = p_dosen));
  select nama into v_lama from dosen where id = p.pembimbing_id;
  select nama into v_lama2 from dosen where id::text = p.data ->> 'pembimbing_2';
  select nama into v_baru from dosen where id = p_dosen;
  select nama into v_dua from dosen where id = p_dosen2;
  select nama into v_oleh from dosen where id = me();
  update pengajuan_mahasiswa set pembimbing_id = p_dosen, diperbarui = now(),
         data = (data - 'pembimbing_2')
                || jsonb_build_object('pembimbing_awal', coalesce(nullif(data ->> 'pembimbing_awal', ''), p.pembimbing_id::text))
                || jsonb_strip_nulls(jsonb_build_object('pembimbing_2', p_dosen2::text, 'judul', v_judul))
   where id = p.id;
  update pengajuan_mahasiswa set pembimbing_id = p_dosen, diperbarui = now(),
         data = (data - 'pembimbing_2') || jsonb_strip_nulls(jsonb_build_object('pembimbing_2', p_dosen2::text))
   where upper(btrim(nim)) = upper(btrim(p.nim)) and jenis = 'ta' and id <> p.id
     and coalesce(data ->> 'tahap_ta', '') <> 'penetapan_pembimbing' and status in ('draf', 'pembimbing', 'admin', 'dikembalikan');
  get diagnostics v_n = row_count;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, p.status, coalesce(v_oleh, 'prodi') || ' (koordinator TA/admin)',
          'Bimbingan dibatalkan, pembimbing diganti. Pembimbing 1: ' || coalesce(v_lama, '-') || ' -> ' || v_baru
          || '; pembimbing 2: ' || coalesce(v_lama2, 'tidak ada') || ' -> ' || coalesce(v_dua, 'tidak ada')
          || case when v_judul is not null and v_judul is distinct from p.data ->> 'judul'
                  then '; judul: ' || left(coalesce(p.data ->> 'judul', '-'), 300) || ' -> ' || left(v_judul, 300) else '' end
          || case when v_cocok then '' else '; di luar kelompok keahlian TA' end
          || case when v_n > 0 then '; ' || v_n || ' pengajuan TA berjalan ikut dipindah' else '' end
          || '. Alasan: ' || left(v_alasan, 600), p.tahap);
  return 'diganti';
end;
$$;

CREATE FUNCTION public.ta_jaga_ba() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public'
    AS $$
declare v_pesan constant text := 'Nilai, berita acara, dan tanda unggah SIUP diisi lewat halaman Penilaian seminar dan sidang TA.';
begin
  -- Hanya peran klien; fungsi security definer, SQL Editor, dan pemulihan cadangan berjalan sebagai pemilik.
  if current_user not in ('authenticated', 'anon') then return coalesce(new, old); end if;
  if tg_op = 'DELETE' then
    if old.ba_ditetapkan is not null then
      raise exception 'Berita acara seminar ini sudah ditetapkan; jadwalnya tidak bisa dihapus.'; end if;
    return old;
  end if;
  if tg_op = 'INSERT' then
    if new.rubrik_id is not null or new.nilai_akhir is not null or new.ba_ditetapkan is not null
       or new.ba_oleh is not null or new.ba_dibuka is not null or new.siup_diunggah is not null or new.siup_oleh is not null then
      raise exception '%', v_pesan; end if;
    return new;
  end if;
  if (new.rubrik_id, new.nilai_akhir, new.ba_ditetapkan, new.ba_oleh, new.ba_dibuka, new.siup_diunggah, new.siup_oleh)
     is distinct from (old.rubrik_id, old.nilai_akhir, old.ba_ditetapkan, old.ba_oleh, old.ba_dibuka, old.siup_diunggah, old.siup_oleh) then
    raise exception '%', v_pesan; end if;
  if old.ba_ditetapkan is not null
     and (new.tahap, new.nim, new.nama_mahasiswa, new.judul, new.pembimbing, new.penguji, new.penguji_luar, new.tanggal, new.status, new.hasil)
         is distinct from
         (old.tahap, old.nim, old.nama_mahasiswa, old.judul, old.pembimbing, old.penguji, old.penguji_luar, old.tanggal, old.status, old.hasil) then
    raise exception 'Berita acara seminar ini sudah ditetapkan; data seminar dan hasilnya dikunci. Koordinator TA bisa membukanya kembali di Penilaian seminar dan sidang TA.';
  end if;
  if old.ba_ditetapkan is null and new.hasil is distinct from old.hasil
     and exists (select 1 from ta_nilai t where t.jadwal_id = old.id) then
    raise exception 'Seminar ini sudah dinilai di situs; hasilnya ditetapkan di Penilaian seminar dan sidang TA.'; end if;
  return new;
end;
$$;

CREATE FUNCTION public.ta_jaga_urutan() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_pesan text;
begin
  if new.jenis = 'ta' and coalesce(new.data ->> 'tahap_ta', '') in ('seminar_kemajuan', 'sidang_akhir')
     and old.status in ('draf', 'dikembalikan') and new.status in ('pembimbing', 'admin') then
    v_pesan := ta_syarat_urutan(new.nim, new.data ->> 'tahap_ta');
    if v_pesan is not null then raise exception '%', v_pesan; end if;
  end if;
  return new;
end;
$$;

CREATE FUNCTION public.ta_kecualikan_urutan(p_nim text, p_tahap text, p_alasan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_nim text := btrim(coalesce(p_nim, '')); v_alasan text := nullif(btrim(coalesce(p_alasan, '')), ''); v_oleh text;
begin
  if not boleh_pengajuan('ta') then raise exception 'Pengecualian urutan tahap dicatat koordinator TA atau admin.'; end if;
  if length(v_nim) not between 3 and 30 then raise exception 'Isi NIM mahasiswa.'; end if;
  if p_tahap not in ('seminar_kemajuan', 'sidang_akhir') then raise exception 'Pilih tahap: seminar kemajuan atau sidang akhir.'; end if;
  if v_alasan is null then
    delete from ta_kecuali_urutan where upper(btrim(nim)) = upper(v_nim) and tahap = p_tahap;
    return 'dihapus';
  end if;
  if length(v_alasan) < 5 then raise exception 'Tulis alasan pengecualian (minimal 5 huruf).'; end if;
  select nama into v_oleh from dosen where id = me();
  update ta_kecuali_urutan set alasan = v_alasan, oleh = v_oleh, dibuat = now()
   where upper(btrim(nim)) = upper(v_nim) and tahap = p_tahap;
  if not found then
    insert into ta_kecuali_urutan (nim, tahap, alasan, oleh) values (v_nim, p_tahap, v_alasan, v_oleh);
  end if;
  return 'dicatat';
end;
$$;

CREATE FUNCTION public.ta_kk_cocok(p_kk_ta text, p_kk_dosen text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce(p_kk_ta, '') <> '' and coalesce(p_kk_dosen, '') <> ''
     and (p_kk_ta = p_kk_dosen or exists (select 1 from ta_kk_dekat k
          where (k.kk_a = p_kk_ta and k.kk_b = p_kk_dosen) or (k.kk_a = p_kk_dosen and k.kk_b = p_kk_ta)))
$$;

CREATE FUNCTION public.ta_lampiran_dihapus(p_kunci text, p_id bigint) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  update ta_bimbingan set lampiran_url = null, lampiran_dihapus = now(), diperbarui = now()
   where id = p_id and lampiran_url is not null and ta_lulus_pada(nim) + 30 <= (now() at time zone 'Asia/Jakarta')::date;
  return case when found then 'dihapus' else 'tidak' end;
end;
$$;

CREATE FUNCTION public.ta_lampiran_kedaluwarsa(p_kunci text) RETURNS TABLE(id bigint, url text)
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if not mhs_kunci_sah(p_kunci) then raise exception 'Kunci layanan salah.'; end if;
  return query
    select b.id, b.lampiran_url from ta_bimbingan b
     where b.lampiran_url is not null and ta_lulus_pada(b.nim) + 30 <= (now() at time zone 'Asia/Jakarta')::date
     order by b.id limit 200;
end;
$$;

CREATE FUNCTION public.ta_lulus_pada(p_nim text) RETURNS date
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select max(case when t.hasil = 'lulus' then t.tanggal when t.hasil = 'lulus_revisi' then t.revisi_selesai end)
    from jadwal_ta t
   where upper(btrim(coalesce(t.nim, ''))) = upper(btrim(p_nim)) and t.tahap = 'sidang_akhir' and t.status = 'selesai'
     and (t.hasil = 'lulus' or (t.hasil = 'lulus_revisi' and t.revisi_selesai is not null))
$$;

CREATE FUNCTION public.ta_lulus_ta(p_nim text) RETURNS date
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select max(t.tanggal) from jadwal_ta t
   where upper(btrim(coalesce(t.nim, ''))) = upper(btrim(p_nim)) and t.tahap = 'sidang_akhir' and t.status = 'selesai'
     and (t.hasil = 'lulus' or (t.hasil = 'lulus_revisi' and t.revisi_selesai is not null))
$$;

CREATE FUNCTION public.ta_nilai_hapus(p_id bigint) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare n ta_nilai; j jadwal_ta;
begin
  select * into n from ta_nilai where id = p_id;
  if n.id is null then raise exception 'Nilai tidak ditemukan.'; end if;
  select * into j from jadwal_ta where id = n.jadwal_id for update;
  if j.ba_ditetapkan is not null then raise exception 'Berita acara sudah ditetapkan; nilai tidak bisa dihapus.'; end if;
  if not (boleh_tabel('jadwal_ta') or (n.penilai_nidn is not null and n.penilai_nidn = (select nidn from dosen where id = me()))) then
    raise exception 'Nilai dihapus penilainya sendiri, koordinator TA, atau admin.'; end if;
  delete from ta_nilai where id = n.id;
  -- Tanpa nilai lagi: jadwal kembali memakai versi form terbaru.
  if not exists (select 1 from ta_nilai where jadwal_id = j.id) then update jadwal_ta set rubrik_id = null where id = j.id; end if;
  return 'dihapus';
end;
$$;

CREATE FUNCTION public.ta_nilai_hitung(p_jadwal bigint) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare j jadwal_ta; r ta_rubrik; v_rp numeric; v_rb numeric; v_rm numeric; v_akhir numeric; v_kurang jsonb; v_luar boolean;
  v_wp numeric; v_wm numeric; v_wb numeric; v_jml numeric := 0; v_w numeric := 0;
begin
  select * into j from jadwal_ta where id = p_jadwal;
  r := ta_rubrik_jadwal(j);
  v_luar := nullif(btrim(coalesce(j.penguji_luar, '')), '') is not null;
  v_wp := coalesce(r.bobot_penguji, 0); v_wm := coalesce(r.bobot_bimbingan, 0); v_wb := 100 - v_wp - v_wm;
  select round(avg(t.total), 2) into v_rp from ta_nilai t where t.jadwal_id = j.id and t.bagian = 'seminar'
     and (t.penilai_nidn = any(j.penguji) or (t.penilai_nidn is null and v_luar));
  select round(avg(t.total), 2) into v_rb from ta_nilai t where t.jadwal_id = j.id and t.bagian = 'seminar' and t.penilai_nidn = any(j.pembimbing);
  if v_wm > 0 then
    select round(avg(t.total), 2) into v_rm from ta_nilai t where t.jadwal_id = j.id and t.bagian = 'bimbingan' and t.penilai_nidn = any(j.pembimbing);
  end if;
  if v_rp is not null and v_wp > 0 then v_jml := v_jml + v_rp * v_wp; v_w := v_w + v_wp; end if;
  if v_rb is not null and v_wb > 0 then v_jml := v_jml + v_rb * v_wb; v_w := v_w + v_wb; end if;
  if v_rm is not null and v_wm > 0 then v_jml := v_jml + v_rm * v_wm; v_w := v_w + v_wm; end if;
  v_akhir := case when v_w > 0 then round(v_jml / v_w, 2) end;
  select coalesce(jsonb_agg(jsonb_build_object('peran', x.peran, 'bagian', x.bagian, 'nidn', x.nidn, 'nama', coalesce(d.nama, x.nidn))
                            order by x.urut), '[]')
    into v_kurang
    from (select 'pembimbing' as peran, 'seminar' as bagian, u.n as nidn, u.o as urut from unnest(j.pembimbing) with ordinality u(n, o)
          union all select 'penguji', 'seminar', u.n, 100 + u.o from unnest(j.penguji) with ordinality u(n, o)
          union all select 'pembimbing', 'bimbingan', u.n, 200 + u.o from unnest(j.pembimbing) with ordinality u(n, o) where v_wm > 0) x
    left join dosen d on d.nidn = x.nidn
   where not exists (select 1 from ta_nilai t where t.jadwal_id = j.id and t.bagian = x.bagian and t.penilai_nidn = x.nidn);
  if v_luar and not exists (select 1 from ta_nilai t where t.jadwal_id = j.id and t.penilai_nidn is null) then
    v_kurang := v_kurang || jsonb_build_array(jsonb_build_object('peran', 'penguji', 'bagian', 'seminar', 'nidn', null, 'nama', btrim(j.penguji_luar)));
  end if;
  return jsonb_build_object('rubrik_id', r.id, 'rata_penguji', v_rp, 'rata_pembimbing', v_rb, 'rata_bimbingan', v_rm,
    'nilai_akhir', v_akhir, 'kurang', v_kurang,
    'saran', case when v_akhir is null then null when v_akhir < r.batas_lulus then 'mengulang' else 'lulus' end);
end;
$$;

CREATE FUNCTION public.ta_nilai_rekap(p_jadwal bigint) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare j jadwal_ta; r ta_rubrik; v_koor boolean := boleh_tabel('jadwal_ta'); v_luar boolean;
begin
  select * into j from jadwal_ta where id = p_jadwal;
  if j.id is null then raise exception 'Jadwal seminar/sidang tidak ditemukan.'; end if;
  if not (v_koor or ta_panel_saya(j.id) is not null) then
    raise exception 'Rekap nilai dibuka pembimbing/penguji seminar ini, koordinator TA, atau admin.'; end if;
  r := ta_rubrik_jadwal(j);
  v_luar := nullif(btrim(coalesce(j.penguji_luar, '')), '') is not null;
  return jsonb_build_object(
    'jadwal', jsonb_build_object('id', j.id, 'tahap', j.tahap, 'nama_mahasiswa', j.nama_mahasiswa, 'nim', j.nim, 'judul', j.judul,
      'tanggal', j.tanggal, 'jam', j.jam, 'ruang', j.ruang, 'status', j.status, 'hasil', j.hasil, 'batas_revisi', j.batas_revisi,
      'catatan_revisi', j.catatan_revisi, 'penguji_luar', j.penguji_luar, 'nilai_akhir', j.nilai_akhir,
      'ba_ditetapkan', j.ba_ditetapkan, 'ba_oleh', j.ba_oleh, 'ba_dibuka', j.ba_dibuka),
    'rubrik', case when r.id is null then null else to_jsonb(r) end,
    'panel', (select coalesce(jsonb_agg(jsonb_build_object('peran', x.peran, 'nidn', x.nidn, 'nama', coalesce(d.nama, x.nidn)) order by x.urut), '[]')
                from (select 'pembimbing' as peran, u.n as nidn, u.o as urut from unnest(j.pembimbing) with ordinality u(n, o)
                      union all select 'penguji', u.n, 100 + u.o from unnest(j.penguji) with ordinality u(n, o)) x
                left join dosen d on d.nidn = x.nidn),
    'nilai', (select coalesce(jsonb_agg(jsonb_build_object('id', t.id, 'bagian', t.bagian, 'peran', t.peran, 'nidn', t.penilai_nidn,
                'nama', t.penilai_nama, 'nilai', t.nilai, 'total', t.total, 'catatan', t.catatan, 'diisi_oleh', t.diisi_oleh,
                'diwakilkan', t.diwakilkan, 'diperbarui', t.diperbarui, 'rubrik_id', t.rubrik_id,
                'di_panel', case when t.bagian = 'bimbingan' then t.penilai_nidn = any(j.pembimbing)
                                 else t.penilai_nidn = any(j.pembimbing) or t.penilai_nidn = any(j.penguji) or (t.penilai_nidn is null and v_luar) end)
                order by t.bagian desc, t.peran, t.penilai_nama), '[]') from ta_nilai t where t.jadwal_id = j.id),
    'hitung', ta_nilai_hitung(j.id),
    'saya', jsonb_build_object('peran', ta_panel_saya(j.id), 'koordinator', v_koor));
end;
$$;

CREATE FUNCTION public.ta_nilai_simpan(p_jadwal bigint, p_nilai jsonb, p_catatan text DEFAULT NULL::text, p_nidn text DEFAULT NULL::text, p_nama_luar text DEFAULT NULL::text, p_bagian text DEFAULT 'seminar'::text) RETURNS numeric
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare j jadwal_ta; r ta_rubrik; k jsonb; v numeric; v_bersih jsonb := '{}'; v_total numeric := 0; v_jumlah numeric := 0;
  v_saya dosen; v_peran text; v_nidn text; v_nama text; v_wakil boolean := false; v_kunci text;
  v_bagian text := coalesce(p_bagian, 'seminar'); v_komp jsonb;
begin
  if v_bagian not in ('seminar', 'bimbingan') then raise exception 'Bagian nilai: seminar atau bimbingan.'; end if;
  select * into j from jadwal_ta where id = p_jadwal for update;
  if j.id is null then raise exception 'Jadwal seminar/sidang tidak ditemukan.'; end if;
  if j.ba_ditetapkan is not null then
    raise exception 'Berita acara sudah ditetapkan; nilai tidak bisa diubah. Minta koordinator TA membukanya kembali.'; end if;
  if j.status not in ('terjadwal', 'selesai') then
    raise exception 'Seminar/sidang ini berstatus %; nilai tidak bisa diisi.', j.status; end if;
  select * into v_saya from dosen where id = me();
  if v_saya.id is null then raise exception 'Masuk sebagai dosen terdaftar dulu.'; end if;

  if p_nidn is null and nullif(btrim(coalesce(p_nama_luar, '')), '') is null then
    v_nidn := v_saya.nidn; v_nama := v_saya.nama;                                  -- nilai saya sendiri
  else
    if not boleh_tabel('jadwal_ta') then
      raise exception 'Nilai atas nama penilai lain diisikan koordinator TA atau admin.'; end if;
    v_wakil := true;
    if p_nidn is not null then
      v_nidn := btrim(p_nidn);
      select nama into v_nama from dosen where nidn = v_nidn;
      v_nama := coalesce(v_nama, v_nidn);
      if v_nidn = v_saya.nidn then v_wakil := false; end if;
    else
      if nullif(btrim(coalesce(j.penguji_luar, '')), '') is null then
        raise exception 'Seminar ini tidak punya penguji luar; isi dulu di Data prodi › Jadwal seminar/sidang TA.'; end if;
      v_nama := btrim(p_nama_luar);
      if length(v_nama) not between 2 and 200 then raise exception 'Nama penguji luar 2–200 huruf.'; end if;
      v_peran := 'penguji';
    end if;
  end if;
  if v_peran is null then
    v_peran := case when v_nidn = any(j.pembimbing) then 'pembimbing' when v_nidn = any(j.penguji) then 'penguji' end;
    if v_peran is null then
      raise exception '% bukan pembimbing atau penguji seminar ini.', case when v_wakil then v_nama else 'Anda' end; end if;
  end if;

  r := ta_rubrik_jadwal(j);
  if r.id is null then raise exception 'Form penilaian tahap ini belum ada.'; end if;
  if v_bagian = 'bimbingan' then
    if v_peran <> 'pembimbing' then raise exception 'Nilai proses bimbingan diisi pembimbing.'; end if;
    if coalesce(r.bobot_bimbingan, 0) = 0 then raise exception 'Form penilaian tahap ini tidak memakai nilai proses bimbingan.'; end if;
    v_komp := r.komponen_bimbingan;
  else
    v_komp := r.komponen;
  end if;
  if jsonb_typeof(p_nilai) is distinct from 'object' then raise exception 'Isi nilai tiap komponen.'; end if;
  for k in select x from jsonb_array_elements(v_komp) x loop
    if jsonb_typeof(p_nilai -> (k ->> 'kode')) is distinct from 'number' then
      raise exception 'Isi nilai "%" (0–100).', k ->> 'label'; end if;
    v := (p_nilai ->> (k ->> 'kode'))::numeric;
    if v < 0 or v > 100 then raise exception 'Nilai "%" harus 0–100.', k ->> 'label'; end if;
    v := round(v, 2);
    v_bersih := v_bersih || jsonb_build_object(k ->> 'kode', v);
    v_total := v_total + v * (k ->> 'bobot')::numeric;
    v_jumlah := v_jumlah + (k ->> 'bobot')::numeric;
  end loop;
  if exists (select 1 from jsonb_object_keys(p_nilai) x where not (v_bersih ? x)) then
    raise exception 'Ada nilai untuk komponen yang tidak ada di form penilaian; muat ulang halaman.'; end if;
  if length(coalesce(p_catatan, '')) > 2000 then raise exception 'Catatan paling banyak 2000 huruf.'; end if;
  v_total := round(v_total / v_jumlah, 2);

  if j.rubrik_id is null then update jadwal_ta set rubrik_id = r.id where id = j.id; end if;
  v_kunci := coalesce(v_nidn, 'luar:' || lower(v_nama));
  update ta_nilai set peran = v_peran, penilai_nama = v_nama, rubrik_id = r.id, nilai = v_bersih, total = v_total,
         catatan = nullif(btrim(coalesce(p_catatan, '')), ''), diisi_oleh = v_saya.nama, diwakilkan = v_wakil, diperbarui = now()
   where jadwal_id = j.id and bagian = v_bagian and coalesce(penilai_nidn, 'luar:' || lower(btrim(penilai_nama))) = v_kunci;
  if not found then
    insert into ta_nilai (jadwal_id, rubrik_id, bagian, peran, penilai_nidn, penilai_nama, nilai, total, catatan, diisi_oleh, diwakilkan)
    values (j.id, r.id, v_bagian, v_peran, v_nidn, v_nama, v_bersih, v_total, nullif(btrim(coalesce(p_catatan, '')), ''), v_saya.nama, v_wakil);
  end if;
  return v_total;
end;
$$;

CREATE FUNCTION public.ta_nilai_tugas() RETURNS TABLE(jadwal_id bigint, tahap text, nama_mahasiswa text, tanggal date, tugas text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with saya as (select nidn from dosen where id = me()),
       kini as (select (now() at time zone 'Asia/Jakarta')::date as hari)
  select j.id, j.tahap, j.nama_mahasiswa, j.tanggal, 'nilai'
    from jadwal_ta j, saya, kini
   where saya.nidn is not null and (saya.nidn = any(j.pembimbing) or saya.nidn = any(j.penguji))
     and j.status in ('terjadwal', 'selesai') and j.ba_ditetapkan is null and j.tanggal <= kini.hari
     and (not exists (select 1 from ta_nilai t where t.jadwal_id = j.id and t.bagian = 'seminar' and t.penilai_nidn = saya.nidn)
          or (saya.nidn = any(j.pembimbing) and coalesce((public.ta_rubrik_jadwal(j)).bobot_bimbingan, 0) > 0
              and not exists (select 1 from ta_nilai t where t.jadwal_id = j.id and t.bagian = 'bimbingan' and t.penilai_nidn = saya.nidn)))
  union all
  select j.id, j.tahap, j.nama_mahasiswa, j.tanggal, 'tetapkan'
    from jadwal_ta j, kini
   where boleh_tabel('jadwal_ta') and j.status in ('terjadwal', 'selesai') and j.ba_ditetapkan is null and j.tanggal <= kini.hari
     and exists (select 1 from ta_nilai t where t.jadwal_id = j.id)
  union all
  select j.id, j.tahap, j.nama_mahasiswa, j.tanggal, 'siup'
    from jadwal_ta j, saya
   where saya.nidn is not null and saya.nidn = any(j.pembimbing) and j.ba_ditetapkan is not null and j.siup_diunggah is null
  union all
  select (select max(t.id) from jadwal_ta t where upper(btrim(coalesce(t.nim, ''))) = a.nim and t.tahap = 'sidang_akhir'),
         'sidang_akhir', a.nama, a.lulus, 'arsip'
    from ta_arsip_siap() a
   where a.arsip_url is null
  order by 4, 1
$$;

CREATE FUNCTION public.ta_panel_saya(p_jadwal bigint) RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select case when d.nidn = any(j.pembimbing) then 'pembimbing' when d.nidn = any(j.penguji) then 'penguji' end
    from jadwal_ta j, dosen d where j.id = p_jadwal and d.id = me() and d.nidn is not null
$$;

CREATE FUNCTION public.ta_pembimbing_nim(p_nim text) RETURNS TABLE(id uuid, nama text, ke integer)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  with p as (
    select o.pembimbing_id, o.data ->> 'pembimbing_2' as p2 from pengajuan_mahasiswa o
     where upper(btrim(o.nim)) = upper(btrim(p_nim)) and o.jenis = 'ta' and o.pembimbing_id is not null
       and o.status not in ('draf', 'ditolak', 'dibatalkan')
     order by (o.data ->> 'tahap_ta' = 'penetapan_pembimbing' and o.status = 'disetujui') desc, o.diperbarui desc, o.id desc
     limit 1)
  select d.id, d.nama, 1 from p join dosen d on d.id = p.pembimbing_id
  union all
  select d.id, d.nama, 2 from p join dosen d on d.id::text = p.p2 where d.id <> p.pembimbing_id
  order by 3
$$;

CREATE FUNCTION public.ta_periksa_berkas() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_kurang text; v_tahap text := coalesce(new.data ->> 'tahap_ta', '');
begin
  if new.jenis = 'ta' and v_tahap in ('penetapan_pembimbing', 'seminar_proposal', 'seminar_kemajuan', 'sidang_akhir')
     and old.status in ('draf', 'dikembalikan') and new.status in ('pembimbing', 'admin') then
    select string_agg(t.label, ', ' order by t.urut, t.kode) into v_kurang
      from ta_berkas t
     where t.tahap = v_tahap and t.aktif and t.wajib
       and not exists (select 1 from pengajuan_berkas b where b.pengajuan_id = new.id and b.jenis = t.kode);
    if v_kurang is not null then
      raise exception 'Berkas wajib % belum lengkap: %.',
        case v_tahap when 'penetapan_pembimbing' then 'pengajuan pembimbing TA' when 'seminar_proposal' then 'seminar proposal'
                     when 'seminar_kemajuan' then 'seminar kemajuan' else 'sidang akhir' end,
        v_kurang;
    end if;
  end if;
  return new;
end;
$$;

CREATE FUNCTION public.ta_periksa_bimbingan() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare h jsonb; v_tahap text := coalesce(new.data ->> 'tahap_ta', '');
begin
  if new.jenis = 'ta' and v_tahap in ('seminar_proposal', 'seminar_kemajuan', 'sidang_akhir')
     and old.status in ('draf', 'dikembalikan') and new.status in ('pembimbing', 'admin') then
    h := ta_syarat_bimbingan_hitung(new.nim, v_tahap);
    if not (h ->> 'cukup')::boolean then
      raise exception 'Bimbingan terkonfirmasi%: baru % dari minimal %. Catat bimbingan Anda di bagian Catatan bimbingan dan minta pembimbing mengonfirmasinya (catatan yang 14 hari tidak ditanggapi terkonfirmasi otomatis).',
        case when h ->> 'sejak' is not null then ' sejak ' || case v_tahap when 'seminar_kemajuan' then 'seminar proposal' else 'seminar kemajuan' end
             || ' (' || to_char((h ->> 'sejak')::date, 'DD-MM-YYYY') || ')' else '' end,
        h ->> 'terhitung', h ->> 'minimal';
    end if;
  end if;
  return new;
end;
$$;

CREATE FUNCTION public.ta_revisi_selesai(p_id bigint, p_selesai boolean DEFAULT true) RETURNS date
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare j jadwal_ta; v_nidn text;
begin
  select * into j from jadwal_ta where id = p_id for update;
  if j.id is null then raise exception 'Jadwal tidak ditemukan.'; end if;
  select nidn into v_nidn from dosen where id = me();
  if not (boleh_tabel('jadwal_ta') or (v_nidn is not null and v_nidn = any(j.pembimbing))) then
    raise exception 'Hanya pembimbing mahasiswa ini, koordinator TA, atau admin.'; end if;
  if j.hasil is distinct from 'lulus_revisi' then raise exception 'Hasilnya bukan lulus dengan revisi.'; end if;
  update jadwal_ta set revisi_selesai = case when p_selesai then current_date else null end, diperbarui = now() where id = j.id;
  return case when p_selesai then current_date else null end;
end;
$$;

CREATE FUNCTION public.ta_rubrik_bersih(p_komponen jsonb, p_awalan text) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    SET search_path TO 'public'
    AS $_$
declare k jsonb; v_kode text[] := '{}'; v_jumlah numeric := 0; v_bersih jsonb := '[]'; v_ur jsonb; i int;
begin
  if jsonb_typeof(p_komponen) is distinct from 'array' or jsonb_array_length(p_komponen) not between 1 and 12 then
    raise exception '%Form penilaian berisi 1 sampai 12 komponen.', p_awalan; end if;
  for k in select x from jsonb_array_elements(p_komponen) x loop
    if coalesce(k ->> 'kode', '') !~ '^[a-z0-9_]{1,20}$' then
      raise exception '%Kode komponen hanya huruf kecil, angka, dan garis bawah (paling banyak 20).', p_awalan; end if;
    if (k ->> 'kode') = any(v_kode) then raise exception '%Kode komponen % dipakai dua kali.', p_awalan, k ->> 'kode'; end if;
    if length(btrim(coalesce(k ->> 'label', ''))) not between 3 and 200 then
      raise exception '%Nama komponen % harus 3–200 huruf.', p_awalan, k ->> 'kode'; end if;
    if jsonb_typeof(k -> 'bobot') is distinct from 'number' or (k ->> 'bobot')::numeric <= 0 or (k ->> 'bobot')::numeric > 100 then
      raise exception '%Bobot komponen "%" harus lebih dari 0 dan paling besar 100.', p_awalan, btrim(k ->> 'label'); end if;
    v_ur := coalesce(k -> 'uraian', '[]'::jsonb);
    if jsonb_typeof(v_ur) is distinct from 'array' or jsonb_array_length(v_ur) <> 4 then
      raise exception '%Uraian rubrik "%" harus 4 tingkat.', p_awalan, btrim(k ->> 'label'); end if;
    for i in 0..3 loop
      if jsonb_typeof(v_ur -> i) is distinct from 'string' or length(v_ur ->> i) > 600 then
        raise exception '%Uraian rubrik "%" tingkat % berupa teks, paling banyak 600 huruf.', p_awalan, btrim(k ->> 'label'), i + 1; end if;
    end loop;
    v_kode := v_kode || (k ->> 'kode');
    v_jumlah := v_jumlah + (k ->> 'bobot')::numeric;
    v_bersih := v_bersih || jsonb_build_array(jsonb_build_object('kode', k ->> 'kode', 'label', btrim(k ->> 'label'),
      'bobot', (k ->> 'bobot')::numeric,
      'uraian', (select jsonb_agg(btrim(u.x) order by u.n) from jsonb_array_elements_text(v_ur) with ordinality u(x, n))));
  end loop;
  if v_jumlah <> 100 then raise exception '%Jumlah bobot komponen harus 100 (sekarang %).', p_awalan, v_jumlah; end if;
  return v_bersih;
end;
$_$;

CREATE TABLE public.jadwal_ta (
    id bigint NOT NULL,
    tahap text NOT NULL,
    nama_mahasiswa text NOT NULL,
    nim text,
    judul text NOT NULL,
    pembimbing text[] DEFAULT '{}'::text[] NOT NULL,
    penguji text[] DEFAULT '{}'::text[] NOT NULL,
    penguji_luar text,
    tanggal date NOT NULL,
    jam text,
    ruang text,
    tautan_daring text,
    status text DEFAULT 'terjadwal'::text NOT NULL,
    hasil text,
    tampil_nama boolean DEFAULT false NOT NULL,
    sembunyikan_publik boolean DEFAULT false NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    pengajuan_id bigint,
    batas_revisi date,
    catatan_revisi text,
    revisi_selesai date,
    bidang text,
    rubrik_id bigint,
    nilai_akhir numeric(5,2),
    ba_ditetapkan timestamp with time zone,
    ba_oleh text,
    ba_dibuka text,
    siup_diunggah timestamp with time zone,
    siup_oleh text,
    CONSTRAINT jadwal_ta_ba_cek CHECK ((((nilai_akhir IS NULL) OR ((nilai_akhir >= (0)::numeric) AND (nilai_akhir <= (100)::numeric))) AND ((ba_dibuka IS NULL) OR (length(ba_dibuka) <= 700)))),
    CONSTRAINT jadwal_ta_bidang_cek CHECK (((bidang IS NULL) OR (bidang ~ '^[A-Z0-9]{2,12}$'::text))),
    CONSTRAINT jadwal_ta_hasil_check CHECK (((hasil IS NULL) OR (hasil = ANY (ARRAY['lulus'::text, 'lulus_revisi'::text, 'mengulang'::text])))),
    CONSTRAINT jadwal_ta_jam_check CHECK (((jam IS NULL) OR (length(jam) <= 40))),
    CONSTRAINT jadwal_ta_judul_check CHECK (((length(btrim(judul)) >= 3) AND (length(btrim(judul)) <= 400))),
    CONSTRAINT jadwal_ta_nama_mahasiswa_check CHECK (((length(btrim(nama_mahasiswa)) >= 2) AND (length(btrim(nama_mahasiswa)) <= 200))),
    CONSTRAINT jadwal_ta_nim_check CHECK (((nim IS NULL) OR (length(nim) <= 100))),
    CONSTRAINT jadwal_ta_penguji_luar_check CHECK (((penguji_luar IS NULL) OR (length(penguji_luar) <= 300))),
    CONSTRAINT jadwal_ta_revisi_check CHECK (((catatan_revisi IS NULL) OR (length(catatan_revisi) <= 2000))),
    CONSTRAINT jadwal_ta_ruang_check CHECK (((ruang IS NULL) OR (length(ruang) <= 120))),
    CONSTRAINT jadwal_ta_status_check CHECK ((status = ANY (ARRAY['terjadwal'::text, 'selesai'::text, 'ditunda'::text, 'batal'::text]))),
    CONSTRAINT jadwal_ta_tahap_check CHECK ((tahap = ANY (ARRAY['seminar_proposal'::text, 'seminar_kemajuan'::text, 'sidang_akhir'::text]))),
    CONSTRAINT jadwal_ta_tautan_daring_check CHECK (((tautan_daring IS NULL) OR (tautan_daring ~* '^https://\S+$'::text)))
);

CREATE TABLE public.ta_rubrik (
    id bigint NOT NULL,
    tahap text NOT NULL,
    versi integer NOT NULL,
    komponen jsonb NOT NULL,
    bobot_penguji numeric(5,2) DEFAULT 40 NOT NULL,
    batas_lulus numeric(5,2) DEFAULT 55 NOT NULL,
    tingkat numeric(5,2)[] DEFAULT '{85,70,55,0}'::numeric[] NOT NULL,
    catatan text,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    bobot_bimbingan numeric(5,2) DEFAULT 0 NOT NULL,
    komponen_bimbingan jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT ta_rubrik_batas_lulus_check CHECK (((batas_lulus >= (1)::numeric) AND (batas_lulus <= (100)::numeric))),
    CONSTRAINT ta_rubrik_bimbingan_cek CHECK (((bobot_bimbingan >= (0)::numeric) AND (bobot_bimbingan <= (100)::numeric))),
    CONSTRAINT ta_rubrik_bobot_penguji_check CHECK (((bobot_penguji >= (0)::numeric) AND (bobot_penguji <= (100)::numeric))),
    CONSTRAINT ta_rubrik_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 1000))),
    CONSTRAINT ta_rubrik_jumlah_cek CHECK (((bobot_penguji + bobot_bimbingan) <= (100)::numeric)),
    CONSTRAINT ta_rubrik_komponen_bimbingan_cek CHECK ((jsonb_typeof(komponen_bimbingan) = 'array'::text)),
    CONSTRAINT ta_rubrik_komponen_check CHECK ((jsonb_typeof(komponen) = 'array'::text)),
    CONSTRAINT ta_rubrik_tahap_check CHECK ((tahap = ANY (ARRAY['seminar_proposal'::text, 'seminar_kemajuan'::text, 'sidang_akhir'::text]))),
    CONSTRAINT ta_rubrik_versi_check CHECK ((versi >= 1))
);

CREATE FUNCTION public.ta_rubrik_jadwal(j public.jadwal_ta) RETURNS public.ta_rubrik
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select r.* from ta_rubrik r
   where (j.rubrik_id is not null and r.id = j.rubrik_id) or (j.rubrik_id is null and r.tahap = j.tahap)
   order by r.versi desc limit 1
$$;

CREATE FUNCTION public.ta_rubrik_simpan(p_tahap text, p_komponen jsonb, p_bobot_penguji numeric, p_batas_lulus numeric, p_tingkat numeric[] DEFAULT '{85,70,55,0}'::numeric[], p_catatan text DEFAULT NULL::text, p_bobot_bimbingan numeric DEFAULT 0, p_komponen_bimbingan jsonb DEFAULT '[]'::jsonb) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_versi int; v_oleh text; v_komp jsonb; v_bimb jsonb := '[]';
begin
  if not boleh_tabel('jadwal_ta') then raise exception 'Form penilaian TA diubah koordinator TA atau admin.'; end if;
  if p_tahap is null or p_tahap not in ('seminar_proposal', 'seminar_kemajuan', 'sidang_akhir') then
    raise exception 'Pilih tahap: seminar proposal, seminar kemajuan, atau sidang akhir.'; end if;
  v_komp := ta_rubrik_bersih(p_komponen, '');
  if p_bobot_penguji is null or p_bobot_penguji not between 0 and 100 then raise exception 'Bobot penguji 0–100 %%.'; end if;
  if p_bobot_bimbingan is null or p_bobot_bimbingan not between 0 and 100 then raise exception 'Bobot proses bimbingan 0–100 %%.'; end if;
  if p_bobot_penguji + p_bobot_bimbingan > 100 then
    raise exception 'Bobot penguji + proses bimbingan paling besar 100 %% (sisanya bobot pembimbing saat seminar/sidang).'; end if;
  if p_bobot_bimbingan > 0 or jsonb_array_length(coalesce(p_komponen_bimbingan, '[]')) > 0 then
    v_bimb := ta_rubrik_bersih(coalesce(p_komponen_bimbingan, '[]'), 'Proses bimbingan: '); end if;
  if p_batas_lulus is null or p_batas_lulus not between 1 and 100 then raise exception 'Batas lulus 1–100.'; end if;
  if p_tingkat is null or array_length(p_tingkat, 1) is distinct from 4 or p_tingkat[4] <> 0 or p_tingkat[1] > 100
     or not (p_tingkat[1] > p_tingkat[2] and p_tingkat[2] > p_tingkat[3] and p_tingkat[3] > 0) then
    raise exception 'Batas bawah 4 tingkat rubrik harus menurun dan tingkat terendah 0 (mis. 85, 70, 55, 0).'; end if;
  if length(coalesce(p_catatan, '')) > 1000 then raise exception 'Catatan perubahan paling banyak 1000 huruf.'; end if;
  select nama into v_oleh from dosen where id = me();
  select coalesce(max(versi), 0) + 1 into v_versi from ta_rubrik where tahap = p_tahap;
  insert into ta_rubrik (tahap, versi, komponen, komponen_bimbingan, bobot_penguji, bobot_bimbingan, batas_lulus, tingkat, catatan, oleh)
  values (p_tahap, v_versi, v_komp, v_bimb, p_bobot_penguji, p_bobot_bimbingan, p_batas_lulus, p_tingkat,
          nullif(btrim(coalesce(p_catatan, '')), ''), v_oleh);
  return v_versi;
end;
$$;

CREATE FUNCTION public.ta_siup_tandai(p_ids bigint[], p_sudah boolean) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_oleh text; v_nidn text; v_belum text; v_bukan text; v_n int;
begin
  if p_sudah is null then raise exception 'Pilih tandai atau batalkan tanda.'; end if;
  if coalesce(array_length(p_ids, 1), 0) = 0 then raise exception 'Pilih seminar/sidang dulu.'; end if;
  select nama, nidn into v_oleh, v_nidn from dosen where id = me();
  if not boleh_tabel('jadwal_ta') then
    select string_agg(j.nama_mahasiswa, ', ' order by j.tanggal) into v_bukan
      from jadwal_ta j where j.id = any(p_ids) and not (v_nidn is not null and v_nidn = any(j.pembimbing));
    if v_bukan is not null then
      raise exception 'Tanda unggah SIUP diisi pembimbingnya, koordinator TA, atau admin (%).', v_bukan; end if;
  end if;
  select string_agg(j.nama_mahasiswa, ', ' order by j.tanggal) into v_belum
    from jadwal_ta j where j.id = any(p_ids) and j.ba_ditetapkan is null;
  if v_belum is not null then raise exception 'Berita acara belum ditetapkan: %.', v_belum; end if;
  update jadwal_ta set siup_diunggah = case when p_sudah then now() end, siup_oleh = case when p_sudah then v_oleh end
   where id = any(p_ids);
  get diagnostics v_n = row_count;
  return v_n;
end;
$$;

CREATE FUNCTION public.ta_syarat_bimbingan_hitung(p_nim text, p_tahap text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_min int; v_sejak date; v_n int; v_sebelum text;
begin
  select minimal into v_min from ta_syarat_bimbingan where tahap = p_tahap;
  v_min := coalesce(v_min, 0);
  v_sebelum := case p_tahap when 'seminar_kemajuan' then 'seminar_proposal' when 'sidang_akhir' then 'seminar_kemajuan' end;
  if v_sebelum is not null then
    select max(t.tanggal) into v_sejak from jadwal_ta t
     where upper(btrim(coalesce(t.nim, ''))) = upper(btrim(p_nim)) and t.tahap = v_sebelum
       and t.status = 'selesai' and t.hasil in ('lulus', 'lulus_revisi');
  end if;
  select count(*) into v_n from ta_bimbingan b
   where upper(btrim(b.nim)) = upper(btrim(p_nim)) and ta_bimbingan_sah(b.status, b.diajukan) and (v_sejak is null or b.tanggal > v_sejak);
  return jsonb_build_object('tahap', p_tahap, 'minimal', v_min, 'terhitung', v_n, 'sejak', v_sejak, 'cukup', v_n >= v_min);
end;
$$;

CREATE FUNCTION public.ta_syarat_urutan(p_nim text, p_tahap text) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare v_sebelum text; v_nama text; j jadwal_ta; v_nim text := upper(btrim(coalesce(p_nim, '')));
begin
  v_sebelum := case p_tahap when 'seminar_kemajuan' then 'seminar_proposal' when 'sidang_akhir' then 'seminar_kemajuan' end;
  if v_sebelum is null then return null; end if;                                  -- proposal / penetapan pembimbing
  if exists (select 1 from ta_kecuali_urutan k where upper(btrim(k.nim)) = v_nim and k.tahap = p_tahap) then return null; end if;
  if exists (select 1 from jadwal_ta t where upper(btrim(coalesce(t.nim, ''))) = v_nim and t.tahap = v_sebelum
               and t.status = 'selesai'
               and (t.hasil = 'lulus' or (t.hasil = 'lulus_revisi' and t.revisi_selesai is not null))) then
    return null; end if;

  v_nama := case v_sebelum when 'seminar_proposal' then 'seminar proposal' else 'seminar kemajuan' end;
  -- Catatan terakhir tahap sebelumnya (yang batal diabaikan) menentukan pesan.
  select * into j from jadwal_ta t where upper(btrim(coalesce(t.nim, ''))) = v_nim and t.tahap = v_sebelum and t.status <> 'batal'
   order by t.tanggal desc, t.id desc limit 1;
  return (case p_tahap when 'seminar_kemajuan' then 'Seminar kemajuan' else 'Sidang akhir' end)
    || ' baru bisa didaftarkan setelah ' || v_nama || ' lulus dan revisinya dinyatakan selesai. '
    || case
         when j.id is null then 'Belum ada catatan ' || v_nama || ' untuk NIM ini. Bila Anda sudah melaluinya sebelum pendaftaran'
                              || ' lewat situs, minta koordinator TA mencatatnya.'
         when j.status in ('terjadwal', 'ditunda') then initcap(v_nama) || ' Anda belum selesai (jadwal '
                              || to_char(j.tanggal, 'DD-MM-YYYY') || ', ' || j.status || ').'
         when j.hasil is null then 'Hasil ' || v_nama || ' Anda belum dicatat; hubungi koordinator TA.'
         when j.hasil = 'mengulang' then 'Hasil ' || v_nama || ' Anda: mengulang. Daftarkan ' || v_nama || ' lagi.'
         else 'Revisi ' || v_nama || ' Anda belum dinyatakan selesai oleh pembimbing'
              || coalesce(' (tenggat ' || to_char(j.batas_revisi, 'DD-MM-YYYY') || ')', '') || '.'
       end;
end;
$$;

CREATE FUNCTION public.ta_tetapkan_pembimbing(p_id bigint, p_dosen uuid, p_dosen2 uuid DEFAULT NULL::uuid, p_alasan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare p pengajuan_mahasiswa; v_lama text; v_baru text; v_dua text; v_oleh text; v_alasan text := nullif(btrim(coalesce(p_alasan, '')), '');
        v_cocok boolean;
begin
  if not boleh_pengajuan('ta') then raise exception 'Pembimbing TA ditetapkan koordinator TA atau admin.'; end if;
  select * into p from pengajuan_mahasiswa where id = p_id for update;
  if p.id is null or p.jenis <> 'ta' or coalesce(p.data ->> 'tahap_ta', '') <> 'penetapan_pembimbing' then
    raise exception 'Pengajuan pembimbing TA tidak ditemukan.'; end if;
  if p.status not in ('pembimbing', 'admin') then raise exception 'Pembimbing hanya bisa ditetapkan pada pengajuan yang sedang diperiksa.'; end if;
  if not exists (select 1 from pembimbing_pilihan() x where x.id = p_dosen) then raise exception 'Pilih pembimbing 1 dari daftar.'; end if;
  if p_dosen2 is not null and not exists (select 1 from pembimbing_pilihan() x where x.id = p_dosen2) then
    raise exception 'Pilih pembimbing 2 dari daftar.'; end if;
  if p_dosen2 = p_dosen then raise exception 'Pembimbing 2 harus berbeda dari pembimbing 1.'; end if;
  v_cocok := ta_kk_cocok(p.data ->> 'kk_ta', (select d.kelompok_keahlian from dosen d where d.id = p_dosen));
  if not v_cocok and (v_alasan is null or length(v_alasan) < 5) then
    raise exception 'Pembimbing 1 di luar kelompok keahlian TA: tulis alasannya.'; end if;
  if p.pembimbing_id = p_dosen and (p.data ->> 'pembimbing_2') is not distinct from p_dosen2::text
     and (v_cocok or (p.data ->> 'alasan_luar_kk') is not distinct from v_alasan) then return 'tetap'; end if;
  select nama into v_lama from dosen where id = p.pembimbing_id;
  select nama into v_baru from dosen where id = p_dosen;
  select nama into v_dua from dosen where id = p_dosen2;
  select nama into v_oleh from dosen where id = me();
  update pengajuan_mahasiswa set pembimbing_id = p_dosen, diperbarui = now(),
         data = (data - 'pembimbing_2' - 'alasan_luar_kk')
                || jsonb_strip_nulls(jsonb_build_object('pembimbing_2', p_dosen2::text,
                                                        'alasan_luar_kk', case when v_cocok then null else left(v_alasan, 600) end))
   where id = p.id;
  insert into pengajuan_riwayat (pengajuan_id, status, oleh, catatan, tahap)
  values (p.id, p.status, coalesce(v_oleh, 'prodi') || ' (koordinator TA/admin)',
          'Pembimbing 1 ditetapkan: ' || v_baru || case when v_lama is distinct from v_baru then coalesce(' (sebelumnya ' || v_lama || ')', '') else '' end
          || '; pembimbing 2: ' || coalesce(v_dua, 'tidak ada')
          || case when v_cocok then '' else '. Di luar kelompok keahlian TA: ' || left(v_alasan, 600) end, p.tahap);
  return 'diganti';
end;
$$;

CREATE FUNCTION public.tanya_jawab_publik() RETURNS TABLE(id bigint, topik text, pertanyaan text, jawaban text, urutan integer, diperbarui timestamp with time zone)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select t.id, t.topik, t.pertanyaan, t.jawaban, t.urutan, t.diperbarui
    from public.tanya_jawab t
   where t.tampil
   order by t.topik nulls last, t.urutan, t.id
   limit 500;
$$;

CREATE FUNCTION public.term_urut(p_ta text, p_semester text) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $$
  select substr(p_ta, 1, 4)::int * 10 + case p_semester when 'Genap' then 2 else 1 end
$$;

CREATE FUNCTION public.tim_hibah(a uuid) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (select 1 from public.hibah_tim t where t.ajuan_id = a and t.dosen_id = public.me())
      or exists (select 1 from public.hibah_ajuan h where h.id = a and h.dibuat_oleh = public.me())
$$;

CREATE FUNCTION public.tinjauan_ajukan(p_id bigint) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t mk_rps_tinjauan;
begin
  select * into t from mk_rps_tinjauan where id = p_id for update;
  if t.id is null then raise exception 'Tinjauan tidak ditemukan; simpan dulu.'; end if;
  if not tinjauan_boleh(t.kurikulum, t.kode_mk, t.tahun_akademik, t.semester) then
    raise exception 'Tinjauan diajukan koordinator MK (atau MK padanannya) atau pengampu kelas MK ini pada semester itu.'; end if;
  if t.status not in ('draf', 'dikembalikan') then raise exception 'Tinjauan sudah diajukan atau disetujui.'; end if;
  if exists (select 1 from unnest(array['analisis_cpl', 'materi_metode', 'penilaian', 'pembaruan']) k where coalesce(btrim(t.data ->> k), '') = '') then
    raise exception 'Isi keempat bagian tinjauan: analisis CPL, materi dan metode, metode penilaian, pembaruan materi.'; end if;
  if t.keputusan is null then raise exception 'Pilih keputusan: RPS tetap, direvisi, atau MK tidak berlanjut.'; end if;
  if t.keputusan = 'revisi' and coalesce(btrim(t.data ->> 'rencana'), '') = '' then raise exception 'Tulis rencana perubahan RPS (tindak lanjut).'; end if;
  if t.keputusan = 'revisi' and not exists (select 1 from tinjauan_sasaran(t.kurikulum, t.kode_mk)) then
    raise exception 'MK ini belum punya RPS sasaran (padanan kurikulum baru); minta admin melengkapi padanan.'; end if;
  if t.keputusan = 'tidak_berlanjut' and not exists (select 1 from ref_mk_padanan p
       where p.kurikulum_lama = t.kurikulum and p.kode_lama = t.kode_mk and p.tidak_berlanjut) then
    raise exception 'Keputusan "MK tidak berlanjut" hanya untuk MK yang di daftar padanan ditandai tidak berlanjut.'; end if;
  perform set_config('tinjauan.fungsi', '1', true);
  update mk_rps_tinjauan set status = 'diajukan', diperbarui = now() where id = p_id;
  insert into mk_rps_tinjauan_log (tinjauan_id, aksi, oleh_id, oleh_nama) values (p_id, 'ajukan', me(), (select coalesce(nama_gelar, nama) from dosen where id = me()));
  return 'diajukan';
end $$;

CREATE FUNCTION public.tinjauan_boleh(p_kurikulum text, p_kode text, p_ta text, p_semester text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select public.me() is not null and (
    exists (select 1 from public.ref_mata_kuliah m join public.dosen d on d.id = public.me()
             where m.kurikulum = p_kurikulum and m.kode = p_kode and d.nidn = any(m.pengampu))
    or exists (select 1 from public.ref_mk_padanan p
                 join public.ref_mata_kuliah m on m.kurikulum = p.kurikulum_baru and m.kode = p.kode_baru
                 join public.dosen d on d.id = public.me()
                where p.kurikulum_lama = p_kurikulum and p.kode_lama = p_kode and d.nidn = any(m.pengampu))
    or exists (select 1 from public.cpl_kelas k
                where upper(k.kode_mk) = upper(p_kode) and k.tahun_akademik = p_ta and k.semester = p_semester
                  and lower(k.dosen_email) = lower(auth.jwt() ->> 'email'))
    or public.mengajar_kelas(p_ta, p_semester, p_kode, null))
$$;

CREATE FUNCTION public.tinjauan_nilai_ada(p_kurikulum text, p_kode text, p_ta text, p_semester text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select exists (
    select 1 from jsonb_array_elements(coalesce((select r.data -> 'berkas' from public.cpl_ringkasan r order by r.diunggah desc, r.id desc limit 1), '[]'::jsonb)) b
     where upper(b ->> 'course_code') = upper(p_kode) and b ->> 'term' = p_ta || ' ' || p_semester
       and coalesce(b ->> 'jenis', 'nilai_akhir') = 'nilai_akhir' and coalesce(nullif(b ->> 'curriculum', ''), p_kurikulum) = p_kurikulum)
$$;

CREATE FUNCTION public.tinjauan_putuskan(p_id bigint, p_aksi text, p_catatan text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare t mk_rps_tinjauan; v_catatan text := nullif(btrim(coalesce(p_catatan, '')), ''); v_sendiri boolean; v_dasar jsonb;
begin
  if not koordinator_aktif('kaprodi') then raise exception 'Tinjauan RPS disetujui Kaprodi aktif (Penugasan koordinator).'; end if;
  select * into t from mk_rps_tinjauan where id = p_id for update;
  if t.id is null or t.status <> 'diajukan' then raise exception 'Tinjauan tidak sedang diajukan.'; end if;
  if p_aksi not in ('setujui', 'kembalikan') then raise exception 'Aksi tidak dikenal.'; end if;
  if p_aksi = 'kembalikan' and v_catatan is null then raise exception 'Tulis catatan untuk koordinator MK.'; end if;
  v_sendiri := tinjauan_boleh(t.kurikulum, t.kode_mk, t.tahun_akademik, t.semester)
    or coalesce((select l.oleh_id = me() from mk_rps_tinjauan_log l where l.tinjauan_id = p_id and l.aksi = 'ajukan' order by l.id desc limit 1), false);
  perform set_config('tinjauan.fungsi', '1', true);
  if p_aksi = 'kembalikan' then
    update mk_rps_tinjauan set status = 'dikembalikan', diperbarui = now() where id = p_id;
  else
    select coalesce(jsonb_object_agg(s.kurikulum || '|' || s.kode, coalesce(r.revisi, 0)), '{}'::jsonb) into v_dasar
      from tinjauan_sasaran(t.kurikulum, t.kode_mk) s left join mk_rps r on r.kurikulum = s.kurikulum and r.kode_mk = s.kode;
    update mk_rps_tinjauan set status = 'disetujui', disetujui_pada = now(), disetujui_oleh = me(), rps_dasar = v_dasar, diperbarui = now() where id = p_id;
    -- Revisi: RPS sasaran yang sudah disahkan menjadi draf supaya diajukan ulang (salinan sah, revisi, RPS ada tetap; 112/114).
    if t.keputusan = 'revisi' then
      update mk_rps r set status = 'draf' from tinjauan_sasaran(t.kurikulum, t.kode_mk) s
       where r.kurikulum = s.kurikulum and r.kode_mk = s.kode and r.status = 'disahkan';
    end if;
  end if;
  insert into mk_rps_tinjauan_log (tinjauan_id, aksi, oleh_id, oleh_nama, catatan, penyusun_sendiri)
  values (p_id, p_aksi, me(), (select coalesce(nama_gelar, nama) from dosen where id = me()), left(v_catatan, 2000), p_aksi = 'setujui' and v_sendiri);
  return case when p_aksi = 'setujui' then 'disetujui' else 'dikembalikan' end;
end $$;

CREATE FUNCTION public.tinjauan_sasaran(p_kurikulum text, p_kode text) RETURNS TABLE(kurikulum text, kode text)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select p.kurikulum_baru, p.kode_baru from public.ref_mk_padanan p
   where p.kurikulum_lama = p_kurikulum and p.kode_lama = p_kode and not p.tidak_berlanjut
  union all
  select m.kurikulum, m.kode from public.ref_mata_kuliah m
   where m.kurikulum = p_kurikulum and m.kode = p_kode and coalesce(m.aktif, true)
     and not exists (select 1 from public.ref_mk_padanan p where p.kurikulum_lama = p_kurikulum and p.kode_lama = p_kode)
$$;

CREATE FUNCTION public.ts_dari(p date) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $$
  select extract(year from p)::int + case when extract(month from p) >= 9 then 1 else 0 end
$$;

CREATE FUNCTION public.turunkan_kategori_lkps() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
begin
  if new.skema_kode is not null then
    select r.sumber_dana_lkps into new.sumber_dana
    from public.ref_skema_dana r where r.kode = new.skema_kode;
  end if;

  if new.kategori_pub_kode is not null then
    select p.tingkat_lkps, coalesce(p.indeksasi_lkps, new.indeksasi)
      into new.tingkat, new.indeksasi
    from public.ref_kategori_publikasi p where p.kode = new.kategori_pub_kode;
  end if;

  -- luaran (HKI umumnya pendaftaran nasional) dan integrasi (tingkat
  -- tidak bermakna): isi 'nasional' bila form tidak mengirimnya.
  if new.kategori in ('luaran','integrasi') and new.tingkat is null then
    new.tingkat := 'nasional';
  end if;

  return new;
end $$;

CREATE FUNCTION public.ubah_karya(k uuid, d jsonb) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
declare
  pelapor uuid;
  st      text;
begin
  select dilaporkan_oleh, status into pelapor, st from public.karya where id = k;
  if not found then raise exception 'Karya tidak ditemukan.'; end if;
  if not (public.is_admin()
          or (pelapor = public.me() and st <> 'terverifikasi')) then
    raise exception 'Karya ini hanya bisa diubah lewat ajuan perubahan.';
  end if;
  perform public._terapkan_karya(k, d);
  -- Diperbaiki pelapor -> kembali menunggu verifikasi; draf tetap draf.
  if not public.is_admin() then
    update public.karya set status = case when st = 'draf' then 'draf' else 'diajukan' end,
                            catatan = null
    where id = k;
  end if;
end $$;

CREATE FUNCTION public.unsur_bukti() RETURNS TABLE(tabel text, baris_id bigint, unsur smallint)
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select distinct b.tabel, b.baris_id, b.unsur
    from public.lkps_bukti b
   where b.unsur is not null
     and b.tabel in ('ref_mata_kuliah', 'lkps_peta_jalan')
     and public.me() is not null
  union
  select distinct 'butir', bb.butir::bigint, bb.unsur
    from public.butir_bukti bb
   where bb.unsur is not null
     and public.me() is not null;
$$;

CREATE FUNCTION public.yudisium_berkas_daftar() RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
  select coalesce(jsonb_agg(jsonb_build_object('kode', kode, 'label', label, 'keterangan', keterangan, 'wajib', wajib)
                            order by urut, kode), '[]'::jsonb)
    from yudisium_berkas where aktif
$$;

CREATE TABLE public.ajuan_bkd (
    id bigint NOT NULL,
    bkd_id bigint NOT NULL,
    data jsonb NOT NULL,
    lama jsonb,
    alasan text NOT NULL,
    oleh uuid DEFAULT public.me() NOT NULL,
    status text DEFAULT 'menunggu'::text NOT NULL,
    catatan_admin text,
    dibuat_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ajuan_bkd_status_check CHECK ((status = ANY (ARRAY['menunggu'::text, 'ditolak'::text])))
);

ALTER TABLE public.ajuan_bkd ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ajuan_bkd_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ajuan_hapus (
    id bigint NOT NULL,
    karya_id uuid NOT NULL,
    alasan text NOT NULL,
    oleh uuid DEFAULT public.me(),
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ajuan_hapus_alasan_check CHECK ((length(TRIM(BOTH FROM alasan)) > 0))
);

ALTER TABLE public.ajuan_hapus ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ajuan_hapus_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ajuan_prestasi (
    id bigint NOT NULL,
    prestasi_id bigint NOT NULL,
    hapus boolean DEFAULT false NOT NULL,
    data jsonb,
    lama jsonb,
    alasan text NOT NULL,
    oleh uuid DEFAULT public.me() NOT NULL,
    status text DEFAULT 'menunggu'::text NOT NULL,
    catatan_admin text,
    dibuat_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ajuan_prestasi_check CHECK ((hapus OR (data IS NOT NULL))),
    CONSTRAINT ajuan_prestasi_status_check CHECK ((status = ANY (ARRAY['menunggu'::text, 'ditolak'::text])))
);

ALTER TABLE public.ajuan_prestasi ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ajuan_prestasi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ajuan_ubah (
    id bigint NOT NULL,
    jenis text NOT NULL,
    karya_id uuid,
    dosen_id uuid,
    data jsonb NOT NULL,
    lama jsonb,
    alasan text,
    oleh uuid DEFAULT public.me() NOT NULL,
    status text DEFAULT 'menunggu'::text NOT NULL,
    catatan_admin text,
    dibuat_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ajuan_ubah_check CHECK ((((jenis = 'karya'::text) AND (karya_id IS NOT NULL) AND (dosen_id IS NULL)) OR ((jenis = 'profil'::text) AND (dosen_id IS NOT NULL) AND (karya_id IS NULL)))),
    CONSTRAINT ajuan_ubah_jenis_check CHECK ((jenis = ANY (ARRAY['karya'::text, 'profil'::text]))),
    CONSTRAINT ajuan_ubah_status_check CHECK ((status = ANY (ARRAY['menunggu'::text, 'ditolak'::text])))
);

ALTER TABLE public.ajuan_ubah ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ajuan_ubah_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ami_temuan (
    id bigint NOT NULL,
    siklus text,
    tahun_ts integer NOT NULL,
    tanggal_audit date,
    kode text,
    standar text,
    butir smallint,
    kategori text NOT NULL,
    uraian text NOT NULL,
    akar_masalah text,
    rencana text,
    pihak text,
    pj_nama text,
    pj_email text,
    tenggat date,
    status text DEFAULT 'terbuka'::text NOT NULL,
    tanggal_selesai date,
    verifikasi text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    standar_id bigint,
    CONSTRAINT ami_temuan_butir_rentang CHECK (((butir IS NULL) OR ((butir >= 1) AND (butir <= 999)))),
    CONSTRAINT ami_temuan_kategori_check CHECK ((kategori = ANY (ARRAY['observasi'::text, 'kts_minor'::text, 'kts_mayor'::text, 'peluang'::text]))),
    CONSTRAINT ami_temuan_kode_check CHECK ((length(kode) <= 30)),
    CONSTRAINT ami_temuan_pihak_check CHECK ((pihak = ANY (ARRAY['U'::text, 'F'::text, 'P'::text, 'S'::text, 'D'::text]))),
    CONSTRAINT ami_temuan_pj_email_check CHECK (((pj_email IS NULL) OR (pj_email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text))),
    CONSTRAINT ami_temuan_siklus_check CHECK ((length(siklus) <= 120)),
    CONSTRAINT ami_temuan_status_check CHECK ((status = ANY (ARRAY['terbuka'::text, 'proses'::text, 'selesai'::text, 'ditutup'::text]))),
    CONSTRAINT ami_temuan_tahun_ts_check CHECK (((tahun_ts >= 2000) AND (tahun_ts <= 2100)))
);

ALTER TABLE public.ami_temuan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ami_temuan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.berhalangan_konfirmasi (
    dosen_id uuid NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    dikonfirmasi_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT berhalangan_konfirmasi_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT berhalangan_konfirmasi_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

CREATE TABLE public.butir_bukti (
    id bigint NOT NULL,
    butir smallint NOT NULL,
    jenis_dokumen text,
    dokumen_id bigint,
    judul text DEFAULT ''::text NOT NULL,
    url text,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    sha256 text,
    unsur smallint,
    CONSTRAINT butir_bukti_butir_rentang CHECK (((butir >= 1) AND (butir <= 999))),
    CONSTRAINT butir_bukti_jenis_dokumen_check CHECK ((jenis_dokumen ~ '^[a-z0-9_]{2,40}$'::text)),
    CONSTRAINT butir_bukti_satu_sumber CHECK ((((((jenis_dokumen IS NOT NULL))::integer + ((dokumen_id IS NOT NULL))::integer) + ((url IS NOT NULL))::integer) = 1)),
    CONSTRAINT butir_bukti_sha256_check CHECK (((sha256 IS NULL) OR (sha256 ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT butir_bukti_unsur_check CHECK (((unsur IS NULL) OR ((unsur >= 1) AND (unsur <= 30)))),
    CONSTRAINT butir_bukti_url_check CHECK ((url ~* '^https?://[^ ]+$'::text))
);

ALTER TABLE public.butir_bukti ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.butir_bukti_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.cpl_berkas (
    id bigint NOT NULL,
    kelas_id bigint NOT NULL,
    url text NOT NULL,
    nama_berkas text,
    ukuran integer,
    sha256 text,
    diunggah timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT cpl_berkas_nama_berkas_check CHECK ((length(nama_berkas) <= 200)),
    CONSTRAINT cpl_berkas_sha256_check CHECK (((sha256 IS NULL) OR (sha256 ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT cpl_berkas_ukuran_check CHECK ((ukuran >= 0)),
    CONSTRAINT cpl_berkas_url_check CHECK ((url ~* '^https://\S+$'::text))
);

ALTER TABLE public.cpl_berkas ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.cpl_berkas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.cpl_kelas (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    kode_mk text NOT NULL,
    nama_mk text,
    kelas text NOT NULL,
    dosen_email text NOT NULL,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT cpl_kelas_dosen_email_check CHECK ((dosen_email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text)),
    CONSTRAINT cpl_kelas_kelas_check CHECK (((length(kelas) >= 1) AND (length(kelas) <= 10))),
    CONSTRAINT cpl_kelas_kode_mk_check CHECK (((length(kode_mk) >= 1) AND (length(kode_mk) <= 20))),
    CONSTRAINT cpl_kelas_nama_mk_check CHECK ((length(nama_mk) <= 150)),
    CONSTRAINT cpl_kelas_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text, 'Pendek'::text]))),
    CONSTRAINT cpl_kelas_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.cpl_kelas ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.cpl_kelas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.cpl_ringkasan (
    id bigint NOT NULL,
    dibuat timestamp with time zone,
    diunggah timestamp with time zone DEFAULT now() NOT NULL,
    data jsonb NOT NULL,
    catatan text,
    oleh text,
    CONSTRAINT cpl_ringkasan_catatan_check CHECK ((length(catatan) <= 200)),
    CONSTRAINT cpl_ringkasan_data_check CHECK (((jsonb_typeof(data) = 'object'::text) AND ((data ->> 'versi'::text) = '1'::text) AND (pg_column_size(data) <= 5000000)))
);

ALTER TABLE public.cpl_ringkasan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.cpl_ringkasan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.dokumen (
    id bigint NOT NULL,
    jenis text NOT NULL,
    tahun integer NOT NULL,
    judul text DEFAULT ''::text NOT NULL,
    url text NOT NULL,
    folder_url text,
    nama_berkas text,
    butir text[] DEFAULT '{}'::text[] NOT NULL,
    diunggah_oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    nomor text,
    tanggal date,
    sha256 text,
    berlaku_sampai date,
    untuk_mahasiswa boolean DEFAULT false NOT NULL,
    CONSTRAINT dokumen_berlaku_check CHECK (((berlaku_sampai IS NULL) OR (tanggal IS NULL) OR (berlaku_sampai >= tanggal))),
    CONSTRAINT dokumen_jenis_check CHECK ((jenis ~ '^[a-z0-9_]{2,40}$'::text)),
    CONSTRAINT dokumen_sha256_check CHECK (((sha256 IS NULL) OR (sha256 ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT dokumen_tahun_check CHECK (((tahun >= 1990) AND (tahun <= 2100))),
    CONSTRAINT dokumen_url_check CHECK ((url ~* '^https?://'::text))
);

COMMENT ON TABLE public.dokumen IS 'Dokumen bukti bernama; jenis di site/rencana-bukti.js. Unik (jenis, tahun, judul).';

ALTER TABLE public.dokumen ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.dokumen_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.dosen (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    nidn text NOT NULL,
    nama text NOT NULL,
    email text,
    peran text DEFAULT 'dosen'::text NOT NULL,
    sinta_id text,
    scopus_id text,
    orcid text,
    aktif boolean DEFAULT true NOT NULL,
    diubah_pada timestamp with time zone DEFAULT now() NOT NULL,
    dtps boolean DEFAULT true NOT NULL,
    pendidikan text,
    jabatan text,
    kategori text,
    riwayat_pendidikan jsonb DEFAULT '[]'::jsonb NOT NULL,
    bidang_keahlian text,
    perusahaan text,
    sesuai_kompetensi_inti boolean,
    nomor_serdos text,
    sertifikat jsonb DEFAULT '[]'::jsonb NOT NULL,
    skip text,
    stri text,
    mk_ps_lain text,
    sesuai_keahlian_mk boolean,
    tim_penyusun boolean DEFAULT false NOT NULL,
    kata_kunci text[],
    topik_keahlian text[],
    email_alternatif text,
    foto_url text,
    kelompok_keahlian text,
    tugas_belajar text,
    nip text,
    nama_gelar text,
    terakhir_aktif timestamp with time zone,
    nuptk text,
    tautan_lain jsonb,
    boleh_masuk boolean DEFAULT true NOT NULL,
    tugas_belajar_mulai date,
    tugas_belajar_selesai date,
    CONSTRAINT dosen_admin_boleh_masuk_check CHECK (((peran <> 'admin'::text) OR boleh_masuk)),
    CONSTRAINT dosen_email_isi_check CHECK (((email IS NULL) OR (btrim(email) <> ''::text))),
    CONSTRAINT dosen_foto_url_check CHECK (((foto_url IS NULL) OR (foto_url ~* '^https://drive\.google\.com/\S+$'::text))),
    CONSTRAINT dosen_jabatan_check CHECK (((jabatan IS NULL) OR (jabatan = ANY (ARRAY['tenaga_pengajar'::text, 'asisten_ahli'::text, 'lektor'::text, 'lektor_kepala'::text, 'guru_besar'::text])))),
    CONSTRAINT dosen_kata_kunci_check CHECK (((kata_kunci IS NULL) OR (cardinality(kata_kunci) <= 10))),
    CONSTRAINT dosen_kategori_check CHECK (((kategori IS NULL) OR (kategori = ANY (ARRAY['tetap'::text, 'tidak_tetap'::text, 'industri'::text])))),
    CONSTRAINT dosen_kelompok_keahlian_check CHECK (((kelompok_keahlian IS NULL) OR (kelompok_keahlian ~ '^[A-Z0-9]{2,12}$'::text))),
    CONSTRAINT dosen_nama_gelar_panjang CHECK (((nama_gelar IS NULL) OR ((length(nama_gelar) >= 3) AND (length(nama_gelar) <= 200)))),
    CONSTRAINT dosen_nip_format CHECK (((nip IS NULL) OR (nip ~ '^[0-9A-Za-z][0-9A-Za-z ./-]{1,38}[0-9A-Za-z]$'::text))),
    CONSTRAINT dosen_nuptk_format CHECK (((nuptk IS NULL) OR (nuptk ~ '^[0-9A-Za-z][0-9A-Za-z ./-]{1,38}[0-9A-Za-z]$'::text))),
    CONSTRAINT dosen_pendidikan_check CHECK (((pendidikan IS NULL) OR (pendidikan = ANY (ARRAY['S2'::text, 'S3'::text])))),
    CONSTRAINT dosen_peran_check CHECK ((peran = ANY (ARRAY['dosen'::text, 'admin'::text, 'asesor'::text, 'pimpinan'::text]))),
    CONSTRAINT dosen_riwayat_pendidikan_check CHECK ((jsonb_typeof(riwayat_pendidikan) = 'array'::text)),
    CONSTRAINT dosen_sertifikat_check CHECK ((jsonb_typeof(sertifikat) = 'array'::text)),
    CONSTRAINT dosen_skip_check CHECK (((skip IS NULL) OR (skip = ANY (ARRAY['IPM'::text, 'IPU'::text])))),
    CONSTRAINT dosen_tautan_lain_check CHECK (((tautan_lain IS NULL) OR ((jsonb_typeof(tautan_lain) = 'array'::text) AND (jsonb_array_length(tautan_lain) <= 5)))),
    CONSTRAINT dosen_topik_keahlian_check CHECK (((topik_keahlian IS NULL) OR (cardinality(topik_keahlian) <= 15))),
    CONSTRAINT dosen_tugas_belajar_bukan_dtps CHECK (((tugas_belajar IS NULL) OR (dtps IS NOT TRUE))),
    CONSTRAINT dosen_tugas_belajar_panjang CHECK (((tugas_belajar IS NULL) OR ((length(btrim(tugas_belajar)) >= 2) AND (length(btrim(tugas_belajar)) <= 200)))),
    CONSTRAINT dosen_tugas_belajar_periode_check CHECK (((tugas_belajar_selesai IS NULL) OR (tugas_belajar_mulai IS NULL) OR (tugas_belajar_selesai >= tugas_belajar_mulai))),
    CONSTRAINT dosen_tugas_belajar_tanggal_check CHECK (((tugas_belajar IS NOT NULL) OR ((tugas_belajar_mulai IS NULL) AND (tugas_belajar_selesai IS NULL))))
);

COMMENT ON COLUMN public.dosen.boleh_masuk IS 'Boleh masuk situs (155, pemilik 2026-11-22). false = tidak bisa masuk walau email tercatat; tetap ada di daftar dan dihitung akreditasi bila mengampu MK pada TS.';

COMMENT ON COLUMN public.dosen.tugas_belajar_mulai IS 'Mulai tugas belajar (156, pemilik 2026-11-22); tidak dihitung DTPS pada TS yang beririsan.';

COMMENT ON COLUMN public.dosen.tugas_belajar_selesai IS 'Selesai tugas belajar (156); kosong = masih tugas belajar.';

CREATE TABLE public.dosen_ampu_ts (
    dosen_id uuid NOT NULL,
    tahun_akademik text NOT NULL,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT dosen_ampu_ts_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

CREATE TABLE public.dosen_berhalangan (
    id bigint NOT NULL,
    dosen_id uuid NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    hari smallint NOT NULL,
    slot_id bigint NOT NULL,
    jenis text DEFAULT 'lainnya'::text NOT NULL,
    alasan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT dosen_berhalangan_alasan_check CHECK (((alasan IS NULL) OR (length(alasan) <= 200))),
    CONSTRAINT dosen_berhalangan_hari_check CHECK (((hari >= 1) AND (hari <= 7))),
    CONSTRAINT dosen_berhalangan_jenis_check CHECK ((jenis = ANY (ARRAY['prodi_lain'::text, 'institusi'::text, 'luar'::text, 'lainnya'::text]))),
    CONSTRAINT dosen_berhalangan_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT dosen_berhalangan_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.dosen_berhalangan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.dosen_berhalangan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.dosen_berhalangan_rentang (
    id bigint NOT NULL,
    dosen_id uuid NOT NULL,
    mulai date NOT NULL,
    selesai date NOT NULL,
    hari smallint[],
    slot_ids bigint[],
    jenis text DEFAULT 'lainnya'::text NOT NULL,
    alasan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT dosen_berhalangan_rentang_alasan_check CHECK (((alasan IS NULL) OR (length(alasan) <= 200))),
    CONSTRAINT dosen_berhalangan_rentang_check CHECK (((selesai >= mulai) AND ((selesai - mulai) <= 366))),
    CONSTRAINT dosen_berhalangan_rentang_hari_check CHECK (((hari IS NULL) OR ((cardinality(hari) >= 1) AND (cardinality(hari) <= 7)))),
    CONSTRAINT dosen_berhalangan_rentang_hari_check1 CHECK (((hari IS NULL) OR ((1 <= ALL (hari)) AND (7 >= ALL (hari))))),
    CONSTRAINT dosen_berhalangan_rentang_jenis_check CHECK ((jenis = ANY (ARRAY['prodi_lain'::text, 'institusi'::text, 'luar'::text, 'lainnya'::text]))),
    CONSTRAINT dosen_berhalangan_rentang_slot_ids_check CHECK (((slot_ids IS NULL) OR ((cardinality(slot_ids) >= 1) AND (cardinality(slot_ids) <= 30))))
);

ALTER TABLE public.dosen_berhalangan_rentang ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.dosen_berhalangan_rentang_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.dosen_berhalangan_tgl (
    id bigint NOT NULL,
    dosen_id uuid NOT NULL,
    tanggal date NOT NULL,
    slot_id bigint,
    jenis text DEFAULT 'lainnya'::text NOT NULL,
    alasan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT dosen_berhalangan_tgl_alasan_check CHECK (((alasan IS NULL) OR (length(alasan) <= 200))),
    CONSTRAINT dosen_berhalangan_tgl_jenis_check CHECK ((jenis = ANY (ARRAY['prodi_lain'::text, 'institusi'::text, 'luar'::text, 'lainnya'::text])))
);

ALTER TABLE public.dosen_berhalangan_tgl ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.dosen_berhalangan_tgl_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.evaluasi_mk (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    kode_mk text NOT NULL,
    nama_mk text,
    dosen_id uuid NOT NULL,
    edom numeric(3,2),
    edom_responden integer,
    rps_sesuai text,
    rps_catatan text,
    metode_catatan text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT evaluasi_mk_edom_check CHECK (((edom >= (0)::numeric) AND (edom <= (4)::numeric))),
    CONSTRAINT evaluasi_mk_edom_responden_check CHECK ((edom_responden >= 0)),
    CONSTRAINT evaluasi_mk_kode_mk_check CHECK (((length(kode_mk) >= 1) AND (length(kode_mk) <= 20))),
    CONSTRAINT evaluasi_mk_metode_catatan_check CHECK (((metode_catatan IS NULL) OR (length(metode_catatan) <= 2000))),
    CONSTRAINT evaluasi_mk_nama_mk_check CHECK (((nama_mk IS NULL) OR (length(nama_mk) <= 150))),
    CONSTRAINT evaluasi_mk_rps_catatan_check CHECK (((rps_catatan IS NULL) OR (length(rps_catatan) <= 2000))),
    CONSTRAINT evaluasi_mk_rps_sesuai_check CHECK ((rps_sesuai = ANY (ARRAY['sesuai'::text, 'sebagian'::text, 'tidak'::text]))),
    CONSTRAINT evaluasi_mk_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT evaluasi_mk_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.evaluasi_mk ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.evaluasi_mk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.evaluasi_tindak (
    id bigint NOT NULL,
    evaluasi_id bigint NOT NULL,
    masalah text NOT NULL,
    penyebab text,
    rencana text NOT NULL,
    pj_id uuid,
    tenggat date,
    status text DEFAULT 'terbuka'::text NOT NULL,
    hasil text,
    tanggal_selesai date,
    standar_id bigint,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT evaluasi_tindak_check CHECK (((status <> 'selesai'::text) OR ((tanggal_selesai IS NOT NULL) AND (hasil IS NOT NULL)))),
    CONSTRAINT evaluasi_tindak_hasil_check CHECK (((hasil IS NULL) OR (length(hasil) <= 2000))),
    CONSTRAINT evaluasi_tindak_masalah_check CHECK (((length(masalah) >= 1) AND (length(masalah) <= 2000))),
    CONSTRAINT evaluasi_tindak_penyebab_check CHECK (((penyebab IS NULL) OR (length(penyebab) <= 2000))),
    CONSTRAINT evaluasi_tindak_rencana_check CHECK (((length(rencana) >= 1) AND (length(rencana) <= 2000))),
    CONSTRAINT evaluasi_tindak_status_check CHECK ((status = ANY (ARRAY['terbuka'::text, 'proses'::text, 'selesai'::text])))
);

ALTER TABLE public.evaluasi_tindak ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.evaluasi_tindak_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.hari_libur (
    tanggal date NOT NULL,
    nama text NOT NULL,
    jenis text DEFAULT 'nasional'::text NOT NULL,
    oleh text,
    dibuat_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT hari_libur_jenis_check CHECK ((jenis = ANY (ARRAY['nasional'::text, 'cuti_bersama'::text, 'kampus'::text]))),
    CONSTRAINT hari_libur_nama_check CHECK (((char_length(btrim(nama)) >= 2) AND (char_length(btrim(nama)) <= 200)))
);

CREATE TABLE public.hibah_ajuan (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    panggilan_id bigint,
    kategori text NOT NULL,
    judul text NOT NULL,
    skema_kode text,
    nama_pemberi_dana text,
    tahun_usulan integer NOT NULL,
    tenggat_ajuan date,
    tanggal_ajuan date,
    status text DEFAULT 'rencana'::text NOT NULL,
    dana_usulan numeric(14,0),
    dana_disetujui numeric(14,0),
    tahun_mulai integer,
    tenggat_kemajuan date,
    kemajuan_selesai date,
    tenggat_akhir date,
    akhir_selesai date,
    anggota_luar text,
    catatan text,
    karya_id uuid,
    dibuat_oleh uuid NOT NULL,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT hibah_ajuan_dana_disetujui_check CHECK (((dana_disetujui IS NULL) OR (dana_disetujui >= (0)::numeric))),
    CONSTRAINT hibah_ajuan_dana_usulan_check CHECK (((dana_usulan IS NULL) OR (dana_usulan >= (0)::numeric))),
    CONSTRAINT hibah_ajuan_judul_check CHECK ((length(judul) <= 500)),
    CONSTRAINT hibah_ajuan_kategori_check CHECK ((kategori = ANY (ARRAY['penelitian'::text, 'pkm'::text]))),
    CONSTRAINT hibah_ajuan_status_check CHECK ((status = ANY (ARRAY['rencana'::text, 'diajukan'::text, 'didanai'::text, 'ditolak'::text, 'batal'::text]))),
    CONSTRAINT hibah_ajuan_tahun_mulai_check CHECK (((tahun_mulai >= 2000) AND (tahun_mulai <= 2100))),
    CONSTRAINT hibah_ajuan_tahun_usulan_check CHECK (((tahun_usulan >= 2000) AND (tahun_usulan <= 2100)))
);

CREATE TABLE public.hibah_panggilan (
    id bigint NOT NULL,
    judul text NOT NULL,
    penyelenggara text,
    kategori text DEFAULT 'keduanya'::text NOT NULL,
    skema_kode text,
    tenggat date,
    tautan text,
    keterangan text,
    diumumkan timestamp with time zone,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT hibah_panggilan_judul_check CHECK ((length(judul) <= 300)),
    CONSTRAINT hibah_panggilan_kategori_check CHECK ((kategori = ANY (ARRAY['penelitian'::text, 'pkm'::text, 'keduanya'::text]))),
    CONSTRAINT hibah_panggilan_penyelenggara_check CHECK ((length(penyelenggara) <= 200)),
    CONSTRAINT hibah_panggilan_tautan_check CHECK (((tautan IS NULL) OR (tautan ~* '^https?://'::text)))
);

ALTER TABLE public.hibah_panggilan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.hibah_panggilan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.hibah_tim (
    ajuan_id uuid NOT NULL,
    dosen_id uuid NOT NULL,
    peran text DEFAULT 'anggota'::text NOT NULL,
    CONSTRAINT hibah_tim_peran_check CHECK ((peran = ANY (ARRAY['ketua'::text, 'anggota'::text])))
);

CREATE TABLE public.insentif_pengajuan (
    id bigint NOT NULL,
    judul text NOT NULL,
    tanggal date DEFAULT ((now() AT TIME ZONE 'Asia/Jakarta'::text))::date NOT NULL,
    catatan text,
    dibuat_oleh uuid DEFAULT public.me(),
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT insentif_pengajuan_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000))),
    CONSTRAINT insentif_pengajuan_judul_check CHECK (((length(btrim(judul)) >= 3) AND (length(btrim(judul)) <= 200)))
);

ALTER TABLE public.insentif_pengajuan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.insentif_pengajuan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.insentif_publikasi (
    id bigint NOT NULL,
    karya_id uuid NOT NULL,
    pengklaim_id uuid NOT NULL,
    status text DEFAULT 'diklaim'::text NOT NULL,
    catatan text,
    pengajuan_id bigint,
    diklaim_pada timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh uuid,
    CONSTRAINT insentif_pengajuan_status_check CHECK (((status = ANY (ARRAY['diajukan'::text, 'disetujui'::text, 'ditolak'::text, 'cair'::text])) = (pengajuan_id IS NOT NULL))),
    CONSTRAINT insentif_publikasi_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000))),
    CONSTRAINT insentif_publikasi_status_check CHECK ((status = ANY (ARRAY['diklaim'::text, 'dikembalikan'::text, 'siap'::text, 'diajukan'::text, 'disetujui'::text, 'ditolak'::text, 'cair'::text])))
);

ALTER TABLE public.insentif_publikasi ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.insentif_publikasi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.jadwal_hari (
    hari smallint NOT NULL,
    CONSTRAINT jadwal_hari_hari_check CHECK (((hari >= 1) AND (hari <= 7)))
);

CREATE TABLE public.jadwal_kuliah (
    kelas_id bigint NOT NULL,
    hari smallint NOT NULL,
    mulai time without time zone NOT NULL,
    selesai time without time zone NOT NULL,
    ruang text,
    kunci boolean DEFAULT false NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT jadwal_kuliah_check CHECK ((selesai > mulai)),
    CONSTRAINT jadwal_kuliah_hari_check CHECK (((hari >= 1) AND (hari <= 7))),
    CONSTRAINT jadwal_kuliah_ruang_check CHECK (((ruang IS NULL) OR ((length(btrim(ruang)) >= 1) AND (length(btrim(ruang)) <= 60))))
);

CREATE TABLE public.jadwal_kuliah_sah (
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    sah_oleh text,
    sah_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT jadwal_kuliah_sah_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT jadwal_kuliah_sah_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

CREATE TABLE public.jadwal_slot (
    id bigint NOT NULL,
    urutan integer DEFAULT 0 NOT NULL,
    label text NOT NULL,
    mulai time without time zone NOT NULL,
    selesai time without time zone NOT NULL,
    aktif boolean DEFAULT true NOT NULL,
    CONSTRAINT jadwal_slot_check CHECK ((selesai > mulai)),
    CONSTRAINT jadwal_slot_label_check CHECK (((length(btrim(label)) >= 1) AND (length(btrim(label)) <= 40)))
);

ALTER TABLE public.jadwal_slot ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.jadwal_slot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE public.jadwal_ta ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.jadwal_ta_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.jejak (
    id bigint NOT NULL,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    tabel text NOT NULL,
    baris text,
    aksi text NOT NULL,
    oleh text NOT NULL,
    ubah jsonb,
    isi jsonb,
    CONSTRAINT jejak_aksi_check CHECK ((aksi = ANY (ARRAY['tambah'::text, 'ubah'::text, 'hapus'::text])))
);

ALTER TABLE public.jejak ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.jejak_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.kabar_kegiatan (
    id bigint NOT NULL,
    judul text NOT NULL,
    tanggal date NOT NULL,
    jenis text DEFAULT 'lainnya'::text NOT NULL,
    tempat text,
    ringkasan text NOT NULL,
    tautan text,
    foto text[] DEFAULT '{}'::text[] NOT NULL,
    status text DEFAULT 'diajukan'::text NOT NULL,
    catatan text,
    dilaporkan_oleh uuid DEFAULT public.me(),
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    keterkaitan text[] DEFAULT '{}'::text[] NOT NULL,
    mata_kuliah text[] DEFAULT '{}'::text[] NOT NULL,
    narasumber text,
    kerjasama_id bigint,
    jumlah_mahasiswa integer,
    bukti text[] DEFAULT '{}'::text[] NOT NULL,
    tampil_publik boolean DEFAULT true NOT NULL,
    CONSTRAINT kabar_kegiatan_akreditasi_check CHECK (((keterkaitan <@ ARRAY['suasana_akademik'::text, 'pembelajaran'::text, 'kerja_sama'::text, 'pemangku'::text]) AND (cardinality(mata_kuliah) <= 10) AND ((narasumber IS NULL) OR (length(narasumber) <= 300)) AND ((jumlah_mahasiswa IS NULL) OR ((jumlah_mahasiswa >= 0) AND (jumlah_mahasiswa <= 5000))) AND (cardinality(bukti) <= 10))),
    CONSTRAINT kabar_kegiatan_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 1000))),
    CONSTRAINT kabar_kegiatan_foto_check CHECK ((cardinality(foto) <= 6)),
    CONSTRAINT kabar_kegiatan_jenis_check CHECK ((jenis = ANY (ARRAY['kuliah_tamu'::text, 'kunjungan_lapangan'::text, 'seminar'::text, 'penelitian'::text, 'pengabdian'::text, 'kerja_praktik'::text, 'kompetisi'::text, 'kerja_sama'::text, 'lainnya'::text]))),
    CONSTRAINT kabar_kegiatan_judul_check CHECK (((length(btrim(judul)) >= 3) AND (length(btrim(judul)) <= 200))),
    CONSTRAINT kabar_kegiatan_ringkasan_check CHECK (((length(btrim(ringkasan)) >= 20) AND (length(btrim(ringkasan)) <= 1200))),
    CONSTRAINT kabar_kegiatan_status_check CHECK ((status = ANY (ARRAY['diajukan'::text, 'terbit'::text, 'ditolak'::text]))),
    CONSTRAINT kabar_kegiatan_tautan_check CHECK (((tautan IS NULL) OR (tautan ~* '^https?://\S+$'::text))),
    CONSTRAINT kabar_kegiatan_tempat_check CHECK (((tempat IS NULL) OR (length(tempat) <= 200)))
);

ALTER TABLE public.kabar_kegiatan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.kabar_kegiatan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.kalender_akademik (
    id bigint NOT NULL,
    semester text NOT NULL,
    kegiatan text NOT NULL,
    kategori text DEFAULT 'lainnya'::text NOT NULL,
    mulai date NOT NULL,
    selesai date,
    catatan text,
    tampil boolean DEFAULT true NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kalender_akademik_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 300))),
    CONSTRAINT kalender_akademik_check CHECK (((selesai IS NULL) OR (selesai >= mulai))),
    CONSTRAINT kalender_akademik_kategori_check CHECK ((kategori = ANY (ARRAY['registrasi'::text, 'perkuliahan'::text, 'ujian'::text, 'tugas_akhir'::text, 'kerja_praktik'::text, 'yudisium'::text, 'libur'::text, 'lainnya'::text]))),
    CONSTRAINT kalender_akademik_kegiatan_check CHECK (((length(btrim(kegiatan)) >= 3) AND (length(btrim(kegiatan)) <= 160))),
    CONSTRAINT kalender_akademik_semester_check CHECK (((length(btrim(semester)) >= 3) AND (length(btrim(semester)) <= 40)))
);

ALTER TABLE public.kalender_akademik ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.kalender_akademik_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.karya (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    kategori text NOT NULL,
    judul text NOT NULL,
    tahun integer NOT NULL,
    jenis text,
    nama_terbitan text,
    kategori_pub_kode text,
    indeksasi text,
    doi text,
    url text,
    skema_kode text,
    nama_pemberi_dana text,
    besaran_dana numeric(14,0),
    mitra_institusi text,
    mitra_negara text,
    tingkat text,
    sumber_dana text,
    keterangan text,
    bukti_path text,
    status text DEFAULT 'diajukan'::text NOT NULL,
    catatan text,
    dilaporkan_oleh uuid NOT NULL,
    dibuat_pada timestamp with time zone DEFAULT now() NOT NULL,
    judul_norm text GENERATED ALWAYS AS (regexp_replace(lower(TRIM(BOTH FROM judul)), '[^a-z0-9]+'::text, ' '::text, 'g'::text)) STORED,
    mitra_tingkat text,
    sub_jenis text,
    mata_kuliah text,
    bukti_url text,
    bulan integer,
    relevan_visi boolean DEFAULT true NOT NULL,
    induk_id uuid,
    kerjasama_id bigint,
    tkt integer,
    nomor_tkt text,
    jumlah_sitasi integer,
    tema_id bigint,
    keterlibatan_mhs text,
    bukti_integrasi text,
    sesuai_rps boolean,
    manfaat_ks text,
    mulai_ks date,
    selesai_ks date,
    jenis_bukti_ks text,
    sumber_sitasi text,
    sitasi_diambil date,
    openalex_id text,
    sdgs smallint[],
    topik jsonb,
    volume text,
    nomor text,
    halaman text,
    CONSTRAINT karya_bukti_integrasi_check CHECK (((bukti_integrasi IS NULL) OR (bukti_integrasi = ANY (ARRAY['naskah_hibah'::text, 'laporan_akhir'::text, 'publikasi'::text, 'lainnya'::text])))),
    CONSTRAINT karya_bukti_url_check CHECK (((bukti_url IS NULL) OR (bukti_url ~* '^https://[^ ]+\.[^ ]+'::text))),
    CONSTRAINT karya_bulan_check CHECK (((bulan >= 1) AND (bulan <= 12))),
    CONSTRAINT karya_halaman_check CHECK (((halaman IS NULL) OR (char_length(halaman) <= 40))),
    CONSTRAINT karya_indeksasi_check CHECK ((indeksasi = ANY (ARRAY['scopus_q1'::text, 'scopus_q2'::text, 'scopus_q3'::text, 'scopus_q4'::text, 'scopus'::text, 'wos'::text, 'sinta_1_2'::text, 'sinta_3_4'::text, 'sinta_5_6'::text, 'tidak_terindeks'::text]))),
    CONSTRAINT karya_jenis_bukti_ks_check CHECK (((jenis_bukti_ks IS NULL) OR (jenis_bukti_ks = ANY (ARRAY['surat_penugasan'::text, 'spk'::text, 'bukti_pelaksanaan'::text, 'lainnya'::text])))),
    CONSTRAINT karya_jenis_check CHECK ((jenis = ANY (ARRAY['jurnal'::text, 'prosiding'::text, 'buku'::text, 'bab_buku'::text, 'haki_paten'::text, 'lainnya'::text]))),
    CONSTRAINT karya_jumlah_sitasi_check CHECK (((jumlah_sitasi IS NULL) OR (jumlah_sitasi >= 0))),
    CONSTRAINT karya_kategori_check CHECK ((kategori = ANY (ARRAY['publikasi'::text, 'penelitian'::text, 'pkm'::text, 'luaran'::text, 'rekognisi'::text, 'integrasi'::text]))),
    CONSTRAINT karya_keterlibatan_mhs_check CHECK (((keterlibatan_mhs IS NULL) OR (keterlibatan_mhs = ANY (ARRAY['tugas_akhir'::text, 'perancangan'::text, 'pengembangan_produk'::text, 'lainnya'::text])))),
    CONSTRAINT karya_mitra_tingkat_check CHECK ((mitra_tingkat = ANY (ARRAY['internasional'::text, 'nasional'::text, 'wilayah_lokal'::text]))),
    CONSTRAINT karya_nomor_check CHECK (((nomor IS NULL) OR (char_length(nomor) <= 40))),
    CONSTRAINT karya_openalex_id_check CHECK (((openalex_id IS NULL) OR (openalex_id ~ '^W[0-9]+$'::text))),
    CONSTRAINT karya_sdgs_check CHECK (((sdgs IS NULL) OR (sdgs <@ ARRAY[(1)::smallint, (2)::smallint, (3)::smallint, (4)::smallint, (5)::smallint, (6)::smallint, (7)::smallint, (8)::smallint, (9)::smallint, (10)::smallint, (11)::smallint, (12)::smallint, (13)::smallint, (14)::smallint, (15)::smallint, (16)::smallint, (17)::smallint]))),
    CONSTRAINT karya_skema_wajib CHECK (((kategori <> ALL (ARRAY['penelitian'::text, 'pkm'::text])) OR (skema_kode IS NOT NULL))),
    CONSTRAINT karya_status_check CHECK ((status = ANY (ARRAY['draf'::text, 'diajukan'::text, 'terverifikasi'::text, 'ditolak'::text]))),
    CONSTRAINT karya_sumber_dana_check CHECK ((sumber_dana = ANY (ARRAY['mandiri'::text, 'perguruan_tinggi'::text, 'dalam_negeri'::text, 'luar_negeri'::text]))),
    CONSTRAINT karya_sumber_sitasi_check CHECK (((sumber_sitasi IS NULL) OR (sumber_sitasi = ANY (ARRAY['openalex'::text, 'google_scholar'::text, 'scopus'::text, 'manual'::text])))),
    CONSTRAINT karya_tahun_check CHECK (((tahun >= 1980) AND (tahun <= 2100))),
    CONSTRAINT karya_tanggal_ks_check CHECK (((mulai_ks IS NULL) OR (selesai_ks IS NULL) OR (selesai_ks >= mulai_ks))),
    CONSTRAINT karya_tingkat_check CHECK ((tingkat = ANY (ARRAY['internasional'::text, 'nasional'::text, 'wilayah_lokal'::text]))),
    CONSTRAINT karya_tingkat_wajib CHECK (((status = 'draf'::text) OR (tingkat IS NOT NULL))),
    CONSTRAINT karya_tkt_check CHECK (((tkt IS NULL) OR ((tkt >= 1) AND (tkt <= 9)))),
    CONSTRAINT karya_topik_check CHECK (((topik IS NULL) OR (jsonb_typeof(topik) = 'array'::text))),
    CONSTRAINT karya_volume_check CHECK (((volume IS NULL) OR (char_length(volume) <= 40)))
);

COMMENT ON COLUMN public.karya.bulan IS 'Bulan terbit/pelaksanaan (1-12), opsional. Dipakai memetakan karya ke tahun akademik (TS): bulan >= 9 masuk TS tahun berikutnya.';

COMMENT ON COLUMN public.karya.relevan_visi IS 'Karya mendukung visi keilmuan prodi. Diputuskan admin saat verifikasi; false = tetap tampil di profil dosen, tetapi tidak ikut dihitung pada butir akreditasi tingkat prodi.';

CREATE TABLE public.karya_bukti (
    id bigint NOT NULL,
    karya_id uuid NOT NULL,
    jenis text NOT NULL,
    judul text DEFAULT ''::text NOT NULL,
    url text NOT NULL,
    oleh uuid DEFAULT public.me(),
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    sha256 text,
    CONSTRAINT karya_bukti_jenis_check CHECK ((jenis = ANY (ARRAY['naskah'::text, 'sk'::text, 'korespondensi'::text, 'laporan'::text, 'sertifikat'::text, 'foto'::text, 'daftar_hadir'::text, 'indeksasi'::text, 'loa'::text, 'pernyataan'::text, 'lainnya'::text]))),
    CONSTRAINT karya_bukti_sha256_check CHECK (((sha256 IS NULL) OR (sha256 ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT karya_bukti_url_check1 CHECK ((url ~* '^https?://[^ ]+$'::text))
);

ALTER TABLE public.karya_bukti ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.karya_bukti_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.karya_mahasiswa (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    karya_id uuid NOT NULL,
    nim text NOT NULL,
    nama text NOT NULL,
    peran text DEFAULT 'anggota'::text NOT NULL,
    korespondensi boolean DEFAULT false NOT NULL,
    ditambahkan_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT km_peran_check CHECK ((peran = ANY (ARRAY['penulis_pertama'::text, 'anggota'::text, 'ketua'::text])))
);

CREATE TABLE public.karya_mitra (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    karya_id uuid NOT NULL,
    institusi text NOT NULL,
    negara text,
    tingkat text,
    ditambahkan_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kmi_tingkat_check CHECK (((tingkat IS NULL) OR (tingkat = ANY (ARRAY['internasional'::text, 'nasional'::text, 'wilayah_lokal'::text]))))
);

CREATE TABLE public.karya_penulis (
    karya_id uuid NOT NULL,
    dosen_id uuid NOT NULL,
    peran text DEFAULT 'anggota'::text NOT NULL,
    ditambahkan_sendiri boolean DEFAULT false NOT NULL,
    ditambahkan_pada timestamp with time zone DEFAULT now() NOT NULL,
    korespondensi boolean DEFAULT false NOT NULL,
    CONSTRAINT karya_penulis_peran_check CHECK ((peran = ANY (ARRAY['penulis_pertama'::text, 'korespondensi'::text, 'anggota'::text, 'ketua'::text])))
);

CREATE TABLE public.karya_sitasi (
    karya_id uuid NOT NULL,
    tahun integer NOT NULL,
    jumlah integer NOT NULL,
    sumber text NOT NULL,
    diambil date DEFAULT CURRENT_DATE NOT NULL,
    CONSTRAINT karya_sitasi_jumlah_check CHECK ((jumlah >= 0)),
    CONSTRAINT karya_sitasi_sumber_check CHECK ((sumber = ANY (ARRAY['openalex'::text, 'google_scholar'::text, 'scopus'::text, 'manual'::text]))),
    CONSTRAINT karya_sitasi_tahun_check CHECK (((tahun >= 1950) AND (tahun <= 2100)))
);

CREATE TABLE public.kegiatan (
    id bigint NOT NULL,
    judul text NOT NULL,
    jenis text DEFAULT 'lain'::text NOT NULL,
    mulai date NOT NULL,
    selesai date,
    jam_mulai time without time zone,
    jam_selesai time without time zone,
    tempat text,
    keterangan text,
    tautan text,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kegiatan_check CHECK (((selesai IS NULL) OR (selesai >= mulai))),
    CONSTRAINT kegiatan_check1 CHECK (((jam_selesai IS NULL) OR (jam_mulai IS NOT NULL))),
    CONSTRAINT kegiatan_jenis_check CHECK ((jenis = ANY (ARRAY['ami'::text, 'akademik'::text, 'yudisium'::text, 'wisuda'::text, 'seminar'::text, 'rapat_luar'::text, 'mengawas'::text, 'sidang'::text, 'piket'::text, 'penugasan'::text, 'lain'::text]))),
    CONSTRAINT kegiatan_judul_check CHECK (((length(TRIM(BOTH FROM judul)) >= 2) AND (length(TRIM(BOTH FROM judul)) <= 300))),
    CONSTRAINT kegiatan_keterangan_check CHECK (((keterangan IS NULL) OR (length(keterangan) <= 2000))),
    CONSTRAINT kegiatan_tautan_check CHECK (((tautan IS NULL) OR (tautan ~* '^https?://\S+$'::text))),
    CONSTRAINT kegiatan_tempat_check CHECK (((tempat IS NULL) OR (length(tempat) <= 200)))
);

CREATE TABLE public.kegiatan_dosen (
    kegiatan_id bigint NOT NULL,
    dosen_id uuid NOT NULL
);

ALTER TABLE public.kegiatan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.kegiatan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.kelas_dosen (
    kelas_id bigint NOT NULL,
    dosen_id uuid NOT NULL,
    peran text DEFAULT 'anggota'::text NOT NULL,
    pertemuan integer,
    urutan integer DEFAULT 0 NOT NULL,
    CONSTRAINT kelas_dosen_peran_check CHECK ((peran = ANY (ARRAY['koordinator'::text, 'anggota'::text]))),
    CONSTRAINT kelas_dosen_pertemuan_check CHECK (((pertemuan IS NULL) OR ((pertemuan >= 1) AND (pertemuan <= 32))))
);

CREATE TABLE public.kelas_kuliah (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    kelas text NOT NULL,
    kapasitas integer,
    angkatan text,
    catatan text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kelas_kuliah_angkatan_check CHECK (((angkatan IS NULL) OR (length(angkatan) <= 40))),
    CONSTRAINT kelas_kuliah_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 500))),
    CONSTRAINT kelas_kuliah_kapasitas_check CHECK (((kapasitas IS NULL) OR ((kapasitas >= 1) AND (kapasitas <= 500)))),
    CONSTRAINT kelas_kuliah_kelas_check CHECK ((kelas ~ '^[A-Za-z0-9._ -]{1,10}$'::text)),
    CONSTRAINT kelas_kuliah_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT kelas_kuliah_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.kelas_kuliah ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.kelas_kuliah_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.koordinator (
    id bigint NOT NULL,
    dosen_id uuid NOT NULL,
    jabatan text NOT NULL,
    laboratorium_id bigint,
    mulai date NOT NULL,
    selesai date,
    nomor_sk text,
    dokumen_id bigint,
    catatan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    sebutan text,
    CONSTRAINT koordinator_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 1000))),
    CONSTRAINT koordinator_check CHECK (((selesai IS NULL) OR (selesai >= mulai))),
    CONSTRAINT koordinator_jabatan_check CHECK ((jabatan = ANY (ARRAY['pembina_kemahasiswaan'::text, 'kepala_lab'::text, 'koordinator_ta'::text, 'koordinator_kp'::text, 'gkm'::text, 'koordinator_capstone'::text, 'kaprodi'::text, 'dekan'::text]))),
    CONSTRAINT koordinator_nomor_sk_check CHECK (((nomor_sk IS NULL) OR (length(nomor_sk) <= 200))),
    CONSTRAINT koordinator_sebutan_check CHECK (((sebutan IS NULL) OR (length(sebutan) <= 200)))
);

ALTER TABLE public.koordinator ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.koordinator_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.kp_instansi_keputusan (
    kunci text NOT NULL,
    nama text NOT NULL,
    keputusan text NOT NULL,
    catatan text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kp_instansi_keputusan_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 500))),
    CONSTRAINT kp_instansi_keputusan_keputusan_check CHECK ((keputusan = ANY (ARRAY['usul'::text, 'tidak'::text]))),
    CONSTRAINT kp_instansi_keputusan_nama_check CHECK (((length(btrim(nama)) >= 2) AND (length(btrim(nama)) <= 300)))
);

CREATE TABLE public.kp_kuota (
    id bigint NOT NULL,
    ts integer NOT NULL,
    dosen_id uuid,
    kuota integer NOT NULL,
    diubah timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kp_kuota_kuota_check CHECK (((kuota >= 0) AND (kuota <= 100))),
    CONSTRAINT kp_kuota_ts_check CHECK (((ts >= 2000) AND (ts <= 2100)))
);

ALTER TABLE public.kp_kuota ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.kp_kuota_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.kp_tolak_instansi (
    id bigint NOT NULL,
    pengajuan_id bigint NOT NULL,
    instansi text NOT NULL,
    alasan text DEFAULT ''::text NOT NULL,
    dibuat timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.kp_tolak_instansi ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.kp_tolak_instansi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.kunjungan_publik (
    tanggal date NOT NULL,
    halaman text NOT NULL,
    rujukan text NOT NULL,
    peristiwa text NOT NULL,
    n integer DEFAULT 1 NOT NULL,
    CONSTRAINT kunjungan_publik_halaman_check CHECK ((halaman ~ '^[a-z0-9._/:-]{1,100}$'::text)),
    CONSTRAINT kunjungan_publik_peristiwa_check CHECK ((peristiwa = ANY (ARRAY['lihat'::text, 'kuis_selesai'::text, 'daftar_klik'::text]))),
    CONSTRAINT kunjungan_publik_rujukan_check CHECK ((rujukan = ANY (ARRAY['langsung'::text, 'internal'::text, 'google'::text, 'bing'::text, 'instagram'::text, 'facebook'::text, 'whatsapp'::text, 'linkedin'::text, 'youtube'::text, 'tiktok'::text, 'x'::text, 'kampus'::text, 'lainnya'::text])))
);

CREATE TABLE public.laboratorium (
    id bigint NOT NULL,
    nama text NOT NULL,
    ringkasan text NOT NULL,
    prasarana text,
    kepala_nidn text,
    mata_kuliah text[] DEFAULT '{}'::text[] NOT NULL,
    layanan text[] DEFAULT '{}'::text[] NOT NULL,
    kontak_layanan text,
    foto text[] DEFAULT '{}'::text[] NOT NULL,
    penelitian uuid[] DEFAULT '{}'::uuid[] NOT NULL,
    urutan integer DEFAULT 100 NOT NULL,
    tampil boolean DEFAULT true NOT NULL,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    bidang text[] DEFAULT '{}'::text[] NOT NULL,
    CONSTRAINT laboratorium_bidang_cek CHECK (((cardinality(bidang) <= 5) AND (array_to_string(bidang, ','::text) ~ '^([A-Z0-9]{2,12}(,|$))*$'::text))),
    CONSTRAINT laboratorium_foto_check CHECK ((cardinality(foto) <= 6)),
    CONSTRAINT laboratorium_kepala_nidn_check CHECK (((kepala_nidn IS NULL) OR (length(kepala_nidn) <= 20))),
    CONSTRAINT laboratorium_kontak_layanan_check CHECK (((kontak_layanan IS NULL) OR (length(kontak_layanan) <= 200))),
    CONSTRAINT laboratorium_layanan_check CHECK ((cardinality(layanan) <= 30)),
    CONSTRAINT laboratorium_mata_kuliah_check CHECK ((cardinality(mata_kuliah) <= 40)),
    CONSTRAINT laboratorium_nama_check CHECK (((length(btrim(nama)) >= 3) AND (length(btrim(nama)) <= 120))),
    CONSTRAINT laboratorium_penelitian_check CHECK ((cardinality(penelitian) <= 30)),
    CONSTRAINT laboratorium_prasarana_check CHECK (((prasarana IS NULL) OR (length(prasarana) <= 200))),
    CONSTRAINT laboratorium_ringkasan_check CHECK (((length(btrim(ringkasan)) >= 20) AND (length(btrim(ringkasan)) <= 1500)))
);

ALTER TABLE public.laboratorium ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.laboratorium_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.layanan_kunci (
    id integer DEFAULT 1 NOT NULL,
    kunci text DEFAULT encode(extensions.gen_random_bytes(24), 'hex'::text) NOT NULL,
    CONSTRAINT layanan_kunci_id_check CHECK ((id = 1))
);

CREATE TABLE public.led_narasi (
    kunci text NOT NULL,
    nilai text NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.led_penugasan (
    kelompok text NOT NULL,
    email text NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.led_tim (
    id bigint NOT NULL,
    urutan integer DEFAULT 0 NOT NULL,
    jenis text DEFAULT 'dosen'::text NOT NULL,
    dosen_id uuid,
    nama text,
    nomor text,
    jabatan text,
    deskripsi text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT led_tim_check CHECK (((dosen_id IS NOT NULL) OR (NULLIF(TRIM(BOTH FROM nama), ''::text) IS NOT NULL))),
    CONSTRAINT led_tim_jenis_check CHECK ((jenis = ANY (ARRAY['dosen'::text, 'nondosen'::text])))
);

ALTER TABLE public.led_tim ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.led_tim_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_bimbingan_utama (
    id bigint NOT NULL,
    nidn text NOT NULL,
    tahun_akademik text NOT NULL,
    jumlah_ps integer DEFAULT 0 NOT NULL,
    jumlah_ps_lain integer DEFAULT 0 NOT NULL,
    keterangan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_bimbingan_utama_jumlah_ps_check CHECK (((jumlah_ps >= 0) AND (jumlah_ps <= 999))),
    CONSTRAINT lkps_bimbingan_utama_jumlah_ps_lain_check CHECK (((jumlah_ps_lain >= 0) AND (jumlah_ps_lain <= 999))),
    CONSTRAINT lkps_bimbingan_utama_keterangan_check CHECK (((keterangan IS NULL) OR (length(keterangan) <= 500))),
    CONSTRAINT lkps_bimbingan_utama_nidn_check CHECK (((length(btrim(nidn)) >= 1) AND (length(btrim(nidn)) <= 30))),
    CONSTRAINT lkps_bimbingan_utama_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.lkps_bimbingan_utama ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_bimbingan_utama_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_bkd (
    id bigint NOT NULL,
    nidn text NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    status text,
    jabatan_akademik text,
    pendidikan_tertinggi text,
    sks_pendidikan numeric,
    sks_penelitian numeric,
    sks_pkm numeric,
    sks_penunjang numeric,
    bukti_url text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    sks_ps_lain_dalam numeric,
    sks_ps_lain_luar numeric,
    sks_lebih_pendidikan numeric,
    sks_lebih_penelitian numeric,
    sks_lebih_pkm numeric,
    sks_lebih_penunjang numeric,
    verifikasi text DEFAULT 'terverifikasi'::text NOT NULL,
    catatan text,
    dilaporkan_oleh uuid,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lkps_bkd_bukti_url_check CHECK ((bukti_url ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_bkd_jabatan_akademik_check CHECK ((jabatan_akademik = ANY (ARRAY['tenaga_pengajar'::text, 'asisten_ahli'::text, 'lektor'::text, 'lektor_kepala'::text, 'guru_besar'::text]))),
    CONSTRAINT lkps_bkd_pendidikan_tertinggi_check CHECK ((pendidikan_tertinggi = ANY (ARRAY['s2'::text, 's3'::text]))),
    CONSTRAINT lkps_bkd_semester_check CHECK ((semester = ANY (ARRAY['ganjil'::text, 'genap'::text]))),
    CONSTRAINT lkps_bkd_sks_lebih_pendidikan_check CHECK ((sks_lebih_pendidikan >= (0)::numeric)),
    CONSTRAINT lkps_bkd_sks_lebih_penelitian_check CHECK ((sks_lebih_penelitian >= (0)::numeric)),
    CONSTRAINT lkps_bkd_sks_lebih_penunjang_check CHECK ((sks_lebih_penunjang >= (0)::numeric)),
    CONSTRAINT lkps_bkd_sks_lebih_pkm_check CHECK ((sks_lebih_pkm >= (0)::numeric)),
    CONSTRAINT lkps_bkd_sks_pendidikan_check CHECK ((sks_pendidikan >= (0)::numeric)),
    CONSTRAINT lkps_bkd_sks_penelitian_check CHECK ((sks_penelitian >= (0)::numeric)),
    CONSTRAINT lkps_bkd_sks_penunjang_check CHECK ((sks_penunjang >= (0)::numeric)),
    CONSTRAINT lkps_bkd_sks_pkm_check CHECK ((sks_pkm >= (0)::numeric)),
    CONSTRAINT lkps_bkd_status_check CHECK ((status = ANY (ARRAY['dtps'::text, 'dosen_tetap'::text, 'dosen_tidak_tetap'::text]))),
    CONSTRAINT lkps_bkd_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text)),
    CONSTRAINT lkps_bkd_verifikasi_check CHECK ((verifikasi = ANY (ARRAY['diajukan'::text, 'terverifikasi'::text, 'ditolak'::text])))
);

ALTER TABLE public.lkps_bkd ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_bkd_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_bukti (
    id bigint NOT NULL,
    tabel text NOT NULL,
    baris_id bigint NOT NULL,
    judul text DEFAULT ''::text NOT NULL,
    url text,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    dokumen_id bigint,
    sha256 text,
    jenis text,
    unsur smallint,
    CONSTRAINT lkps_bukti_jenis_check CHECK (((jenis IS NULL) OR (jenis = ANY (ARRAY['sertifikat'::text, 'surat_tugas'::text, 'foto'::text, 'lainnya'::text])))),
    CONSTRAINT lkps_bukti_satu_sumber CHECK (((((url IS NOT NULL))::integer + ((dokumen_id IS NOT NULL))::integer) = 1)),
    CONSTRAINT lkps_bukti_sha256_check CHECK (((sha256 IS NULL) OR (sha256 ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT lkps_bukti_tabel_check CHECK ((tabel = ANY (ARRAY['lkps_mahasiswa_ta'::text, 'lkps_kohort_lulusan'::text, 'lkps_tracer_lulusan'::text, 'lkps_kerjasama'::text, 'lkps_bkd'::text, 'lkps_prestasi_mahasiswa'::text, 'lkps_publikasi_mahasiswa'::text, 'lkps_luaran_mahasiswa'::text, 'lkps_kepuasan_pengguna'::text, 'ref_mata_kuliah'::text, 'ref_tema_peta_jalan'::text, 'lkps_vmts'::text, 'lkps_prodi_upps'::text, 'lkps_penggunaan_dana'::text, 'lkps_tendik'::text, 'lkps_prasarana'::text, 'lkps_dokumen_k3l'::text, 'lkps_fasilitas_k3l'::text, 'lkps_spmi_ppepp'::text, 'lkps_target_kinerja'::text, 'lkps_peta_jalan'::text, 'ami_temuan'::text, 'spmi_standar'::text, 'spmi_standar_revisi'::text, 'jadwal_ta'::text, 'lkps_sarana_standar'::text, 'lkps_bimbingan_utama'::text, 'lkps_keuangan'::text, 'lkps_mahasiswa_angkatan'::text]))),
    CONSTRAINT lkps_bukti_unsur_check CHECK (((unsur IS NULL) OR ((unsur >= 1) AND (unsur <= 4)))),
    CONSTRAINT lkps_bukti_url_check CHECK ((url ~* '^https?://\S+$'::text))
);

ALTER TABLE public.lkps_bukti ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_bukti_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_dokumen_k3l (
    id bigint NOT NULL,
    jenis_dokumen text NOT NULL,
    jumlah integer,
    riwayat_pengesahan text,
    urutan integer DEFAULT 100 NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_dokumen_k3l_jumlah_check CHECK (((jumlah IS NULL) OR (jumlah >= 0)))
);

ALTER TABLE public.lkps_dokumen_k3l ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_dokumen_k3l_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_fasilitas_k3l (
    id bigint NOT NULL,
    nama_sarana text NOT NULL,
    fungsi text,
    jumlah_unit integer,
    kondisi text,
    urutan integer DEFAULT 100 NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_fasilitas_k3l_jumlah_unit_check CHECK (((jumlah_unit IS NULL) OR (jumlah_unit >= 0))),
    CONSTRAINT lkps_fasilitas_k3l_kondisi_check CHECK (((kondisi IS NULL) OR (kondisi = ANY (ARRAY['terawat'::text, 'tidak_terawat'::text]))))
);

ALTER TABLE public.lkps_fasilitas_k3l ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_fasilitas_k3l_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_kepuasan_pengguna (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    aspek text NOT NULL,
    sangat_baik numeric NOT NULL,
    baik numeric NOT NULL,
    cukup numeric NOT NULL,
    kurang numeric NOT NULL,
    rencana_tindak_lanjut text,
    bukti_url text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_kepuasan_pengguna_aspek_check CHECK ((aspek = ANY (ARRAY['etika'::text, 'keahlian_bidang_ilmu'::text, 'bahasa_asing'::text, 'teknologi_informasi'::text, 'komunikasi'::text, 'kerja_sama_tim'::text, 'pengembangan_diri'::text]))),
    CONSTRAINT lkps_kepuasan_pengguna_baik_check CHECK (((baik >= (0)::numeric) AND (baik <= (100)::numeric))),
    CONSTRAINT lkps_kepuasan_pengguna_bukti_url_check CHECK ((bukti_url ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_kepuasan_pengguna_cukup_check CHECK (((cukup >= (0)::numeric) AND (cukup <= (100)::numeric))),
    CONSTRAINT lkps_kepuasan_pengguna_jumlah_check CHECK ((abs(((((sangat_baik + baik) + cukup) + kurang) - (100)::numeric)) <= (1)::numeric)),
    CONSTRAINT lkps_kepuasan_pengguna_kurang_check CHECK (((kurang >= (0)::numeric) AND (kurang <= (100)::numeric))),
    CONSTRAINT lkps_kepuasan_pengguna_sangat_baik_check CHECK (((sangat_baik >= (0)::numeric) AND (sangat_baik <= (100)::numeric))),
    CONSTRAINT lkps_kepuasan_pengguna_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.lkps_kepuasan_pengguna ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_kepuasan_pengguna_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_kerjasama (
    id bigint NOT NULL,
    mitra text NOT NULL,
    jenis text NOT NULL,
    tingkat text NOT NULL,
    kegiatan text,
    tahun_mulai integer NOT NULL,
    tahun_selesai integer,
    tautan_bukti text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    manfaat text,
    tanggal_mulai date,
    tanggal_selesai date,
    jenis_bukti text,
    sembunyikan_publik boolean DEFAULT false NOT NULL,
    CONSTRAINT lkps_kerjasama_jenis_bukti_check CHECK (((jenis_bukti IS NULL) OR (jenis_bukti = ANY (ARRAY['surat_penugasan'::text, 'spk'::text, 'bukti_pelaksanaan'::text, 'lainnya'::text])))),
    CONSTRAINT lkps_kerjasama_jenis_check CHECK ((jenis = ANY (ARRAY['pendidikan'::text, 'penelitian'::text, 'pkm'::text]))),
    CONSTRAINT lkps_kerjasama_tahun_mulai_check CHECK (((tahun_mulai >= 1990) AND (tahun_mulai <= 2100))),
    CONSTRAINT lkps_kerjasama_tahun_selesai_check CHECK (((tahun_selesai >= 1990) AND (tahun_selesai <= 2100))),
    CONSTRAINT lkps_kerjasama_tanggal_check CHECK (((tanggal_selesai IS NULL) OR (tanggal_mulai IS NULL) OR (tanggal_selesai >= tanggal_mulai))),
    CONSTRAINT lkps_kerjasama_tautan_bukti_check CHECK ((tautan_bukti ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_kerjasama_tingkat_check CHECK ((tingkat = ANY (ARRAY['internasional'::text, 'nasional'::text, 'wilayah'::text])))
);

ALTER TABLE public.lkps_kerjasama ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_kerjasama_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_keuangan (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    pos text NOT NULL,
    dana_upps numeric,
    dana_ps numeric,
    keterangan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_keuangan_dana_ps_check CHECK (((dana_ps IS NULL) OR (dana_ps >= (0)::numeric))),
    CONSTRAINT lkps_keuangan_dana_upps_check CHECK (((dana_upps IS NULL) OR (dana_upps >= (0)::numeric))),
    CONSTRAINT lkps_keuangan_keterangan_check CHECK (((keterangan IS NULL) OR (length(keterangan) <= 500))),
    CONSTRAINT lkps_keuangan_pos_check CHECK ((pos ~ '^[a-z0-9_]{2,60}$'::text)),
    CONSTRAINT lkps_keuangan_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.lkps_keuangan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_keuangan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_kohort_lulusan (
    id bigint NOT NULL,
    tahun_masuk integer NOT NULL,
    jumlah_masuk integer,
    lulus_3_5_sd_4_5 integer,
    lulus_4_5_sd_5_5 integer,
    lulus_5_5_sd_6_5 integer,
    lulus_6_5_sd_8 integer,
    bukti_url text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_kohort_lulusan_bukti_url_check CHECK ((bukti_url ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_kohort_lulusan_jumlah_masuk_check CHECK ((jumlah_masuk >= 0)),
    CONSTRAINT lkps_kohort_lulusan_lulus_3_5_sd_4_5_check CHECK ((lulus_3_5_sd_4_5 >= 0)),
    CONSTRAINT lkps_kohort_lulusan_lulus_4_5_sd_5_5_check CHECK ((lulus_4_5_sd_5_5 >= 0)),
    CONSTRAINT lkps_kohort_lulusan_lulus_5_5_sd_6_5_check CHECK ((lulus_5_5_sd_6_5 >= 0)),
    CONSTRAINT lkps_kohort_lulusan_lulus_6_5_sd_8_check CHECK ((lulus_6_5_sd_8 >= 0)),
    CONSTRAINT lkps_kohort_lulusan_tahun_masuk_check CHECK (((tahun_masuk >= 1990) AND (tahun_masuk <= 2100)))
);

ALTER TABLE public.lkps_kohort_lulusan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_kohort_lulusan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_luaran_mahasiswa (
    id bigint NOT NULL,
    tahun integer NOT NULL,
    bulan smallint,
    jenis text NOT NULL,
    judul text NOT NULL,
    nama_mahasiswa text,
    nim text,
    bukti_url text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    status_hki text,
    nomor text,
    tkt integer,
    CONSTRAINT lkps_luaran_mahasiswa_bukti_url_check CHECK ((bukti_url ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_luaran_mahasiswa_bulan_check CHECK (((bulan >= 1) AND (bulan <= 12))),
    CONSTRAINT lkps_luaran_mahasiswa_jenis_check CHECK ((jenis = ANY (ARRAY['paten'::text, 'paten_sederhana'::text, 'hak_cipta'::text, 'desain_industri'::text, 'merek'::text, 'ttg'::text, 'produk'::text, 'buku_isbn'::text, 'book_chapter'::text]))),
    CONSTRAINT lkps_luaran_mahasiswa_lkps26_check CHECK ((((status_hki IS NULL) OR (status_hki = ANY (ARRAY['registered'::text, 'granted'::text, 'komersial'::text]))) AND ((tkt IS NULL) OR ((tkt >= 1) AND (tkt <= 9))))),
    CONSTRAINT lkps_luaran_mahasiswa_tahun_check CHECK (((tahun >= 1990) AND (tahun <= 2100)))
);

ALTER TABLE public.lkps_luaran_mahasiswa ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_luaran_mahasiswa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_mahasiswa_angkatan (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    daya_tampung integer,
    pendaftar integer,
    lulus_seleksi integer,
    afirmasi integer,
    transfer integer,
    asing integer,
    aktif integer,
    tidak_aktif integer,
    lulus integer,
    gagal integer,
    asing_penuh_waktu integer,
    asing_satu_semester integer,
    asing_pendek_kredit integer,
    asing_tanpa_kredit integer,
    keterangan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_mahasiswa_angkatan_afirmasi_check CHECK ((afirmasi >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_aktif_check CHECK ((aktif >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_asing_check CHECK ((asing >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_asing_pendek_kredit_check CHECK ((asing_pendek_kredit >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_asing_penuh_waktu_check CHECK ((asing_penuh_waktu >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_asing_satu_semester_check CHECK ((asing_satu_semester >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_asing_tanpa_kredit_check CHECK ((asing_tanpa_kredit >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_daya_tampung_check CHECK ((daya_tampung >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_gagal_check CHECK ((gagal >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_keterangan_check CHECK (((keterangan IS NULL) OR (length(keterangan) <= 500))),
    CONSTRAINT lkps_mahasiswa_angkatan_lulus_check CHECK ((lulus >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_lulus_seleksi_check CHECK ((lulus_seleksi >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_pendaftar_check CHECK ((pendaftar >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text)),
    CONSTRAINT lkps_mahasiswa_angkatan_tidak_aktif_check CHECK ((tidak_aktif >= 0)),
    CONSTRAINT lkps_mahasiswa_angkatan_transfer_check CHECK ((transfer >= 0))
);

ALTER TABLE public.lkps_mahasiswa_angkatan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_mahasiswa_angkatan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_mahasiswa_ta (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    jumlah_mahasiswa_aktif integer,
    jumlah_lulusan integer,
    rerata_ipk_lulusan numeric,
    jumlah_mahasiswa_asing integer,
    rerata_masa_studi_tahun numeric,
    persen_lulus_tepat_waktu numeric,
    bukti_url text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    jumlah_mahasiswa_asing_penuh integer,
    jumlah_mahasiswa_asing_paruh integer,
    ipk_min numeric,
    ipk_maks numeric,
    CONSTRAINT lkps_mahasiswa_ta_bukti_url_check CHECK ((bukti_url ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_mahasiswa_ta_jumlah_lulusan_check CHECK ((jumlah_lulusan >= 0)),
    CONSTRAINT lkps_mahasiswa_ta_jumlah_mahasiswa_aktif_check CHECK ((jumlah_mahasiswa_aktif >= 0)),
    CONSTRAINT lkps_mahasiswa_ta_jumlah_mahasiswa_asing_check CHECK ((jumlah_mahasiswa_asing >= 0)),
    CONSTRAINT lkps_mahasiswa_ta_lkps26_check CHECK (((COALESCE(jumlah_mahasiswa_asing_penuh, 0) >= 0) AND (COALESCE(jumlah_mahasiswa_asing_paruh, 0) >= 0) AND ((ipk_min IS NULL) OR ((ipk_min >= (0)::numeric) AND (ipk_min <= (4)::numeric))) AND ((ipk_maks IS NULL) OR ((ipk_maks >= (0)::numeric) AND (ipk_maks <= (4)::numeric))) AND ((ipk_min IS NULL) OR (ipk_maks IS NULL) OR (ipk_min <= ipk_maks)))),
    CONSTRAINT lkps_mahasiswa_ta_persen_lulus_tepat_waktu_check CHECK (((persen_lulus_tepat_waktu >= (0)::numeric) AND (persen_lulus_tepat_waktu <= (100)::numeric))),
    CONSTRAINT lkps_mahasiswa_ta_rerata_ipk_lulusan_check CHECK (((rerata_ipk_lulusan >= (0)::numeric) AND (rerata_ipk_lulusan <= (4)::numeric))),
    CONSTRAINT lkps_mahasiswa_ta_rerata_masa_studi_tahun_check CHECK (((rerata_masa_studi_tahun >= (0)::numeric) AND (rerata_masa_studi_tahun <= (15)::numeric))),
    CONSTRAINT lkps_mahasiswa_ta_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.lkps_mahasiswa_ta ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_mahasiswa_ta_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_penggunaan_dana (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    jenis text NOT NULL,
    dana_upps numeric,
    dana_ps numeric,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_penggunaan_dana_dana_ps_check CHECK (((dana_ps IS NULL) OR (dana_ps >= (0)::numeric))),
    CONSTRAINT lkps_penggunaan_dana_dana_upps_check CHECK (((dana_upps IS NULL) OR (dana_upps >= (0)::numeric))),
    CONSTRAINT lkps_penggunaan_dana_jenis_check CHECK ((jenis = ANY (ARRAY['biaya_dosen'::text, 'biaya_tendik'::text, 'operasional_pembelajaran'::text, 'operasional_tidak_langsung'::text, 'operasional_luar_pt'::text, 'investasi'::text, 'kemahasiswaan'::text, 'penelitian'::text, 'pkm'::text]))),
    CONSTRAINT lkps_penggunaan_dana_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.lkps_penggunaan_dana ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_penggunaan_dana_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_peta_jalan (
    id bigint NOT NULL,
    jenis text NOT NULL,
    judul text NOT NULL,
    tahun_mulai integer,
    tahun_selesai integer,
    keterangan text,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lkps_peta_jalan_jenis_check CHECK ((jenis = ANY (ARRAY['penelitian'::text, 'pkm'::text]))),
    CONSTRAINT lkps_peta_jalan_tahun_check CHECK (((tahun_mulai IS NULL) OR (tahun_selesai IS NULL) OR (tahun_selesai >= tahun_mulai))),
    CONSTRAINT lkps_peta_jalan_tahun_mulai_check CHECK (((tahun_mulai >= 2000) AND (tahun_mulai <= 2100))),
    CONSTRAINT lkps_peta_jalan_tahun_selesai_check CHECK (((tahun_selesai >= 2000) AND (tahun_selesai <= 2100)))
);

ALTER TABLE public.lkps_peta_jalan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_peta_jalan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_prasarana (
    id bigint NOT NULL,
    prasarana text NOT NULL,
    jumlah_prasarana integer,
    alat text,
    jumlah_standar integer,
    jumlah_dimiliki integer,
    kepemilikan text,
    kondisi text,
    urutan integer DEFAULT 100 NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_prasarana_jumlah_dimiliki_check CHECK (((jumlah_dimiliki IS NULL) OR (jumlah_dimiliki >= 0))),
    CONSTRAINT lkps_prasarana_jumlah_prasarana_check CHECK (((jumlah_prasarana IS NULL) OR (jumlah_prasarana >= 0))),
    CONSTRAINT lkps_prasarana_jumlah_standar_check CHECK (((jumlah_standar IS NULL) OR (jumlah_standar >= 0))),
    CONSTRAINT lkps_prasarana_kepemilikan_check CHECK (((kepemilikan IS NULL) OR (kepemilikan = ANY (ARRAY['sendiri'::text, 'sewa'::text])))),
    CONSTRAINT lkps_prasarana_kondisi_check CHECK (((kondisi IS NULL) OR (kondisi = ANY (ARRAY['terawat'::text, 'tidak_terawat'::text]))))
);

ALTER TABLE public.lkps_prasarana ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_prasarana_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_prestasi_mahasiswa (
    id bigint NOT NULL,
    nama_mahasiswa text,
    nim text,
    nama_kegiatan text NOT NULL,
    penyelenggara text,
    bidang text NOT NULL,
    bulan smallint,
    tingkat text NOT NULL,
    capaian text,
    tahun integer NOT NULL,
    nidn_pembimbing text,
    tautan_bukti text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    pembimbing text[] DEFAULT '{}'::text[] NOT NULL,
    status text DEFAULT 'terverifikasi'::text NOT NULL,
    catatan text,
    dilaporkan_oleh uuid,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    tampil_nama boolean DEFAULT false NOT NULL,
    cerita text,
    sembunyikan_publik boolean DEFAULT false NOT NULL,
    CONSTRAINT lkps_prestasi_mahasiswa_bidang_check CHECK ((bidang = ANY (ARRAY['akademik'::text, 'non_akademik'::text]))),
    CONSTRAINT lkps_prestasi_mahasiswa_bulan_check CHECK (((bulan >= 1) AND (bulan <= 12))),
    CONSTRAINT lkps_prestasi_mahasiswa_cerita_check CHECK (((cerita IS NULL) OR (length(cerita) <= 600))),
    CONSTRAINT lkps_prestasi_mahasiswa_tahun_check CHECK (((tahun >= 1990) AND (tahun <= 2100))),
    CONSTRAINT lkps_prestasi_mahasiswa_tautan_bukti_check CHECK ((tautan_bukti ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_prestasi_mahasiswa_tingkat_check CHECK ((tingkat = ANY (ARRAY['internasional'::text, 'nasional'::text, 'wilayah_lokal'::text]))),
    CONSTRAINT lkps_prestasi_status_check CHECK ((status = ANY (ARRAY['diajukan'::text, 'terverifikasi'::text, 'ditolak'::text])))
);

ALTER TABLE public.lkps_prestasi_mahasiswa ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_prestasi_mahasiswa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_prodi_upps (
    id bigint NOT NULL,
    jenis_program text NOT NULL,
    nama_prodi text NOT NULL,
    diakreditasi boolean DEFAULT false NOT NULL,
    status_akreditasi text,
    nomor_sk text,
    tanggal_sk date,
    tanggal_kedaluwarsa date,
    mahasiswa_ts2 integer,
    mahasiswa_ts1 integer,
    mahasiswa_ts integer,
    urutan integer DEFAULT 100 NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_prodi_upps_mahasiswa_ts1_check CHECK (((mahasiswa_ts1 IS NULL) OR (mahasiswa_ts1 >= 0))),
    CONSTRAINT lkps_prodi_upps_mahasiswa_ts2_check CHECK (((mahasiswa_ts2 IS NULL) OR (mahasiswa_ts2 >= 0))),
    CONSTRAINT lkps_prodi_upps_mahasiswa_ts_check CHECK (((mahasiswa_ts IS NULL) OR (mahasiswa_ts >= 0))),
    CONSTRAINT lkps_prodi_upps_status_akreditasi_check CHECK (((status_akreditasi IS NULL) OR (status_akreditasi = ANY (ARRAY['unggul'::text, 'a'::text, 'baik_sekali'::text, 'b'::text, 'baik'::text, 'c'::text, 'minimum'::text, 'tidak_terakreditasi'::text]))))
);

ALTER TABLE public.lkps_prodi_upps ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_prodi_upps_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_publikasi_mahasiswa (
    id bigint NOT NULL,
    tahun integer NOT NULL,
    judul text NOT NULL,
    nama_mahasiswa text,
    nim text,
    jenis text,
    tingkat text,
    indeksasi text,
    bulan smallint,
    bukti_url text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_publikasi_mahasiswa_bukti_url_check CHECK ((bukti_url ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_publikasi_mahasiswa_bulan_check CHECK (((bulan >= 1) AND (bulan <= 12))),
    CONSTRAINT lkps_publikasi_mahasiswa_indeksasi_check CHECK ((indeksasi = ANY (ARRAY['scopus'::text, 'wos'::text, 'bereputasi'::text, 'sinta'::text, 'tidak_terindeks'::text]))),
    CONSTRAINT lkps_publikasi_mahasiswa_jenis_check CHECK ((jenis = ANY (ARRAY['jurnal'::text, 'prosiding'::text, 'buku'::text, 'lainnya'::text]))),
    CONSTRAINT lkps_publikasi_mahasiswa_tahun_check CHECK (((tahun >= 1990) AND (tahun <= 2100)))
);

ALTER TABLE public.lkps_publikasi_mahasiswa ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_publikasi_mahasiswa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_sarana_standar (
    id bigint NOT NULL,
    jenis text NOT NULL,
    kategori text,
    nama text NOT NULL,
    lokasi text,
    ukuran text,
    nama_standar text,
    occupancy text,
    standar_ditetapkan text,
    ukuran_eksisting text,
    urutan integer DEFAULT 100 NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_sarana_standar_jenis_check CHECK ((jenis = ANY (ARRAY['belajar'::text, 'kerja'::text, 'diseminasi'::text, 'kesejahteraan'::text]))),
    CONSTRAINT lkps_sarana_standar_kategori_belajar CHECK (((jenis <> 'belajar'::text) OR (kategori IS NOT NULL))),
    CONSTRAINT lkps_sarana_standar_kategori_check CHECK (((kategori IS NULL) OR (kategori = ANY (ARRAY['perabot'::text, 'media'::text, 'kenyamanan'::text, 'administrasi'::text, 'k3'::text])))),
    CONSTRAINT lkps_sarana_standar_lokasi_check CHECK (((lokasi IS NULL) OR (length(lokasi) <= 200))),
    CONSTRAINT lkps_sarana_standar_nama_check CHECK (((length(btrim(nama)) >= 1) AND (length(btrim(nama)) <= 300))),
    CONSTRAINT lkps_sarana_standar_nama_standar_check CHECK (((nama_standar IS NULL) OR (length(nama_standar) <= 500))),
    CONSTRAINT lkps_sarana_standar_occupancy_check CHECK (((occupancy IS NULL) OR (length(occupancy) <= 300))),
    CONSTRAINT lkps_sarana_standar_standar_ditetapkan_check CHECK (((standar_ditetapkan IS NULL) OR (length(standar_ditetapkan) <= 300))),
    CONSTRAINT lkps_sarana_standar_ukuran_check CHECK (((ukuran IS NULL) OR (length(ukuran) <= 300))),
    CONSTRAINT lkps_sarana_standar_ukuran_eksisting_check CHECK (((ukuran_eksisting IS NULL) OR (length(ukuran_eksisting) <= 300)))
);

ALTER TABLE public.lkps_sarana_standar ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_sarana_standar_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_spmi_ppepp (
    id bigint NOT NULL,
    tahap text NOT NULL,
    dokumen_id bigint,
    audit_dokumen_id bigint,
    rtm_dokumen_id bigint,
    peningkatan_dokumen_id bigint,
    keterangan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_spmi_ppepp_tahap_check CHECK ((tahap = ANY (ARRAY['penetapan'::text, 'pelaksanaan'::text, 'evaluasi'::text, 'pengendalian'::text, 'peningkatan'::text])))
);

ALTER TABLE public.lkps_spmi_ppepp ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_spmi_ppepp_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_target_kinerja (
    id bigint NOT NULL,
    jenis text NOT NULL,
    bidang text,
    nama text NOT NULL,
    butir smallint,
    satuan text,
    arah text DEFAULT 'minimal'::text NOT NULL,
    target numeric,
    capaian numeric,
    tahun_ts integer NOT NULL,
    tujuan_strategis text,
    dampak text,
    daya_saing text,
    analisis text,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    sumber text,
    rencana_perbaikan text,
    standar_id bigint,
    CONSTRAINT lkps_target_kinerja_arah_check CHECK ((arah = ANY (ARRAY['minimal'::text, 'maksimal'::text]))),
    CONSTRAINT lkps_target_kinerja_bidang_check CHECK ((bidang = ANY (ARRAY['pendidikan'::text, 'penelitian'::text, 'pkm'::text, 'tata_kelola'::text, 'lainnya'::text]))),
    CONSTRAINT lkps_target_kinerja_butir_rentang CHECK (((butir IS NULL) OR ((butir >= 1) AND (butir <= 999)))),
    CONSTRAINT lkps_target_kinerja_jenis_check CHECK ((jenis = ANY (ARRAY['iku'::text, 'ikt'::text]))),
    CONSTRAINT lkps_target_kinerja_sumber_check CHECK (((sumber IS NULL) OR (sumber ~ '^[a-z0-9_]{2,40}$'::text))),
    CONSTRAINT lkps_target_kinerja_tahun_ts_check CHECK (((tahun_ts >= 2000) AND (tahun_ts <= 2100)))
);

ALTER TABLE public.lkps_target_kinerja ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_target_kinerja_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_tendik (
    id bigint NOT NULL,
    nama text NOT NULL,
    jabatan text,
    pendidikan text,
    sertifikat text,
    unit_kerja text,
    aktif boolean DEFAULT true NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    status_kerja text DEFAULT 'tetap'::text NOT NULL,
    laboratorium_id bigint,
    boleh_tampil boolean DEFAULT false NOT NULL,
    CONSTRAINT lkps_tendik_jabatan_check CHECK (((jabatan IS NULL) OR (jabatan = ANY (ARRAY['admin_prodi'::text, 'laboran'::text, 'asisten_lab'::text, 'teknisi'::text, 'administrator_sistem'::text, 'lainnya'::text])))),
    CONSTRAINT lkps_tendik_pendidikan_check CHECK (((pendidikan IS NULL) OR (pendidikan = ANY (ARRAY['s3'::text, 's2'::text, 's1'::text, 'd4'::text, 'd3'::text, 'd2'::text, 'd1'::text, 'sma_smk'::text])))),
    CONSTRAINT lkps_tendik_status_kerja_check CHECK ((status_kerja = ANY (ARRAY['tetap'::text, 'kontrak'::text, 'magang'::text]))),
    CONSTRAINT lkps_tendik_unit_kerja_check CHECK (((unit_kerja IS NULL) OR (unit_kerja = ANY (ARRAY['upps'::text, 'prodi'::text, 'institusi'::text]))))
);

ALTER TABLE public.lkps_tendik ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_tendik_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_tracer_lulusan (
    id bigint NOT NULL,
    tahun_lulus integer NOT NULL,
    jumlah_lulusan integer,
    jumlah_terlacak integer,
    rata_rata_waktu_tunggu_bulan numeric,
    bekerja_sesuai_bidang integer,
    kerja_internasional integer,
    kerja_nasional integer,
    kerja_wilayah integer,
    bukti_url text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    wt_kurang_3 integer,
    wt_3_18 integer,
    wt_lebih_18 integer,
    kesesuaian_rendah integer,
    kesesuaian_sedang integer,
    kesesuaian_tinggi integer,
    pengguna_tanggapan integer,
    CONSTRAINT lkps_tracer_lulusan_bekerja_sesuai_bidang_check CHECK ((bekerja_sesuai_bidang >= 0)),
    CONSTRAINT lkps_tracer_lulusan_bukti_url_check CHECK ((bukti_url ~* '^https?://\S+$'::text)),
    CONSTRAINT lkps_tracer_lulusan_jumlah_lulusan_check CHECK ((jumlah_lulusan >= 0)),
    CONSTRAINT lkps_tracer_lulusan_jumlah_terlacak_check CHECK ((jumlah_terlacak >= 0)),
    CONSTRAINT lkps_tracer_lulusan_kerja_internasional_check CHECK ((kerja_internasional >= 0)),
    CONSTRAINT lkps_tracer_lulusan_kerja_nasional_check CHECK ((kerja_nasional >= 0)),
    CONSTRAINT lkps_tracer_lulusan_kerja_wilayah_check CHECK ((kerja_wilayah >= 0)),
    CONSTRAINT lkps_tracer_lulusan_lkps26_check CHECK (((COALESCE(wt_kurang_3, 0) >= 0) AND (COALESCE(wt_3_18, 0) >= 0) AND (COALESCE(wt_lebih_18, 0) >= 0) AND (COALESCE(kesesuaian_rendah, 0) >= 0) AND (COALESCE(kesesuaian_sedang, 0) >= 0) AND (COALESCE(kesesuaian_tinggi, 0) >= 0))),
    CONSTRAINT lkps_tracer_lulusan_rata_rata_waktu_tunggu_bulan_check CHECK ((rata_rata_waktu_tunggu_bulan >= (0)::numeric)),
    CONSTRAINT lkps_tracer_lulusan_tahun_lulus_check CHECK (((tahun_lulus >= 1990) AND (tahun_lulus <= 2100))),
    CONSTRAINT lkps_tracer_pengguna_check CHECK (((pengguna_tanggapan IS NULL) OR (pengguna_tanggapan >= 0)))
);

ALTER TABLE public.lkps_tracer_lulusan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_tracer_lulusan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.lkps_vmts (
    id bigint NOT NULL,
    jenis text NOT NULL,
    visi text,
    misi text,
    tujuan text,
    strategi text,
    nomor_sk text,
    tautan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    oleh text,
    CONSTRAINT lkps_vmts_jenis_check CHECK ((jenis = ANY (ARRAY['pt'::text, 'upps'::text, 'ps'::text]))),
    CONSTRAINT lkps_vmts_tautan_check CHECK (((tautan IS NULL) OR (tautan ~* '^https?://\S+$'::text)))
);

ALTER TABLE public.lkps_vmts ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lkps_vmts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.masukan_mahasiswa (
    id bigint NOT NULL,
    jenis text NOT NULL,
    isi text NOT NULL,
    nama text,
    email text,
    status text DEFAULT 'baru'::text NOT NULL,
    catatan text,
    dikirim timestamp with time zone DEFAULT now() NOT NULL,
    diubah timestamp with time zone,
    diubah_oleh text,
    CONSTRAINT masukan_mahasiswa_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 4000))),
    CONSTRAINT masukan_mahasiswa_email_check CHECK (((email IS NULL) OR (length(email) <= 200))),
    CONSTRAINT masukan_mahasiswa_isi_check CHECK (((length(btrim(isi)) >= 10) AND (length(btrim(isi)) <= 3000))),
    CONSTRAINT masukan_mahasiswa_jenis_check CHECK ((jenis = ANY (ARRAY['tanya'::text, 'masukan'::text]))),
    CONSTRAINT masukan_mahasiswa_nama_check CHECK (((nama IS NULL) OR (length(nama) <= 120))),
    CONSTRAINT masukan_mahasiswa_status_check CHECK ((status = ANY (ARRAY['baru'::text, 'ditindaklanjuti'::text, 'selesai'::text])))
);

CREATE SEQUENCE public.masukan_mahasiswa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.masukan_mahasiswa_id_seq OWNED BY public.masukan_mahasiswa.id;

CREATE TABLE public.mhs_email_alt (
    nim text NOT NULL,
    email text,
    calon text,
    calon_hash text,
    calon_dikirim timestamp with time zone,
    oleh text DEFAULT 'mahasiswa'::text NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mhs_email_alt_calon_check CHECK (((calon IS NULL) OR ((calon = lower(calon)) AND (calon ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text)))),
    CONSTRAINT mhs_email_alt_email_check CHECK (((email IS NULL) OR ((email = lower(email)) AND (email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text)))),
    CONSTRAINT mhs_email_alt_nim_check CHECK ((nim ~ '^[0-9]{6,15}$'::text))
);

CREATE TABLE public.mhs_email_alt_riwayat (
    id bigint NOT NULL,
    nim text NOT NULL,
    email text,
    aksi text NOT NULL,
    oleh text NOT NULL,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mhs_email_alt_riwayat_aksi_check CHECK ((aksi = ANY (ARRAY['diminta'::text, 'aktif'::text, 'dicabut'::text])))
);

ALTER TABLE public.mhs_email_alt_riwayat ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mhs_email_alt_riwayat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_padanan_sah (
    kurikulum_lama text NOT NULL,
    kurikulum_baru text NOT NULL,
    status text DEFAULT 'draf'::text NOT NULL,
    usulan jsonb,
    sah_pada timestamp with time zone,
    sah_oleh uuid,
    sah_nama text,
    tetap_pada timestamp with time zone,
    tetap_oleh uuid,
    tetap_nama text,
    terbit jsonb,
    terbit_pada timestamp with time zone,
    revisi integer DEFAULT 0 NOT NULL,
    catatan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_padanan_sah_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000))),
    CONSTRAINT mk_padanan_sah_check CHECK ((kurikulum_lama <> kurikulum_baru)),
    CONSTRAINT mk_padanan_sah_kurikulum_baru_check CHECK ((kurikulum_baru ~ '^K[0-9]{2}$'::text)),
    CONSTRAINT mk_padanan_sah_kurikulum_lama_check CHECK ((kurikulum_lama ~ '^K[0-9]{2}$'::text)),
    CONSTRAINT mk_padanan_sah_status_check CHECK ((status = ANY (ARRAY['draf'::text, 'disahkan'::text, 'ditetapkan'::text])))
);

CREATE TABLE public.mk_padanan_sah_log (
    id bigint NOT NULL,
    kurikulum_lama text NOT NULL,
    kurikulum_baru text NOT NULL,
    aksi text NOT NULL,
    oleh_id uuid,
    oleh_nama text,
    catatan text,
    revisi integer,
    pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_padanan_sah_log_aksi_check CHECK ((aksi = ANY (ARRAY['sahkan'::text, 'tetapkan'::text, 'kembalikan'::text, 'berubah'::text]))),
    CONSTRAINT mk_padanan_sah_log_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000)))
);

ALTER TABLE public.mk_padanan_sah_log ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_padanan_sah_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_rps (
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    data jsonb NOT NULL,
    status text DEFAULT 'draf'::text NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    revisi integer DEFAULT 0 NOT NULL,
    sah jsonb,
    sah_pada timestamp with time zone,
    sah_oleh uuid,
    sah_atas_nama uuid,
    tetap_pada timestamp with time zone,
    tetap_oleh uuid,
    tetap_atas_nama uuid,
    kode_verifikasi uuid,
    CONSTRAINT mk_rps_data_check CHECK (((jsonb_typeof(data) = 'object'::text) AND ((data ->> 'versi'::text) = '1'::text) AND (pg_column_size(data) <= 300000))),
    CONSTRAINT mk_rps_status_check CHECK ((status = ANY (ARRAY['draf'::text, 'diajukan'::text, 'dikembalikan'::text, 'disahkan'::text])))
);

CREATE TABLE public.mk_rps_pengesahan (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    aksi text NOT NULL,
    oleh_id uuid,
    oleh_nama text,
    catatan text,
    revisi integer,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    penyusun_sendiri boolean DEFAULT false NOT NULL,
    atas_nama_id uuid,
    atas_nama_nama text,
    CONSTRAINT mk_rps_pengesahan_aksi_check CHECK ((aksi = ANY (ARRAY['ajukan'::text, 'kembalikan'::text, 'sahkan'::text, 'tetapkan'::text]))),
    CONSTRAINT mk_rps_pengesahan_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000)))
);

ALTER TABLE public.mk_rps_pengesahan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_rps_pengesahan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_rps_review (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    reviewer_id uuid NOT NULL,
    ditunjuk_oleh uuid,
    ditunjuk_pada timestamp with time zone DEFAULT now() NOT NULL,
    skor jsonb DEFAULT '{}'::jsonb NOT NULL,
    catatan jsonb DEFAULT '{}'::jsonb NOT NULL,
    umum text,
    kesimpulan text,
    revisi integer,
    sidik text,
    kirim_pada timestamp with time zone,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    tanggapan jsonb DEFAULT '{}'::jsonb NOT NULL,
    tanggapan_umum text,
    tanggapan_pada timestamp with time zone,
    tanggapan_oleh uuid,
    dikabari_pada timestamp with time zone,
    CONSTRAINT mk_rps_review_catatan_check CHECK (((jsonb_typeof(catatan) = 'object'::text) AND (pg_column_size(catatan) <= 60000))),
    CONSTRAINT mk_rps_review_kesimpulan_check CHECK (((kesimpulan IS NULL) OR (kesimpulan = ANY (ARRAY['layak'::text, 'perbaikan_kecil'::text, 'perbaikan_besar'::text])))),
    CONSTRAINT mk_rps_review_skor_check CHECK (((jsonb_typeof(skor) = 'object'::text) AND (pg_column_size(skor) <= 20000))),
    CONSTRAINT mk_rps_review_tanggapan_check CHECK (((jsonb_typeof(tanggapan) = 'object'::text) AND (pg_column_size(tanggapan) <= 60000))),
    CONSTRAINT mk_rps_review_tanggapan_umum_check CHECK (((tanggapan_umum IS NULL) OR (length(tanggapan_umum) <= 8000))),
    CONSTRAINT mk_rps_review_umum_check CHECK (((umum IS NULL) OR (length(umum) <= 8000)))
);

ALTER TABLE public.mk_rps_review ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_rps_review_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_rps_riwayat (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    data jsonb NOT NULL,
    status text,
    oleh text,
    waktu timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.mk_rps_riwayat ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_rps_riwayat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_rps_tinjauan (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    term_order integer GENERATED ALWAYS AS (public.term_urut(tahun_akademik, semester)) STORED,
    data jsonb NOT NULL,
    keputusan text,
    status text DEFAULT 'draf'::text NOT NULL,
    rps_dasar jsonb,
    disetujui_pada timestamp with time zone,
    disetujui_oleh uuid,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_rps_tinjauan_data_check CHECK (((jsonb_typeof(data) = 'object'::text) AND ((data ->> 'versi'::text) = '1'::text) AND (pg_column_size(data) <= 100000))),
    CONSTRAINT mk_rps_tinjauan_keputusan_check CHECK (((keputusan IS NULL) OR (keputusan = ANY (ARRAY['tetap'::text, 'revisi'::text, 'tidak_berlanjut'::text])))),
    CONSTRAINT mk_rps_tinjauan_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT mk_rps_tinjauan_status_check CHECK ((status = ANY (ARRAY['draf'::text, 'diajukan'::text, 'dikembalikan'::text, 'disetujui'::text]))),
    CONSTRAINT mk_rps_tinjauan_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text))
);

ALTER TABLE public.mk_rps_tinjauan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_rps_tinjauan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_rps_tinjauan_log (
    id bigint NOT NULL,
    tinjauan_id bigint NOT NULL,
    aksi text NOT NULL,
    oleh_id uuid,
    oleh_nama text,
    catatan text,
    penyusun_sendiri boolean DEFAULT false NOT NULL,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_rps_tinjauan_log_aksi_check CHECK ((aksi = ANY (ARRAY['ajukan'::text, 'kembalikan'::text, 'setujui'::text]))),
    CONSTRAINT mk_rps_tinjauan_log_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000)))
);

ALTER TABLE public.mk_rps_tinjauan_log ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_rps_tinjauan_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_rps_ttd (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    url text NOT NULL,
    nama text,
    revisi integer,
    oleh text,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_rps_ttd_nama_check CHECK (((nama IS NULL) OR (length(nama) <= 200))),
    CONSTRAINT mk_rps_ttd_url_check CHECK ((url ~* '^https://\S+$'::text))
);

ALTER TABLE public.mk_rps_ttd ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_rps_ttd_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_silabus (
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    data jsonb NOT NULL,
    status text DEFAULT 'draf'::text NOT NULL,
    revisi integer DEFAULT 0 NOT NULL,
    sah jsonb,
    sah_pada timestamp with time zone,
    sah_oleh uuid,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_silabus_data_check CHECK (((jsonb_typeof(data) = 'object'::text) AND ((data ->> 'versi'::text) = '1'::text) AND (pg_column_size(data) <= 100000))),
    CONSTRAINT mk_silabus_status_check CHECK ((status = ANY (ARRAY['draf'::text, 'diajukan'::text, 'dikembalikan'::text, 'disahkan'::text])))
);

CREATE TABLE public.mk_silabus_log (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    aksi text NOT NULL,
    oleh_id uuid,
    oleh_nama text,
    catatan text,
    revisi integer,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_silabus_log_aksi_check CHECK ((aksi = ANY (ARRAY['impor'::text, 'ajukan'::text, 'kembalikan'::text, 'sahkan'::text]))),
    CONSTRAINT mk_silabus_log_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000)))
);

ALTER TABLE public.mk_silabus_log ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_silabus_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.mk_struktur (
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    data jsonb NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT mk_struktur_data_check CHECK (((jsonb_typeof(data) = 'object'::text) AND ((data ->> 'versi'::text) = '1'::text) AND (jsonb_typeof((data -> 'cpmk'::text)) = 'array'::text) AND (jsonb_typeof((data -> 'sub'::text)) = 'array'::text) AND (jsonb_typeof((data -> 'asesmen'::text)) = 'array'::text) AND (jsonb_typeof((data -> 'bobot'::text)) = 'object'::text) AND (jsonb_array_length((data -> 'cpmk'::text)) <= 10) AND (jsonb_array_length((data -> 'sub'::text)) <= 50) AND (jsonb_array_length((data -> 'asesmen'::text)) <= 50) AND (pg_column_size(data) <= 300000)))
);

CREATE TABLE public.mk_struktur_riwayat (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    data jsonb NOT NULL,
    oleh text,
    waktu timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.mk_struktur_riwayat ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.mk_struktur_riwayat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.pemakaian_halaman (
    tanggal date NOT NULL,
    halaman text NOT NULL,
    dosen_id uuid NOT NULL,
    peran text,
    jabatan text[] DEFAULT '{}'::text[] NOT NULL,
    n integer DEFAULT 1 NOT NULL,
    CONSTRAINT pemakaian_halaman_halaman_check CHECK ((halaman ~ '^[a-z0-9._-]{1,80}$'::text))
);

CREATE TABLE public.pengajuan_berkas (
    id bigint NOT NULL,
    pengajuan_id bigint NOT NULL,
    jenis text NOT NULL,
    nama text DEFAULT ''::text NOT NULL,
    url text NOT NULL,
    oleh text DEFAULT 'mahasiswa'::text NOT NULL,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    tautan boolean DEFAULT false NOT NULL,
    CONSTRAINT pengajuan_berkas_jenis_check CHECK (((jenis = ANY (ARRAY['surat_permohonan'::text, 'surat_balasan'::text, 'laporan_kp'::text, 'surat_selesai'::text, 'logbook'::text, 'nilai_lapangan'::text, 'laporan_lomba'::text, 'sertifikat'::text, 'surat_tugas'::text, 'foto'::text, 'lainnya'::text, 'surat_pengantar'::text, 'surat_jadi'::text, 'naskah_ta'::text, 'bukti_luaran'::text])) OR (jenis ~ '^yud_[a-z0-9_]{2,40}$'::text) OR (jenis ~ '^ta_[a-z0-9_]{2,40}$'::text))),
    CONSTRAINT pengajuan_berkas_nama_check CHECK ((length(nama) <= 200)),
    CONSTRAINT pengajuan_berkas_url_check CHECK ((url ~* '^https://\S+$'::text))
);

ALTER TABLE public.pengajuan_berkas ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.pengajuan_berkas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE public.pengajuan_mahasiswa ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.pengajuan_mahasiswa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.pengajuan_riwayat (
    id bigint NOT NULL,
    pengajuan_id bigint NOT NULL,
    status text NOT NULL,
    oleh text NOT NULL,
    catatan text,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    tahap text DEFAULT 'pengajuan'::text NOT NULL,
    CONSTRAINT pengajuan_riwayat_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000)))
);

ALTER TABLE public.pengajuan_riwayat ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.pengajuan_riwayat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.pengaturan (
    kunci text NOT NULL,
    nilai numeric,
    keterangan text
);

CREATE TABLE public.pengelola_prodi (
    id bigint NOT NULL,
    jabatan text NOT NULL,
    nidn text,
    nama text,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pengelola_prodi_check CHECK (((nidn IS NOT NULL) OR (nama IS NOT NULL))),
    CONSTRAINT pengelola_prodi_jabatan_check CHECK (((length(btrim(jabatan)) >= 3) AND (length(btrim(jabatan)) <= 120))),
    CONSTRAINT pengelola_prodi_nama_check CHECK (((nama IS NULL) OR ((length(btrim(nama)) >= 3) AND (length(btrim(nama)) <= 160)))),
    CONSTRAINT pengelola_prodi_nidn_check CHECK (((nidn IS NULL) OR (length(nidn) <= 20)))
);

ALTER TABLE public.pengelola_prodi ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.pengelola_prodi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.pengumuman_mahasiswa (
    id bigint NOT NULL,
    judul text NOT NULL,
    isi text DEFAULT ''::text NOT NULL,
    berlaku_sampai date,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pengumuman_mahasiswa_isi_check CHECK ((length(isi) <= 4000)),
    CONSTRAINT pengumuman_mahasiswa_judul_check CHECK (((length(btrim(judul)) >= 1) AND (length(btrim(judul)) <= 200)))
);

CREATE SEQUENCE public.pengumuman_mahasiswa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.pengumuman_mahasiswa_id_seq OWNED BY public.pengumuman_mahasiswa.id;

CREATE TABLE public.peringatan_keamanan (
    id bigint NOT NULL,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    jenis text NOT NULL,
    oleh text NOT NULL,
    rinci text NOT NULL,
    dikirim timestamp with time zone,
    CONSTRAINT peringatan_keamanan_jenis_check CHECK ((jenis = ANY (ARRAY['akun_baru'::text, 'peran'::text, 'email'::text, 'akun_dihapus'::text, 'koordinator'::text, 'hapus_massal'::text])))
);

ALTER TABLE public.peringatan_keamanan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.peringatan_keamanan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.portofolio_berkas (
    id bigint NOT NULL,
    tahun_akademik text NOT NULL,
    semester text NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    kelas text,
    komponen text NOT NULL,
    asesmen text,
    nama_berkas text,
    url text NOT NULL,
    oleh text,
    diunggah timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT portofolio_berkas_asesmen_check CHECK (((asesmen IS NULL) OR ((length(asesmen) >= 1) AND (length(asesmen) <= 100)))),
    CONSTRAINT portofolio_berkas_check CHECK (((komponen = 'lainnya'::text) OR ((komponen = ANY (ARRAY['materi'::text, 'soal'::text, 'kunci'::text, 'rubrik'::text])) = (kelas IS NULL)))),
    CONSTRAINT portofolio_berkas_kelas_check CHECK (((kelas IS NULL) OR ((length(kelas) >= 1) AND (length(kelas) <= 10)))),
    CONSTRAINT portofolio_berkas_komponen_check CHECK ((komponen = ANY (ARRAY['materi'::text, 'soal'::text, 'kunci'::text, 'rubrik'::text, 'contoh_tinggi'::text, 'contoh_sedang'::text, 'contoh_rendah'::text, 'presensi'::text, 'bap'::text, 'lainnya'::text]))),
    CONSTRAINT portofolio_berkas_nama_berkas_check CHECK (((nama_berkas IS NULL) OR (length(nama_berkas) <= 200))),
    CONSTRAINT portofolio_berkas_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT portofolio_berkas_tahun_akademik_check CHECK ((tahun_akademik ~ '^\d{4}/\d{4}$'::text)),
    CONSTRAINT portofolio_berkas_url_check CHECK ((url ~* '^https://'::text))
);

ALTER TABLE public.portofolio_berkas ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.portofolio_berkas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.potret_skor (
    id bigint NOT NULL,
    diambil timestamp with time zone DEFAULT now() NOT NULL,
    bulan date NOT NULL,
    otomatis boolean DEFAULT false NOT NULL,
    ts integer NOT NULL,
    na numeric NOT NULL,
    na_maks numeric,
    cakupan numeric,
    status text,
    butir_terisi integer,
    butir_total integer,
    skor jsonb DEFAULT '{}'::jsonb NOT NULL,
    syarat jsonb DEFAULT '{}'::jsonb NOT NULL,
    catatan text,
    oleh text,
    CONSTRAINT potret_skor_bulan_check CHECK ((EXTRACT(day FROM bulan) = (1)::numeric)),
    CONSTRAINT potret_skor_butir_terisi_check CHECK ((butir_terisi >= 0)),
    CONSTRAINT potret_skor_butir_total_check CHECK ((butir_total >= 0)),
    CONSTRAINT potret_skor_cakupan_check CHECK (((cakupan >= (0)::numeric) AND (cakupan <= (100)::numeric))),
    CONSTRAINT potret_skor_catatan_check CHECK ((length(catatan) <= 200)),
    CONSTRAINT potret_skor_na_check CHECK (((na >= (0)::numeric) AND (na <= (400)::numeric))),
    CONSTRAINT potret_skor_na_maks_check CHECK (((na_maks >= (0)::numeric) AND (na_maks <= (400)::numeric))),
    CONSTRAINT potret_skor_skor_check CHECK ((jsonb_typeof(skor) = 'object'::text)),
    CONSTRAINT potret_skor_status_check CHECK ((length(status) <= 80)),
    CONSTRAINT potret_skor_syarat_check CHECK ((jsonb_typeof(syarat) = 'object'::text)),
    CONSTRAINT potret_skor_ts_check CHECK (((ts >= 2000) AND (ts <= 2100)))
);

ALTER TABLE public.potret_skor ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.potret_skor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.profil_prodi (
    id smallint DEFAULT 1 NOT NULL,
    sejarah text,
    sambutan text,
    penyambut_nidn text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT profil_prodi_id_check CHECK ((id = 1)),
    CONSTRAINT profil_prodi_penyambut_nidn_check CHECK (((penyambut_nidn IS NULL) OR (length(penyambut_nidn) <= 20))),
    CONSTRAINT profil_prodi_sambutan_check CHECK (((sambutan IS NULL) OR (length(sambutan) <= 2500))),
    CONSTRAINT profil_prodi_sejarah_check CHECK (((sejarah IS NULL) OR (length(sejarah) <= 4000)))
);

CREATE TABLE public.rapat (
    id bigint NOT NULL,
    judul text NOT NULL,
    jenis text DEFAULT 'rapat_prodi'::text NOT NULL,
    tanggal date NOT NULL,
    mulai time without time zone,
    selesai time without time zone,
    tempat text,
    pimpinan text,
    notulis text,
    agenda text,
    pembahasan text,
    terbatas boolean DEFAULT false NOT NULL,
    status text DEFAULT 'draf'::text NOT NULL,
    dokumen_id bigint,
    token_hadir text,
    hadir_sampai timestamp with time zone,
    dibuat_oleh uuid NOT NULL,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT rapat_jenis_check CHECK ((jenis ~ '^[a-z0-9_]{2,40}$'::text)),
    CONSTRAINT rapat_judul_check CHECK (((length(judul) >= 1) AND (length(judul) <= 300))),
    CONSTRAINT rapat_status_check CHECK ((status = ANY (ARRAY['draf'::text, 'final'::text]))),
    CONSTRAINT rapat_token_hadir_check CHECK (((token_hadir IS NULL) OR (length(token_hadir) >= 32)))
);

ALTER TABLE public.rapat ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.rapat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.rapat_peserta (
    id bigint NOT NULL,
    rapat_id bigint NOT NULL,
    dosen_id uuid,
    nama text NOT NULL,
    instansi text,
    peran text DEFAULT 'peserta'::text NOT NULL,
    hadir boolean DEFAULT true NOT NULL,
    cara text DEFAULT 'dicatat'::text NOT NULL,
    klien uuid,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT rapat_peserta_cara_check CHECK ((cara = ANY (ARRAY['dicatat'::text, 'daring'::text]))),
    CONSTRAINT rapat_peserta_instansi_check CHECK (((instansi IS NULL) OR (length(instansi) <= 160))),
    CONSTRAINT rapat_peserta_nama_check CHECK (((length(TRIM(BOTH FROM nama)) >= 2) AND (length(TRIM(BOTH FROM nama)) <= 120))),
    CONSTRAINT rapat_peserta_peran_check CHECK ((peran = ANY (ARRAY['pimpinan'::text, 'notulis'::text, 'narasumber'::text, 'peserta'::text])))
);

ALTER TABLE public.rapat_peserta ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.rapat_peserta_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.rapat_tindak (
    id bigint NOT NULL,
    rapat_id bigint NOT NULL,
    urutan integer DEFAULT 1 NOT NULL,
    keputusan text NOT NULL,
    pj_dosen_id uuid,
    pj_nama text,
    tenggat date,
    status text DEFAULT 'terbuka'::text NOT NULL,
    tanggal_selesai date,
    catatan text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT rapat_tindak_keputusan_check CHECK ((length(TRIM(BOTH FROM keputusan)) >= 2)),
    CONSTRAINT rapat_tindak_status_check CHECK ((status = ANY (ARRAY['terbuka'::text, 'proses'::text, 'selesai'::text, 'batal'::text])))
);

ALTER TABLE public.rapat_tindak ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.rapat_tindak_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_bidang_keahlian (
    id bigint NOT NULL,
    kode text NOT NULL,
    nama text NOT NULL,
    nama_en text NOT NULL,
    cakupan text,
    urutan integer DEFAULT 100 NOT NULL,
    aktif boolean DEFAULT true NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_bidang_keahlian_kode_check CHECK ((kode ~ '^[A-Z]{3}$'::text))
);

ALTER TABLE public.ref_bidang_keahlian ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ref_bidang_keahlian_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_cpl (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode text NOT NULL,
    ranah text,
    rumusan text NOT NULL,
    rumusan_en text,
    indikator text,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_cpl_indikator_check CHECK (((indikator IS NULL) OR (length(indikator) <= 5000))),
    CONSTRAINT ref_cpl_kode_check CHECK ((kode ~ '^[A-Za-z0-9.-]{1,10}$'::text)),
    CONSTRAINT ref_cpl_kurikulum_check CHECK ((kurikulum ~ '^K[0-9]{2}$'::text)),
    CONSTRAINT ref_cpl_ranah_check CHECK (((ranah IS NULL) OR (length(ranah) <= 100))),
    CONSTRAINT ref_cpl_rumusan_check CHECK (((length(rumusan) >= 1) AND (length(rumusan) <= 2000))),
    CONSTRAINT ref_cpl_rumusan_en_check CHECK (((rumusan_en IS NULL) OR (length(rumusan_en) <= 2000)))
);

ALTER TABLE public.ref_cpl ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ref_cpl_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_cpl_korelasi (
    id bigint NOT NULL,
    kurikulum_asal text NOT NULL,
    cpl_asal text NOT NULL,
    kurikulum_tujuan text NOT NULL,
    cpl_tujuan text NOT NULL,
    tingkat text NOT NULL,
    alasan text,
    status text DEFAULT 'usulan'::text NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_cpl_korelasi_alasan_check CHECK (((alasan IS NULL) OR (length(alasan) <= 1000))),
    CONSTRAINT ref_cpl_korelasi_check CHECK ((kurikulum_asal <> kurikulum_tujuan)),
    CONSTRAINT ref_cpl_korelasi_status_check CHECK ((status = ANY (ARRAY['usulan'::text, 'disetujui'::text]))),
    CONSTRAINT ref_cpl_korelasi_tingkat_check CHECK ((tingkat = ANY (ARRAY['setara'::text, 'sebagian'::text])))
);

ALTER TABLE public.ref_cpl_korelasi ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ref_cpl_korelasi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_kata_visi (
    kata text NOT NULL
);

CREATE TABLE public.ref_kategori_publikasi (
    kode text NOT NULL,
    nama text NOT NULL,
    tingkat_lkps text NOT NULL,
    indeksasi_lkps text,
    lembar_lkps text,
    aktif boolean DEFAULT true NOT NULL,
    urutan integer DEFAULT 0 NOT NULL,
    CONSTRAINT ref_kategori_publikasi_tingkat_lkps_check CHECK ((tingkat_lkps = ANY (ARRAY['internasional'::text, 'nasional'::text, 'wilayah_lokal'::text])))
);

CREATE TABLE public.ref_kelompok_dana (
    kode text NOT NULL,
    nama text NOT NULL,
    urutan integer DEFAULT 0 NOT NULL
);

CREATE TABLE public.ref_mata_kuliah (
    kode text NOT NULL,
    nama text NOT NULL,
    sks numeric,
    semester integer,
    inti boolean DEFAULT false NOT NULL,
    aktif boolean DEFAULT true NOT NULL,
    urutan integer DEFAULT 100 NOT NULL,
    id bigint NOT NULL,
    sks_kuliah numeric,
    sks_seminar numeric,
    sks_praktikum numeric,
    rps_ada boolean,
    rps_url text,
    unit_penyelenggara text,
    basic_science boolean DEFAULT false NOT NULL,
    capstone boolean DEFAULT false NOT NULL,
    capstone_cakupan text,
    capstone_pendukung text[] DEFAULT '{}'::text[] NOT NULL,
    pengampu text[] DEFAULT '{}'::text[] NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    rps_9_komponen boolean,
    sifat text,
    kurikulum text NOT NULL,
    nama_en text,
    peminatan text,
    koordinator_nidn text,
    CONSTRAINT ref_mata_kuliah_koordinator_tim_check CHECK (((koordinator_nidn IS NULL) OR (koordinator_nidn = ANY (pengampu)))),
    CONSTRAINT ref_mata_kuliah_kurikulum_check CHECK ((kurikulum ~ '^K[0-9]{2}$'::text)),
    CONSTRAINT ref_mata_kuliah_nama_en_check CHECK (((nama_en IS NULL) OR (length(nama_en) <= 200))),
    CONSTRAINT ref_mata_kuliah_peminatan_check CHECK (((peminatan IS NULL) OR (peminatan ~ '^[A-Z0-9]{2,12}$'::text))),
    CONSTRAINT ref_mata_kuliah_semester_check CHECK (((semester IS NULL) OR ((semester >= 1) AND (semester <= 14)))),
    CONSTRAINT ref_mata_kuliah_sifat_check CHECK (((sifat IS NULL) OR (sifat = ANY (ARRAY['wajib'::text, 'pilihan'::text])))),
    CONSTRAINT ref_mata_kuliah_sks_check CHECK (((COALESCE(sks_kuliah, (0)::numeric) >= (0)::numeric) AND (COALESCE(sks_seminar, (0)::numeric) >= (0)::numeric) AND (COALESCE(sks_praktikum, (0)::numeric) >= (0)::numeric) AND (COALESCE(sks, (0)::numeric) >= (0)::numeric))),
    CONSTRAINT ref_mata_kuliah_unit_check CHECK (((unit_penyelenggara IS NULL) OR (unit_penyelenggara = ANY (ARRAY['universitas'::text, 'fakultas'::text, 'prodi'::text]))))
);

COMMENT ON COLUMN public.ref_mata_kuliah.koordinator_nidn IS 'Koordinator MK (158, pemilik 2026-11-23); salah satu anggota pengampu (tim). Ditetapkan Kaprodi aktif atau admin.';

ALTER TABLE public.ref_mata_kuliah ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.ref_mata_kuliah_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_mk_cpl (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode_mk text NOT NULL,
    cpl text NOT NULL,
    indikator text,
    bobot numeric,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_mk_cpl_bobot_check CHECK (((bobot IS NULL) OR ((bobot > (0)::numeric) AND (bobot <= (100)::numeric)))),
    CONSTRAINT ref_mk_cpl_indikator_check CHECK (((indikator IS NULL) OR (length(indikator) <= 300)))
);

ALTER TABLE public.ref_mk_cpl ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ref_mk_cpl_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_mk_padanan (
    id bigint NOT NULL,
    kurikulum_lama text NOT NULL,
    kode_lama text NOT NULL,
    kurikulum_baru text,
    kode_baru text,
    model text,
    tidak_berlanjut boolean DEFAULT false NOT NULL,
    catatan text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_mk_padanan_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 500))),
    CONSTRAINT ref_mk_padanan_check CHECK (((tidak_berlanjut = (kode_baru IS NULL)) AND ((kode_baru IS NULL) = (kurikulum_baru IS NULL)))),
    CONSTRAINT ref_mk_padanan_model_check CHECK (((model IS NULL) OR (model = ANY (ARRAY['1:1'::text, '1:2'::text, '2:1'::text, 'nama sama'::text]))))
);

ALTER TABLE public.ref_mk_padanan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ref_mk_padanan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_profil_lulusan (
    id bigint NOT NULL,
    kurikulum text NOT NULL,
    kode text NOT NULL,
    nama text NOT NULL,
    nama_en text,
    deskripsi text,
    cpl text,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_profil_lulusan_cpl_check CHECK (((cpl IS NULL) OR (length(cpl) <= 300))),
    CONSTRAINT ref_profil_lulusan_deskripsi_check CHECK (((deskripsi IS NULL) OR (length(deskripsi) <= 3000))),
    CONSTRAINT ref_profil_lulusan_kode_check CHECK ((kode ~ '^[A-Za-z0-9.-]{1,10}$'::text)),
    CONSTRAINT ref_profil_lulusan_kurikulum_check CHECK ((kurikulum ~ '^K[0-9]{2}$'::text)),
    CONSTRAINT ref_profil_lulusan_nama_check CHECK (((length(btrim(nama)) >= 1) AND (length(btrim(nama)) <= 200))),
    CONSTRAINT ref_profil_lulusan_nama_en_check CHECK (((nama_en IS NULL) OR (length(nama_en) <= 200)))
);

ALTER TABLE public.ref_profil_lulusan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ref_profil_lulusan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_skema_dana (
    kode text NOT NULL,
    nama text NOT NULL,
    kelompok text NOT NULL,
    kategori text DEFAULT 'keduanya'::text NOT NULL,
    sumber_dana_lkps text NOT NULL,
    penyelenggara text,
    aktif boolean DEFAULT true NOT NULL,
    urutan integer DEFAULT 0 NOT NULL,
    catatan text,
    CONSTRAINT ref_skema_dana_kategori_check CHECK ((kategori = ANY (ARRAY['penelitian'::text, 'pkm'::text, 'keduanya'::text]))),
    CONSTRAINT ref_skema_dana_sumber_dana_lkps_check CHECK ((sumber_dana_lkps = ANY (ARRAY['mandiri'::text, 'perguruan_tinggi'::text, 'dalam_negeri'::text, 'luar_negeri'::text])))
);

CREATE TABLE public.ref_tema_peta_jalan (
    id bigint NOT NULL,
    nama text NOT NULL,
    jenis text DEFAULT 'keduanya'::text NOT NULL,
    keterangan text,
    aktif boolean DEFAULT true NOT NULL,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_tema_peta_jalan_jenis_check CHECK ((jenis = ANY (ARRAY['penelitian'::text, 'pkm'::text, 'keduanya'::text])))
);

ALTER TABLE public.ref_tema_peta_jalan ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.ref_tema_peta_jalan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ref_topik_keahlian (
    id bigint NOT NULL,
    kode text NOT NULL,
    bidang text NOT NULL,
    nama text NOT NULL,
    nama_en text NOT NULL,
    sinonim text,
    padanan text,
    urutan integer DEFAULT 100 NOT NULL,
    aktif boolean DEFAULT true NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ref_topik_keahlian_kode_check CHECK ((kode ~ '^[A-Z]{3}[0-9]{2,3}$'::text))
);

ALTER TABLE public.ref_topik_keahlian ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ref_topik_keahlian_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.spmi_capaian (
    standar_id bigint NOT NULL,
    tahun_ts integer NOT NULL,
    target text,
    capaian text,
    status text,
    bukti_url text,
    dokumen_id bigint,
    analisis text,
    rencana text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT spmi_capaian_analisis_check CHECK (((analisis IS NULL) OR (length(analisis) <= 4000))),
    CONSTRAINT spmi_capaian_bukti_url_check CHECK (((bukti_url IS NULL) OR (bukti_url ~* '^https?://'::text))),
    CONSTRAINT spmi_capaian_capaian_check CHECK (((capaian IS NULL) OR (length(capaian) <= 4000))),
    CONSTRAINT spmi_capaian_rencana_check CHECK (((rencana IS NULL) OR (length(rencana) <= 4000))),
    CONSTRAINT spmi_capaian_status_check CHECK ((status = ANY (ARRAY['tercapai'::text, 'belum'::text, 'tidak_berlaku'::text]))),
    CONSTRAINT spmi_capaian_tahun_ts_check CHECK (((tahun_ts >= 2000) AND (tahun_ts <= 2100))),
    CONSTRAINT spmi_capaian_target_check CHECK (((target IS NULL) OR (length(target) <= 4000)))
);

CREATE TABLE public.spmi_standar (
    id bigint NOT NULL,
    kode text NOT NULL,
    induk text,
    sub text,
    lembar text,
    pernyataan text NOT NULL,
    luaran text,
    pic text,
    referensi text,
    asal text DEFAULT 'institusi'::text NOT NULL,
    dipantau boolean DEFAULT true NOT NULL,
    dokumen_id bigint,
    berlaku_sejak date,
    aktif boolean DEFAULT true NOT NULL,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT spmi_standar_asal_check CHECK ((asal = ANY (ARRAY['institusi'::text, 'prodi'::text]))),
    CONSTRAINT spmi_standar_induk_check CHECK (((induk IS NULL) OR (length(induk) <= 200))),
    CONSTRAINT spmi_standar_kode_check CHECK (((length(kode) >= 1) AND (length(kode) <= 30))),
    CONSTRAINT spmi_standar_lembar_check CHECK (((lembar IS NULL) OR (length(lembar) <= 100))),
    CONSTRAINT spmi_standar_luaran_check CHECK (((luaran IS NULL) OR (length(luaran) <= 8000))),
    CONSTRAINT spmi_standar_pernyataan_check CHECK (((length(pernyataan) >= 1) AND (length(pernyataan) <= 8000))),
    CONSTRAINT spmi_standar_pic_check CHECK (((pic IS NULL) OR (length(pic) <= 200))),
    CONSTRAINT spmi_standar_referensi_check CHECK (((referensi IS NULL) OR (length(referensi) <= 1000))),
    CONSTRAINT spmi_standar_sub_check CHECK (((sub IS NULL) OR (length(sub) <= 300)))
);

ALTER TABLE public.spmi_standar ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.spmi_standar_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.spmi_standar_revisi (
    id bigint NOT NULL,
    standar_id bigint NOT NULL,
    tanggal date NOT NULL,
    versi text,
    perubahan text NOT NULL,
    dasar text DEFAULT 'rtm'::text NOT NULL,
    rapat_id bigint,
    temuan_id bigint,
    dokumen_id bigint,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT spmi_standar_revisi_dasar_check CHECK ((dasar = ANY (ARRAY['rtm'::text, 'ami'::text, 'evaluasi_capaian'::text, 'kebijakan'::text, 'lainnya'::text]))),
    CONSTRAINT spmi_standar_revisi_perubahan_check CHECK (((length(perubahan) >= 1) AND (length(perubahan) <= 4000))),
    CONSTRAINT spmi_standar_revisi_versi_check CHECK (((versi IS NULL) OR (length(versi) <= 30)))
);

ALTER TABLE public.spmi_standar_revisi ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.spmi_standar_revisi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.status_sistem (
    kunci text NOT NULL,
    waktu timestamp with time zone DEFAULT now() NOT NULL,
    ok boolean DEFAULT true NOT NULL,
    isi jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT status_sistem_kunci_check CHECK ((kunci ~ '^[a-z_]{3,40}$'::text))
);

CREATE TABLE public.survei (
    id bigint NOT NULL,
    kelompok text NOT NULL,
    judul text NOT NULL,
    tahun_ts integer NOT NULL,
    mulai date NOT NULL,
    selesai date NOT NULL,
    token text DEFAULT replace((gen_random_uuid())::text, '-'::text, ''::text) NOT NULL,
    pertanyaan jsonb NOT NULL,
    pengantar text,
    publik boolean DEFAULT true NOT NULL,
    dicabut boolean DEFAULT false NOT NULL,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    identitas text DEFAULT 'tidak'::text NOT NULL,
    ambang_puas numeric DEFAULT 75 NOT NULL,
    ambang_rerata numeric DEFAULT 3 NOT NULL,
    judul_en text,
    pengantar_en text,
    rekap_terbit jsonb,
    terbit_pada timestamp with time zone,
    terbit_oleh text,
    CONSTRAINT survei_ambang_puas_check CHECK (((ambang_puas >= (0)::numeric) AND (ambang_puas <= (100)::numeric))),
    CONSTRAINT survei_ambang_rerata_check CHECK (((ambang_rerata >= (1)::numeric) AND (ambang_rerata <= (4)::numeric))),
    CONSTRAINT survei_identitas_check CHECK ((identitas = ANY (ARRAY['tidak'::text, 'opsional'::text, 'wajib'::text]))),
    CONSTRAINT survei_judul_check CHECK (((length(judul) >= 3) AND (length(judul) <= 150))),
    CONSTRAINT survei_judul_en_check CHECK (((judul_en IS NULL) OR ((length(judul_en) >= 3) AND (length(judul_en) <= 150)))),
    CONSTRAINT survei_kelompok_check CHECK ((kelompok = ANY (ARRAY['mahasiswa'::text, 'dosen'::text, 'tendik'::text, 'mitra'::text, 'pengguna'::text, 'alumni'::text]))),
    CONSTRAINT survei_pengantar_check CHECK ((length(pengantar) <= 2000)),
    CONSTRAINT survei_pengantar_en_check CHECK (((pengantar_en IS NULL) OR (length(pengantar_en) <= 2000))),
    CONSTRAINT survei_pertanyaan_check CHECK (((jsonb_typeof(pertanyaan) = 'array'::text) AND ((jsonb_array_length(pertanyaan) >= 1) AND (jsonb_array_length(pertanyaan) <= 60)))),
    CONSTRAINT survei_tahun_ts_check CHECK (((tahun_ts >= 2000) AND (tahun_ts <= 2100))),
    CONSTRAINT survei_tanggal_check CHECK ((selesai >= mulai))
);

ALTER TABLE public.survei ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.survei_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.survei_jawaban (
    id bigint NOT NULL,
    survei_id bigint NOT NULL,
    klien uuid NOT NULL,
    diisi timestamp with time zone DEFAULT now() NOT NULL,
    jawaban jsonb NOT NULL,
    nama text,
    nim text,
    email text,
    CONSTRAINT survei_jawaban_email_check CHECK (((email IS NULL) OR ((length(email) <= 120) AND (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text)))),
    CONSTRAINT survei_jawaban_jawaban_check CHECK ((jsonb_typeof(jawaban) = 'object'::text)),
    CONSTRAINT survei_jawaban_nama_check CHECK ((length(nama) <= 120)),
    CONSTRAINT survei_jawaban_nim_check CHECK ((length(nim) <= 30))
);

ALTER TABLE public.survei_jawaban ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.survei_jawaban_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ta_arsip (
    nim text NOT NULL,
    nama text NOT NULL,
    url text NOT NULL,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ta_arsip_nama_check CHECK (((length(btrim(nama)) >= 2) AND (length(btrim(nama)) <= 200))),
    CONSTRAINT ta_arsip_nim_check CHECK (((length(btrim(nim)) >= 3) AND (length(btrim(nim)) <= 30))),
    CONSTRAINT ta_arsip_url_check CHECK ((url ~ '^https://(drive|docs)\.google\.com/\S+$'::text))
);

CREATE TABLE public.ta_berkas (
    tahap text NOT NULL,
    kode text NOT NULL,
    label text NOT NULL,
    keterangan text DEFAULT ''::text NOT NULL,
    wajib boolean DEFAULT true NOT NULL,
    urut integer DEFAULT 100 NOT NULL,
    aktif boolean DEFAULT true NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ta_berkas_keterangan_check CHECK ((length(keterangan) <= 500)),
    CONSTRAINT ta_berkas_kode_check CHECK (((kode = 'naskah_ta'::text) OR (kode ~ '^ta_[a-z0-9_]{2,40}$'::text))),
    CONSTRAINT ta_berkas_label_check CHECK (((length(btrim(label)) >= 2) AND (length(btrim(label)) <= 200))),
    CONSTRAINT ta_berkas_naskah_cek CHECK (((kode <> 'naskah_ta'::text) OR (wajib AND aktif))),
    CONSTRAINT ta_berkas_naskah_tahap_cek CHECK (((kode <> 'naskah_ta'::text) OR (tahap <> 'penetapan_pembimbing'::text))),
    CONSTRAINT ta_berkas_tahap_check CHECK ((tahap = ANY (ARRAY['penetapan_pembimbing'::text, 'seminar_proposal'::text, 'seminar_kemajuan'::text, 'sidang_akhir'::text])))
);

CREATE TABLE public.ta_bimbingan (
    id bigint NOT NULL,
    nim text NOT NULL,
    nama text NOT NULL,
    tanggal date NOT NULL,
    cara text NOT NULL,
    pembimbing_id uuid,
    topik text NOT NULL,
    arahan text DEFAULT ''::text NOT NULL,
    status text DEFAULT 'menunggu'::text NOT NULL,
    catatan_pembimbing text,
    konfirmasi_oleh text,
    konfirmasi_pada timestamp with time zone,
    diajukan timestamp with time zone DEFAULT now() NOT NULL,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    lampiran_nama text,
    lampiran_url text,
    lampiran_dihapus timestamp with time zone,
    CONSTRAINT ta_bimbingan_arahan_check CHECK ((length(arahan) <= 2000)),
    CONSTRAINT ta_bimbingan_cara_check CHECK ((cara = ANY (ARRAY['tatap_muka'::text, 'daring'::text]))),
    CONSTRAINT ta_bimbingan_catatan_pembimbing_check CHECK (((catatan_pembimbing IS NULL) OR (length(catatan_pembimbing) <= 1000))),
    CONSTRAINT ta_bimbingan_lampiran_cek CHECK (((lampiran_url IS NULL) OR (lampiran_url ~ '^https://(drive|docs)\.google\.com/\S+$'::text))),
    CONSTRAINT ta_bimbingan_lampiran_nama_cek CHECK (((lampiran_nama IS NULL) OR (length(lampiran_nama) <= 200))),
    CONSTRAINT ta_bimbingan_nama_check CHECK (((length(btrim(nama)) >= 2) AND (length(btrim(nama)) <= 200))),
    CONSTRAINT ta_bimbingan_nim_check CHECK (((length(btrim(nim)) >= 3) AND (length(btrim(nim)) <= 30))),
    CONSTRAINT ta_bimbingan_status_check CHECK ((status = ANY (ARRAY['menunggu'::text, 'dikonfirmasi'::text, 'dikembalikan'::text]))),
    CONSTRAINT ta_bimbingan_topik_check CHECK (((length(btrim(topik)) >= 5) AND (length(btrim(topik)) <= 1000)))
);

ALTER TABLE public.ta_bimbingan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ta_bimbingan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ta_kecuali_urutan (
    id bigint NOT NULL,
    nim text NOT NULL,
    tahap text NOT NULL,
    alasan text NOT NULL,
    oleh text,
    dibuat timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ta_kecuali_urutan_alasan_check CHECK (((length(btrim(alasan)) >= 5) AND (length(btrim(alasan)) <= 500))),
    CONSTRAINT ta_kecuali_urutan_nim_check CHECK (((length(btrim(nim)) >= 3) AND (length(btrim(nim)) <= 30))),
    CONSTRAINT ta_kecuali_urutan_tahap_check CHECK ((tahap = ANY (ARRAY['seminar_kemajuan'::text, 'sidang_akhir'::text])))
);

ALTER TABLE public.ta_kecuali_urutan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ta_kecuali_urutan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ta_kk_dekat (
    kk_a text NOT NULL,
    kk_b text NOT NULL,
    CONSTRAINT ta_kk_dekat_check CHECK ((kk_a < kk_b)),
    CONSTRAINT ta_kk_dekat_kk_a_check CHECK ((kk_a ~ '^[A-Z0-9]{2,12}$'::text)),
    CONSTRAINT ta_kk_dekat_kk_b_check CHECK ((kk_b ~ '^[A-Z0-9]{2,12}$'::text))
);

CREATE TABLE public.ta_kuota (
    id bigint NOT NULL,
    ts integer NOT NULL,
    dosen_id uuid,
    kuota integer NOT NULL,
    diubah timestamp with time zone DEFAULT now() NOT NULL,
    semester text NOT NULL,
    CONSTRAINT ta_kuota_kuota_check CHECK (((kuota >= 0) AND (kuota <= 100))),
    CONSTRAINT ta_kuota_semester_check CHECK ((semester = ANY (ARRAY['Ganjil'::text, 'Genap'::text]))),
    CONSTRAINT ta_kuota_ts_check CHECK (((ts >= 2000) AND (ts <= 2100)))
);

ALTER TABLE public.ta_kuota ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ta_kuota_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ta_nilai (
    id bigint NOT NULL,
    jadwal_id bigint NOT NULL,
    rubrik_id bigint NOT NULL,
    peran text NOT NULL,
    penilai_nidn text,
    penilai_nama text NOT NULL,
    nilai jsonb NOT NULL,
    total numeric(5,2) NOT NULL,
    catatan text,
    diisi_oleh text,
    diwakilkan boolean DEFAULT false NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    bagian text DEFAULT 'seminar'::text NOT NULL,
    CONSTRAINT ta_nilai_bagian_cek CHECK ((bagian = ANY (ARRAY['seminar'::text, 'bimbingan'::text]))),
    CONSTRAINT ta_nilai_bimbingan_cek CHECK (((bagian = 'seminar'::text) OR (peran = 'pembimbing'::text))),
    CONSTRAINT ta_nilai_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 2000))),
    CONSTRAINT ta_nilai_nilai_check CHECK ((jsonb_typeof(nilai) = 'object'::text)),
    CONSTRAINT ta_nilai_penilai_nama_check CHECK (((length(btrim(penilai_nama)) >= 2) AND (length(btrim(penilai_nama)) <= 200))),
    CONSTRAINT ta_nilai_penilai_nidn_check CHECK (((penilai_nidn IS NULL) OR (length(penilai_nidn) <= 30))),
    CONSTRAINT ta_nilai_peran_check CHECK ((peran = ANY (ARRAY['pembimbing'::text, 'penguji'::text]))),
    CONSTRAINT ta_nilai_total_check CHECK (((total >= (0)::numeric) AND (total <= (100)::numeric)))
);

ALTER TABLE public.ta_nilai ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ta_nilai_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE public.ta_rubrik ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ta_rubrik_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.ta_syarat_bimbingan (
    tahap text NOT NULL,
    minimal integer DEFAULT 4 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ta_syarat_bimbingan_minimal_check CHECK (((minimal >= 0) AND (minimal <= 50))),
    CONSTRAINT ta_syarat_bimbingan_tahap_check CHECK ((tahap = ANY (ARRAY['seminar_proposal'::text, 'seminar_kemajuan'::text, 'sidang_akhir'::text])))
);

CREATE TABLE public.tanya_jawab (
    id bigint NOT NULL,
    topik text,
    pertanyaan text NOT NULL,
    jawaban text NOT NULL,
    urutan integer DEFAULT 100 NOT NULL,
    tampil boolean DEFAULT true NOT NULL,
    sumber_id bigint,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tanya_jawab_jawaban_check CHECK (((length(btrim(jawaban)) >= 1) AND (length(btrim(jawaban)) <= 6000))),
    CONSTRAINT tanya_jawab_pertanyaan_check CHECK (((length(btrim(pertanyaan)) >= 3) AND (length(btrim(pertanyaan)) <= 1000))),
    CONSTRAINT tanya_jawab_topik_check CHECK (((topik IS NULL) OR (length(topik) <= 80)))
);

CREATE SEQUENCE public.tanya_jawab_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tanya_jawab_id_seq OWNED BY public.tanya_jawab.id;

CREATE TABLE public.target_baku (
    tahun integer NOT NULL,
    jabatan text NOT NULL,
    indikator text NOT NULL,
    target numeric(6,2) NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT target_baku_indikator_check CHECK ((indikator ~ '^[a-z_]{2,40}$'::text)),
    CONSTRAINT target_baku_jabatan_check CHECK ((jabatan = ANY (ARRAY['tenaga_pengajar'::text, 'asisten_ahli'::text, 'lektor'::text, 'lektor_kepala'::text, 'guru_besar'::text]))),
    CONSTRAINT target_baku_tahun_check CHECK (((tahun >= 2000) AND (tahun <= 2100))),
    CONSTRAINT target_baku_target_check CHECK ((target >= (0)::numeric))
);

CREATE TABLE public.target_dosen (
    tahun integer NOT NULL,
    dosen_id uuid NOT NULL,
    indikator text NOT NULL,
    target numeric(6,2) NOT NULL,
    catatan text,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT target_dosen_catatan_check CHECK (((catatan IS NULL) OR (length(catatan) <= 500))),
    CONSTRAINT target_dosen_indikator_check CHECK ((indikator ~ '^[a-z_]{2,40}$'::text)),
    CONSTRAINT target_dosen_tahun_check CHECK (((tahun >= 2000) AND (tahun <= 2100))),
    CONSTRAINT target_dosen_target_check CHECK ((target >= (0)::numeric))
);

CREATE TABLE public.tautan_ami (
    id bigint NOT NULL,
    token text DEFAULT replace((gen_random_uuid())::text, '-'::text, ''::text) NOT NULL,
    judul text NOT NULL,
    mode text DEFAULT 'ts'::text NOT NULL,
    periode text DEFAULT 'ts3'::text NOT NULL,
    akhir integer,
    ts_iku integer,
    sampai timestamp with time zone NOT NULL,
    dicabut boolean DEFAULT false NOT NULL,
    oleh text,
    dibuat_pada timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tautan_ami_akhir_check CHECK (((akhir >= 2000) AND (akhir <= 2100))),
    CONSTRAINT tautan_ami_judul_check CHECK (((length(judul) >= 3) AND (length(judul) <= 120))),
    CONSTRAINT tautan_ami_mode_check CHECK ((mode = ANY (ARRAY['kal'::text, 'ts'::text]))),
    CONSTRAINT tautan_ami_periode_check CHECK ((periode ~ '^(ts3|semua|[0-9]{4})$'::text)),
    CONSTRAINT tautan_ami_ts_iku_check CHECK (((ts_iku >= 2000) AND (ts_iku <= 2100)))
);

ALTER TABLE public.tautan_ami ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.tautan_ami_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE TABLE public.templat_email (
    kunci text NOT NULL,
    subjek text NOT NULL,
    isi text NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT templat_email_isi_check CHECK (((length(isi) >= 1) AND (length(isi) <= 10000))),
    CONSTRAINT templat_email_kunci_check CHECK ((kunci ~ '^[a-z0-9_]{2,40}$'::text)),
    CONSTRAINT templat_email_subjek_check CHECK (((length(subjek) >= 1) AND (length(subjek) <= 200)))
);

CREATE TABLE public.testimoni (
    id bigint NOT NULL,
    nama text NOT NULL,
    peran text DEFAULT 'alumni'::text NOT NULL,
    angkatan integer,
    tahun_lulus integer,
    pekerjaan text,
    kutipan text NOT NULL,
    persetujuan_tanggal date,
    persetujuan_cara text,
    tampil boolean DEFAULT true NOT NULL,
    urutan integer DEFAULT 100 NOT NULL,
    oleh text,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT testimoni_angkatan_check CHECK (((angkatan IS NULL) OR ((angkatan >= 2000) AND (angkatan <= 2100)))),
    CONSTRAINT testimoni_kutipan_check CHECK (((length(btrim(kutipan)) >= 20) AND (length(btrim(kutipan)) <= 400))),
    CONSTRAINT testimoni_nama_check CHECK (((length(btrim(nama)) >= 3) AND (length(btrim(nama)) <= 120))),
    CONSTRAINT testimoni_pekerjaan_check CHECK (((pekerjaan IS NULL) OR (length(pekerjaan) <= 160))),
    CONSTRAINT testimoni_peran_check CHECK ((peran = ANY (ARRAY['alumni'::text, 'mahasiswa'::text]))),
    CONSTRAINT testimoni_persetujuan_cara_check CHECK (((persetujuan_cara IS NULL) OR (length(persetujuan_cara) <= 200))),
    CONSTRAINT testimoni_tahun_lulus_check CHECK (((tahun_lulus IS NULL) OR ((tahun_lulus >= 2000) AND (tahun_lulus <= 2100))))
);

ALTER TABLE public.testimoni ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.testimoni_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE VIEW public.v_mahasiswa_terlibat WITH (security_invoker='true') AS
 SELECT k.tahun,
    k.kategori,
    (count(DISTINCT km.nim))::integer AS mahasiswa_unik,
    (count(*))::integer AS keterlibatan,
    (count(*) FILTER (WHERE (km.peran = 'penulis_pertama'::text)))::integer AS penulis_pertama,
    (count(*) FILTER (WHERE km.korespondensi))::integer AS korespondensi,
    (count(*) FILTER (WHERE (km.peran = 'ketua'::text)))::integer AS ketua
   FROM (public.karya_mahasiswa km
     JOIN public.karya k ON ((k.id = km.karya_id)))
  WHERE (k.status = 'terverifikasi'::text)
  GROUP BY k.tahun, k.kategori;

CREATE VIEW public.v_mitra WITH (security_invoker='true') AS
 SELECT lower(TRIM(BOTH FROM m.institusi)) AS kunci,
    min(TRIM(BOTH FROM m.institusi)) AS nama,
    max(m.negara) AS negara,
    max(m.tingkat) AS tingkat,
    (count(*) FILTER (WHERE (k.kategori = 'publikasi'::text)))::integer AS publikasi,
    (count(*) FILTER (WHERE (k.kategori = 'penelitian'::text)))::integer AS penelitian,
    (count(*) FILTER (WHERE (k.kategori = 'pkm'::text)))::integer AS pkm,
    (count(*))::integer AS total,
    min(k.tahun) AS tahun_awal,
    max(k.tahun) AS tahun_akhir
   FROM (public.karya_mitra m
     JOIN public.karya k ON ((k.id = m.karya_id)))
  WHERE (k.status = 'terverifikasi'::text)
  GROUP BY (lower(TRIM(BOTH FROM m.institusi)));

CREATE VIEW public.v_penulis_utama WITH (security_invoker='true') AS
 SELECT k.tahun,
    d.nidn,
    d.nama,
    (count(*) FILTER (WHERE (kp.peran = 'penulis_pertama'::text)))::integer AS jml_penulis_pertama,
    (count(*) FILTER (WHERE kp.korespondensi))::integer AS jml_korespondensi,
    (count(*) FILTER (WHERE ((kp.peran = 'penulis_pertama'::text) OR kp.korespondensi)))::integer AS jml_utama
   FROM ((public.karya_penulis kp
     JOIN public.karya k ON ((k.id = kp.karya_id)))
     JOIN public.dosen d ON ((d.id = kp.dosen_id)))
  WHERE ((k.status = 'terverifikasi'::text) AND (k.kategori = 'publikasi'::text))
  GROUP BY k.tahun, d.nidn, d.nama;

CREATE VIEW public.v_rekap_karya WITH (security_invoker='true') AS
 SELECT tahun,
    kategori,
    tingkat,
    sumber_dana,
    (count(*))::integer AS jumlah
   FROM public.karya
  WHERE (status = 'terverifikasi'::text)
  GROUP BY tahun, kategori, tingkat, sumber_dana;

CREATE VIEW public.v_rekap_skema WITH (security_invoker='true') AS
 SELECT k.tahun,
    k.kategori,
    s.kelompok,
    s.nama AS skema,
    (count(*))::integer AS jumlah,
    COALESCE(sum(k.besaran_dana), (0)::numeric) AS total_dana
   FROM (public.karya k
     JOIN public.ref_skema_dana s ON ((s.kode = k.skema_kode)))
  WHERE (k.status = 'terverifikasi'::text)
  GROUP BY k.tahun, k.kategori, s.kelompok, s.nama;

CREATE TABLE public.yudisium_berkas (
    kode text NOT NULL,
    label text NOT NULL,
    keterangan text DEFAULT ''::text NOT NULL,
    wajib boolean DEFAULT true NOT NULL,
    urut integer DEFAULT 100 NOT NULL,
    aktif boolean DEFAULT true NOT NULL,
    diperbarui timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT yudisium_berkas_kode_check CHECK ((kode ~ '^yud_[a-z0-9_]{2,40}$'::text)),
    CONSTRAINT yudisium_berkas_label_check CHECK (((length(btrim(label)) >= 2) AND (length(btrim(label)) <= 200)))
);

ALTER TABLE ONLY public.masukan_mahasiswa ALTER COLUMN id SET DEFAULT nextval('public.masukan_mahasiswa_id_seq'::regclass);

ALTER TABLE ONLY public.pengumuman_mahasiswa ALTER COLUMN id SET DEFAULT nextval('public.pengumuman_mahasiswa_id_seq'::regclass);

ALTER TABLE ONLY public.tanya_jawab ALTER COLUMN id SET DEFAULT nextval('public.tanya_jawab_id_seq'::regclass);

INSERT INTO public.layanan_kunci (id) VALUES (1);

INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('bop', NULL, 'Butir 9. Rata-rata dana operasional pendidikan per mahasiswa per tahun, 3 tahun terakhir, rupiah penuh.');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('kerjasama_pendidikan_3th', NULL, 'Butir 6-I. Jumlah kerja sama PENDIDIKAN 3 tahun terakhir (penelitian dan PkM dihitung otomatis dari mitra karya).');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('ndtt', NULL, 'Butir 26. Jumlah dosen tidak tetap pengampu mata kuliah di prodi.');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('sks_basic_sciences', NULL, 'Butir 19. Jumlah SKS mata kuliah basic sciences + matematika.');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('kib_3th', NULL, 'Butir 36. Jumlah karya bereputasi DTPS yang disitasi, 3 tahun terakhir (dari Scopus/Google Scholar).');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('ambang_edom', 3.00, 'Evaluasi pembelajaran (patch 68): EDOM di bawah angka ini (skala 0-4) perlu tindak lanjut. Bawaan 3,00 (pemilik 2026-11-12).');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('tinjauan_rps_mulai', 20252, 'Tinjauan RPS (patch 115): semester pertama yang ditinjau, tahun awal x 10 + 1 Ganjil / 2 Genap. Bawaan 20252 = 2025/2026 Genap (pemilik 2026-11-19).');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('rps_tanggal_ganjil', NULL, 'Tanggal dokumen RPS MK semester ganjil (TTTTBBHH, mis. 20260902), dicetak di Word; patch 117, pemilik 2026-11-19.');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('rps_tanggal_genap', NULL, 'Tanggal dokumen RPS MK semester genap (TTTTBBHH), dicetak di Word; patch 117, pemilik 2026-11-19.');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('rps_tenggat_ganjil', NULL, 'Tenggat pengajuan RPS MK semester ganjil ke Kaprodi (TTTTBBHH); patch 120, pemilik 2026-11-19.');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('rps_tenggat_genap', NULL, 'Tenggat pengajuan RPS MK semester genap ke Kaprodi (TTTTBBHH); patch 120, pemilik 2026-11-19.');
INSERT INTO public.pengaturan (kunci, nilai, keterangan) VALUES ('rps_review_hari', 14, 'Tenggat review RPS: jumlah hari sejak reviewer ditunjuk; patch 120, pemilik 2026-11-19.');

INSERT INTO public.ref_kelompok_dana (kode, nama, urutan) VALUES ('mandiri', 'Mandiri / biaya sendiri', 1);
INSERT INTO public.ref_kelompok_dana (kode, nama, urutan) VALUES ('internal', 'Hibah internal perguruan tinggi', 2);
INSERT INTO public.ref_kelompok_dana (kode, nama, urutan) VALUES ('nasional', 'Kemendiktisaintek / DPPM', 3);
INSERT INTO public.ref_kelompok_dana (kode, nama, urutan) VALUES ('pemerintah', 'Kementerian / lembaga lain / pemda', 4);
INSERT INTO public.ref_kelompok_dana (kode, nama, urutan) VALUES ('industri', 'Kerja sama industri / swasta', 5);
INSERT INTO public.ref_kelompok_dana (kode, nama, urutan) VALUES ('internasional', 'Pendanaan luar negeri', 6);

INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('mandiri', 'Mandiri / biaya sendiri', 'mandiri', 'keduanya', 'mandiri', NULL, true, 10, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pmp', 'PMP — Pemberdayaan Masyarakat Pemula', 'nasional', 'pkm', 'dalam_negeri', 'DPPM Kemendiktisaintek', true, 50, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pkm_dppm', 'PKM — Pemberdayaan Kemitraan Masyarakat', 'nasional', 'pkm', 'dalam_negeri', 'DPPM Kemendiktisaintek', true, 51, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pmm', 'PMM — Pemberdayaan Masyarakat oleh Mahasiswa', 'nasional', 'pkm', 'dalam_negeri', 'DPPM Kemendiktisaintek', true, 52, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pm_upud', 'PM-UPUD — Mitra Usaha Produk Unggulan Daerah', 'nasional', 'pkm', 'dalam_negeri', 'DPPM Kemendiktisaintek', true, 53, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pw', 'PW — Pemberdayaan Wilayah', 'nasional', 'pkm', 'dalam_negeri', 'DPPM Kemendiktisaintek', true, 54, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pdb', 'PDB — Pemberdayaan Desa Binaan', 'nasional', 'pkm', 'dalam_negeri', 'DPPM Kemendiktisaintek', true, 55, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pupr', 'Kementerian PUPR', 'pemerintah', 'keduanya', 'dalam_negeri', NULL, true, 60, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('brin', 'BRIN / RIIM', 'pemerintah', 'penelitian', 'dalam_negeri', NULL, true, 61, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pemda', 'Pemerintah daerah / Balitbangda', 'pemerintah', 'keduanya', 'dalam_negeri', NULL, true, 62, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('lpdp', 'LPDP / dana abadi', 'pemerintah', 'penelitian', 'dalam_negeri', NULL, true, 63, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('kl_lainnya', 'Kementerian / lembaga lain', 'pemerintah', 'keduanya', 'dalam_negeri', NULL, true, 69, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('industri', 'Kerja sama industri / BUMN / swasta', 'industri', 'keduanya', 'dalam_negeri', NULL, true, 70, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('ln_hibah', 'Hibah lembaga luar negeri', 'internasional', 'keduanya', 'luar_negeri', NULL, true, 80, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('ln_kerjasama', 'Kerja sama riset internasional — dana dari mitra luar negeri', 'internasional', 'keduanya', 'luar_negeri', NULL, true, 81, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('lainnya', 'Lainnya — sebutkan di keterangan', 'pemerintah', 'keduanya', 'dalam_negeri', NULL, true, 99, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('int_reguler', 'Hibah internal universitas', 'internal', 'keduanya', 'perguruan_tinggi', NULL, true, 20, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('int_kolab_ln', 'Kerja sama riset dengan PT luar negeri — dana kampus sendiri', 'internal', 'keduanya', 'perguruan_tinggi', NULL, true, 21, 'Kedua pihak mengajukan proposal dan dibiayai kampus masing-masing. Isi kolom mitra.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('int_kolab_dn', 'Kerja sama riset dengan PT dalam negeri — dana kampus sendiri', 'internal', 'keduanya', 'perguruan_tinggi', NULL, true, 22, 'Kolaborasi antar PT dalam negeri, dana dari anggaran kampus sendiri.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('ks_pt_dana_mitra', 'Kerja sama antar PT — dibiayai kampus mitra', 'internal', 'keduanya', 'dalam_negeri', NULL, true, 23, 'Dana masuk dari perguruan tinggi lain, bukan dari kampus sendiri.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('int_lainnya', 'Hibah internal lainnya — sebutkan namanya', 'internal', 'keduanya', 'perguruan_tinggi', NULL, true, 29, 'Penampung sementara. Nama skema wajib ditulis di kolom keterangan.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pdp', 'PDP — Penelitian Dosen Pemula', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 30, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('ptm', 'PTM — Penelitian Tesis Magister', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 31, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pdd', 'PDD — Penelitian Disertasi Doktor', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 32, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pmdsu', 'PMDSU', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 33, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pf', 'Penelitian Fundamental', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 34, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pkpt', 'PKPT — Penelitian Kerja Sama antar PT', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 35, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pt_prototipe', 'Penelitian Terapan — Luaran Prototipe', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 40, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pt_model', 'Penelitian Terapan — Luaran Model', 'nasional', 'penelitian', 'dalam_negeri', 'BIMA / DPPM', true, 41, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pbm_pkm', 'PBM: PKM — Pemberdayaan Kemitraan Masyarakat', 'nasional', 'pkm', 'dalam_negeri', 'BIMA / DPPM', true, 50, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pbm_pmp', 'PBM: PMP — Pemberdayaan Masyarakat Pemula', 'nasional', 'pkm', 'dalam_negeri', 'BIMA / DPPM', true, 51, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pbm_pmm', 'PBM: PMM — Pemberdayaan Masyarakat oleh Mahasiswa', 'nasional', 'pkm', 'dalam_negeri', 'BIMA / DPPM', true, 52, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pbk_kbm', 'PBK: KBM — Kewirausahaan Berbasis Mahasiswa', 'nasional', 'pkm', 'dalam_negeri', 'BIMA / DPPM', true, 53, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pbk_upud', 'PBK: PM-UPUD — Pemberdayaan Mitra Usaha Produk Unggulan Daerah', 'nasional', 'pkm', 'dalam_negeri', 'BIMA / DPPM', true, 54, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pbw_pw', 'PBW: PW — Pemberdayaan Wilayah', 'nasional', 'pkm', 'dalam_negeri', 'BIMA / DPPM', true, 55, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pbw_pdb', 'PBW: PDB — Pemberdayaan Desa Binaan', 'nasional', 'pkm', 'dalam_negeri', 'BIMA / DPPM', true, 56, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('riim_kompetisi', 'RIIM Kompetisi (BRIN x LPDP)', 'pemerintah', 'penelitian', 'dalam_negeri', 'BRIN', true, 60, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('riim_ekspedisi', 'RIIM Ekspedisi', 'pemerintah', 'penelitian', 'dalam_negeri', 'BRIN', true, 61, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('riim_kolab_int', 'RIIM Kolaborasi Internasional', 'pemerintah', 'penelitian', 'dalam_negeri', 'BRIN', true, 62, 'Pendanaan dari BRIN (dalam negeri) meski mitranya internasional.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('riim_eksplorasi', 'RIIM Eksplorasi', 'pemerintah', 'penelitian', 'dalam_negeri', 'BRIN', true, 63, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('riim_startup', 'RIIM Start-Up', 'pemerintah', 'penelitian', 'dalam_negeri', 'BRIN', true, 64, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('riim_postdoc', 'RIIM Postdoctoral', 'pemerintah', 'penelitian', 'dalam_negeri', 'BRIN', true, 65, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('riim_cofunding', 'RIIM Co-funding', 'pemerintah', 'penelitian', 'dalam_negeri', 'BRIN', true, 66, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('rispro_komersial', 'RISPRO Komersial', 'pemerintah', 'penelitian', 'dalam_negeri', 'LPDP', true, 67, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('rispro_implementatif', 'RISPRO Implementatif', 'pemerintah', 'penelitian', 'dalam_negeri', 'LPDP', true, 68, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('rispro_ki', 'RISPRO Kolaborasi Internasional (RISPRO-KI)', 'pemerintah', 'penelitian', 'dalam_negeri', 'LPDP', true, 69, 'Pendanaan dari LPDP (dalam negeri) meski mitranya internasional.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('rispro_invitasi', 'RISPRO Invitasi', 'pemerintah', 'penelitian', 'dalam_negeri', 'LPDP', true, 70, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('rispro_mandatori', 'RISPRO Mandatori / Tematik', 'pemerintah', 'penelitian', 'dalam_negeri', 'LPDP', true, 71, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('innovillage', 'Innovillage (pendanaan Telkom)', 'industri', 'pkm', 'dalam_negeri', 'PT Telkom', true, 75, NULL);
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('nas_lainnya', 'Skema BIMA/DPPM lainnya — sebutkan namanya', 'nasional', 'keduanya', 'dalam_negeri', 'BIMA / DPPM', true, 59, 'Penampung. Nama skema wajib ditulis di kolom keterangan.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('pem_lainnya', 'Kementerian/lembaga/pemda lainnya — sebutkan namanya', 'pemerintah', 'keduanya', 'dalam_negeri', NULL, true, 79, 'Penampung. Nama skema dan lembaganya wajib ditulis di kolom keterangan.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('industri_lainnya', 'Kerja sama industri/swasta lainnya — sebutkan namanya', 'industri', 'keduanya', 'dalam_negeri', NULL, true, 78, 'Penampung. Nama perusahaan wajib ditulis di kolom keterangan.');
INSERT INTO public.ref_skema_dana (kode, nama, kelompok, kategori, sumber_dana_lkps, penyelenggara, aktif, urutan, catatan) VALUES ('ln_lainnya', 'Pendanaan luar negeri lainnya — sebutkan namanya', 'internasional', 'keduanya', 'luar_negeri', NULL, true, 89, 'Penampung. Nama lembaga penyandang dana wajib ditulis di kolom keterangan.');

INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('seminar_proposal', 'naskah_ta', 'Naskah proposal TA', 'PDF naskah proposal yang akan diseminarkan.', true, 1, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('seminar_kemajuan', 'naskah_ta', 'Laporan kemajuan TA', 'PDF laporan kemajuan yang akan diseminarkan.', true, 1, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('sidang_akhir', 'naskah_ta', 'Laporan akhir TA', 'PDF laporan akhir yang akan disidangkan.', true, 1, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('sidang_akhir', 'ta_transkrip', 'Transkrip atau KHS', 'Transkrip atau KHS terakhir dari SIUP.', true, 3, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('sidang_akhir', 'ta_artikel', 'Draf artikel atau bukti publikasi', 'Draf artikel ilmiah dari TA, atau LoA/bukti terbit bila sudah dipublikasikan.', true, 4, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('penetapan_pembimbing', 'ta_terdaftar_siup', 'Bukti terdaftar TA di SIUP', 'KRS/KHS atau tangkapan layar SIUP yang menunjukkan mata kuliah Tugas Akhir sudah diambil semester ini.', true, 1, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('seminar_proposal', 'ta_bukti_bimbingan', 'Bukti bimbingan SIUP', 'Tangkapan layar atau cetakan riwayat bimbingan dari SIUP. (dinonaktifkan patch 176)', true, 2, false, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('seminar_kemajuan', 'ta_bukti_bimbingan', 'Bukti bimbingan SIUP', 'Tangkapan layar atau cetakan riwayat bimbingan dari SIUP. (dinonaktifkan patch 176)', true, 2, false, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_berkas (tahap, kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('sidang_akhir', 'ta_bukti_bimbingan', 'Bukti bimbingan SIUP', 'Tangkapan layar atau cetakan riwayat bimbingan dari SIUP. (dinonaktifkan patch 176)', true, 2, false, '2026-11-25 12:04:57.303+00');

INSERT INTO public.ta_kk_dekat (kk_a, kk_b) VALUES ('GEO', 'STR');
INSERT INTO public.ta_kk_dekat (kk_a, kk_b) VALUES ('MRK', 'STR');
INSERT INTO public.ta_kk_dekat (kk_a, kk_b) VALUES ('AIR', 'GEO');
INSERT INTO public.ta_kk_dekat (kk_a, kk_b) VALUES ('GEO', 'TRN');

INSERT INTO public.ta_rubrik (id, tahap, versi, komponen, bobot_penguji, batas_lulus, tingkat, catatan, oleh, dibuat, bobot_bimbingan, komponen_bimbingan) OVERRIDING SYSTEM VALUE VALUES (1, 'sidang_akhir', 1, '[{"kode": "materi", "bobot": 20, "label": "Penguasaan materi dan dasar teori", "uraian": ["Menguasai teori dan konteks rekayasa; mampu mengaitkannya dengan standar dan praktik.", "Menguasai sebagian besar teori yang dipakai.", "Penguasaan teori terbatas.", "Tidak menguasai dasar teori."]}, {"kode": "metode", "bobot": 25, "label": "Metodologi dan analisis", "uraian": ["Metode dan analisis benar, terverifikasi, dan dapat diulang; asumsi dan batasan dijelaskan.", "Metode dan analisis benar dengan kekurangan kecil.", "Ada kesalahan analisis atau asumsi tidak dijelaskan.", "Analisis salah atau tidak sesuai metode."]}, {"kode": "hasil", "bobot": 25, "label": "Hasil, pembahasan, dan kesimpulan", "uraian": ["Hasil menjawab semua tujuan; pembahasan kritis dan dibandingkan dengan pustaka; kesimpulan dan saran didukung data.", "Hasil menjawab tujuan; pembahasan atau saran kurang mendalam.", "Sebagian tujuan belum terjawab atau kesimpulan kurang didukung hasil.", "Hasil tidak menjawab tujuan."]}, {"kode": "penulisan", "bobot": 15, "label": "Penulisan naskah", "uraian": ["Sistematis, bahasa baku dan runtut; gambar, tabel, sitasi, dan daftar pustaka sesuai pedoman.", "Sistematis; ada kesalahan kecil bahasa atau format.", "Banyak kesalahan bahasa, format, atau sitasi.", "Tidak mengikuti pedoman; sulit dipahami."]}, {"kode": "presentasi", "bobot": 15, "label": "Presentasi dan tanya jawab", "uraian": ["Penyajian jelas dan tepat waktu; menjawab pertanyaan dengan tepat dan menguasai materi.", "Penyajian jelas; sebagian jawaban kurang tepat.", "Penyajian kurang runtut; banyak pertanyaan tidak terjawab dengan baik.", "Tidak menguasai materi."]}]', 40.00, 55.00, '{85.00,70.00,55.00,0.00}', 'Draf awal (pemilik 2026-11-25).', 'pemasangan', '2026-11-25 12:04:57.303+00', 50.00, '[{"kode": "keaktifan", "bobot": 30, "label": "Keaktifan dan keteraturan bimbingan", "uraian": ["Bimbingan teratur sesuai jadwal; selalu membawa kemajuan dan pertanyaan yang siap dibahas.", "Bimbingan cukup teratur; sesekali tanpa kemajuan berarti.", "Bimbingan jarang atau tidak teratur.", "Hampir tidak pernah bimbingan."]}, {"kode": "kemandirian", "bobot": 25, "label": "Kemandirian dan inisiatif", "uraian": ["Mencari solusi sendiri, mengusulkan langkah, dan memakai sumber dengan tepat.", "Cukup mandiri; sesekali menunggu arahan.", "Banyak bergantung pada arahan pembimbing.", "Tidak menunjukkan inisiatif."]}, {"kode": "ketepatan", "bobot": 25, "label": "Ketepatan waktu dan kemajuan sesuai rencana", "uraian": ["Tahapan selesai sesuai atau lebih cepat dari rencana.", "Terlambat sedikit dengan alasan yang wajar.", "Sering terlambat dari rencana.", "Jauh tertinggal dari rencana."]}, {"kode": "sikap", "bobot": 20, "label": "Sikap, etika, dan tindak lanjut arahan", "uraian": ["Santun, jujur secara akademik, dan menindaklanjuti semua arahan.", "Baik; sebagian kecil arahan belum ditindaklanjuti.", "Banyak arahan tidak ditindaklanjuti.", "Ada pelanggaran etika atau arahan diabaikan."]}]');
INSERT INTO public.ta_rubrik (id, tahap, versi, komponen, bobot_penguji, batas_lulus, tingkat, catatan, oleh, dibuat, bobot_bimbingan, komponen_bimbingan) OVERRIDING SYSTEM VALUE VALUES (2, 'seminar_kemajuan', 1, '[{"kode": "tindak_lanjut", "bobot": 20, "label": "Kesesuaian dengan proposal dan tindak lanjut revisi", "uraian": ["Pekerjaan sesuai rencana proposal; semua masukan seminar proposal ditindaklanjuti; perubahan dijelaskan.", "Sebagian besar sesuai rencana dan masukan ditindaklanjuti.", "Banyak bagian menyimpang dari rencana atau masukan belum ditindaklanjuti.", "Tidak sesuai rencana dan masukan diabaikan."]}, {"kode": "data", "bobot": 35, "label": "Data, pengolahan, dan analisis awal", "uraian": ["Data lengkap dan terverifikasi; pengolahan benar dan terdokumentasi; analisis awal menjawab sebagian tujuan.", "Data cukup; pengolahan benar dengan kekurangan kecil.", "Data belum lengkap atau pengolahan mengandung kesalahan.", "Data dan pengolahan belum ada atau salah."]}, {"kode": "pembahasan", "bobot": 20, "label": "Pembahasan sementara", "uraian": ["Hasil sementara ditafsirkan dengan benar dan dibandingkan dengan pustaka; langkah lanjutan jelas.", "Tafsiran benar; perbandingan dengan pustaka atau langkah lanjutan kurang.", "Tafsiran dangkal atau kurang tepat.", "Belum ada pembahasan."]}, {"kode": "penulisan", "bobot": 10, "label": "Penulisan naskah", "uraian": ["Sistematis, bahasa baku dan runtut; gambar, tabel, sitasi, dan daftar pustaka sesuai pedoman.", "Sistematis; ada kesalahan kecil bahasa atau format.", "Banyak kesalahan bahasa, format, atau sitasi.", "Tidak mengikuti pedoman; sulit dipahami."]}, {"kode": "presentasi", "bobot": 15, "label": "Presentasi dan tanya jawab", "uraian": ["Penyajian jelas dan tepat waktu; menjawab pertanyaan dengan tepat dan menguasai materi.", "Penyajian jelas; sebagian jawaban kurang tepat.", "Penyajian kurang runtut; banyak pertanyaan tidak terjawab dengan baik.", "Tidak menguasai materi."]}]', 40.00, 55.00, '{85.00,70.00,55.00,0.00}', 'Draf awal (pemilik 2026-11-25).', 'pemasangan', '2026-11-25 12:04:57.303+00', 0.00, '[]');
INSERT INTO public.ta_rubrik (id, tahap, versi, komponen, bobot_penguji, batas_lulus, tingkat, catatan, oleh, dibuat, bobot_bimbingan, komponen_bimbingan) OVERRIDING SYSTEM VALUE VALUES (3, 'seminar_proposal', 1, '[{"kode": "masalah", "bobot": 20, "label": "Latar belakang dan rumusan masalah", "uraian": ["Masalah jelas, penting, dan didukung data; rumusan, tujuan, dan batasan tegas serta saling sesuai.", "Masalah dan tujuan jelas; dukungan data atau batasan masih kurang di beberapa bagian.", "Masalah cukup dipahami, tetapi rumusan, tujuan, atau batasan kurang tegas atau kurang sesuai.", "Masalah tidak jelas atau rumusan tidak sesuai dengan tujuan."]}, {"kode": "pustaka", "bobot": 20, "label": "Tinjauan pustaka", "uraian": ["Pustaka mutakhir dan relevan (jurnal, standar); teori dan penelitian terdahulu dirangkum kritis menjadi dasar metode.", "Pustaka relevan dan cukup; rangkuman lebih banyak memaparkan daripada membandingkan.", "Pustaka terbatas atau kurang mutakhir; kaitannya dengan masalah lemah.", "Pustaka sangat kurang atau tidak relevan."]}, {"kode": "metode", "bobot": 30, "label": "Metodologi dan rencana kerja", "uraian": ["Metode tepat dan terperinci (data, alat, langkah analisis); rencana kerja dan jadwal realistis.", "Metode tepat; beberapa langkah atau kebutuhan data belum terperinci.", "Metode kurang sesuai atau banyak langkah belum jelas; jadwal kurang realistis.", "Metode tidak sesuai dengan tujuan atau tidak dapat dijalankan."]}, {"kode": "penulisan", "bobot": 15, "label": "Penulisan naskah", "uraian": ["Sistematis, bahasa baku dan runtut; gambar, tabel, sitasi, dan daftar pustaka sesuai pedoman.", "Sistematis; ada kesalahan kecil bahasa atau format.", "Banyak kesalahan bahasa, format, atau sitasi.", "Tidak mengikuti pedoman; sulit dipahami."]}, {"kode": "presentasi", "bobot": 15, "label": "Presentasi dan tanya jawab", "uraian": ["Penyajian jelas dan tepat waktu; menjawab pertanyaan dengan tepat dan menguasai materi.", "Penyajian jelas; sebagian jawaban kurang tepat.", "Penyajian kurang runtut; banyak pertanyaan tidak terjawab dengan baik.", "Tidak menguasai materi."]}]', 40.00, 55.00, '{85.00,70.00,55.00,0.00}', 'Draf awal (pemilik 2026-11-25).', 'pemasangan', '2026-11-25 12:04:57.303+00', 0.00, '[]');

INSERT INTO public.ta_syarat_bimbingan (tahap, minimal, oleh, diperbarui) VALUES ('seminar_proposal', 4, NULL, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_syarat_bimbingan (tahap, minimal, oleh, diperbarui) VALUES ('seminar_kemajuan', 4, NULL, '2026-11-25 12:04:57.303+00');
INSERT INTO public.ta_syarat_bimbingan (tahap, minimal, oleh, diperbarui) VALUES ('sidang_akhir', 4, NULL, '2026-11-25 12:04:57.303+00');

INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_form_pendaftaran', 'Form pendaftaran yudisium', '', true, 1, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_laporan_ta', 'Laporan Tugas Akhir', '', true, 2, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_transkrip', 'Transkrip', '', true, 3, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_pem', 'PEM', '', true, 4, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_toefl', 'TOEFL', '', true, 5, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_bebas_pustaka', 'SKET bebas pustaka', '', true, 6, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_repository', 'SKET repository', '', true, 7, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_bebas_alat_lab', 'Bebas pinjam alat laboratorium', '', true, 8, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_foto_warna', 'Foto warna', '', true, 9, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_foto_bw', 'Foto BW', '', true, 10, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_bebas_fasilitas', 'Bebas pinjam fasilitas universitas', '', true, 11, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_bebas_plagiasi', 'Bebas plagiasi', '', true, 12, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_form_fpi', 'Form FPI pengumpulan draft publikasi', '', true, 13, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_artikel', 'Artikel ilmiah', '', true, 14, true, '2026-11-25 12:04:57.303+00');
INSERT INTO public.yudisium_berkas (kode, label, keterangan, wajib, urut, aktif, diperbarui) VALUES ('yud_bukti_tambahan', 'Bukti tambahan', '', false, 99, true, '2026-11-25 12:04:57.303+00');

SELECT pg_catalog.setval('public.ajuan_bkd_id_seq', 1, false);

SELECT pg_catalog.setval('public.ajuan_hapus_id_seq', 1, false);

SELECT pg_catalog.setval('public.ajuan_prestasi_id_seq', 1, false);

SELECT pg_catalog.setval('public.ajuan_ubah_id_seq', 1, false);

SELECT pg_catalog.setval('public.ami_temuan_id_seq', 1, false);

SELECT pg_catalog.setval('public.butir_bukti_id_seq', 1, false);

SELECT pg_catalog.setval('public.cpl_berkas_id_seq', 1, false);

SELECT pg_catalog.setval('public.cpl_kelas_id_seq', 1, false);

SELECT pg_catalog.setval('public.cpl_ringkasan_id_seq', 1, false);

SELECT pg_catalog.setval('public.dokumen_id_seq', 1, false);

SELECT pg_catalog.setval('public.dosen_berhalangan_id_seq', 1, false);

SELECT pg_catalog.setval('public.dosen_berhalangan_rentang_id_seq', 1, false);

SELECT pg_catalog.setval('public.dosen_berhalangan_tgl_id_seq', 1, false);

SELECT pg_catalog.setval('public.evaluasi_mk_id_seq', 1, false);

SELECT pg_catalog.setval('public.evaluasi_tindak_id_seq', 1, false);

SELECT pg_catalog.setval('public.hibah_panggilan_id_seq', 1, false);

SELECT pg_catalog.setval('public.insentif_pengajuan_id_seq', 1, false);

SELECT pg_catalog.setval('public.insentif_publikasi_id_seq', 1, false);

SELECT pg_catalog.setval('public.jadwal_slot_id_seq', 1, false);

SELECT pg_catalog.setval('public.jadwal_ta_id_seq', 1, false);

SELECT pg_catalog.setval('public.jejak_id_seq', 1, false);

SELECT pg_catalog.setval('public.kabar_kegiatan_id_seq', 1, false);

SELECT pg_catalog.setval('public.kalender_akademik_id_seq', 1, false);

SELECT pg_catalog.setval('public.karya_bukti_id_seq', 1, false);

SELECT pg_catalog.setval('public.kegiatan_id_seq', 1, false);

SELECT pg_catalog.setval('public.kelas_kuliah_id_seq', 1, false);

SELECT pg_catalog.setval('public.koordinator_id_seq', 1, false);

SELECT pg_catalog.setval('public.kp_kuota_id_seq', 1, false);

SELECT pg_catalog.setval('public.kp_tolak_instansi_id_seq', 1, false);

SELECT pg_catalog.setval('public.laboratorium_id_seq', 1, false);

SELECT pg_catalog.setval('public.led_tim_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_bimbingan_utama_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_bkd_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_bukti_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_dokumen_k3l_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_fasilitas_k3l_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_kepuasan_pengguna_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_kerjasama_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_keuangan_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_kohort_lulusan_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_luaran_mahasiswa_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_mahasiswa_angkatan_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_mahasiswa_ta_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_penggunaan_dana_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_peta_jalan_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_prasarana_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_prestasi_mahasiswa_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_prodi_upps_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_publikasi_mahasiswa_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_sarana_standar_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_spmi_ppepp_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_target_kinerja_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_tendik_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_tracer_lulusan_id_seq', 1, false);

SELECT pg_catalog.setval('public.lkps_vmts_id_seq', 1, false);

SELECT pg_catalog.setval('public.masukan_mahasiswa_id_seq', 1, false);

SELECT pg_catalog.setval('public.mhs_email_alt_riwayat_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_padanan_sah_log_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_rps_pengesahan_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_rps_review_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_rps_riwayat_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_rps_tinjauan_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_rps_tinjauan_log_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_rps_ttd_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_silabus_log_id_seq', 1, false);

SELECT pg_catalog.setval('public.mk_struktur_riwayat_id_seq', 1, false);

SELECT pg_catalog.setval('public.pengajuan_berkas_id_seq', 1, false);

SELECT pg_catalog.setval('public.pengajuan_mahasiswa_id_seq', 1, false);

SELECT pg_catalog.setval('public.pengajuan_riwayat_id_seq', 1, false);

SELECT pg_catalog.setval('public.pengelola_prodi_id_seq', 1, false);

SELECT pg_catalog.setval('public.pengumuman_mahasiswa_id_seq', 1, false);

SELECT pg_catalog.setval('public.peringatan_keamanan_id_seq', 1, false);

SELECT pg_catalog.setval('public.portofolio_berkas_id_seq', 1, false);

SELECT pg_catalog.setval('public.potret_skor_id_seq', 1, false);

SELECT pg_catalog.setval('public.rapat_id_seq', 1, false);

SELECT pg_catalog.setval('public.rapat_peserta_id_seq', 1, false);

SELECT pg_catalog.setval('public.rapat_tindak_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_bidang_keahlian_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_cpl_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_cpl_korelasi_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_mata_kuliah_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_mk_cpl_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_mk_padanan_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_profil_lulusan_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_tema_peta_jalan_id_seq', 1, false);

SELECT pg_catalog.setval('public.ref_topik_keahlian_id_seq', 1, false);

SELECT pg_catalog.setval('public.spmi_standar_id_seq', 1, false);

SELECT pg_catalog.setval('public.spmi_standar_revisi_id_seq', 1, false);

SELECT pg_catalog.setval('public.survei_id_seq', 1, false);

SELECT pg_catalog.setval('public.survei_jawaban_id_seq', 1, false);

SELECT pg_catalog.setval('public.ta_bimbingan_id_seq', 1, false);

SELECT pg_catalog.setval('public.ta_kecuali_urutan_id_seq', 1, false);

SELECT pg_catalog.setval('public.ta_kuota_id_seq', 1, false);

SELECT pg_catalog.setval('public.ta_nilai_id_seq', 1, false);

SELECT pg_catalog.setval('public.ta_rubrik_id_seq', 3, true);

SELECT pg_catalog.setval('public.tanya_jawab_id_seq', 1, false);

SELECT pg_catalog.setval('public.tautan_ami_id_seq', 1, false);

SELECT pg_catalog.setval('public.testimoni_id_seq', 1, false);

ALTER TABLE ONLY public.ajuan_bkd
    ADD CONSTRAINT ajuan_bkd_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ajuan_hapus
    ADD CONSTRAINT ajuan_hapus_karya_id_key UNIQUE (karya_id);

ALTER TABLE ONLY public.ajuan_hapus
    ADD CONSTRAINT ajuan_hapus_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ajuan_prestasi
    ADD CONSTRAINT ajuan_prestasi_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ajuan_ubah
    ADD CONSTRAINT ajuan_ubah_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ami_temuan
    ADD CONSTRAINT ami_temuan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.berhalangan_konfirmasi
    ADD CONSTRAINT berhalangan_konfirmasi_pkey PRIMARY KEY (dosen_id, tahun_akademik, semester);

ALTER TABLE ONLY public.butir_bukti
    ADD CONSTRAINT butir_bukti_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.cpl_berkas
    ADD CONSTRAINT cpl_berkas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.cpl_kelas
    ADD CONSTRAINT cpl_kelas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.cpl_kelas
    ADD CONSTRAINT cpl_kelas_tahun_akademik_semester_kode_mk_kelas_key UNIQUE (tahun_akademik, semester, kode_mk, kelas);

ALTER TABLE ONLY public.cpl_ringkasan
    ADD CONSTRAINT cpl_ringkasan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dokumen
    ADD CONSTRAINT dokumen_jenis_tahun_judul_key UNIQUE (jenis, tahun, judul);

ALTER TABLE ONLY public.dokumen
    ADD CONSTRAINT dokumen_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dosen_ampu_ts
    ADD CONSTRAINT dosen_ampu_ts_pkey PRIMARY KEY (dosen_id, tahun_akademik);

ALTER TABLE ONLY public.dosen_berhalangan
    ADD CONSTRAINT dosen_berhalangan_dosen_id_tahun_akademik_semester_hari_slo_key UNIQUE (dosen_id, tahun_akademik, semester, hari, slot_id);

ALTER TABLE ONLY public.dosen_berhalangan
    ADD CONSTRAINT dosen_berhalangan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dosen_berhalangan_rentang
    ADD CONSTRAINT dosen_berhalangan_rentang_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dosen_berhalangan_tgl
    ADD CONSTRAINT dosen_berhalangan_tgl_pkey PRIMARY KEY (id);

ALTER TABLE public.dosen
    ADD CONSTRAINT dosen_dtps_tetap_check CHECK (((NOT dtps) OR (kategori = 'tetap'::text))) NOT VALID;

ALTER TABLE ONLY public.dosen
    ADD CONSTRAINT dosen_email_key UNIQUE (email);

ALTER TABLE public.dosen
    ADD CONSTRAINT dosen_email_wajib_check CHECK (((email IS NOT NULL) OR ((peran <> 'admin'::text) AND (NOT COALESCE(dtps, false))))) NOT VALID;

ALTER TABLE ONLY public.dosen
    ADD CONSTRAINT dosen_nidn_key UNIQUE (nidn);

ALTER TABLE ONLY public.dosen
    ADD CONSTRAINT dosen_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.evaluasi_mk
    ADD CONSTRAINT evaluasi_mk_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.evaluasi_mk
    ADD CONSTRAINT evaluasi_mk_tahun_akademik_semester_kode_mk_dosen_id_key UNIQUE (tahun_akademik, semester, kode_mk, dosen_id);

ALTER TABLE ONLY public.evaluasi_tindak
    ADD CONSTRAINT evaluasi_tindak_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.hari_libur
    ADD CONSTRAINT hari_libur_pkey PRIMARY KEY (tanggal);

ALTER TABLE ONLY public.hibah_ajuan
    ADD CONSTRAINT hibah_ajuan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.hibah_panggilan
    ADD CONSTRAINT hibah_panggilan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.hibah_tim
    ADD CONSTRAINT hibah_tim_pkey PRIMARY KEY (ajuan_id, dosen_id);

ALTER TABLE ONLY public.insentif_pengajuan
    ADD CONSTRAINT insentif_pengajuan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.insentif_publikasi
    ADD CONSTRAINT insentif_publikasi_karya_id_key UNIQUE (karya_id);

ALTER TABLE ONLY public.insentif_publikasi
    ADD CONSTRAINT insentif_publikasi_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.jadwal_hari
    ADD CONSTRAINT jadwal_hari_pkey PRIMARY KEY (hari);

ALTER TABLE ONLY public.jadwal_kuliah
    ADD CONSTRAINT jadwal_kuliah_pkey PRIMARY KEY (kelas_id);

ALTER TABLE ONLY public.jadwal_kuliah_sah
    ADD CONSTRAINT jadwal_kuliah_sah_pkey PRIMARY KEY (tahun_akademik, semester);

ALTER TABLE ONLY public.jadwal_slot
    ADD CONSTRAINT jadwal_slot_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.jadwal_ta
    ADD CONSTRAINT jadwal_ta_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.jejak
    ADD CONSTRAINT jejak_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kabar_kegiatan
    ADD CONSTRAINT kabar_kegiatan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kalender_akademik
    ADD CONSTRAINT kalender_akademik_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.karya_bukti
    ADD CONSTRAINT karya_bukti_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.karya_mahasiswa
    ADD CONSTRAINT karya_mahasiswa_karya_id_nim_key UNIQUE (karya_id, nim);

ALTER TABLE ONLY public.karya_mahasiswa
    ADD CONSTRAINT karya_mahasiswa_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.karya_mitra
    ADD CONSTRAINT karya_mitra_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.karya_penulis
    ADD CONSTRAINT karya_penulis_pkey PRIMARY KEY (karya_id, dosen_id);

ALTER TABLE ONLY public.karya
    ADD CONSTRAINT karya_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.karya_sitasi
    ADD CONSTRAINT karya_sitasi_pkey PRIMARY KEY (karya_id, tahun);

ALTER TABLE ONLY public.kegiatan_dosen
    ADD CONSTRAINT kegiatan_dosen_pkey PRIMARY KEY (kegiatan_id, dosen_id);

ALTER TABLE ONLY public.kegiatan
    ADD CONSTRAINT kegiatan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kelas_dosen
    ADD CONSTRAINT kelas_dosen_pkey PRIMARY KEY (kelas_id, dosen_id);

ALTER TABLE ONLY public.kelas_kuliah
    ADD CONSTRAINT kelas_kuliah_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kelas_kuliah
    ADD CONSTRAINT kelas_kuliah_tahun_akademik_semester_kurikulum_kode_mk_kela_key UNIQUE (tahun_akademik, semester, kurikulum, kode_mk, kelas);

ALTER TABLE ONLY public.koordinator
    ADD CONSTRAINT koordinator_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kp_instansi_keputusan
    ADD CONSTRAINT kp_instansi_keputusan_pkey PRIMARY KEY (kunci);

ALTER TABLE ONLY public.kp_kuota
    ADD CONSTRAINT kp_kuota_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kp_tolak_instansi
    ADD CONSTRAINT kp_tolak_instansi_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kunjungan_publik
    ADD CONSTRAINT kunjungan_publik_pkey PRIMARY KEY (tanggal, halaman, rujukan, peristiwa);

ALTER TABLE ONLY public.laboratorium
    ADD CONSTRAINT laboratorium_nama_key UNIQUE (nama);

ALTER TABLE ONLY public.laboratorium
    ADD CONSTRAINT laboratorium_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.layanan_kunci
    ADD CONSTRAINT layanan_kunci_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.led_narasi
    ADD CONSTRAINT led_narasi_pkey PRIMARY KEY (kunci);

ALTER TABLE ONLY public.led_penugasan
    ADD CONSTRAINT led_penugasan_pkey PRIMARY KEY (kelompok);

ALTER TABLE ONLY public.led_tim
    ADD CONSTRAINT led_tim_dosen_id_key UNIQUE (dosen_id);

ALTER TABLE ONLY public.led_tim
    ADD CONSTRAINT led_tim_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_bimbingan_utama
    ADD CONSTRAINT lkps_bimbingan_utama_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_bimbingan_utama
    ADD CONSTRAINT lkps_bimbingan_utama_unik UNIQUE (nidn, tahun_akademik);

ALTER TABLE ONLY public.lkps_bkd
    ADD CONSTRAINT lkps_bkd_nidn_tahun_akademik_semester_key UNIQUE (nidn, tahun_akademik, semester);

ALTER TABLE ONLY public.lkps_bkd
    ADD CONSTRAINT lkps_bkd_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_bukti
    ADD CONSTRAINT lkps_bukti_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_dokumen_k3l
    ADD CONSTRAINT lkps_dokumen_k3l_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_fasilitas_k3l
    ADD CONSTRAINT lkps_fasilitas_k3l_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_kepuasan_pengguna
    ADD CONSTRAINT lkps_kepuasan_pengguna_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_kepuasan_pengguna
    ADD CONSTRAINT lkps_kepuasan_pengguna_tahun_akademik_aspek_key UNIQUE (tahun_akademik, aspek);

ALTER TABLE ONLY public.lkps_kerjasama
    ADD CONSTRAINT lkps_kerjasama_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_keuangan
    ADD CONSTRAINT lkps_keuangan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_keuangan
    ADD CONSTRAINT lkps_keuangan_unik UNIQUE (tahun_akademik, pos);

ALTER TABLE ONLY public.lkps_kohort_lulusan
    ADD CONSTRAINT lkps_kohort_lulusan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_kohort_lulusan
    ADD CONSTRAINT lkps_kohort_lulusan_tahun_masuk_key UNIQUE (tahun_masuk);

ALTER TABLE ONLY public.lkps_luaran_mahasiswa
    ADD CONSTRAINT lkps_luaran_mahasiswa_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_mahasiswa_angkatan
    ADD CONSTRAINT lkps_mahasiswa_angkatan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_mahasiswa_angkatan
    ADD CONSTRAINT lkps_mahasiswa_angkatan_tahun_akademik_key UNIQUE (tahun_akademik);

ALTER TABLE ONLY public.lkps_mahasiswa_ta
    ADD CONSTRAINT lkps_mahasiswa_ta_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_mahasiswa_ta
    ADD CONSTRAINT lkps_mahasiswa_ta_tahun_akademik_key UNIQUE (tahun_akademik);

ALTER TABLE ONLY public.lkps_penggunaan_dana
    ADD CONSTRAINT lkps_penggunaan_dana_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_penggunaan_dana
    ADD CONSTRAINT lkps_penggunaan_dana_tahun_akademik_jenis_key UNIQUE (tahun_akademik, jenis);

ALTER TABLE ONLY public.lkps_peta_jalan
    ADD CONSTRAINT lkps_peta_jalan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_prasarana
    ADD CONSTRAINT lkps_prasarana_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_prestasi_mahasiswa
    ADD CONSTRAINT lkps_prestasi_mahasiswa_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_prodi_upps
    ADD CONSTRAINT lkps_prodi_upps_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_publikasi_mahasiswa
    ADD CONSTRAINT lkps_publikasi_mahasiswa_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_sarana_standar
    ADD CONSTRAINT lkps_sarana_standar_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_spmi_ppepp
    ADD CONSTRAINT lkps_spmi_ppepp_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_spmi_ppepp
    ADD CONSTRAINT lkps_spmi_ppepp_tahap_key UNIQUE (tahap);

ALTER TABLE ONLY public.lkps_target_kinerja
    ADD CONSTRAINT lkps_target_kinerja_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_tendik
    ADD CONSTRAINT lkps_tendik_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_tracer_lulusan
    ADD CONSTRAINT lkps_tracer_lulusan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lkps_tracer_lulusan
    ADD CONSTRAINT lkps_tracer_lulusan_tahun_lulus_key UNIQUE (tahun_lulus);

ALTER TABLE ONLY public.lkps_vmts
    ADD CONSTRAINT lkps_vmts_jenis_key UNIQUE (jenis);

ALTER TABLE ONLY public.lkps_vmts
    ADD CONSTRAINT lkps_vmts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.masukan_mahasiswa
    ADD CONSTRAINT masukan_mahasiswa_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mhs_email_alt
    ADD CONSTRAINT mhs_email_alt_calon_hash_key UNIQUE (calon_hash);

ALTER TABLE ONLY public.mhs_email_alt
    ADD CONSTRAINT mhs_email_alt_pkey PRIMARY KEY (nim);

ALTER TABLE ONLY public.mhs_email_alt_riwayat
    ADD CONSTRAINT mhs_email_alt_riwayat_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_padanan_sah_log
    ADD CONSTRAINT mk_padanan_sah_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_padanan_sah
    ADD CONSTRAINT mk_padanan_sah_pkey PRIMARY KEY (kurikulum_lama, kurikulum_baru);

ALTER TABLE ONLY public.mk_rps_pengesahan
    ADD CONSTRAINT mk_rps_pengesahan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_rps
    ADD CONSTRAINT mk_rps_pkey PRIMARY KEY (kurikulum, kode_mk);

ALTER TABLE ONLY public.mk_rps_review
    ADD CONSTRAINT mk_rps_review_kurikulum_kode_mk_reviewer_id_key UNIQUE (kurikulum, kode_mk, reviewer_id);

ALTER TABLE ONLY public.mk_rps_review
    ADD CONSTRAINT mk_rps_review_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_rps_riwayat
    ADD CONSTRAINT mk_rps_riwayat_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_rps_tinjauan
    ADD CONSTRAINT mk_rps_tinjauan_kurikulum_kode_mk_tahun_akademik_semester_key UNIQUE (kurikulum, kode_mk, tahun_akademik, semester);

ALTER TABLE ONLY public.mk_rps_tinjauan_log
    ADD CONSTRAINT mk_rps_tinjauan_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_rps_tinjauan
    ADD CONSTRAINT mk_rps_tinjauan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_rps_ttd
    ADD CONSTRAINT mk_rps_ttd_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_silabus_log
    ADD CONSTRAINT mk_silabus_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mk_silabus
    ADD CONSTRAINT mk_silabus_pkey PRIMARY KEY (kurikulum, kode_mk);

ALTER TABLE ONLY public.mk_struktur
    ADD CONSTRAINT mk_struktur_pkey PRIMARY KEY (kurikulum, kode_mk);

ALTER TABLE ONLY public.mk_struktur_riwayat
    ADD CONSTRAINT mk_struktur_riwayat_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pemakaian_halaman
    ADD CONSTRAINT pemakaian_halaman_pkey PRIMARY KEY (tanggal, halaman, dosen_id);

ALTER TABLE ONLY public.pengajuan_berkas
    ADD CONSTRAINT pengajuan_berkas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pengajuan_mahasiswa
    ADD CONSTRAINT pengajuan_mahasiswa_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pengajuan_mahasiswa
    ADD CONSTRAINT pengajuan_mahasiswa_token_hash_key UNIQUE (token_hash);

ALTER TABLE ONLY public.pengajuan_riwayat
    ADD CONSTRAINT pengajuan_riwayat_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pengaturan
    ADD CONSTRAINT pengaturan_pkey PRIMARY KEY (kunci);

ALTER TABLE ONLY public.pengelola_prodi
    ADD CONSTRAINT pengelola_prodi_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pengumuman_mahasiswa
    ADD CONSTRAINT pengumuman_mahasiswa_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.peringatan_keamanan
    ADD CONSTRAINT peringatan_keamanan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.portofolio_berkas
    ADD CONSTRAINT portofolio_berkas_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.potret_skor
    ADD CONSTRAINT potret_skor_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.profil_prodi
    ADD CONSTRAINT profil_prodi_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.rapat_peserta
    ADD CONSTRAINT rapat_peserta_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.rapat
    ADD CONSTRAINT rapat_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.rapat_tindak
    ADD CONSTRAINT rapat_tindak_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.rapat
    ADD CONSTRAINT rapat_token_hadir_key UNIQUE (token_hadir);

ALTER TABLE ONLY public.ref_bidang_keahlian
    ADD CONSTRAINT ref_bidang_keahlian_kode_key UNIQUE (kode);

ALTER TABLE ONLY public.ref_bidang_keahlian
    ADD CONSTRAINT ref_bidang_keahlian_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_cpl_korelasi
    ADD CONSTRAINT ref_cpl_korelasi_kurikulum_asal_cpl_asal_kurikulum_tujuan_c_key UNIQUE (kurikulum_asal, cpl_asal, kurikulum_tujuan, cpl_tujuan);

ALTER TABLE ONLY public.ref_cpl_korelasi
    ADD CONSTRAINT ref_cpl_korelasi_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_cpl
    ADD CONSTRAINT ref_cpl_kurikulum_kode_key UNIQUE (kurikulum, kode);

ALTER TABLE ONLY public.ref_cpl
    ADD CONSTRAINT ref_cpl_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_kata_visi
    ADD CONSTRAINT ref_kata_visi_pkey PRIMARY KEY (kata);

ALTER TABLE ONLY public.ref_kategori_publikasi
    ADD CONSTRAINT ref_kategori_publikasi_pkey PRIMARY KEY (kode);

ALTER TABLE ONLY public.ref_kelompok_dana
    ADD CONSTRAINT ref_kelompok_dana_pkey PRIMARY KEY (kode);

ALTER TABLE ONLY public.ref_mata_kuliah
    ADD CONSTRAINT ref_mata_kuliah_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_mk_cpl
    ADD CONSTRAINT ref_mk_cpl_kurikulum_kode_mk_cpl_key UNIQUE (kurikulum, kode_mk, cpl);

ALTER TABLE ONLY public.ref_mk_cpl
    ADD CONSTRAINT ref_mk_cpl_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_mk_padanan
    ADD CONSTRAINT ref_mk_padanan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_profil_lulusan
    ADD CONSTRAINT ref_profil_lulusan_kurikulum_kode_key UNIQUE (kurikulum, kode);

ALTER TABLE ONLY public.ref_profil_lulusan
    ADD CONSTRAINT ref_profil_lulusan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_skema_dana
    ADD CONSTRAINT ref_skema_dana_pkey PRIMARY KEY (kode);

ALTER TABLE ONLY public.ref_tema_peta_jalan
    ADD CONSTRAINT ref_tema_peta_jalan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ref_topik_keahlian
    ADD CONSTRAINT ref_topik_keahlian_kode_key UNIQUE (kode);

ALTER TABLE ONLY public.ref_topik_keahlian
    ADD CONSTRAINT ref_topik_keahlian_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.spmi_capaian
    ADD CONSTRAINT spmi_capaian_pkey PRIMARY KEY (standar_id, tahun_ts);

ALTER TABLE ONLY public.spmi_standar
    ADD CONSTRAINT spmi_standar_kode_key UNIQUE (kode);

ALTER TABLE ONLY public.spmi_standar
    ADD CONSTRAINT spmi_standar_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.spmi_standar_revisi
    ADD CONSTRAINT spmi_standar_revisi_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.status_sistem
    ADD CONSTRAINT status_sistem_pkey PRIMARY KEY (kunci);

ALTER TABLE ONLY public.survei_jawaban
    ADD CONSTRAINT survei_jawaban_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.survei_jawaban
    ADD CONSTRAINT survei_jawaban_survei_id_klien_key UNIQUE (survei_id, klien);

ALTER TABLE ONLY public.survei
    ADD CONSTRAINT survei_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.survei
    ADD CONSTRAINT survei_token_key UNIQUE (token);

ALTER TABLE ONLY public.ta_arsip
    ADD CONSTRAINT ta_arsip_pkey PRIMARY KEY (nim);

ALTER TABLE ONLY public.ta_berkas
    ADD CONSTRAINT ta_berkas_pkey PRIMARY KEY (tahap, kode);

ALTER TABLE ONLY public.ta_bimbingan
    ADD CONSTRAINT ta_bimbingan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ta_kecuali_urutan
    ADD CONSTRAINT ta_kecuali_urutan_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ta_kk_dekat
    ADD CONSTRAINT ta_kk_dekat_pkey PRIMARY KEY (kk_a, kk_b);

ALTER TABLE ONLY public.ta_kuota
    ADD CONSTRAINT ta_kuota_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ta_nilai
    ADD CONSTRAINT ta_nilai_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ta_rubrik
    ADD CONSTRAINT ta_rubrik_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ta_rubrik
    ADD CONSTRAINT ta_rubrik_tahap_versi_key UNIQUE (tahap, versi);

ALTER TABLE ONLY public.ta_syarat_bimbingan
    ADD CONSTRAINT ta_syarat_bimbingan_pkey PRIMARY KEY (tahap);

ALTER TABLE ONLY public.tanya_jawab
    ADD CONSTRAINT tanya_jawab_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.target_baku
    ADD CONSTRAINT target_baku_pkey PRIMARY KEY (tahun, jabatan, indikator);

ALTER TABLE ONLY public.target_dosen
    ADD CONSTRAINT target_dosen_pkey PRIMARY KEY (tahun, dosen_id, indikator);

ALTER TABLE ONLY public.tautan_ami
    ADD CONSTRAINT tautan_ami_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tautan_ami
    ADD CONSTRAINT tautan_ami_token_key UNIQUE (token);

ALTER TABLE ONLY public.templat_email
    ADD CONSTRAINT templat_email_pkey PRIMARY KEY (kunci);

ALTER TABLE ONLY public.testimoni
    ADD CONSTRAINT testimoni_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.yudisium_berkas
    ADD CONSTRAINT yudisium_berkas_pkey PRIMARY KEY (kode);

CREATE UNIQUE INDEX ajuan_bkd_menunggu ON public.ajuan_bkd USING btree (bkd_id) WHERE (status = 'menunggu'::text);

CREATE UNIQUE INDEX ajuan_prestasi_menunggu ON public.ajuan_prestasi USING btree (prestasi_id) WHERE (status = 'menunggu'::text);

CREATE UNIQUE INDEX ajuan_ubah_karya_menunggu ON public.ajuan_ubah USING btree (karya_id) WHERE ((status = 'menunggu'::text) AND (karya_id IS NOT NULL));

CREATE UNIQUE INDEX ajuan_ubah_profil_menunggu ON public.ajuan_ubah USING btree (dosen_id) WHERE ((status = 'menunggu'::text) AND (dosen_id IS NOT NULL));

CREATE INDEX butir_bukti_butir ON public.butir_bukti USING btree (butir);

CREATE INDEX butir_bukti_sha256 ON public.butir_bukti USING btree (sha256) WHERE (sha256 IS NOT NULL);

CREATE UNIQUE INDEX butir_bukti_unik_dokumen ON public.butir_bukti USING btree (butir, COALESCE((unsur)::integer, 0), dokumen_id) WHERE (dokumen_id IS NOT NULL);

CREATE UNIQUE INDEX butir_bukti_unik_jenis ON public.butir_bukti USING btree (butir, COALESCE((unsur)::integer, 0), jenis_dokumen) WHERE (jenis_dokumen IS NOT NULL);

CREATE INDEX cpl_berkas_kelas ON public.cpl_berkas USING btree (kelas_id, diunggah DESC);

CREATE INDEX dokumen_sha256 ON public.dokumen USING btree (sha256) WHERE (sha256 IS NOT NULL);

CREATE INDEX dosen_berhalangan_rentang_tanggal ON public.dosen_berhalangan_rentang USING btree (selesai, mulai);

CREATE UNIQUE INDEX dosen_berhalangan_tgl_unik ON public.dosen_berhalangan_tgl USING btree (dosen_id, tanggal, COALESCE(slot_id, (0)::bigint));

CREATE UNIQUE INDEX dosen_email_alternatif_unik ON public.dosen USING btree (lower(email_alternatif)) WHERE (email_alternatif IS NOT NULL);

CREATE INDEX evaluasi_mk_dosen ON public.evaluasi_mk USING btree (dosen_id);

CREATE INDEX evaluasi_tindak_evaluasi ON public.evaluasi_tindak USING btree (evaluasi_id);

CREATE INDEX evaluasi_tindak_pj ON public.evaluasi_tindak USING btree (pj_id);

CREATE INDEX hibah_ajuan_status ON public.hibah_ajuan USING btree (status, tahun_usulan);

CREATE INDEX hibah_tim_dosen ON public.hibah_tim USING btree (dosen_id);

CREATE UNIQUE INDEX hibah_tim_satu_ketua ON public.hibah_tim USING btree (ajuan_id) WHERE (peran = 'ketua'::text);

CREATE INDEX insentif_publikasi_pengajuan ON public.insentif_publikasi USING btree (pengajuan_id);

CREATE INDEX insentif_publikasi_pengklaim ON public.insentif_publikasi USING btree (pengklaim_id);

CREATE UNIQUE INDEX jadwal_ta_pengajuan ON public.jadwal_ta USING btree (pengajuan_id);

CREATE INDEX jadwal_ta_tanggal ON public.jadwal_ta USING btree (tanggal);

CREATE INDEX jejak_oleh ON public.jejak USING btree (oleh);

CREATE INDEX jejak_tabel_baris ON public.jejak USING btree (tabel, baris);

CREATE INDEX jejak_waktu ON public.jejak USING btree (waktu DESC);

CREATE INDEX kabar_kegiatan_tanggal ON public.kabar_kegiatan USING btree (tanggal DESC);

CREATE INDEX kalender_akademik_mulai ON public.kalender_akademik USING btree (mulai);

CREATE INDEX karya_bukti_karya ON public.karya_bukti USING btree (karya_id);

CREATE INDEX karya_bukti_sha256 ON public.karya_bukti USING btree (sha256) WHERE (sha256 IS NOT NULL);

CREATE UNIQUE INDEX karya_doi_unik ON public.karya USING btree (lower(TRIM(BOTH FROM doi))) WHERE ((doi IS NOT NULL) AND (TRIM(BOTH FROM doi) <> ''::text));

CREATE INDEX karya_induk_idx ON public.karya USING btree (induk_id);

CREATE INDEX karya_judul_norm ON public.karya USING btree (judul_norm);

CREATE INDEX karya_kat ON public.karya USING btree (kategori, status);

CREATE INDEX karya_kerjasama_idx ON public.karya USING btree (kerjasama_id);

CREATE INDEX karya_mitra_kolom_lama ON public.karya USING btree (lower(TRIM(BOTH FROM mitra_institusi))) WHERE ((mitra_institusi IS NOT NULL) AND (TRIM(BOTH FROM mitra_institusi) <> ''::text));

CREATE INDEX karya_skema ON public.karya USING btree (skema_kode);

CREATE INDEX karya_sub_jenis ON public.karya USING btree (kategori, sub_jenis) WHERE (sub_jenis IS NOT NULL);

CREATE INDEX karya_tahun ON public.karya USING btree (tahun);

CREATE INDEX kegiatan_dosen_dosen ON public.kegiatan_dosen USING btree (dosen_id);

CREATE INDEX kegiatan_mulai ON public.kegiatan USING btree (mulai);

CREATE INDEX kelas_dosen_dosen ON public.kelas_dosen USING btree (dosen_id);

CREATE UNIQUE INDEX kelas_dosen_satu_koordinator ON public.kelas_dosen USING btree (kelas_id) WHERE (peran = 'koordinator'::text);

CREATE INDEX kelas_kuliah_periode ON public.kelas_kuliah USING btree (tahun_akademik, semester);

CREATE INDEX km_karya ON public.karya_mahasiswa USING btree (karya_id);

CREATE INDEX km_koresp ON public.karya_mahasiswa USING btree (korespondensi) WHERE korespondensi;

CREATE INDEX km_nim ON public.karya_mahasiswa USING btree (nim);

CREATE INDEX kmi_karya ON public.karya_mitra USING btree (karya_id);

CREATE INDEX kmi_nama ON public.karya_mitra USING btree (lower(TRIM(BOTH FROM institusi)));

CREATE UNIQUE INDEX kmi_unik ON public.karya_mitra USING btree (karya_id, lower(TRIM(BOTH FROM institusi)));

CREATE INDEX koordinator_dosen ON public.koordinator USING btree (dosen_id);

CREATE INDEX kp_dosen ON public.karya_penulis USING btree (dosen_id);

CREATE INDEX kp_koresp ON public.karya_penulis USING btree (korespondensi) WHERE korespondensi;

CREATE UNIQUE INDEX kp_kuota_unik ON public.kp_kuota USING btree (ts, COALESCE(dosen_id, '00000000-0000-0000-0000-000000000000'::uuid));

CREATE INDEX kp_tolak_instansi_pengajuan ON public.kp_tolak_instansi USING btree (pengajuan_id);

CREATE INDEX lkps_bukti_baris ON public.lkps_bukti USING btree (tabel, baris_id);

CREATE UNIQUE INDEX lkps_bukti_dokumen_unik ON public.lkps_bukti USING btree (tabel, baris_id, dokumen_id) WHERE (dokumen_id IS NOT NULL);

CREATE INDEX lkps_bukti_sha256 ON public.lkps_bukti USING btree (sha256) WHERE (sha256 IS NOT NULL);

CREATE INDEX lkps_prestasi_status ON public.lkps_prestasi_mahasiswa USING btree (status);

CREATE INDEX masukan_mahasiswa_dikirim ON public.masukan_mahasiswa USING btree (dikirim DESC);

CREATE INDEX mhs_email_alt_riwayat_nim ON public.mhs_email_alt_riwayat USING btree (nim, waktu DESC);

CREATE INDEX mk_padanan_sah_log_pasangan ON public.mk_padanan_sah_log USING btree (kurikulum_lama, kurikulum_baru, pada DESC);

CREATE UNIQUE INDEX mk_rps_kode_verifikasi ON public.mk_rps USING btree (kode_verifikasi) WHERE (kode_verifikasi IS NOT NULL);

CREATE INDEX mk_rps_pengesahan_mk ON public.mk_rps_pengesahan USING btree (kurikulum, kode_mk, waktu);

CREATE INDEX mk_rps_review_reviewer ON public.mk_rps_review USING btree (reviewer_id);

CREATE INDEX mk_rps_riwayat_mk ON public.mk_rps_riwayat USING btree (kurikulum, kode_mk, waktu DESC);

CREATE INDEX mk_rps_tinjauan_log_t ON public.mk_rps_tinjauan_log USING btree (tinjauan_id, waktu);

CREATE INDEX mk_rps_ttd_mk ON public.mk_rps_ttd USING btree (kurikulum, kode_mk, waktu DESC);

CREATE INDEX mk_silabus_log_mk ON public.mk_silabus_log USING btree (kurikulum, kode_mk, id);

CREATE INDEX mk_struktur_riwayat_mk ON public.mk_struktur_riwayat USING btree (kurikulum, kode_mk, waktu DESC);

CREATE INDEX pengajuan_berkas_induk ON public.pengajuan_berkas USING btree (pengajuan_id);

CREATE INDEX pengajuan_mahasiswa_nim ON public.pengajuan_mahasiswa USING btree (nim);

CREATE INDEX pengajuan_mahasiswa_status ON public.pengajuan_mahasiswa USING btree (status);

CREATE INDEX pengajuan_riwayat_induk ON public.pengajuan_riwayat USING btree (pengajuan_id, waktu);

CREATE INDEX peringatan_keamanan_belum ON public.peringatan_keamanan USING btree (id) WHERE (dikirim IS NULL);

CREATE INDEX portofolio_berkas_mk ON public.portofolio_berkas USING btree (tahun_akademik, semester, kode_mk);

CREATE UNIQUE INDEX potret_skor_otomatis_bulan ON public.potret_skor USING btree (bulan) WHERE otomatis;

CREATE UNIQUE INDEX rapat_peserta_dosen ON public.rapat_peserta USING btree (rapat_id, dosen_id) WHERE (dosen_id IS NOT NULL);

CREATE UNIQUE INDEX rapat_peserta_klien ON public.rapat_peserta USING btree (rapat_id, klien) WHERE (klien IS NOT NULL);

CREATE INDEX rapat_tanggal ON public.rapat USING btree (tanggal DESC);

CREATE INDEX rapat_tindak_pj ON public.rapat_tindak USING btree (pj_dosen_id);

CREATE INDEX rapat_tindak_rapat ON public.rapat_tindak USING btree (rapat_id, urutan);

CREATE INDEX ref_cpl_korelasi_tujuan ON public.ref_cpl_korelasi USING btree (kurikulum_tujuan, cpl_tujuan);

CREATE UNIQUE INDEX ref_mata_kuliah_id ON public.ref_mata_kuliah USING btree (id);

CREATE UNIQUE INDEX ref_mata_kuliah_kurikulum_kode ON public.ref_mata_kuliah USING btree (kurikulum, kode);

CREATE INDEX ref_mk_cpl_cpl ON public.ref_mk_cpl USING btree (kurikulum, cpl);

CREATE UNIQUE INDEX ref_mk_padanan_unik ON public.ref_mk_padanan USING btree (kurikulum_lama, kode_lama, COALESCE(kode_baru, ''::text));

CREATE INDEX ref_topik_keahlian_bidang ON public.ref_topik_keahlian USING btree (bidang, urutan);

CREATE INDEX spmi_standar_revisi_standar ON public.spmi_standar_revisi USING btree (standar_id);

CREATE INDEX ta_bimbingan_nim ON public.ta_bimbingan USING btree (upper(btrim(nim)), tanggal);

CREATE UNIQUE INDEX ta_kecuali_urutan_nim_tahap ON public.ta_kecuali_urutan USING btree (upper(btrim(nim)), tahap);

CREATE UNIQUE INDEX ta_kuota_unik_smt ON public.ta_kuota USING btree (ts, semester, COALESCE(dosen_id, '00000000-0000-0000-0000-000000000000'::uuid));

CREATE UNIQUE INDEX ta_nilai_penilai ON public.ta_nilai USING btree (jadwal_id, bagian, COALESCE(penilai_nidn, ('luar:'::text || lower(btrim(penilai_nama)))));

CREATE INDEX target_dosen_dosen ON public.target_dosen USING btree (dosen_id);

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ami_temuan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.butir_bukti FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.cpl_berkas FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.cpl_kelas FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.cpl_ringkasan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.dokumen FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.dosen FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.evaluasi_mk FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.evaluasi_tindak FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.karya FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.karya_bukti FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.karya_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.karya_mitra FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.karya_penulis FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.koordinator FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.led_narasi FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.led_penugasan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.led_tim FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_bkd FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_bukti FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_dokumen_k3l FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_fasilitas_k3l FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_kepuasan_pengguna FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_kerjasama FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_kohort_lulusan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_luaran_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_mahasiswa_ta FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_penggunaan_dana FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_peta_jalan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_prasarana FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_prestasi_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_prodi_upps FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_publikasi_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_spmi_ppepp FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_target_kinerja FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_tendik FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_tracer_lulusan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.lkps_vmts FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.pengaturan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_bidang_keahlian FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_cpl FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_cpl_korelasi FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_kata_visi FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_kategori_publikasi FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_kelompok_dana FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_mata_kuliah FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_mk_cpl FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_skema_dana FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_tema_peta_jalan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ref_topik_keahlian FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.spmi_capaian FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.spmi_standar FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.spmi_standar_revisi FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ta_arsip FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ta_berkas FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ta_bimbingan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ta_kecuali_urutan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ta_nilai FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ta_rubrik FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.ta_syarat_bimbingan FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.target_baku FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER catat_jejak AFTER INSERT OR DELETE OR UPDATE ON public.target_dosen FOR EACH ROW EXECUTE FUNCTION public.catat_jejak();

CREATE TRIGGER dosen_berhalangan_rentang_cek BEFORE INSERT OR UPDATE ON public.dosen_berhalangan_rentang FOR EACH ROW EXECUTE FUNCTION public.berhalangan_rentang_cek();

CREATE TRIGGER hapus_bukti_prestasi AFTER DELETE ON public.lkps_prestasi_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.hapus_bukti_prestasi();

CREATE TRIGGER jadwal_slot_hapus_rentang AFTER DELETE ON public.jadwal_slot FOR EACH ROW EXECUTE FUNCTION public.berhalangan_rentang_slot_hapus();

CREATE TRIGGER jaga_email_alternatif BEFORE INSERT OR UPDATE OF email, email_alternatif ON public.dosen FOR EACH ROW EXECUTE FUNCTION public.jaga_email_alternatif();

CREATE TRIGGER jaga_evaluasi_mk BEFORE UPDATE ON public.evaluasi_mk FOR EACH ROW EXECUTE FUNCTION public.jaga_evaluasi_mk();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ajuan_bkd FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ajuan_hapus FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ajuan_prestasi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ajuan_ubah FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ami_temuan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.berhalangan_konfirmasi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.butir_bukti FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.cpl_berkas FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.cpl_kelas FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.cpl_ringkasan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.dokumen FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE ON public.dosen FOR EACH ROW EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.dosen_ampu_ts FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.dosen_berhalangan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.dosen_berhalangan_rentang FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.dosen_berhalangan_tgl FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.evaluasi_mk FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.evaluasi_tindak FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.hari_libur FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.hibah_ajuan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.hibah_panggilan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.hibah_tim FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.insentif_pengajuan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.insentif_publikasi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.jadwal_hari FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.jadwal_kuliah FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.jadwal_kuliah_sah FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.jadwal_slot FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.jadwal_ta FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kabar_kegiatan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kalender_akademik FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.karya FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.karya_bukti FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.karya_mahasiswa FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.karya_mitra FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.karya_penulis FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.karya_sitasi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kegiatan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kegiatan_dosen FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kelas_dosen FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kelas_kuliah FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.koordinator FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kp_instansi_keputusan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kp_kuota FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kp_tolak_instansi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.kunjungan_publik FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.laboratorium FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.layanan_kunci FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.led_narasi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.led_penugasan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.led_tim FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_bimbingan_utama FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_bkd FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_bukti FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_dokumen_k3l FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_fasilitas_k3l FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_kepuasan_pengguna FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_kerjasama FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_keuangan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_kohort_lulusan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_luaran_mahasiswa FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_mahasiswa_angkatan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_mahasiswa_ta FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_penggunaan_dana FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_peta_jalan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_prasarana FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_prestasi_mahasiswa FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_prodi_upps FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_publikasi_mahasiswa FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_sarana_standar FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_spmi_ppepp FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_target_kinerja FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_tendik FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_tracer_lulusan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.lkps_vmts FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.masukan_mahasiswa FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mhs_email_alt FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mhs_email_alt_riwayat FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_padanan_sah FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_padanan_sah_log FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_rps FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_rps_pengesahan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_rps_review FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_rps_riwayat FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_rps_tinjauan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_rps_tinjauan_log FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_rps_ttd FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_silabus FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_silabus_log FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_struktur FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.mk_struktur_riwayat FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.pengajuan_berkas FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.pengajuan_mahasiswa FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.pengajuan_riwayat FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.pengaturan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.pengelola_prodi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.pengumuman_mahasiswa FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.peringatan_keamanan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.portofolio_berkas FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.potret_skor FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.profil_prodi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.rapat FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.rapat_peserta FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.rapat_tindak FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_bidang_keahlian FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_cpl FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_cpl_korelasi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_kata_visi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_kategori_publikasi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_kelompok_dana FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_mata_kuliah FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_mk_cpl FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_mk_padanan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_profil_lulusan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_skema_dana FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_tema_peta_jalan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ref_topik_keahlian FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.spmi_capaian FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.spmi_standar FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.spmi_standar_revisi FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.status_sistem FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.survei FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.survei_jawaban FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_arsip FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_berkas FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_bimbingan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_kecuali_urutan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_kk_dekat FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_kuota FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_nilai FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_rubrik FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.ta_syarat_bimbingan FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.tanya_jawab FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.target_baku FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.target_dosen FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.tautan_ami FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.templat_email FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.testimoni FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hanya_baca BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON public.yudisium_berkas FOR EACH STATEMENT EXECUTE FUNCTION public.jaga_hanya_baca();

CREATE TRIGGER jaga_hibah_ajuan BEFORE UPDATE ON public.hibah_ajuan FOR EACH ROW EXECUTE FUNCTION public.jaga_hibah_ajuan();

CREATE TRIGGER jaga_kegiatan BEFORE UPDATE ON public.kegiatan FOR EACH ROW EXECUTE FUNCTION public.jaga_kegiatan();

CREATE TRIGGER jaga_mk_rps BEFORE INSERT OR UPDATE ON public.mk_rps FOR EACH ROW EXECUTE FUNCTION public.jaga_mk_rps();

CREATE TRIGGER jaga_mk_rps_tinjauan BEFORE INSERT OR UPDATE ON public.mk_rps_tinjauan FOR EACH ROW EXECUTE FUNCTION public.jaga_mk_rps_tinjauan();

CREATE TRIGGER jaga_rapat BEFORE UPDATE ON public.rapat FOR EACH ROW EXECUTE FUNCTION public.jaga_rapat();

CREATE TRIGGER jejak_mk_rps BEFORE INSERT OR UPDATE ON public.mk_rps FOR EACH ROW EXECUTE FUNCTION public.jejak_mk_rps();

CREATE TRIGGER jejak_mk_struktur BEFORE INSERT OR UPDATE ON public.mk_struktur FOR EACH ROW EXECUTE FUNCTION public.jejak_mk_struktur();

CREATE TRIGGER jejak_portofolio BEFORE INSERT ON public.portofolio_berkas FOR EACH ROW EXECUTE FUNCTION public.jejak_portofolio();

CREATE TRIGGER karya_induk_periksa BEFORE INSERT OR UPDATE ON public.karya FOR EACH ROW EXECUTE FUNCTION public.periksa_induk();

CREATE TRIGGER kp_instansi_keputusan_rapikan BEFORE INSERT OR UPDATE ON public.kp_instansi_keputusan FOR EACH ROW EXECUTE FUNCTION public.kp_instansi_keputusan_rapikan();

CREATE TRIGGER led_tim_sinkron AFTER INSERT OR DELETE OR UPDATE OF dosen_id ON public.led_tim FOR EACH ROW EXECUTE FUNCTION public.sinkron_tim_penyusun();

CREATE TRIGGER mhs_email_alt_jejak AFTER INSERT OR DELETE OR UPDATE ON public.mhs_email_alt FOR EACH ROW EXECUTE FUNCTION public.mhs_email_alt_jejak();

CREATE TRIGGER mhs_email_alt_rapikan BEFORE INSERT OR UPDATE ON public.mhs_email_alt FOR EACH ROW EXECUTE FUNCTION public.mhs_email_alt_rapikan();

CREATE TRIGGER periksa_keamanan AFTER INSERT ON public.jejak FOR EACH ROW EXECUTE FUNCTION public.periksa_keamanan();

CREATE TRIGGER ref_mk_padanan_berubah AFTER INSERT OR DELETE OR UPDATE ON public.ref_mk_padanan FOR EACH ROW EXECUTE FUNCTION public.padanan_berubah();

CREATE TRIGGER rps_b_berubah AFTER INSERT OR UPDATE ON public.mk_struktur FOR EACH ROW EXECUTE FUNCTION public.rps_b_berubah();

CREATE TRIGGER ta_jaga_ba BEFORE INSERT OR DELETE OR UPDATE ON public.jadwal_ta FOR EACH ROW EXECUTE FUNCTION public.ta_jaga_ba();

CREATE TRIGGER ta_jaga_urutan BEFORE UPDATE OF status ON public.pengajuan_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.ta_jaga_urutan();

CREATE TRIGGER ta_periksa_berkas BEFORE UPDATE OF status ON public.pengajuan_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.ta_periksa_berkas();

CREATE TRIGGER ta_periksa_bimbingan BEFORE UPDATE OF status ON public.pengajuan_mahasiswa FOR EACH ROW EXECUTE FUNCTION public.ta_periksa_bimbingan();

CREATE TRIGGER trg_turunkan BEFORE INSERT OR UPDATE ON public.karya FOR EACH ROW EXECUTE FUNCTION public.turunkan_kategori_lkps();

ALTER TABLE ONLY public.ajuan_bkd
    ADD CONSTRAINT ajuan_bkd_bkd_id_fkey FOREIGN KEY (bkd_id) REFERENCES public.lkps_bkd(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ajuan_bkd
    ADD CONSTRAINT ajuan_bkd_oleh_fkey FOREIGN KEY (oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.ajuan_hapus
    ADD CONSTRAINT ajuan_hapus_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ajuan_hapus
    ADD CONSTRAINT ajuan_hapus_oleh_fkey FOREIGN KEY (oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.ajuan_prestasi
    ADD CONSTRAINT ajuan_prestasi_oleh_fkey FOREIGN KEY (oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.ajuan_prestasi
    ADD CONSTRAINT ajuan_prestasi_prestasi_id_fkey FOREIGN KEY (prestasi_id) REFERENCES public.lkps_prestasi_mahasiswa(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ajuan_ubah
    ADD CONSTRAINT ajuan_ubah_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ajuan_ubah
    ADD CONSTRAINT ajuan_ubah_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ajuan_ubah
    ADD CONSTRAINT ajuan_ubah_oleh_fkey FOREIGN KEY (oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.ami_temuan
    ADD CONSTRAINT ami_temuan_standar_id_fkey FOREIGN KEY (standar_id) REFERENCES public.spmi_standar(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.berhalangan_konfirmasi
    ADD CONSTRAINT berhalangan_konfirmasi_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.butir_bukti
    ADD CONSTRAINT butir_bukti_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.cpl_berkas
    ADD CONSTRAINT cpl_berkas_kelas_id_fkey FOREIGN KEY (kelas_id) REFERENCES public.cpl_kelas(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dosen_ampu_ts
    ADD CONSTRAINT dosen_ampu_ts_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dosen_berhalangan
    ADD CONSTRAINT dosen_berhalangan_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dosen_berhalangan_rentang
    ADD CONSTRAINT dosen_berhalangan_rentang_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dosen_berhalangan
    ADD CONSTRAINT dosen_berhalangan_slot_id_fkey FOREIGN KEY (slot_id) REFERENCES public.jadwal_slot(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dosen_berhalangan_tgl
    ADD CONSTRAINT dosen_berhalangan_tgl_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dosen_berhalangan_tgl
    ADD CONSTRAINT dosen_berhalangan_tgl_slot_id_fkey FOREIGN KEY (slot_id) REFERENCES public.jadwal_slot(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.evaluasi_mk
    ADD CONSTRAINT evaluasi_mk_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.evaluasi_tindak
    ADD CONSTRAINT evaluasi_tindak_evaluasi_id_fkey FOREIGN KEY (evaluasi_id) REFERENCES public.evaluasi_mk(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.evaluasi_tindak
    ADD CONSTRAINT evaluasi_tindak_pj_id_fkey FOREIGN KEY (pj_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.evaluasi_tindak
    ADD CONSTRAINT evaluasi_tindak_standar_id_fkey FOREIGN KEY (standar_id) REFERENCES public.spmi_standar(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.hibah_ajuan
    ADD CONSTRAINT hibah_ajuan_dibuat_oleh_fkey FOREIGN KEY (dibuat_oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.hibah_ajuan
    ADD CONSTRAINT hibah_ajuan_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.hibah_ajuan
    ADD CONSTRAINT hibah_ajuan_panggilan_id_fkey FOREIGN KEY (panggilan_id) REFERENCES public.hibah_panggilan(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.hibah_ajuan
    ADD CONSTRAINT hibah_ajuan_skema_kode_fkey FOREIGN KEY (skema_kode) REFERENCES public.ref_skema_dana(kode);

ALTER TABLE ONLY public.hibah_panggilan
    ADD CONSTRAINT hibah_panggilan_skema_kode_fkey FOREIGN KEY (skema_kode) REFERENCES public.ref_skema_dana(kode) ON DELETE SET NULL;

ALTER TABLE ONLY public.hibah_tim
    ADD CONSTRAINT hibah_tim_ajuan_id_fkey FOREIGN KEY (ajuan_id) REFERENCES public.hibah_ajuan(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.hibah_tim
    ADD CONSTRAINT hibah_tim_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.insentif_pengajuan
    ADD CONSTRAINT insentif_pengajuan_dibuat_oleh_fkey FOREIGN KEY (dibuat_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.insentif_publikasi
    ADD CONSTRAINT insentif_publikasi_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.insentif_publikasi
    ADD CONSTRAINT insentif_publikasi_oleh_fkey FOREIGN KEY (oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.insentif_publikasi
    ADD CONSTRAINT insentif_publikasi_pengajuan_id_fkey FOREIGN KEY (pengajuan_id) REFERENCES public.insentif_pengajuan(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.insentif_publikasi
    ADD CONSTRAINT insentif_publikasi_pengklaim_id_fkey FOREIGN KEY (pengklaim_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.jadwal_kuliah
    ADD CONSTRAINT jadwal_kuliah_kelas_id_fkey FOREIGN KEY (kelas_id) REFERENCES public.kelas_kuliah(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.jadwal_ta
    ADD CONSTRAINT jadwal_ta_pengajuan_id_fkey FOREIGN KEY (pengajuan_id) REFERENCES public.pengajuan_mahasiswa(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.jadwal_ta
    ADD CONSTRAINT jadwal_ta_rubrik_id_fkey FOREIGN KEY (rubrik_id) REFERENCES public.ta_rubrik(id);

ALTER TABLE ONLY public.kabar_kegiatan
    ADD CONSTRAINT kabar_kegiatan_dilaporkan_oleh_fkey FOREIGN KEY (dilaporkan_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.kabar_kegiatan
    ADD CONSTRAINT kabar_kegiatan_kerjasama_id_fkey FOREIGN KEY (kerjasama_id) REFERENCES public.lkps_kerjasama(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.karya_bukti
    ADD CONSTRAINT karya_bukti_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.karya_bukti
    ADD CONSTRAINT karya_bukti_oleh_fkey FOREIGN KEY (oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.karya
    ADD CONSTRAINT karya_dilaporkan_oleh_fkey FOREIGN KEY (dilaporkan_oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.karya
    ADD CONSTRAINT karya_induk_id_fkey FOREIGN KEY (induk_id) REFERENCES public.karya(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.karya
    ADD CONSTRAINT karya_kategori_pub_kode_fkey FOREIGN KEY (kategori_pub_kode) REFERENCES public.ref_kategori_publikasi(kode);

ALTER TABLE ONLY public.karya
    ADD CONSTRAINT karya_kerjasama_id_fkey FOREIGN KEY (kerjasama_id) REFERENCES public.lkps_kerjasama(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.karya_mahasiswa
    ADD CONSTRAINT karya_mahasiswa_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.karya_mitra
    ADD CONSTRAINT karya_mitra_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.karya_penulis
    ADD CONSTRAINT karya_penulis_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.karya_penulis
    ADD CONSTRAINT karya_penulis_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.karya_sitasi
    ADD CONSTRAINT karya_sitasi_karya_id_fkey FOREIGN KEY (karya_id) REFERENCES public.karya(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.karya
    ADD CONSTRAINT karya_skema_kode_fkey FOREIGN KEY (skema_kode) REFERENCES public.ref_skema_dana(kode);

ALTER TABLE ONLY public.karya
    ADD CONSTRAINT karya_tema_id_fkey FOREIGN KEY (tema_id) REFERENCES public.ref_tema_peta_jalan(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.kegiatan_dosen
    ADD CONSTRAINT kegiatan_dosen_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kegiatan_dosen
    ADD CONSTRAINT kegiatan_dosen_kegiatan_id_fkey FOREIGN KEY (kegiatan_id) REFERENCES public.kegiatan(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kelas_dosen
    ADD CONSTRAINT kelas_dosen_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kelas_dosen
    ADD CONSTRAINT kelas_dosen_kelas_id_fkey FOREIGN KEY (kelas_id) REFERENCES public.kelas_kuliah(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kelas_kuliah
    ADD CONSTRAINT kelas_kuliah_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.koordinator
    ADD CONSTRAINT koordinator_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.koordinator
    ADD CONSTRAINT koordinator_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.koordinator
    ADD CONSTRAINT koordinator_laboratorium_id_fkey FOREIGN KEY (laboratorium_id) REFERENCES public.laboratorium(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.kp_kuota
    ADD CONSTRAINT kp_kuota_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kp_tolak_instansi
    ADD CONSTRAINT kp_tolak_instansi_pengajuan_id_fkey FOREIGN KEY (pengajuan_id) REFERENCES public.pengajuan_mahasiswa(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.led_tim
    ADD CONSTRAINT led_tim_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.lkps_bkd
    ADD CONSTRAINT lkps_bkd_dilaporkan_oleh_fkey FOREIGN KEY (dilaporkan_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.lkps_bukti
    ADD CONSTRAINT lkps_bukti_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.lkps_prestasi_mahasiswa
    ADD CONSTRAINT lkps_prestasi_mahasiswa_dilaporkan_oleh_fkey FOREIGN KEY (dilaporkan_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.lkps_spmi_ppepp
    ADD CONSTRAINT lkps_spmi_ppepp_audit_dokumen_id_fkey FOREIGN KEY (audit_dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.lkps_spmi_ppepp
    ADD CONSTRAINT lkps_spmi_ppepp_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.lkps_spmi_ppepp
    ADD CONSTRAINT lkps_spmi_ppepp_peningkatan_dokumen_id_fkey FOREIGN KEY (peningkatan_dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.lkps_spmi_ppepp
    ADD CONSTRAINT lkps_spmi_ppepp_rtm_dokumen_id_fkey FOREIGN KEY (rtm_dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.lkps_target_kinerja
    ADD CONSTRAINT lkps_target_kinerja_standar_id_fkey FOREIGN KEY (standar_id) REFERENCES public.spmi_standar(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.lkps_tendik
    ADD CONSTRAINT lkps_tendik_laboratorium_id_fkey FOREIGN KEY (laboratorium_id) REFERENCES public.laboratorium(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_padanan_sah_log
    ADD CONSTRAINT mk_padanan_sah_log_oleh_id_fkey FOREIGN KEY (oleh_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_padanan_sah
    ADD CONSTRAINT mk_padanan_sah_sah_oleh_fkey FOREIGN KEY (sah_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_padanan_sah
    ADD CONSTRAINT mk_padanan_sah_tetap_oleh_fkey FOREIGN KEY (tetap_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps
    ADD CONSTRAINT mk_rps_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.mk_rps_pengesahan
    ADD CONSTRAINT mk_rps_pengesahan_atas_nama_id_fkey FOREIGN KEY (atas_nama_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps_pengesahan
    ADD CONSTRAINT mk_rps_pengesahan_oleh_id_fkey FOREIGN KEY (oleh_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps_review
    ADD CONSTRAINT mk_rps_review_ditunjuk_oleh_fkey FOREIGN KEY (ditunjuk_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps_review
    ADD CONSTRAINT mk_rps_review_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.mk_rps_review
    ADD CONSTRAINT mk_rps_review_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.mk_rps_review
    ADD CONSTRAINT mk_rps_review_tanggapan_oleh_fkey FOREIGN KEY (tanggapan_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps
    ADD CONSTRAINT mk_rps_sah_atas_nama_fkey FOREIGN KEY (sah_atas_nama) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps
    ADD CONSTRAINT mk_rps_sah_oleh_fkey FOREIGN KEY (sah_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps
    ADD CONSTRAINT mk_rps_tetap_atas_nama_fkey FOREIGN KEY (tetap_atas_nama) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps
    ADD CONSTRAINT mk_rps_tetap_oleh_fkey FOREIGN KEY (tetap_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps_tinjauan
    ADD CONSTRAINT mk_rps_tinjauan_disetujui_oleh_fkey FOREIGN KEY (disetujui_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps_tinjauan
    ADD CONSTRAINT mk_rps_tinjauan_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.mk_rps_tinjauan_log
    ADD CONSTRAINT mk_rps_tinjauan_log_oleh_id_fkey FOREIGN KEY (oleh_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_rps_tinjauan_log
    ADD CONSTRAINT mk_rps_tinjauan_log_tinjauan_id_fkey FOREIGN KEY (tinjauan_id) REFERENCES public.mk_rps_tinjauan(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.mk_rps_ttd
    ADD CONSTRAINT mk_rps_ttd_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.mk_silabus
    ADD CONSTRAINT mk_silabus_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.mk_silabus_log
    ADD CONSTRAINT mk_silabus_log_oleh_id_fkey FOREIGN KEY (oleh_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_silabus
    ADD CONSTRAINT mk_silabus_sah_oleh_fkey FOREIGN KEY (sah_oleh) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.mk_struktur
    ADD CONSTRAINT mk_struktur_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.pemakaian_halaman
    ADD CONSTRAINT pemakaian_halaman_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.pengajuan_berkas
    ADD CONSTRAINT pengajuan_berkas_pengajuan_id_fkey FOREIGN KEY (pengajuan_id) REFERENCES public.pengajuan_mahasiswa(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.pengajuan_mahasiswa
    ADD CONSTRAINT pengajuan_mahasiswa_kabar_id_fkey FOREIGN KEY (kabar_id) REFERENCES public.kabar_kegiatan(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.pengajuan_mahasiswa
    ADD CONSTRAINT pengajuan_mahasiswa_pembimbing_id_fkey FOREIGN KEY (pembimbing_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.pengajuan_mahasiswa
    ADD CONSTRAINT pengajuan_mahasiswa_prestasi_id_fkey FOREIGN KEY (prestasi_id) REFERENCES public.lkps_prestasi_mahasiswa(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.pengajuan_riwayat
    ADD CONSTRAINT pengajuan_riwayat_pengajuan_id_fkey FOREIGN KEY (pengajuan_id) REFERENCES public.pengajuan_mahasiswa(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.portofolio_berkas
    ADD CONSTRAINT portofolio_berkas_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.rapat
    ADD CONSTRAINT rapat_dibuat_oleh_fkey FOREIGN KEY (dibuat_oleh) REFERENCES public.dosen(id);

ALTER TABLE ONLY public.rapat
    ADD CONSTRAINT rapat_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.rapat_peserta
    ADD CONSTRAINT rapat_peserta_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.rapat_peserta
    ADD CONSTRAINT rapat_peserta_rapat_id_fkey FOREIGN KEY (rapat_id) REFERENCES public.rapat(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.rapat_tindak
    ADD CONSTRAINT rapat_tindak_pj_dosen_id_fkey FOREIGN KEY (pj_dosen_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.rapat_tindak
    ADD CONSTRAINT rapat_tindak_rapat_id_fkey FOREIGN KEY (rapat_id) REFERENCES public.rapat(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ref_cpl_korelasi
    ADD CONSTRAINT ref_cpl_korelasi_kurikulum_asal_cpl_asal_fkey FOREIGN KEY (kurikulum_asal, cpl_asal) REFERENCES public.ref_cpl(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.ref_cpl_korelasi
    ADD CONSTRAINT ref_cpl_korelasi_kurikulum_tujuan_cpl_tujuan_fkey FOREIGN KEY (kurikulum_tujuan, cpl_tujuan) REFERENCES public.ref_cpl(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.ref_mata_kuliah
    ADD CONSTRAINT ref_mata_kuliah_koordinator_fk FOREIGN KEY (koordinator_nidn) REFERENCES public.dosen(nidn) ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE ONLY public.ref_mk_cpl
    ADD CONSTRAINT ref_mk_cpl_kurikulum_cpl_fkey FOREIGN KEY (kurikulum, cpl) REFERENCES public.ref_cpl(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.ref_mk_cpl
    ADD CONSTRAINT ref_mk_cpl_kurikulum_kode_mk_fkey FOREIGN KEY (kurikulum, kode_mk) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.ref_mk_padanan
    ADD CONSTRAINT ref_mk_padanan_kurikulum_baru_kode_baru_fkey FOREIGN KEY (kurikulum_baru, kode_baru) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.ref_mk_padanan
    ADD CONSTRAINT ref_mk_padanan_kurikulum_lama_kode_lama_fkey FOREIGN KEY (kurikulum_lama, kode_lama) REFERENCES public.ref_mata_kuliah(kurikulum, kode) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY public.ref_skema_dana
    ADD CONSTRAINT ref_skema_dana_kelompok_fkey FOREIGN KEY (kelompok) REFERENCES public.ref_kelompok_dana(kode);

ALTER TABLE ONLY public.ref_topik_keahlian
    ADD CONSTRAINT ref_topik_keahlian_bidang_fkey FOREIGN KEY (bidang) REFERENCES public.ref_bidang_keahlian(kode) ON UPDATE CASCADE;

ALTER TABLE ONLY public.spmi_capaian
    ADD CONSTRAINT spmi_capaian_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.spmi_capaian
    ADD CONSTRAINT spmi_capaian_standar_id_fkey FOREIGN KEY (standar_id) REFERENCES public.spmi_standar(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.spmi_standar
    ADD CONSTRAINT spmi_standar_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.spmi_standar_revisi
    ADD CONSTRAINT spmi_standar_revisi_dokumen_id_fkey FOREIGN KEY (dokumen_id) REFERENCES public.dokumen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.spmi_standar_revisi
    ADD CONSTRAINT spmi_standar_revisi_rapat_id_fkey FOREIGN KEY (rapat_id) REFERENCES public.rapat(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.spmi_standar_revisi
    ADD CONSTRAINT spmi_standar_revisi_standar_id_fkey FOREIGN KEY (standar_id) REFERENCES public.spmi_standar(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.spmi_standar_revisi
    ADD CONSTRAINT spmi_standar_revisi_temuan_id_fkey FOREIGN KEY (temuan_id) REFERENCES public.ami_temuan(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.survei_jawaban
    ADD CONSTRAINT survei_jawaban_survei_id_fkey FOREIGN KEY (survei_id) REFERENCES public.survei(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ta_bimbingan
    ADD CONSTRAINT ta_bimbingan_pembimbing_id_fkey FOREIGN KEY (pembimbing_id) REFERENCES public.dosen(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.ta_kuota
    ADD CONSTRAINT ta_kuota_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ta_nilai
    ADD CONSTRAINT ta_nilai_jadwal_id_fkey FOREIGN KEY (jadwal_id) REFERENCES public.jadwal_ta(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ta_nilai
    ADD CONSTRAINT ta_nilai_rubrik_id_fkey FOREIGN KEY (rubrik_id) REFERENCES public.ta_rubrik(id);

ALTER TABLE ONLY public.tanya_jawab
    ADD CONSTRAINT tanya_jawab_sumber_id_fkey FOREIGN KEY (sumber_id) REFERENCES public.masukan_mahasiswa(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.target_dosen
    ADD CONSTRAINT target_dosen_dosen_id_fkey FOREIGN KEY (dosen_id) REFERENCES public.dosen(id) ON DELETE CASCADE;

ALTER TABLE public.ajuan_bkd ENABLE ROW LEVEL SECURITY;

CREATE POLICY ajuan_bkd_admin ON public.ajuan_bkd TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ajuan_bkd_ajukan ON public.ajuan_bkd FOR INSERT TO authenticated WITH CHECK (((oleh = public.me()) AND (status = 'menunggu'::text) AND public.bkd_milik(bkd_id)));

CREATE POLICY ajuan_bkd_baca ON public.ajuan_bkd FOR SELECT TO authenticated USING ((oleh = public.me()));

CREATE POLICY ajuan_bkd_batal ON public.ajuan_bkd FOR DELETE TO authenticated USING ((oleh = public.me()));

ALTER TABLE public.ajuan_hapus ENABLE ROW LEVEL SECURITY;

CREATE POLICY ajuan_hapus_admin ON public.ajuan_hapus TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ajuan_hapus_ajukan ON public.ajuan_hapus FOR INSERT TO authenticated WITH CHECK ((public.penulis_karya(karya_id) AND (oleh = public.me())));

CREATE POLICY ajuan_hapus_baca ON public.ajuan_hapus FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY ajuan_hapus_batal ON public.ajuan_hapus FOR DELETE TO authenticated USING ((oleh = public.me()));

ALTER TABLE public.ajuan_prestasi ENABLE ROW LEVEL SECURITY;

CREATE POLICY ajuan_prestasi_admin ON public.ajuan_prestasi TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ajuan_prestasi_ajukan ON public.ajuan_prestasi FOR INSERT TO authenticated WITH CHECK (((oleh = public.me()) AND (status = 'menunggu'::text) AND public.prestasi_milik(prestasi_id)));

CREATE POLICY ajuan_prestasi_baca ON public.ajuan_prestasi FOR SELECT TO authenticated USING ((oleh = public.me()));

CREATE POLICY ajuan_prestasi_batal ON public.ajuan_prestasi FOR DELETE TO authenticated USING ((oleh = public.me()));

ALTER TABLE public.ajuan_ubah ENABLE ROW LEVEL SECURITY;

CREATE POLICY ajuan_ubah_admin ON public.ajuan_ubah TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ajuan_ubah_ajukan ON public.ajuan_ubah FOR INSERT TO authenticated WITH CHECK (((oleh = public.me()) AND (status = 'menunggu'::text) AND (((jenis = 'karya'::text) AND (public.penulis_karya(karya_id) OR (EXISTS ( SELECT 1
   FROM public.karya k
  WHERE ((k.id = ajuan_ubah.karya_id) AND (k.dilaporkan_oleh = public.me())))))) OR ((jenis = 'profil'::text) AND (dosen_id = public.me())))));

CREATE POLICY ajuan_ubah_baca ON public.ajuan_ubah FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY ajuan_ubah_batal ON public.ajuan_ubah FOR DELETE TO authenticated USING ((oleh = public.me()));

ALTER TABLE public.ami_temuan ENABLE ROW LEVEL SECURITY;

CREATE POLICY ami_temuan_admin ON public.ami_temuan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ami_temuan_baca ON public.ami_temuan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY ami_temuan_gkm ON public.ami_temuan TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.berhalangan_konfirmasi ENABLE ROW LEVEL SECURITY;

CREATE POLICY berhalangan_konfirmasi_baca ON public.berhalangan_konfirmasi FOR SELECT TO authenticated USING (((dosen_id = public.me()) OR public.pengatur_jadwal()));

CREATE POLICY berhalangan_konfirmasi_tulis ON public.berhalangan_konfirmasi TO authenticated USING (((dosen_id = public.me()) OR public.is_admin())) WITH CHECK ((((dosen_id = public.me()) AND (public.me() IS NOT NULL)) OR public.is_admin()));

ALTER TABLE public.butir_bukti ENABLE ROW LEVEL SECURITY;

CREATE POLICY butir_bukti_admin ON public.butir_bukti TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY butir_bukti_baca ON public.butir_bukti FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY butir_bukti_gkm ON public.butir_bukti TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.cpl_berkas ENABLE ROW LEVEL SECURITY;

CREATE POLICY cpl_berkas_admin ON public.cpl_berkas TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY cpl_berkas_baca_sendiri ON public.cpl_berkas FOR SELECT TO authenticated USING (public.cpl_kelas_milik(kelas_id));

CREATE POLICY cpl_berkas_tambah_sendiri ON public.cpl_berkas FOR INSERT TO authenticated WITH CHECK (public.cpl_kelas_milik(kelas_id));

ALTER TABLE public.cpl_kelas ENABLE ROW LEVEL SECURITY;

CREATE POLICY cpl_kelas_admin ON public.cpl_kelas TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY cpl_kelas_baca_sendiri ON public.cpl_kelas FOR SELECT TO authenticated USING (((public.me() IS NOT NULL) AND (lower(dosen_email) = public.email_saya())));

CREATE POLICY cpl_kelas_gkm ON public.cpl_kelas FOR SELECT TO authenticated USING (public.boleh_mutu());

ALTER TABLE public.cpl_ringkasan ENABLE ROW LEVEL SECURITY;

CREATE POLICY cpl_ringkasan_admin ON public.cpl_ringkasan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY cpl_ringkasan_baca ON public.cpl_ringkasan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.dokumen ENABLE ROW LEVEL SECURITY;

CREATE POLICY dokumen_admin ON public.dokumen TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY dokumen_baca ON public.dokumen FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY dokumen_gkm ON public.dokumen TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.dosen ENABLE ROW LEVEL SECURITY;

CREATE POLICY dosen_admin ON public.dosen TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.dosen_ampu_ts ENABLE ROW LEVEL SECURITY;

CREATE POLICY dosen_ampu_ts_admin ON public.dosen_ampu_ts TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY dosen_ampu_ts_baca ON public.dosen_ampu_ts FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY dosen_baca ON public.dosen FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.dosen_berhalangan ENABLE ROW LEVEL SECURITY;

CREATE POLICY dosen_berhalangan_baca ON public.dosen_berhalangan FOR SELECT TO authenticated USING (((dosen_id = public.me()) OR public.pengatur_jadwal()));

ALTER TABLE public.dosen_berhalangan_rentang ENABLE ROW LEVEL SECURITY;

CREATE POLICY dosen_berhalangan_rentang_baca ON public.dosen_berhalangan_rentang FOR SELECT TO authenticated USING (((dosen_id = public.me()) OR public.pengatur_jadwal()));

CREATE POLICY dosen_berhalangan_rentang_tulis ON public.dosen_berhalangan_rentang TO authenticated USING (((dosen_id = public.me()) OR public.is_admin())) WITH CHECK ((((dosen_id = public.me()) AND (public.me() IS NOT NULL)) OR public.is_admin()));

ALTER TABLE public.dosen_berhalangan_tgl ENABLE ROW LEVEL SECURITY;

CREATE POLICY dosen_berhalangan_tgl_baca ON public.dosen_berhalangan_tgl FOR SELECT TO authenticated USING (((dosen_id = public.me()) OR public.pengatur_jadwal()));

CREATE POLICY dosen_berhalangan_tgl_tulis ON public.dosen_berhalangan_tgl TO authenticated USING (((dosen_id = public.me()) OR public.is_admin())) WITH CHECK ((((dosen_id = public.me()) AND (public.me() IS NOT NULL)) OR public.is_admin()));

CREATE POLICY dosen_berhalangan_tulis ON public.dosen_berhalangan TO authenticated USING (((dosen_id = public.me()) OR public.is_admin())) WITH CHECK ((((dosen_id = public.me()) AND (public.me() IS NOT NULL)) OR public.is_admin()));

ALTER TABLE public.evaluasi_mk ENABLE ROW LEVEL SECURITY;

CREATE POLICY evaluasi_mk_admin ON public.evaluasi_mk TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY evaluasi_mk_baca ON public.evaluasi_mk FOR SELECT TO authenticated USING (((dosen_id = public.me()) OR public.lihat_semua_hibah()));

CREATE POLICY evaluasi_mk_gkm ON public.evaluasi_mk TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

CREATE POLICY evaluasi_mk_pengampu ON public.evaluasi_mk FOR UPDATE TO authenticated USING ((dosen_id = public.me())) WITH CHECK ((dosen_id = public.me()));

ALTER TABLE public.evaluasi_tindak ENABLE ROW LEVEL SECURITY;

CREATE POLICY evaluasi_tindak_admin ON public.evaluasi_tindak TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY evaluasi_tindak_baca ON public.evaluasi_tindak FOR SELECT TO authenticated USING (((pj_id = public.me()) OR public.pengampu_evaluasi(evaluasi_id) OR public.lihat_semua_hibah()));

CREATE POLICY evaluasi_tindak_gkm ON public.evaluasi_tindak TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

CREATE POLICY evaluasi_tindak_tambah ON public.evaluasi_tindak FOR INSERT TO authenticated WITH CHECK (public.pengampu_evaluasi(evaluasi_id));

CREATE POLICY evaluasi_tindak_ubah ON public.evaluasi_tindak FOR UPDATE TO authenticated USING (((pj_id = public.me()) OR public.pengampu_evaluasi(evaluasi_id))) WITH CHECK (((pj_id = public.me()) OR public.pengampu_evaluasi(evaluasi_id)));

ALTER TABLE public.hari_libur ENABLE ROW LEVEL SECURITY;

CREATE POLICY hari_libur_admin ON public.hari_libur TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY hari_libur_baca ON public.hari_libur FOR SELECT TO authenticated USING (((public.me() IS NOT NULL) OR public.is_admin()));

ALTER TABLE public.hibah_ajuan ENABLE ROW LEVEL SECURITY;

CREATE POLICY hibah_ajuan_baca ON public.hibah_ajuan FOR SELECT TO authenticated USING ((public.lihat_semua_hibah() OR (dibuat_oleh = public.me()) OR public.tim_hibah(id)));

CREATE POLICY hibah_ajuan_hapus ON public.hibah_ajuan FOR DELETE TO authenticated USING ((public.is_admin() OR public.tim_hibah(id)));

CREATE POLICY hibah_ajuan_tambah ON public.hibah_ajuan FOR INSERT TO authenticated WITH CHECK ((public.boleh_hibah() AND (dibuat_oleh = public.me())));

CREATE POLICY hibah_ajuan_ubah ON public.hibah_ajuan FOR UPDATE TO authenticated USING ((public.is_admin() OR public.tim_hibah(id))) WITH CHECK ((public.is_admin() OR public.tim_hibah(id)));

ALTER TABLE public.hibah_panggilan ENABLE ROW LEVEL SECURITY;

CREATE POLICY hibah_panggilan_admin ON public.hibah_panggilan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY hibah_panggilan_baca ON public.hibah_panggilan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.hibah_tim ENABLE ROW LEVEL SECURITY;

CREATE POLICY hibah_tim_baca ON public.hibah_tim FOR SELECT TO authenticated USING ((public.lihat_semua_hibah() OR public.tim_hibah(ajuan_id)));

CREATE POLICY hibah_tim_ubah ON public.hibah_tim TO authenticated USING ((public.is_admin() OR public.tim_hibah(ajuan_id))) WITH CHECK ((public.is_admin() OR public.tim_hibah(ajuan_id)));

ALTER TABLE public.insentif_pengajuan ENABLE ROW LEVEL SECURITY;

CREATE POLICY insentif_pengajuan_baca ON public.insentif_pengajuan FOR SELECT TO authenticated USING ((public.pengelola_insentif() OR (EXISTS ( SELECT 1
   FROM public.insentif_publikasi i
  WHERE ((i.pengajuan_id = insentif_pengajuan.id) AND ((i.pengklaim_id = public.me()) OR public.penulis_karya(i.karya_id)))))));

ALTER TABLE public.insentif_publikasi ENABLE ROW LEVEL SECURITY;

CREATE POLICY insentif_publikasi_baca ON public.insentif_publikasi FOR SELECT TO authenticated USING (((pengklaim_id = public.me()) OR public.penulis_karya(karya_id) OR public.pengelola_insentif()));

ALTER TABLE public.jadwal_hari ENABLE ROW LEVEL SECURITY;

CREATE POLICY jadwal_hari_admin ON public.jadwal_hari TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY jadwal_hari_baca ON public.jadwal_hari FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.jadwal_kuliah ENABLE ROW LEVEL SECURITY;

CREATE POLICY jadwal_kuliah_baca ON public.jadwal_kuliah FOR SELECT TO authenticated USING (((public.me() IS NOT NULL) AND (public.pengatur_kelas() OR (EXISTS ( SELECT 1
   FROM public.kelas_kuliah k
  WHERE ((k.id = jadwal_kuliah.kelas_id) AND public.jadwal_periode_sah(k.tahun_akademik, k.semester)))))));

ALTER TABLE public.jadwal_kuliah_sah ENABLE ROW LEVEL SECURITY;

CREATE POLICY jadwal_kuliah_sah_baca ON public.jadwal_kuliah_sah FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.jadwal_slot ENABLE ROW LEVEL SECURITY;

CREATE POLICY jadwal_slot_admin ON public.jadwal_slot TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY jadwal_slot_baca ON public.jadwal_slot FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.jadwal_ta ENABLE ROW LEVEL SECURITY;

CREATE POLICY jadwal_ta_admin ON public.jadwal_ta TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY jadwal_ta_baca ON public.jadwal_ta FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY jadwal_ta_koordinator ON public.jadwal_ta TO authenticated USING (public.boleh_tabel('jadwal_ta'::text)) WITH CHECK (public.boleh_tabel('jadwal_ta'::text));

ALTER TABLE public.jejak ENABLE ROW LEVEL SECURITY;

CREATE POLICY jejak_admin_baca ON public.jejak FOR SELECT TO authenticated USING (public.is_admin());

CREATE POLICY kabar_admin ON public.kabar_kegiatan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY kabar_ajukan ON public.kabar_kegiatan FOR INSERT TO authenticated WITH CHECK (((public.me() IS NOT NULL) AND (dilaporkan_oleh = public.me()) AND (status = 'diajukan'::text) AND (catatan IS NULL)));

CREATE POLICY kabar_baca ON public.kabar_kegiatan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY kabar_hapus ON public.kabar_kegiatan FOR DELETE TO authenticated USING (((dilaporkan_oleh = public.me()) AND (status <> 'terbit'::text)));

ALTER TABLE public.kabar_kegiatan ENABLE ROW LEVEL SECURITY;

CREATE POLICY kabar_ubah ON public.kabar_kegiatan FOR UPDATE TO authenticated USING (((dilaporkan_oleh = public.me()) AND (status <> 'terbit'::text))) WITH CHECK (((dilaporkan_oleh = public.me()) AND (status = 'diajukan'::text) AND (catatan IS NULL)));

ALTER TABLE public.kalender_akademik ENABLE ROW LEVEL SECURITY;

CREATE POLICY kalender_akademik_admin ON public.kalender_akademik TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY kalender_akademik_baca ON public.kalender_akademik FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.karya ENABLE ROW LEVEL SECURITY;

CREATE POLICY karya_admin ON public.karya TO authenticated USING ((public.is_admin() AND ((status <> 'draf'::text) OR (dilaporkan_oleh = public.me())))) WITH CHECK (public.is_admin());

CREATE POLICY karya_baca ON public.karya FOR SELECT TO authenticated USING (((public.me() IS NOT NULL) AND ((status <> 'draf'::text) OR (dilaporkan_oleh = public.me()) OR public.penulis_karya(id))));

ALTER TABLE public.karya_bukti ENABLE ROW LEVEL SECURITY;

CREATE POLICY karya_bukti_admin ON public.karya_bukti TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY karya_bukti_baca ON public.karya_bukti FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY karya_bukti_hapus ON public.karya_bukti FOR DELETE TO authenticated USING (((oleh = public.me()) OR public.penulis_karya(karya_id)));

CREATE POLICY karya_bukti_tambah ON public.karya_bukti FOR INSERT TO authenticated WITH CHECK ((public.penulis_karya(karya_id) AND (oleh = public.me())));

CREATE POLICY karya_hapus ON public.karya FOR DELETE TO authenticated USING (((status <> 'terverifikasi'::text) AND (dilaporkan_oleh = public.me())));

ALTER TABLE public.karya_mahasiswa ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.karya_mitra ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.karya_penulis ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.karya_sitasi ENABLE ROW LEVEL SECURITY;

CREATE POLICY karya_sitasi_baca ON public.karya_sitasi FOR SELECT TO authenticated USING ((EXISTS ( SELECT 1
   FROM public.karya k
  WHERE (k.id = karya_sitasi.karya_id))));

CREATE POLICY karya_sitasi_tulis ON public.karya_sitasi TO authenticated USING ((public.penulis_karya(karya_id) OR (public.is_admin() AND (EXISTS ( SELECT 1
   FROM public.karya k
  WHERE (k.id = karya_sitasi.karya_id)))))) WITH CHECK ((public.penulis_karya(karya_id) OR (public.is_admin() AND (EXISTS ( SELECT 1
   FROM public.karya k
  WHERE (k.id = karya_sitasi.karya_id))))));

CREATE POLICY karya_tambah ON public.karya FOR INSERT TO authenticated WITH CHECK (((dilaporkan_oleh = public.me()) AND (status = ANY (ARRAY['diajukan'::text, 'draf'::text]))));

CREATE POLICY karya_ubah ON public.karya FOR UPDATE TO authenticated USING (((status <> 'terverifikasi'::text) AND public.penulis_karya(id))) WITH CHECK (((status = ANY (ARRAY['diajukan'::text, 'draf'::text])) AND public.penulis_karya(id)));

CREATE POLICY kata_visi_admin ON public.ref_kata_visi TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY kata_visi_baca ON public.ref_kata_visi FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.kegiatan ENABLE ROW LEVEL SECURITY;

CREATE POLICY kegiatan_admin ON public.kegiatan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY kegiatan_baca ON public.kegiatan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.kegiatan_dosen ENABLE ROW LEVEL SECURITY;

CREATE POLICY kegiatan_dosen_admin ON public.kegiatan_dosen TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY kegiatan_dosen_baca ON public.kegiatan_dosen FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.kelas_dosen ENABLE ROW LEVEL SECURITY;

CREATE POLICY kelas_dosen_atur ON public.kelas_dosen TO authenticated USING (public.pengatur_kelas()) WITH CHECK (public.pengatur_kelas());

CREATE POLICY kelas_dosen_baca ON public.kelas_dosen FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.kelas_kuliah ENABLE ROW LEVEL SECURITY;

CREATE POLICY kelas_kuliah_atur ON public.kelas_kuliah TO authenticated USING (public.pengatur_kelas()) WITH CHECK (public.pengatur_kelas());

CREATE POLICY kelas_kuliah_baca ON public.kelas_kuliah FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY km_admin ON public.karya_mahasiswa TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY km_baca ON public.karya_mahasiswa FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY km_hapus ON public.karya_mahasiswa FOR DELETE TO authenticated USING ((EXISTS ( SELECT 1
   FROM public.karya k
  WHERE ((k.id = karya_mahasiswa.karya_id) AND (k.status <> 'terverifikasi'::text) AND ((k.dilaporkan_oleh = public.me()) OR public.penulis_karya(k.id))))));

CREATE POLICY km_tambah ON public.karya_mahasiswa FOR INSERT TO authenticated WITH CHECK ((EXISTS ( SELECT 1
   FROM public.karya k
  WHERE ((k.id = karya_mahasiswa.karya_id) AND (k.status <> 'terverifikasi'::text) AND ((k.dilaporkan_oleh = public.me()) OR public.penulis_karya(k.id))))));

CREATE POLICY kmi_admin ON public.karya_mitra TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY kmi_baca ON public.karya_mitra FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY kmi_hapus ON public.karya_mitra FOR DELETE TO authenticated USING ((EXISTS ( SELECT 1
   FROM public.karya k
  WHERE ((k.id = karya_mitra.karya_id) AND (k.status <> 'terverifikasi'::text) AND ((k.dilaporkan_oleh = public.me()) OR public.penulis_karya(k.id))))));

CREATE POLICY kmi_tambah ON public.karya_mitra FOR INSERT TO authenticated WITH CHECK ((EXISTS ( SELECT 1
   FROM public.karya k
  WHERE ((k.id = karya_mitra.karya_id) AND (k.status <> 'terverifikasi'::text) AND ((k.dilaporkan_oleh = public.me()) OR public.penulis_karya(k.id))))));

ALTER TABLE public.koordinator ENABLE ROW LEVEL SECURITY;

CREATE POLICY koordinator_admin ON public.koordinator TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY koordinator_baca ON public.koordinator FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY kp_admin ON public.karya_penulis TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY kp_baca ON public.karya_penulis FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY kp_hapus ON public.karya_penulis FOR DELETE TO authenticated USING (((dosen_id = public.me()) OR (EXISTS ( SELECT 1
   FROM public.karya k
  WHERE ((k.id = karya_penulis.karya_id) AND (k.status <> 'terverifikasi'::text) AND (k.dilaporkan_oleh = public.me()))))));

ALTER TABLE public.kp_instansi_keputusan ENABLE ROW LEVEL SECURITY;

CREATE POLICY kp_instansi_keputusan_baca ON public.kp_instansi_keputusan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY kp_instansi_keputusan_tulis ON public.kp_instansi_keputusan TO authenticated USING (public.boleh_pengajuan('kp'::text)) WITH CHECK (public.boleh_pengajuan('kp'::text));

ALTER TABLE public.kp_kuota ENABLE ROW LEVEL SECURITY;

CREATE POLICY kp_kuota_baca ON public.kp_kuota FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY kp_tambah ON public.karya_penulis FOR INSERT TO authenticated WITH CHECK ((((dosen_id = public.me()) AND (ditambahkan_sendiri = true) AND (public.me() IS NOT NULL)) OR ((ditambahkan_sendiri = false) AND (EXISTS ( SELECT 1
   FROM public.karya k
  WHERE ((k.id = karya_penulis.karya_id) AND (k.status <> 'terverifikasi'::text) AND (k.dilaporkan_oleh = public.me())))))));

ALTER TABLE public.kp_tolak_instansi ENABLE ROW LEVEL SECURITY;

CREATE POLICY kp_tolak_instansi_baca ON public.kp_tolak_instansi FOR SELECT TO authenticated USING (public.kp_tolak_boleh(pengajuan_id));

ALTER TABLE public.kunjungan_publik ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.laboratorium ENABLE ROW LEVEL SECURITY;

CREATE POLICY laboratorium_admin ON public.laboratorium TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY laboratorium_baca ON public.laboratorium FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY laboratorium_kepala ON public.laboratorium FOR UPDATE TO authenticated USING (public.kepala_lab_dari(id)) WITH CHECK (public.kepala_lab_dari(id));

ALTER TABLE public.layanan_kunci ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.led_narasi ENABLE ROW LEVEL SECURITY;

CREATE POLICY led_narasi_baca ON public.led_narasi FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY led_narasi_gkm ON public.led_narasi TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

CREATE POLICY led_narasi_tulis ON public.led_narasi TO authenticated USING (public.boleh_narasi()) WITH CHECK (public.boleh_narasi());

ALTER TABLE public.led_penugasan ENABLE ROW LEVEL SECURITY;

CREATE POLICY led_penugasan_admin ON public.led_penugasan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY led_penugasan_baca ON public.led_penugasan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY led_penugasan_gkm ON public.led_penugasan TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.led_tim ENABLE ROW LEVEL SECURITY;

CREATE POLICY led_tim_admin ON public.led_tim TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY led_tim_baca ON public.led_tim FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY led_tim_gkm ON public.led_tim TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.lkps_bimbingan_utama ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_bimbingan_utama_admin ON public.lkps_bimbingan_utama TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_bkd ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_bkd_admin ON public.lkps_bkd TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_bkd_ajukan ON public.lkps_bkd FOR INSERT TO authenticated WITH CHECK (((nidn = public.nidn_saya()) AND public.saya_dtps() AND (status = 'dtps'::text) AND (verifikasi = 'diajukan'::text) AND (catatan IS NULL) AND (dilaporkan_oleh = public.me())));

CREATE POLICY lkps_bkd_baca ON public.lkps_bkd FOR SELECT TO authenticated USING ((nidn = public.nidn_saya()));

CREATE POLICY lkps_bkd_hapus ON public.lkps_bkd FOR DELETE TO authenticated USING (((verifikasi <> 'terverifikasi'::text) AND (nidn = public.nidn_saya())));

CREATE POLICY lkps_bkd_ubah ON public.lkps_bkd FOR UPDATE TO authenticated USING (((verifikasi <> 'terverifikasi'::text) AND (nidn = public.nidn_saya()))) WITH CHECK (((nidn = public.nidn_saya()) AND (status = 'dtps'::text) AND (verifikasi = 'diajukan'::text) AND (catatan IS NULL)));

ALTER TABLE public.lkps_bukti ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_bukti_admin ON public.lkps_bukti TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_bukti_ami_baca ON public.lkps_bukti FOR SELECT TO authenticated USING (((tabel = 'ami_temuan'::text) AND (public.me() IS NOT NULL)));

CREATE POLICY lkps_bukti_koordinator ON public.lkps_bukti TO authenticated USING (public.boleh_tabel(tabel)) WITH CHECK (public.boleh_tabel(tabel));

CREATE POLICY lkps_bukti_prestasi_baca ON public.lkps_bukti FOR SELECT TO authenticated USING (((tabel = 'lkps_prestasi_mahasiswa'::text) AND public.prestasi_milik(baris_id)));

CREATE POLICY lkps_bukti_prestasi_hapus ON public.lkps_bukti FOR DELETE TO authenticated USING (((tabel = 'lkps_prestasi_mahasiswa'::text) AND public.prestasi_milik(baris_id) AND public.prestasi_belum_verifikasi(baris_id) AND (lower(oleh) = public.email_saya())));

CREATE POLICY lkps_bukti_prestasi_tambah ON public.lkps_bukti FOR INSERT TO authenticated WITH CHECK (((tabel = 'lkps_prestasi_mahasiswa'::text) AND (dokumen_id IS NULL) AND public.prestasi_milik(baris_id) AND (lower(oleh) = public.email_saya())));

ALTER TABLE public.lkps_dokumen_k3l ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_dokumen_k3l_admin ON public.lkps_dokumen_k3l TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_fasilitas_k3l ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_fasilitas_k3l_admin ON public.lkps_fasilitas_k3l TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_kepuasan_pengguna ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_kepuasan_pengguna_admin ON public.lkps_kepuasan_pengguna TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_kepuasan_pengguna_gkm ON public.lkps_kepuasan_pengguna TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.lkps_kerjasama ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_kerjasama_admin ON public.lkps_kerjasama TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_kerjasama_baca ON public.lkps_kerjasama FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.lkps_keuangan ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_keuangan_admin ON public.lkps_keuangan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_kohort_lulusan ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_kohort_lulusan_admin ON public.lkps_kohort_lulusan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_luaran_mahasiswa ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_luaran_mahasiswa_admin ON public.lkps_luaran_mahasiswa TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_luaran_mahasiswa_koordinator ON public.lkps_luaran_mahasiswa TO authenticated USING (public.boleh_tabel('lkps_luaran_mahasiswa'::text)) WITH CHECK (public.boleh_tabel('lkps_luaran_mahasiswa'::text));

ALTER TABLE public.lkps_mahasiswa_angkatan ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_mahasiswa_angkatan_admin ON public.lkps_mahasiswa_angkatan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_mahasiswa_ta ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_mahasiswa_ta_admin ON public.lkps_mahasiswa_ta TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_penggunaan_dana ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_penggunaan_dana_admin ON public.lkps_penggunaan_dana TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_peta_jalan ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_peta_jalan_admin ON public.lkps_peta_jalan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_peta_jalan_baca ON public.lkps_peta_jalan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.lkps_prasarana ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_prasarana_admin ON public.lkps_prasarana TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_prestasi_ajukan ON public.lkps_prestasi_mahasiswa FOR INSERT TO authenticated WITH CHECK (((dilaporkan_oleh = public.me()) AND (status = 'diajukan'::text) AND (catatan IS NULL) AND (public.nidn_saya() = ANY (pembimbing))));

CREATE POLICY lkps_prestasi_baca ON public.lkps_prestasi_mahasiswa FOR SELECT TO authenticated USING (((dilaporkan_oleh = public.me()) OR (public.nidn_saya() = ANY (pembimbing))));

CREATE POLICY lkps_prestasi_hapus ON public.lkps_prestasi_mahasiswa FOR DELETE TO authenticated USING (((status <> 'terverifikasi'::text) AND (dilaporkan_oleh = public.me())));

ALTER TABLE public.lkps_prestasi_mahasiswa ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_prestasi_mahasiswa_admin ON public.lkps_prestasi_mahasiswa TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_prestasi_mahasiswa_koordinator ON public.lkps_prestasi_mahasiswa TO authenticated USING (public.boleh_tabel('lkps_prestasi_mahasiswa'::text)) WITH CHECK (public.boleh_tabel('lkps_prestasi_mahasiswa'::text));

CREATE POLICY lkps_prestasi_ubah ON public.lkps_prestasi_mahasiswa FOR UPDATE TO authenticated USING (((status <> 'terverifikasi'::text) AND (dilaporkan_oleh = public.me()))) WITH CHECK (((status = 'diajukan'::text) AND (catatan IS NULL) AND (dilaporkan_oleh = public.me()) AND (public.nidn_saya() = ANY (pembimbing))));

ALTER TABLE public.lkps_prodi_upps ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_prodi_upps_admin ON public.lkps_prodi_upps TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_publikasi_mahasiswa ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_publikasi_mahasiswa_admin ON public.lkps_publikasi_mahasiswa TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_publikasi_mahasiswa_koordinator ON public.lkps_publikasi_mahasiswa TO authenticated USING (public.boleh_tabel('lkps_publikasi_mahasiswa'::text)) WITH CHECK (public.boleh_tabel('lkps_publikasi_mahasiswa'::text));

ALTER TABLE public.lkps_sarana_standar ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_sarana_standar_admin ON public.lkps_sarana_standar TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_spmi_ppepp ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_spmi_ppepp_admin ON public.lkps_spmi_ppepp TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_spmi_ppepp_gkm ON public.lkps_spmi_ppepp TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.lkps_target_kinerja ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_target_kinerja_admin ON public.lkps_target_kinerja TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY lkps_target_kinerja_baca ON public.lkps_target_kinerja FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY lkps_target_kinerja_gkm ON public.lkps_target_kinerja TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.lkps_tendik ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_tendik_admin ON public.lkps_tendik TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_tracer_lulusan ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_tracer_lulusan_admin ON public.lkps_tracer_lulusan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.lkps_vmts ENABLE ROW LEVEL SECURITY;

CREATE POLICY lkps_vmts_admin ON public.lkps_vmts TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.masukan_mahasiswa ENABLE ROW LEVEL SECURITY;

CREATE POLICY masukan_mahasiswa_admin ON public.masukan_mahasiswa TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.mhs_email_alt ENABLE ROW LEVEL SECURITY;

CREATE POLICY mhs_email_alt_kelola ON public.mhs_email_alt TO authenticated USING (public.boleh_email_alt()) WITH CHECK (public.boleh_email_alt());

ALTER TABLE public.mhs_email_alt_riwayat ENABLE ROW LEVEL SECURITY;

CREATE POLICY mhs_email_alt_riwayat_baca ON public.mhs_email_alt_riwayat FOR SELECT TO authenticated USING (public.boleh_email_alt());

CREATE POLICY mk_admin ON public.ref_mata_kuliah TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY mk_baca ON public.ref_mata_kuliah FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_padanan_sah ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_padanan_sah_baca ON public.mk_padanan_sah FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_padanan_sah_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_padanan_sah_log_baca ON public.mk_padanan_sah_log FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_rps ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_rps_baca ON public.mk_rps FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_rps_pengesahan ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_rps_pengesahan_baca ON public.mk_rps_pengesahan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_rps_review ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_rps_review_baca ON public.mk_rps_review FOR SELECT TO authenticated USING (((reviewer_id = public.me()) OR public.is_admin() OR public.koordinator_aktif('kaprodi'::text)));

ALTER TABLE public.mk_rps_riwayat ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_rps_riwayat_baca ON public.mk_rps_riwayat FOR SELECT TO authenticated USING (public.boleh_mk(kurikulum, kode_mk));

ALTER TABLE public.mk_rps_tinjauan ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_rps_tinjauan_baca ON public.mk_rps_tinjauan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_rps_tinjauan_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_rps_tinjauan_log_baca ON public.mk_rps_tinjauan_log FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY mk_rps_tinjauan_tambah ON public.mk_rps_tinjauan FOR INSERT TO authenticated WITH CHECK ((public.tinjauan_boleh(kurikulum, kode_mk, tahun_akademik, semester) AND (status = 'draf'::text)));

CREATE POLICY mk_rps_tinjauan_ubah ON public.mk_rps_tinjauan FOR UPDATE TO authenticated USING ((public.tinjauan_boleh(kurikulum, kode_mk, tahun_akademik, semester) AND (status = ANY (ARRAY['draf'::text, 'dikembalikan'::text])))) WITH CHECK ((public.tinjauan_boleh(kurikulum, kode_mk, tahun_akademik, semester) AND (status = 'draf'::text)));

ALTER TABLE public.mk_rps_ttd ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_rps_ttd_baca ON public.mk_rps_ttd FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY mk_rps_tulis ON public.mk_rps TO authenticated USING ((public.boleh_rps(kurikulum, kode_mk) AND (status <> 'diajukan'::text))) WITH CHECK ((public.boleh_rps(kurikulum, kode_mk) AND (status = 'draf'::text)));

ALTER TABLE public.mk_silabus ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_silabus_baca ON public.mk_silabus FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_silabus_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_silabus_log_baca ON public.mk_silabus_log FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_struktur ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_struktur_baca ON public.mk_struktur FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.mk_struktur_riwayat ENABLE ROW LEVEL SECURITY;

CREATE POLICY mk_struktur_riwayat_baca ON public.mk_struktur_riwayat FOR SELECT TO authenticated USING (public.boleh_mk(kurikulum, kode_mk));

CREATE POLICY mk_struktur_tulis ON public.mk_struktur TO authenticated USING (public.boleh_mk(kurikulum, kode_mk)) WITH CHECK (public.boleh_mk(kurikulum, kode_mk));

ALTER TABLE public.pemakaian_halaman ENABLE ROW LEVEL SECURITY;

CREATE POLICY pengajuan_baca ON public.pengajuan_mahasiswa FOR SELECT TO authenticated USING ((public.boleh_pengajuan(jenis) OR ((pembimbing_id = public.me()) AND (status <> 'draf'::text)) OR ((jenis = 'kp'::text) AND (tahap = 'selesai'::text) AND (status = 'disetujui'::text) AND public.asesor_aktif())));

ALTER TABLE public.pengajuan_berkas ENABLE ROW LEVEL SECURITY;

CREATE POLICY pengajuan_berkas_baca ON public.pengajuan_berkas FOR SELECT TO authenticated USING (((EXISTS ( SELECT 1
   FROM public.pengajuan_mahasiswa p
  WHERE (p.id = pengajuan_berkas.pengajuan_id))) AND ((NOT public.asesor_aktif()) OR (jenis = ANY (ARRAY['laporan_kp'::text, 'surat_selesai'::text])))));

ALTER TABLE public.pengajuan_mahasiswa ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.pengajuan_riwayat ENABLE ROW LEVEL SECURITY;

CREATE POLICY pengajuan_riwayat_baca ON public.pengajuan_riwayat FOR SELECT TO authenticated USING (((EXISTS ( SELECT 1
   FROM public.pengajuan_mahasiswa p
  WHERE (p.id = pengajuan_riwayat.pengajuan_id))) AND (NOT public.asesor_aktif())));

ALTER TABLE public.pengaturan ENABLE ROW LEVEL SECURITY;

CREATE POLICY pengaturan_admin ON public.pengaturan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY pengaturan_baca ON public.pengaturan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY pengaturan_gkm ON public.pengaturan TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.pengelola_prodi ENABLE ROW LEVEL SECURITY;

CREATE POLICY pengelola_prodi_admin ON public.pengelola_prodi TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY pengelola_prodi_baca ON public.pengelola_prodi FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.pengumuman_mahasiswa ENABLE ROW LEVEL SECURITY;

CREATE POLICY pengumuman_mahasiswa_admin ON public.pengumuman_mahasiswa TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY pengumuman_mahasiswa_baca ON public.pengumuman_mahasiswa FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.peringatan_keamanan ENABLE ROW LEVEL SECURITY;

CREATE POLICY peringatan_keamanan_admin ON public.peringatan_keamanan FOR SELECT TO authenticated USING (public.is_admin());

CREATE POLICY portofolio_baca ON public.portofolio_berkas FOR SELECT TO authenticated USING (public.boleh_portofolio_baca(tahun_akademik, semester, kurikulum, kode_mk));

ALTER TABLE public.portofolio_berkas ENABLE ROW LEVEL SECURITY;

CREATE POLICY portofolio_buang ON public.portofolio_berkas FOR DELETE TO authenticated USING (public.boleh_portofolio_tulis(tahun_akademik, semester, kurikulum, kode_mk, kelas));

CREATE POLICY portofolio_tambah ON public.portofolio_berkas FOR INSERT TO authenticated WITH CHECK (public.boleh_portofolio_tulis(tahun_akademik, semester, kurikulum, kode_mk, kelas));

ALTER TABLE public.potret_skor ENABLE ROW LEVEL SECURITY;

CREATE POLICY potret_skor_admin ON public.potret_skor TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY potret_skor_baca ON public.potret_skor FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY potret_skor_gkm ON public.potret_skor TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.profil_prodi ENABLE ROW LEVEL SECURITY;

CREATE POLICY profil_prodi_admin ON public.profil_prodi TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY profil_prodi_baca ON public.profil_prodi FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.rapat ENABLE ROW LEVEL SECURITY;

CREATE POLICY rapat_baca ON public.rapat FOR SELECT TO authenticated USING (((dibuat_oleh = public.me()) OR public.rapat_baca(id)));

CREATE POLICY rapat_hapus ON public.rapat FOR DELETE TO authenticated USING (public.rapat_editor(id));

ALTER TABLE public.rapat_peserta ENABLE ROW LEVEL SECURITY;

CREATE POLICY rapat_peserta_baca ON public.rapat_peserta FOR SELECT TO authenticated USING (((dosen_id = public.me()) OR public.rapat_isi_boleh(rapat_id)));

CREATE POLICY rapat_peserta_ubah ON public.rapat_peserta TO authenticated USING (public.rapat_editor(rapat_id)) WITH CHECK (public.rapat_editor(rapat_id));

CREATE POLICY rapat_tambah ON public.rapat FOR INSERT TO authenticated WITH CHECK ((public.boleh_hibah() AND (dibuat_oleh = public.me())));

ALTER TABLE public.rapat_tindak ENABLE ROW LEVEL SECURITY;

CREATE POLICY rapat_tindak_baca ON public.rapat_tindak FOR SELECT TO authenticated USING (((pj_dosen_id = public.me()) OR public.rapat_isi_boleh(rapat_id)));

CREATE POLICY rapat_tindak_ubah ON public.rapat_tindak TO authenticated USING (public.rapat_editor(rapat_id)) WITH CHECK (public.rapat_editor(rapat_id));

CREATE POLICY rapat_ubah ON public.rapat FOR UPDATE TO authenticated USING (public.rapat_editor(id)) WITH CHECK (public.rapat_editor(id));

CREATE POLICY ref1_baca ON public.ref_kelompok_dana FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY ref2_baca ON public.ref_skema_dana FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY ref3_baca ON public.ref_kategori_publikasi FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ref_bidang_keahlian ENABLE ROW LEVEL SECURITY;

CREATE POLICY ref_bidang_keahlian_admin ON public.ref_bidang_keahlian TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ref_bidang_keahlian_baca ON public.ref_bidang_keahlian FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ref_cpl ENABLE ROW LEVEL SECURITY;

CREATE POLICY ref_cpl_admin ON public.ref_cpl TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ref_cpl_baca ON public.ref_cpl FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ref_cpl_korelasi ENABLE ROW LEVEL SECURITY;

CREATE POLICY ref_cpl_korelasi_admin ON public.ref_cpl_korelasi TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ref_cpl_korelasi_baca ON public.ref_cpl_korelasi FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ref_kata_visi ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ref_kategori_publikasi ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ref_kelompok_dana ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ref_mata_kuliah ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ref_mk_cpl ENABLE ROW LEVEL SECURITY;

CREATE POLICY ref_mk_cpl_admin ON public.ref_mk_cpl TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ref_mk_cpl_baca ON public.ref_mk_cpl FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ref_mk_padanan ENABLE ROW LEVEL SECURITY;

CREATE POLICY ref_mk_padanan_admin ON public.ref_mk_padanan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ref_mk_padanan_baca ON public.ref_mk_padanan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ref_profil_lulusan ENABLE ROW LEVEL SECURITY;

CREATE POLICY ref_profil_lulusan_admin ON public.ref_profil_lulusan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ref_profil_lulusan_baca ON public.ref_profil_lulusan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ref_skema_dana ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ref_tema_peta_jalan ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ref_topik_keahlian ENABLE ROW LEVEL SECURITY;

CREATE POLICY ref_topik_keahlian_admin ON public.ref_topik_keahlian TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY ref_topik_keahlian_baca ON public.ref_topik_keahlian FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.spmi_capaian ENABLE ROW LEVEL SECURITY;

CREATE POLICY spmi_capaian_admin ON public.spmi_capaian TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY spmi_capaian_baca ON public.spmi_capaian FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY spmi_capaian_gkm ON public.spmi_capaian TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.spmi_standar ENABLE ROW LEVEL SECURITY;

CREATE POLICY spmi_standar_admin ON public.spmi_standar TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY spmi_standar_baca ON public.spmi_standar FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY spmi_standar_gkm ON public.spmi_standar TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.spmi_standar_revisi ENABLE ROW LEVEL SECURITY;

CREATE POLICY spmi_standar_revisi_admin ON public.spmi_standar_revisi TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY spmi_standar_revisi_baca ON public.spmi_standar_revisi FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY spmi_standar_revisi_gkm ON public.spmi_standar_revisi TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.status_sistem ENABLE ROW LEVEL SECURITY;

CREATE POLICY status_sistem_baca ON public.status_sistem FOR SELECT TO authenticated USING ((public.is_admin() OR (EXISTS ( SELECT 1
   FROM public.dosen d
  WHERE ((d.id = public.me()) AND (d.peran = 'pimpinan'::text))))));

ALTER TABLE public.survei ENABLE ROW LEVEL SECURITY;

CREATE POLICY survei_admin ON public.survei TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY survei_gkm ON public.survei TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.survei_jawaban ENABLE ROW LEVEL SECURITY;

CREATE POLICY survei_jawaban_admin ON public.survei_jawaban TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY survei_jawaban_gkm ON public.survei_jawaban TO authenticated USING (public.boleh_mutu()) WITH CHECK (public.boleh_mutu());

ALTER TABLE public.ta_arsip ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_arsip_baca ON public.ta_arsip FOR SELECT TO authenticated USING (public.ta_arsip_boleh(nim));

ALTER TABLE public.ta_berkas ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_berkas_baca ON public.ta_berkas FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY ta_berkas_tambah ON public.ta_berkas FOR INSERT TO authenticated WITH CHECK (public.boleh_pengajuan('ta'::text));

CREATE POLICY ta_berkas_ubah ON public.ta_berkas FOR UPDATE TO authenticated USING (public.boleh_pengajuan('ta'::text)) WITH CHECK (public.boleh_pengajuan('ta'::text));

ALTER TABLE public.ta_bimbingan ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_bimbingan_baca ON public.ta_bimbingan FOR SELECT TO authenticated USING (public.ta_bimbingan_boleh(nim));

ALTER TABLE public.ta_kecuali_urutan ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_kecuali_urutan_baca ON public.ta_kecuali_urutan FOR SELECT TO authenticated USING (public.boleh_pengajuan('ta'::text));

ALTER TABLE public.ta_kk_dekat ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_kk_dekat_baca ON public.ta_kk_dekat FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ta_kuota ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_kuota_baca ON public.ta_kuota FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ta_nilai ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_nilai_baca ON public.ta_nilai FOR SELECT TO authenticated USING ((public.boleh_tabel('jadwal_ta'::text) OR (public.ta_panel_saya(jadwal_id) IS NOT NULL)));

ALTER TABLE public.ta_rubrik ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_rubrik_baca ON public.ta_rubrik FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.ta_syarat_bimbingan ENABLE ROW LEVEL SECURITY;

CREATE POLICY ta_syarat_bimbingan_baca ON public.ta_syarat_bimbingan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

CREATE POLICY ta_syarat_bimbingan_ubah ON public.ta_syarat_bimbingan FOR UPDATE TO authenticated USING (public.boleh_pengajuan('ta'::text)) WITH CHECK (public.boleh_pengajuan('ta'::text));

ALTER TABLE public.tanya_jawab ENABLE ROW LEVEL SECURITY;

CREATE POLICY tanya_jawab_admin ON public.tanya_jawab TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY tanya_jawab_baca ON public.tanya_jawab FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.target_baku ENABLE ROW LEVEL SECURITY;

CREATE POLICY target_baku_admin ON public.target_baku TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY target_baku_baca ON public.target_baku FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.target_dosen ENABLE ROW LEVEL SECURITY;

CREATE POLICY target_dosen_admin ON public.target_dosen TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY target_dosen_baca ON public.target_dosen FOR SELECT TO authenticated USING (((dosen_id = public.me()) OR public.lihat_semua_hibah()));

ALTER TABLE public.tautan_ami ENABLE ROW LEVEL SECURITY;

CREATE POLICY tautan_ami_admin ON public.tautan_ami TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY tema_admin ON public.ref_tema_peta_jalan TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY tema_baca ON public.ref_tema_peta_jalan FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.templat_email ENABLE ROW LEVEL SECURITY;

CREATE POLICY templat_email_admin ON public.templat_email TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

ALTER TABLE public.testimoni ENABLE ROW LEVEL SECURITY;

CREATE POLICY testimoni_admin ON public.testimoni TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY testimoni_baca ON public.testimoni FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

ALTER TABLE public.yudisium_berkas ENABLE ROW LEVEL SECURITY;

CREATE POLICY yudisium_berkas_admin ON public.yudisium_berkas TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY yudisium_berkas_baca ON public.yudisium_berkas FOR SELECT TO authenticated USING ((public.me() IS NOT NULL));

-- Hak akses: tabel dan sequence ditulis lengkap (tidak bergantung pada kotak
-- "Grant API access to new tables automatically"), lalu yang dibatasi dari bawaan Supabase
revoke all on function public._terapkan_karya(uuid,jsonb) from public, anon, authenticated;
grant execute on function public._terapkan_karya(uuid,jsonb) to service_role;
revoke all on function public.ajukan_karya(uuid) from public, anon;
grant execute on function public.ajukan_karya(uuid) to authenticated, service_role;
revoke all on function public.akses_masuk_ditutup() from public, anon;
grant execute on function public.akses_masuk_ditutup() to authenticated, service_role;
revoke all on function public.ami_buka(text) from public;
grant execute on function public.ami_buka(text) to anon, authenticated, service_role;
revoke all on function public.ami_portofolio_cakup(text,text) from public, anon, authenticated;
grant execute on function public.ami_portofolio_cakup(text,text) to service_role;
revoke all on function public.asesor_aktif() from public, anon;
grant execute on function public.asesor_aktif() to authenticated, service_role;
revoke all on function public.atur_foto_profil(text) from public, anon;
grant execute on function public.atur_foto_profil(text) to authenticated, service_role;
revoke all on function public.atur_nama_gelar(text) from public, anon;
grant execute on function public.atur_nama_gelar(text) to authenticated, service_role;
revoke all on function public.atur_nip_nuptk(text,text) from public, anon;
grant execute on function public.atur_nip_nuptk(text,text) to authenticated, service_role;
revoke all on function public.beban_bimbingan(integer) from public, anon;
grant execute on function public.beban_bimbingan(integer) to authenticated, service_role;
revoke all on function public.bersihkan_jejak() from public, anon, authenticated;
grant execute on function public.bersihkan_jejak() to service_role;
revoke all on function public.bkd_milik(bigint) from public, anon;
grant execute on function public.bkd_milik(bigint) to authenticated, service_role;
revoke all on function public.boleh_email_alt() from public;
grant execute on function public.boleh_email_alt() to anon, authenticated, service_role;
revoke all on function public.boleh_hibah() from public, anon;
grant execute on function public.boleh_hibah() to authenticated, service_role;
revoke all on function public.boleh_mk(text,text) from public, anon;
grant execute on function public.boleh_mk(text,text) to authenticated, service_role;
revoke all on function public.boleh_mutu() from public, anon;
grant execute on function public.boleh_mutu() to authenticated, service_role;
revoke all on function public.boleh_narasi() from public, anon;
grant execute on function public.boleh_narasi() to authenticated, service_role;
revoke all on function public.boleh_pengajuan(text) from public, anon;
grant execute on function public.boleh_pengajuan(text) to authenticated, service_role;
revoke all on function public.boleh_portofolio_baca(text,text,text,text) from public, anon;
grant execute on function public.boleh_portofolio_baca(text,text,text,text) to authenticated, service_role;
revoke all on function public.boleh_portofolio_tulis(text,text,text,text,text) from public, anon;
grant execute on function public.boleh_portofolio_tulis(text,text,text,text,text) to authenticated, service_role;
revoke all on function public.boleh_rps(text,text) from public, anon;
grant execute on function public.boleh_rps(text,text) to authenticated, service_role;
revoke all on function public.boleh_silabus() from public, anon;
grant execute on function public.boleh_silabus() to authenticated, service_role;
revoke all on function public.boleh_tabel(text) from public, anon;
grant execute on function public.boleh_tabel(text) to authenticated, service_role;
revoke all on function public.cari_sha256(text) from public, anon;
grant execute on function public.cari_sha256(text) to authenticated, service_role;
revoke all on function public.cari_waktu_rapat(uuid[],date,date,bigint) from public, anon;
grant execute on function public.cari_waktu_rapat(uuid[],date,date,bigint) to authenticated, service_role;
revoke all on function public.catat_aktif() from public, anon;
grant execute on function public.catat_aktif() to authenticated, service_role;
revoke all on function public.catat_jejak() from public, anon, authenticated;
grant execute on function public.catat_jejak() to service_role;
revoke all on function public.catat_kunjungan(text) from public, anon;
grant execute on function public.catat_kunjungan(text) to authenticated, service_role;
revoke all on function public.catat_kunjungan_publik(text,text,text) from public;
grant execute on function public.catat_kunjungan_publik(text,text,text) to anon, authenticated, service_role;
revoke all on function public.catat_openalex(jsonb) from public, anon;
grant execute on function public.catat_openalex(jsonb) to authenticated, service_role;
revoke all on function public.catat_terbitan(jsonb) from public, anon;
grant execute on function public.catat_terbitan(jsonb) to authenticated, service_role;
revoke all on function public.catat_topik(jsonb) from public, anon;
grant execute on function public.catat_topik(jsonb) to authenticated, service_role;
revoke all on function public.cpl_belum_semester() from public, anon;
grant execute on function public.cpl_belum_semester() to authenticated, service_role;
revoke all on function public.cpl_belum_tanpa_evaluasi() from public, anon;
grant execute on function public.cpl_belum_tanpa_evaluasi() to authenticated, service_role;
revoke all on function public.cpl_kelas_milik(bigint) from public, anon;
grant execute on function public.cpl_kelas_milik(bigint) to authenticated, service_role;
revoke all on function public.dokumen_mahasiswa() from public;
grant execute on function public.dokumen_mahasiswa() to anon, authenticated, service_role;
revoke all on function public.dosen_mengampu(text) from public, anon;
grant execute on function public.dosen_mengampu(text) to authenticated, service_role;
revoke all on function public.email_saya() from public, anon;
grant execute on function public.email_saya() to authenticated, service_role;
revoke all on function public.evaluasi_perlu_tl() from public, anon;
grant execute on function public.evaluasi_perlu_tl() to authenticated, service_role;
revoke all on function public.hanya_baca() from public, anon;
grant execute on function public.hanya_baca() to authenticated, service_role;
revoke all on function public.hapus_bukti_awal(uuid) from public, anon;
grant execute on function public.hapus_bukti_awal(uuid) to authenticated, service_role;
revoke all on function public.hari_libur_antara(date,date) from public;
grant execute on function public.hari_libur_antara(date,date) to anon, authenticated, service_role;
revoke all on function public.hibah_rekap() from public, anon;
grant execute on function public.hibah_rekap() to authenticated, service_role;
revoke all on function public.id_dosen_login() from public, anon;
grant execute on function public.id_dosen_login() to authenticated, service_role;
revoke all on function public.insentif_ajukan(text,bigint[],text) from public, anon;
grant execute on function public.insentif_ajukan(text,bigint[],text) to authenticated, service_role;
revoke all on function public.insentif_batal(uuid) from public, anon;
grant execute on function public.insentif_batal(uuid) to authenticated, service_role;
revoke all on function public.insentif_berkas_kurang(uuid) from public, anon;
grant execute on function public.insentif_berkas_kurang(uuid) to authenticated, service_role;
revoke all on function public.insentif_hasil(bigint[],text,text) from public, anon;
grant execute on function public.insentif_hasil(bigint[],text,text) to authenticated, service_role;
revoke all on function public.insentif_klaim(uuid) from public, anon;
grant execute on function public.insentif_klaim(uuid) to authenticated, service_role;
revoke all on function public.insentif_periksa(bigint,text,text) from public, anon;
grant execute on function public.insentif_periksa(bigint,text,text) to authenticated, service_role;
revoke all on function public.is_admin() from public, anon;
grant execute on function public.is_admin() to authenticated, service_role;
revoke all on function public.isi_sha256(jsonb) from public, anon;
grant execute on function public.isi_sha256(jsonb) to authenticated, service_role;
revoke all on function public.jadwal_berhalangan_rekap(text,text,date,date) from public, anon;
grant execute on function public.jadwal_berhalangan_rekap(text,text,date,date) to authenticated, service_role;
revoke all on function public.jadwal_impor(text,text,jsonb,boolean) from public, anon;
grant execute on function public.jadwal_impor(text,text,jsonb,boolean) to authenticated, service_role;
revoke all on function public.jadwal_periode_sah(text,text) from public, anon;
grant execute on function public.jadwal_periode_sah(text,text) to authenticated, service_role;
revoke all on function public.jadwal_sahkan(text,text,boolean) from public, anon;
grant execute on function public.jadwal_sahkan(text,text,boolean) to authenticated, service_role;
revoke all on function public.jadwal_simpan(jsonb) from public, anon;
grant execute on function public.jadwal_simpan(jsonb) to authenticated, service_role;
revoke all on function public.jaga_email_alternatif() from public, anon;
grant execute on function public.jaga_email_alternatif() to authenticated, service_role;
revoke all on function public.jaga_mk_rps_tinjauan() from public, anon, authenticated;
grant execute on function public.jaga_mk_rps_tinjauan() to service_role;
revoke all on function public.jumlah_rujukan(text) from public, anon;
grant execute on function public.jumlah_rujukan(text) to authenticated, service_role;
revoke all on function public.keamanan_antrean(text) from public;
grant execute on function public.keamanan_antrean(text) to anon, authenticated, service_role;
revoke all on function public.keamanan_tandai(text,bigint[]) from public;
grant execute on function public.keamanan_tandai(text,bigint[]) to anon, authenticated, service_role;
revoke all on function public.kelas_impor(text,text,jsonb,boolean) from public, anon;
grant execute on function public.kelas_impor(text,text,jsonb,boolean) to authenticated, service_role;
revoke all on function public.kelas_ke_cpl(text,text) from public, anon;
grant execute on function public.kelas_ke_cpl(text,text) to authenticated, service_role;
revoke all on function public.kelas_simpan(jsonb) from public, anon;
grant execute on function public.kelas_simpan(jsonb) to authenticated, service_role;
revoke all on function public.kepala_lab_dari(bigint) from public, anon;
grant execute on function public.kepala_lab_dari(bigint) to authenticated, service_role;
revoke all on function public.kirim_masukan_mahasiswa(text,text,text,text,text) from public;
grant execute on function public.kirim_masukan_mahasiswa(text,text,text,text,text) to anon, authenticated, service_role;
revoke all on function public.koordinator_aktif(text) from public, anon;
grant execute on function public.koordinator_aktif(text) to authenticated, service_role;
revoke all on function public.kp_atur_kuota(integer,uuid,integer) from public, anon;
grant execute on function public.kp_atur_kuota(integer,uuid,integer) to authenticated, service_role;
revoke all on function public.kp_bakukan_instansi(bigint,text,boolean) from public, anon;
grant execute on function public.kp_bakukan_instansi(bigint,text,boolean) to authenticated, service_role;
revoke all on function public.kp_beban(integer) from public, anon;
grant execute on function public.kp_beban(integer) to authenticated, service_role;
revoke all on function public.kp_pelaksanaan_mitra() from public, anon;
grant execute on function public.kp_pelaksanaan_mitra() to authenticated, service_role;
revoke all on function public.kp_rekap_baris() from public, anon;
grant execute on function public.kp_rekap_baris() to authenticated, service_role;
revoke all on function public.kp_tanggal_acuan(public.pengajuan_mahasiswa) from public, anon;
grant execute on function public.kp_tanggal_acuan(public.pengajuan_mahasiswa) to authenticated, service_role;
revoke all on function public.kp_tetapkan_pembimbing(bigint,uuid) from public, anon;
grant execute on function public.kp_tetapkan_pembimbing(bigint,uuid) to authenticated, service_role;
revoke all on function public.kp_tolak_boleh(bigint) from public, anon;
grant execute on function public.kp_tolak_boleh(bigint) to authenticated, service_role;
revoke all on function public.kp_tolak_rekap() from public, anon;
grant execute on function public.kp_tolak_rekap() to authenticated, service_role;
revoke all on function public.kunjungan_publik_rekap(integer) from public;
grant execute on function public.kunjungan_publik_rekap(integer) to anon, authenticated, service_role;
revoke all on function public.lihat_semua_hibah() from public, anon;
grant execute on function public.lihat_semua_hibah() to authenticated, service_role;
revoke all on function public.masa_kuliah_tanggal(date,text,text) from public, anon;
grant execute on function public.masa_kuliah_tanggal(date,text,text) to authenticated, service_role;
revoke all on function public.masukkan_pustaka(text,text,integer,text,text,text) from public, anon;
grant execute on function public.masukkan_pustaka(text,text,integer,text,text,text) to authenticated, service_role;
revoke all on function public.me() from public, anon;
grant execute on function public.me() to authenticated, service_role;
revoke all on function public.mengajar_kelas(text,text,text,text) from public, anon;
grant execute on function public.mengajar_kelas(text,text,text,text) to authenticated, service_role;
revoke all on function public.mengajar_mk(text,text) from public, anon;
grant execute on function public.mengajar_mk(text,text) to authenticated, service_role;
revoke all on function public.mhs_batal(text,text) from public;
grant execute on function public.mhs_batal(text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_berkas(text,text,bigint,boolean) from public;
grant execute on function public.mhs_berkas(text,text,bigint,boolean) to anon, authenticated, service_role;
revoke all on function public.mhs_bimbingan(text) from public;
grant execute on function public.mhs_bimbingan(text) to anon, authenticated, service_role;
revoke all on function public.mhs_bimbingan_hapus(text,bigint) from public;
grant execute on function public.mhs_bimbingan_hapus(text,bigint) to anon, authenticated, service_role;
revoke all on function public.mhs_bimbingan_lampiran(text,text,bigint,text,text) from public;
grant execute on function public.mhs_bimbingan_lampiran(text,text,bigint,text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_bimbingan_lampiran_url(text,text,bigint) from public;
grant execute on function public.mhs_bimbingan_lampiran_url(text,text,bigint) to anon, authenticated, service_role;
revoke all on function public.mhs_bimbingan_simpan(text,bigint,date,text,uuid,text,text) from public;
grant execute on function public.mhs_bimbingan_simpan(text,bigint,date,text,uuid,text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_boleh(public.pengajuan_mahasiswa) from public, anon, authenticated;
grant execute on function public.mhs_boleh(public.pengajuan_mahasiswa) to service_role;
revoke all on function public.mhs_buat(text,text,text,text,text,uuid,jsonb) from public;
grant execute on function public.mhs_buat(text,text,text,text,text,uuid,jsonb) to anon, authenticated, service_role;
revoke all on function public.mhs_cari(text) from public, anon, authenticated;
grant execute on function public.mhs_cari(text) to service_role;
revoke all on function public.mhs_catat_berkas(text,text,text,text,text) from public;
grant execute on function public.mhs_catat_berkas(text,text,text,text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_cek(text,text) from public;
grant execute on function public.mhs_cek(text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_email_alt_jejak() from public, anon, authenticated;
grant execute on function public.mhs_email_alt_jejak() to service_role;
revoke all on function public.mhs_email_alt_konfirmasi(text,text) from public;
grant execute on function public.mhs_email_alt_konfirmasi(text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_email_alt_minta(text,text,text) from public;
grant execute on function public.mhs_email_alt_minta(text,text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_email_alt_rapikan() from public, anon, authenticated;
grant execute on function public.mhs_email_alt_rapikan() to service_role;
revoke all on function public.mhs_email_alt_tujuan(text,text) from public;
grant execute on function public.mhs_email_alt_tujuan(text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_jendela_selesai(public.pengajuan_mahasiswa) from public, anon, authenticated;
grant execute on function public.mhs_jendela_selesai(public.pengajuan_mahasiswa) to service_role;
revoke all on function public.mhs_jenis_berkas_sah(public.pengajuan_mahasiswa,text) from public, anon, authenticated;
grant execute on function public.mhs_jenis_berkas_sah(public.pengajuan_mahasiswa,text) to service_role;
revoke all on function public.mhs_judul(text,jsonb) from public, anon, authenticated;
grant execute on function public.mhs_judul(text,jsonb) to service_role;
revoke all on function public.mhs_kirim(text) from public;
grant execute on function public.mhs_kirim(text) to anon, authenticated, service_role;
revoke all on function public.mhs_kirim_selesai(text) from public;
grant execute on function public.mhs_kirim_selesai(text) to anon, authenticated, service_role;
revoke all on function public.mhs_kunci_sah(text) from public, anon, authenticated;
grant execute on function public.mhs_kunci_sah(text) to service_role;
revoke all on function public.mhs_kunci_tahap(public.pengajuan_mahasiswa) from public, anon, authenticated;
grant execute on function public.mhs_kunci_tahap(public.pengajuan_mahasiswa) to service_role;
revoke all on function public.mhs_lihat(text) from public;
grant execute on function public.mhs_lihat(text) to anon, authenticated, service_role;
revoke all on function public.mhs_pemeriksa(text,bigint,integer,integer) from public;
grant execute on function public.mhs_pemeriksa(text,bigint,integer,integer) to anon, authenticated, service_role;
revoke all on function public.mhs_pemeriksa_antrean(text,integer,integer) from public;
grant execute on function public.mhs_pemeriksa_antrean(text,integer,integer) to anon, authenticated, service_role;
revoke all on function public.mhs_pemeriksa_tandai(text,bigint,text,integer) from public;
grant execute on function public.mhs_pemeriksa_tandai(text,bigint,text,integer) to anon, authenticated, service_role;
revoke all on function public.mhs_pratinjau_admin(bigint) from public, anon;
grant execute on function public.mhs_pratinjau_admin(bigint) to authenticated, service_role;
revoke all on function public.mhs_rapikan(text,jsonb) from public, anon, authenticated;
grant execute on function public.mhs_rapikan(text,jsonb) to service_role;
revoke all on function public.mhs_rapikan_selesai(jsonb) from public, anon, authenticated;
grant execute on function public.mhs_rapikan_selesai(jsonb) to service_role;
revoke all on function public.mhs_tautan_berkas(text,text,text,text) from public;
grant execute on function public.mhs_tautan_berkas(text,text,text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_tautan_id(text,bigint) from public;
grant execute on function public.mhs_tautan_id(text,bigint) to anon, authenticated, service_role;
revoke all on function public.mhs_tautan_ulang(text,text) from public;
grant execute on function public.mhs_tautan_ulang(text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_terima_instansi(text,text) from public;
grant execute on function public.mhs_terima_instansi(text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_tingkat_kabar(public.pengajuan_mahasiswa) from public, anon, authenticated;
grant execute on function public.mhs_tingkat_kabar(public.pengajuan_mahasiswa) to service_role;
revoke all on function public.mhs_tingkat_tempo(public.pengajuan_mahasiswa,integer,integer) from public, anon, authenticated;
grant execute on function public.mhs_tingkat_tempo(public.pengajuan_mahasiswa,integer,integer) to service_role;
revoke all on function public.mhs_token_baru() from public, anon, authenticated;
grant execute on function public.mhs_token_baru() to service_role;
revoke all on function public.mhs_tolak_instansi(text,text) from public;
grant execute on function public.mhs_tolak_instansi(text,text) to anon, authenticated, service_role;
revoke all on function public.mhs_ubah(text,text,uuid,jsonb) from public;
grant execute on function public.mhs_ubah(text,text,uuid,jsonb) to anon, authenticated, service_role;
revoke all on function public.mhs_ubah_selesai(text,jsonb) from public;
grant execute on function public.mhs_ubah_selesai(text,jsonb) to anon, authenticated, service_role;
revoke all on function public.mhs_waktu_tahap(public.pengajuan_mahasiswa) from public, anon, authenticated;
grant execute on function public.mhs_waktu_tahap(public.pengajuan_mahasiswa) to service_role;
revoke all on function public.mk_atur_pengampu(text,text,text[]) from public, anon;
grant execute on function public.mk_atur_pengampu(text,text,text[]) to authenticated, service_role;
revoke all on function public.mk_atur_tim(text,text,text,text[]) from public, anon;
grant execute on function public.mk_atur_tim(text,text,text,text[]) to authenticated, service_role;
revoke all on function public.mk_boleh_saya() from public, anon;
grant execute on function public.mk_boleh_saya() to authenticated, service_role;
revoke all on function public.mk_simpan_rps(text,text,text,boolean) from public, anon, authenticated;
grant execute on function public.mk_simpan_rps(text,text,text,boolean) to service_role;
revoke all on function public.nidn_saya() from public, anon;
grant execute on function public.nidn_saya() to authenticated, service_role;
revoke all on function public.padanan_catat(text,text,text,text,integer) from public, anon, authenticated;
grant execute on function public.padanan_catat(text,text,text,text,integer) to service_role;
revoke all on function public.padanan_kembalikan(text,text,text) from public, anon;
grant execute on function public.padanan_kembalikan(text,text,text) to authenticated, service_role;
revoke all on function public.padanan_sahkan(text,text,text) from public, anon;
grant execute on function public.padanan_sahkan(text,text,text) to authenticated, service_role;
revoke all on function public.padanan_salinan(text,text) from public, anon;
grant execute on function public.padanan_salinan(text,text) to authenticated, service_role;
revoke all on function public.padanan_tetapkan(text,text,text) from public, anon;
grant execute on function public.padanan_tetapkan(text,text,text) to authenticated, service_role;
revoke all on function public.pasang_jaga_hanya_baca() from public, anon, authenticated;
grant execute on function public.pasang_jaga_hanya_baca() to service_role;
revoke all on function public.pasang_jejak() from public, anon, authenticated;
grant execute on function public.pasang_jejak() to service_role;
revoke all on function public.pasang_jejak_evaluasi() from public, anon, authenticated;
grant execute on function public.pasang_jejak_evaluasi() to service_role;
revoke all on function public.pasang_jejak_spmi() from public, anon, authenticated;
grant execute on function public.pasang_jejak_spmi() to service_role;
revoke all on function public.pasang_jejak_target() from public, anon, authenticated;
grant execute on function public.pasang_jejak_target() to service_role;
revoke all on function public.pejabat_aktif(text) from public, anon;
grant execute on function public.pejabat_aktif(text) to authenticated, service_role;
revoke all on function public.pemakaian_rekap(integer) from public, anon;
grant execute on function public.pemakaian_rekap(integer) to authenticated, service_role;
revoke all on function public.pembimbing_pilihan() from public;
grant execute on function public.pembimbing_pilihan() to anon, authenticated, service_role;
revoke all on function public.pembimbing_pilihan_ta() from public;
grant execute on function public.pembimbing_pilihan_ta() to anon, authenticated, service_role;
revoke all on function public.pengajuan_batalkan(bigint,text) from public, anon;
grant execute on function public.pengajuan_batalkan(bigint,text) to authenticated, service_role;
revoke all on function public.pengajuan_catat_berkas(bigint,text,text,text) from public, anon;
grant execute on function public.pengajuan_catat_berkas(bigint,text,text,text) to authenticated, service_role;
revoke all on function public.pengajuan_jadwalkan(bigint,date,text,text,text,text[],text) from public, anon;
grant execute on function public.pengajuan_jadwalkan(bigint,date,text,text,text,text[],text) to authenticated, service_role;
revoke all on function public.pengajuan_putuskan(bigint,text,text) from public, anon;
grant execute on function public.pengajuan_putuskan(bigint,text,text) to authenticated, service_role;
revoke all on function public.pengampu_evaluasi(bigint) from public, anon;
grant execute on function public.pengampu_evaluasi(bigint) to authenticated, service_role;
revoke all on function public.pengampu_kelas_mk(text,text,text,text) from public, anon;
grant execute on function public.pengampu_kelas_mk(text,text,text,text) to authenticated, service_role;
revoke all on function public.pengatur_jadwal() from public, anon;
grant execute on function public.pengatur_jadwal() to authenticated, service_role;
revoke all on function public.pengatur_kelas() from public, anon;
grant execute on function public.pengatur_kelas() to authenticated, service_role;
revoke all on function public.pengelola_insentif() from public, anon;
grant execute on function public.pengelola_insentif() to authenticated, service_role;
revoke all on function public.pengumuman_mahasiswa_aktif() from public;
grant execute on function public.pengumuman_mahasiswa_aktif() to anon, authenticated, service_role;
revoke all on function public.penulis_karya(uuid) from public, anon;
grant execute on function public.penulis_karya(uuid) to authenticated, service_role;
revoke all on function public.perbarui_tindak_lanjut(bigint,text,text) from public, anon;
grant execute on function public.perbarui_tindak_lanjut(bigint,text,text) to authenticated, service_role;
revoke all on function public.periksa_keamanan() from public, anon, authenticated;
grant execute on function public.periksa_keamanan() to service_role;
revoke all on function public.portofolio_ringkas() from public, anon;
grant execute on function public.portofolio_ringkas() to authenticated, service_role;
revoke all on function public.portofolio_url(bigint) from public, anon;
grant execute on function public.portofolio_url(bigint) to authenticated, service_role;
revoke all on function public.prestasi_belum_verifikasi(bigint) from public, anon;
grant execute on function public.prestasi_belum_verifikasi(bigint) to authenticated, service_role;
revoke all on function public.prestasi_milik(bigint) from public, anon;
grant execute on function public.prestasi_milik(bigint) to authenticated, service_role;
revoke all on function public.prestasi_mirip(integer) from public, anon;
grant execute on function public.prestasi_mirip(integer) to authenticated, service_role;
revoke all on function public.rapat_baca(bigint) from public, anon;
grant execute on function public.rapat_baca(bigint) to authenticated, service_role;
revoke all on function public.rapat_buka_hadir(text) from public;
grant execute on function public.rapat_buka_hadir(text) to anon, authenticated, service_role;
revoke all on function public.rapat_editor(bigint) from public, anon;
grant execute on function public.rapat_editor(bigint) to authenticated, service_role;
revoke all on function public.rapat_hadir(text,uuid,text,text,uuid) from public;
grant execute on function public.rapat_hadir(text,uuid,text,text,uuid) to anon, authenticated, service_role;
revoke all on function public.rapat_isi(bigint) from public, anon;
grant execute on function public.rapat_isi(bigint) to authenticated, service_role;
revoke all on function public.rapat_isi_boleh(bigint) from public, anon;
grant execute on function public.rapat_isi_boleh(bigint) to authenticated, service_role;
revoke all on function public.rapikan_kata_kunci(jsonb) from public, anon;
grant execute on function public.rapikan_kata_kunci(jsonb) to authenticated, service_role;
revoke all on function public.rapikan_tautan_lain(jsonb) from public, anon;
grant execute on function public.rapikan_tautan_lain(jsonb) to authenticated, service_role;
revoke all on function public.rapikan_topik_keahlian(jsonb) from public, anon;
grant execute on function public.rapikan_topik_keahlian(jsonb) to authenticated, service_role;
revoke all on function public.rbk_prodi() from public, anon;
grant execute on function public.rbk_prodi() to authenticated, service_role;
revoke all on function public.rekap_evaluasi() from public, anon;
grant execute on function public.rekap_evaluasi() to authenticated, service_role;
revoke all on function public.rps_ajukan(text,text,text) from public, anon;
grant execute on function public.rps_ajukan(text,text,text) to authenticated, service_role;
revoke all on function public.rps_b_berubah() from public, anon, authenticated;
grant execute on function public.rps_b_berubah() to service_role;
revoke all on function public.rps_boleh_saya() from public, anon;
grant execute on function public.rps_boleh_saya() to authenticated, service_role;
revoke all on function public.rps_dokumen(uuid) from public;
grant execute on function public.rps_dokumen(uuid) to anon, authenticated, service_role;
revoke all on function public.rps_pasang_tautan(text,text,text) from public, anon;
grant execute on function public.rps_pasang_tautan(text,text,text) to authenticated, service_role;
revoke all on function public.rps_putuskan(text,text,text,text,text) from public, anon;
grant execute on function public.rps_putuskan(text,text,text,text,text) to authenticated, service_role;
revoke all on function public.rps_review_batal(text,text,uuid) from public, anon;
grant execute on function public.rps_review_batal(text,text,uuid) to authenticated, service_role;
revoke all on function public.rps_review_hari() from public, anon;
grant execute on function public.rps_review_hari() to authenticated, service_role;
revoke all on function public.rps_review_mk(text,text) from public, anon;
grant execute on function public.rps_review_mk(text,text) to authenticated, service_role;
revoke all on function public.rps_review_rekap() from public, anon;
grant execute on function public.rps_review_rekap() to authenticated, service_role;
revoke all on function public.rps_review_simpan(text,text,jsonb,jsonb,text,text,boolean) from public, anon;
grant execute on function public.rps_review_simpan(text,text,jsonb,jsonb,text,text,boolean) to authenticated, service_role;
revoke all on function public.rps_review_tanggapi(text,text,uuid,jsonb,text) from public, anon;
grant execute on function public.rps_review_tanggapi(text,text,uuid,jsonb,text) to authenticated, service_role;
revoke all on function public.rps_review_tunjuk(text,text,uuid) from public, anon;
grant execute on function public.rps_review_tunjuk(text,text,uuid) to authenticated, service_role;
revoke all on function public.rps_review_undangan(text,text,uuid) from public, anon;
grant execute on function public.rps_review_undangan(text,text,uuid) to authenticated, service_role;
revoke all on function public.rps_tetapkan(text,text) from public, anon;
grant execute on function public.rps_tetapkan(text,text) to authenticated, service_role;
revoke all on function public.rps_unggah_ttd(text,text,text,text) from public, anon;
grant execute on function public.rps_unggah_ttd(text,text,text,text) to authenticated, service_role;
revoke all on function public.rps_verifikasi(uuid) from public;
grant execute on function public.rps_verifikasi(uuid) to anon, authenticated, service_role;
revoke all on function public.satukan_berkas(text,text[]) from public, anon;
grant execute on function public.satukan_berkas(text,text[]) to authenticated, service_role;
revoke all on function public.saya_dtps() from public, anon;
grant execute on function public.saya_dtps() to authenticated, service_role;
revoke all on function public.sebutan_pada(uuid,text,timestamp with time zone) from public, anon;
grant execute on function public.sebutan_pada(uuid,text,timestamp with time zone) to authenticated, service_role;
revoke all on function public.semester_akhir(integer,text) from public;
grant execute on function public.semester_akhir(integer,text) to anon, authenticated, service_role;
revoke all on function public.semester_awal(integer,text) from public;
grant execute on function public.semester_awal(integer,text) to anon, authenticated, service_role;
revoke all on function public.setujui_ajuan_bkd(bigint) from public, anon;
grant execute on function public.setujui_ajuan_bkd(bigint) to authenticated, service_role;
revoke all on function public.setujui_ajuan_prestasi(bigint) from public, anon;
grant execute on function public.setujui_ajuan_prestasi(bigint) to authenticated, service_role;
revoke all on function public.setujui_ajuan_ubah(bigint) from public, anon;
grant execute on function public.setujui_ajuan_ubah(bigint) to authenticated, service_role;
revoke all on function public.silabus_ajukan(text,text,text) from public, anon;
grant execute on function public.silabus_ajukan(text,text,text) to authenticated, service_role;
revoke all on function public.silabus_impor(text,jsonb) from public, anon;
grant execute on function public.silabus_impor(text,jsonb) to authenticated, service_role;
revoke all on function public.silabus_putuskan(text,text,text,text) from public, anon;
grant execute on function public.silabus_putuskan(text,text,text,text) to authenticated, service_role;
revoke all on function public.silabus_simpan(text,text,jsonb) from public, anon;
grant execute on function public.silabus_simpan(text,text,jsonb) to authenticated, service_role;
revoke all on function public.sistem_kesehatan() from public, anon;
grant execute on function public.sistem_kesehatan() to authenticated, service_role;
revoke all on function public.sistem_kesehatan_kunci(text) from public;
grant execute on function public.sistem_kesehatan_kunci(text) to anon, authenticated, service_role;
revoke all on function public.sistem_lapor(text,text,boolean,jsonb) from public;
grant execute on function public.sistem_lapor(text,text,boolean,jsonb) to anon, authenticated, service_role;
revoke all on function public.sistem_periksa() from public, anon, authenticated;
grant execute on function public.sistem_periksa() to service_role;
revoke all on function public.survei_buka(text) from public;
grant execute on function public.survei_buka(text) to anon, authenticated, service_role;
revoke all on function public.survei_kirim(text,uuid,jsonb,jsonb) from public;
grant execute on function public.survei_kirim(text,uuid,jsonb,jsonb) to anon, authenticated, service_role;
revoke all on function public.survei_rekap() from public;
grant execute on function public.survei_rekap() to anon, authenticated, service_role;
revoke all on function public.survei_rekap_hitung(bigint) from public, anon, authenticated;
grant execute on function public.survei_rekap_hitung(bigint) to service_role;
revoke all on function public.survei_tarik_terbit(bigint) from public, anon;
grant execute on function public.survei_tarik_terbit(bigint) to authenticated, service_role;
revoke all on function public.survei_terbitkan(bigint) from public, anon;
grant execute on function public.survei_terbitkan(bigint) to authenticated, service_role;
revoke all on function public.ta_arsip_boleh(text) from public, anon;
grant execute on function public.ta_arsip_boleh(text) to authenticated, service_role;
revoke all on function public.ta_arsip_catat(text,text) from public, anon;
grant execute on function public.ta_arsip_catat(text,text) to authenticated, service_role;
revoke all on function public.ta_arsip_siap() from public, anon;
grant execute on function public.ta_arsip_siap() to authenticated, service_role;
revoke all on function public.ta_arsip_url(text) from public, anon;
grant execute on function public.ta_arsip_url(text) to authenticated, service_role;
revoke all on function public.ta_atur_kuota(integer,text,uuid,integer) from public, anon;
grant execute on function public.ta_atur_kuota(integer,text,uuid,integer) to authenticated, service_role;
revoke all on function public.ta_ba_buka(bigint,text) from public, anon;
grant execute on function public.ta_ba_buka(bigint,text) to authenticated, service_role;
revoke all on function public.ta_ba_tetapkan(bigint,text,date,text) from public, anon;
grant execute on function public.ta_ba_tetapkan(bigint,text,date,text) to authenticated, service_role;
revoke all on function public.ta_beban(integer,text) from public, anon;
grant execute on function public.ta_beban(integer,text) to authenticated, service_role;
revoke all on function public.ta_berkas_daftar() from public;
grant execute on function public.ta_berkas_daftar() to anon, authenticated, service_role;
revoke all on function public.ta_bimbingan_boleh(text) from public, anon;
grant execute on function public.ta_bimbingan_boleh(text) to authenticated, service_role;
revoke all on function public.ta_bimbingan_konfirmasi(bigint[],boolean,text) from public, anon;
grant execute on function public.ta_bimbingan_konfirmasi(bigint[],boolean,text) to authenticated, service_role;
revoke all on function public.ta_bimbingan_menunggu() from public, anon;
grant execute on function public.ta_bimbingan_menunggu() to authenticated, service_role;
revoke all on function public.ta_bimbingan_rekap() from public, anon;
grant execute on function public.ta_bimbingan_rekap() to authenticated, service_role;
revoke all on function public.ta_bimbingan_sah(text,timestamp with time zone) from public, anon;
grant execute on function public.ta_bimbingan_sah(text,timestamp with time zone) to authenticated, service_role;
revoke all on function public.ta_ganti_pembimbing(bigint,uuid,uuid,text,text) from public, anon;
grant execute on function public.ta_ganti_pembimbing(bigint,uuid,uuid,text,text) to authenticated, service_role;
revoke all on function public.ta_jaga_ba() from public, anon, authenticated;
grant execute on function public.ta_jaga_ba() to service_role;
revoke all on function public.ta_jaga_urutan() from public, anon, authenticated;
grant execute on function public.ta_jaga_urutan() to service_role;
revoke all on function public.ta_kecualikan_urutan(text,text,text) from public, anon;
grant execute on function public.ta_kecualikan_urutan(text,text,text) to authenticated, service_role;
revoke all on function public.ta_kk_cocok(text,text) from public, anon;
grant execute on function public.ta_kk_cocok(text,text) to authenticated, service_role;
revoke all on function public.ta_lampiran_dihapus(text,bigint) from public;
grant execute on function public.ta_lampiran_dihapus(text,bigint) to anon, authenticated, service_role;
revoke all on function public.ta_lampiran_kedaluwarsa(text) from public;
grant execute on function public.ta_lampiran_kedaluwarsa(text) to anon, authenticated, service_role;
revoke all on function public.ta_lulus_pada(text) from public, anon;
grant execute on function public.ta_lulus_pada(text) to authenticated, service_role;
revoke all on function public.ta_lulus_ta(text) from public, anon;
grant execute on function public.ta_lulus_ta(text) to authenticated, service_role;
revoke all on function public.ta_nilai_hapus(bigint) from public, anon;
grant execute on function public.ta_nilai_hapus(bigint) to authenticated, service_role;
revoke all on function public.ta_nilai_hitung(bigint) from public, anon, authenticated;
grant execute on function public.ta_nilai_hitung(bigint) to service_role;
revoke all on function public.ta_nilai_rekap(bigint) from public, anon;
grant execute on function public.ta_nilai_rekap(bigint) to authenticated, service_role;
revoke all on function public.ta_nilai_simpan(bigint,jsonb,text,text,text,text) from public, anon;
grant execute on function public.ta_nilai_simpan(bigint,jsonb,text,text,text,text) to authenticated, service_role;
revoke all on function public.ta_nilai_tugas() from public, anon;
grant execute on function public.ta_nilai_tugas() to authenticated, service_role;
revoke all on function public.ta_panel_saya(bigint) from public, anon;
grant execute on function public.ta_panel_saya(bigint) to authenticated, service_role;
revoke all on function public.ta_pembimbing_nim(text) from public, anon;
grant execute on function public.ta_pembimbing_nim(text) to authenticated, service_role;
revoke all on function public.ta_periksa_berkas() from public, anon, authenticated;
grant execute on function public.ta_periksa_berkas() to service_role;
revoke all on function public.ta_periksa_bimbingan() from public, anon, authenticated;
grant execute on function public.ta_periksa_bimbingan() to service_role;
revoke all on function public.ta_revisi_selesai(bigint,boolean) from public, anon;
grant execute on function public.ta_revisi_selesai(bigint,boolean) to authenticated, service_role;
revoke all on function public.ta_rubrik_bersih(jsonb,text) from public, anon, authenticated;
grant execute on function public.ta_rubrik_bersih(jsonb,text) to service_role;
revoke all on function public.ta_rubrik_jadwal(public.jadwal_ta) from public, anon, authenticated;
grant execute on function public.ta_rubrik_jadwal(public.jadwal_ta) to service_role;
revoke all on function public.ta_rubrik_simpan(text,jsonb,numeric,numeric,numeric[],text,numeric,jsonb) from public, anon;
grant execute on function public.ta_rubrik_simpan(text,jsonb,numeric,numeric,numeric[],text,numeric,jsonb) to authenticated, service_role;
revoke all on function public.ta_siup_tandai(bigint[],boolean) from public, anon;
grant execute on function public.ta_siup_tandai(bigint[],boolean) to authenticated, service_role;
revoke all on function public.ta_syarat_bimbingan_hitung(text,text) from public, anon, authenticated;
grant execute on function public.ta_syarat_bimbingan_hitung(text,text) to service_role;
revoke all on function public.ta_syarat_urutan(text,text) from public, anon, authenticated;
grant execute on function public.ta_syarat_urutan(text,text) to service_role;
revoke all on function public.ta_tetapkan_pembimbing(bigint,uuid,uuid,text) from public, anon;
grant execute on function public.ta_tetapkan_pembimbing(bigint,uuid,uuid,text) to authenticated, service_role;
revoke all on function public.tanya_jawab_publik() from public;
grant execute on function public.tanya_jawab_publik() to anon, authenticated, service_role;
revoke all on function public.tim_hibah(uuid) from public, anon;
grant execute on function public.tim_hibah(uuid) to authenticated, service_role;
revoke all on function public.tinjauan_ajukan(bigint) from public, anon;
grant execute on function public.tinjauan_ajukan(bigint) to authenticated, service_role;
revoke all on function public.tinjauan_boleh(text,text,text,text) from public, anon;
grant execute on function public.tinjauan_boleh(text,text,text,text) to authenticated, service_role;
revoke all on function public.tinjauan_nilai_ada(text,text,text,text) from public, anon;
grant execute on function public.tinjauan_nilai_ada(text,text,text,text) to authenticated, service_role;
revoke all on function public.tinjauan_putuskan(bigint,text,text) from public, anon;
grant execute on function public.tinjauan_putuskan(bigint,text,text) to authenticated, service_role;
revoke all on function public.tinjauan_sasaran(text,text) from public, anon;
grant execute on function public.tinjauan_sasaran(text,text) to authenticated, service_role;
revoke all on function public.ubah_karya(uuid,jsonb) from public, anon;
grant execute on function public.ubah_karya(uuid,jsonb) to authenticated, service_role;
revoke all on function public.unsur_bukti() from public, anon;
grant execute on function public.unsur_bukti() to authenticated, service_role;
revoke all on function public.yudisium_berkas_daftar() from public;
grant execute on function public.yudisium_berkas_daftar() to anon, authenticated, service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_bkd to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_bkd to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_bkd to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_hapus to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_hapus to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_hapus to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_prestasi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_prestasi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_prestasi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_ubah to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_ubah to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ajuan_ubah to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ami_temuan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ami_temuan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ami_temuan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.berhalangan_konfirmasi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.berhalangan_konfirmasi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.butir_bukti to anon;
grant select, insert, update, delete, truncate, references, trigger on public.butir_bukti to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.butir_bukti to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_berkas to anon;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_berkas to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_berkas to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_kelas to anon;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_kelas to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_kelas to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_ringkasan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_ringkasan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.cpl_ringkasan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.dokumen to anon;
grant select, insert, update, delete, truncate, references, trigger on public.dokumen to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.dokumen to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.dosen to anon;
grant select, insert, update, delete, truncate, references, trigger on public.dosen to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.dosen to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_ampu_ts to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_ampu_ts to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_berhalangan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_berhalangan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_berhalangan_rentang to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_berhalangan_rentang to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_berhalangan_tgl to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.dosen_berhalangan_tgl to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.evaluasi_mk to anon;
grant select, insert, update, delete, truncate, references, trigger on public.evaluasi_mk to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.evaluasi_mk to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.evaluasi_tindak to anon;
grant select, insert, update, delete, truncate, references, trigger on public.evaluasi_tindak to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.evaluasi_tindak to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.hari_libur to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.hari_libur to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_ajuan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_ajuan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_ajuan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_panggilan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_panggilan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_panggilan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_tim to anon;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_tim to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.hibah_tim to service_role;
grant select, truncate, references, trigger on public.insentif_pengajuan to anon;
grant select, truncate, references, trigger on public.insentif_pengajuan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.insentif_pengajuan to service_role;
grant select, truncate, references, trigger on public.insentif_publikasi to anon;
grant select, truncate, references, trigger on public.insentif_publikasi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.insentif_publikasi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_hari to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_hari to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_kuliah to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_kuliah to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_kuliah_sah to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_kuliah_sah to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_slot to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_slot to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_ta to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.jadwal_ta to service_role;
grant select, references, trigger on public.jejak to anon;
grant select, references, trigger on public.jejak to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.jejak to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kabar_kegiatan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.kabar_kegiatan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kabar_kegiatan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kalender_akademik to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kalender_akademik to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.karya to anon;
grant select, insert, update, delete, truncate, references, trigger on public.karya to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.karya to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.karya_bukti to anon;
grant select, insert, update, delete, truncate, references, trigger on public.karya_bukti to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.karya_bukti to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.karya_mahasiswa to anon;
grant select, insert, update, delete, truncate, references, trigger on public.karya_mahasiswa to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.karya_mahasiswa to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.karya_mitra to anon;
grant select, insert, update, delete, truncate, references, trigger on public.karya_mitra to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.karya_mitra to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.karya_penulis to anon;
grant select, insert, update, delete, truncate, references, trigger on public.karya_penulis to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.karya_penulis to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.karya_sitasi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.karya_sitasi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.karya_sitasi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kegiatan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.kegiatan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kegiatan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kegiatan_dosen to anon;
grant select, insert, update, delete, truncate, references, trigger on public.kegiatan_dosen to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kegiatan_dosen to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kelas_dosen to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kelas_dosen to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kelas_kuliah to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kelas_kuliah to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.koordinator to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.koordinator to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kp_instansi_keputusan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kp_instansi_keputusan to service_role;
grant select, truncate, references, trigger on public.kp_kuota to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kp_kuota to service_role;
grant select, truncate, references, trigger on public.kp_tolak_instansi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.kp_tolak_instansi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.kunjungan_publik to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.laboratorium to anon;
grant select, insert, update, delete, truncate, references, trigger on public.laboratorium to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.laboratorium to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.layanan_kunci to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.led_narasi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.led_narasi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.led_narasi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.led_penugasan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.led_penugasan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.led_penugasan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.led_tim to anon;
grant select, insert, update, delete, truncate, references, trigger on public.led_tim to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.led_tim to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bimbingan_utama to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bimbingan_utama to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bimbingan_utama to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bkd to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bkd to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bkd to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bukti to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bukti to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_bukti to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_dokumen_k3l to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_dokumen_k3l to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_dokumen_k3l to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_fasilitas_k3l to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_fasilitas_k3l to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_fasilitas_k3l to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kepuasan_pengguna to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kepuasan_pengguna to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kepuasan_pengguna to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kerjasama to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kerjasama to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kerjasama to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_keuangan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_keuangan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_keuangan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kohort_lulusan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kohort_lulusan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_kohort_lulusan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_luaran_mahasiswa to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_luaran_mahasiswa to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_luaran_mahasiswa to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_mahasiswa_angkatan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_mahasiswa_angkatan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_mahasiswa_angkatan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_mahasiswa_ta to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_mahasiswa_ta to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_mahasiswa_ta to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_penggunaan_dana to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_penggunaan_dana to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_penggunaan_dana to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_peta_jalan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_peta_jalan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_peta_jalan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prasarana to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prasarana to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prasarana to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prestasi_mahasiswa to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prestasi_mahasiswa to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prestasi_mahasiswa to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prodi_upps to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prodi_upps to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_prodi_upps to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_publikasi_mahasiswa to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_publikasi_mahasiswa to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_publikasi_mahasiswa to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_sarana_standar to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_sarana_standar to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_sarana_standar to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_spmi_ppepp to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_spmi_ppepp to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_spmi_ppepp to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_target_kinerja to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_target_kinerja to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_target_kinerja to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_tendik to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_tendik to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_tendik to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_tracer_lulusan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_tracer_lulusan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_tracer_lulusan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_vmts to anon;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_vmts to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.lkps_vmts to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.masukan_mahasiswa to anon;
grant select, insert, update, delete, truncate, references, trigger on public.masukan_mahasiswa to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.masukan_mahasiswa to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.mhs_email_alt to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mhs_email_alt to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.mhs_email_alt_riwayat to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mhs_email_alt_riwayat to service_role;
grant select, truncate, references, trigger on public.mk_padanan_sah to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_padanan_sah to service_role;
grant select, truncate, references, trigger on public.mk_padanan_sah_log to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_padanan_sah_log to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps to service_role;
grant select, truncate, references, trigger on public.mk_rps_pengesahan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps_pengesahan to service_role;
grant select, truncate, references, trigger on public.mk_rps_review to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps_review to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps_riwayat to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps_riwayat to service_role;
grant select, insert, update, truncate, references, trigger on public.mk_rps_tinjauan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps_tinjauan to service_role;
grant select, truncate, references, trigger on public.mk_rps_tinjauan_log to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps_tinjauan_log to service_role;
grant select, truncate, references, trigger on public.mk_rps_ttd to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_rps_ttd to service_role;
grant select, truncate, references, trigger on public.mk_silabus to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_silabus to service_role;
grant select, truncate, references, trigger on public.mk_silabus_log to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_silabus_log to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.mk_struktur to anon;
grant select, insert, update, delete, truncate, references, trigger on public.mk_struktur to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_struktur to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.mk_struktur_riwayat to anon;
grant select, insert, update, delete, truncate, references, trigger on public.mk_struktur_riwayat to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.mk_struktur_riwayat to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.pemakaian_halaman to service_role;
grant select, truncate, references, trigger on public.pengajuan_berkas to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.pengajuan_berkas to service_role;
grant select, truncate, references, trigger on public.pengajuan_mahasiswa to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.pengajuan_mahasiswa to service_role;
grant select, truncate, references, trigger on public.pengajuan_riwayat to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.pengajuan_riwayat to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.pengaturan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.pengaturan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.pengaturan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.pengelola_prodi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.pengelola_prodi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.pengelola_prodi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.pengumuman_mahasiswa to anon;
grant select, insert, update, delete, truncate, references, trigger on public.pengumuman_mahasiswa to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.pengumuman_mahasiswa to service_role;
grant select, references, trigger on public.peringatan_keamanan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.peringatan_keamanan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.portofolio_berkas to anon;
grant select, insert, update, delete, truncate, references, trigger on public.portofolio_berkas to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.portofolio_berkas to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.potret_skor to anon;
grant select, insert, update, delete, truncate, references, trigger on public.potret_skor to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.potret_skor to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.profil_prodi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.profil_prodi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.profil_prodi to service_role;
grant insert, update, delete, truncate, references, trigger on public.rapat to anon;
grant insert, update, delete, truncate, references, trigger on public.rapat to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.rapat to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.rapat_peserta to anon;
grant select, insert, update, delete, truncate, references, trigger on public.rapat_peserta to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.rapat_peserta to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.rapat_tindak to anon;
grant select, insert, update, delete, truncate, references, trigger on public.rapat_tindak to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.rapat_tindak to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_bidang_keahlian to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_bidang_keahlian to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_bidang_keahlian to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_cpl to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_cpl to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_cpl_korelasi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_cpl_korelasi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kata_visi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kata_visi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kata_visi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kategori_publikasi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kategori_publikasi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kategori_publikasi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kelompok_dana to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kelompok_dana to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_kelompok_dana to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_mata_kuliah to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_mata_kuliah to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_mata_kuliah to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_mk_cpl to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_mk_cpl to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_mk_padanan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_mk_padanan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_profil_lulusan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_profil_lulusan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_profil_lulusan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_skema_dana to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_skema_dana to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_skema_dana to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_tema_peta_jalan to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_tema_peta_jalan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_tema_peta_jalan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.ref_topik_keahlian to anon;
grant select, insert, update, delete, truncate, references, trigger on public.ref_topik_keahlian to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ref_topik_keahlian to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_capaian to anon;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_capaian to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_capaian to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_standar to anon;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_standar to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_standar to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_standar_revisi to anon;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_standar_revisi to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.spmi_standar_revisi to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.status_sistem to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.status_sistem to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.survei to anon;
grant select, insert, update, delete, truncate, references, trigger on public.survei to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.survei to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.survei_jawaban to anon;
grant select, insert, update, delete, truncate, references, trigger on public.survei_jawaban to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.survei_jawaban to service_role;
grant select, references, trigger on public.ta_arsip to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_arsip to service_role;
grant select, insert, update, references, trigger on public.ta_berkas to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_berkas to service_role;
grant select, references, trigger on public.ta_bimbingan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_bimbingan to service_role;
grant select, references, trigger on public.ta_kecuali_urutan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_kecuali_urutan to service_role;
grant select, truncate, references, trigger on public.ta_kk_dekat to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_kk_dekat to service_role;
grant select, truncate, references, trigger on public.ta_kuota to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_kuota to service_role;
grant select, references, trigger on public.ta_nilai to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_nilai to service_role;
grant select, references, trigger on public.ta_rubrik to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_rubrik to service_role;
grant select, update, references, trigger on public.ta_syarat_bimbingan to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.ta_syarat_bimbingan to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.tanya_jawab to anon;
grant select, insert, update, delete, truncate, references, trigger on public.tanya_jawab to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.tanya_jawab to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.target_baku to anon;
grant select, insert, update, delete, truncate, references, trigger on public.target_baku to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.target_baku to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.target_dosen to anon;
grant select, insert, update, delete, truncate, references, trigger on public.target_dosen to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.target_dosen to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.tautan_ami to anon;
grant select, insert, update, delete, truncate, references, trigger on public.tautan_ami to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.tautan_ami to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.templat_email to anon;
grant select, insert, update, delete, truncate, references, trigger on public.templat_email to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.templat_email to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.testimoni to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.testimoni to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.v_mahasiswa_terlibat to anon;
grant select, insert, update, delete, truncate, references, trigger on public.v_mahasiswa_terlibat to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.v_mahasiswa_terlibat to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.v_mitra to anon;
grant select, insert, update, delete, truncate, references, trigger on public.v_mitra to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.v_mitra to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.v_penulis_utama to anon;
grant select, insert, update, delete, truncate, references, trigger on public.v_penulis_utama to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.v_penulis_utama to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.v_rekap_karya to anon;
grant select, insert, update, delete, truncate, references, trigger on public.v_rekap_karya to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.v_rekap_karya to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.v_rekap_skema to anon;
grant select, insert, update, delete, truncate, references, trigger on public.v_rekap_skema to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.v_rekap_skema to service_role;
grant select, insert, update, delete, truncate, references, trigger on public.yudisium_berkas to authenticated;
grant select, insert, update, delete, truncate, references, trigger on public.yudisium_berkas to service_role;
grant usage, select, update on sequence public.ajuan_bkd_id_seq to anon;
grant usage, select, update on sequence public.ajuan_bkd_id_seq to authenticated;
grant usage, select, update on sequence public.ajuan_bkd_id_seq to service_role;
grant usage, select, update on sequence public.ajuan_hapus_id_seq to anon;
grant usage, select, update on sequence public.ajuan_hapus_id_seq to authenticated;
grant usage, select, update on sequence public.ajuan_hapus_id_seq to service_role;
grant usage, select, update on sequence public.ajuan_prestasi_id_seq to anon;
grant usage, select, update on sequence public.ajuan_prestasi_id_seq to authenticated;
grant usage, select, update on sequence public.ajuan_prestasi_id_seq to service_role;
grant usage, select, update on sequence public.ajuan_ubah_id_seq to anon;
grant usage, select, update on sequence public.ajuan_ubah_id_seq to authenticated;
grant usage, select, update on sequence public.ajuan_ubah_id_seq to service_role;
grant usage, select, update on sequence public.ami_temuan_id_seq to anon;
grant usage, select, update on sequence public.ami_temuan_id_seq to authenticated;
grant usage, select, update on sequence public.ami_temuan_id_seq to service_role;
grant usage, select, update on sequence public.butir_bukti_id_seq to anon;
grant usage, select, update on sequence public.butir_bukti_id_seq to authenticated;
grant usage, select, update on sequence public.butir_bukti_id_seq to service_role;
grant usage, select, update on sequence public.cpl_berkas_id_seq to anon;
grant usage, select, update on sequence public.cpl_berkas_id_seq to authenticated;
grant usage, select, update on sequence public.cpl_berkas_id_seq to service_role;
grant usage, select, update on sequence public.cpl_kelas_id_seq to anon;
grant usage, select, update on sequence public.cpl_kelas_id_seq to authenticated;
grant usage, select, update on sequence public.cpl_kelas_id_seq to service_role;
grant usage, select, update on sequence public.cpl_ringkasan_id_seq to anon;
grant usage, select, update on sequence public.cpl_ringkasan_id_seq to authenticated;
grant usage, select, update on sequence public.cpl_ringkasan_id_seq to service_role;
grant usage, select, update on sequence public.dokumen_id_seq to anon;
grant usage, select, update on sequence public.dokumen_id_seq to authenticated;
grant usage, select, update on sequence public.dokumen_id_seq to service_role;
grant usage, select, update on sequence public.dosen_berhalangan_id_seq to anon;
grant usage, select, update on sequence public.dosen_berhalangan_id_seq to authenticated;
grant usage, select, update on sequence public.dosen_berhalangan_id_seq to service_role;
grant usage, select, update on sequence public.dosen_berhalangan_rentang_id_seq to anon;
grant usage, select, update on sequence public.dosen_berhalangan_rentang_id_seq to authenticated;
grant usage, select, update on sequence public.dosen_berhalangan_rentang_id_seq to service_role;
grant usage, select, update on sequence public.dosen_berhalangan_tgl_id_seq to anon;
grant usage, select, update on sequence public.dosen_berhalangan_tgl_id_seq to authenticated;
grant usage, select, update on sequence public.dosen_berhalangan_tgl_id_seq to service_role;
grant usage, select, update on sequence public.evaluasi_mk_id_seq to anon;
grant usage, select, update on sequence public.evaluasi_mk_id_seq to authenticated;
grant usage, select, update on sequence public.evaluasi_mk_id_seq to service_role;
grant usage, select, update on sequence public.evaluasi_tindak_id_seq to anon;
grant usage, select, update on sequence public.evaluasi_tindak_id_seq to authenticated;
grant usage, select, update on sequence public.evaluasi_tindak_id_seq to service_role;
grant usage, select, update on sequence public.hibah_panggilan_id_seq to anon;
grant usage, select, update on sequence public.hibah_panggilan_id_seq to authenticated;
grant usage, select, update on sequence public.hibah_panggilan_id_seq to service_role;
grant usage, select, update on sequence public.insentif_pengajuan_id_seq to anon;
grant usage, select, update on sequence public.insentif_pengajuan_id_seq to authenticated;
grant usage, select, update on sequence public.insentif_pengajuan_id_seq to service_role;
grant usage, select, update on sequence public.insentif_publikasi_id_seq to anon;
grant usage, select, update on sequence public.insentif_publikasi_id_seq to authenticated;
grant usage, select, update on sequence public.insentif_publikasi_id_seq to service_role;
grant usage, select, update on sequence public.jadwal_slot_id_seq to anon;
grant usage, select, update on sequence public.jadwal_slot_id_seq to authenticated;
grant usage, select, update on sequence public.jadwal_slot_id_seq to service_role;
grant usage, select, update on sequence public.jadwal_ta_id_seq to anon;
grant usage, select, update on sequence public.jadwal_ta_id_seq to authenticated;
grant usage, select, update on sequence public.jadwal_ta_id_seq to service_role;
grant usage, select, update on sequence public.jejak_id_seq to anon;
grant usage, select, update on sequence public.jejak_id_seq to authenticated;
grant usage, select, update on sequence public.jejak_id_seq to service_role;
grant usage, select, update on sequence public.kabar_kegiatan_id_seq to anon;
grant usage, select, update on sequence public.kabar_kegiatan_id_seq to authenticated;
grant usage, select, update on sequence public.kabar_kegiatan_id_seq to service_role;
grant usage, select, update on sequence public.kalender_akademik_id_seq to anon;
grant usage, select, update on sequence public.kalender_akademik_id_seq to authenticated;
grant usage, select, update on sequence public.kalender_akademik_id_seq to service_role;
grant usage, select, update on sequence public.karya_bukti_id_seq to anon;
grant usage, select, update on sequence public.karya_bukti_id_seq to authenticated;
grant usage, select, update on sequence public.karya_bukti_id_seq to service_role;
grant usage, select, update on sequence public.kegiatan_id_seq to anon;
grant usage, select, update on sequence public.kegiatan_id_seq to authenticated;
grant usage, select, update on sequence public.kegiatan_id_seq to service_role;
grant usage, select, update on sequence public.kelas_kuliah_id_seq to anon;
grant usage, select, update on sequence public.kelas_kuliah_id_seq to authenticated;
grant usage, select, update on sequence public.kelas_kuliah_id_seq to service_role;
grant usage, select, update on sequence public.koordinator_id_seq to anon;
grant usage, select, update on sequence public.koordinator_id_seq to authenticated;
grant usage, select, update on sequence public.koordinator_id_seq to service_role;
grant usage, select, update on sequence public.kp_kuota_id_seq to anon;
grant usage, select, update on sequence public.kp_kuota_id_seq to authenticated;
grant usage, select, update on sequence public.kp_kuota_id_seq to service_role;
grant usage, select, update on sequence public.kp_tolak_instansi_id_seq to anon;
grant usage, select, update on sequence public.kp_tolak_instansi_id_seq to authenticated;
grant usage, select, update on sequence public.kp_tolak_instansi_id_seq to service_role;
grant usage, select, update on sequence public.laboratorium_id_seq to anon;
grant usage, select, update on sequence public.laboratorium_id_seq to authenticated;
grant usage, select, update on sequence public.laboratorium_id_seq to service_role;
grant usage, select, update on sequence public.led_tim_id_seq to anon;
grant usage, select, update on sequence public.led_tim_id_seq to authenticated;
grant usage, select, update on sequence public.led_tim_id_seq to service_role;
grant usage, select, update on sequence public.lkps_bimbingan_utama_id_seq to anon;
grant usage, select, update on sequence public.lkps_bimbingan_utama_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_bimbingan_utama_id_seq to service_role;
grant usage, select, update on sequence public.lkps_bkd_id_seq to anon;
grant usage, select, update on sequence public.lkps_bkd_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_bkd_id_seq to service_role;
grant usage, select, update on sequence public.lkps_bukti_id_seq to anon;
grant usage, select, update on sequence public.lkps_bukti_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_bukti_id_seq to service_role;
grant usage, select, update on sequence public.lkps_dokumen_k3l_id_seq to anon;
grant usage, select, update on sequence public.lkps_dokumen_k3l_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_dokumen_k3l_id_seq to service_role;
grant usage, select, update on sequence public.lkps_fasilitas_k3l_id_seq to anon;
grant usage, select, update on sequence public.lkps_fasilitas_k3l_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_fasilitas_k3l_id_seq to service_role;
grant usage, select, update on sequence public.lkps_kepuasan_pengguna_id_seq to anon;
grant usage, select, update on sequence public.lkps_kepuasan_pengguna_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_kepuasan_pengguna_id_seq to service_role;
grant usage, select, update on sequence public.lkps_kerjasama_id_seq to anon;
grant usage, select, update on sequence public.lkps_kerjasama_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_kerjasama_id_seq to service_role;
grant usage, select, update on sequence public.lkps_keuangan_id_seq to anon;
grant usage, select, update on sequence public.lkps_keuangan_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_keuangan_id_seq to service_role;
grant usage, select, update on sequence public.lkps_kohort_lulusan_id_seq to anon;
grant usage, select, update on sequence public.lkps_kohort_lulusan_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_kohort_lulusan_id_seq to service_role;
grant usage, select, update on sequence public.lkps_luaran_mahasiswa_id_seq to anon;
grant usage, select, update on sequence public.lkps_luaran_mahasiswa_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_luaran_mahasiswa_id_seq to service_role;
grant usage, select, update on sequence public.lkps_mahasiswa_angkatan_id_seq to anon;
grant usage, select, update on sequence public.lkps_mahasiswa_angkatan_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_mahasiswa_angkatan_id_seq to service_role;
grant usage, select, update on sequence public.lkps_mahasiswa_ta_id_seq to anon;
grant usage, select, update on sequence public.lkps_mahasiswa_ta_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_mahasiswa_ta_id_seq to service_role;
grant usage, select, update on sequence public.lkps_penggunaan_dana_id_seq to anon;
grant usage, select, update on sequence public.lkps_penggunaan_dana_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_penggunaan_dana_id_seq to service_role;
grant usage, select, update on sequence public.lkps_peta_jalan_id_seq to anon;
grant usage, select, update on sequence public.lkps_peta_jalan_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_peta_jalan_id_seq to service_role;
grant usage, select, update on sequence public.lkps_prasarana_id_seq to anon;
grant usage, select, update on sequence public.lkps_prasarana_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_prasarana_id_seq to service_role;
grant usage, select, update on sequence public.lkps_prestasi_mahasiswa_id_seq to anon;
grant usage, select, update on sequence public.lkps_prestasi_mahasiswa_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_prestasi_mahasiswa_id_seq to service_role;
grant usage, select, update on sequence public.lkps_prodi_upps_id_seq to anon;
grant usage, select, update on sequence public.lkps_prodi_upps_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_prodi_upps_id_seq to service_role;
grant usage, select, update on sequence public.lkps_publikasi_mahasiswa_id_seq to anon;
grant usage, select, update on sequence public.lkps_publikasi_mahasiswa_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_publikasi_mahasiswa_id_seq to service_role;
grant usage, select, update on sequence public.lkps_sarana_standar_id_seq to anon;
grant usage, select, update on sequence public.lkps_sarana_standar_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_sarana_standar_id_seq to service_role;
grant usage, select, update on sequence public.lkps_spmi_ppepp_id_seq to anon;
grant usage, select, update on sequence public.lkps_spmi_ppepp_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_spmi_ppepp_id_seq to service_role;
grant usage, select, update on sequence public.lkps_target_kinerja_id_seq to anon;
grant usage, select, update on sequence public.lkps_target_kinerja_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_target_kinerja_id_seq to service_role;
grant usage, select, update on sequence public.lkps_tendik_id_seq to anon;
grant usage, select, update on sequence public.lkps_tendik_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_tendik_id_seq to service_role;
grant usage, select, update on sequence public.lkps_tracer_lulusan_id_seq to anon;
grant usage, select, update on sequence public.lkps_tracer_lulusan_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_tracer_lulusan_id_seq to service_role;
grant usage, select, update on sequence public.lkps_vmts_id_seq to anon;
grant usage, select, update on sequence public.lkps_vmts_id_seq to authenticated;
grant usage, select, update on sequence public.lkps_vmts_id_seq to service_role;
grant usage, select, update on sequence public.masukan_mahasiswa_id_seq to anon;
grant usage, select, update on sequence public.masukan_mahasiswa_id_seq to authenticated;
grant usage, select, update on sequence public.masukan_mahasiswa_id_seq to service_role;
grant usage, select, update on sequence public.mhs_email_alt_riwayat_id_seq to anon;
grant usage, select, update on sequence public.mhs_email_alt_riwayat_id_seq to authenticated;
grant usage, select, update on sequence public.mhs_email_alt_riwayat_id_seq to service_role;
grant usage, select, update on sequence public.mk_padanan_sah_log_id_seq to anon;
grant usage, select, update on sequence public.mk_padanan_sah_log_id_seq to authenticated;
grant usage, select, update on sequence public.mk_padanan_sah_log_id_seq to service_role;
grant usage, select, update on sequence public.mk_rps_pengesahan_id_seq to anon;
grant usage, select, update on sequence public.mk_rps_pengesahan_id_seq to authenticated;
grant usage, select, update on sequence public.mk_rps_pengesahan_id_seq to service_role;
grant usage, select, update on sequence public.mk_rps_review_id_seq to anon;
grant usage, select, update on sequence public.mk_rps_review_id_seq to authenticated;
grant usage, select, update on sequence public.mk_rps_review_id_seq to service_role;
grant usage, select, update on sequence public.mk_rps_riwayat_id_seq to anon;
grant usage, select, update on sequence public.mk_rps_riwayat_id_seq to authenticated;
grant usage, select, update on sequence public.mk_rps_riwayat_id_seq to service_role;
grant usage, select, update on sequence public.mk_rps_tinjauan_id_seq to anon;
grant usage, select, update on sequence public.mk_rps_tinjauan_id_seq to authenticated;
grant usage, select, update on sequence public.mk_rps_tinjauan_id_seq to service_role;
grant usage, select, update on sequence public.mk_rps_tinjauan_log_id_seq to anon;
grant usage, select, update on sequence public.mk_rps_tinjauan_log_id_seq to authenticated;
grant usage, select, update on sequence public.mk_rps_tinjauan_log_id_seq to service_role;
grant usage, select, update on sequence public.mk_rps_ttd_id_seq to anon;
grant usage, select, update on sequence public.mk_rps_ttd_id_seq to authenticated;
grant usage, select, update on sequence public.mk_rps_ttd_id_seq to service_role;
grant usage, select, update on sequence public.mk_silabus_log_id_seq to anon;
grant usage, select, update on sequence public.mk_silabus_log_id_seq to authenticated;
grant usage, select, update on sequence public.mk_silabus_log_id_seq to service_role;
grant usage, select, update on sequence public.mk_struktur_riwayat_id_seq to anon;
grant usage, select, update on sequence public.mk_struktur_riwayat_id_seq to authenticated;
grant usage, select, update on sequence public.mk_struktur_riwayat_id_seq to service_role;
grant usage, select, update on sequence public.pengajuan_berkas_id_seq to anon;
grant usage, select, update on sequence public.pengajuan_berkas_id_seq to authenticated;
grant usage, select, update on sequence public.pengajuan_berkas_id_seq to service_role;
grant usage, select, update on sequence public.pengajuan_mahasiswa_id_seq to anon;
grant usage, select, update on sequence public.pengajuan_mahasiswa_id_seq to authenticated;
grant usage, select, update on sequence public.pengajuan_mahasiswa_id_seq to service_role;
grant usage, select, update on sequence public.pengajuan_riwayat_id_seq to anon;
grant usage, select, update on sequence public.pengajuan_riwayat_id_seq to authenticated;
grant usage, select, update on sequence public.pengajuan_riwayat_id_seq to service_role;
grant usage, select, update on sequence public.pengelola_prodi_id_seq to anon;
grant usage, select, update on sequence public.pengelola_prodi_id_seq to authenticated;
grant usage, select, update on sequence public.pengelola_prodi_id_seq to service_role;
grant usage, select, update on sequence public.pengumuman_mahasiswa_id_seq to anon;
grant usage, select, update on sequence public.pengumuman_mahasiswa_id_seq to authenticated;
grant usage, select, update on sequence public.pengumuman_mahasiswa_id_seq to service_role;
grant usage, select, update on sequence public.peringatan_keamanan_id_seq to anon;
grant usage, select, update on sequence public.peringatan_keamanan_id_seq to authenticated;
grant usage, select, update on sequence public.peringatan_keamanan_id_seq to service_role;
grant usage, select, update on sequence public.portofolio_berkas_id_seq to anon;
grant usage, select, update on sequence public.portofolio_berkas_id_seq to authenticated;
grant usage, select, update on sequence public.portofolio_berkas_id_seq to service_role;
grant usage, select, update on sequence public.potret_skor_id_seq to anon;
grant usage, select, update on sequence public.potret_skor_id_seq to authenticated;
grant usage, select, update on sequence public.potret_skor_id_seq to service_role;
grant usage, select, update on sequence public.rapat_id_seq to anon;
grant usage, select, update on sequence public.rapat_id_seq to authenticated;
grant usage, select, update on sequence public.rapat_id_seq to service_role;
grant usage, select, update on sequence public.rapat_peserta_id_seq to anon;
grant usage, select, update on sequence public.rapat_peserta_id_seq to authenticated;
grant usage, select, update on sequence public.rapat_peserta_id_seq to service_role;
grant usage, select, update on sequence public.rapat_tindak_id_seq to anon;
grant usage, select, update on sequence public.rapat_tindak_id_seq to authenticated;
grant usage, select, update on sequence public.rapat_tindak_id_seq to service_role;
grant usage, select, update on sequence public.ref_bidang_keahlian_id_seq to anon;
grant usage, select, update on sequence public.ref_bidang_keahlian_id_seq to authenticated;
grant usage, select, update on sequence public.ref_bidang_keahlian_id_seq to service_role;
grant usage, select, update on sequence public.ref_cpl_id_seq to anon;
grant usage, select, update on sequence public.ref_cpl_id_seq to authenticated;
grant usage, select, update on sequence public.ref_cpl_id_seq to service_role;
grant usage, select, update on sequence public.ref_cpl_korelasi_id_seq to anon;
grant usage, select, update on sequence public.ref_cpl_korelasi_id_seq to authenticated;
grant usage, select, update on sequence public.ref_cpl_korelasi_id_seq to service_role;
grant usage, select, update on sequence public.ref_mata_kuliah_id_seq to anon;
grant usage, select, update on sequence public.ref_mata_kuliah_id_seq to authenticated;
grant usage, select, update on sequence public.ref_mata_kuliah_id_seq to service_role;
grant usage, select, update on sequence public.ref_mk_cpl_id_seq to anon;
grant usage, select, update on sequence public.ref_mk_cpl_id_seq to authenticated;
grant usage, select, update on sequence public.ref_mk_cpl_id_seq to service_role;
grant usage, select, update on sequence public.ref_mk_padanan_id_seq to anon;
grant usage, select, update on sequence public.ref_mk_padanan_id_seq to authenticated;
grant usage, select, update on sequence public.ref_mk_padanan_id_seq to service_role;
grant usage, select, update on sequence public.ref_profil_lulusan_id_seq to anon;
grant usage, select, update on sequence public.ref_profil_lulusan_id_seq to authenticated;
grant usage, select, update on sequence public.ref_profil_lulusan_id_seq to service_role;
grant usage, select, update on sequence public.ref_tema_peta_jalan_id_seq to anon;
grant usage, select, update on sequence public.ref_tema_peta_jalan_id_seq to authenticated;
grant usage, select, update on sequence public.ref_tema_peta_jalan_id_seq to service_role;
grant usage, select, update on sequence public.ref_topik_keahlian_id_seq to anon;
grant usage, select, update on sequence public.ref_topik_keahlian_id_seq to authenticated;
grant usage, select, update on sequence public.ref_topik_keahlian_id_seq to service_role;
grant usage, select, update on sequence public.spmi_standar_id_seq to anon;
grant usage, select, update on sequence public.spmi_standar_id_seq to authenticated;
grant usage, select, update on sequence public.spmi_standar_id_seq to service_role;
grant usage, select, update on sequence public.spmi_standar_revisi_id_seq to anon;
grant usage, select, update on sequence public.spmi_standar_revisi_id_seq to authenticated;
grant usage, select, update on sequence public.spmi_standar_revisi_id_seq to service_role;
grant usage, select, update on sequence public.survei_id_seq to anon;
grant usage, select, update on sequence public.survei_id_seq to authenticated;
grant usage, select, update on sequence public.survei_id_seq to service_role;
grant usage, select, update on sequence public.survei_jawaban_id_seq to anon;
grant usage, select, update on sequence public.survei_jawaban_id_seq to authenticated;
grant usage, select, update on sequence public.survei_jawaban_id_seq to service_role;
grant usage, select, update on sequence public.ta_bimbingan_id_seq to anon;
grant usage, select, update on sequence public.ta_bimbingan_id_seq to authenticated;
grant usage, select, update on sequence public.ta_bimbingan_id_seq to service_role;
grant usage, select, update on sequence public.ta_kecuali_urutan_id_seq to anon;
grant usage, select, update on sequence public.ta_kecuali_urutan_id_seq to authenticated;
grant usage, select, update on sequence public.ta_kecuali_urutan_id_seq to service_role;
grant usage, select, update on sequence public.ta_kuota_id_seq to anon;
grant usage, select, update on sequence public.ta_kuota_id_seq to authenticated;
grant usage, select, update on sequence public.ta_kuota_id_seq to service_role;
grant usage, select, update on sequence public.ta_nilai_id_seq to anon;
grant usage, select, update on sequence public.ta_nilai_id_seq to authenticated;
grant usage, select, update on sequence public.ta_nilai_id_seq to service_role;
grant usage, select, update on sequence public.ta_rubrik_id_seq to anon;
grant usage, select, update on sequence public.ta_rubrik_id_seq to authenticated;
grant usage, select, update on sequence public.ta_rubrik_id_seq to service_role;
grant usage, select, update on sequence public.tanya_jawab_id_seq to anon;
grant usage, select, update on sequence public.tanya_jawab_id_seq to authenticated;
grant usage, select, update on sequence public.tanya_jawab_id_seq to service_role;
grant usage, select, update on sequence public.tautan_ami_id_seq to anon;
grant usage, select, update on sequence public.tautan_ami_id_seq to authenticated;
grant usage, select, update on sequence public.tautan_ami_id_seq to service_role;
grant usage, select, update on sequence public.testimoni_id_seq to anon;
grant usage, select, update on sequence public.testimoni_id_seq to authenticated;
grant usage, select, update on sequence public.testimoni_id_seq to service_role;
revoke delete on public.berhalangan_konfirmasi from anon;
revoke insert on public.berhalangan_konfirmasi from anon;
revoke references on public.berhalangan_konfirmasi from anon;
revoke select on public.berhalangan_konfirmasi from anon;
revoke trigger on public.berhalangan_konfirmasi from anon;
revoke truncate on public.berhalangan_konfirmasi from anon;
revoke update on public.berhalangan_konfirmasi from anon;
revoke delete on public.dosen_ampu_ts from anon;
revoke insert on public.dosen_ampu_ts from anon;
revoke references on public.dosen_ampu_ts from anon;
revoke select on public.dosen_ampu_ts from anon;
revoke trigger on public.dosen_ampu_ts from anon;
revoke truncate on public.dosen_ampu_ts from anon;
revoke update on public.dosen_ampu_ts from anon;
revoke delete on public.dosen_berhalangan from anon;
revoke insert on public.dosen_berhalangan from anon;
revoke references on public.dosen_berhalangan from anon;
revoke select on public.dosen_berhalangan from anon;
revoke trigger on public.dosen_berhalangan from anon;
revoke truncate on public.dosen_berhalangan from anon;
revoke update on public.dosen_berhalangan from anon;
revoke delete on public.dosen_berhalangan_rentang from anon;
revoke insert on public.dosen_berhalangan_rentang from anon;
revoke references on public.dosen_berhalangan_rentang from anon;
revoke select on public.dosen_berhalangan_rentang from anon;
revoke trigger on public.dosen_berhalangan_rentang from anon;
revoke truncate on public.dosen_berhalangan_rentang from anon;
revoke update on public.dosen_berhalangan_rentang from anon;
revoke delete on public.dosen_berhalangan_tgl from anon;
revoke insert on public.dosen_berhalangan_tgl from anon;
revoke references on public.dosen_berhalangan_tgl from anon;
revoke select on public.dosen_berhalangan_tgl from anon;
revoke trigger on public.dosen_berhalangan_tgl from anon;
revoke truncate on public.dosen_berhalangan_tgl from anon;
revoke update on public.dosen_berhalangan_tgl from anon;
revoke delete on public.hari_libur from anon;
revoke insert on public.hari_libur from anon;
revoke references on public.hari_libur from anon;
revoke select on public.hari_libur from anon;
revoke trigger on public.hari_libur from anon;
revoke truncate on public.hari_libur from anon;
revoke update on public.hari_libur from anon;
revoke delete on public.insentif_pengajuan from anon;
revoke insert on public.insentif_pengajuan from anon;
revoke update on public.insentif_pengajuan from anon;
revoke delete on public.insentif_pengajuan from authenticated;
revoke insert on public.insentif_pengajuan from authenticated;
revoke update on public.insentif_pengajuan from authenticated;
revoke delete on public.insentif_publikasi from anon;
revoke insert on public.insentif_publikasi from anon;
revoke update on public.insentif_publikasi from anon;
revoke delete on public.insentif_publikasi from authenticated;
revoke insert on public.insentif_publikasi from authenticated;
revoke update on public.insentif_publikasi from authenticated;
revoke delete on public.jadwal_hari from anon;
revoke insert on public.jadwal_hari from anon;
revoke references on public.jadwal_hari from anon;
revoke select on public.jadwal_hari from anon;
revoke trigger on public.jadwal_hari from anon;
revoke truncate on public.jadwal_hari from anon;
revoke update on public.jadwal_hari from anon;
revoke delete on public.jadwal_kuliah from anon;
revoke insert on public.jadwal_kuliah from anon;
revoke references on public.jadwal_kuliah from anon;
revoke select on public.jadwal_kuliah from anon;
revoke trigger on public.jadwal_kuliah from anon;
revoke truncate on public.jadwal_kuliah from anon;
revoke update on public.jadwal_kuliah from anon;
revoke delete on public.jadwal_kuliah_sah from anon;
revoke insert on public.jadwal_kuliah_sah from anon;
revoke references on public.jadwal_kuliah_sah from anon;
revoke select on public.jadwal_kuliah_sah from anon;
revoke trigger on public.jadwal_kuliah_sah from anon;
revoke truncate on public.jadwal_kuliah_sah from anon;
revoke update on public.jadwal_kuliah_sah from anon;
revoke delete on public.jadwal_slot from anon;
revoke insert on public.jadwal_slot from anon;
revoke references on public.jadwal_slot from anon;
revoke select on public.jadwal_slot from anon;
revoke trigger on public.jadwal_slot from anon;
revoke truncate on public.jadwal_slot from anon;
revoke update on public.jadwal_slot from anon;
revoke delete on public.jadwal_ta from anon;
revoke insert on public.jadwal_ta from anon;
revoke references on public.jadwal_ta from anon;
revoke select on public.jadwal_ta from anon;
revoke trigger on public.jadwal_ta from anon;
revoke truncate on public.jadwal_ta from anon;
revoke update on public.jadwal_ta from anon;
revoke delete on public.jejak from anon;
revoke insert on public.jejak from anon;
revoke truncate on public.jejak from anon;
revoke update on public.jejak from anon;
revoke delete on public.jejak from authenticated;
revoke insert on public.jejak from authenticated;
revoke truncate on public.jejak from authenticated;
revoke update on public.jejak from authenticated;
revoke delete on public.kalender_akademik from anon;
revoke insert on public.kalender_akademik from anon;
revoke references on public.kalender_akademik from anon;
revoke select on public.kalender_akademik from anon;
revoke trigger on public.kalender_akademik from anon;
revoke truncate on public.kalender_akademik from anon;
revoke update on public.kalender_akademik from anon;
revoke delete on public.kelas_dosen from anon;
revoke insert on public.kelas_dosen from anon;
revoke references on public.kelas_dosen from anon;
revoke select on public.kelas_dosen from anon;
revoke trigger on public.kelas_dosen from anon;
revoke truncate on public.kelas_dosen from anon;
revoke update on public.kelas_dosen from anon;
revoke delete on public.kelas_kuliah from anon;
revoke insert on public.kelas_kuliah from anon;
revoke references on public.kelas_kuliah from anon;
revoke select on public.kelas_kuliah from anon;
revoke trigger on public.kelas_kuliah from anon;
revoke truncate on public.kelas_kuliah from anon;
revoke update on public.kelas_kuliah from anon;
revoke delete on public.koordinator from anon;
revoke insert on public.koordinator from anon;
revoke references on public.koordinator from anon;
revoke select on public.koordinator from anon;
revoke trigger on public.koordinator from anon;
revoke truncate on public.koordinator from anon;
revoke update on public.koordinator from anon;
revoke delete on public.kp_instansi_keputusan from anon;
revoke insert on public.kp_instansi_keputusan from anon;
revoke references on public.kp_instansi_keputusan from anon;
revoke select on public.kp_instansi_keputusan from anon;
revoke trigger on public.kp_instansi_keputusan from anon;
revoke truncate on public.kp_instansi_keputusan from anon;
revoke update on public.kp_instansi_keputusan from anon;
revoke delete on public.kp_kuota from anon;
revoke insert on public.kp_kuota from anon;
revoke references on public.kp_kuota from anon;
revoke select on public.kp_kuota from anon;
revoke trigger on public.kp_kuota from anon;
revoke truncate on public.kp_kuota from anon;
revoke update on public.kp_kuota from anon;
revoke delete on public.kp_kuota from authenticated;
revoke insert on public.kp_kuota from authenticated;
revoke update on public.kp_kuota from authenticated;
revoke delete on public.kp_tolak_instansi from anon;
revoke insert on public.kp_tolak_instansi from anon;
revoke references on public.kp_tolak_instansi from anon;
revoke select on public.kp_tolak_instansi from anon;
revoke trigger on public.kp_tolak_instansi from anon;
revoke truncate on public.kp_tolak_instansi from anon;
revoke update on public.kp_tolak_instansi from anon;
revoke delete on public.kp_tolak_instansi from authenticated;
revoke insert on public.kp_tolak_instansi from authenticated;
revoke update on public.kp_tolak_instansi from authenticated;
revoke delete on public.kunjungan_publik from anon;
revoke insert on public.kunjungan_publik from anon;
revoke references on public.kunjungan_publik from anon;
revoke select on public.kunjungan_publik from anon;
revoke trigger on public.kunjungan_publik from anon;
revoke truncate on public.kunjungan_publik from anon;
revoke update on public.kunjungan_publik from anon;
revoke delete on public.kunjungan_publik from authenticated;
revoke insert on public.kunjungan_publik from authenticated;
revoke references on public.kunjungan_publik from authenticated;
revoke select on public.kunjungan_publik from authenticated;
revoke trigger on public.kunjungan_publik from authenticated;
revoke truncate on public.kunjungan_publik from authenticated;
revoke update on public.kunjungan_publik from authenticated;
revoke delete on public.layanan_kunci from anon;
revoke insert on public.layanan_kunci from anon;
revoke references on public.layanan_kunci from anon;
revoke select on public.layanan_kunci from anon;
revoke trigger on public.layanan_kunci from anon;
revoke truncate on public.layanan_kunci from anon;
revoke update on public.layanan_kunci from anon;
revoke delete on public.layanan_kunci from authenticated;
revoke insert on public.layanan_kunci from authenticated;
revoke references on public.layanan_kunci from authenticated;
revoke select on public.layanan_kunci from authenticated;
revoke trigger on public.layanan_kunci from authenticated;
revoke truncate on public.layanan_kunci from authenticated;
revoke update on public.layanan_kunci from authenticated;
revoke delete on public.mhs_email_alt from anon;
revoke insert on public.mhs_email_alt from anon;
revoke references on public.mhs_email_alt from anon;
revoke select on public.mhs_email_alt from anon;
revoke trigger on public.mhs_email_alt from anon;
revoke truncate on public.mhs_email_alt from anon;
revoke update on public.mhs_email_alt from anon;
revoke delete on public.mhs_email_alt_riwayat from anon;
revoke insert on public.mhs_email_alt_riwayat from anon;
revoke references on public.mhs_email_alt_riwayat from anon;
revoke select on public.mhs_email_alt_riwayat from anon;
revoke trigger on public.mhs_email_alt_riwayat from anon;
revoke truncate on public.mhs_email_alt_riwayat from anon;
revoke update on public.mhs_email_alt_riwayat from anon;
revoke delete on public.mk_padanan_sah from anon;
revoke insert on public.mk_padanan_sah from anon;
revoke references on public.mk_padanan_sah from anon;
revoke select on public.mk_padanan_sah from anon;
revoke trigger on public.mk_padanan_sah from anon;
revoke truncate on public.mk_padanan_sah from anon;
revoke update on public.mk_padanan_sah from anon;
revoke delete on public.mk_padanan_sah from authenticated;
revoke insert on public.mk_padanan_sah from authenticated;
revoke update on public.mk_padanan_sah from authenticated;
revoke delete on public.mk_padanan_sah_log from anon;
revoke insert on public.mk_padanan_sah_log from anon;
revoke references on public.mk_padanan_sah_log from anon;
revoke select on public.mk_padanan_sah_log from anon;
revoke trigger on public.mk_padanan_sah_log from anon;
revoke truncate on public.mk_padanan_sah_log from anon;
revoke update on public.mk_padanan_sah_log from anon;
revoke delete on public.mk_padanan_sah_log from authenticated;
revoke insert on public.mk_padanan_sah_log from authenticated;
revoke update on public.mk_padanan_sah_log from authenticated;
revoke delete on public.mk_rps from anon;
revoke insert on public.mk_rps from anon;
revoke references on public.mk_rps from anon;
revoke select on public.mk_rps from anon;
revoke trigger on public.mk_rps from anon;
revoke truncate on public.mk_rps from anon;
revoke update on public.mk_rps from anon;
revoke delete on public.mk_rps_pengesahan from anon;
revoke insert on public.mk_rps_pengesahan from anon;
revoke references on public.mk_rps_pengesahan from anon;
revoke select on public.mk_rps_pengesahan from anon;
revoke trigger on public.mk_rps_pengesahan from anon;
revoke truncate on public.mk_rps_pengesahan from anon;
revoke update on public.mk_rps_pengesahan from anon;
revoke delete on public.mk_rps_pengesahan from authenticated;
revoke insert on public.mk_rps_pengesahan from authenticated;
revoke update on public.mk_rps_pengesahan from authenticated;
revoke delete on public.mk_rps_review from anon;
revoke insert on public.mk_rps_review from anon;
revoke references on public.mk_rps_review from anon;
revoke select on public.mk_rps_review from anon;
revoke trigger on public.mk_rps_review from anon;
revoke truncate on public.mk_rps_review from anon;
revoke update on public.mk_rps_review from anon;
revoke delete on public.mk_rps_review from authenticated;
revoke insert on public.mk_rps_review from authenticated;
revoke update on public.mk_rps_review from authenticated;
revoke delete on public.mk_rps_riwayat from anon;
revoke insert on public.mk_rps_riwayat from anon;
revoke references on public.mk_rps_riwayat from anon;
revoke select on public.mk_rps_riwayat from anon;
revoke trigger on public.mk_rps_riwayat from anon;
revoke truncate on public.mk_rps_riwayat from anon;
revoke update on public.mk_rps_riwayat from anon;
revoke delete on public.mk_rps_tinjauan from anon;
revoke insert on public.mk_rps_tinjauan from anon;
revoke references on public.mk_rps_tinjauan from anon;
revoke select on public.mk_rps_tinjauan from anon;
revoke trigger on public.mk_rps_tinjauan from anon;
revoke truncate on public.mk_rps_tinjauan from anon;
revoke update on public.mk_rps_tinjauan from anon;
revoke delete on public.mk_rps_tinjauan from authenticated;
revoke delete on public.mk_rps_tinjauan_log from anon;
revoke insert on public.mk_rps_tinjauan_log from anon;
revoke references on public.mk_rps_tinjauan_log from anon;
revoke select on public.mk_rps_tinjauan_log from anon;
revoke trigger on public.mk_rps_tinjauan_log from anon;
revoke truncate on public.mk_rps_tinjauan_log from anon;
revoke update on public.mk_rps_tinjauan_log from anon;
revoke delete on public.mk_rps_tinjauan_log from authenticated;
revoke insert on public.mk_rps_tinjauan_log from authenticated;
revoke update on public.mk_rps_tinjauan_log from authenticated;
revoke delete on public.mk_rps_ttd from anon;
revoke insert on public.mk_rps_ttd from anon;
revoke references on public.mk_rps_ttd from anon;
revoke select on public.mk_rps_ttd from anon;
revoke trigger on public.mk_rps_ttd from anon;
revoke truncate on public.mk_rps_ttd from anon;
revoke update on public.mk_rps_ttd from anon;
revoke delete on public.mk_rps_ttd from authenticated;
revoke insert on public.mk_rps_ttd from authenticated;
revoke update on public.mk_rps_ttd from authenticated;
revoke delete on public.mk_silabus from anon;
revoke insert on public.mk_silabus from anon;
revoke references on public.mk_silabus from anon;
revoke select on public.mk_silabus from anon;
revoke trigger on public.mk_silabus from anon;
revoke truncate on public.mk_silabus from anon;
revoke update on public.mk_silabus from anon;
revoke delete on public.mk_silabus from authenticated;
revoke insert on public.mk_silabus from authenticated;
revoke update on public.mk_silabus from authenticated;
revoke delete on public.mk_silabus_log from anon;
revoke insert on public.mk_silabus_log from anon;
revoke references on public.mk_silabus_log from anon;
revoke select on public.mk_silabus_log from anon;
revoke trigger on public.mk_silabus_log from anon;
revoke truncate on public.mk_silabus_log from anon;
revoke update on public.mk_silabus_log from anon;
revoke delete on public.mk_silabus_log from authenticated;
revoke insert on public.mk_silabus_log from authenticated;
revoke update on public.mk_silabus_log from authenticated;
revoke delete on public.pemakaian_halaman from anon;
revoke insert on public.pemakaian_halaman from anon;
revoke references on public.pemakaian_halaman from anon;
revoke select on public.pemakaian_halaman from anon;
revoke trigger on public.pemakaian_halaman from anon;
revoke truncate on public.pemakaian_halaman from anon;
revoke update on public.pemakaian_halaman from anon;
revoke delete on public.pemakaian_halaman from authenticated;
revoke insert on public.pemakaian_halaman from authenticated;
revoke references on public.pemakaian_halaman from authenticated;
revoke select on public.pemakaian_halaman from authenticated;
revoke trigger on public.pemakaian_halaman from authenticated;
revoke truncate on public.pemakaian_halaman from authenticated;
revoke update on public.pemakaian_halaman from authenticated;
revoke delete on public.pengajuan_berkas from anon;
revoke insert on public.pengajuan_berkas from anon;
revoke references on public.pengajuan_berkas from anon;
revoke select on public.pengajuan_berkas from anon;
revoke trigger on public.pengajuan_berkas from anon;
revoke truncate on public.pengajuan_berkas from anon;
revoke update on public.pengajuan_berkas from anon;
revoke delete on public.pengajuan_berkas from authenticated;
revoke insert on public.pengajuan_berkas from authenticated;
revoke update on public.pengajuan_berkas from authenticated;
revoke delete on public.pengajuan_mahasiswa from anon;
revoke insert on public.pengajuan_mahasiswa from anon;
revoke references on public.pengajuan_mahasiswa from anon;
revoke select on public.pengajuan_mahasiswa from anon;
revoke trigger on public.pengajuan_mahasiswa from anon;
revoke truncate on public.pengajuan_mahasiswa from anon;
revoke update on public.pengajuan_mahasiswa from anon;
revoke delete on public.pengajuan_mahasiswa from authenticated;
revoke insert on public.pengajuan_mahasiswa from authenticated;
revoke update on public.pengajuan_mahasiswa from authenticated;
revoke delete on public.pengajuan_riwayat from anon;
revoke insert on public.pengajuan_riwayat from anon;
revoke references on public.pengajuan_riwayat from anon;
revoke select on public.pengajuan_riwayat from anon;
revoke trigger on public.pengajuan_riwayat from anon;
revoke truncate on public.pengajuan_riwayat from anon;
revoke update on public.pengajuan_riwayat from anon;
revoke delete on public.pengajuan_riwayat from authenticated;
revoke insert on public.pengajuan_riwayat from authenticated;
revoke update on public.pengajuan_riwayat from authenticated;
revoke delete on public.peringatan_keamanan from anon;
revoke insert on public.peringatan_keamanan from anon;
revoke references on public.peringatan_keamanan from anon;
revoke select on public.peringatan_keamanan from anon;
revoke trigger on public.peringatan_keamanan from anon;
revoke truncate on public.peringatan_keamanan from anon;
revoke update on public.peringatan_keamanan from anon;
revoke delete on public.peringatan_keamanan from authenticated;
revoke insert on public.peringatan_keamanan from authenticated;
revoke truncate on public.peringatan_keamanan from authenticated;
revoke update on public.peringatan_keamanan from authenticated;
revoke select on public.rapat from anon;
revoke select on public.rapat from authenticated;
revoke delete on public.ref_cpl from anon;
revoke insert on public.ref_cpl from anon;
revoke references on public.ref_cpl from anon;
revoke select on public.ref_cpl from anon;
revoke trigger on public.ref_cpl from anon;
revoke truncate on public.ref_cpl from anon;
revoke update on public.ref_cpl from anon;
revoke delete on public.ref_cpl_korelasi from anon;
revoke insert on public.ref_cpl_korelasi from anon;
revoke references on public.ref_cpl_korelasi from anon;
revoke select on public.ref_cpl_korelasi from anon;
revoke trigger on public.ref_cpl_korelasi from anon;
revoke truncate on public.ref_cpl_korelasi from anon;
revoke update on public.ref_cpl_korelasi from anon;
revoke delete on public.ref_mk_cpl from anon;
revoke insert on public.ref_mk_cpl from anon;
revoke references on public.ref_mk_cpl from anon;
revoke select on public.ref_mk_cpl from anon;
revoke trigger on public.ref_mk_cpl from anon;
revoke truncate on public.ref_mk_cpl from anon;
revoke update on public.ref_mk_cpl from anon;
revoke delete on public.ref_mk_padanan from anon;
revoke insert on public.ref_mk_padanan from anon;
revoke references on public.ref_mk_padanan from anon;
revoke select on public.ref_mk_padanan from anon;
revoke trigger on public.ref_mk_padanan from anon;
revoke truncate on public.ref_mk_padanan from anon;
revoke update on public.ref_mk_padanan from anon;
revoke delete on public.status_sistem from anon;
revoke insert on public.status_sistem from anon;
revoke references on public.status_sistem from anon;
revoke select on public.status_sistem from anon;
revoke trigger on public.status_sistem from anon;
revoke truncate on public.status_sistem from anon;
revoke update on public.status_sistem from anon;
revoke delete on public.ta_arsip from anon;
revoke insert on public.ta_arsip from anon;
revoke references on public.ta_arsip from anon;
revoke select on public.ta_arsip from anon;
revoke trigger on public.ta_arsip from anon;
revoke truncate on public.ta_arsip from anon;
revoke update on public.ta_arsip from anon;
revoke delete on public.ta_arsip from authenticated;
revoke insert on public.ta_arsip from authenticated;
revoke truncate on public.ta_arsip from authenticated;
revoke update on public.ta_arsip from authenticated;
revoke delete on public.ta_berkas from anon;
revoke insert on public.ta_berkas from anon;
revoke references on public.ta_berkas from anon;
revoke select on public.ta_berkas from anon;
revoke trigger on public.ta_berkas from anon;
revoke truncate on public.ta_berkas from anon;
revoke update on public.ta_berkas from anon;
revoke delete on public.ta_berkas from authenticated;
revoke truncate on public.ta_berkas from authenticated;
revoke delete on public.ta_bimbingan from anon;
revoke insert on public.ta_bimbingan from anon;
revoke references on public.ta_bimbingan from anon;
revoke select on public.ta_bimbingan from anon;
revoke trigger on public.ta_bimbingan from anon;
revoke truncate on public.ta_bimbingan from anon;
revoke update on public.ta_bimbingan from anon;
revoke delete on public.ta_bimbingan from authenticated;
revoke insert on public.ta_bimbingan from authenticated;
revoke truncate on public.ta_bimbingan from authenticated;
revoke update on public.ta_bimbingan from authenticated;
revoke delete on public.ta_kecuali_urutan from anon;
revoke insert on public.ta_kecuali_urutan from anon;
revoke references on public.ta_kecuali_urutan from anon;
revoke select on public.ta_kecuali_urutan from anon;
revoke trigger on public.ta_kecuali_urutan from anon;
revoke truncate on public.ta_kecuali_urutan from anon;
revoke update on public.ta_kecuali_urutan from anon;
revoke delete on public.ta_kecuali_urutan from authenticated;
revoke insert on public.ta_kecuali_urutan from authenticated;
revoke truncate on public.ta_kecuali_urutan from authenticated;
revoke update on public.ta_kecuali_urutan from authenticated;
revoke delete on public.ta_kk_dekat from anon;
revoke insert on public.ta_kk_dekat from anon;
revoke references on public.ta_kk_dekat from anon;
revoke select on public.ta_kk_dekat from anon;
revoke trigger on public.ta_kk_dekat from anon;
revoke truncate on public.ta_kk_dekat from anon;
revoke update on public.ta_kk_dekat from anon;
revoke delete on public.ta_kk_dekat from authenticated;
revoke insert on public.ta_kk_dekat from authenticated;
revoke update on public.ta_kk_dekat from authenticated;
revoke delete on public.ta_kuota from anon;
revoke insert on public.ta_kuota from anon;
revoke references on public.ta_kuota from anon;
revoke select on public.ta_kuota from anon;
revoke trigger on public.ta_kuota from anon;
revoke truncate on public.ta_kuota from anon;
revoke update on public.ta_kuota from anon;
revoke delete on public.ta_kuota from authenticated;
revoke insert on public.ta_kuota from authenticated;
revoke update on public.ta_kuota from authenticated;
revoke delete on public.ta_nilai from anon;
revoke insert on public.ta_nilai from anon;
revoke references on public.ta_nilai from anon;
revoke select on public.ta_nilai from anon;
revoke trigger on public.ta_nilai from anon;
revoke truncate on public.ta_nilai from anon;
revoke update on public.ta_nilai from anon;
revoke delete on public.ta_nilai from authenticated;
revoke insert on public.ta_nilai from authenticated;
revoke truncate on public.ta_nilai from authenticated;
revoke update on public.ta_nilai from authenticated;
revoke delete on public.ta_rubrik from anon;
revoke insert on public.ta_rubrik from anon;
revoke references on public.ta_rubrik from anon;
revoke select on public.ta_rubrik from anon;
revoke trigger on public.ta_rubrik from anon;
revoke truncate on public.ta_rubrik from anon;
revoke update on public.ta_rubrik from anon;
revoke delete on public.ta_rubrik from authenticated;
revoke insert on public.ta_rubrik from authenticated;
revoke truncate on public.ta_rubrik from authenticated;
revoke update on public.ta_rubrik from authenticated;
revoke delete on public.ta_syarat_bimbingan from anon;
revoke insert on public.ta_syarat_bimbingan from anon;
revoke references on public.ta_syarat_bimbingan from anon;
revoke select on public.ta_syarat_bimbingan from anon;
revoke trigger on public.ta_syarat_bimbingan from anon;
revoke truncate on public.ta_syarat_bimbingan from anon;
revoke update on public.ta_syarat_bimbingan from anon;
revoke delete on public.ta_syarat_bimbingan from authenticated;
revoke insert on public.ta_syarat_bimbingan from authenticated;
revoke truncate on public.ta_syarat_bimbingan from authenticated;
revoke delete on public.testimoni from anon;
revoke insert on public.testimoni from anon;
revoke references on public.testimoni from anon;
revoke select on public.testimoni from anon;
revoke trigger on public.testimoni from anon;
revoke truncate on public.testimoni from anon;
revoke update on public.testimoni from anon;
revoke delete on public.yudisium_berkas from anon;
revoke insert on public.yudisium_berkas from anon;
revoke references on public.yudisium_berkas from anon;
revoke select on public.yudisium_berkas from anon;
revoke trigger on public.yudisium_berkas from anon;
revoke truncate on public.yudisium_berkas from anon;
revoke update on public.yudisium_berkas from anon;
grant select (id, judul, jenis, tanggal, mulai, selesai, tempat, pimpinan, notulis, agenda, terbatas, status, dokumen_id, token_hadir, hadir_sampai, dibuat_oleh, oleh, dibuat, diperbarui) on public.rapat to authenticated;

-- Penyimpanan berkas
insert into storage.buckets (id, name, public) values ('bukti', 'bukti', false)
  on conflict (id) do nothing;
create policy bukti_baca on storage.objects as permissive for select to authenticated
  using (((bucket_id = 'bukti'::text) AND (public.me() IS NOT NULL)));
create policy bukti_hapus on storage.objects as permissive for delete to authenticated
  using (((bucket_id = 'bukti'::text) AND (((storage.foldername(name))[1] = (public.me())::text) OR public.is_admin())));
