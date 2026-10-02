from fastapi import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional
from pathlib import Path
import json

tags_metadata = [
    {
        "name": "General",
        "description": "General system information and landing endpoints.",
    },
    {
        "name": "Patients",
        "description": "Comprehensive CRUD and query operations for patient records.",
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

DATA_FILE = Path(__file__).resolve().parent / "patient.json"

class Patient(BaseModel):
    id: Annotated[str, Field(..., description='ID of the patient', examples=['P001'])]
    name: str = Field(..., description="Full name of the patient", examples=["Aman Gupta"])
    city: str = Field(..., description="City of residence", examples=["Jaipur"])
    age: Annotated[int, Field(..., gt=0, lt=120, description='Age of the patient in years', examples=[38])]
    gender: Annotated[Literal['male', 'female', 'others'], Field(..., description='Gender of the patient')]
    height: Annotated[float, Field(..., gt=0, description='Height of the patient in meters', examples=[1.78])]
    weight: Annotated[float, Field(..., gt=0, description='Weight of the patient in kilograms', examples=[78.0])]

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

@app.get("/", tags=["General"], summary="Welcome Endpoint")
def hello():
    """Returns a welcome message indicating the status of the API."""
    return {"message": "Patient management system API"}

@app.get('/about', tags=["General"], summary="API Overview")
def about():
    """Provides high-level information about the API and its capabilities."""
    return {"message": "Fully functional api to manage records"}

@app.get('/view', tags=["Patients"], summary="Get All Patients")
def view():
    """Retrieve all patient records currently saved in the database."""
    return load_data()

@app.get('/patient/{patient_id}', tags=["Patients"], summary="Get Patient by ID")
def view_patient(patient_id: str = Path(..., description='Unique ID of the patient', example='P001')):
    """Retrieve complete profile and health metrics of a specific patient."""
    data = load_data()
    if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get('/sort', tags=["Patients"], summary="Sort Patients by Metric")
def sort_patients(
    sort_by: str = Query(..., description="Attribute to sort by: height, weight, or bmi"),
    order: str = Query('asc', description='Sorting order: asc (ascending) or desc (descending)')
):
    """Sort patients dynamically based on height, weight, or calculated BMI."""
    valid_fields = ['height', 'weight', 'bmi']

    if sort_by not in valid_fields:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid Field select from {valid_fields}'
        )

    if order not in ['asc', 'desc']:
        raise HTTPException(
            status_code=400,
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

@app.post('/create', tags=["Patients"], summary="Create New Patient")
def create_patient(patient: Patient):
    """Register a new patient, calculate initial BMI and verdict, and store in the database."""
    data = load_data()
    if patient.id in data:
        raise HTTPException(status_code=400, detail='Patient already exists')

    data[patient.id] = patient.model_dump(exclude={'id'})
    save_data(data)

    return JSONResponse(status_code=201, content={'message': 'patient created successfully'})

@app.put('/edit/{patient_id}', tags=["Patients"], summary="Update Patient Details")
def update_patient(patient_id: str, patient_update: PatientUpdate):
    """Partially update an existing patient's details and automatically recalculate BMI and verdict."""
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing_patient_info = data[patient_id]
    updated_patient_info = patient_update.model_dump(exclude_unset=True)

    for key, value in updated_patient_info.items():
        existing_patient_info[key] = value

    existing_patient_info['id'] = patient_id
    patient_pydantic_obj = Patient(**existing_patient_info)

    existing_patient_info = patient_pydantic_obj.model_dump(exclude={'id'})
    data[patient_id] = existing_patient_info
    save_data(data)

    return JSONResponse(status_code=200, content={"message": 'patient updated'})

@app.delete('/delete/{patient_id}', tags=["Patients"], summary="Delete Patient Record")
def delete_patient(patient_id: str):
    """Delete a patient record by ID from the database."""
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail='Patient not found')

    del data[patient_id]
    save_data(data)
    return JSONResponse(status_code=200, content={'message': "patient deleted"})
