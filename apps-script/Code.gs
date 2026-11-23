// =====================================================================
//  Unggah berkas bukti dari cv-site ke Google Drive prodi.
//
//  Dipasang sebagai Web App di akun Google prodi (Execute as: Me,
//  Who has access: Anyone). Langkah pasang: apps-script/README.md.
//  Sumber kode ini ada di repo ini; salinan di editor Apps Script
//  diganti seluruhnya bila berkas ini berubah.
//
//  Alur doPost:
//    1. token login Supabase dosen diperiksa ke /auth/v1/user;
//    2. email itu harus ada di tabel dosen (aturan sama dengan input.html);
//    3. berkas disimpan menurut jenis unggahan (field `kind`):
//         'karya' (bawaan) -> <FOLDER_ID>/<tahun>/<nama dosen>/   (input.html);
//                             dengan `group` (judul karya, untuk banyak
//                             berkas/folder): .../<nama dosen>/<judul>/[path]/,
//                             folder judul dibagikan Viewer -> folderUrl
//         'butir'          -> <FOLDER_ID>/butir-manual/butir-NN/[path]/
//                             (input-butir.html, khusus peran admin; bukti
//                             ke-60 butir; `path` = subfolder dari unggah
//                             folder; folder butir-NN dibagikan Viewer dan
//                             tautannya dikembalikan sebagai folderUrl)
//         'dokumen'        -> <FOLDER_ID>/dokumen/<jenis>/<tahun>/[<judul>/]
//                             (input-butir.html, khusus admin; dokumen
//                             bernama seperti statuta/kurikulum/SK; mode
//                             'ganti' memindahkan berkas lama ke _arsip,
//                             mode 'tambah' tidak; tautannya dicatat di
//                             tabel Supabase `dokumen`)
//         'daftar_berkas'  -> khusus admin: daftar semua berkas bukti
//                             (tanpa _arsip) untuk alat berkas tak terpakai
//         'sidik'          -> khusus admin: SHA-256 isi berkas pada `urls`
//                             (1-10 tautan), untuk pemeriksa berkas ganda
//                             (supabase/instal-lengkap.sql); hanya
//                             membaca, hanya berkas di dalam FOLDER_ID
//         'bkd'            -> Laporan Kinerja Dosen: bkd-privat/<ta>/<dosen>/,
//                             TANPA tautan publik (memuat data pribadi);
//                             admin boleh mengunggah `atas_nama` dosen lain
//         'buka_bkd'       -> isi berkas LKD pada `url`, untuk admin atau
//                             dosen pemiliknya
//         'buka_lkd_sandi' -> tanpa login: isi LKD untuk asesor dengan kata
//                             sandi LKD_SANDI (site/lkd.html); hanya berkas di
//                             folder bkd-privat
//         'bagikan_sementara' -> admin atau pemilik: tautan 2 bulan tanpa login
//         'buka_lkd_token' -> tanpa login: isi berkas dengan tautan sementara
//         'cpl'            -> berkas nilai CPL (2026-11-11): hanya .xlsx, hanya
//                             pengampu kelas (cpl_kelas dibaca dengan token
//                             pengunggah) atau admin; berkas-privat/cpl/<TA sem>/
//                             <MK-kelas>/, versi lama ke riwayat/; hanya admin
//                             yang bisa membukanya (tidak lewat tautan sementara,
//                             asesor, sandi, atau token)
//         'cpl_unduh'      -> tanpa login, untuk run_cpl.py: kunci CPL_KUNCI;
//                             aksi daftar (berkas terbaru tiap kelas) / ambil
//         'hapus'          -> khusus admin: berkas pada `url` dipindah ke
//                             Sampah Drive (hanya berkas di dalam FOLDER_ID;
//                             tautan non-Drive dan folder dilewati)
//         'buang_milik'    -> pemilik (folder bernama dosen itu) atau admin:
//                             bukti profil privat di berkas-privat/karya/ yang
//                             diganti atau tidak jadi dipakai, ke Sampah Drive
//                             (2026-11-13)
//    4. berkas dibagikan "siapa pun yang punya link: Viewer" supaya asesor
//       bisa membuka tautan di LKPS/LED tanpa login. Folder induk tetap privat.
//
//  Script Properties (Project Settings > Script properties), semuanya wajib:
//    FOLDER_ID     ID folder bukti-lkps di Drive akun prodi
//                  (bagian URL setelah /folders/)
//    SUPABASE_URL  https://<ref>.supabase.co, sama dengan SB_URL di config.js
//    SUPABASE_KEY  publishable key (sb_publishable_...), sama dengan SB_KEY
//                  di config.js. BUKAN secret key.
//    MAX_MB        batas ukuran satu berkas dalam MB, bilangan bulat 1-40
//    ALLOWED_EXT   ekstensi yang diterima, dipisah koma, huruf kecil,
//                  mis. pdf,jpg,jpeg,png,docx,xlsx
//  Zona waktu nama berkas mengikuti Project Settings > Time zone.
//
//  Tambahan, hanya untuk cadangan otomatis (kind 'cadangan', repo publik;
//  tanpa dua kunci ini cadangan ditolak, unggahan bukti tetap berjalan):
//    CADANGAN_FOLDER_ID  ID folder privat di LUAR FOLDER_ID, tidak dibagikan
//    CADANGAN_TOKEN      token acak minimal 32 karakter, sama dengan GitHub
//                        Secret CADANGAN_TOKEN
// =====================================================================

// Jenis MIME per ekstensi. Bukan pilihan pemakai: ini pemetaan tetap.
// Ekstensi di ALLOWED_EXT yang tidak ada di sini ditolak saat validasi.
// Jenis dokumen dan tabel Data prodi yang disimpan tanpa tautan publik (pemilik
// 2026-11-06). Sama dengan JENIS_DOKUMEN (privat: true) dan TABEL_PRIVAT di
// site/rencana-bukti.js; tests/js/tautan_privat.test.mjs memeriksa keduanya.
var JENIS_PRIVAT = ['rekap_bkd', 'laporan_keuangan', 'laporan_audit_keuangan', 'dokumen_kerjasama', 'laporan_ami',
  'laporan_rtm', 'notulen', 'berkas_pribadi', 'data_mahasiswa', 'data_survei_mentah', 'daftar_hadir', 'kontrak_hibah',
  'lkps_mahasiswa_ta', 'lkps_kohort_lulusan', 'lkps_tendik', 'lkps_penggunaan_dana', 'lkps_kerjasama', 'jadwal_ta'];

var MIME_BY_EXT = {
  pdf: 'application/pdf',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
};

