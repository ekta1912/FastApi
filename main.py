from fastapi import FastAPI, Path, HTTPException, Query, status
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional, Dict, List
from pathlib import Path as FilePath
import json

tags_metadata = [
    {
        "name": "General",
        "description": "General system information, health checks, and landing endpoints.",
    },
    {
        "name": "Patients",
        "description": "Comprehensive CRUD and query operations for patient records.",
    },
    {
        "name": "Analytics",
        "description": "Statistical aggregation and population health analysis.",
    },
]

app = FastAPI(
    title="Patient Management System API",
    description="A high-performance RESTful API built with FastAPI and Pydantic for managing patient records, calculating real-time BMI metrics, and evaluating health statuses.",
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Ekta Singh",
        "email": "ektasingh19.12.2004@gmail.com",
    },
)

DATA_FILE = FilePath(__file__).resolve().parent / "patient.json"

class MessageResponse(BaseModel):
    message: str = Field(..., description="Status or information message")

class BatchCreateResponse(BaseModel):
    message: str = Field(..., description="Status message")
    inserted_count: int = Field(..., description="Total records created in this batch")
    inserted_ids: List[str] = Field(..., description="List of IDs successfully registered")

class HealthResponse(BaseModel):
    status: str = Field(..., description="API operational health status")
    total_records: int = Field(..., description="Total patient records loaded in storage")
    storage_active: bool = Field(..., description="Storage file accessibility status")

class AnalyticsSummaryResponse(BaseModel):
    total_patients: int = Field(..., description="Total number of registered patients")
    average_age: float = Field(..., description="Average age of patients")
    average_bmi: float = Field(..., description="Average BMI across patients")
    average_weight: float = Field(..., description="Average weight in kilograms")
    average_height: float = Field(..., description="Average height in meters")
    gender_distribution: Dict[str, int] = Field(..., description="Breakdown of patients by gender")
    verdict_distribution: Dict[str, int] = Field(..., description="Breakdown of patients by BMI health verdict")

class PatientBase(BaseModel):
    name: str = Field(..., description="Full name of the patient", examples=["Aman Gupta"])
    city: str = Field(..., description="City of residence", examples=["Jaipur"])
    age: Annotated[int, Field(..., gt=0, lt=120, description='Age of the patient in years', examples=[38])]
    gender: Annotated[Literal['male', 'female', 'others'], Field(..., description='Gender of the patient')]
    height: Annotated[float, Field(..., gt=0, description='Height of the patient in meters', examples=[1.78])]
    weight: Annotated[float, Field(..., gt=0, description='Weight of the patient in kilograms', examples=[78.0])]

class Patient(PatientBase):
    id: Annotated[str, Field(..., description='ID of the patient', examples=['P001'])]

    @computed_field
    @property
    def bmi(self) -> float:
        """Calculate Body Mass Index (BMI): weight / (height ** 2)"""
        return round(self.weight / (self.height ** 2), 2)

    @computed_field
    @property
    def verdict(self) -> str:
        """Determine health category based on WHO BMI classifications."""
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25.0:
            return "Normal"
        elif self.bmi < 30.0:
            return "Overweight"
        else:
            return "Obese"

class PatientResponse(PatientBase):
    bmi: float = Field(..., description="Calculated Body Mass Index")
    verdict: str = Field(..., description="Health classification verdict")

class PatientRecord(PatientResponse):
    id: str = Field(..., description="Unique patient identifier")

class PaginatedPatientsResponse(BaseModel):
    total: int = Field(..., description="Total matching patients found")
    limit: int = Field(..., description="Number of items returned")
    offset: int = Field(..., description="Number of items skipped")
    patients: List[PatientRecord] = Field(..., description="List of matching patient records")

