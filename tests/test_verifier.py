from rx_strategist.models.prescription import Medication, Patient, Prescription
from rx_strategist.verification.verifier import verify_prescription


def make_patient():
    return Patient(
        age=55,
        gender="female",
        conditions=["hypertension", "type 2 diabetes"],
        allergies=[],
        kidney_function="normal",
    )


def test_appropriate_prescription_passes():
    prescription = Prescription(
        patient=make_patient(),
        medications=[
            Medication(
                drug="losartan",
                dose="50 mg",
                frequency="once daily",
                route="oral",
            )
        ],
    )

    result = verify_prescription(prescription)

    assert result["overall_status"] == "APPROPRIATE"
    assert result["medications"][0]["final_status"] == "APPROPRIATE"


def test_interaction_causes_prescription_review():
    prescription = Prescription(
        patient=make_patient(),
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

    result = verify_prescription(prescription)

    assert result["overall_status"] == "REVIEW"
    assert result["interaction_summary"]["status"] == "INTERACTION_FOUND"
