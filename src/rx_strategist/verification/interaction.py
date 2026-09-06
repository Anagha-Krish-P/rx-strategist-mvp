from typing import List
from rx_strategist.knowledge.drug_database import INTERACTIONS
from rx_strategist.models.prescription import Medication

def check_interactions(medications: List[Medication]):
    results = []
    drugs = [
        medication.drug.lower()
        for medication in medications
    ]
    for i in range(len(drugs)):
        for j in range(i + 1, len(drugs)):
            drug_a = drugs[i]
            drug_b = drugs[j]
            interaction = (
                INTERACTIONS
                .get(drug_a, {})
                .get(drug_b)
            )
            if interaction:
                results.append({
                    "drug_a": drug_a,
                    "drug_b": drug_b,
                    "status": "INTERACTION_FOUND",
                    "details": interaction
                })
    if results:
        return {
            "status": "INTERACTION_FOUND",
            "interactions": results
        }
    return {
        "status": "NO_KNOWN_INTERACTION",
        "interactions": []
    }
