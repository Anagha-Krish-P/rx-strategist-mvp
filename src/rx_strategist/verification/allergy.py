from typing import List

from rx_strategist.models.prescription import Medication


def check_allergies(medications: List[Medication], allergies: List[str]):
    allergy_tokens = [
        allergy.strip().lower()
        for allergy in allergies or []
        if allergy and str(allergy).strip()
    ]
    matches = []
    for medication in medications:
        drug = medication.drug.lower().strip()
        for allergy in allergy_tokens:
            if allergy == drug or allergy in drug or drug in allergy:
                matches.append(
                    {
                        "drug": medication.drug,
                        "allergy": allergy,
                        "status": "ALLERGY_MATCH",
                        "reason": (
                            f"Prescribed {medication.drug} may match "
                            f"recorded allergy '{allergy}'."
                        ),
                    }
                )
                break
    if matches:
        return {
            "status": "ALLERGY_FOUND",
            "matches": matches,
        }
    return {
        "status": "NO_ALLERGY_MATCH",
        "matches": [],
    }
