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


def test_matching_allergy_causes_prescription_review():
    prescription = Prescription(
        patient=Patient(
            age=55,
            gender="female",
            conditions=["hypertension"],
            allergies=["losartan"],
            kidney_function="normal",
        ),
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

    assert result["overall_status"] == "REVIEW"
    assert result["allergy_summary"]["status"] == "ALLERGY_FOUND"


def test_unknown_drug_is_appropriate_when_public_api_resolves(monkeypatch):
    resolved = {
        "resolved": True,
        "source": "rxnorm/openfda",
        "ingredients": ["ciprofloxacin"],
        "indications_text": "infections",
        "dosage_text": "500 mg twice daily",
        "rxcui": "20481",
        "error": None,
        "name": "Ciplox",
    }
    monkeypatch.setattr(
        "rx_strategist.verification.indication.lookup_drug",
        lambda name: resolved,
    )
    monkeypatch.setattr(
        "rx_strategist.verification.dosage.lookup_drug",
        lambda name: resolved,
    )
    prescription = Prescription(
        patient=Patient(
            age=42,
            gender="unknown",
            conditions=["dry eye"],
            allergies=[],
            kidney_function="unknown",
        ),
        medications=[
            Medication(
                drug="Ciplox",
                dose="500 mg",
                frequency="twice daily",
                route="oral",
            )
        ],
    )
    result = verify_prescription(prescription)
    assert result["overall_status"] == "APPROPRIATE"
    assert result["medications"][0]["final_status"] == "APPROPRIATE"
    assert result["medications"][0]["api_lookup"]["rxcui"] == "20481"
