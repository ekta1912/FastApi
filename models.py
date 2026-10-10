"""Pydantic data models and schemas for Patient Management System."""

from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional, Dict, List
from datetime import datetime

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

class IntegrityIssue(BaseModel):
    patient_id: str = Field(..., description="Affected patient ID")
    field: str = Field(..., description="Field failing validation")
    issue: str = Field(..., description="Description of the discrepancy")

class DatabaseIntegrityResponse(BaseModel):
    is_healthy: bool = Field(..., description="True if database has zero validation issues")
    total_checked: int = Field(..., description="Total patient profiles audited")
    issues_found: int = Field(..., description="Number of discrepancies discovered")
    issues: List[IntegrityIssue] = Field(..., description="List of specific integrity issues")
    checked_at: str = Field(..., description="Audit execution timestamp")

class CompactionResponse(BaseModel):
    message: str = Field(..., description="Operation status")
    records_compacted: int = Field(..., description="Number of sorted and validated records")
    bytes_before: int = Field(..., description="File size before compaction in bytes")
    bytes_after: int = Field(..., description="File size after compaction in bytes")
    compacted_at: str = Field(..., description="Compaction execution timestamp")

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
