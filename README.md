# 🏥 FastAPI Patient Management System

A high-performance, lightweight RESTful API built with **FastAPI** and **Pydantic v2** for managing patient health records, calculating BMI dynamically, and analyzing patient statistics.

---

## 🚀 Features

- **CRUD Operations**: Create, read, update, and delete patient records with unique patient IDs.
- **Computed Health Metrics**: Automatic real-time BMI computation and health verdict assignment (Underweight, Normal, Overweight, Obese) using Pydantic `@computed_field`.
- **Sorting & Filtering**: Sort patients dynamically by height, weight, or BMI in ascending/descending order.
- **Advanced Search**: Query patients by multiple criteria such as city, gender, age range, and BMI verdict with pagination.
- **Health Analytics**: Aggregate summary endpoint providing averages and distribution statistics.
- **Interactive Documentation**: Auto-generated Swagger UI and ReDoc documentation out-of-the-box.
- **Automated Testing**: Comprehensive unit test suite with `pytest` and FastAPI's `TestClient`.

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **FastAPI**: Modern, fast web framework for building APIs.
- **Pydantic v2**: Data validation and settings management.
- **Uvicorn**: Lightning-fast ASGI web server implementation.
- **Pytest & HTTPX**: Testing framework and asynchronous HTTP client for endpoint verification.

---

## 📦 Installation & Setup

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

4. **Run the API server**:
   ```bash
   uvicorn main:app --reload
   ```
   The application will be accessible at `http://127.0.0.1:8000`.

---

## 📖 Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📌 API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root welcome message |
| `GET` | `/health` | API health check and status |
| `GET` | `/about` | API information and description |
| `GET` | `/view` | Retrieve all patient records |
| `GET` | `/patient/{patient_id}` | Retrieve details of a specific patient |
| `GET` | `/sort` | Sort patients by `height`, `weight`, or `bmi` |
| `GET` | `/patients/search` | Search & filter patients with pagination |
| `GET` | `/analytics/summary` | Aggregate statistical summary of all patients |
| `POST` | `/create` | Register a new patient record |
| `POST` | `/batch-create` | Register multiple patients in a single batch |
| `PUT` | `/edit/{patient_id}` | Update existing patient details |
| `DELETE` | `/delete/{patient_id}` | Remove a patient record |

---

## 🧪 Running Tests

To run the automated test suite:
```bash
pytest test_main.py -v
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
