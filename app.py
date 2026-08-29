import os
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# File Database Fisik Permanen
db_path = os.path.join('/tmp', 'tpa_permanen.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------------------------------------
# MODEL DATABASE
# --------------------------------------------------
class Santri(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    umur = db.Column(db.Integer, nullable=False)
    jenis_ngaji = db.Column(db.String(20), nullable=False)
    capaian = db.Column(db.String(100), nullable=False)
    halaman = db.Column(db.String(50), nullable=False)
    absensi = db.relationship('Absensi', backref='santri', lazy=True, cascade="all, delete-orphan")
    pembayaran = db.relationship('Pembayaran', backref='santri', lazy=True, cascade="all, delete-orphan")

class Absensi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    santri_id = db.Column(db.Integer, db.ForeignKey('santri.id'), nullable=False)
    tanggal = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)

class Pembayaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    santri_id = db.Column(db.Integer, db.ForeignKey('santri.id'), nullable=False)
    tahun = db.Column(db.Integer, nullable=False)
    bulan = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False) # 'Lunas Pengajar', 'Lunas Pengurus', 'Belum'

class MateriPelajaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.String(20), nullable=False, unique=True)
    hari = db.Column(db.String(20), nullable=False)
    pelajaran = db.Column(db.String(100), nullable=False)
    materi = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# HELPER TANGGAL & SPP MULAI JULI
