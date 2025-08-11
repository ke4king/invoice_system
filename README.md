# Invoice Management System (FastAPI + Vue3)

An end-to-end invoice ingestion and management platform built with FastAPI, MySQL, SQLAlchemy, Celery, Redis, and a Vue 3 + Vite + Element Plus frontend. It supports email-based invoice collection, OCR (Baidu), structured storage, searching, monitoring, and batch printing.

English | [中文说明](README.zh-CN.md)

## Features
- Invoice ingestion from email and manual upload
- OCR via Baidu OCR, with retry and QPS control
- Secure user auth (JWT), role-based operations
- Search, statistics, dashboard, and enhanced logging/monitoring
- Batch printing and export (Excel)
- Async workers with Celery and Redis
- Docker Compose one-command setup

## Architecture
- Backend: FastAPI, SQLAlchemy, Alembic, Celery, Redis, MySQL
- Frontend: Vue 3, Vite, Pinia, Element Plus, ECharts
- Docker: backend + frontend + MySQL + Redis + Celery worker/beat

## Quick Start

### Prerequisites
- Docker and Docker Compose v2
- Optional for local dev without containers: Node.js 18+, Python 3.11+

### 1) Configure environment
Copy and edit the example env file at project root:

```bash
cp .env.example .env
```

Update secrets like `SECRET_KEY`, database credentials, and any OCR keys.

### 2) Run with Docker Compose (recommended)

```bash
docker compose up -d --build
```

Services:
- Frontend: http://localhost
- Backend API: http://127.0.0.1:8000
- API Docs (Swagger UI): http://127.0.0.1:8000/docs

### 3) Local development helper (optional)

There is a helper script that spins up MySQL/Redis/Celery via Docker, and runs frontend/backend locally:

```bash
./start-dev.sh
```

This script will prepare a `.env` if missing and start all services. See the script output for URLs and logs.

## Configuration
Key environment variables (see `backend/app/core/config.py` for defaults):

- `SECRET_KEY`: JWT/crypto secret
- `DATABASE_URL`: e.g. `mysql+pymysql://user:pass@localhost:3306/invoice_system`
- `REDIS_URL`: e.g. `redis://localhost:6379/0`
- `UPLOAD_DIR`: path for file storage, defaults to `./storage`
- `MAX_FILE_SIZE`: max upload size in bytes (default 10MB)
- `BAIDU_OCR_API_KEY`, `BAIDU_OCR_SECRET_KEY`: Baidu OCR credentials
- `OCR_RETRY_TIMES`, `OCR_TIMEOUT`, `OCR_QPS_LIMIT`, `OCR_AMOUNT_IN_CENTS`
- `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- `LOG_LEVEL`, `LOG_FILE_MAX_SIZE`, `LOG_FILE_BACKUP_COUNT`
- Cookie/health/rate limit flags: `USE_COOKIE_AUTH`, `COOKIE_SECURE`, `HEALTH_REQUIRE_AUTH`, `RATE_LIMIT_ENABLED`

## Project Structure

```
backend/
  app/
    api/api_v1/endpoints/    # Auth, emails, invoices, logs, print APIs
    core/                    # Settings, DB, deps, logging, metrics
    models/                  # SQLAlchemy models
    schemas/                 # Pydantic schemas
    services/                # Business services (OCR, email, invoice, etc.)
    workers/                 # Celery app and tasks
    main.py                  # FastAPI entry
  Dockerfile
  requirements.txt
frontend/
  src/                      # Vue 3 app (Vite + Element Plus)
  Dockerfile
docker-compose.yml          # Prod/preview
docker-compose.dev.yml      # Dev (containers for infra + celery)
start-dev.sh                # Local dev helper
```

## API
- Health: `GET /health`, `GET /health/detailed`
- Status: `GET /api/status`
- OpenAPI docs: `GET /docs`

## Development
- Backend dev server: `uvicorn app.main:app --reload`
- Frontend dev server: `npm run dev` in `frontend/`
- Tests (backend): `pytest` in `backend/`

## Security
- Never commit real secrets. Use `.env` (ignored by git) and `.env.example` for placeholders.
- Rotate credentials regularly and set strong passwords for the admin user.

## Contributing
Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License
This project is licensed under the MIT License - see [LICENSE](LICENSE).