function doPost(e) {
  try {
    var cfg = readConfig_();
    if (!e || !e.postData || !e.postData.contents) {
      throw new Error('Permintaan kosong.');
    }
    var req = JSON.parse(e.postData.contents);
    // Cadangan (pemilik 2026-11-05): dikirim GitHub Actions, bukan dosen, jadi
    // diperiksa dengan token cadangan dan bukan login Supabase.
    if (req.kind === 'cadangan') return json_(simpanCadangan_(req));
    // Asesor tidak punya akun situs (pemilik 2026-11-06): diperiksa dengan kata sandi.
    if (req.kind === 'buka_lkd_sandi') return json_(bukaLkdSandi_(cfg, req));
    // Tautan sementara bertanda tangan, mis. untuk laporan SISTER: tanpa login.
    if (req.kind === 'buka_lkd_token') return json_(bukaLkdToken_(cfg, req));
    // Akses asesor (pemilik 2026-11-10): selama dibuka admin, tautan berkas privat tanpa sandi.
    if (req.kind === 'buka_lkd_asesor') return json_(bukaLkdAsesor_(cfg, req));
    // Berkas nilai CPL untuk run_cpl.py di komputer admin (pemilik 2026-11-11): kunci CPL_KUNCI.
    if (req.kind === 'cpl_unduh') return json_(cplUnduh_(cfg, req));
    // Cadangan berkas Drive ke komputer prodi (pemilik 2026-11-20): run_cadangan_drive.py, kunci CADANGAN_DRIVE_KUNCI.
    if (req.kind === 'cadangan_drive') return json_(cadanganDrive_(cfg, req));
    // Pengajuan mahasiswa KP/lomba (instal-lengkap.sql, pemilik 2026-11-17): mahasiswa tanpa
    // login; tautan pribadi dikirim ke email kampus, token tautan membuka pengajuannya sendiri.
    if (req.kind === 'mhs_ajukan') return json_(mhsAjukan_(cfg, req));
    if (req.kind === 'mhs_tautan_ulang') return json_(mhsTautanUlang_(cfg, req));
    // Email alternatif mahasiswa (104, pemilik 2026-11-18): diminta, lalu dikonfirmasi lewat email kampus.
    if (req.kind === 'mhs_email_alt') return json_(mhsEmailAlt_(cfg, req));
    if (req.kind === 'mhs_email_alt_konfirmasi') return json_(mhsEmailAltKonfirmasi_(cfg, req));
    if (req.kind === 'mhs_unggah') return json_(mhsUnggah_(cfg, req));
    if (req.kind === 'mhs_buka') return json_(mhsBerkas_(cfg, req, false));
    if (req.kind === 'mhs_buang') return json_(mhsBerkas_(cfg, req, true));
    // Portofolio MK lewat tautan AMI (instal-lengkap.sql, pemilik 2026-11-17): auditor tanpa akun;
    // basis data memeriksa token AMI berlaku dan berkas dalam periodenya.
    if (req.kind === 'ami_portofolio_buka') {
      return json_(bukaPortofolio_(cfg, rpc_(cfg, 'ami_portofolio_url', { p_token: String(req.ami || ''), p_id: Number(req.id) })));
    }
    var lecturer = verifyLecturer_(cfg, req.token);
    // Hitung CPL otomatis sekarang (pemilik 2026-11-17, OBE O4): admin atau GKM memicu workflow hitung-cpl.yml.
    if (req.kind === 'cpl_hitung') return json_(cplHitung_(cfg, lecturer, req));
    // Build situs otomatis (pemilik 2026-11-19): halaman ruang kerja memanggil ini setelah data publik berubah (pemicu-bangun.js).
    if (req.kind === 'bangun_situs') return json_(bangunSitus_(lecturer));
    // Undangan reviewer RPS (120, pemilik 2026-11-19): isi email dari rps_review_undangan dengan token pengirim; basis data
    // memeriksa Kaprodi aktif/admin dan penunjukan yang belum dikirim, jadi permintaan ini tidak bisa mengirim email bebas.
    if (req.kind === 'rps_review_kabari') return json_(rpsReviewKabari_(cfg, lecturer, req));
    // Portofolio MK (103): dibuka dengan token login; portofolio_url menolak bila tidak boleh baca.
    if (req.kind === 'portofolio_buka') {
      return json_(bukaPortofolio_(cfg, rpc_(cfg, 'portofolio_url', { p_id: Number(req.id) }, req.token)));
    }
    // Pembimbing/admin: berkas pengajuan mahasiswa dibaca dengan token login mereka (RLS menentukan boleh).
    if (req.kind === 'mhs_buka_prodi') return json_(mhsBukaProdi_(cfg, req));
    if (req.kind === 'mhs_unggah_prodi') return json_(mhsUnggahProdi_(cfg, lecturer, req));
    if (req.kind === 'mhs_kabari') return json_(mhsKabari_(cfg, lecturer, req));
    var kind = req.kind || 'karya';
    // Pengingat email (pemilik 2026-11-11): admin mengirim dari akun Google prodi.
    if (kind === 'kirim_pengingat') {
      if (lecturer.peran !== 'admin') {
        throw new Error('Mengirim pengingat khusus peran admin.');
      }
      return json_(kirimPengingat_(lecturer, req));
    }
    if (kind === 'akses_asesor') {
      if (lecturer.peran !== 'admin') {
        throw new Error('Akses asesor khusus peran admin.');
      }
      return json_(aksesAsesor_(req.mode));
    }
    // Hapus (pemilik 2026-11-03): admin membuang berkas bukti ke Sampah
    // Drive (bisa dipulihkan 30 hari). Hanya berkas di dalam FOLDER_ID.
    if (kind === 'hapus') {
      if (lecturer.peran !== 'admin') {
        throw new Error('Membuang berkas khusus peran admin.');
      }
      return json_(buangBerkas_(cfg, req.url));
    }
    // Daftar berkas (pemilik 2026-11-03): bahan alat "berkas tak terpakai" di
    // input-butir.html. Hanya membaca; membuang tetap lewat kind 'hapus'.
    if (kind === 'daftar_berkas') {
      if (lecturer.peran !== 'admin') {
        throw new Error('Daftar berkas khusus peran admin.');
      }
      return json_(daftarBerkas_(cfg));
    }
    // Sidik berkas (pemilik 2026-11-04): berkas lama diberi sidik supaya
    // berkas yang tersimpan lebih dari sekali bisa disatukan. Hanya membaca.
    // Berkas lama yang jenisnya privat: keluar dari folder publik, tautan dicabut.
    if (kind === 'privatkan') {
      if (lecturer.peran !== 'admin') {
        throw new Error('Memprivatkan berkas khusus peran admin.');
      }
      return json_(privatkan_(cfg, req.url));
    }
    if (kind === 'sidik') {
      if (lecturer.peran !== 'admin') {
        throw new Error('Sidik berkas khusus peran admin.');
      }
      return json_(sidikBerkas_(cfg, req.urls));
    }
    // LKD privat (pemilik 2026-11-06): tidak punya tautan publik, jadi dibuka lewat sini.
    if (kind === 'buka_bkd') return json_(isiBerkas_(berkasBoleh_(cfg, lecturer, req.url)));
    if (kind === 'bagikan_sementara') return json_(bagikanSementara_(cfg, lecturer, req.url));
    // LKD lama yang sudah diganti (pemilik 2026-11-11): pemilik atau admin membuangnya
    // ke Sampah Drive (bisa dipulihkan 30 hari). Hanya berkas di folder bkd-privat.
    if (kind === 'buang_bkd') return json_(buangBkd_(cfg, lecturer, req.url));
    // Bukti profil (ijazah/sertifikat) yang diganti atau tidak jadi dipakai (pemilik 2026-11-13):
    // pemilik membuang berkas privatnya sendiri; situs memeriksa dulu bahwa tidak dirujuk catatan lain.
    if (kind === 'buang_milik') return json_(buangMilik_(cfg, lecturer, req.url));
    var folder, keterangan, folderUrl = null, privat = false;
    if (kind === 'butir') {
      if (lecturer.peran !== 'admin' && rpc_(cfg, 'boleh_mutu', {}, req.token) !== true) {   // GKM (98)
        throw new Error('Unggahan bukti butir khusus peran admin.');
      }
      var no = butirNumber_(req.butir);
      // Folder butir-NN dibagikan "siapa pun dengan link: Viewer" supaya satu
      // tautan di LED membuka semua bukti butir itu (pemilik 2026-11-03).
      // Folder induk data-lkps dan folder karya tetap privat.
      if (req.privat) {
        folder = privatFolder_(cfg, ['butir', 'butir-' + no]);
        privat = true;
      } else {
        var base = butirFolder_(cfg, no);
        shareFolder_(base);
        folderUrl = base.getUrl();
        folder = subFolder_(base, req.path);   // unggah folder: struktur subfolder ikut
      }
      keterangan = 'Bukti butir ' + no + ', diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else if (kind === 'dokumen') {
      // Koordinator (instal-lengkap.sql): bukti baris Data prodi untuk tabel bidangnya (boleh_tabel dengan token pengunggah).
      if (lecturer.peran !== 'admin' && rpc_(cfg, 'boleh_tabel', { p_tabel: String(req.jenis || '') }, req.token) !== true
          && rpc_(cfg, 'boleh_mutu', {}, req.token) !== true) {   // GKM (98): pustaka dokumen
        throw new Error('Unggahan dokumen induk khusus peran admin atau koordinator bidangnya.');
      }
      // Dokumen bernama (statuta, kurikulum, SK, ...): satu folder per
      // jenis + tahun (+ judul untuk jenis yang banyak per tahun), dibagikan
      // Viewer. Mode 'ganti' (bawaan) memindahkan berkas lama di folder itu
      // ke _arsip, jadi tahun sama = mengganti, tahun beda = versi lain;
      // mode 'tambah' menambah berkas tanpa mengarsipkan (pemilik 2026-11-03).
      // Tautannya dicatat browser di tabel Supabase `dokumen`.
      var jenis = dokumenId_(req.jenis);
      var dokFolder = dokumenFolder_(cfg, jenis, tahunDokumen_(req.tahun), req.judul);
      privat = JENIS_PRIVAT.indexOf(jenis) >= 0;
      if (privat) {
        dokFolder.setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.EDIT);
      } else {
        shareFolder_(dokFolder);
        folderUrl = dokFolder.getUrl();
      }
      if (req.mode !== 'tambah') arsipkan_(dokFolder);
      folder = dokFolder;
      keterangan = 'Dokumen ' + jenis + ' ' + req.tahun + (req.judul ? ' ' + req.judul : '')
        + ', diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else if (kind === 'rps') {
      // RPS mata kuliah (instal-lengkap.sql, pemilik 2026-11-17): koordinator MK/pengampu, GKM, atau admin
      // (boleh_mk dengan token pengunggah). dokumen/rps/<kurikulum>/<kode MK>, dibagikan Viewer; RPS lama ke _arsip.
      // Tautannya dicatat browser lewat mk_simpan_rps.
      var kurRps = String(req.kurikulum || ''), kodeRps = String(req.kode_mk || '');
      if (!/^K\d{2}$/.test(kurRps) || !/^[A-Za-z0-9.-]{1,20}$/.test(kodeRps)) throw new Error('Kurikulum atau kode MK tidak sah.');
      if (rpc_(cfg, 'boleh_mk', { p_kurikulum: kurRps, p_kode: kodeRps }, req.token) !== true) {
        throw new Error('RPS diunggah koordinator/pengampu mata kuliah ini, GKM, atau admin prodi.');
      }
      var rpsFolder = dokumenFolder_(cfg, 'rps', kurRps, kodeRps);
      shareFolder_(rpsFolder);
      folderUrl = rpsFolder.getUrl();
      arsipkan_(rpsFolder);
      folder = rpsFolder;
      keterangan = 'RPS ' + kurRps + ' ' + kodeRps + ', diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else if (kind === 'portofolio') {
      // Portofolio MK (instal-lengkap.sql, pemilik 2026-11-17): selalu privat (contoh jawaban memuat NIM).
      // berkas-privat/portofolio/<TA semester>/<kode MK>/<kelas atau MK>; izin: boleh_portofolio_tulis dengan token pengunggah.
      var taP = String(req.tahun_akademik || ''), smP = String(req.semester || ''), kurP = String(req.kurikulum || '');
      var kodeP = String(req.kode_mk || ''), kelasP = req.kelas ? String(req.kelas) : null;
      if (!/^\d{4}\/\d{4}$/.test(taP) || ['Ganjil', 'Genap'].indexOf(smP) < 0 || !/^K\d{2}$/.test(kurP)
          || !/^[A-Za-z0-9.-]{1,20}$/.test(kodeP) || (kelasP !== null && !/^.{1,10}$/.test(kelasP))) {
        throw new Error('Identitas portofolio tidak sah.');
      }
      if (rpc_(cfg, 'boleh_portofolio_tulis', { p_ta: taP, p_sm: smP, p_kur: kurP, p_kode: kodeP, p_kelas: kelasP }, req.token) !== true) {
        throw new Error('Portofolio diisi koordinator MK/pengampu kelas itu, GKM, atau admin prodi.');
      }
      folder = privatFolder_(cfg, ['portofolio', taP.replace('/', '-') + ' ' + smP, kodeP, kelasP ? 'kelas ' + kelasP : 'MK']);
      privat = true;
      keterangan = 'Portofolio ' + kodeP + (kelasP ? ' kelas ' + kelasP : '') + ' ' + taP + ' ' + smP + ' (' + String(req.komponen || '')
        + '), diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else if (kind === 'bkd') {
      var pemilik = String(req.atas_nama || '').trim() || lecturer.nama;
      if (pemilik !== lecturer.nama && lecturer.peran !== 'admin') {
        throw new Error('Mengunggah LKD dosen lain khusus peran admin.');
      }
      folder = bkdFolder_(cfg, req.tahun_akademik, pemilik);
      privat = true;
      keterangan = 'LKD ' + req.tahun_akademik + ' ' + req.semester + ' ' + pemilik
        + ', diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else if (kind === 'cpl') {
      // Berkas nilai CPL (pemilik 2026-11-11, instal-lengkap.sql): memuat NIM, jadi
      // privat dan hanya admin yang bisa membukanya. Kelas dibaca dengan token pengunggah,
      // jadi RLS menjamin ia pengampu kelas itu (atau admin). Versi lama ke subfolder riwayat.
      if (!/\.xlsx$/i.test(String(req.filename || ''))) {
        throw new Error('Berkas nilai CPL harus .xlsx (Template_Input_Data_CPL).');
      }
      var kls = cplKelas_(cfg, req.token, req.kelas_id);
      folder = privatFolder_(cfg, ['cpl', kls.tahun_akademik.replace('/', '-') + ' ' + kls.semester,
                                   kls.kode_mk + '-' + kls.kelas]);
      cplRiwayat_(folder);
      privat = true;
      keterangan = 'Nilai CPL ' + kls.kode_mk + ' kelas ' + kls.kelas + ' ' + kls.tahun_akademik + ' '
        + kls.semester + ', diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else if (kind === 'karya' && req.privat) {
      // Folder nama dosen = tanda pemilik saat membuka lewat buka_bkd.
      folder = privatFolder_(cfg, ['karya', req.year, lecturer.nama]);
      privat = true;
      keterangan = 'Diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else if (kind === 'karya') {
      folder = targetFolder_(cfg, req.year, lecturer.nama);
      // Banyak berkas / folder untuk satu karya (pemilik 2026-11-03): semua
      // masuk satu folder karya (`group` = judul karya), folder itu dibagikan
      // Viewer dan tautannya dikembalikan. Tanpa `group`: satu berkas, seperti
      // sebelumnya. Folder tahun dan folder nama dosen tetap privat.
      var group = String(req.group || '').trim();
      if (group) {
        var karyaFolder = groupFolder_(folder, group);
        shareFolder_(karyaFolder);
        folderUrl = karyaFolder.getUrl();
        folder = subFolder_(karyaFolder, req.path);
      }
      keterangan = 'Diunggah oleh ' + lecturer.email + ' lewat cv-site';
    } else {
      throw new Error('Jenis unggahan tidak dikenal: ' + kind);
    }
    var blob = kind === 'cpl' ? blobCpl_(cfg, req) : makeBlob_(cfg, req);
    var file = folder.createFile(blob);
    if (!privat) file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    file.setDescription(keterangan);
    var hasil = { ok: true, url: file.getUrl(), name: file.getName() };
    if (privat) { hasil.privat = true; hasil.id = file.getId(); }
    if (folderUrl) hasil.folderUrl = folderUrl;
    return json_(hasil);
  } catch (err) {
    return json_({ ok: false, error: String((err && err.message) || err) });
  }
}

// Satu zip dari GitHub Actions ke folder cadangan. Memuat data pribadi dosen,
// jadi berkasnya tidak dibagikan dan foldernya di luar folder bukti.
function simpanCadangan_(req) {
  var p = PropertiesService.getScriptProperties();
  var token = String(p.getProperty('CADANGAN_TOKEN') || '').trim();
  var folderId = String(p.getProperty('CADANGAN_FOLDER_ID') || '').trim();
  if (token.length < 32 || !folderId) {
    throw new Error('Script property CADANGAN_FOLDER_ID dan CADANGAN_TOKEN '
      + '(minimal 32 karakter) belum diisi.');
  }
  if (String(req.cadangan_token || '') !== token) {
    throw new Error('Token cadangan salah.');
  }
  var nama = String(req.name || '');
  if (!/^[a-z0-9-]+\.zip$/.test(nama)) {
    throw new Error('Nama cadangan tidak sah.');
  }
  var isi = Utilities.base64Decode(String(req.data || ''));
  if (!isi.length) throw new Error('Cadangan kosong.');
  var waktu = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd-HHmmss');
  var file = DriveApp.getFolderById(folderId)
    .createFile(Utilities.newBlob(isi, 'application/zip', waktu + '_' + nama));
  file.setDescription('Cadangan otomatis dari GitHub Actions');
  var dipangkas = nama === 'cadangan.zip' ? pangkasCadangan_(DriveApp.getFolderById(folderId)) : 0;
  return { ok: true, name: file.getName(), bytes: isi.length, dipangkas: dipangkas };
}

// Cadangan harian (templat prodi, 2026-11-23): yang berumur lebih dari 35 hari dipindah ke Sampah Drive (masih bisa
// dipulihkan 30 hari), KECUALI cadangan tanggal 01 (cadangan bulanan, disimpan). Arsip tahunan (nama lain) tidak disentuh.
function pangkasCadangan_(folder) {
  var batas = new Date(Date.now() - 35 * 86400000), it = folder.getFiles(), n = 0;
  while (it.hasNext()) {
    var f = it.next(), m = /^(\d{4})(\d{2})(\d{2})-\d{6}_cadangan\.zip$/.exec(f.getName());
    if (!m || m[3] === '01' || f.getDateCreated() >= batas) continue;
    f.setTrashed(true);
    n++;
  }
  return n;
}

// Pemeriksaan cepat setelah deploy: buka URL Web App di browser.
function doGet() {
  try {
    var cfg = readConfig_();
    var folder = DriveApp.getFolderById(cfg.folderId);
    // `versi`: penanda untuk memastikan dari luar bahwa deployment sudah baru.
    return json_({ ok: true, folder: folder.getName(), maxMb: cfg.maxMb,
                   allowedExt: cfg.allowedExt, versi: '2026-11-23-pangkas-cadangan' });
  } catch (err) {
    return json_({ ok: false, error: String((err && err.message) || err) });
  }
}

function readConfig_() {
  var p = PropertiesService.getScriptProperties();
  var missing = [];
  ['FOLDER_ID', 'SUPABASE_URL', 'SUPABASE_KEY', 'MAX_MB', 'ALLOWED_EXT']
    .forEach(function (k) { if (!p.getProperty(k)) missing.push(k); });
  if (missing.length) {
    throw new Error('Script property belum diisi: ' + missing.join(', '));
  }
  var url = p.getProperty('SUPABASE_URL').trim().replace(/\/+$/, '');
  if (!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(url)) {
    throw new Error('SUPABASE_URL harus berbentuk https://<ref>.supabase.co');
  }
  var key = p.getProperty('SUPABASE_KEY').trim();
  if (key.indexOf('sb_secret_') === 0) {
    throw new Error('SUPABASE_KEY harus publishable key, bukan secret key.');
  }
  var maxMb = Number(p.getProperty('MAX_MB'));
  if (!(maxMb >= 1 && maxMb <= 40 && Math.floor(maxMb) === maxMb)) {
    throw new Error('MAX_MB harus bilangan bulat 1-40.');
  }
  var allowedExt = p.getProperty('ALLOWED_EXT').toLowerCase().split(',')
    .map(function (s) { return s.trim(); }).filter(String);
  var unknown = allowedExt.filter(function (x) { return !MIME_BY_EXT[x]; });
  if (!allowedExt.length || unknown.length) {
    throw new Error('ALLOWED_EXT memuat ekstensi tak dikenal: ' + unknown.join(', ')
      + '. Yang dikenal: ' + Object.keys(MIME_BY_EXT).join(', '));
  }
  return { folderId: p.getProperty('FOLDER_ID').trim(), url: url, key: key,
           maxMb: maxMb, allowedExt: allowedExt };
}

