import os
from flask import Flask, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Gunakan direktori /tmp/ agar SQLite bisa menulis data di Vercel
db_path = os.path.join('/tmp', 'tpa_local.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Santri(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    usia_kategori = db.Column(db.String(50), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    santri_list = Santri.query.all()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TPA Baiturrahman - Vercel</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4 bg-light">
        <div class="container bg-white p-4 rounded shadow-sm" style="max-width: 500px;">
            <h3 class="text-success fw-bold">🕌 TPA Baiturrahman</h3>
            <p class="text-muted">Aplikasi Flask + SQLAlchemy Aktif di Vercel</p>
            <hr>
            <h5>Daftar Santri:</h5>
            <ul class="list-group">
                {% for s in santri_list %}
                    <li class="list-group-item">{{ s.nama }} - {{ s.usia_kategori }}</li>
                {% else %}
                    <li class="list-group-item text-muted">Belum ada data santri.</li>
                {% endfor %}
            </ul>
        </div>
    </body>
    </html>
    ''', santri_list=santri_list)

app = app
