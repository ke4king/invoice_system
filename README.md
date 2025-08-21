# Invoice Management System (FastAPI + Vue3)

A comprehensive enterprise-grade invoice management platform built with modern technologies. Features intelligent email collection, advanced OCR processing, real-time monitoring, and flexible printing options. Perfect for businesses requiring automated invoice processing and management.

English | [中文说明](README.zh-CN.md)

## 📸 Screenshots

### Dashboard Overview
![Dashboard](image/dashboard.png)
*Real-time dashboard showing invoice statistics, processing metrics, and system health*

### Invoice Management Interface
![Invoice Management](image/screenshot-1.png)
*Invoice list with advanced filtering, search, and status management*

### Email Configuration
![Email Settings](image/screenshot-2.png)
*Email account configuration for automated invoice collection*

### Print Layout Options
![Print Settings](image/screenshot-3.png)
*Flexible printing options with 1/2/4 invoices per page layouts*

### System Monitoring
![Monitoring Dashboard](image/screenshot-4.png)
*Comprehensive system monitoring with performance metrics and logs*

## ✨ Key Features

### 📧 Intelligent Email Integration
- **Automated Email Collection**: Connect to email servers (IMAP/POP3) for automatic invoice retrieval
- **Email Configuration Management**: Easy setup and management of multiple email accounts
- **Email Processing Queue**: Async processing with Celery for high-throughput email handling
- **Email Status Tracking**: Real-time monitoring of email processing status

### 🤖 Advanced OCR Processing
- **Baidu OCR Integration**: High-accuracy optical character recognition for Chinese invoices
- **Intelligent Retry Logic**: Automatic retry with exponential backoff for failed OCR requests
- **QPS Rate Limiting**: Configurable rate limits to respect API quotas and avoid throttling
- **OCR Caching**: Smart caching system to reduce redundant API calls and improve performance
- **Cost Optimization**: Efficient token usage with intelligent processing strategies

### 🔐 Security & Authentication
- **JWT Authentication**: Secure token-based authentication with configurable expiration
- **Role-Based Access Control**: Granular permissions system (Admin, User, Read-only roles)
- **Password Security**: Strong password requirements with bcrypt hashing
- **Session Management**: Secure session handling with configurable timeouts
- **API Rate Limiting**: Built-in rate limiting to prevent abuse

### 📊 Dashboard & Analytics
- **Real-time Statistics**: Live dashboard with key metrics and KPIs
- **Interactive Charts**: Visual data representation using ECharts
- **Invoice Analytics**: Comprehensive statistics on invoice processing, success rates, and trends
- **Performance Monitoring**: System health metrics and performance indicators
- **Custom Date Ranges**: Flexible time period filtering for analytics

### 🔍 Advanced Search & Filtering
- **Full-text Search**: Multi-field search across invoice content, metadata, and attachments
- **Date Range Filtering**: Filter by upload date, processing date, or invoice date
- **Status-based Filtering**: Filter by processing status (pending, processing, completed, failed)
- **Email Source Filtering**: Filter invoices by originating email account
- **Pagination Support**: Efficient handling of large datasets with pagination

### 🖨️ Flexible Printing & Export
- **Multiple Layout Options**:
  - 1 invoice per page (standard layout)
  - 2 invoices per page (compact layout)
  - 4 invoices per page (ultra-compact layout)
- **Batch Printing**: Print multiple invoices in a single operation
- **Excel Export**: Export invoice data to Excel with customizable templates
- **Print Preview**: WYSIWYG preview before printing
- **Custom Templates**: Support for custom print templates and layouts

### 📈 Enhanced Monitoring & Logging
- **Real-time System Monitoring**: Live system health and performance metrics
- **Comprehensive Logging**: Structured logging with configurable levels
- **Error Tracking**: Detailed error reporting with stack traces
- **Performance Metrics**: Response times, throughput, and resource utilization
- **Audit Trail**: Complete audit logs for compliance and debugging

### ⚡ Async Processing
- **Celery Integration**: Distributed task processing with Redis as message broker
- **Task Scheduling**: Periodic tasks with Celery Beat
- **Background Jobs**: Non-blocking processing for OCR, email fetching, and report generation
- **Task Monitoring**: Real-time task status and progress tracking
- **Retry Mechanisms**: Automatic retry for failed tasks with configurable policies

### 🐳 DevOps & Deployment
- **Docker Compose**: One-command deployment for all services
- **Multi-environment Support**: Separate configurations for development, staging, and production
- **Health Checks**: Automated health monitoring for all services
- **Auto-scaling Ready**: Containerized architecture supports horizontal scaling
- **Database Migrations**: Alembic for smooth database schema updates

## 🏗️ System Architecture