// Token -> {email, nama}. Kueri dosen memakai token dosen itu sendiri,
// jadi Row Level Security Supabase tetap berlaku.
function verifyLecturer_(cfg, token) {
  if (!token) throw new Error('Belum masuk. Muat ulang halaman lalu masuk lagi.');
  var auth = { apikey: cfg.key, Authorization: 'Bearer ' + token };
  var res = UrlFetchApp.fetch(cfg.url + '/auth/v1/user',
                              { headers: auth, muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) {
    throw new Error('Sesi masuk tidak sah atau kedaluwarsa. Muat ulang halaman lalu masuk lagi.');
  }
  var email = (JSON.parse(res.getContentText()).email || '').trim();
  if (!email) throw new Error('Akun yang masuk tidak memiliki email.');

  // Email login boleh email alternatif (instal-lengkap.sql): id_dosen_login()
  // memetakannya ke dosen, dan email yang dipakai selanjutnya adalah email utama.
  // Sebelum patch 69 (rpc gagal) pencarian kembali ke email login.
  var q = cfg.url + '/rest/v1/dosen?select=nama,email,peran&email=ilike.' + encodeURIComponent(email);
  var rId = UrlFetchApp.fetch(cfg.url + '/rest/v1/rpc/id_dosen_login', { method: 'post', contentType: 'application/json',
    payload: '{}', headers: auth, muteHttpExceptions: true });
  if (rId.getResponseCode() === 200) {
    var idDosen = JSON.parse(rId.getContentText());
    if (!idDosen) throw new Error(email + ' belum terdaftar sebagai dosen prodi.');
    q = cfg.url + '/rest/v1/dosen?select=nama,email,peran&id=eq.' + encodeURIComponent(idDosen);
  }
  var r2 = UrlFetchApp.fetch(q, { headers: auth, muteHttpExceptions: true });
  if (r2.getResponseCode() !== 200) {
    throw new Error('Gagal membaca daftar dosen (HTTP ' + r2.getResponseCode() + ').');
  }
  var rows = JSON.parse(r2.getContentText());
  if (!rows.length) throw new Error(email + ' belum terdaftar sebagai dosen prodi.');
  return { email: rows[0].email || email, nama: rows[0].nama || email, peran: rows[0].peran || '' };
}

// Nomor butir matriks APS-AV 2025 Sarjana: 1-60, dikembalikan dua digit.
function butirNumber_(v) {
  var s = String(v || '').trim();
  if (!/^\d{1,2}$/.test(s) || +s < 1 || +s > 60) {
    throw new Error('Nomor butir tidak sah: ' + s);
  }
  return (+s < 10 ? '0' : '') + (+s);
}

// <FOLDER_ID>/butir-manual/butir-NN/. Lock seperti targetFolder_.
function butirFolder_(cfg, no) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var root = DriveApp.getFolderById(cfg.folderId);
    return childFolder_(childFolder_(root, 'butir-manual'), 'butir-' + no);
  } finally {
    lock.releaseLock();
  }
}

// Buang satu berkas bukti ke Sampah Drive. Tautan yang bukan berkas Drive
// (DOI, halaman jurnal, tautan folder) dilewati tanpa galat; berkas di luar
// folder bukti prodi ditolak supaya skrip tidak pernah menyentuh berkas lain.
function buangBerkas_(cfg, url) {
  var id = idBerkas_(url);
  if (!id) return { ok: true, dibuang: false, alasan: 'bukan berkas Google Drive' };
  var file;
  try {
    file = DriveApp.getFileById(id);
  } catch (err) {
    return { ok: true, dibuang: false, alasan: 'berkas tidak ditemukan' };
  }
  if (!diDalamFolder_(file, cfg.folderId)) {
    throw new Error('Berkas berada di luar folder bukti prodi; tidak dibuang.');
  }
  file.setTrashed(true);
  return { ok: true, dibuang: true, nama: file.getName() };
}

// Folder LKD: data-lkps/bkd-privat/<2025-2026>/<nama dosen>/, tidak dibagikan.
function bkdFolder_(cfg, ta, nama) {
  ta = String(ta || '').trim();
  if (!/^\d{4}\/\d{4}$/.test(ta)) throw new Error('Tahun akademik ditulis seperti 2025/2026.');
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var root = childFolder_(DriveApp.getFolderById(cfg.folderId), 'bkd-privat');
    return childFolder_(childFolder_(root, ta.replace('/', '-')), safeName_(nama));
  } finally {
    lock.releaseLock();
  }
}

// Isi LKD untuk admin, atau dosen yang nama foldernya sama dengan namanya.
function berkasBoleh_(cfg, lecturer, url) {
  var id = idBerkas_(url);
  if (!id) throw new Error('Tautan berkas tidak dikenali.');
  var file = DriveApp.getFileById(id);
  if (!terlindungi_(cfg, file)) throw new Error('Berkas ini bukan berkas privat.');
  tolakNilaiCpl_(cfg, file, lecturer);
  if (lecturer.peran !== 'admin' && file.getParents().next().getName() !== safeName_(lecturer.nama)) {
    throw new Error('Berkas ini hanya bisa dibuka pemiliknya dan admin.');
  }
  return file;
}

