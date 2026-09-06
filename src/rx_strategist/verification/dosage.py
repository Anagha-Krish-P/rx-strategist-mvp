from rx_strategist.knowledge.drug_database import DRUG_DATABASE

def check_dosage(
    drug_name,
    condition,
    prescribed_dose,
    prescribed_frequency
):
    drug = DRUG_DATABASE.get(drug_name.lower())
    if not drug:
        return {
            "status": "REVIEW",
            "reason": "Drug not found."
        }
    dosage = drug["dosages"].get(condition.lower())
    if not dosage:
        return {
            "status": "REVIEW",
            "reason": "No dosage information available."
        }
    dose_match = (
        prescribed_dose.lower()
        == dosage["dose"].lower()
    )
    frequency_match = (
        prescribed_frequency.lower()
        == dosage["frequency"].lower()
    )
    if dose_match and frequency_match:
        return {
            "status": "APPROPRIATE",
            "prescribed": {
                "dose": prescribed_dose,
                "frequency": prescribed_frequency
            },
            "recommended": dosage
        }
    return {
        "status": "REVIEW",
        "prescribed": {
            "dose": prescribed_dose,
            "frequency": prescribed_frequency
        },
        "recommended": dosage
    }
