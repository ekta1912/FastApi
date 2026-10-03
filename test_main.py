from fastapi.testclient import TestClient
from main import app, load_data, save_data
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def preserve_data_state():
    """Ensure data is preserved before and after each test."""
    original_data = load_data()
    yield
    save_data(original_data)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Patient management system API"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data
    assert data["total_records"] >= 0
    assert data["storage_active"] is True

def test_settings_configuration():
    from config import get_settings
    settings = get_settings()
    assert settings.app_name == "Patient Management System API"
    assert settings.app_version == "1.0.0"
    assert isinstance(settings.cors_origins, list)


def test_about_endpoint():
    response = client.get("/about")
    assert response.status_code == 200
    assert "message" in response.json()

def test_view_patients():
    response = client.get("/view")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "P001" in data

def test_view_single_patient_success():
    response = client.get("/patient/P001")
    assert response.status_code == 200
    patient = response.json()
    assert patient["name"] == "Ananya Sharma"
    assert "bmi" in patient
    assert "verdict" in patient

def test_view_single_patient_not_found():
    response = client.get("/patient/NONEXISTENT_999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Patient not found"

def test_sort_patients_valid():
    response = client.get("/sort?sort_by=bmi&order=asc")
    assert response.status_code == 200
    patients = response.json()
    assert len(patients) > 0
    # verify ascending order
    bmis = [p["bmi"] for p in patients]
    assert bmis == sorted(bmis)

def test_sort_patients_invalid_field():
    response = client.get("/sort?sort_by=invalid_col&order=asc")
    assert response.status_code == 400
    assert "Invalid Field" in response.json()["detail"]

def test_sort_patients_invalid_order():
    response = client.get("/sort?sort_by=bmi&order=sideways")
    assert response.status_code == 400
    assert "Invalid order" in response.json()["detail"]

def test_search_patients_by_city():
    response = client.get("/patients/search?city=jaipur")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(p["city"] == "Jaipur" for p in data["patients"])

def test_search_patients_pagination():
    response = client.get("/patients/search?limit=3&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["patients"]) <= 3
    assert data["limit"] == 3
    assert data["offset"] == 0

def test_analytics_summary():
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_patients"] > 0
    assert stats["average_age"] > 0
    assert stats["average_bmi"] > 0
    assert "gender_distribution" in stats
    assert "verdict_distribution" in stats

def test_create_and_delete_patient():
    new_patient = {
        "id": "PTEST999",
        "name": "Test User",
        "city": "Testing City",
        "age": 25,
        "gender": "female",
        "height": 1.65,
        "weight": 60.0
    }
    # Create
    create_res = client.post("/create", json=new_patient)
    assert create_res.status_code == 201
    assert create_res.json()["message"] == "patient created successfully"

    # Verify creation and computed fields
    get_res = client.get("/patient/PTEST999")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["name"] == "Test User"
    assert data["bmi"] == round(60.0 / (1.65 ** 2), 2)

    # Duplicate creation error
    dup_res = client.post("/create", json=new_patient)
    assert dup_res.status_code == 400

    # Edit patient
    update_res = client.put("/edit/PTEST999", json={"weight": 70.0})
    assert update_res.status_code == 200

    # Delete
    del_res = client.delete("/delete/PTEST999")
    assert del_res.status_code == 200

    # Confirm deletion
    confirm_res = client.get("/patient/PTEST999")
    assert confirm_res.status_code == 404

def test_create_patient_validation_error():
    # Invalid age (gt 120) and invalid gender
    invalid_patient = {
        "id": "PTEST_INV",
        "name": "Invalid Person",
        "city": "Nowhere",
        "age": 200,
        "gender": "unknown_gender",
        "height": -1.5,
        "weight": -50.0
    }
    response = client.post("/create", json=invalid_patient)
    assert response.status_code == 422

def test_batch_create_patients():
    batch = [
        {
            "id": "PBATCH1",
            "name": "Batch User One",
            "city": "Delhi",
            "age": 30,
            "gender": "male",
            "height": 1.75,
            "weight": 72.0
        },
        {
            "id": "PBATCH2",
            "name": "Batch User Two",
            "city": "Noida",
            "age": 28,
            "gender": "female",
            "height": 1.60,
            "weight": 55.0
        }
    ]
    res = client.post("/batch-create", json=batch)
    assert res.status_code == 201
    assert res.json()["inserted_count"] == 2

    # Cleanup batch test records
    client.delete("/delete/PBATCH1")
    client.delete("/delete/PBATCH2")

def test_cors_and_process_time_headers():
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "x-process-time" in response.headers
    assert float(response.headers["x-process-time"]) >= 0.0
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_export_patients_csv():
    import csv
    import io
    response = client.get("/patients/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "patients_export.csv" in response.headers["content-disposition"]
    
    csv_reader = csv.reader(io.StringIO(response.text))
    rows = list(csv_reader)
    assert len(rows) >= 2  # Header + at least 1 record
    headers = rows[0]
    assert headers == ["id", "name", "city", "age", "gender", "height", "weight", "bmi", "verdict"]
    
    # Check that P001 is included
    p001_row = next((r for r in rows[1:] if r[0] == "P001"), None)
    assert p001_row is not None
    assert p001_row[1] == "Ananya Sharma"



