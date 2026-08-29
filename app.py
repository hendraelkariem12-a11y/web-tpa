import os
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

app = Flask(__name__)

# Konfigurasi database SQLite di folder /tmp agar kompatibel dengan Vercel
db_path = os.path.join('/tmp', 'tpa_v2.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------------------------------------
# MODEL DATABASE
# --------------------------------------------------
class Santri(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    absensi = db.relationship('Absensi', backref='santri', lazy=True, cascade="all, delete-orphan")

class Absensi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    santri_id = db.Column(db.Integer, db.ForeignKey('santri.id'), nullable=False)
    tanggal = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()

# --------------------------------------------------
# HELPER TANGGAL & JADWAL MATERI
# --------------------------------------------------
JADWAL_MATERI = {
    'Senin': 'Adab & Akhlak Sehari-hari (Makan, Minum, Orang Tua)',
    'Selasa': 'Kisah Nabi & Sahabat (Storytelling Islami)',
    'Rabu': 'Doa Harian & Zikir Pendek',
    'Kamis': 'Praktik Ibadah (Wudhu & Sholat)',
    'Jumat': 'Mengenal Ciptaan Allah & Tadabbur Alam',
    'Sabtu': 'Seni Islami, Kuis Pekanan & Hafalan',
    'Minggu': 'Libur / Pengajian Bebas'
}

def get_waktu_sekarang():
    tz_wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz_wib)
    
    hari_map = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }
    bulan_map = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
        7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    hari_indo = hari_map.get(now.strftime('%A'), 'Senin')
    tanggal_indo = f"{now.day} {bulan_map[now.month]} {now.year}"
    tanggal_db = now.strftime('%Y-%m-%d')
    materi = JADWAL_MATERI.get(hari_indo, '-')
    
    return hari_indo, tanggal_indo, tanggal_db, materi

