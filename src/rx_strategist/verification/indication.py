from typing import Callable, Optional

from rx_strategist.knowledge.drug_database import DRUG_DATABASE
from rx_strategist.knowledge.drug_lookup import lookup_drug


def check_indication(drug_name, conditions, lookup_fn: Optional[Callable] = None):
    drug = DRUG_DATABASE.get(drug_name.lower())
    if drug:
        for condition in conditions:
            if condition.lower() in [
                indication.lower()
                for indication in drug["indications"]
            ]:
                return {
                    "status": "APPROPRIATE",
                    "matched_condition": condition,
                    "reason": f"{drug_name} has a matching indication.",
                }
        return {
            "status": "REVIEW",
            "reason": "No matching indication found.",
        }

    lookup = (lookup_fn or lookup_drug)(drug_name)
    if lookup.get("resolved"):
        ingredients = ", ".join(lookup.get("ingredients") or [])
        snippet = (lookup.get("indications_text") or "").strip()
        reason = f"{drug_name} verified via {(lookup.get('source') or 'public API')}."
        if ingredients:
            reason += f" Active ingredient(s): {ingredients}."
        if snippet:
            reason += " FDA label indications were retrieved."
        return {
            "status": "APPROPRIATE",
            "source": lookup.get("source"),
            "reason": reason,
            "lookup": lookup,
        }
    return {
        "status": "REVIEW",
        "reason": "Drug not found in knowledge base.",
        "lookup": lookup,
    }
