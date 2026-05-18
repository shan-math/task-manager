# Task Management System (TMS)

Enterprise-style task management with Flask, MySQL, and a high-tech dark UI.

## Project structure

```
task-manager/
├── Backend/                 # Python API & business logic
│   ├── app.py               # Flask application entry
│   ├── blueprints/          # Route handlers
│   ├── services/            # Email, audit, reminders
│   ├── sql/                 # Database schema
│   ├── tests/               # Pytest suite
│   ├── uploads/             # File attachments (runtime)
│   ├── requirements.txt
│   └── .env.example
├── Frontend/                # UI layer
│   ├── templates/           # Jinja2 HTML
│   └── static/              # CSS, JavaScript
├── deploy/                  # Production deployment
│   ├── Dockerfile
│   └── docker-compose.yml
└── README.md
```

## Local development

### 1. Environment

```powershell
cd task-manager
copy Backend\.env.example Backend\.env
# Edit Backend\.env with MySQL credentials
```

`.env` in the project root is also loaded if present.

### 2. Install & database

```powershell
cd Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
mysql -u root -p < sql\schema.sql
flask --app app init-db
```

### 3. Run

```powershell
cd Backend
python app.py
```

Open http://127.0.0.1:5000

## Production deployment (Docker)

```powershell
cd deploy
copy ..\Backend\.env.example .env
# Edit .env — set MYSQL_PASSWORD, FLASK_SECRET_KEY, etc.
docker compose up --build -d
```

| Service | URL / port |
|---------|------------|
| Web app | http://localhost:5000 |
| MySQL   | localhost:3306 |

Uploads persist in the `uploads_data` volume.

### Environment variables (production)

| Variable | Purpose |
|----------|---------|
| `FLASK_SECRET_KEY` | Session signing (required in prod) |
| `MYSQL_*` | Database connection |
| `MAIL_*` | SMTP for notifications |
| `FLASK_ENV=production` | Enables secure cookies |

## API

`GET /api/tasks` — session cookie or `X-API-Token` header.

## Tests

```powershell
cd Backend
pytest
```

## Default admin

On first init (empty database): `admin` / value of `DEFAULT_ADMIN_PASSWORD` in `.env`.
