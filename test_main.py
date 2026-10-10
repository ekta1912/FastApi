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

def test_risk_assessment_endpoint():
    response = client.get("/analytics/risk-assessment")
    assert response.status_code == 200
    data = response.json()
    assert data["total_assessed"] > 0
    assert "risk_breakdown" in data
    assert "high_risk_percentage" in data
    assert len(data["patients"]) == data["total_assessed"]
    
    # Check fields of patient profile
    first_patient = data["patients"][0]
    assert "risk_level" in first_patient
    assert first_patient["risk_level"] in ["Low", "Moderate", "High", "Critical"]
    assert isinstance(first_patient["risk_factors"], list)

def test_high_risk_patients_endpoint():
    response = client.get("/patients/high-risk")
    assert response.status_code == 200
    patients = response.json()
    assert isinstance(patients, list)
    for p in patients:
        assert p["risk_level"] in ["High", "Critical"]

def test_admin_backup_and_restore_workflow():
    from main import BACKUP_DIR
    import os
    
    admin_headers = {"X-API-Key": "admin-secret-key-123"}

    # Unauthorized access check
    unauth_res = client.post("/admin/backup")
    assert unauth_res.status_code == 401
    assert unauth_res.json()["error_code"] == "UNAUTHORIZED_ACCESS"

    # 1. Create backup with valid key
    res = client.post("/admin/backup", headers=admin_headers)
    assert res.status_code == 201
    backup_data = res.json()
    assert "backup" in backup_data
    filename = backup_data["backup"]["filename"]
    assert filename.startswith("backup_")
    assert backup_data["backup"]["record_count"] >= 0

    # 2. List backups
    list_res = client.get("/admin/backups", headers=admin_headers)
    assert list_res.status_code == 200
    listed = list_res.json()
    assert listed["total_backups"] >= 1
    assert any(b["filename"] == filename for b in listed["backups"])

    # 3. Restore from backup
    restore_res = client.post("/admin/restore", json={"filename": filename}, headers=admin_headers)
    assert restore_res.status_code == 200
    assert "restored_records" in restore_res.json()

    # 4. Restore from non-existent backup
    fail_res = client.post("/admin/restore", json={"filename": "non_existent_file.json"}, headers=admin_headers)
    assert fail_res.status_code == 404

    # Cleanup backup file created
    target_file = BACKUP_DIR / filename
    if target_file.exists():
        os.remove(target_file)

def test_custom_exception_envelopes():
    # Test 404 Patient Not Found envelope
    res_404 = client.get("/patient/NON_EXISTENT_ID")
    assert res_404.status_code == 404
    data_404 = res_404.json()
    assert data_404["detail"] == "Patient not found"
    assert data_404["error_code"] == "PATIENT_NOT_FOUND"
    assert "timestamp" in data_404

    # Test 400 Invalid Query Parameter envelope
    res_400 = client.get("/sort?sort_by=invalid_col&order=asc")
    assert res_400.status_code == 400
    data_400 = res_400.json()
    assert "Invalid Field" in data_400["detail"]
    assert data_400["error_code"] == "INVALID_QUERY_PARAMETER"
    assert "timestamp" in data_400

def test_search_patients_with_combined_filters():
    response = client.get("/patients/search?gender=female&min_age=20&max_age=50")
    assert response.status_code == 200
    data = response.json()
    assert "patients" in data
    for p in data["patients"]:
        assert p["gender"] == "female"
        assert 20 <= p["age"] <= 50

def test_search_patients_no_results():
    response = client.get("/patients/search?city=AtlantisUnderwater")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["patients"]) == 0

def test_batch_create_empty_list():
    res = client.post("/batch-create", json=[])
    assert res.status_code == 400
    assert "cannot be empty" in res.json()["detail"]

def test_batch_create_intra_batch_duplicates():
    dup_batch = [
        {
            "id": "DUP_ID_01",
            "name": "Person One",
            "city": "Delhi",
            "age": 25,
            "gender": "male",
            "height": 1.70,
            "weight": 65.0
        },
        {
            "id": "DUP_ID_01",
            "name": "Person Two",
            "city": "Mumbai",
            "age": 30,
            "gender": "female",
            "height": 1.65,
            "weight": 55.0
        }
    ]
    res = client.post("/batch-create", json=dup_batch)
    assert res.status_code == 400
    assert "Duplicate patient IDs" in res.json()["detail"]

def test_batch_create_existing_conflict():
    conflict_batch = [
        {
            "id": "P001",
            "name": "Conflicting Record",
            "city": "Kolkata",
            "age": 40,
            "gender": "male",
            "height": 1.80,
            "weight": 80.0
        }
    ]
    res = client.post("/batch-create", json=conflict_batch)
    assert res.status_code == 400
    assert "already exist" in res.json()["detail"]

def test_edit_patient_not_found():
    res = client.put("/edit/NON_EXISTENT_PATIENT_999", json={"age": 45})
    assert res.status_code == 404
    assert res.json()["error_code"] == "PATIENT_NOT_FOUND"

def test_delete_patient_not_found():
    res = client.delete("/delete/NON_EXISTENT_PATIENT_999")
    assert res.status_code == 404
    assert res.json()["error_code"] == "PATIENT_NOT_FOUND"







