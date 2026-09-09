from rx_strategist.agents.workflow import run_workflow
from rx_strategist.models.prescription import Prescription, Medication, Patient
import pytest


def make_combo_prescription():
    return Prescription(
        patient=Patient(
            age=55,
            gender="female",
            conditions=["hypertension", "type 2 diabetes"],
            allergies=[],
            kidney_function="normal",
        ),
        medications=[
            Medication(
                drug="losartan",
                dose="50 mg",
                frequency="once daily",
                route="oral",
            ),
            Medication(
                drug="metformin",
                dose="500 mg",
                frequency="twice daily",
                route="oral",
            ),
        ],
    )


def test_workflow_runs_retrieve_verify_kg_and_final_check():
    result = run_workflow(prescription=make_combo_prescription())

    assert result["verification"]["overall_status"] == "REVIEW"
    assert result["final_check"]["final_decision"] == "REVIEW"
    assert result["evidence"]
    assert result["kg_context"]["interactions"]
    assert result["final_check"]["verification_status"] == "REVIEW"


def test_workflow_requires_input():
    with pytest.raises(ValueError, match="prescription, raw_text, or image_path"):
        run_workflow()