# --------------------------------------------------
# ROUTE ADMIN / DASHBOARD
# --------------------------------------------------
@app.route('/')
def admin_dashboard():
    hari_indo, tanggal_indo, tanggal_db, materi = get_waktu_sekarang()
    santri_list = Santri.query.all()
    
    # Hitung Statistik Absensi Hari Ini
    absensi_today = Absensi.query.filter_by(tanggal=tanggal_db).all()
    status_dict = {a.santri_id: a.status for a in absensi_today}
    
    hadir = sum(1 for s in status_dict.values() if s == "Hadir")
    izin = sum(1 for s in status_dict.values() if s == "Izin")
    alfa = sum(1 for s in status_dict.values() if s == "Alfa")

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
                <a href="/orangtua" class="btn btn-light btn-sm fw-bold text-success"><i class="bi bi-eye"></i> Mode Orang Tua</a>
            </div>
        </nav>

        <div class="container my-4">
            <div class="card border-0 bg-success text-white shadow-sm p-3 mb-4 rounded-3">
                <div class="d-flex justify-content-between align-items-center flex-wrap">
                    <div>
                        <span class="badge bg-warning text-dark mb-1">📅 {{ hari_indo }}, {{ tanggal_indo }}</span>
                        <h4 class="fw-bold m-0">Materi Hari Ini: {{ materi }}</h4>
                    </div>
                </div>
            </div>

            <div class="row g-3 mb-4 text-center">
                <div class="col-4">
                    <div class="card bg-success text-white border-0 shadow-sm p-2">
                        <small>Hadir</small>
                        <h3 class="fw-bold m-0" id="stat-hadir">{{ hadir }}</h3>
                    </div>
                </div>
                <div class="col-4">
                    <div class="card bg-warning text-dark border-0 shadow-sm p-2">
                        <small>Izin</small>
                        <h3 class="fw-bold m-0" id="stat-izin">{{ izin }}</h3>
                    </div>
                </div>
                <div class="col-4">
                    <div class="card bg-danger text-white border-0 shadow-sm p-2">
                        <small>Alfa</small>
                        <h3 class="fw-bold m-0" id="stat-alfa">{{ alfa }}</h3>
                    </div>
                </div>
            </div>

            <div class="row g-4">
                <div class="col-md-4">
                    <div class="card border-0 shadow-sm p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-person-plus-fill"></i> Tambah Santri Baru</h5>
                        <form action="/api/tambah-santri" method="POST">
                            <div class="mb-2">
                                <label class="form-label small fw-bold">Nama Santri</label>
                                <input type="text" name="nama" class="form-control" placeholder="Nama lengkap" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Kelompok / Jilid</label>
                                <select name="kategori" class="form-select" required>
                                    <option value="Iqro 1">Iqro 1</option>
                                    <option value="Iqro 2">Iqro 2</option>
                                    <option value="Iqro 3">Iqro 3</option>
                                    <option value="Iqro 4">Iqro 4</option>
                                    <option value="Iqro 5">Iqro 5</option>
                                    <option value="Iqro 6">Iqro 6</option>
                                    <option value="Al-Qur'an">Al-Qur'an</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-success w-100 fw-bold">Simpan Santri</button>
                        </form>
                    </div>
                </div>

                <div class="col-md-8">
                    <div class="card border-0 shadow-sm p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-check2-square"></i> Presensi Santri</h5>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th>Nama</th>
                                        <th>Status Absen</th>
                                        <th class="text-end">Aksi</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for s in santri_list %}
                                    <tr id="row-santri-{{ s.id }}">
                                        <td>
                                            <div class="fw-bold">{{ s.nama }}</div>
                                            <small class="text-muted">{{ s.kategori }}</small>
                                        </td>
                                        <td>
                                            {% set st = status_dict.get(s.id, 'Belum') %}
                                            <span id="badge-{{ s.id }}" class="badge {{ 'bg-success' if st=='Hadir' else ('bg-warning text-dark' if st=='Izin' else ('bg-danger' if st=='Alfa' else 'bg-secondary')) }}">
                                                {{ st }}
                                            </span>
                                        </td>
                                        <td class="text-end">
                                            <button onclick="absenInstan({{ s.id }}, 'Hadir')" class="btn btn-sm btn-outline-success">H</button>
                                            <button onclick="absenInstan({{ s.id }}, 'Izin')" class="btn btn-sm btn-outline-warning">I</button>
                                            <button onclick="absenInstan({{ s.id }}, 'Alfa')" class="btn btn-sm btn-outline-danger">A</button>
                                            <button onclick="hapusSantri({{ s.id }})" class="btn btn-sm btn-light text-danger ms-1" title="Hapus"><i class="bi bi-trash"></i></button>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="3" class="text-center text-muted py-4">Belum ada data santri. Silakan tambahkan di form sebelah kiri.</td>
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
            async function absenInstan(id, status) {
                const res = await fetch('/api/absen', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({santri_id: id, status: status})
                });
                const data = await res.json();
                if(data.success) {
                    const badge = document.getElementById(`badge-${id}`);
                    badge.innerText = status;
                    badge.className = 'badge ' + (status==='Hadir' ? 'bg-success' : (status==='Izin' ? 'bg-warning text-dark' : 'bg-danger'));
                    
                    document.getElementById('stat-hadir').innerText = data.stats.hadir;
                    document.getElementById('stat-izin').innerText = data.stats.izin;
                    document.getElementById('stat-alfa').innerText = data.stats.alfa;
                }
            }

            async function hapusSantri(id) {
                if(confirm("Yakin ingin menghapus santri ini?")) {
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
    ''', santri_list=santri_list, status_dict=status_dict, hari_indo=hari_indo, tanggal_indo=tanggal_indo, materi=materi, hadir=hadir, izin=izin, alfa=alfa)

# --------------------------------------------------
# ROUTE HALAMAN ORANG TUA (READ-ONLY)
# --------------------------------------------------
@app.route('/orangtua')
def portal_orangtua():
    hari_indo, tanggal_indo, tanggal_db, materi = get_waktu_sekarang()
    santri_list = Santri.query.all()
    absensi_today = Absensi.query.filter_by(tanggal=tanggal_db).all()
    status_dict = {a.santri_id: a.status for a in absensi_today}

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Portal Wali Murid - TPA Baiturrahman</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    </head>
    <body class="bg-light">
        <div class="container py-3" style="max-width: 500px;">
            <div class="text-center bg-success text-white p-3 rounded-3 shadow-sm mb-3">
                <h4 class="fw-bold m-0">🕌 TPA BAITURRAHMAN</h4>
                <small>Informasi Pengajian & Kehadiran Santri</small>
            </div>

            <div class="card border-0 shadow-sm p-3 mb-3 bg-white">
                <small class="text-uppercase fw-bold text-success">Jadwal Hari Ini</small>
                <h5 class="fw-bold text-dark m-0">{{ hari_indo }}, {{ tanggal_indo }}</h5>
                <hr class="my-2">
                <small class="text-muted">Materi Pelajaran:</small>
                <div class="fw-bold text-dark">{{ materi }}</div>
            </div>

            <div class="card border-0 shadow-sm p-3 bg-white">
                <h6 class="fw-bold text-success mb-3"><i class="bi bi-card-checklist"></i> Status Kehadiran Santri</h6>
                <div class="list-group list-group-flush">
                    {% for s in santri_list %}
                    <div class="list-group-item d-flex justify-content-between align-items-center px-0">
                        <div>
                            <div class="fw-bold">{{ s.nama }}</div>
                            <small class="text-muted">{{ s.kategori }}</small>
                        </div>
                        {% set st = status_dict.get(s.id, 'Belum Absen') %}
                        <span class="badge {{ 'bg-success' if st=='Hadir' else ('bg-warning text-dark' if st=='Izin' else ('bg-danger' if st=='Alfa' else 'bg-secondary')) }} px-3 py-2">
                            {{ st }}
                        </span>
                    </div>
                    {% else %}
                    <div class="text-center text-muted py-3">Belum ada data santri yang terdaftar.</div>
                    {% endfor %}
                </div>
            </div>

            <div class="text-center mt-4">
                <a href="/" class="text-muted small text-decoration-none">🔑 Masuk Halaman Admin</a>
            </div>
        </div>
    </body>
    </html>
    ''', santri_list=santri_list, status_dict=status_dict, hari_indo=hari_indo, tanggal_indo=tanggal_indo, materi=materi)

# --------------------------------------------------
# API ENDPOINTS (AJAX)
# --------------------------------------------------
@app.route('/api/tambah-santri', methods=['POST'])
def api_tambah_santri():
    nama = request.form.get('nama')
    kategori = request.form.get('kategori')
    if nama and kategori:
        db.session.add(Santri(nama=nama, kategori=kategori))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/absen', methods=['POST'])
def api_absen():
    data = request.json
    santri_id = data.get('santri_id')
    status = data.get('status')
    
    _, _, tanggal_db, _ = get_waktu_sekarang()
    
    existing = Absensi.query.filter_by(santri_id=santri_id, tanggal=tanggal_db).first()
    if existing:
        existing.status = status
    else:
        db.session.add(Absensi(santri_id=santri_id, tanggal=tanggal_db, status=status))
    db.session.commit()

    # Stat terbaru
    absensi_today = Absensi.query.filter_by(tanggal=tanggal_db).all()
    stats = {
        'hadir': sum(1 for a in absensi_today if a.status == "Hadir"),
        'izin': sum(1 for a in absensi_today if a.status == "Izin"),
        'alfa': sum(1 for a in absensi_today if a.status == "Alfa")
    }
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/hapus-santri/<int:santri_id>', methods=['DELETE'])
def api_hapus_santri(santri_id):
    santri = Santri.query.get(santri_id)
    if santri:
        db.session.delete(santri)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

app = app
