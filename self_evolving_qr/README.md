# Self-Evolving QR Identification System

A production-style Flask prototype for secure QR identification with adaptive custom attributes.

## Run locally

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python run.py
```

Open http://127.0.0.1:5000. Demo credentials: `admin` / `Admin@123`.

## Highlights
- Flask application factory, SQLAlchemy ORM, Flask-Login and hashed passwords
- Records, categories, custom fields, role-aware access, QR PNG generation
- Public token verification with inactive/revoked protection and scan history
- Dashboard metrics, reports and JSON API
- SQLite by default; set `DATABASE_URL` for PostgreSQL later

## API
`GET /api/dashboard/stats`, `GET /api/identifications`, `POST /api/identifications`, `GET /api/identify/<token>`, `POST /api/scans`.

QR codes contain only `/identify/<secure-token>`; private fields stay server-side.
