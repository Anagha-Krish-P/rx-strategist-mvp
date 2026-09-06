from rx_strategist.knowledge.drug_database import DRUG_DATABASE

def check_indication(drug_name, conditions):
    drug = DRUG_DATABASE.get(drug_name.lower())
    if not drug:
        return {
            "status": "REVIEW",
            "reason": "Drug not found in knowledge base."
        }
    for condition in conditions:
        if condition.lower() in [
            indication.lower()
            for indication in drug["indications"]
        ]:
            return {
                "status": "APPROPRIATE",
                "matched_condition": condition,
                "reason": f"{drug_name} has a matching indication."
            }
    return {
        "status": "REVIEW",
        "reason": "No matching indication found."
    }
