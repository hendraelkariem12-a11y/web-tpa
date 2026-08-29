import os
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# SQLAlchemy Database Configuration (In-Memory for Vercel Serverless)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------------------------------------
# MODEL DATABASE (SQLAlchemy)
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
    tanggal = db.Column(db.String(20), nullable=False) # YYYY-MM-DD
    status = db.Column(db.String(20), nullable=False) # 'Hadir' / 'Alfa'

class Pembayaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    santri_id = db.Column(db.Integer, db.ForeignKey('santri.id'), nullable=False)
    tahun = db.Column(db.Integer, nullable=False)
    bulan = db.Column(db.String(20), nullable=False) # 'Januari', 'Februari', dst
    status = db.Column(db.String(20), nullable=False) # 'Lunas' / 'Belum'

class MateriPelajaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.String(20), nullable=False, unique=True)
    hari = db.Column(db.String(20), nullable=False)
    pelajaran = db.Column(db.String(100), nullable=False)
    materi = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# --------------------------------------------------
# HELPER TANGGAL & BULAN
# --------------------------------------------------
HARI_LIST = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']
BULAN_LIST = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

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
# 1. HALAMAN UTAMA (PORTAL WALI SANTRI) -> `/`
# --------------------------------------------------
@app.route('/')
def portal_orangtua():
    dates_week, today_db, current_year = get_minggu_sekarang()
    
    # SQLAlchemy Queries
    santri_list = Santri.query.all()
    all_dates = list(dates_week.values())
    absensi_records = Absensi.query.filter(Absensi.tanggal.in_(all_dates)).all()
    absen_map = {(a.santri_id, a.tanggal): a.status for a in absensi_records}

    bayar_records = Pembayaran.query.filter_by(tahun=current_year).all()
    bayar_map = {(b.santri_id, b.bulan): b.status for b in bayar_records}

    materi_today = MateriPelajaran.query.filter_by(tanggal=today_db).first()

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
            <!-- Header TPA -->
            <div class="text-center bg-success text-white p-3 rounded-3 shadow-sm mb-3">
                <h4 class="fw-bold m-0">🕌 TPA BAITURRAHMAN</h4>
                <small>Informasi Pembelajaran & Presensi Santri</small>
            </div>

            <!-- Pelajaran Hari Ini -->
            <div class="card border-0 shadow-sm p-3 mb-3 bg-white">
                <small class="text-uppercase fw-bold text-success"><i class="bi bi-book"></i> Pelajaran Hari Ini ({{ today_db }})</small>
                {% if materi_today %}
                    <h5 class="fw-bold text-dark mb-1">{{ materi_today.pelajaran }}</h5>
                    <p class="text-muted m-0 small">{{ materi_today.materi }}</p>
                {% else %}
                    <p class="text-muted m-0 small">Belum ada materi harian yang diinput Ustadz/Ustadzah.</p>
                {% endif %}
            </div>

            <!-- Daftar Santri & Rekap -->
            {% for s in santri_list %}
            <div class="card border-0 shadow-sm p-3 mb-3 bg-white">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h5 class="fw-bold text-success m-0">{{ s.nama }}</h5>
                        <small class="text-muted">Umur: {{ s.umur }} Tahun</small>
                    </div>
                    <span class="badge bg-success px-3 py-2">{{ s.jenis_ngaji }}</span>
                </div>
                
                <div class="bg-light p-2 rounded mb-3">
                    <small class="text-muted d-block">Capaian Mengaji:</small>
                    <span class="fw-bold text-dark">{{ s.capaian }}</span> — <small class="text-dark">{{ s.halaman }}</small>
                </div>

                <!-- Kehadiran Mingguan -->
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

                <!-- SPP Bulanan -->
                <h6 class="fw-bold small text-muted mb-2"><i class="bi bi-cash-coin"></i> Status SPP Bulanan ({{ current_year }}):</h6>
                <div class="row g-1 text-center">
                    {% for b in bulan_list %}
                    {% set is_lunas = (bayar_map.get((s.id, b)) == 'Lunas') %}
                    <div class="col-3">
                        <div class="border rounded p-1 {{ 'bg-success text-white' if is_lunas else 'bg-light text-muted' }}">
                            <small class="d-block" style="font-size: 10px;">{{ b }}</small>
                            <span class="fw-bold" style="font-size: 11px;">{{ 'Lunas' if is_lunas else 'Belum' }}</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% else %}
            <div class="card border-0 p-4 text-center text-muted">Belum ada data santri. Silakan minta Ustadz/Ustadzah untuk menambahkan.</div>
            {% endfor %}

            <div class="text-center mt-3">
                <a href="/admin" class="btn btn-outline-success btn-sm rounded-pill fw-bold"><i class="bi bi-shield-lock"></i> Masuk Mode Admin / Pengajar</a>
            </div>
        </div>
    </body>
    </html>
    ''', santri_list=santri_list, dates_week=dates_week, absen_map=absen_map, bulan_list=BULAN_LIST, bayar_map=bayar_map, current_year=current_year, today_db=today_db, materi_today=materi_today)

# --------------------------------------------------
# 2. HALAMAN PANEL ADMIN -> `/admin`
# --------------------------------------------------
@app.route('/admin')
def admin_dashboard():
    dates_week, today_db, current_year = get_minggu_sekarang()
    
    # SQLAlchemy Queries
    santri_list = Santri.query.all()
    all_dates = list(dates_week.values())
    absensi_records = Absensi.query.filter(Absensi.tanggal.in_(all_dates)).all()
    absen_map = {(a.santri_id, a.tanggal): a.status for a in absensi_records}

    bayar_records = Pembayaran.query.filter_by(tahun=current_year).all()
    bayar_map = {(b.santri_id, b.bulan): b.status for b in bayar_records}

    materi_today = MateriPelajaran.query.filter_by(tanggal=today_db).first()

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
                <a href="/" class="btn btn-light btn-sm fw-bold text-success"><i class="bi bi-eye"></i> Lihat Tampilan Orang Tua</a>
            </div>
        </nav>

        <div class="container my-4">
            <!-- Form Input Pelajaran & Materi Hari Ini -->
            <div class="card border-0 shadow-sm p-3 mb-4 bg-white">
                <h5 class="fw-bold text-success mb-2"><i class="bi bi-journal-bookmark-fill"></i> Kelola Pelajaran & Materi Hari Ini</h5>
                <form action="/api/simpan-materi" method="POST" class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label small fw-bold">Tanggal</label>
                        <input type="date" name="tanggal" value="{{ today_db }}" class="form-control form-control-sm" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small fw-bold">Nama Pelajaran</label>
                        <input type="text" name="pelajaran" value="{{ materi_today.pelajaran if materi_today else '' }}" placeholder="Contoh: Fiqih / Tajwid" class="form-control form-control-sm" required>
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
                <!-- Form Tambah Santri -->
                <div class="col-lg-4">
                    <div class="card border-0 shadow-sm p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-person-plus-fill"></i> Tambah Santri Baru</h5>
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
                                <label class="form-label small fw-bold" id="lbl-capaian">Jilid Iqro</label>
                                <input type="text" name="capaian" id="capaian" class="form-control form-control-sm" placeholder="Contoh: Jilid 3" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold" id="lbl-halaman">Halaman</label>
                                <input type="text" name="halaman" class="form-control form-control-sm" placeholder="Contoh: Halaman 12" required>
                            </div>
                            <button type="submit" class="btn btn-success w-100 fw-bold btn-sm">Simpan Santri</button>
                        </form>
                    </div>
                </div>

                <!-- Presensi & SPP Bulanan -->
                <div class="col-lg-8">
                    <!-- Tabel Presensi Mingguan -->
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
                                            <div><small class="fw-bold">{{ s.capaian }}</small></div>
                                            <small class="text-muted">{{ s.halaman }}</small>
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

                    <!-- Tabel Pembayaran SPP Bulanan -->
                    <div class="card border-0 shadow-sm p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-cash-coin"></i> Kelola SPP Bulanan ({{ current_year }})</h5>
                        <div class="table-responsive">
                            <table class="table table-bordered align-middle text-center small">
                                <thead class="table-warning">
                                    <tr>
                                        <th class="text-start" style="min-width: 150px;">Nama Santri</th>
                                        {% for b in bulan_list %}
                                        <th>{{ b[:3] }}</th>
                                        {% endfor %}
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for s in santri_list %}
                                    <tr>
                                        <td class="text-start fw-bold">{{ s.nama }}</td>
                                        {% for b in bulan_list %}
                                        {% set is_lunas = (bayar_map.get((s.id, b)) == 'Lunas') %}
                                        <td>
                                            <input type="checkbox" class="form-check-input p-2" 
                                                   onchange="togglePembayaran({{ s.id }}, {{ current_year }}, '{{ b }}', this.checked)"
                                                   {{ 'checked' if is_lunas else '' }}>
                                        </td>
                                        {% endfor %}
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="13" class="text-center text-muted py-3">Belum ada data santri.</td>
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
                    document.getElementById('lbl-capaian').innerText = 'Jilid Iqro';
                    document.getElementById('capaian').placeholder = 'Contoh: Jilid 3';
                } else {
                    document.getElementById('lbl-capaian').innerText = 'Nama Surah';
                    document.getElementById('capaian').placeholder = 'Contoh: Surah Al-Baqarah';
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

            async function togglePembayaran(santriId, tahun, bulan, isChecked) {
                const status = isChecked ? 'Lunas' : 'Belum';
                await fetch('/api/pembayaran', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({santri_id: santriId, tahun: tahun, bulan: bulan, status: status})
                });
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
    ''', santri_list=santri_list, dates_week=dates_week, absen_map=absen_map, bulan_list=BULAN_LIST, bayar_map=bayar_map, current_year=current_year, today_db=today_db, materi_today=materi_today)

# --------------------------------------------------
# 3. API ENDPOINTS (SQLAlchemy Execution)
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
