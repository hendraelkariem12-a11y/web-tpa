import os
from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Konfigurasi SQLite di folder /tmp agar Vercel Serverless Function dapat menulis data
db_path = os.path.join('/tmp', 'tpa_dashboard.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------------------------------------
# MODEL DATABASE (SQLAlchemy)
# --------------------------------------------------
class Santri(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(50), nullable=False) # Iqro / Al-Qur'an
    absensi = db.relationship('Absensi', backref='santri', lazy=True, cascade="all, delete-orphan")

class Absensi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    santri_id = db.Column(db.Integer, db.ForeignKey('santri.id'), nullable=False)
    tanggal = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False) # Hadir / Izin / Alfa

# Inisialisasi Database & Data Awal
with app.app_context():
    db.create_all()
    if Santri.query.count() == 0:
        s1 = Santri(nama="Ahmad Fauzi", kategori="Iqro 3")
        s2 = Santri(nama="Siti Nurhaliza", kategori="Al-Qur'an")
        s3 = Santri(nama="Muhammad Bilal", kategori="Iqro 1")
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        # Dummy Data Absensi Hari Ini
        today = datetime.now().strftime("%Y-%m-%d")
        db.session.add_all([
            Absensi(santri_id=s1.id, tanggal=today, status="Hadir"),
            Absensi(santri_id=s2.id, tanggal=today, status="Hadir"),
            Absensi(santri_id=s3.id, tanggal=today, status="Izin")
        ])
        db.session.commit()

# --------------------------------------------------
# ROUTE UTAMA (DASHBOARD)
# --------------------------------------------------
@app.route('/')
def home():
    santri_list = Santri.query.all()
    total_santri = len(santri_list)
    
    # Hitung Statistik Absensi Hari Ini
    today = datetime.now().strftime("%Y-%m-%d")
    absensi_today = Absensi.query.filter_filter_by(tanggal=today).all() if hasattr(Absensi.query, 'filter_filter_by') else Absensi.query.filter_by(tanggal=today).all()
    
    hadir = sum(1 for a in absensi_today if a.status == "Hadir")
    izin = sum(1 for a in absensi_today if a.status == "Izin")
    alfa = sum(1 for a in absensi_today if a.status == "Alfa")

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard TPA Baiturrahman</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    </head>
    <body class="bg-light">
        <!-- Navbar -->
        <nav class="navbar navbar-expand-lg navbar-dark bg-success shadow-sm">
            <div class="container">
                <a class="navbar-brand fw-bold" href="#">🕌 TPA Baiturrahman</a>
            </div>
        </nav>

        <div class="container my-4">
            <!-- Ringkasan Kartu -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card bg-primary text-white shadow-sm border-0 p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-0">Total Santri</h6>
                                <h2 class="fw-bold mb-0">{{ total_santri }}</h2>
                            </div>
                            <i class="bi bi-people-fill fs-1"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white shadow-sm border-0 p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-0">Hadir Hari Ini</h6>
                                <h2 class="fw-bold mb-0">{{ hadir }}</h2>
                            </div>
                            <i class="bi bi-check-circle-fill fs-1"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-dark shadow-sm border-0 p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-0">Izin Hari Ini</h6>
                                <h2 class="fw-bold mb-0">{{ izin }}</h2>
                            </div>
                            <i class="bi bi-exclamation-circle-fill fs-1"></i>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-danger text-white shadow-sm border-0 p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-0">Alfa Hari Ini</h6>
                                <h2 class="fw-bold mb-0">{{ alfa }}</h2>
                            </div>
                            <i class="bi bi-x-circle-fill fs-1"></i>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row g-4">
                <!-- Form Tambah Santri & Grafik -->
                <div class="col-md-5">
                    <div class="card shadow-sm border-0 p-3 mb-4">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-person-plus"></i> Tambah Santri Baru</h5>
                        <form action="/tambah-santri" method="POST">
                            <div class="mb-2">
                                <label class="form-label small fw-bold">Nama Lengkap</label>
                                <input type="text" name="nama" class="form-control" required placeholder="Contoh: Ahmad">
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Kategori/Jilid</label>
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
                            <button type="submit" class="btn btn-success w-100">Simpan Santri</button>
                        </form>
                    </div>

                    <div class="card shadow-sm border-0 p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-pie-chart-fill"></i> Diagram Absensi</h5>
                        <canvas id="attendanceChart" style="max-height: 200px;"></canvas>
                    </div>
                </div>

                <!-- Tabel Santri & Presensi -->
                <div class="col-md-7">
                    <div class="card shadow-sm border-0 p-3">
                        <h5 class="fw-bold text-success mb-3"><i class="bi bi-journal-check"></i> Data Santri & Absensi Hari Ini</h5>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th>Nama Santri</th>
                                        <th>Kategori</th>
                                        <th>Aksi Absensi</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for s in santri_list %}
                                    <tr>
                                        <td class="fw-bold">{{ s.nama }}</td>
                                        <td><span class="badge bg-secondary">{{ s.kategori }}</span></td>
                                        <td>
                                            <a href="/absen/{{ s.id }}/Hadir" class="btn btn-sm btn-outline-success">Hadir</a>
                                            <a href="/absen/{{ s.id }}/Izin" class="btn btn-sm btn-outline-warning">Izin</a>
                                            <a href="/absen/{{ s.id }}/Alfa" class="btn btn-sm btn-outline-danger">Alfa</a>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="3" class="text-center text-muted">Belum ada data santri.</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Script Chart.js -->
        <script>
            const ctx = document.getElementById('attendanceChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Hadir', 'Izin', 'Alfa'],
                    datasets: [{
                        data: [{{ hadir }}, {{ izin }}, {{ alfa }}],
                        backgroundColor: ['#198754', '#ffc107', '#dc3545']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        </script>
    </body>
    </html>
    ''', santri_list=santri_list, total_santri=total_santri, hadir=hadir, izin=izin, alfa=alfa)

# --------------------------------------------------
# ROUTE AKSI (DATABASE)
# --------------------------------------------------
@app.route('/tambah-santri', methods=['POST'])
def tambah_santri():
    nama = request.form.get('nama')
    kategori = request.form.get('kategori')
    if nama and kategori:
        santri_baru = Santri(nama=nama, kategori=kategori)
        db.session.add(santri_baru)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/absen/<int:santri_id>/<string:status>')
def absen(santri_id, status):
    today = datetime.now().strftime("%Y-%m-%d")
    # Cek apakah sudah absen hari ini
    existing_absen = Absensi.query.filter_by(santri_id=santri_id, tanggal=today).first()
    if existing_absen:
        existing_absen.status = status
    else:
        absen_baru = Absensi(santri_id=santri_id, tanggal=today, status=status)
        db.session.add(absen_baru)
    db.session.commit()
    return redirect(url_for('home'))

app = app