class PatientUpdate(BaseModel):  
    name: Annotated[Optional[str], Field(default=None, description="Updated patient name")]
    city: Annotated[Optional[str], Field(default=None, description="Updated patient city")]
    age: Annotated[Optional[int], Field(default=None, gt=0, lt=120, description="Updated patient age")]
    gender: Annotated[Optional[Literal['male', 'female', 'others']], Field(default=None, description="Updated patient gender")]
    height: Annotated[Optional[float], Field(default=None, gt=0, description="Updated patient height in meters")]
    weight: Annotated[Optional[float], Field(default=None, gt=0, description="Updated patient weight in kg")]      

def load_data() -> dict:
    """Safely load patient records from local JSON storage."""
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data: dict) -> None:
    """Safely persist patient records to local JSON storage."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

@app.get("/", response_model=MessageResponse, tags=["General"], summary="Welcome Endpoint")
def hello():
    """Returns a welcome message indicating the status of the API."""
    return {"message": "Patient management system API"}

@app.get("/health", response_model=HealthResponse, tags=["General"], summary="Health Check")
def health_check():
    """Returns system status, file storage connectivity, and total active records."""
    data = load_data()
    return HealthResponse(
        status="healthy",
        total_records=len(data),
        storage_active=DATA_FILE.exists()
    )

@app.get('/about', response_model=MessageResponse, tags=["General"], summary="API Overview")
def about():
    """Provides high-level information about the API and its capabilities."""
    return {"message": "Fully functional api to manage records"}

@app.get('/view', response_model=Dict[str, PatientResponse], tags=["Patients"], summary="Get All Patients")
def view():
    """Retrieve all patient records currently saved in the database."""
    return load_data()

@app.get('/patient/{patient_id}', response_model=PatientResponse, tags=["Patients"], summary="Get Patient by ID")
def view_patient(patient_id: str = Path(..., description='Unique ID of the patient', examples=['P001'])):
    """Retrieve complete profile and health metrics of a specific patient."""
    data = load_data()
    if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

@app.get('/sort', response_model=List[PatientResponse], tags=["Patients"], summary="Sort Patients by Metric")
def sort_patients(
    sort_by: str = Query(..., description="Attribute to sort by: height, weight, or bmi"),
    order: str = Query('asc', description='Sorting order: asc (ascending) or desc (descending)')
):
    """Sort patients dynamically based on height, weight, or calculated BMI."""
    valid_fields = ['height', 'weight', 'bmi']

    if sort_by not in valid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid Field select from {valid_fields}'
        )

    if order not in ['asc', 'desc']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid order select between asc and desc'
        )

    data = load_data()
    sort_order = True if order == 'desc' else False

    sorted_data = sorted(
        data.values(),
        key=lambda x: x.get(sort_by, 0),
        reverse=sort_order
    )

    return sorted_data

@app.get('/patients/search', response_model=PaginatedPatientsResponse, tags=["Patients"], summary="Search & Filter Patients")
def search_patients(
    city: Optional[str] = Query(None, description="Filter by city name (case-insensitive)"),
    gender: Optional[Literal['male', 'female', 'others']] = Query(None, description="Filter by patient gender"),
    min_age: Optional[int] = Query(None, ge=1, le=120, description="Minimum age filter"),
    max_age: Optional[int] = Query(None, ge=1, le=120, description="Maximum age filter"),
    verdict: Optional[str] = Query(None, description="Filter by verdict (e.g. Normal, Obese, Underweight, Overweight)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Search and filter patient records by multiple parameters with pagination support."""
    data = load_data()
    filtered: List[PatientRecord] = []

    for pid, pdata in data.items():
        if city and pdata.get("city", "").lower() != city.lower():
            continue
        if gender and pdata.get("gender") != gender:
            continue
        if min_age and pdata.get("age", 0) < min_age:
            continue
        if max_age and pdata.get("age", 0) > max_age:
            continue
        if verdict and pdata.get("verdict", "").lower() != verdict.lower():
            continue

        record_data = {**pdata, "id": pid}
        filtered.append(PatientRecord(**record_data))

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return PaginatedPatientsResponse(
        total=total,
        limit=limit,
        offset=offset,
        patients=paginated
    )