function buangMilik_(cfg, lecturer, url) {
  var file = berkasBoleh_(cfg, lecturer, url);
  if (!/^berkas-privat\/karya\//.test(jalurBerkas_(file, cfg.folderId))) throw new Error('Bukan berkas bukti profil.');
  file.setTrashed(true);
  return { ok: true, dibuang: true };
}

function buangBkd_(cfg, lecturer, url) {
  var file = berkasBoleh_(cfg, lecturer, url);
  if (!/^bkd-privat\//.test(jalurBerkas_(file, cfg.folderId))) throw new Error('Bukan berkas LKD.');
  file.setTrashed(true);
  return { ok: true, dibuang: true };
}

// Tautan sementara (pemilik 2026-11-06): admin atau pemilik berkas membuat tautan
// yang bisa dibuka siapa pun selama 2 bulan, untuk laporan SISTER. Masa berlakunya
// ada di dalam tanda tangan, jadi tidak perlu pemicu terjadwal untuk mencabutnya.
// Script Property TAUTAN_RAHASIA dibuat otomatis; menghapusnya mematikan semua
// tautan sementara yang sudah dibuat.
function rahasiaTautan_() {
  var p = PropertiesService.getScriptProperties();
  var r = p.getProperty('TAUTAN_RAHASIA');
  if (!r) {
    r = Utilities.getUuid() + Utilities.getUuid();
    p.setProperty('TAUTAN_RAHASIA', r);
  }
  return r;
}

function tandaTautan_(id, sampai) {
  return Utilities.base64EncodeWebSafe(
    Utilities.computeHmacSha256Signature(id + '|' + sampai, rahasiaTautan_()));
}

function bagikanSementara_(cfg, lecturer, url) {
  var file = berkasBoleh_(cfg, lecturer, url);
  tolakNilaiCpl_(cfg, file, null);
  var d = new Date();
  d.setMonth(d.getMonth() + 2);
  var sampai = d.getTime();
  return { ok: true, token: sampai + '.' + tandaTautan_(file.getId(), sampai),
           sampai: Utilities.formatDate(d, Session.getScriptTimeZone(), 'dd/MM/yyyy') };
}

function bukaLkdToken_(cfg, req) {
  var id = String(req.id || ''), m = String(req.tautan || '').match(/^(\d+)\.(.+)$/);
  if (!m || !/^[A-Za-z0-9_-]{20,}$/.test(id) || tandaTautan_(id, m[1]) !== m[2]) {
    throw new Error('Tautan tidak sah.');
  }
  if (Date.now() > Number(m[1])) throw new Error('Masa berlaku tautan ini sudah habis.');
  var file = DriveApp.getFileById(id);
  if (!terlindungi_(cfg, file)) throw new Error('Berkas ini bukan berkas privat.');
  tolakNilaiCpl_(cfg, file, null);
  return isiBerkas_(file);
}

// Memicu GitHub Actions hitung-cpl.yml (workflow_dispatch). Script Properties:
//   GITHUB_REPO            pemilik/nama repo data situs, mis. organisasi/cv-data
//   GITHUB_DISPATCH_TOKEN  fine-grained personal access token khusus repo itu, izin Actions: Read and write
// Token tidak pernah dikirim ke peramban; hanya admin/GKM yang login yang bisa memicunya.
function cplHitung_(cfg, lecturer, req) {
  if (lecturer.peran !== 'admin' && rpc_(cfg, 'boleh_mutu', {}, req.token) !== true) {
    throw new Error('Hitung ulang CPL khusus admin prodi atau GKM.');
  }
  var p = PropertiesService.getScriptProperties();
  var repo = String(p.getProperty('GITHUB_REPO') || '').trim(), tok = String(p.getProperty('GITHUB_DISPATCH_TOKEN') || '').trim();
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo) || !tok) {
    throw new Error('Script property GITHUB_REPO dan GITHUB_DISPATCH_TOKEN belum diisi (lihat petunjuk hitung CPL otomatis).');
  }
  var res = UrlFetchApp.fetch('https://api.github.com/repos/' + repo + '/actions/workflows/hitung-cpl.yml/dispatches', {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    payload: JSON.stringify({ ref: 'main', inputs: { paksa: true } }),
    headers: { Authorization: 'Bearer ' + tok, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' } });
  if (res.getResponseCode() !== 204) {
    throw new Error('GitHub menolak (HTTP ' + res.getResponseCode() + '): ' + res.getContentText().slice(0, 200));
  }
  return { ok: true, oleh: lecturer.email };
}

// Memicu GitHub Actions bangun-situs.yml (workflow_dispatch) setelah data publik berubah (pemilik 2026-11-19).
// Script Properties sama dengan cplHitung_ (GITHUB_REPO, GITHUB_DISPATCH_TOKEN). Siapa pun yang login boleh memicu;
// paling sering sekali per 60 detik (CacheService); pemicu dalam jeda itu tertampung build yang sedang berjalan/antre
// (workflow memakai concurrency tanpa membatalkan). Build tiap jam tetap ada sebagai cadangan.
function bangunSitus_(lecturer) {
  var cache = CacheService.getScriptCache();
  if (cache.get('bangun_situs')) return { ok: true, antre: true };
  var p = PropertiesService.getScriptProperties();
  var repo = String(p.getProperty('GITHUB_REPO') || '').trim(), tok = String(p.getProperty('GITHUB_DISPATCH_TOKEN') || '').trim();
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo) || !tok) {
    throw new Error('Script property GITHUB_REPO dan GITHUB_DISPATCH_TOKEN belum diisi (lihat petunjuk hitung CPL otomatis).');
  }
  var res = UrlFetchApp.fetch('https://api.github.com/repos/' + repo + '/actions/workflows/bangun-situs.yml/dispatches', {
    method: 'post', contentType: 'application/json', muteHttpExceptions: true, payload: JSON.stringify({ ref: 'main' }),
    headers: { Authorization: 'Bearer ' + tok, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' } });
  if (res.getResponseCode() !== 204) {
    throw new Error('GitHub menolak (HTTP ' + res.getResponseCode() + '): ' + res.getContentText().slice(0, 200));
  }
  cache.put('bangun_situs', String(new Date().getTime()), 60);
  return { ok: true, oleh: lecturer.email };
}

// Berkas portofolio MK (103): hanya dari berkas-privat/portofolio/, sesudah izin diperiksa basis data.
function bukaPortofolio_(cfg, url) {
  var id = idBerkas_(url);
  if (!id) throw new Error('Tautan berkas tidak dikenali.');
  var file = DriveApp.getFileById(id);
  if (!diDalamFolder_(file, cfg.folderId) || !/^berkas-privat\/portofolio\//.test(jalurBerkas_(file, cfg.folderId))) {
    throw new Error('Bukan berkas portofolio.');
  }
  return isiBerkas_(file);
}

function isiBerkas_(file) {
  var blob = file.getBlob();
  return { ok: true, name: file.getName(), mime: blob.getContentType(),
           data: Utilities.base64Encode(blob.getBytes()) };
}

// Izin kirim email (2026-11-11). Izin script.send_mail tidak diminta ulang hanya
// karena deploy versi baru: pilih fungsi ini di editor lalu klik Run sekali,
// setujui izin "Send email as you". Tidak mengirim email; hanya mencatat sisa kuota.
function izinkanEmail() {
  Logger.log('Izin email aktif. Sisa kuota hari ini: ' + MailApp.getRemainingDailyQuota());
}

// Pengingat email (pemilik 2026-11-11): paling banyak 30 email sekali kirim, dari
// akun Google pemilik Apps Script (kuota harian MailApp). Balasan ke admin pengirim.
function kirimPengingat_(lecturer, req) {
  var xs = req.pesan || [];
  if (!xs.length) throw new Error('Tidak ada pesan.');
  if (xs.length > 30) throw new Error('Paling banyak 30 email sekali kirim.');
  var sisa = MailApp.getRemainingDailyQuota();
  if (xs.length > sisa) throw new Error('Kuota email hari ini tinggal ' + sisa + '.');
  var terkirim = 0, gagal = [];
  xs.forEach(function (p) {
    var ke = String(p.ke || '').trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(ke)) { gagal.push(ke + ': alamat tidak sah'); return; }
    try {
      MailApp.sendEmail({ to: ke, subject: String(p.subjek || 'Pengingat').slice(0, 200),
        body: String(p.isi || '').slice(0, 10000), name: String(req.pengirim || 'Program Studi').slice(0, 80),
        replyTo: lecturer.email });
      terkirim++;
    } catch (e) { gagal.push(ke + ': ' + e.message); }
  });
  return { ok: true, terkirim: terkirim, gagal: gagal, sisa: MailApp.getRemainingDailyQuota() };
}

var BULAN_ID = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
function tanggalPanjang_(iso) {
  var m = String(iso || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? Number(m[3]) + ' ' + BULAN_ID[Number(m[2]) - 1] + ' ' + m[1] : String(iso || '');
}

// Email undangan reviewer RPS (120). Tautan ke halaman RPS memakai Script Property MHS_SITUS (alamat situs) bila ada.
function rpsReviewKabari_(cfg, lecturer, req) {
  var u = rpc_(cfg, 'rps_review_undangan', { p_kurikulum: String(req.kurikulum || ''), p_kode: String(req.kode || ''),
    p_reviewer: String(req.reviewer || '') }, req.token);
  if (MailApp.getRemainingDailyQuota() < 1) throw new Error('Kuota email hari ini habis; coba lagi besok (tombol Kirim ulang email).');
  var situs = String(PropertiesService.getScriptProperties().getProperty('MHS_SITUS') || '').trim();
  var tautan = /^https:\/\/\S+\/$/.test(situs)
    ? situs + 'rps.html?kur=' + encodeURIComponent(u.kurikulum) + '&kode=' + encodeURIComponent(u.kode_mk) : '';
  var mk = u.kode_mk + (u.nama_mk ? ' ' + u.nama_mk : '');
  var isi = 'Yth. ' + u.nama + ',\n\n'
    + 'Anda ditunjuk' + (u.penunjuk ? ' oleh ' + u.penunjuk : '') + ' sebagai reviewer Rencana Pembelajaran Semester (RPS) mata kuliah '
    + mk + ' (kurikulum ' + u.kurikulum + ').\n\n'
    + 'Mohon mengisi form review paling lambat ' + tanggalPanjang_(u.tenggat) + '.\n'
    + (tautan ? 'Buka RPS dan form review (masuk dengan akun dosen Anda):\n' + tautan + '\n' : '')
    + 'Form review ada di samping RPS; tugas ini juga tampil di Ruang kerja › Tugas saya.\n\n'
    + 'Terima kasih.\n' + String(req.pengirim || 'Program Studi') + '\n\n(Email ini dikirim otomatis oleh sistem program studi.)';
  MailApp.sendEmail({ to: u.email, subject: 'Permohonan review RPS ' + mk, body: isi,
    name: String(req.pengirim || 'Program Studi').slice(0, 80), replyTo: lecturer.email });
  return { ok: true, ke: u.email, tenggat: u.tenggat };
}

// Akses asesor (pemilik 2026-11-10): admin membuka akses selama 6 bulan. Selama
// itu siapa pun yang memegang tautan berkas privat (lkd.html?f=<id>, tertulis di
// LED, LKPS, dan daftar bukti) bisa membukanya tanpa login dan tanpa kata sandi.
// Script Property ASESOR_SAMPAI (milidetik); kosong atau lewat = tertutup.
//   mode 'buka' -> sampai = sekarang + 6 bulan; 'tutup' -> hapus; lainnya -> status.
function aksesAsesor_(mode) {
  var p = PropertiesService.getScriptProperties();
  if (mode === 'buka') {
    var d = new Date();
    d.setMonth(d.getMonth() + 6);
    p.setProperty('ASESOR_SAMPAI', String(d.getTime()));
  } else if (mode === 'tutup') {
    p.deleteProperty('ASESOR_SAMPAI');
  }
  var sampai = Number(p.getProperty('ASESOR_SAMPAI') || 0);
  var buka = sampai > Date.now();
  return { ok: true, buka: buka, sampai: buka ? sampai : null,
           teks: buka ? Utilities.formatDate(new Date(sampai), Session.getScriptTimeZone(), 'dd/MM/yyyy') : '' };
}

function bukaLkdAsesor_(cfg, req) {
  var sampai = Number(PropertiesService.getScriptProperties().getProperty('ASESOR_SAMPAI') || 0);
  if (!(sampai > Date.now())) throw new Error('Akses asesor tanpa kata sandi sedang ditutup.');
  var id = String(req.id || '');
  if (!/^[A-Za-z0-9_-]{20,}$/.test(id)) throw new Error('Tautan berkas tidak lengkap.');
  var file = DriveApp.getFileById(id);
  if (!terlindungi_(cfg, file)) throw new Error('Berkas ini bukan berkas privat.');
  tolakNilaiCpl_(cfg, file, null);
  var out = isiBerkas_(file);
  out.sampai = Utilities.formatDate(new Date(sampai), Session.getScriptTimeZone(), 'dd/MM/yyyy');
  return out;
}

// LKD untuk asesor. Script Property LKD_SANDI (minimal 8 karakter); kosong =
// akses ditutup, jadi cukup dikosongkan setelah visitasi. 20 kali salah
// menutup akses selama satu jam.
function bukaLkdSandi_(cfg, req) {
  var sandi = String(PropertiesService.getScriptProperties().getProperty('LKD_SANDI') || '');
  if (sandi.length < 8) throw new Error('Akses dengan kata sandi sedang ditutup. Hubungi program studi.');
  var cache = CacheService.getScriptCache();
  var gagal = Number(cache.get('lkd_gagal') || 0);
  if (gagal >= 20) throw new Error('Terlalu banyak percobaan. Coba lagi satu jam lagi.');
  if (String(req.sandi || '') !== sandi) {
    cache.put('lkd_gagal', String(gagal + 1), 3600);
    throw new Error('Kata sandi salah.');
  }
  var id = String(req.id || '');
  if (!/^[A-Za-z0-9_-]{20,}$/.test(id)) throw new Error('Tautan berkas tidak lengkap.');
  var file = DriveApp.getFileById(id);
  if (!terlindungi_(cfg, file)) throw new Error('Berkas ini bukan berkas privat.');
  tolakNilaiCpl_(cfg, file, null);
  return isiBerkas_(file);
}

// Hanya berkas privat yang boleh keluar lewat buka_bkd dan buka_lkd_sandi, supaya
// berkas lain di Drive akun prodi (mis. cadangan) tidak ikut terbuka.
function terlindungi_(cfg, file) {
  if (!diDalamFolder_(file, cfg.folderId)) return false;
  var jalur = jalurBerkas_(file, cfg.folderId);
  if (/^(bkd-privat|berkas-privat)\//.test(jalur)) return true;
  var m = jalur.match(/^dokumen\/([^\/]+)\//);
  return !!m && JENIS_PRIVAT.indexOf(m[1]) >= 0;
}

// data-lkps/berkas-privat/<segmen...>/, tidak dibagikan.
function privatFolder_(cfg, segmen) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var f = childFolder_(DriveApp.getFolderById(cfg.folderId), 'berkas-privat');
    for (var i = 0; i < segmen.length; i++) f = childFolder_(f, safeName_(segmen[i]));
    return f;
  } finally {
    lock.releaseLock();
  }
}

// Dipindah dulu: berkas di folder yang dibagikan mewarisi tautan foldernya.
function privatkan_(cfg, url) {
  var id = idBerkas_(url);
  if (!id) throw new Error('Tautan berkas tidak dikenali.');
  var file = DriveApp.getFileById(id);
  if (!diDalamFolder_(file, cfg.folderId)) throw new Error('Berkas di luar folder bukti.');
  file.moveTo(privatFolder_(cfg, ['dipindah']));
  file.setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.EDIT);
  return { ok: true, id: id };
}

// ID berkas dari tautan Drive (.../file/d/<id>/..., ...?id=<id>). Tautan
// folder (/folders/<id>) sengaja tidak dikenali: folder tidak dibuang.
function idBerkas_(url) {
  var s = String(url || '');
  var lkd = s.match(/lkd\.html\?f=([A-Za-z0-9_-]{20,})/);
  if (lkd) return lkd[1];
  if (!/^https:\/\/(drive|docs)\.google\.com\//.test(s)) return '';
  var m = s.match(/\/d\/([A-Za-z0-9_-]{20,})/) || s.match(/[?&]id=([A-Za-z0-9_-]{20,})/);
  return m ? m[1] : '';
}

// True bila berkas (lewat induk-induknya) berada di dalam folder rootId.
function diDalamFolder_(file, rootId) {
  var antre = [], it = file.getParents();
  while (it.hasNext()) antre.push(it.next());
  for (var langkah = 0; antre.length && langkah < 200; langkah++) {
    var f = antre.shift();
    if (f.getId() === rootId) return true;
    var p = f.getParents();
    while (p.hasNext()) antre.push(p.next());
  }
  return false;
}

// Jenis dokumen dari site/rencana-bukti.js (JENIS_DOKUMEN): huruf kecil,
// angka, garis bawah, 2-40 karakter. Dipakai langsung sebagai nama folder.
function dokumenId_(v) {
  var s = String(v || '').trim();
  if (!/^[a-z0-9_]{2,40}$/.test(s)) throw new Error('Jenis dokumen tidak sah: ' + s);
  return s;
}

function tahunDokumen_(v) {
  var s = String(v || '').trim();
  if (!/^\d{4}$/.test(s) || +s < 1990 || +s > 2100) throw new Error('Tahun dokumen tidak sah: ' + s);
  return s;
}

// <FOLDER_ID>/dokumen/<jenis>/<tahun>/[<judul>/]. Lock seperti targetFolder_.
function dokumenFolder_(cfg, jenis, tahun, judul) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var root = DriveApp.getFolderById(cfg.folderId);
    var f = childFolder_(childFolder_(childFolder_(root, 'dokumen'), jenis), tahun);
    judul = String(judul || '').trim();
    return judul ? childFolder_(f, safeName_(judul).slice(0, 80)) : f;
  } finally {
    lock.releaseLock();
  }
}

// Pindahkan semua berkas aktif di folder dokumen ke subfolder _arsip.
// Berkas tidak dihapus; tautan lama tetap bisa dibuka.
function arsipkan_(folder) {
  var files = folder.getFiles();
  if (!files.hasNext()) return;
  var arsip = childFolder_(folder, '_arsip');
  while (files.hasNext()) files.next().moveTo(arsip);
}

// Isi berkas harus cocok dengan ekstensinya (pemilik 2026-11-20): berkas berbahaya yang sekadar diganti namanya
// menjadi .pdf/.docx ditolak. bytes = hasil Utilities.base64Decode (bilangan bertanda -128..127). Hasil: '' bila
// cocok atau jenis tidak diperiksa, selain itu pesan untuk pengunggah. DOCX/XLSX/PPTX = ZIP; bermakro (vbaProject.bin,
// dicari di 256 KB terakhir tempat daftar isi ZIP) atau berkas Office terkunci kata sandi/format lama (OLE) ditolak.
function periksaIsi_(ext, bytes) {
  var b = function (i) { return bytes[i] & 0xFF; };
  var awal = function (tanda, dari) {
    if ((dari || 0) + tanda.length > bytes.length) return false;
    for (var i = 0; i < tanda.length; i++) if (b((dari || 0) + i) !== tanda[i]) return false;
    return true;
  };
  var cocok;
  if (ext === 'pdf') {
    cocok = false;
    for (var i = 0; i <= Math.min(bytes.length - 4, 1024); i++) if (awal([0x25, 0x50, 0x44, 0x46], i)) { cocok = true; break; }
  } else if (ext === 'png') {
    cocok = awal([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
  } else if (ext === 'jpg' || ext === 'jpeg') {
    cocok = awal([0xFF, 0xD8, 0xFF]);
  } else if (ext === 'docx' || ext === 'xlsx' || ext === 'pptx') {
    if (awal([0xD0, 0xCF, 0x11, 0xE0])) {
      return 'Berkas Office ini terkunci kata sandi atau berformat lama. Buka kuncinya lalu simpan ulang sebagai .' + ext + '.';
    }
    cocok = awal([0x50, 0x4B, 0x03, 0x04]);
    if (cocok) {
      var cari = [0x76, 0x62, 0x61, 0x50, 0x72, 0x6F, 0x6A, 0x65, 0x63, 0x74];   // "vbaProject"
      for (var j = Math.max(0, bytes.length - 262144); j <= bytes.length - cari.length; j++) {
        if (b(j) === 0x76 && awal(cari, j)) {
          return 'Berkas memuat makro dan tidak diterima. Simpan ulang sebagai .' + ext + ' biasa (tanpa makro).';
        }
      }
    }
  } else {
    return '';   // jenis lain di ALLOWED_EXT: isinya tidak diperiksa
  }
  return cocok ? '' : 'Isi berkas tidak sesuai dengan jenisnya (.' + ext + '): berkas rusak, atau bukan berkas '
    + ext.toUpperCase() + ' sungguhan yang hanya diganti namanya. Simpan ulang dari aplikasi aslinya lalu unggah lagi.';
}

function makeBlob_(cfg, req) {
  var name = String(req.filename || '').trim();
  var ext = (name.match(/\.([A-Za-z0-9]+)$/) || [])[1];
  ext = ext ? ext.toLowerCase() : '';
  if (cfg.allowedExt.indexOf(ext) < 0) {
    throw new Error('Jenis berkas tidak diterima. Gunakan: ' + cfg.allowedExt.join(', '));
  }
  if (!req.data) throw new Error('Isi berkas kosong.');
  var bytes = Utilities.base64Decode(req.data);
  if (!bytes.length) throw new Error('Isi berkas kosong.');
  if (bytes.length > cfg.maxMb * 1024 * 1024) {
    throw new Error('Berkas lebih dari ' + cfg.maxMb + ' MB.');
  }
  var salah = periksaIsi_(ext, bytes);   // isi harus cocok dengan ekstensi (2026-11-20)
  if (salah) throw new Error(salah);
  var stamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(),
                                   'yyyyMMdd-HHmmss');
  return Utilities.newBlob(bytes, MIME_BY_EXT[ext], stamp + '_' + safeName_(name));
}

// <FOLDER_ID>/<tahun>/<nama dosen>/. Lock mencegah dua unggahan bersamaan
// membuat folder kembar.
function targetFolder_(cfg, year, lecturerName) {
  year = String(year || '').trim();
  if (!/^\d{4}$/.test(year)) throw new Error('Pilih tahun pada isian dulu.');
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var root = DriveApp.getFolderById(cfg.folderId);
    var yearFolder = childFolder_(root, year);
    return childFolder_(yearFolder, safeName_(lecturerName));
  } finally {
    lock.releaseLock();
  }
}

// Subfolder relatif di dalam folder butir, dari unggah folder di browser
// (webkitRelativePath tanpa nama berkas), mis. 'Laporan AMI/2025'.
// Segmen '.' dan '..' ditolak, kedalaman maksimal 5, tiap segmen dibersihkan.
function subFolder_(base, path) {
  var seg = String(path || '').split(/[\\\/]+/).map(function (s) { return s.trim(); })
    .filter(String);
  if (!seg.length) return base;
  if (seg.length > 5) throw new Error('Subfolder terlalu dalam (maksimal 5 tingkat).');
  seg.forEach(function (s) {
    if (s === '.' || s === '..') throw new Error('Nama subfolder tidak sah: ' + s);
  });
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var f = base;
    seg.forEach(function (s) { f = childFolder_(f, safeName_(s)); });
    return f;
  } finally {
    lock.releaseLock();
  }
}

// Folder satu karya di dalam folder <tahun>/<nama dosen>/, dinamai dari
// judul karya (dipotong 80 karakter). Judul yang sama = folder yang sama,
// jadi unggahan susulan untuk karya itu bergabung ke folder yang sudah ada.
function groupFolder_(parent, judul) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    return childFolder_(parent, safeName_(judul).slice(0, 80));
  } finally {
    lock.releaseLock();
  }
}

