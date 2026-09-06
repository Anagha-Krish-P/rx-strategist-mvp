from pydantic import BaseModel
from typing import List, Optional

class Patient(BaseModel):
    age: int
    gender: str
    conditions: List[str]
    allergies: List[str]
    kidney_function: str

class Medication(BaseModel):
    drug: str
    dose: str
    frequency: str
    route: str

class Prescription(BaseModel):
    patient: Patient
    medications: List[Medication]

class ExtractedPrescription(BaseModel):
    patient: Patient
    medications: List[Medication]