@app.get('/analytics/summary', response_model=AnalyticsSummaryResponse, tags=["Analytics"], summary="Population Health Summary")
def get_analytics_summary():
    """Calculate aggregate population health statistics, averages, and distributions across all registered patients."""
    data = load_data()
    total = len(data)
    if total == 0:
        return AnalyticsSummaryResponse(
            total_patients=0,
            average_age=0.0,
            average_bmi=0.0,
            average_weight=0.0,
            average_height=0.0,
            gender_distribution={},
            verdict_distribution={}
        )

    patients = list(data.values())
    total_age = sum(p.get("age", 0) for p in patients)
    total_bmi = sum(p.get("bmi", 0.0) for p in patients)
    total_weight = sum(p.get("weight", 0.0) for p in patients)
    total_height = sum(p.get("height", 0.0) for p in patients)

    gender_dist: Dict[str, int] = {}
    verdict_dist: Dict[str, int] = {}

    for p in patients:
        gender = p.get("gender", "unknown")
        gender_dist[gender] = gender_dist.get(gender, 0) + 1

        verdict = p.get("verdict", "unknown")
        verdict_dist[verdict] = verdict_dist.get(verdict, 0) + 1

    return AnalyticsSummaryResponse(
        total_patients=total,
        average_age=round(total_age / total, 2),
        average_bmi=round(total_bmi / total, 2),
        average_weight=round(total_weight / total, 2),
        average_height=round(total_height / total, 2),
        gender_distribution=gender_dist,
        verdict_distribution=verdict_dist
    )

@app.post('/create', response_model=MessageResponse, status_code=status.HTTP_201_CREATED, tags=["Patients"], summary="Create New Patient")
def create_patient(patient: Patient):
    """Register a new patient, calculate initial BMI and verdict, and store in the database."""
    data = load_data()
    if patient.id in data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Patient already exists')

    data[patient.id] = patient.model_dump(exclude={'id'})
    save_data(data)

    return {"message": "patient created successfully"}

@app.post('/batch-create', response_model=BatchCreateResponse, status_code=status.HTTP_201_CREATED, tags=["Patients"], summary="Batch Create Patients")
def batch_create_patients(patients: List[Patient]):
    """Register multiple patients in an atomic batch. If any patient ID is duplicate or invalid, the entire operation is rejected."""
    if not patients:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient list cannot be empty")

    data = load_data()

    # Validate for intra-batch duplicate IDs
    batch_ids = [p.id for p in patients]
    if len(batch_ids) != len(set(batch_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate patient IDs found within the provided batch"
        )

    # Validate against existing IDs in storage
    conflicts = [pid for pid in batch_ids if pid in data]
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient IDs already exist: {', '.join(conflicts)}"
        )

    # Perform atomic insertion
    for patient in patients:
        data[patient.id] = patient.model_dump(exclude={'id'})

    save_data(data)

    return BatchCreateResponse(
        message="Batch patients created successfully",
        inserted_count=len(patients),
        inserted_ids=batch_ids
    )

@app.put('/edit/{patient_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK, tags=["Patients"], summary="Update Patient Details")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    """Partially update an existing patient's details and automatically recalculate BMI and verdict."""
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    existing_patient_info = data[patient_id]
    updated_patient_info = patient_update.model_dump(exclude_unset=True)

    for key, value in updated_patient_info.items():
        existing_patient_info[key] = value

    existing_patient_info['id'] = patient_id
    patient_pydantic_obj = Patient(**existing_patient_info)

    existing_patient_info = patient_pydantic_obj.model_dump(exclude={'id'})
    data[patient_id] = existing_patient_info
    save_data(data)

    return {"message": "patient updated"}

@app.delete('/delete/{patient_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK, tags=["Patients"], summary="Delete Patient Record")
def delete_patient(patient_id: str):
    """Delete a patient record by ID from the database."""
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Patient not found')

    del data[patient_id]
    save_data(data)
    return {"message": "patient deleted"}