function shareFolder_(folder) {
  if (folder.getSharingAccess() !== DriveApp.Access.ANYONE_WITH_LINK) {
    folder.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  }
}

function childFolder_(parent, name) {
  var it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

function safeName_(s) {
  s = String(s).replace(/[\\\/:*?"<>|\r\n\t]+/g, '_').replace(/\s+/g, ' ').trim();
  return (s || 'berkas').slice(0, 120);
}

// Semua berkas di bawah FOLDER_ID, kecuali isi folder `_arsip` (versi
// dokumen lama yang sengaja disimpan). Tiap berkas membawa id folder
// induknya (`induk`), karena sebagian bukti lama dirujuk lewat tautan
// folder, bukan tautan berkas.
function daftarBerkas_(cfg) {
  var hasil = [];
  var antre = [{ folder: DriveApp.getFolderById(cfg.folderId), jalur: '', induk: [] }];
  while (antre.length) {
    var x = antre.shift();
    var induk = x.induk.concat([x.folder.getId()]);
    var fs = x.folder.getFiles();
    while (fs.hasNext()) {
      var f = fs.next();
      hasil.push({ id: f.getId(), nama: f.getName(), url: f.getUrl(), jalur: x.jalur,
                   induk: induk, ukuran: f.getSize(), dibuat: f.getDateCreated().toISOString() });
    }
    var ds = x.folder.getFolders();
    while (ds.hasNext()) {
      var d = ds.next();
      if (d.getName() === '_arsip') continue;
      antre.push({ folder: d, jalur: x.jalur + d.getName() + '/', induk: induk });
    }
  }
  return { ok: true, berkas: hasil };
}

// SHA-256 (hex huruf kecil) isi berkas-berkas Drive pada `urls`. Sama dengan
// sidik yang dihitung browser sebelum mengunggah (site/sidik-berkas.js),
// karena makeBlob_ menyimpan isi berkas apa adanya (hanya namanya diberi
// cap waktu). Tautan bukan berkas Drive, berkas di luar FOLDER_ID, dan
// berkas Google Docs/Sheets (tidak punya isi biner) dilewati dengan alasan.
function sidikBerkas_(cfg, urls) {
  if (!Array.isArray(urls) || !urls.length || urls.length > 10) {
    throw new Error('Kirim 1-10 tautan per permintaan.');
  }
  var hasil = urls.map(function (url) {
    var id = idBerkas_(url);
    if (!id) return { url: url, sha256: null, alasan: 'bukan berkas Google Drive' };
    var file;
    try {
      file = DriveApp.getFileById(id);
    } catch (err) {
      return { url: url, sha256: null, alasan: 'berkas tidak ditemukan' };
    }
    if (!diDalamFolder_(file, cfg.folderId)) {
      return { url: url, sha256: null, alasan: 'di luar folder bukti prodi' };
    }
    if (file.isTrashed()) return { url: url, sha256: null, alasan: 'berkas di Sampah' };
    if (/^application\/vnd\.google-apps\./.test(file.getMimeType())) {
      return { url: url, sha256: null, alasan: 'berkas Google Docs/Sheets' };
    }
    var b = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, file.getBlob().getBytes());
    var hex = b.map(function (x) {
      var v = (x < 0 ? x + 256 : x).toString(16);
      return v.length === 1 ? '0' + v : v;
    }).join('');
    return { url: url, sha256: hex, nama: file.getName(), ukuran: file.getSize(),
             jalur: jalurBerkas_(file, cfg.folderId) };
  });
  return { ok: true, hasil: hasil };
}

// Jalur folder berkas relatif terhadap FOLDER_ID, mis. 'dokumen/lkps_vmts/2025/Visi/'.
function jalurBerkas_(file, rootId) {
  var seg = [], it = file.getParents(), f = it.hasNext() ? it.next() : null;
  for (var i = 0; f && f.getId() !== rootId && i < 20; i++) {
    seg.unshift(f.getName());
    var p = f.getParents();
    f = p.hasNext() ? p.next() : null;
  }
  return seg.length ? seg.join('/') + '/' : '';
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}


// ---------------------------------------------------------------------------
// Berkas nilai CPL (pemilik 2026-11-11, pilihan 2; instal-lengkap.sql).
// Folder: <FOLDER_ID>/berkas-privat/cpl/<TA semester>/<MK-kelas>/, versi lama di riwayat/.

// true bila berkas ada di bawah berkas-privat/cpl/ (memuat NIM).
function nilaiCpl_(cfg, file) {
  return /^berkas-privat\/cpl\//.test(jalurBerkas_(file, cfg.folderId));
}

// Berkas nilai hanya untuk admin; tidak pernah lewat tautan sementara, asesor, sandi, atau token.
function tolakNilaiCpl_(cfg, file, lecturer) {
  if (nilaiCpl_(cfg, file) && !(lecturer && lecturer.peran === 'admin')) {
    throw new Error('Berkas nilai CPL hanya bisa dibuka admin prodi.');
  }
}

// Baris cpl_kelas dibaca dengan token pengunggah: RLS hanya mengembalikan kelasnya sendiri (atau semua bagi admin).
function cplKelas_(cfg, token, id) {
  var n = Number(id);
  if (!(n > 0)) throw new Error('Kelas tidak dipilih.');
  var res = UrlFetchApp.fetch(cfg.url + '/rest/v1/cpl_kelas?select=tahun_akademik,semester,kode_mk,kelas&id=eq.' + n,
    { headers: { apikey: cfg.key, Authorization: 'Bearer ' + token }, muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) throw new Error('Gagal membaca daftar kelas (HTTP ' + res.getResponseCode() + ').');
  var rows = JSON.parse(res.getContentText());
  if (!rows.length) throw new Error('Kelas tidak ditemukan atau bukan kelas Anda.');
  return rows[0];
}

// ---------- Cadangan berkas Drive ke komputer prodi (pemilik 2026-11-20) ----------
// Untuk run_cadangan_drive.py di komputer prodi. Script Property CADANGAN_DRIVE_KUNCI (minimal 32 karakter), sama
// dengan baris CADANGAN_DRIVE_KUNCI di rahasia.env komputer itu; 20 kali salah menutup akses selama satu jam.
//   aksi 'daftar'  : semua berkas di bawah FOLDER_ID (tanpa Sampah): id, jalur folder, nama, ukuran, waktu ubah, jenis;
//   aksi 'ambil'   : potongan isi satu berkas (mulai, panjang <= 20 MB), hanya berkas di dalam FOLDER_ID;
//   aksi 'selesai' : laporan hasil ke panel Kesehatan sistem (status cadangan_drive, 127-patch).
// Berkas Google Dokumen/Spreadsheet asli (bukan unggahan) tidak punya isi biner dan tidak dicadangkan.
var CADANGAN_DRIVE_POTONG_MAKS = 20 * 1024 * 1024;
function cadanganDrive_(cfg, req) {
  var kunci = String(PropertiesService.getScriptProperties().getProperty('CADANGAN_DRIVE_KUNCI') || '').trim();
  if (kunci.length < 32) throw new Error('Script property CADANGAN_DRIVE_KUNCI (minimal 32 karakter) belum diisi.');
  var cache = CacheService.getScriptCache();
  var gagal = Number(cache.get('cdrive_gagal') || 0);
  if (gagal >= 20) throw new Error('Terlalu banyak percobaan. Coba lagi satu jam lagi.');
  if (String(req.kunci || '') !== kunci) {
    cache.put('cdrive_gagal', String(gagal + 1), 3600);
    throw new Error('Kunci salah.');
  }
  if (req.aksi === 'daftar') {
    var out = [], antre = [{ folder: DriveApp.getFolderById(cfg.folderId), jalur: '' }];
    while (antre.length) {
      var x = antre.shift(), it = x.folder.getFiles(), sub = x.folder.getFolders();
      while (it.hasNext()) {
        var f = it.next();
        if (f.isTrashed()) continue;
        out.push({ id: f.getId(), jalur: x.jalur, nama: f.getName(), ukuran: f.getSize(),
                   diubah: f.getLastUpdated().toISOString(), jenis: f.getMimeType() });
      }
      while (sub.hasNext()) {
        var s = sub.next();
        if (!s.isTrashed()) antre.push({ folder: s, jalur: x.jalur ? x.jalur + '/' + s.getName() : s.getName() });
      }
    }
    return { ok: true, berkas: out };
  }
  if (req.aksi === 'ambil') {
    var file = DriveApp.getFileById(String(req.id || ''));
    if (!diDalamFolder_(file, cfg.folderId)) throw new Error('Berkas di luar folder prodi.');
    if (/^application\/vnd\.google-apps\./.test(file.getMimeType())) throw new Error('Berkas Google asli tidak dicadangkan.');
    var bytes = file.getBlob().getBytes(), mulai = Math.max(0, Number(req.mulai) || 0);
    var panjang = Math.min(CADANGAN_DRIVE_POTONG_MAKS, Math.max(1, Number(req.panjang) || CADANGAN_DRIVE_POTONG_MAKS));
    return { ok: true, total: bytes.length, mulai: mulai, data: Utilities.base64Encode(bytes.slice(mulai, mulai + panjang)) };
  }
  if (req.aksi === 'selesai') {
    var h = req.hasil || {}, isi = {};
    ['berkas', 'baru', 'berubah', 'hilang', 'gagal', 'lewat', 'megabita'].forEach(function (k) {
      if (isFinite(Number(h[k]))) isi[k] = Number(h[k]);
    });
    rpc_(cfg, 'sistem_lapor', { p_kunci: mhsConfig_().kunci, p_status: 'cadangan_drive', p_ok: !Number(h.gagal), p_isi: isi });
    return { ok: true };
  }
  throw new Error('Aksi tidak dikenal.');
}

// Pindahkan berkas yang ada (versi lama) ke subfolder riwayat sebelum berkas baru disimpan.
function cplRiwayat_(folder) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var it = folder.getFiles(), riwayat = null;
    while (it.hasNext()) {
      var f = it.next();
      if (!riwayat) riwayat = childFolder_(folder, 'riwayat');
      f.moveTo(riwayat);
    }
  } finally {
    lock.releaseLock();
  }
}

// Blob .xlsx untuk berkas nilai (tidak bergantung pada ALLOWED_EXT), batas ukuran tetap MAX_MB.
function blobCpl_(cfg, req) {
  if (!req.data) throw new Error('Isi berkas kosong.');
  var bytes = Utilities.base64Decode(req.data);
  if (!bytes.length) throw new Error('Isi berkas kosong.');
  if (bytes.length > cfg.maxMb * 1024 * 1024) throw new Error('Berkas lebih dari ' + cfg.maxMb + ' MB.');
  var salah = periksaIsi_('xlsx', bytes);   // isi harus berkas Excel tanpa makro (2026-11-20)
  if (salah) throw new Error(salah);
  var stamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd-HHmmss');
  return Utilities.newBlob(bytes, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           stamp + '_' + safeName_(String(req.filename || 'nilai.xlsx')));
}

// Unduh berkunci untuk run_cpl.py. Script Property CPL_KUNCI (minimal 32 karakter);
// 20 kali salah menutup akses selama satu jam. aksi 'daftar': berkas terbaru tiap kelas
// (tanpa riwayat); aksi 'ambil': isi satu berkas (base64), hanya dari folder kelas.
function cplUnduh_(cfg, req) {
  var kunci = String(PropertiesService.getScriptProperties().getProperty('CPL_KUNCI') || '').trim();
  if (kunci.length < 32) throw new Error('Script property CPL_KUNCI (minimal 32 karakter) belum diisi.');
  var cache = CacheService.getScriptCache();
  var gagal = Number(cache.get('cpl_gagal') || 0);
  if (gagal >= 20) throw new Error('Terlalu banyak percobaan. Coba lagi satu jam lagi.');
  if (String(req.kunci || '') !== kunci) {
    cache.put('cpl_gagal', String(gagal + 1), 3600);
    throw new Error('Kunci salah.');
  }
  if (req.aksi === 'daftar') {
    var out = [], akar = privatFolder_(cfg, ['cpl']), sem = akar.getFolders();
    while (sem.hasNext()) {
      var fs = sem.next(), kls = fs.getFolders();
      while (kls.hasNext()) {
        var fk = kls.next(), it = fk.getFiles();
        while (it.hasNext()) {
          var f = it.next();
          out.push({ id: f.getId(), semester: fs.getName(), kelas: fk.getName(), nama: f.getName(),
                     ukuran: f.getSize(), diubah: f.getLastUpdated().toISOString() });
        }
      }
    }
    return { ok: true, berkas: out };
  }
  // Hitung CPL otomatis (pemilik 2026-11-17, OBE O4; tools/cpl_otomatis.py di GitHub Actions):
  // masukan tambahan dari berkas-privat/cpl-masukan/ (nilai akhir kampus, CSV mahasiswa/perwalian, foto),
  // laporan ber-NIM disimpan ke berkas-privat/cpl-laporan/<waktu>/. Semua privat.
  if (req.aksi === 'masukan_daftar') {
    var hasilM = [];
    (function jalan(f, awal) {
      var it = f.getFiles();
      while (it.hasNext()) {
        var b = it.next();
        // dibuat = saat masuk Drive: unggahan peramban mempertahankan tanggal ubah asli berkas (bisa lama).
        hasilM.push({ id: b.getId(), jalur: awal + b.getName(), ukuran: b.getSize(), diubah: b.getLastUpdated().toISOString(),
                      dibuat: b.getDateCreated().toISOString() });
      }
      var sub = f.getFolders();
      while (sub.hasNext()) { var s2 = sub.next(); jalan(s2, awal + s2.getName() + '/'); }
    })(privatFolder_(cfg, ['cpl-masukan']), '');
    return { ok: true, berkas: hasilM };
  }
  if (req.aksi === 'masukan_ambil') {
    var fm = DriveApp.getFileById(String(req.id || ''));
    if (!/^berkas-privat\/cpl-masukan\//.test(jalurBerkas_(fm, cfg.folderId))) throw new Error('Bukan berkas masukan CPL.');
    return { ok: true, nama: fm.getName(), data: Utilities.base64Encode(fm.getBlob().getBytes()) };
  }
  if (req.aksi === 'laporan_simpan') {
    var folderL = String(req.folder || ''), jalurL = String(req.jalur || '').split('/');
    if (!/^\d{4}-\d{2}-\d{2} \d{4} UTC$/.test(folderL) || jalurL.length > 2
        || jalurL.some(function (x) { return !/^[\w.\- ]{1,120}$/.test(x) || x === '.' || x === '..'; })) {
      throw new Error('Jalur laporan tidak sah.');
    }
    var tujuan = privatFolder_(cfg, ['cpl-laporan', folderL].concat(jalurL.slice(0, -1)));
    var bytes = Utilities.base64Decode(String(req.data || ''));
    if (bytes.length > 45 * 1024 * 1024) throw new Error('Laporan terlalu besar (> 45 MB).');
    var fl = tujuan.createFile(Utilities.newBlob(bytes, null, jalurL[jalurL.length - 1]));
    fl.setDescription('Laporan CPL otomatis (memuat NIM), GitHub Actions ' + folderL);
    return { ok: true, id: fl.getId() };
  }
  if (req.aksi === 'ambil') {
    var file = DriveApp.getFileById(String(req.id || ''));
    if (!/^berkas-privat\/cpl\/[^\/]+\/[^\/]+\/$/.test(jalurBerkas_(file, cfg.folderId))) {
      throw new Error('Bukan berkas nilai CPL terbaru.');
    }
    return { ok: true, nama: file.getName(), data: Utilities.base64Encode(file.getBlob().getBytes()) };
  }
  throw new Error('Aksi tidak dikenal.');
}

// =====================================================================
//  Pengajuan mahasiswa KP/lomba (instal-lengkap.sql, pemilik 2026-11-17)
//
//  Script Properties tambahan (hanya untuk fitur ini):
//    MHS_KUNCI   hasil: select kunci from public.layanan_kunci;  (Supabase SQL Editor)
//    MHS_DOMAIN  domain email kampus mahasiswa, mis. student.kampus.ac.id;
//                email = <NIM>@<MHS_DOMAIN>
//    MHS_SITUS   alamat situs dengan garis miring akhir, mis. https://<organisasi>.github.io/<repo-situs>/
//  Token tautan hanya dikirim ke email kampus, tidak pernah ke peramban yang mengajukan.
//  Berkas: data-lkps/berkas-privat/mahasiswa/<jenis>/<tahun>/<NIM nama>/ (privat); foto lomba dan foto kabar kegiatan (144)
//  di data-lkps/mahasiswa-foto/<tahun>/ dibagikan dengan tautan supaya bisa tampil di halaman prestasi dan kabar.
// =====================================================================
// 99: nilai_lapangan tidak lagi diunggah mahasiswa (dosen pembimbing/koordinator KP/admin lewat mhs_unggah_prodi).
var MHS_BERKAS = { kp: ['surat_permohonan', 'surat_balasan', 'laporan_kp', 'surat_selesai', 'logbook', 'foto', 'lainnya'],
                   lomba: ['laporan_lomba', 'sertifikat', 'surat_tugas', 'foto', 'lainnya'],
                   surat: ['lainnya'],   // 93: lampiran pendukung (mis. proposal)
                   ta: ['naskah_ta', 'lainnya'],   // 94: seminar/sidang TA
                   luaran: ['bukti_luaran', 'lainnya'],   // 96: publikasi/luaran mahasiswa
                   kabar: ['foto', 'lainnya'] };   // 144: kabar kegiatan dari mahasiswa (foto tampil di situs publik)
// 122: berkas yudisium berkode yud_* dari tabel yudisium_berkas (admin bisa mengubah daftarnya); kodenya diperiksa SQL.
var MHS_BERKAS_YUDISIUM = /^yud_[a-z0-9_]{2,40}$/;
// Mahasiswa hanya mengunggah PDF dan gambar (pemilik 2026-11-20): berkas Office bisa membawa kode berbahaya ke komputer
// pemeriksa. Berlaku untuk semua jenis pengajuan; berkas dari prodi (surat pengantar, dll.) tetap mengikuti ALLOWED_EXT.
var MHS_EXT = ['pdf', 'jpg', 'jpeg', 'png'];
var MHS_JENIS = { kp: 'Kerja Praktik', lomba: 'laporan lomba', surat: 'surat', ta: 'seminar/sidang TA', luaran: 'laporan publikasi/luaran',
                  yudisium: 'berkas yudisium', kabar: 'kabar kegiatan' };
var MHS_STATUS_TEKS = { dikembalikan: 'dikembalikan untuk diperbaiki', ditolak: 'ditolak', disetujui: 'disetujui',
                        admin: 'disetujui dosen pembimbing dan sedang diperiksa admin' };

function mhsConfig_() {
  var p = PropertiesService.getScriptProperties();
  var c = { kunci: String(p.getProperty('MHS_KUNCI') || '').trim(),
            domain: String(p.getProperty('MHS_DOMAIN') || '').trim().replace(/^@/, '').toLowerCase(),
            situs: String(p.getProperty('MHS_SITUS') || '').trim() };
  if (c.kunci.length < 32 || !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(c.domain) || !/^https:\/\/\S+\/$/.test(c.situs)) {
    throw new Error('Layanan pengajuan mahasiswa belum disiapkan admin (Script Property MHS_KUNCI, MHS_DOMAIN, MHS_SITUS).');
  }
  return c;
}

// Panggil fungsi Supabase. bearer kosong = sebagai anon (kunci publik).
function rpc_(cfg, nama, args, bearer) {
  var res = UrlFetchApp.fetch(cfg.url + '/rest/v1/rpc/' + nama, { method: 'post', contentType: 'application/json',
    payload: JSON.stringify(args || {}), muteHttpExceptions: true,
    headers: { apikey: cfg.key, Authorization: 'Bearer ' + (bearer || cfg.key) } });
  var teks = res.getContentText(), isi = null;
  try { isi = JSON.parse(teks); } catch (e) { isi = teks; }
  if (res.getResponseCode() >= 300) {
    throw new Error((isi && isi.message) || ('Gagal (' + nama + ', HTTP ' + res.getResponseCode() + ').'));
  }
  return isi;
}

function mhsNim_(v) {
  var nim = String(v || '').trim();
  if (!/^[0-9]{6,15}$/.test(nim)) throw new Error('NIM harus angka 6-15 digit.');
  return nim;
}

function mhsTautanTeks_(m, t) { return m.situs + 'pengajuan.html#t=' + t; }

// Email alternatif (104): alamat tersamar untuk layar, mis. an***@gmail.com.
function mhsSamar_(email) {
  var x = String(email || '').split('@');
  return x.length === 2 ? x[0].slice(0, 2) + '***@' + x[1] : '';
}
// Tujuan kirim: email kampus + email alternatif aktif NIM itu (bila ada). Hasil {to, alt}.
function mhsTujuan_(cfg, m, nim, utama) {
  var alt = String(rpc_(cfg, 'mhs_email_alt_tujuan', { p_kunci: m.kunci, p_nim: nim }) || '').trim().toLowerCase();
  if (alt === String(utama || '').trim().toLowerCase()) alt = '';
  return { to: alt ? utama + ',' + alt : utama, alt: alt };
}
function mhsTeksTujuan_(utama, alt) { return utama + (alt ? ' dan email alternatif ' + mhsSamar_(alt) : ''); }

// Jalur A langkah 1: tautan konfirmasi dikirim ke EMAIL KAMPUS, bukan ke email alternatif.
function mhsEmailAlt_(cfg, req) {
  if (String(req.jebakan || '').trim()) return { ok: true };
  var m = mhsConfig_(), nim = mhsNim_(req.nim), kampus = nim + '@' + m.domain;
  var alt = String(req.email || '').trim().toLowerCase();
  if (alt.split('@')[1] === m.domain) throw new Error('Email alternatif harus di luar email kampus.');
  if (MailApp.getRemainingDailyQuota() < 1) throw new Error('Kuota email prodi hari ini habis. Coba lagi besok.');
  var token = rpc_(cfg, 'mhs_email_alt_minta', { p_kunci: m.kunci, p_nim: nim, p_email: alt });
  MailApp.sendEmail({ to: kampus, name: 'Program Studi', subject: 'Konfirmasi email alternatif layanan mahasiswa',
    body: 'Ada permintaan memakai ' + alt + ' sebagai email alternatif layanan mahasiswa untuk NIM ' + nim + '.\n\n'
      + 'Bila itu Anda, buka tautan berikut dalam 2 hari untuk mengaktifkannya:\n\n' + m.situs + 'pengajuan.html#alt=' + token
      + '\n\nSesudah aktif, tautan dan kabar pengajuan dikirim ke email kampus dan email alternatif itu.\n\n'
      + 'Bila Anda tidak memintanya, abaikan email ini; email alternatif tidak aktif tanpa tautan di atas.' });
  return { ok: true, email: kampus };
}

// Jalur A langkah 2: tautan dari email kampus. Pemberitahuan dikirim ke kedua alamat.
function mhsEmailAltKonfirmasi_(cfg, req) {
  var m = mhsConfig_();
  var r = rpc_(cfg, 'mhs_email_alt_konfirmasi', { p_kunci: m.kunci, p_token: String(req.token || '') });
  if (MailApp.getRemainingDailyQuota() >= 1) {
    MailApp.sendEmail({ to: r.nim + '@' + m.domain + ',' + r.email, name: 'Program Studi', subject: 'Email alternatif aktif',
      body: 'Email alternatif ' + r.email + ' sekarang aktif untuk layanan mahasiswa NIM ' + r.nim + '. Tautan dan kabar '
        + 'pengajuan dikirim ke email kampus dan email alternatif ini.\n\nBila Anda tidak merasa mengaktifkannya, segera '
        + 'hubungi admin prodi.' });
  }
  return { ok: true, email: mhsSamar_(r.email) };
}

function mhsAjukan_(cfg, req) {
  if (String(req.jebakan || '').trim()) return { ok: true };   // kolom jebakan terisi: pura-pura berhasil
  var m = mhsConfig_(), nim = mhsNim_(req.nim), email = nim + '@' + m.domain;
  if (MailApp.getRemainingDailyQuota() < 1) throw new Error('Kuota email prodi hari ini habis. Coba lagi besok.');
  var token = rpc_(cfg, 'mhs_buat', { p_kunci: m.kunci, p_jenis: req.jenis, p_nim: nim, p_nama: String(req.nama || ''),
    p_email: email, p_pembimbing: req.pembimbing_id || null, p_data: req.data || {} });
  var tj = mhsTujuan_(cfg, m, nim, email);
  MailApp.sendEmail({ to: tj.to, name: 'Program Studi', subject: 'Tautan pengajuan ' + (MHS_JENIS[req.jenis] || '') + ' Anda',
    body: 'Halo ' + String(req.nama || '').trim() + ',\n\nPengajuan ' + (MHS_JENIS[req.jenis] || '') + ' Anda sudah dibuat '
      + 'sebagai draf. Buka tautan pribadi berikut untuk mengunggah berkas, memeriksa isian, lalu menekan "Kirim untuk diperiksa":\n\n'
      + mhsTautanTeks_(m, token) + '\n\nSimpan email ini; tautan yang sama dipakai untuk melihat proses pemeriksaan. '
      + 'Jangan teruskan tautan ini ke orang lain.\n\nBila Anda tidak merasa mengajukan, abaikan email ini.' });
  return { ok: true, email: mhsTeksTujuan_(email, tj.alt) };
}

// Tautan baru untuk semua pengajuan satu NIM. Jawaban sama walau NIM tidak punya pengajuan.
function mhsTautanUlang_(cfg, req) {
  if (String(req.jebakan || '').trim()) return { ok: true };
  var m = mhsConfig_(), nim = mhsNim_(req.nim);
  if (MailApp.getRemainingDailyQuota() < 1) throw new Error('Kuota email prodi hari ini habis. Coba lagi besok.');
  var xs = rpc_(cfg, 'mhs_tautan_ulang', { p_kunci: m.kunci, p_nim: nim }) || [];
  // Alamat di layar tidak bergantung pada ada/tidaknya pengajuan (tidak membocorkan apa pun tentang NIM itu).
  var kampusU = nim + '@' + m.domain;
  if (xs.length) {
    MailApp.sendEmail({ to: mhsTujuan_(cfg, m, nim, xs[0].email).to, name: 'Program Studi', subject: 'Tautan baru pengajuan Anda',
      body: 'Tautan baru pengajuan Anda (tautan lama tidak berlaku lagi):\n\n' + xs.map(function (x) {
        return '- ' + (MHS_JENIS[x.jenis] || x.jenis) + (x.judul ? ' (' + x.judul + ')' : '') + ':\n  ' + mhsTautanTeks_(m, x.token);
      }).join('\n') + '\n\nJangan teruskan tautan ini ke orang lain.' });
  }
  return { ok: true, email: kampusU + ' (dan email alternatif, bila sudah aktif)' };
}

// Folder berkas satu pengajuan; foto lomba dan kabar kegiatan (144) ke folder bertautan (lihat kepala bagian ini).
function mhsFolder_(cfg, p, jenisBerkas) {
  if ((p.jenis === 'lomba' || p.jenis === 'kabar') && jenisBerkas === 'foto') {
    var lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      return { folder: childFolder_(childFolder_(DriveApp.getFolderById(cfg.folderId), 'mahasiswa-foto'), String(p.tahun)),
               privat: false };
    } finally { lock.releaseLock(); }
  }
  return { folder: privatFolder_(cfg, ['mahasiswa', p.jenis, String(p.tahun), p.nim + ' ' + p.nama]), privat: true };
}

function mhsSimpan_(cfg, p, jenisBerkas, req, keterangan) {
  var t = mhsFolder_(cfg, p, jenisBerkas);
  var file = t.folder.createFile(makeBlob_(cfg, req));
  if (!t.privat) file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  file.setDescription(keterangan);
  return file;
}

function mhsUnggah_(cfg, req) {
  var m = mhsConfig_();
  var p = rpc_(cfg, 'mhs_cek', { p_kunci: m.kunci, p_token: String(req.t || '') });
  if (!p.boleh_ubah) throw new Error('Pengajuan sedang diperiksa; berkas tidak bisa ditambah.');
  var jb = String(req.jenis_berkas || '');
  var sah = p.jenis === 'yudisium' ? MHS_BERKAS_YUDISIUM.test(jb) : (MHS_BERKAS[p.jenis] || []).indexOf(jb) >= 0;
  if (!sah) throw new Error('Jenis berkas tidak dikenal.');
  var maks = p.jenis === 'yudisium' ? 40 : 20;   // 122: yudisium 14 berkas wajib + tambahan
  if (p.berkas >= maks) throw new Error('Paling banyak ' + maks + ' berkas per pengajuan.');
  var ext = (String(req.filename || '').match(/\.([A-Za-z0-9]+)$/) || [, ''])[1].toLowerCase();
  if (MHS_EXT.indexOf(ext) < 0) throw new Error('Mahasiswa hanya bisa mengunggah PDF, JPG, atau PNG. Simpan berkas Word/Excel sebagai PDF dulu.');
  var file = mhsSimpan_(cfg, p, jb, req, 'Pengajuan mahasiswa #' + p.id + ' (' + jb + '), diunggah mahasiswa ' + p.nim);
  try {
    var id = rpc_(cfg, 'mhs_catat_berkas', { p_kunci: m.kunci, p_token: String(req.t), p_jenis: jb,
      p_nama: String(req.filename || '').slice(0, 200), p_url: file.getUrl() });
    return { ok: true, id: id, name: file.getName() };
  } catch (e) {
    file.setTrashed(true);   // tidak tercatat: jangan tinggalkan berkas tak terpakai
    throw e;
  }
}

// Buka (isi berkas) atau buang (ke Sampah Drive) berkas milik pengajuan bertoken.
function mhsBerkas_(cfg, req, buang) {
  var m = mhsConfig_();
  var url = rpc_(cfg, 'mhs_berkas', { p_kunci: m.kunci, p_token: String(req.t || ''), p_berkas: Number(req.berkas),
                                      p_buang: !!buang });
  if (buang) return buangBerkas_(cfg, url);
  var file = DriveApp.getFileById(idBerkas_(url));
  if (!diDalamFolder_(file, cfg.folderId)) throw new Error('Berkas di luar folder prodi.');
  return isiBerkas_(file);
}

// Baca satu baris dengan token login (RLS: admin, atau pembimbing pengajuan itu).
function mhsBaca_(cfg, token, tabel, kolom, id) {
  var res = UrlFetchApp.fetch(cfg.url + '/rest/v1/' + tabel + '?select=' + kolom + '&id=eq.' + Number(id),
    { headers: { apikey: cfg.key, Authorization: 'Bearer ' + token }, muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) throw new Error('Gagal membaca ' + tabel + ' (HTTP ' + res.getResponseCode() + ').');
  var rows = JSON.parse(res.getContentText());
  if (!rows.length) throw new Error('Tidak ditemukan, atau bukan pengajuan yang Anda bimbing.');
  return rows[0];
}

function mhsBukaProdi_(cfg, req) {
  var b = mhsBaca_(cfg, req.token, 'pengajuan_berkas', 'url', req.berkas);
  var file = DriveApp.getFileById(idBerkas_(b.url));
  if (!diDalamFolder_(file, cfg.folderId)) throw new Error('Berkas di luar folder prodi.');
  return isiBerkas_(file);
}

// Surat pengantar (admin) atau berkas lain dari prodi; dicatat dengan token login pengunggah.
function mhsUnggahProdi_(cfg, lecturer, req) {
  var p = mhsBaca_(cfg, req.token, 'pengajuan_mahasiswa', 'id,jenis,nim,nama,dibuat', req.pengajuan_id);
  p.tahun = String(p.dibuat).slice(0, 4);
  var jb = String(req.jenis_berkas || 'surat_pengantar');
  var file = mhsSimpan_(cfg, p, jb, req, 'Pengajuan mahasiswa #' + p.id + ' (' + jb + '), diunggah ' + lecturer.email);
  try {
    var id = rpc_(cfg, 'pengajuan_catat_berkas', { p_id: p.id, p_jenis: jb, p_nama: String(req.filename || '').slice(0, 200),
                                                   p_url: file.getUrl() }, req.token);
    return { ok: true, id: id, name: file.getName() };
  } catch (e) {
    file.setTrashed(true);
    throw e;
  }
}

// ---------- Email ke pemeriksa (123/124-patch-kabar-pemeriksa*.sql, pemilik 2026-11-20) ----------
// Pemicu per jam (kirimKabarPemeriksa), HANYA pada jam kerja (Senin-Jumat 09.00-16.00 WIB, bukan hari libur di tabel
// hari_libur, instal-lengkap.sql). Basis data menentukan yang jatuh tempo dan penerimanya:
//   - 1 jam setelah pengajuan masuk tahap dan belum diputuskan: pemeriksa yang belum membuka ruang kerja sejak itu;
//   - 24 jam setelah masuk dan masih belum diputuskan: pengingat ke semua pemeriksa tahap itu (sekali).
// Kuota email habis: tidak ditandai, dicoba lagi pada putaran berikutnya.
// Pasang pemicunya SEKALI: di editor pilih fungsi pasangPemicuKabarPemeriksa lalu Run (izinkan akses).
var KABAR_PEMERIKSA_MENIT = 60;          // pemilik 2026-11-20: "jika dalam satu jam belum di-approve"
var KABAR_PEMERIKSA_PENGINGAT = 24 * 60; // pemilik 2026-11-20: sudah di ruang kerja tapi 24 jam belum di-approve
var KABAR_PEMERIKSA_JAM = [9, 16];       // pemilik 2026-11-20: jam kerja 9-16 (WIB), hari kerja
var KABAR_PEMERIKSA_ZONA = 'Asia/Jakarta';

// Senin-Jumat, 09.00 <= jam < 16.00 WIB.
function jamKerja_(kini) {
  var hari = Number(Utilities.formatDate(kini || new Date(), KABAR_PEMERIKSA_ZONA, 'u'));   // 1 = Senin ... 7 = Minggu
  var jam = Number(Utilities.formatDate(kini || new Date(), KABAR_PEMERIKSA_ZONA, 'H'));
  return hari >= 1 && hari <= 5 && jam >= KABAR_PEMERIKSA_JAM[0] && jam < KABAR_PEMERIKSA_JAM[1];
}

// Hari libur (139, pemilik 2026-11-21): { 'yyyy-MM-dd': nama } untuk Senin-Minggu minggu tanggal `kini` (WIB). Basis data
// tidak terbaca (mis. patch 139 belum dijalankan) = tidak ada hari libur, supaya email tidak berhenti.
function tanggalWib_(d) { return Utilities.formatDate(d, KABAR_PEMERIKSA_ZONA, 'yyyy-MM-dd'); }
function liburMingguIni_(cfg, kini) {
  var k = kini || new Date(), u = Number(Utilities.formatDate(k, KABAR_PEMERIKSA_ZONA, 'u'));
  var geser = function (n) { return tanggalWib_(new Date(k.getTime() + n * 864e5)); };
  var out = {};
  try {
    (rpc_(cfg, 'hari_libur_antara', { p_dari: geser(1 - u), p_sampai: geser(7 - u) }) || [])
      .forEach(function (x) { out[String(x.tanggal).slice(0, 10)] = x.nama; });
  } catch (e) { Logger.log('Hari libur tidak terbaca (jalankan supabase/instal-lengkap.sql?): ' + e.message); }
  return out;
}
// Hari kerja pertama minggu ini: Senin-Jumat, bukan libur, dan semua hari kerja sebelumnya di minggu ini libur.
function hariKerjaPertama_(kini, libur) {
  var k = kini || new Date(), u = Number(Utilities.formatDate(k, KABAR_PEMERIKSA_ZONA, 'u')), lb = libur || {};
  if (u > 5 || lb[tanggalWib_(k)]) return false;
  for (var n = 1; n < u; n++) if (!lb[tanggalWib_(new Date(k.getTime() - (u - n) * 864e5))]) return false;
  return true;
}

function kabariPemeriksa_(cfg, m, id) {
  var x = rpc_(cfg, 'mhs_pemeriksa', { p_kunci: m.kunci, p_id: Number(id), p_jam1: KABAR_PEMERIKSA_MENIT, p_jam24: KABAR_PEMERIKSA_PENGINGAT });
  if (!x || !x.perlu) return 'lewat';
  var tandai = function () {
    rpc_(cfg, 'mhs_pemeriksa_tandai', { p_kunci: m.kunci, p_id: x.id, p_kunci_tahap: x.kunci_tahap, p_tingkat: x.tingkat });
  };
  var ke = (x.penerima || []).map(function (r) { return r.email; });
  if (!ke.length) { tandai(); return 'sudah dilihat di ruang kerja'; }
  if (MailApp.getRemainingDailyQuota() < ke.length) return 'kuota habis';
  var jenis = x.jenis === 'kp' && x.tahap === 'selesai' ? 'laporan selesai KP' : (MHS_JENIS[x.jenis] || x.jenis);
  var siapa = x.status === 'pembimbing'
    ? (x.jenis === 'lomba' || x.jenis === 'kabar' ? 'dosen pembimbing atau pembina kemahasiswaan' : 'dosen pembimbing')
    : ({ kp: 'koordinator KP', ta: 'koordinator TA', lomba: 'pembina kemahasiswaan', luaran: 'pembina kemahasiswaan',
         kabar: 'pembina kemahasiswaan' }[x.jenis] || 'admin prodi');
  var ingat = x.tingkat === 24;
  MailApp.sendEmail({ to: ke.join(','), name: 'Program Studi',
    subject: ((ingat ? 'Pengingat: belum diperiksa 24 jam: ' : 'Menunggu pemeriksaan: ') + jenis + ' ' + x.nama + ' (' + x.nim + ')').slice(0, 200),
    body: 'Yth. Bapak/Ibu,\n\nPengajuan berikut menunggu pemeriksaan ' + siapa
      + (ingat ? ' dan belum diputuskan lebih dari 24 jam' : ' lebih dari satu jam') + ':\n\n'
      + '- Mahasiswa: ' + x.nama + ' (' + x.nim + ')\n- Jenis: ' + jenis + '\n- Judul: ' + (x.judul || '-') + '\n\n'
      + 'Buka Ruang kerja > Kemahasiswaan > Pengajuan mahasiswa:\n' + m.situs + 'pengajuan-mahasiswa.html\n\n'
      + (ingat ? 'Ini pengingat terakhir untuk tahap ini.' : 'Bila belum diputuskan dalam 24 jam, dikirim satu pengingat lagi.')
      + ' Pengajuan yang sama juga tampil di Tugas saya.' });
  tandai();
  return ingat ? 'pengingat 24 jam' : 'kabar 1 jam';
}

// Dijalankan pemicu per jam (tanpa garis bawah supaya bisa dipilih di daftar pemicu). Di luar jam kerja tidak mengirim apa pun;
// yang jatuh tempo dikirim pada putaran pertama jam kerja berikutnya.
function kirimKabarPemeriksa() {
  // Kesehatan sistem (125): tiap jam, juga di luar jam kerja, melapor bahwa pemicu ini hidup (+ kuota email, Drive).
  laporAppsScript_();
  kirimPeringatanKeamanan_();   // 126: kapan pun, tidak menunggu jam kerja
  if (!jamKerja_()) { Logger.log('Di luar jam kerja (Senin-Jumat 09.00-16.00 WIB): tidak mengirim.'); return; }
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;   // putaran sebelumnya masih berjalan
  try {
    var cfg = readConfig_(), m = mhsConfig_(), hit = {};
    var libur = liburMingguIni_(cfg), hariIni = tanggalWib_(new Date());
    if (libur[hariIni]) { Logger.log('Hari libur (' + libur[hariIni] + '): tidak mengirim.'); return; }
    try { ringkasanMingguan_(cfg, m, libur); } catch (e) { Logger.log('Ringkasan mingguan: ' + e.message); }
    var ids = rpc_(cfg, 'mhs_pemeriksa_antrean', { p_kunci: m.kunci, p_jam1: KABAR_PEMERIKSA_MENIT, p_jam24: KABAR_PEMERIKSA_PENGINGAT }) || [];
    ids.forEach(function (id) {
      var h;
      try { h = kabariPemeriksa_(cfg, m, id); } catch (e) { h = 'galat'; Logger.log('Pengajuan #' + id + ': ' + e.message); }
      hit[h] = (hit[h] || 0) + 1;
    });
    Logger.log('Kabar pemeriksa: ' + JSON.stringify(hit));
  } finally { lock.releaseLock(); }
}

// ---------- Peringatan keamanan (instal-lengkap.sql, pemilik 2026-11-20) ----------
// Tiap jam, kapan pun: tindakan sensitif yang tercatat di basis data (peran/email dosen berubah, akun berperan khusus
// dibuat atau dihapus, penugasan koordinator berubah, hapus massal) dikirim dalam satu email ke semua admin prodi.
var KEAMANAN_LABEL = { akun_baru: 'Akun baru berperan khusus', peran: 'Peran berubah', email: 'Email login berubah',
                       akun_dihapus: 'Akun dihapus', koordinator: 'Penugasan koordinator', hapus_massal: 'Hapus massal' };
function kirimPeringatanKeamanan_() {
  try {
    var cfg = readConfig_(), m = mhsConfig_();
    var x = rpc_(cfg, 'keamanan_antrean', { p_kunci: m.kunci });
    var xs = x.peringatan || [], ke = x.admin || [];
    if (!xs.length || !ke.length || MailApp.getRemainingDailyQuota() < ke.length) return;
    var tgl = function (s) { return Utilities.formatDate(new Date(s), KABAR_PEMERIKSA_ZONA, 'd MMM yyyy HH:mm') + ' WIB'; };
    MailApp.sendEmail({ to: ke.join(','), name: 'Program Studi',
      subject: 'Peringatan keamanan situs prodi: ' + xs.length + ' tindakan sensitif',
      body: 'Tindakan berikut tercatat di situs prodi. Bila bukan Anda atau rekan admin yang melakukannya, segera:\n'
        + '1) periksa Pengelolaan > Kelola dosen dan Penugasan koordinator;\n'
        + '2) minta pemilik akun yang bersangkutan menekan Keluar (mengakhiri sesi di semua perangkat) dan mengamankan emailnya;\n'
        + '3) lihat rinciannya di Pengelolaan > Jejak perubahan.\n\n'
        + xs.map(function (p) {
            return '- ' + tgl(p.waktu) + ' | ' + (KEAMANAN_LABEL[p.jenis] || p.jenis) + ' | oleh ' + p.oleh + '\n  ' + p.rinci;
          }).join('\n') + '\n\n' + m.situs + 'jejak.html' });
    rpc_(cfg, 'keamanan_tandai', { p_kunci: m.kunci, p_ids: xs.map(function (p) { return p.id; }) });
  } catch (e) { Logger.log('Peringatan keamanan: ' + e.message); }
}

// ---------- Kesehatan sistem (instal-lengkap.sql, pemilik 2026-11-20) ----------
// Tiap jam: status apps_script (sisa kuota email hari ini, pemakaian Drive akun prodi). Galat diabaikan: laporan
// kesehatan tidak boleh menghentikan email pemeriksa.
function laporAppsScript_() {
  try {
    var cfg = readConfig_(), m = mhsConfig_(), isi = { kuota_email: MailApp.getRemainingDailyQuota() };
    try { isi.drive_terpakai = DriveApp.getStorageUsed(); isi.drive_batas = DriveApp.getStorageLimit(); } catch (e) { /* tanpa izin Drive */ }
    rpc_(cfg, 'sistem_lapor', { p_kunci: m.kunci, p_status: 'apps_script', p_ok: true, p_isi: isi });
  } catch (e) { Logger.log('Lapor kesehatan: ' + e.message); }
}

// Hari kerja pertama minggu itu (Senin, atau sesudahnya bila Senin libur; 139) pada jam kerja (dipanggil kirimKabarPemeriksa
// setelah pemeriksaan jam kerja): satu email ringkasan ke admin prodi, bila belum terkirim dalam 3 hari terakhir.
// Penilaian dari basis data (sistem_periksa), sama dengan Dasbor.
var KESEHATAN_LABEL = { baik: 'baik', terlambat: 'TERLAMBAT', gagal: 'GAGAL', belum_ada: 'belum pernah melapor',
                        perlu_dicek: 'PERLU DICEK', info: 'info' };
function ringkasanMingguan_(cfg, m, libur) {
  if (!hariKerjaPertama_(new Date(), libur)) return;
  var x = rpc_(cfg, 'sistem_kesehatan_kunci', { p_kunci: m.kunci });
  if (x.ringkasan_terakhir && new Date() - new Date(x.ringkasan_terakhir) < 3 * 864e5) return;
  var ke = x.admin || [];
  if (!ke.length || MailApp.getRemainingDailyQuota() < ke.length) return;
  var tgl = function (s) { return s ? Utilities.formatDate(new Date(s), KABAR_PEMERIKSA_ZONA, 'd MMM yyyy HH:mm') + ' WIB' : '-'; };
  var baris = (x.butir || []).map(function (b) {
    return '- ' + b.label + ': ' + (KESEHATAN_LABEL[b.status] || b.status) + ' (terakhir ' + tgl(b.waktu) + ')' + (b.rinci ? '\n    ' + b.rinci : '');
  });
  var n = Number(x.perlu_dicek || 0);
  MailApp.sendEmail({ to: ke.join(','), name: 'Program Studi',
    subject: 'Kesehatan sistem situs prodi: ' + (n ? n + ' butir perlu dicek' : 'semua baik'),
    body: 'Ringkasan mingguan kesehatan sistem situs prodi.\n\n' + baris.join('\n')
      + '\n\nUkuran basis data: ' + x.basis_data_mb + ' MB.\n\nRincian terkini: Ruang kerja > Pemantauan > Dasbor operasional\n'
      + m.situs + 'dasbor.html' });
  rpc_(cfg, 'sistem_lapor', { p_kunci: m.kunci, p_status: 'ringkasan_mingguan', p_ok: true, p_isi: { perlu_dicek: n } });
}

// Jalankan sekali dari editor: memasang pemicu per jam (pemicu lama untuk fungsi yang sama dihapus dulu).
function pasangPemicuKabarPemeriksa() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'kirimKabarPemeriksa') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('kirimKabarPemeriksa').timeBased().everyHours(1).create();
  Logger.log('Pemicu per jam untuk kirimKabarPemeriksa terpasang.');
}

