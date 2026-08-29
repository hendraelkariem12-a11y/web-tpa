import os
from flask import Flask, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Ambil URL Database dari Render PostgreSQL
db_url = os.environ.get('DATABASE_URL', 'sqlite:///tpa_local.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Model Data Santri
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
        <title>TPA Baiturrahman - Render</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4 bg-light">
        <div class="container bg-white p-4 rounded shadow-sm" style="max-width: 500px;">
            <h3 class="text-success fw-bold">TPA Baiturrahman</h3>
            <p class="text-muted">Aplikasi Web Flask + SQLAlchemy di Render</p>
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

if __name__ == '__main__':
    app.run(debug=True)