HARI_LIST = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']
BULAN_LIST = ['Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
NOMINAL_SPP = 50000

def get_minggu_sekarang():
    try:
        tz = pytz.timezone('Asia/Jakarta')
        now = datetime.now(tz)
    except:
        now = datetime.now()
    
    start_of_week = now - timedelta(days=now.weekday())
    dates_of_week = {}
    for idx, hari in enumerate(HARI_LIST):
        dt = start_of_week + timedelta(days=idx)
        dates_of_week[hari] = dt.strftime('%Y-%m-%d')
        
    return dates_of_week, now.strftime('%Y-%m-%d'), now.year

# --------------------------------------------------
# PORTAL WALI SANTRI -> `/`
# --------------------------------------------------
@app.route('/')
def portal_orangtua():
    dates_week, today_db, current_year = get_minggu_sekarang()
    search_q = request.args.get('q', '').strip()
    
    if search_q:
        santri_list = Santri.query.filter(Santri.nama.ilike(f'%{search_q}%')).all()
    else:
        santri_list = Santri.query.all()

    all_dates = list(dates_week.values())
    absensi_records = Absensi.query.filter(Absensi.tanggal.in_(all_dates)).all()
    absen_map = {(a.santri_id, a.tanggal): a.status for a in absensi_records}

    bayar_records = Pembayaran.query.filter_by(tahun=current_year).all()
    bayar_map = {(b.santri_id, b.bulan): b.status for b in bayar_records}

    materi_today = MateriPelajaran.query.filter_by(tanggal=today_db).first()
    materi_minggu_ini = MateriPelajaran.query.filter(MateriPelajaran.tanggal.in_(all_dates)).all()

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Portal Wali Santri - TPA Baiturrahman</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    </head>
    <body class="bg-light">
        <div class="container py-3" style="max-width: 600px;">
            
            <div class="bg-success text-white p-4 rounded-3 shadow-sm mb-3 text-center">
                <h3 class="fw-bold m-0">🕌 Selamat Datang</h3>
                <h5 class="fw-normal mb-1">di TPA Baiturrahman</h5>
                <small class="opacity-75">Pantau Perkembangan Mengaji & Kehadiran Putra-Putri Anda</small>
            </div>

            <!-- Search Bar -->
            <form action="/" method="GET" class="mb-3">
                <div class="input-group shadow-sm">
                    <input type="text" name="q" value="{{ search_q }}" class="form-control" placeholder="Cari nama santri...">
                    <button class="btn btn-success" type="submit"><i class="bi bi-search"></i> Cari</button>
                    {% if search_q %}
                        <a href="/" class="btn btn-outline-secondary"><i class="bi bi-x-lg"></i></a>
                    {% endif %}
                </div>
            </form>

            <!-- Pelajaran Hari Ini -->
            <div class="card border-0 shadow-sm p-3 mb-3 bg-white rounded-3">
                <small class="text-uppercase fw-bold text-success"><i class="bi bi-book"></i> Pelajaran Hari Ini ({{ today_db }})</small>
                {% if materi_today %}
                    <h5 class="fw-bold text-dark mb-1 mt-1">{{ materi_today.pelajaran }}</h5>
                    <p class="text-muted m-0 small">{{ materi_today.materi }}</p>
                {% else %}
                    <p class="text-muted m-0 small mt-1">Belum ada materi harian yang diinput Ustadz/Ustadzah.</p>
                {% endif %}
            </div>

            <!-- Rekapan Mingguan -->
            <div class="card border-0 bg-success bg-opacity-10 border-success shadow-sm p-3 mb-3 rounded-3">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-journal-check text-success fs-3 me-2"></i>
                    <div>
                        <h6 class="fw-bold text-success m-0">📋 Rekapan Pembelajaran Pekan Ini</h6>
                        <small class="text-muted">Rangkuman materi yang dipelajari selama 1 minggu</small>
                    </div>
                </div>
                <hr class="my-2">
                {% if materi_minggu_ini %}
                    <ul class="list-group list-group-flush bg-transparent small">
                        {% for m in materi_minggu_ini %}
                        <li class="list-group-item bg-transparent px-0 py-1">
                            <strong class="text-dark">{{ m.hari }} ({{ m.pelajaran }}):</strong> 
                            <span class="text-muted">{{ m.materi }}</span>
                        </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <small class="text-muted">Belum ada rekapan materi untuk pekan ini.</small>
                {% endif %}
            </div>

            <!-- Daftar Santri -->
            {% for s in santri_list %}
            <div class="card border-0 shadow-sm p-3 mb-3 bg-white rounded-3">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h5 class="fw-bold text-success m-0">{{ s.nama }}</h5>
                        <small class="text-muted">Umur: {{ s.umur }} Tahun</small>
                    </div>
                    <span class="badge bg-success px-3 py-2 fs-6">{{ s.jenis_ngaji }}</span>
                </div>
                
                <div class="bg-light p-3 rounded mb-3 border">
                    <small class="text-muted d-block fw-bold mb-1">Capaian Mengaji Terakhir:</small>
                    {% if s.jenis_ngaji == 'Iqro' %}
                        <span class="fw-bold text-dark fs-5">Iqro {{ s.capaian }}</span> 
                        <span class="text-muted fs-6">— Halaman {{ s.halaman }}</span>
                    {% else %}
                        <span class="fw-bold text-dark fs-5">{{ s.capaian }}</span> 
                        <span class="text-muted fs-6">— Ayat / Hal {{ s.halaman }}</span>
                    {% endif %}
                    
                    <div class="mt-2 pt-2 border-top text-success small fw-bold">
                        <i class="bi bi-star-fill text-warning me-1"></i>
                        Alhamdulillah, pencapaian Ananda pekan ini sudah mencapai {{ 'Iqro ' + s.capaian + ' Halaman ' + s.halaman if s.jenis_ngaji == 'Iqro' else s.capaian + ' Ayat/Hal ' + s.halaman }}.
                    </div>
                </div>

                <h6 class="fw-bold small text-muted mb-2"><i class="bi bi-calendar-week"></i> Kehadiran Minggu Ini:</h6>
                <div class="d-flex justify-content-between text-center border rounded p-2 bg-white mb-3">
                    {% for h in ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'] %}
                    {% set tgl = dates_week[h] %}
                    {% set is_hadir = (absen_map.get((s.id, tgl)) == 'Hadir') %}
                    <div>
                        <small class="d-block text-muted" style="font-size: 11px;">{{ h[:3] }}</small>
                        {% if is_hadir %}
                            <i class="bi bi-check-circle-fill text-success fs-5"></i>
                        {% else %}
                            <i class="bi bi-dash-circle text-secondary fs-5"></i>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>

                <!-- Status SPP Bulanan Mulai Juli -->
                <h6 class="fw-bold small text-muted mb-2"><i class="bi bi-cash-coin"></i> Status SPP Bulanan (Mulai Juli {{ current_year }}):</h6>
                <div class="row g-1 text-center">
                    {% for b in bulan_list %}
                    {% set st_bayar = bayar_map.get((s.id, b), 'Belum') %}
                    <div class="col-4 mb-1">
                        <div class="border rounded p-1 {{ 'bg-success text-white' if st_bayar=='Lunas Pengajar' else ('bg-info text-dark fw-bold' if st_bayar=='Lunas Pengurus' else 'bg-light text-muted') }}">
                            <small class="d-block fw-bold" style="font-size: 10px;">{{ b }}</small>
                            <span style="font-size: 10px;">
                                {% if st_bayar == 'Lunas Pengajar' %}
                                    <i class="bi bi-check-circle-fill"></i> Lunas (Ust)
                                {% elif st_bayar == 'Lunas Pengurus' %}
                                    <i class="bi bi-patch-check-fill text-primary"></i> Lunas (Pengurus)
                                {% else %}
                                    Belum
                                {% endif %}
                            </span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% else %}
            <div class="card border-0 p-4 text-center text-muted rounded-3">Santri tidak ditemukan.</div>
            {% endfor %}

            <!-- Kedai Banner -->
            <div class="card border-0 bg-warning bg-opacity-10 border-warning shadow-sm p-3 mb-4 rounded-3 text-center">
                <i class="bi bi-shop-window text-warning-emphasis fs-1 mb-2"></i>
                <h5 class="fw-bold text-dark mb-1">Kedai Pedas & Manis</h5>
                <p class="small text-muted mb-3">
                    Belanja makanan & minuman di kedai kami sama dengan <strong>beramal di Yayasan Amal Anak Nagari</strong>.
                </p>
                <a href="https://kedai-pedas-manis.vercel.app" target="_blank" class="btn btn-warning fw-bold text-dark w-100 shadow-sm">
                    <i class="bi bi-cart-fill me-1"></i> Buka Menu & Pesan Sekarang
                </a>
            </div>

            <div class="text-center mt-3 mb-4">
                <a href="/admin" class="btn btn-outline-secondary btn-sm rounded-pill"><i class="bi bi-shield-lock"></i> Masuk Mode Admin</a>
            </div>
        </div>
    </body>
    </html>
    ''', santri_list=santri_list, dates_week=dates_week, absen_map=absen_map, bulan_list=BULAN_LIST, bayar_map=bayar_map, current_year=current_year, today_db=today_db, materi_today=materi_today, materi_minggu_ini=materi_minggu_ini, search_q=search_q)

# --------------------------------------------------
# MODE ADMIN -> `/admin`
# --------------------------------------------------
@app.route('/admin')
def admin_dashboard():
    dates_week, today_db, current_year = get_minggu_sekarang()
    search_q = request.args.get('q', '').strip()

    if search_q:
        santri_list = Santri.query.filter(Santri.nama.ilike(f'%{search_q}%')).all()
    else:
        santri_list = Santri.query.all()

    all_dates = list(dates_week.values())
    absensi_records = Absensi.query.filter(Absensi.tanggal.in_(all_dates)).all()
    absen_map = {(a.santri_id, a.tanggal): a.status for a in absensi_records}

    bayar_records = Pembayaran.query.filter_by(tahun=current_year).all()
    bayar_map = {(b.santri_id, b.bulan): b.status for b in bayar_records}

    materi_today = MateriPelajaran.query.filter_by(tanggal=today_db).first()

    # Total Uang SPP yang Diterima Pengajar Langsung
    lunas_pengajar_count = db.session.query(db.func.count(Pembayaran.id)).filter(Pembayaran.tahun==current_year, Pembayaran.status=='Lunas Pengajar').scalar() or 0
    total_uang_spp = lunas_pengajar_count * NOMINAL_SPP

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panel Admin - TPA Baiturrahman</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-success shadow-sm">
            <div class="container">
                <a class="navbar-brand fw-bold" href="/admin">🕌 Mode Admin - TPA Baiturrahman</a>
                <a href="/" class="btn btn-light btn-sm fw-bold text-success"><i class="bi bi-eye"></i> Tampilan Orang Tua</a>
            </div>
        </nav>

        <div class="container my-4">
            <div class="row g-3 mb-4">
                <div class="col-md-6">
                    <div class="card border-0 bg-success text-white shadow-sm p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <small class="text-uppercase fw-bold">SPP Diterima Langsung {{ current_year }}</small>
                                <h2 class="fw-bold m-0">Rp {{ "{:,.0f}".format(total_uang_spp).replace(',', '.') }}</h2>
                                <small>{{ lunas_pengajar_count }} Bulan Terbayar ke Pengajar</small>
                            </div>
                            <i class="bi bi-wallet2 fs-1"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card border-0 bg-white shadow-sm p-3">
                        <form action="/admin" method="GET">
                            <label class="form-label small fw-bold text-success">Cari Santri di Admin</label>
                            <div class="input-group">
                                <input type="text" name="q" value="{{ search_q }}" class="form-control" placeholder="Ketik nama santri...">
                                <button class="btn btn-success" type="submit"><i class="bi bi-search"></i> Cari</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Form Input Pelajaran -->
            <div class="card border-0 shadow-sm p-3 mb-4 bg-white">
                <h5 class="fw-bold text-success mb-2"><i class="bi bi-journal-bookmark-fill"></i> Kelola Pelajaran & Materi Hari Ini</h5>
                <form action="/api/simpan-materi" method="POST" class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label small fw-bold">Tanggal</label>
                        <input type="date" name="tanggal" value="{{ today_db }}" class="form-control form-control-sm" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small fw-bold">Nama Pelajaran</label>
                        <input type="text" name="pelajaran" value="{{ materi_today.pelajaran if materi_today else '' }}" placeholder="Contoh: Fiqih" class="form-control form-control-sm" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Materi Ringkas</label>
                        <input type="text" name="materi" value="{{ materi_today.materi if materi_today else '' }}" placeholder="Contoh: Tata Cara Wudhu" class="form-control form-control-sm" required>
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <button type="submit" class="btn btn-success btn-sm w-100 fw-bold">Simpan Materi</button>
                    </div>
                </form>
            </div>

            <div class="row g-4">
                <div class="col-lg-4">
                    <div class="card border-0 shadow-sm p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-person-plus-fill"></i> Tambah / Edit Santri</h5>
                        <form action="/api/tambah-santri" method="POST">
                            <div class="mb-2">
                                <label class="form-label small fw-bold">Nama Santri</label>
                                <input type="text" name="nama" class="form-control form-control-sm" placeholder="Nama lengkap" required>
                            </div>
                            <div class="mb-2">
                                <label class="form-label small fw-bold">Umur (Tahun)</label>
                                <input type="number" name="umur" class="form-control form-control-sm" placeholder="Contoh: 7" required>
                            </div>
                            <div class="mb-2">
                                <label class="form-label small fw-bold">Tingkat Mengaji</label>
                                <select name="jenis_ngaji" id="jenis_ngaji" class="form-select form-select-sm" onchange="updateFormTingkat()" required>
                                    <option value="Iqro">Iqro</option>
                                    <option value="Al-Qur'an">Al-Qur'an</option>
                                </select>
                            </div>
                            <div class="mb-2">
                                <label class="form-label small fw-bold" id="lbl-capaian">Angka Jilid (Misal: 3)</label>
                                <input type="text" name="capaian" id="capaian" class="form-control form-control-sm" placeholder="3" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold" id="lbl-halaman">Angka Halaman (Misal: 9)</label>
                                <input type="text" name="halaman" id="halaman" class="form-control form-control-sm" placeholder="9" required>
                            </div>
                            <button type="submit" class="btn btn-success w-100 fw-bold btn-sm">Simpan Santri</button>
                        </form>
                    </div>
                </div>

                <div class="col-lg-8">
                    <!-- Presensi Mingguan -->
                    <div class="card border-0 shadow-sm p-3 mb-4">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-calendar-check"></i> Presensi Mingguan (Senin - Sabtu)</h5>
                        <div class="table-responsive">
                            <table class="table table-bordered align-middle text-center small">
                                <thead class="table-success">
                                    <tr>
                                        <th class="text-start" style="min-width: 150px;">Nama Santri</th>
                                        <th>Capaian</th>
                                        {% for h in ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'] %}
                                        <th>{{ h }}</th>
                                        {% endfor %}
                                        <th>Aksi</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for s in santri_list %}
                                    <tr id="row-santri-{{ s.id }}">
                                        <td class="text-start">
                                            <div class="fw-bold text-dark">{{ s.nama }}</div>
                                            <small class="text-muted">{{ s.umur }} Tahun</small>
                                        </td>
                                        <td>
                                            <span class="badge bg-info text-dark">{{ s.jenis_ngaji }}</span>
                                            <div>
                                                {% if s.jenis_ngaji == 'Iqro' %}
                                                    <small class="fw-bold">Iqro {{ s.capaian }}</small>
                                                    <div class="text-muted">Hal {{ s.halaman }}</div>
                                                {% else %}
                                                    <small class="fw-bold">{{ s.capaian }}</small>
                                                    <div class="text-muted">Ayat/Hal {{ s.halaman }}</div>
                                                {% endif %}
                                            </div>
                                        </td>

                                        {% for h in ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'] %}
                                        {% set tgl = dates_week[h] %}
                                        {% set is_checked = (absen_map.get((s.id, tgl)) == 'Hadir') %}
                                        <td>
                                            <input type="checkbox" class="form-check-input p-2" 
                                                   onchange="toggleAbsen({{ s.id }}, '{{ tgl }}', this.checked)"
                                                   {{ 'checked' if is_checked else '' }}>
                                        </td>
                                        {% endfor %}

                                        <td>
                                            <button onclick="hapusSantri({{ s.id }})" class="btn btn-sm btn-light text-danger"><i class="bi bi-trash"></i></button>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="9" class="text-center text-muted py-3">Belum ada data santri.</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- SPP Bulanan Mulai Juli -->
                    <div class="card border-0 shadow-sm p-3">
                        <h5 class="fw-bold text-success mb-2"><i class="bi bi-cash-coin"></i> Kelola SPP Bulanan (Mulai Juli {{ current_year }})</h5>
                        <small class="text-muted mb-3 d-block">Pilih status pembayaran: Belum / Ke Ustadz / Ke Pengurus</small>
                        
                        <div class="table-responsive">
                            <table class="table table-bordered align-middle text-center small">
                                <thead class="table-warning">
                                    <tr>
                                        <th class="text-start" style="min-width: 140px;">Nama Santri</th>
                                        {% for b in bulan_list %}
                                        <th>{{ b }}</th>
                                        {% endfor %}
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for s in santri_list %}
                                    <tr>
                                        <td class="text-start fw-bold">{{ s.nama }}</td>
                                        {% for b in bulan_list %}
                                        {% set st_bayar = bayar_map.get((s.id, b), 'Belum') %}
                                        <td>
                                            <select class="form-select form-select-sm p-1" style="font-size: 11px;" 
                                                    onchange="updatePembayaran({{ s.id }}, {{ current_year }}, '{{ b }}', this.value)">
                                                <option value="Belum" {{ 'selected' if st_bayar=='Belum' else '' }}>Belum</option>
                                                <option value="Lunas Pengajar" {{ 'selected' if st_bayar=='Lunas Pengajar' else '' }}>Ke Ustadz</option>
                                                <option value="Lunas Pengurus" {{ 'selected' if st_bayar=='Lunas Pengurus' else '' }}>Ke Pengurus</option>
                                            </select>
                                        </td>
                                        {% endfor %}
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="7" class="text-center text-muted py-3">Belum ada data santri.</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function updateFormTingkat() {
                const jenis = document.getElementById('jenis_ngaji').value;
                if(jenis === 'Iqro') {
                    document.getElementById('lbl-capaian').innerText = 'Angka Jilid (Misal: 3)';
                    document.getElementById('capaian').placeholder = '3';
                    document.getElementById('lbl-halaman').innerText = 'Angka Halaman (Misal: 9)';
                    document.getElementById('halaman').placeholder = '9';
                } else {
                    document.getElementById('lbl-capaian').innerText = 'Nama Surah (Misal: Surah Al-Baqarah)';
                    document.getElementById('capaian').placeholder = 'Surah Al-Baqarah';
                    document.getElementById('lbl-halaman').innerText = 'Ayat / Halaman';
                    document.getElementById('halaman').placeholder = 'Ayat 255 / Hal 10';
                }
            }

            async function toggleAbsen(santriId, tanggal, isChecked) {
                const status = isChecked ? 'Hadir' : 'Alfa';
                await fetch('/api/absen', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({santri_id: santriId, tanggal: tanggal, status: status})
                });
            }

            async function updatePembayaran(santriId, tahun, bulan, status) {
                await fetch('/api/pembayaran', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({santri_id: santriId, tahun: tahun, bulan: bulan, status: status})
                });
                location.reload();
            }

            async function hapusSantri(id) {
                if(confirm("Hapus data santri ini?")) {
                    const res = await fetch(`/api/hapus-santri/${id}`, {method: 'DELETE'});
                    const data = await res.json();
                    if(data.success) {
                        location.reload();
                    }
                }
            }
        </script>
    </body>
    </html>
    ''', santri_list=santri_list, dates_week=dates_week, absen_map=absen_map, bulan_list=BULAN_LIST, bayar_map=bayar_map, current_year=current_year, today_db=today_db, materi_today=materi_today, total_uang_spp=total_uang_spp, lunas_pengajar_count=lunas_pengajar_count, search_q=search_q)