// Kabari mahasiswa (dikembalikan, ditolak, disetujui) dengan tautan baru; tautan lama tidak berlaku.
function mhsKabari_(cfg, lecturer, req) {
  var m = mhsConfig_();
  var p = mhsBaca_(cfg, req.token, 'pengajuan_mahasiswa', 'id,jenis,nim,nama,email,status,tahap,data,pembimbing_id', req.pengajuan_id);
  if (!MHS_STATUS_TEKS[p.status]) return { ok: true, terkirim: false };
  // Kalimat kabar: "Pengajuan Kerja Praktik Anda disetujui"; laporan selesai KP (91) punya kalimat sendiri.
  var kabar = 'Pengajuan ' + (MHS_JENIS[p.jenis] || '') + ' Anda ' + MHS_STATUS_TEKS[p.status];
  if (p.jenis === 'surat') {   // instal-lengkap.sql
    kabar = { disetujui: 'Surat Anda sudah terbit; unduh lewat tautan pribadi Anda', dikembalikan: 'Permohonan surat Anda dikembalikan untuk diperbaiki',
              ditolak: 'Permohonan surat Anda ditolak' }[p.status] || kabar;
  }
  if (p.jenis === 'kabar') {   // instal-lengkap.sql: disahkan = langsung terbit di situs prodi
    kabar = { disetujui: 'Kabar kegiatan Anda sudah diverifikasi dan terbit di situs program studi',
              dikembalikan: 'Kabar kegiatan Anda dikembalikan untuk diperbaiki', ditolak: 'Kabar kegiatan Anda ditolak' }[p.status] || kabar;
  }
  if (p.jenis === 'yudisium') {   // instal-lengkap.sql: diperiksa admin prodi saja
    kabar = { disetujui: 'Berkas yudisium Anda lengkap dan sudah disahkan admin prodi',
              dikembalikan: 'Berkas yudisium Anda dikembalikan untuk diperbaiki', ditolak: 'Berkas yudisium Anda ditolak' }[p.status] || kabar;
  }
  // Seminar/sidang TA (94): jadwal dibaca dengan token login admin; mahasiswa lalu menginput ke SIUP.
  var jadwalTeks = '';
  var penetapanTA = p.jenis === 'ta' && p.data && p.data.tahap_ta === 'penetapan_pembimbing';   // 110: pengajuan pembimbing TA
  if (penetapanTA && p.status === 'disetujui') {
    var ids = [p.pembimbing_id, p.data.pembimbing_2].filter(function (x) { return x; });
    var rd = UrlFetchApp.fetch(cfg.url + '/rest/v1/dosen?select=id,nama&id=in.(' + ids.map(encodeURIComponent).join(',') + ')',
      { headers: { apikey: cfg.key, Authorization: 'Bearer ' + req.token }, muteHttpExceptions: true });
    var nm = {};
    if (rd.getResponseCode() === 200) JSON.parse(rd.getContentText()).forEach(function (d) { nm[d.id] = d.nama; });
    kabar = 'Pembimbing TA Anda sudah ditetapkan';
    jadwalTeks = '\n\nPembimbing 1: ' + (nm[p.pembimbing_id] || '-')
      + (p.data.pembimbing_2 ? '\nPembimbing 2: ' + (nm[p.data.pembimbing_2] || '-') : '')
      + '\n\nLangkah berikutnya: saat siap seminar proposal, buat pengajuan TA tahap Seminar proposal; pembimbing mengikuti penetapan ini.';
  }
  else if (p.jenis === 'ta' && p.status === 'disetujui') {
    var rj = UrlFetchApp.fetch(cfg.url + '/rest/v1/jadwal_ta?select=tanggal,jam,ruang,tautan_daring&pengajuan_id=eq.' + Number(p.id),
      { headers: { apikey: cfg.key, Authorization: 'Bearer ' + req.token }, muteHttpExceptions: true });
    var j = rj.getResponseCode() === 200 ? (JSON.parse(rj.getContentText())[0] || null) : null;
    kabar = 'Seminar/sidang TA Anda sudah dijadwalkan';
    if (j) jadwalTeks = '\n\nJadwal: ' + j.tanggal + (j.jam ? ', ' + j.jam : '') + (j.ruang ? ', ' + j.ruang : '')
      + (j.tautan_daring ? '\nTautan daring: ' + j.tautan_daring : '')
      + '\n\nLangkah berikutnya: input jadwal ini ke SIUP sesuai ketentuan universitas.';
  }
  if (p.tahap === 'selesai') {
    kabar = { dikembalikan: 'Laporan selesai KP Anda dikembalikan untuk diperbaiki', ditolak: 'Laporan selesai KP Anda ditolak',
              disetujui: 'Laporan selesai KP Anda diterima; KP Anda dinyatakan selesai',
              admin: 'Laporan selesai KP Anda disetujui dosen pembimbing dan sedang diperiksa admin' }[p.status] || kabar;
  }
  if (MailApp.getRemainingDailyQuota() < 1) {
    throw new Error('Kuota email prodi hari ini habis; mahasiswa tetap melihat status di tautannya.');
  }
  var t = rpc_(cfg, 'mhs_tautan_id', { p_kunci: m.kunci, p_id: p.id });
  var catatan = String(req.catatan || '').trim();
  MailApp.sendEmail({ to: mhsTujuan_(cfg, m, p.nim, p.email).to, name: 'Program Studi', replyTo: lecturer.email, subject: kabar.slice(0, 200),
    body: 'Halo ' + p.nama + ',\n\n' + kabar + '.' + jadwalTeks
      + (catatan ? '\n\nCatatan dari ' + lecturer.nama + ':\n' + catatan.slice(0, 2000) : '')
      + '\n\nLihat rincian dan prosesnya di tautan pribadi Anda (tautan sebelumnya tidak berlaku lagi):\n'
      + mhsTautanTeks_(m, t) + '\n\nJangan teruskan tautan ini ke orang lain.' });
  return { ok: true, terkirim: true };
}
