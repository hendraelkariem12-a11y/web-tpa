import os
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Konfigurasi Database In-Memory untuk Serverless Vercel
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------------------------------------
# MODEL DATABASE
# --------------------------------------------------
class Santri(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    umur = db.Column(db.Integer, nullable=False)
    jenis_ngaji = db.Column(db.String(20), nullable=False) # 'Iqro' atau 'Al-Qur\'an'
    capaian = db.Column(db.String(100), nullable=False) # 'Jilid 3' atau 'Surah Al-Baqarah'
    halaman = db.Column(db.String(50), nullable=False)  # 'Halaman 15' atau 'Ayat 25'
    absensi = db.relationship('Absensi', backref='santri', lazy=True, cascade="all, delete-orphan")

class Absensi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    santri_id = db.Column(db.Integer, db.ForeignKey('santri.id'), nullable=False)
    tanggal = db.Column(db.String(20), nullable=False) # YYYY-MM-DD
    status = db.Column(db.String(20), nullable=False) # 'Hadir' / 'Alfa'

with app.app_context():
    db.create_all()

# --------------------------------------------------
# HELPER TANGGAL MINGGUAN (SENIN - SABTU)
# --------------------------------------------------
HARI_LIST = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']

def get_minggu_sekarang():
    try:
        tz = pytz.timezone('Asia/Jakarta')
        now = datetime.now(tz)
    except:
        now = datetime.now()
    
    # Cari hari Senin dari minggu berjalan
    start_of_week = now - timedelta(days=now.weekday())
    
    dates_of_week = {}
    for idx, hari in enumerate(HARI_LIST):
        dt = start_of_week + timedelta(days=idx)
        dates_of_week[hari] = dt.strftime('%Y-%m-%d')
        
    return dates_of_week, now.strftime('%Y-%m-%d')

# --------------------------------------------------
# ROUTE ADMIN / DASHBOARD
# --------------------------------------------------
@app.route('/')
def admin_dashboard():
    dates_week, today_db = get_minggu_sekarang()
    santri_list = Santri.query.all()
    
    # Ambil seluruh data absensi minggu ini
    all_dates = list(dates_week.values())
    absensi_records = Absensi.query.filter(Absensi.tanggal.in_(all_dates)).all()
    
    # Mapping absensi: (santri_id, tgl) -> status
    absen_map = {(a.santri_id, a.tanggal): a.status for a in absensi_records}

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panel Pengajar - TPA Baiturrahman</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-dark bg-success shadow-sm">
            <div class="container">
                <a class="navbar-brand fw-bold" href="/">🕌 Admin TPA Baiturrahman</a>
                <a href="/orangtua" class="btn btn-light btn-sm fw-bold text-success"><i class="bi bi-person-heart"></i> Portal Wali Santri</a>
            </div>
        </nav>

        <div class="container my-4">
            <div class="row g-4">
                <!-- Form Tambah Data Santri -->
                <div class="col-lg-4">
                    <div class="card border-0 shadow-sm p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-person-plus-fill"></i> Tambah Data Santri</h5>
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
                            <div class="mb-2" id="box-capaian">
                                <label class="form-label small fw-bold" id="lbl-capaian">Jilid Iqro</label>
                                <input type="text" name="capaian" id="capaian" class="form-control form-control-sm" placeholder="Contoh: Jilid 3" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold" id="lbl-halaman">Halaman</label>
                                <input type="text" name="halaman" class="form-control form-control-sm" placeholder="Contoh: Halaman 12" required>
                            </div>
                            <button type="submit" class="btn btn-success w-100 fw-bold btn-sm">Simpan Data Santri</button>
                        </form>
                    </div>
                </div>

                <!-- Tabel Data Santri & Centang Absensi Mingguan -->
                <div class="col-lg-8">
                    <div class="card border-0 shadow-sm p-3">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="fw-bold text-success m-0"><i class="bi bi-calendar-check"></i> Presensi Mingguan (Senin - Sabtu)</h5>
                        </div>
                        
                        <div class="table-responsive">
                            <table class="table table-bordered align-middle text-center small">
                                <thead class="table-success">
                                    <tr>
                                        <th class="text-start" style="min-width: 160px;">Nama Santri</th>
                                        <th>Capaian Mengaji</th>
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
                                        <td class="align-middle">
                                            <input type="checkbox" class="form-check-input p-2" 
                                                   onchange="toggleAbsen({{ s.id }}, '{{ tgl }}', this.checked)"
                                                   {{ 'checked' if is_checked else '' }}>
                                        </td>
                                        {% endfor %}

                                        <td>
                                            <button onclick="hapusSantri({{ s.id }})" class="btn btn-sm btn-light text-danger" title="Hapus"><i class="bi bi-trash"></i></button>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="9" class="text-center text-muted py-4">Belum ada data santri. Silakan isi form di sebelah kiri.</td>
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
                    document.getElementById('lbl-halaman').innerText = 'Halaman';
                } else {
                    document.getElementById('lbl-capaian').innerText = 'Nama Surah';
                    document.getElementById('capaian').placeholder = 'Contoh: Surah Al-Baqarah';
                    document.getElementById('lbl-halaman').innerText = 'Ayat / Halaman';
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

            async function hapusSantri(id) {
                if(confirm("Hapus data santri ini?")) {
                    const res = await fetch(`/api/hapus-santri/${id}`, {method: 'DELETE'});
                    const data = await res.json();
                    if(data.success) {
                        document.getElementById(`row-santri-${id}`).remove();
                    }
                }
            }
        </script>
    </body>
    </html>
    ''', santri_list=santri_list, dates_week=dates_week, absen_map=absen_map)

# --------------------------------------------------
# ROUTE PORTAL WALI SANTRI
# --------------------------------------------------
@app.route('/orangtua')
def portal_orangtua():
    dates_week, _ = get_minggu_sekarang()
    santri_list = Santri.query.all()
    
    all_dates = list(dates_week.values())
    absensi_records = Absensi.query.filter(Absensi.tanggal.in_(all_dates)).all()
    absen_map = {(a.santri_id, a.tanggal): a.status for a in absensi_records}

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
            <div class="text-center bg-success text-white p-3 rounded-3 shadow-sm mb-3">
                <h4 class="fw-bold m-0">🕌 TPA BAITURRAHMAN</h4>
                <small>Informasi Progres Mengaji & Kehadiran Santri</small>
            </div>

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
                    <small class="text-muted d-block">Capaian Terakhir:</small>
                    <span class="fw-bold text-dark">{{ s.capaian }}</span> — <small class="text-dark">{{ s.halaman }}</small>
                </div>

                <h6 class="fw-bold small text-muted mb-2"><i class="bi bi-calendar-week"></i> Kehadiran Minggu Ini:</h6>
                <div class="d-flex justify-content-between text-center border rounded p-2 bg-white">
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
            </div>
            {% else %}
            <div class="card border-0 p-4 text-center text-muted">Belum ada data santri terdaftar.</div>
            {% endfor %}

            <div class="text-center mt-3">
                <a href="/" class="text-muted small text-decoration-none">🔑 Masuk Panel Pengajar/Admin</a>
            </div>
        </div>
    </body>
    </html>
    ''', santri_list=santri_list, dates_week=dates_week, absen_map=absen_map)

# --------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------
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

@app.route('/api/hapus-santri/<int:santri_id>', methods=['DELETE'])
def api_hapus_santri(santri_id):
    santri = Santri.query.get(santri_id)
    if santri:
        db.session.delete(santri)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

app = app
