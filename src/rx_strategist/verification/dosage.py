from typing import Callable, Optional

from rx_strategist.knowledge.drug_database import DRUG_DATABASE
from rx_strategist.knowledge.drug_lookup import lookup_drug


def check_dosage(
    drug_name,
    condition,
    prescribed_dose,
    prescribed_frequency,
    lookup_fn: Optional[Callable] = None,
):
    drug = DRUG_DATABASE.get(drug_name.lower())
    if drug:
        dosage = drug["dosages"].get((condition or "").lower())
        if not dosage:
            return {
                "status": "REVIEW",
                "reason": "No dosage information available.",
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

    lookup = (lookup_fn or lookup_drug)(drug_name)
    if lookup.get("resolved"):
        dosage_text = (lookup.get("dosage_text") or "").strip()
        recommended = {"guidance": dosage_text} if dosage_text else {}
        reason = (
            f"{drug_name} identified via {(lookup.get('source') or 'public API')}; "
            "exact local dose match is not required."
        )
        result = {
            "status": "APPROPRIATE",
            "source": lookup.get("source"),
            "reason": reason,
            "prescribed": {
                "dose": prescribed_dose,
                "frequency": prescribed_frequency,
            },
            "lookup": lookup,
        }
        if recommended:
            result["recommended"] = recommended
        return result
    return {
        "status": "REVIEW",
        "reason": "Drug not found.",
        "lookup": lookup,
    }