### Backend Architecture
- **FastAPI**: High-performance async web framework for building APIs
- **SQLAlchemy + Alembic**: ORM with database migrations for data persistence
- **MySQL**: Relational database for structured invoice and user data
- **Redis**: High-performance caching and message broker for Celery
- **Celery + Celery Beat**: Distributed task queue for async processing
- **Pydantic**: Data validation and serialization
- **JWT**: Secure authentication with configurable token expiration

### Frontend Architecture
- **Vue 3**: Progressive JavaScript framework with Composition API
- **Vite**: Next-generation frontend tooling for fast development
- **Pinia**: Intuitive state management for Vue applications
- **Element Plus**: Enterprise-grade Vue component library
- **ECharts**: Powerful charting and visualization library
- **Vue Router**: Official router for Vue.js with advanced routing features
- **Axios**: Promise-based HTTP client for API communication

### Infrastructure & DevOps
- **Docker + Docker Compose**: Containerized deployment with service orchestration
- **Nginx**: High-performance web server and reverse proxy
- **Supervisor**: Process management for production deployments
- **GitHub Actions**: CI/CD pipeline with automated testing and deployment
- **Pre-built Images**: Optimized container images available on GHCR

### Data Flow Architecture
```
Email Sources → IMAP/POP3 → Email Processing → Invoice Extraction → OCR Processing → Data Storage
                                                                 ↓
User Interface ← API Layer ← Business Logic ← Database/Redis ← Background Tasks
                                                                 ↓
Reporting & Analytics ← Monitoring ← Logging ← Error Tracking
```

### Service Components
- **API Gateway**: FastAPI application serving RESTful APIs
- **Authentication Service**: JWT-based user authentication and authorization
- **Email Service**: Automated email collection and processing
- **OCR Service**: Baidu OCR integration with retry logic
- **Invoice Service**: Invoice data processing and management
- **Print Service**: Flexible printing with multiple layout options
- **Monitoring Service**: System health and performance monitoring
- **Logging Service**: Structured logging with rotation and backup

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

You can run with local builds, or use prebuilt images on GitHub Container Registry (GHCR).

Using prebuilt images (recommended for CI/CD and servers):

```bash
export FRONTEND_IMAGE=ghcr.io/ke4king/invoice_system-frontend:latest
export BACKEND_IMAGE=ghcr.io/ke4king/invoice_system-backend:latest

docker compose pull
docker compose up -d
```

Build locally instead of using prebuilt images:

```bash
unset FRONTEND_IMAGE BACKEND_IMAGE
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

## 🔌 API Documentation

### Core Endpoints

#### System Health & Status
- `GET /health` - Basic health check
- `GET /health/detailed` - Comprehensive system health with metrics
- `GET /api/status` - Application status and version information
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI specification

#### Authentication
- `POST /api/v1/auth/login` - User login with JWT token
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `GET /api/v1/auth/me` - Get current user information

#### Invoice Management
- `GET /api/v1/invoices/` - List invoices with filtering and pagination
- `POST /api/v1/invoices/` - Upload new invoice
- `GET /api/v1/invoices/{id}` - Get invoice details
- `PUT /api/v1/invoices/{id}` - Update invoice information
- `DELETE /api/v1/invoices/{id}` - Delete invoice
- `POST /api/v1/invoices/{id}/reprocess` - Reprocess invoice with OCR

#### Email Management
- `GET /api/v1/emails/` - List email configurations
- `POST /api/v1/emails/` - Add new email configuration
- `PUT /api/v1/emails/{id}` - Update email configuration
- `DELETE /api/v1/emails/{id}` - Remove email configuration
- `POST /api/v1/emails/{id}/test` - Test email connection

#### Batch Operations
- `POST /api/v1/print/batch` - Batch print invoices with layout options
- `POST /api/v1/export/excel` - Export invoices to Excel format
- `POST /api/v1/invoices/batch-delete` - Batch delete invoices

#### Monitoring & Analytics
- `GET /api/v1/monitoring/dashboard` - Dashboard statistics and metrics
- `GET /api/v1/logs/` - System logs with filtering
- `GET /api/v1/monitoring/performance` - Performance metrics
- `GET /api/v1/monitoring/tasks` - Celery task status

#### Configuration
- `GET /api/v1/configs/` - List system configurations
- `PUT /api/v1/configs/{key}` - Update configuration value

### API Features
- **JWT Authentication**: Bearer token in Authorization header
- **Role-based Access**: Different permissions for Admin/User roles
- **Rate Limiting**: Configurable rate limits per endpoint
- **Request Validation**: Pydantic models for input validation
- **Error Handling**: Structured error responses with codes
- **Pagination**: Cursor-based pagination for large datasets
- **Filtering**: Advanced filtering options for all list endpoints
- **CORS Support**: Cross-origin requests enabled for frontend

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


