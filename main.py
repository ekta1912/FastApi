from fastapi import FastAPI, Path, HTTPException, Query, status, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional, Dict, List
from pathlib import Path as FilePath
import json
import time
import csv
import io
import uuid
import logging
from datetime import datetime

from config import get_settings
from exceptions import PatientNotFoundError, PatientAlreadyExistsError, InvalidQueryParameterError, AuthenticationError
from security import verify_admin_key

settings = get_settings()

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
    {
        "name": "Admin",
        "description": "Administrative maintenance, data snapshotting, and restoration operations.",
    },
]

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    openapi_tags=tags_metadata,
    contact={
        "name": settings.contact_name,
        "email": settings.contact_email,
    },
)

logger = logging.getLogger("patient_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
)

@app.middleware("http")
async def request_trace_and_timing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.6f}"
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"request_id={request_id} method={request.method} path={request.url.path} "
        f"status={response.status_code} latency={process_time:.6f}s"
    )
    return response

@app.exception_handler(PatientNotFoundError)
async def patient_not_found_handler(request: Request, exc: PatientNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(PatientAlreadyExistsError)
async def patient_already_exists_handler(request: Request, exc: PatientAlreadyExistsError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(InvalidQueryParameterError)
async def invalid_query_parameter_handler(request: Request, exc: InvalidQueryParameterError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now().isoformat()
        }
    )



DATA_FILE = settings.data_file_path
BACKUP_DIR = DATA_FILE.parent / "backups"

class BackupInfo(BaseModel):
    filename: str = Field(..., description="Backup filename")
    created_at: str = Field(..., description="ISO 8601 timestamp of creation")
    record_count: int = Field(..., description="Total patient records in the backup")
    file_size_bytes: int = Field(..., description="Backup file size in bytes")

class BackupResponse(BaseModel):
    message: str = Field(..., description="Operation status")
    backup: BackupInfo = Field(..., description="Metadata of the created backup")

class BackupListResponse(BaseModel):
    total_backups: int = Field(..., description="Count of stored backups")
    backups: List[BackupInfo] = Field(..., description="Available database backups")

class RestoreRequest(BaseModel):
    filename: str = Field(..., description="Name of the backup file to restore from")

class RestoreResponse(BaseModel):
    message: str = Field(..., description="Status message")
    restored_records: int = Field(..., description="Count of restored patient records")

class MessageResponse(BaseModel):
    message: str = Field(..., description="Status or information message")


class BatchCreateResponse(BaseModel):
    message: str = Field(..., description="Status message")
    inserted_count: int = Field(..., description="Total records created in this batch")
    inserted_ids: List[str] = Field(..., description="List of IDs successfully registered")

class HealthResponse(BaseModel):
    status: str = Field(..., description="API operational health status")
    environment: str = Field(..., description="Application execution environment")
    version: str = Field(..., description="API semantic version")
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
    blood_group: Annotated[Optional[Literal['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']], Field(default=None, description='ABO/Rh blood group type', examples=['O+'])] = None
    allergies: List[str] = Field(default_factory=list, description='Known medical or dietary allergies', examples=[['Penicillin']])
    chronic_conditions: List[str] = Field(default_factory=list, description='Documented chronic health conditions', examples=[['Hypertension']])
    vitals_history: List[dict] = Field(default_factory=list, description='Historical clinical vitals records')

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

class PatientRiskProfile(BaseModel):
    id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Patient name")
    age: int = Field(..., description="Patient age")
    bmi: float = Field(..., description="Calculated Body Mass Index")
    verdict: str = Field(..., description="Health classification")
    risk_level: Literal["Low", "Moderate", "High", "Critical"] = Field(..., description="Stratified health risk level")
    risk_factors: List[str] = Field(..., description="Identified risk factors contributing to the score")

class RiskAssessmentResponse(BaseModel):
    total_assessed: int = Field(..., description="Total patients assessed")
    risk_breakdown: Dict[str, int] = Field(..., description="Count of patients per risk tier")
    high_risk_percentage: float = Field(..., description="Percentage of patients in High or Critical tier")
    patients: List[PatientRiskProfile] = Field(..., description="List of individual patient risk assessments")


class PatientUpdate(BaseModel):  
    name: Annotated[Optional[str], Field(default=None, description="Updated patient name")]
    city: Annotated[Optional[str], Field(default=None, description="Updated patient city")]
    age: Annotated[Optional[int], Field(default=None, gt=0, lt=120, description="Updated patient age")]
    gender: Annotated[Optional[Literal['male', 'female', 'others']], Field(default=None, description="Updated patient gender")]
    height: Annotated[Optional[float], Field(default=None, gt=0, description="Updated patient height in meters")]
    weight: Annotated[Optional[float], Field(default=None, gt=0, description="Updated patient weight in kg")]
    blood_group: Annotated[Optional[Literal['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']], Field(default=None, description="Updated blood group")] = None
    allergies: Optional[List[str]] = Field(default=None, description="Updated list of allergies")
    chronic_conditions: Optional[List[str]] = Field(default=None, description="Updated chronic conditions")

class VitalsEntry(BaseModel):
    systolic: Annotated[int, Field(..., ge=60, le=250, description="Systolic blood pressure in mmHg", examples=[120])]
    diastolic: Annotated[int, Field(..., ge=40, le=150, description="Diastolic blood pressure in mmHg", examples=[80])]
    heart_rate: Annotated[int, Field(..., ge=40, le=220, description="Resting heart rate in beats per minute", examples=[72])]
    temperature_celsius: Annotated[Optional[float], Field(default=None, ge=30.0, le=45.0, description="Body temperature in Celsius", examples=[37.0])] = None
    spo2_percentage: Annotated[Optional[int], Field(default=None, ge=50, le=100, description="Blood oxygen saturation percentage", examples=[98])] = None
    recorded_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Measurement timestamp")

    @computed_field
    @property
    def bp_category(self) -> str:
        """Categorize blood pressure status according to clinical criteria."""
        if self.systolic > 180 or self.diastolic > 120:
            return "Hypertensive Crisis"
        elif self.systolic >= 140 or self.diastolic >= 90:
            return "Hypertension Stage 2"
        elif self.systolic >= 130 or self.diastolic >= 80:
            return "Hypertension Stage 1"
        elif self.systolic >= 120 and self.diastolic < 80:
            return "Elevated"
        else:
            return "Normal"

class VitalsResponse(BaseModel):
    message: str = Field(..., description="Operation status")
    patient_id: str = Field(..., description="Target patient ID")
    vitals: VitalsEntry = Field(..., description="Recorded vitals details")

class PatientVitalsHistoryResponse(BaseModel):
    patient_id: str = Field(..., description="Patient identifier")
    total_records: int = Field(..., description="Total vital checks recorded")
    vitals_history: List[VitalsEntry] = Field(..., description="Chronological vitals history")

class JsonExportMetadata(BaseModel):
    exported_at: str = Field(..., description="Timestamp of export generation")
    total_records: int = Field(..., description="Total patients included in export")
    version: str = Field(..., description="API software version at export")

class PatientExportResponse(BaseModel):
    metadata: JsonExportMetadata = Field(..., description="Export metadata")
    patients: Dict[str, PatientResponse] = Field(..., description="Dictionary of exported patient profiles")

class PatientImportRequest(BaseModel):
    strategy: Literal["skip", "overwrite", "fail"] = Field(default="skip", description="Collision resolution strategy for existing records")
    patients: List[Patient] = Field(..., description="List of patient profiles to import")

class PatientImportResponse(BaseModel):
    message: str = Field(..., description="Summary status of import operation")
    imported_count: int = Field(..., description="Count of newly created records")
    skipped_count: int = Field(..., description="Count of records ignored due to collisions")
    overwritten_count: int = Field(..., description="Count of pre-existing records updated")
    processed_ids: List[str] = Field(..., description="List of all patient IDs handled")

class CityHealthMetric(BaseModel):
    city: str = Field(..., description="City name")
    patient_count: int = Field(..., description="Total patients in this city")
    average_bmi: float = Field(..., description="Average BMI of patients in city")
    average_age: float = Field(..., description="Average age of patients in city")

class DemographicsAnalyticsResponse(BaseModel):
    total_evaluated: int = Field(..., description="Total patient profiles evaluated")
    age_brackets: Dict[str, int] = Field(..., description="Patient breakdown by demographic age groups")
    blood_group_distribution: Dict[str, int] = Field(..., description="Breakdown by ABO/Rh blood groups")
    allergy_frequency: Dict[str, int] = Field(..., description="Occurrence frequency of documented allergies")
    top_cities: List[CityHealthMetric] = Field(..., description="Aggregated health metrics grouped by city")


      

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
        environment=settings.environment,
        version=settings.app_version,
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
    raise PatientNotFoundError("Patient not found")

@app.post('/patient/{patient_id}/vitals', response_model=VitalsResponse, status_code=status.HTTP_201_CREATED, tags=["Patients"], summary="Record Patient Vitals")
def record_patient_vitals(
    patient_id: str = Path(..., description='Unique ID of the patient', examples=['P001']),
    vitals: VitalsEntry = ...
):
    """Log vital signs including blood pressure, heart rate, temperature, and SpO2 for a patient."""
    data = load_data()
    if patient_id not in data:
        raise PatientNotFoundError("Patient not found")

    vitals_data = vitals.model_dump()
    data[patient_id].setdefault("vitals_history", []).append(vitals_data)
    save_data(data)

    return VitalsResponse(
        message="Vitals recorded successfully",
        patient_id=patient_id,
        vitals=vitals
    )

@app.get('/patient/{patient_id}/vitals', response_model=PatientVitalsHistoryResponse, tags=["Patients"], summary="Get Patient Vitals History")
def get_patient_vitals(patient_id: str = Path(..., description='Unique ID of the patient', examples=['P001'])):
    """Retrieve full chronological history of recorded vital signs and blood pressure classifications."""
    data = load_data()
    if patient_id not in data:
        raise PatientNotFoundError("Patient not found")

    history = data[patient_id].get("vitals_history", [])
    parsed_history = [VitalsEntry(**v) for v in history]

    return PatientVitalsHistoryResponse(
        patient_id=patient_id,
        total_records=len(parsed_history),
        vitals_history=parsed_history
    )


@app.get('/sort', response_model=List[PatientResponse], tags=["Patients"], summary="Sort Patients by Metric")
def sort_patients(
    sort_by: str = Query(..., description="Attribute to sort by: height, weight, or bmi"),
    order: str = Query('asc', description='Sorting order: asc (ascending) or desc (descending)')
):
    """Sort patients dynamically based on height, weight, or calculated BMI."""
    valid_fields = ['height', 'weight', 'bmi']

    if sort_by not in valid_fields:
        raise InvalidQueryParameterError(f'Invalid Field select from {valid_fields}')

    if order not in ['asc', 'desc']:
        raise InvalidQueryParameterError('Invalid order select between asc and desc')


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

@app.get(
    '/patients/export/csv',
    tags=["Patients"],
    summary="Export Patients as CSV",
    response_description="A downloadable CSV file containing all registered patient records and computed metrics."
)
def export_patients_csv():
    """Stream and export all patient records in standard CSV format with BMI and health verdicts."""
    data = load_data()
    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV headers
    headers = ["id", "name", "city", "age", "gender", "height", "weight", "bmi", "verdict", "blood_group", "allergies", "chronic_conditions"]
    writer.writerow(headers)

    # Write patient rows
    for pid, pdata in data.items():
        allergies = pdata.get("allergies", [])
        allergies_str = "; ".join(allergies) if isinstance(allergies, list) else str(allergies or "")
        conditions = pdata.get("chronic_conditions", [])
        conditions_str = "; ".join(conditions) if isinstance(conditions, list) else str(conditions or "")
        writer.writerow([
            pid,
            pdata.get("name", ""),
            pdata.get("city", ""),
            pdata.get("age", ""),
            pdata.get("gender", ""),
            pdata.get("height", ""),
            pdata.get("weight", ""),
            pdata.get("bmi", ""),
            pdata.get("verdict", ""),
            pdata.get("blood_group", ""),
            allergies_str,
            conditions_str
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="patients_export.csv"'}
    )

@app.get('/patients/export/json', response_model=PatientExportResponse, tags=["Patients"], summary="Export Patients as JSON")
def export_patients_json():
    """Export complete patient database as a structured JSON object with system metadata."""
    data = load_data()
    metadata = JsonExportMetadata(
        exported_at=datetime.now().isoformat(),
        total_records=len(data),
        version=settings.app_version
    )
    return PatientExportResponse(
        metadata=metadata,
        patients=data
    )

@app.post('/patients/import/json', response_model=PatientImportResponse, status_code=status.HTTP_200_OK, tags=["Patients"], summary="Bulk Import Patients via JSON")
def import_patients_json(request: PatientImportRequest):
    """Import an array of patient records with collision resolution ('skip', 'overwrite', or 'fail')."""
    if not request.patients:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient list cannot be empty")

    data = load_data()
    imported_count = 0
    skipped_count = 0
    overwritten_count = 0
    processed_ids = []

    # Check for fail strategy upfront
    if request.strategy == "fail":
        conflicts = [p.id for p in request.patients if p.id in data]
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Conflict detected on existing patient IDs: {', '.join(conflicts)}"
            )

    for p in request.patients:
        processed_ids.append(p.id)
        if p.id in data:
            if request.strategy == "skip":
                skipped_count += 1
                continue
            elif request.strategy == "overwrite":
                data[p.id] = p.model_dump(exclude={'id'})
                overwritten_count += 1
        else:
            data[p.id] = p.model_dump(exclude={'id'})
            imported_count += 1

    save_data(data)

    return PatientImportResponse(
        message=f"Import completed: {imported_count} added, {overwritten_count} overwritten, {skipped_count} skipped",
        imported_count=imported_count,
        skipped_count=skipped_count,
        overwritten_count=overwritten_count,
        processed_ids=processed_ids
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

def evaluate_patient_risk(pid: str, pdata: dict) -> PatientRiskProfile:
    """Evaluate clinical risk level and risk factors based on age and BMI."""
    age = pdata.get("age", 0)
    bmi = pdata.get("bmi", 0.0)
    verdict = pdata.get("verdict", "")
    factors = []
    score = 0

    if bmi >= 35.0:
        factors.append("Severe Obesity (BMI >= 35)")
        score += 3
    elif bmi >= 30.0:
        factors.append("Obesity (BMI >= 30)")
        score += 2
    elif bmi < 18.5 and bmi > 0:
        factors.append("Underweight Malnutrition Risk (BMI < 18.5)")
        score += 1

    if age >= 65:
        factors.append("Geriatric Vulnerability (Age >= 65)")
        score += 2
    elif age >= 50:
        factors.append("Elevated Age Factor (Age >= 50)")
        score += 1

    if score >= 4:
        risk_level = "Critical"
    elif score >= 2:
        risk_level = "High"
    elif score == 1:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    return PatientRiskProfile(
        id=pid,
        name=pdata.get("name", "Unknown"),
        age=age,
        bmi=bmi,
        verdict=verdict,
        risk_level=risk_level,
        risk_factors=factors
    )

@app.get('/analytics/risk-assessment', response_model=RiskAssessmentResponse, tags=["Analytics"], summary="Clinical Health Risk Assessment")
def get_risk_assessment():
    """Calculate clinical risk tier stratification and factor analysis across all registered patients."""
    data = load_data()
    total = len(data)
    if total == 0:
        return RiskAssessmentResponse(
            total_assessed=0,
            risk_breakdown={"Low": 0, "Moderate": 0, "High": 0, "Critical": 0},
            high_risk_percentage=0.0,
            patients=[]
        )

    breakdown = {"Low": 0, "Moderate": 0, "High": 0, "Critical": 0}
    assessed_patients: List[PatientRiskProfile] = []

    for pid, pdata in data.items():
        profile = evaluate_patient_risk(pid, pdata)
        assessed_patients.append(profile)
        breakdown[profile.risk_level] = breakdown.get(profile.risk_level, 0) + 1

    high_risk_count = breakdown.get("High", 0) + breakdown.get("Critical", 0)
    high_risk_percentage = round((high_risk_count / total) * 100, 2)

    return RiskAssessmentResponse(
        total_assessed=total,
        risk_breakdown=breakdown,
        high_risk_percentage=high_risk_percentage,
        patients=assessed_patients
    )

@app.get('/analytics/demographics', response_model=DemographicsAnalyticsResponse, tags=["Analytics"], summary="Demographics & Regional Analysis")
def get_demographics_analytics():
    """Analyze population age brackets, blood type distribution, allergy frequencies, and regional city metrics."""
    data = load_data()
    total = len(data)
    if total == 0:
        return DemographicsAnalyticsResponse(
            total_evaluated=0,
            age_brackets={"Pediatric (0-17)": 0, "Young Adult (18-35)": 0, "Middle Aged (36-55)": 0, "Senior (56+)": 0},
            blood_group_distribution={},
            allergy_frequency={},
            top_cities=[]
        )

    brackets = {"Pediatric (0-17)": 0, "Young Adult (18-35)": 0, "Middle Aged (36-55)": 0, "Senior (56+)": 0}
    blood_groups: Dict[str, int] = {}
    allergies: Dict[str, int] = {}
    city_data: Dict[str, List[dict]] = {}

    for p in data.values():
        age = p.get("age", 0)
        if age <= 17:
            brackets["Pediatric (0-17)"] += 1
        elif age <= 35:
            brackets["Young Adult (18-35)"] += 1
        elif age <= 55:
            brackets["Middle Aged (36-55)"] += 1
        else:
            brackets["Senior (56+)"] += 1

        bg = p.get("blood_group") or "Unspecified"
        blood_groups[bg] = blood_groups.get(bg, 0) + 1

        for allergy in p.get("allergies", []):
            cleaned_allergy = allergy.strip().title()
            allergies[cleaned_allergy] = allergies.get(cleaned_allergy, 0) + 1

        city_name = p.get("city", "Unknown").strip().title()
        city_data.setdefault(city_name, []).append(p)

    cities_summary = []
    for city, plist in city_data.items():
        count = len(plist)
        avg_bmi = round(sum(p.get("bmi", 0.0) for p in plist) / count, 2)
        avg_age = round(sum(p.get("age", 0) for p in plist) / count, 2)
        cities_summary.append(CityHealthMetric(
            city=city,
            patient_count=count,
            average_bmi=avg_bmi,
            average_age=avg_age
        ))

    cities_summary.sort(key=lambda x: x.patient_count, reverse=True)

    return DemographicsAnalyticsResponse(
        total_evaluated=total,
        age_brackets=brackets,
        blood_group_distribution=blood_groups,
        allergy_frequency=allergies,
        top_cities=cities_summary
    )

@app.get('/patients/high-risk', response_model=List[PatientRiskProfile], tags=["Patients"], summary="Get High-Risk Patients")
def get_high_risk_patients():
    """Retrieve all patients classified in High or Critical health risk categories for prioritized medical attention."""
    data = load_data()
    high_risk: List[PatientRiskProfile] = []
    for pid, pdata in data.items():
        profile = evaluate_patient_risk(pid, pdata)
        if profile.risk_level in ["High", "Critical"]:
            high_risk.append(profile)
    return high_risk

@app.post('/create', response_model=MessageResponse, status_code=status.HTTP_201_CREATED, tags=["Patients"], summary="Create New Patient")
def create_patient(patient: Patient):
    """Register a new patient, calculate initial BMI and verdict, and store in the database."""
    data = load_data()
    if patient.id in data:
        raise PatientAlreadyExistsError('Patient already exists')

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
        raise PatientNotFoundError("Patient not found")

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
        raise PatientNotFoundError('Patient not found')

    del data[patient_id]
    save_data(data)
    return {"message": "patient deleted"}


@app.post('/admin/backup', response_model=BackupResponse, status_code=status.HTTP_201_CREATED, tags=["Admin"], summary="Create Database Backup", dependencies=[Security(verify_admin_key)])
def create_backup():
    """Create a point-in-time timestamped JSON snapshot of all patient records."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{now_str}.json"
    backup_path = BACKUP_DIR / backup_filename

    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

    stat = backup_path.stat()
    backup_info = BackupInfo(
        filename=backup_filename,
        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
        record_count=len(data),
        file_size_bytes=stat.st_size
    )

    return BackupResponse(
        message="Database backup created successfully",
        backup=backup_info
    )

@app.get('/admin/backups', response_model=BackupListResponse, tags=["Admin"], summary="List Available Backups", dependencies=[Security(verify_admin_key)])
def list_backups():
    """List all available historical backup snapshots in storage."""
    if not BACKUP_DIR.exists():
        return BackupListResponse(total_backups=0, backups=[])

    backups = []
    for file in sorted(BACKUP_DIR.glob("backup_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                count = len(content) if isinstance(content, dict) else 0
        except Exception:
            count = 0
        stat = file.stat()
        backups.append(BackupInfo(
            filename=file.name,
            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            record_count=count,
            file_size_bytes=stat.st_size
        ))

    return BackupListResponse(
        total_backups=len(backups),
        backups=backups
    )

@app.post('/admin/restore', response_model=RestoreResponse, tags=["Admin"], summary="Restore Database from Backup", dependencies=[Security(verify_admin_key)])
def restore_backup(request: RestoreRequest):
    """Restore database state from a specified valid backup snapshot."""
    import os
    safe_filename = os.path.basename(request.filename)
    backup_path = (BACKUP_DIR / safe_filename).resolve()

    if not backup_path.is_relative_to(BACKUP_DIR.resolve()) or not backup_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Backup file '{safe_filename}' not found")

    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Corrupt backup file: {str(e)}")

    if not isinstance(backup_data, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup file structure: expected dict")

    save_data(backup_data)
    return RestoreResponse(
        message=f"Database successfully restored from '{safe_filename}'",
        restored_records=len(backup_data)
    )

