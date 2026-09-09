from typing import List, Optional


def final_check(
    prescription: dict,
    verification: dict,
    evidence: Optional[List[dict]] = None,
    kg_context: Optional[dict] = None,
) -> dict:
    evidence = evidence or []
    kg_context = kg_context or {}
    verification_status = verification["overall_status"]

    cited = []
    for hit in evidence:
        cited.append(
            {
                "id": hit["id"],
                "title": hit.get("title", hit["id"]),
                "score": hit.get("score", 0.0),
                "snippet": _snippet(hit.get("text", "")),
            }
        )

    drugs = [
        medication["drug"].lower()
        for medication in prescription.get("medications", [])
    ]
    covered = []
    missing = []
    for drug in drugs:
        if any(drug in hit["id"] or drug in hit.get("text", "").lower() for hit in evidence):
            covered.append(drug)
        else:
            missing.append(drug)

    return {
        "final_decision": verification_status,
        "verification_status": verification_status,
        "checker_status": "COMPLETE",
        "evidence_count": len(evidence),
        "evidence_coverage": {
            "covered_drugs": covered,
            "missing_drugs": missing,
        },
        "supporting_evidence": cited,
        "kg_context": kg_context,
        "notes": (
            "Final decision matches the deterministic verification engine. "
            "Retrieved evidence and knowledge-graph context are attached for "
            "review and are not used to override APPROPRIATE or REVIEW."
        ),
    }


def _snippet(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
