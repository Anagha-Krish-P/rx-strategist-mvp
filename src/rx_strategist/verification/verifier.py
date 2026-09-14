from typing import List
from rx_strategist.models.prescription import Patient, Medication, Prescription
from rx_strategist.verification.indication import check_indication
from rx_strategist.verification.dosage import check_dosage
from rx_strategist.verification.interaction import check_interactions
from rx_strategist.verification.allergy import check_allergies

def verify_medication(medication: Medication, patient: Patient):
    indication = check_indication(
        medication.drug,
        patient.conditions
    )
    dosage = {
        "status": "REVIEW",
        "reason": "No matching indication."
    }
    matched_condition = indication.get(
        "matched_condition"
    )
    if matched_condition:
        dosage = check_dosage(
            medication.drug,
            matched_condition,
            medication.dose,
            medication.frequency
        )
    if (
        indication["status"] == "APPROPRIATE"
        and dosage["status"] == "APPROPRIATE"
    ):
        final_status = "APPROPRIATE"
    else:
        final_status = "REVIEW"
    return {
        "drug": medication.drug,
        "dose": medication.dose,
        "frequency": medication.frequency,
        "route": medication.route,
        "indication": indication,
        "dosage": dosage,
        "final_status": final_status
    }

def verify_prescription(prescription: Prescription):
    medication_results = []
    for medication in prescription.medications:
        result = verify_medication(
            medication,
            prescription.patient
        )
        medication_results.append(result)
    interaction_result = check_interactions(
        prescription.medications
    )
    allergy_result = check_allergies(
        prescription.medications,
        prescription.patient.allergies,
    )
    has_review = any(
        medication["final_status"] == "REVIEW"
        for medication in medication_results
    )
    if (
        has_review
        or interaction_result["status"]
        == "INTERACTION_FOUND"
        or allergy_result["status"]
        == "ALLERGY_FOUND"
    ):
        overall_status = "REVIEW"
    else:
        overall_status = "APPROPRIATE"
    return {
        "overall_status": overall_status,
        "medications": medication_results,
        "interaction_summary": interaction_result,
        "allergy_summary": allergy_result,
    }
