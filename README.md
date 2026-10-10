# 🏥 FastAPI Patient Management System

[![CI Pipeline](https://github.com/ekta1912/FastApi/actions/workflows/ci.yml/badge.svg)](https://github.com/ekta1912/FastApi/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063.svg?logo=pydantic&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A production-ready, high-performance RESTful API built with **FastAPI** and **Pydantic v2** for managing patient health records, logging clinical vital signs (blood pressure, heart rate, SpO2), calculating real-time clinical metrics (BMI, WHO verdicts, AHA blood pressure stages), evaluating cardiovascular/metabolic risk profiles, and performing secured database administration and disaster recovery.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    Client["Client (Browser, cURL, Mobile, Frontend)"]
    
    subgraph FastAPI App ["FastAPI Application"]
        CORS["CORS Middleware"]
        Tracing["Tracing & Latency Middleware (X-Request-ID, X-Process-Time)"]
        SecurityLayer["API Key Security (X-API-Key)"]
        Exc["Domain Exception Envelopes"]
        
        subgraph Endpoints ["API Route Handlers"]
            General["General / Health / Info"]
            Patients["Patients CRUD / Search / Sort / Vitals / Import-Export"]
            Analytics["Population Analytics / Risk Stratification / Demographics"]
            Admin["Admin Backups / Integrity Audit / DB Compaction"]
        end
        
        Models["Modular Pydantic v2 Models & Computed Fields (models.py)"]
        Config["Configuration Management (config.py)"]
        AuditLog["Structured Request Audit Logger"]
    end
    
    Storage[("Local JSON Storage (patient.json)")]
    Backups[("Point-in-Time Backups (/backups/)")]
    
    Client --> CORS
    CORS --> Tracing
    Tracing --> AuditLog
    Tracing --> SecurityLayer
    SecurityLayer --> Exc
    Exc --> Endpoints
    Endpoints --> Models
    Endpoints --> Config
    Endpoints --> Storage
    Endpoints --> Backups
```

---

## 🚀 Key Features

- **Full Patient Lifecycle Management (CRUD)**: Create, view, update, and delete patient records with unique identifiers and type-safe validation.
- **Clinical Profile & Medical History**: Track blood group (`A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`), allergies, and documented chronic conditions.
- **Vital Signs & Blood Pressure Classification**: Record timestamped patient vitals (systolic, diastolic, heart rate, temperature, SpO2) with automatic AHA/ACC blood pressure stage categorization (*Normal*, *Elevated*, *Hypertension Stage 1*, *Hypertension Stage 2*, *Hypertensive Crisis*).
- **Computed Health Metrics**: Real-time Body Mass Index (BMI) and WHO health classifications (*Underweight*, *Normal*, *Overweight*, *Obese*) computed automatically via `@computed_field`.
- **Clinical Risk Assessment**: Stratifies patients into clinical risk categories (*Low*, *Moderate*, *High*, *Critical*) based on age and BMI vulnerability factors.
- **Population Demographics & Regional Metrics**: Endpoint (`/analytics/demographics`) breaking down age brackets (Pediatric, Young Adult, Adult, Senior), blood group distributions, allergy frequencies, and regional city metrics.
- **Bulk Data Import & Export**:
  - Export data as downloadable **CSV** (`/patients/export/csv`) or structured **JSON** (`/patients/export/json`).
  - Bulk import patients with collision resolution strategies (*skip*, *overwrite*, *fail*).
- **Administrative Security & Operations**:
  - Secured via configurable **API Key Authentication** (`X-API-Key`).
  - Create and restore point-in-time timestamped snapshots.
  - Automated database **integrity audits** (`/admin/integrity`) to detect schema discrepancies, bounds violations, and BMI drift.
  - Database **compaction and deterministic key sorting** (`/admin/compact`).
- **Enterprise Middleware & Observability**:
  - Global **CORS** middleware with configurable origin whitelists.
  - Request correlation ID tracing (`X-Request-ID`) generated per request and propagated across response headers and error envelopes.
  - Request latency profiling (`X-Process-Time`).
  - Structured audit logging per request.
- **Production Containerization**: Multi-stage `Dockerfile` and `docker-compose.yml` with built-in container healthchecks.
- **Automated CI/CD**: Matrix testing across Python 3.10, 3.11, 3.12, and 3.13 via GitHub Actions.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core programming language runtime |
| **FastAPI** | High-performance asynchronous web framework |
| **Pydantic v2** | Data modeling, validation, computed fields, and settings |
| **Uvicorn** | ASGI web server for asynchronous request dispatching |
| **Pytest** | Automated unit and integration testing suite |
| **HTTPX / TestClient** | Client-side test fixtures and endpoint verification |
| **Docker & Compose** | Containerized deployment and local orchestration |

---

## 📦 Getting Started

### Option A: Local Python Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ekta1912/FastApi.git
   cd FastApi
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv myenv
   myenv\Scripts\activate

   # macOS / Linux
   python3 -m venv myenv
   source myenv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the development server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Option B: Docker & Docker Compose

Run the entire service in an isolated, containerized environment:

```bash
docker compose up -d --build
```

To view live container logs:
```bash
docker compose logs -f
```

To stop the container:
```bash
docker compose down
```

---

## ⚙️ Environment Configuration

The application uses `config.py` with environment variable overrides:

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `Patient Management System API` | Name displayed in OpenAPI documentation |
| `APP_VERSION` | `1.0.0` | Semantic API version |
| `APP_ENV` | `production` | Execution environment (`development`, `staging`, `production`) |
| `APP_DEBUG` | `false` | Enable or disable debug mode |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins |
| `ADMIN_API_KEY` | `admin-secret-key-123` | Secret key required for `/admin/*` operations |
| `DATA_FILE_PATH` | `./patient.json` | Path to the persistent JSON storage file |

---

## 📖 Interactive Documentation

Once the server is running, explore the interactive documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📌 Complete API Endpoint Reference

### General & System
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API landing welcome message |
| `GET` | `/health` | System health check, active records, version, and environment |
| `GET` | `/about` | API description and capabilities |

### Patient Operations & Vitals
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/view` | Retrieve all registered patient records |
| `GET` | `/patient/{patient_id}` | Retrieve details and calculated metrics for a patient |
| `POST` | `/patient/{patient_id}/vitals` | Record vital signs and calculate blood pressure classification |
| `GET` | `/patient/{patient_id}/vitals` | Retrieve chronological vitals history for a patient |
| `GET` | `/sort` | Sort patients by `height`, `weight`, or `bmi` (`asc` or `desc`) |
| `GET` | `/patients/search` | Advanced multi-parameter search with pagination |
| `GET` | `/patients/high-risk` | Retrieve patients in `High` or `Critical` risk tiers |
| `GET` | `/patients/export/csv` | Download patient database as a formatted CSV file |
| `GET` | `/patients/export/json` | Export patient records as structured JSON with metadata |
| `POST` | `/patients/import/json` | Bulk import patients with collision strategy (*skip*, *overwrite*, *fail*) |
| `POST` | `/create` | Register a new single patient record |
| `POST` | `/batch-create` | Atomically register multiple patient records |
| `PUT` | `/edit/{patient_id}` | Partially update patient details and recalculate metrics |
| `DELETE` | `/delete/{patient_id}` | Remove a patient record by ID |

### Population Analytics & Demographics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/analytics/summary` | Population statistics (averages, gender & BMI distribution) |
| `GET` | `/analytics/risk-assessment` | Clinical risk breakdown and factor analysis |
| `GET` | `/analytics/demographics` | Age brackets, blood groups, allergy frequencies, and regional city metrics |

### Secured Administration (Requires `X-API-Key`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/integrity` | Audit database for missing fields, bounds violations, and BMI drift |
| `POST` | `/admin/compact` | Defragment, sort keys deterministically, and optimize JSON file |
| `POST` | `/admin/backup` | Create a timestamped point-in-time JSON database snapshot |
| `GET` | `/admin/backups` | List all historical backups in storage |
| `POST` | `/admin/restore` | Restore database state from a specified backup snapshot |

---

## 🧪 Automated Testing

Execute the comprehensive test suite with `pytest`:

```bash
# Run tests with detailed output
pytest test_main.py -v
```

All 35 automated test cases verify:
- Complete CRUD flows and boundary validations.
- Real-time BMI and WHO verdict computation.
- Clinical blood pressure classification across all AHA stages.
- Patient vital sign logging and chronological history retrieval.
- Batch creation, conflict handling, and collision strategies.
- Dynamic sorting, multi-criteria filtering, and pagination.
- Population health summary, risk stratification, and regional demographics.
- CSV and JSON export streaming headers and structure.
- Secured administrative backups, restoration, and data compaction.
- Database integrity verification and anomaly reporting.
- API key authentication checks (401 on unauthorized).
- CORS headers, `X-Request-ID` correlation tracing, and `X-Process-Time` timing middleware.
- Structured domain exception responses (`PATIENT_NOT_FOUND`, `UNAUTHORIZED_ACCESS`, etc.).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