# --------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------
@app.route('/api/simpan-materi', methods=['POST'])
def api_simpan_materi():
    tanggal = request.form.get('tanggal')
    pelajaran = request.form.get('pelajaran')
    materi = request.form.get('materi')
    
    if tanggal and pelajaran and materi:
        dt = datetime.strptime(tanggal, '%Y-%m-%d')
        hari_map = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
        hari = hari_map.get(dt.strftime('%A'), 'Senin')

        existing = MateriPelajaran.query.filter_by(tanggal=tanggal).first()
        if existing:
            existing.pelajaran = pelajaran
            existing.materi = materi
        else:
            db.session.add(MateriPelajaran(tanggal=tanggal, hari=hari, pelajaran=pelajaran, materi=materi))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/tambah-santri', methods=['POST'])
def api_tambah_santri():
    nama = request.form.get('nama')
    umur = request.form.get('umur')
    jenis_ngaji = request.form.get('jenis_ngaji')
    capaian = request.form.get('capaian')
    halaman = request.form.get('halaman')
    
    if nama and umur:
        s = Santri(nama=nama, umur=int(umur), jenis_ngaji=jenis_ngaji, capaian=capaian, halaman=halaman)
        db.session.add(s)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/absen', methods=['POST'])
def api_absen():
    data = request.json
    santri_id = data.get('santri_id')
    tanggal = data.get('tanggal')
    status = data.get('status')
    
    existing = Absensi.query.filter_by(santri_id=santri_id, tanggal=tanggal).first()
    if existing:
        existing.status = status
    else:
        db.session.add(Absensi(santri_id=santri_id, tanggal=tanggal, status=status))
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/pembayaran', methods=['POST'])
def api_pembayaran():
    data = request.json
    santri_id = data.get('santri_id')
    tahun = data.get('tahun')
    bulan = data.get('bulan')
    status = data.get('status')
    
    existing = Pembayaran.query.filter_by(santri_id=santri_id, tahun=tahun, bulan=bulan).first()
    if existing:
        existing.status = status
    else:
        db.session.add(Pembayaran(santri_id=santri_id, tahun=tahun, bulan=bulan, status=status))
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/hapus-santri/<int:santri_id>', methods=['DELETE'])
def api_hapus_santri(santri_id):
    santri = Santri.query.get(santri_id)
    if santri:
        db.session.delete(santri)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

app = app
