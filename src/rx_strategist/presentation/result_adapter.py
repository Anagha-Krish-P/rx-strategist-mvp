from typing import Any, Dict, List, Optional


def _text_or_missing(value: Any) -> str:
    if value is None:
        return "Not extracted"
    text = str(value).strip()
    return text if text else "Not extracted"


def _status_view(overall_status: Optional[str], has_medicines: bool) -> Dict[str, str]:
    if not has_medicines or overall_status not in {"APPROPRIATE", "REVIEW"}:
        return {
            "key": "UNKNOWN",
            "label": "UNKNOWN / INCOMPLETE",
            "headline": "The analysis result is incomplete.",
            "css_class": "status-unknown",
        }
    if overall_status == "APPROPRIATE":
        return {
            "key": "LOW_CONCERN",
            "label": "LOW CONCERN",
            "headline": "No major concern detected by the current analysis.",
            "css_class": "status-low",
        }
    return {
        "key": "REVIEW",
        "label": "REVIEW RECOMMENDED",
        "headline": "Potential safety concern detected.",
        "css_class": "status-review",
    }


def adapt_workflow_result(result: Optional[dict]) -> Dict[str, Any]:
    result = result or {}
    verification = result.get("verification") or {}
    prescription = result.get("prescription") or {}
    patient = prescription.get("patient") or {}
    medications = verification.get("medications") or []
    interaction_summary = verification.get("interaction_summary") or {}
    interactions = interaction_summary.get("interactions") or []
    allergy_summary = verification.get("allergy_summary") or {}
    allergy_matches = allergy_summary.get("matches") or []
    evidence = result.get("evidence") or []
    kg_context = result.get("kg_context") or {}
    final_check = result.get("final_check") or {}

    medicine_rows = []
    indication_findings = []
    dosage_findings = []
    review_meds = 0
    for medication in medications:
        final_status = medication.get("final_status") or "REVIEW"
        if final_status == "REVIEW":
            review_meds += 1
        medicine_rows.append(
            {
                "Medicine": _text_or_missing(medication.get("drug")),
                "Dose": _text_or_missing(medication.get("dose")),
                "Frequency": _text_or_missing(medication.get("frequency")),
                "Verification": final_status,
                "Risk": "Low" if final_status == "APPROPRIATE" else "Review",
            }
        )
        indication = medication.get("indication") or {}
        if indication.get("status") == "REVIEW":
            indication_findings.append(
                {
                    "severity": "Review",
                    "medicines": [_text_or_missing(medication.get("drug"))],
                    "reason": indication.get("reason") or "No matching indication found.",
                    "recommendation": "Clinician review of indication is recommended.",
                    "evidence": None,
                }
            )
        dosage = medication.get("dosage") or {}
        if dosage.get("status") == "REVIEW":
            recommended = dosage.get("recommended") or {}
            reason = dosage.get("reason")
            if not reason and recommended:
                reason = (
                    "Prescribed dose or frequency does not match the demo "
                    f"recommended {recommended.get('dose', '')} "
                    f"{recommended.get('frequency', '')}.".strip()
                )
            dosage_findings.append(
                {
                    "severity": "Review",
                    "medicines": [_text_or_missing(medication.get("drug"))],
                    "reason": reason or "Dosage requires review.",
                    "recommendation": "Clinician review of dose and frequency is recommended.",
                    "evidence": None,
                }
            )

    interaction_findings = []
    for item in interactions:
        details = item.get("details") or {}
        interaction_findings.append(
            {
                "severity": details.get("severity") or "Review",
                "medicines": [item.get("drug_a"), item.get("drug_b")],
                "reason": details.get("reason") or "Potential interaction detected.",
                "recommendation": "Clinician review of this drug combination is recommended.",
                "evidence": None,
            }
        )

    allergy_findings = []
    for item in allergy_matches:
        allergy_findings.append(
            {
                "severity": "Review",
                "medicines": [item.get("drug")],
                "reason": item.get("reason") or "Possible allergy match.",
                "recommendation": "Clinician review of allergy status is recommended.",
                "evidence": None,
            }
        )

    evidence_items = []
    for hit in evidence:
        evidence_items.append(
            {
                "source": hit.get("id") or hit.get("title") or "evidence",
                "title": hit.get("title") or hit.get("id") or "Evidence",
                "text": hit.get("text") or "",
                "score": hit.get("score"),
            }
        )
    if not evidence_items:
        for hit in final_check.get("supporting_evidence") or []:
            evidence_items.append(
                {
                    "source": hit.get("id") or hit.get("title") or "evidence",
                    "title": hit.get("title") or hit.get("id") or "Evidence",
                    "text": hit.get("snippet") or "",
                    "score": hit.get("score"),
                }
            )

    kg_lines = _kg_lines(kg_context)
    recap = _deterministic_recap(
        verification.get("overall_status"),
        interaction_findings,
        indication_findings,
        dosage_findings,
        allergy_findings,
    )

    return {
        "status": _status_view(verification.get("overall_status"), bool(medicine_rows)),
        "patient": patient,
        "medicines": medicine_rows,
        "metrics": {
            "medicines": len(medicine_rows),
            "interactions": len(interactions),
            "patient_risks": review_meds + len(allergy_matches),
            "evidence": len(evidence_items),
        },
        "findings": {
            "interactions": interaction_findings,
            "indications": indication_findings,
            "dosage": dosage_findings,
            "allergies": allergy_findings,
        },
        "evidence": evidence_items,
        "kg_lines": kg_lines,
        "ocr_text": result.get("ocr_text") or result.get("raw_text") or "",
        "explanation_notes": final_check.get("notes") or "",
        "explanation_recap": recap,
        "overall_status": verification.get("overall_status"),
    }


def _kg_lines(kg_context: dict) -> List[str]:
    lines = []
    indications = kg_context.get("indications") or {}
    for drug, conditions in indications.items():
        for condition in conditions or []:
            lines.append(f"{drug} → TREATS → {condition}")
    for item in kg_context.get("interactions") or []:
        lines.append(
            f"{item.get('drug_a')} → INTERACTS_WITH → {item.get('drug_b')}"
        )
    dosages = kg_context.get("dosages") or {}
    for key, dosage in dosages.items():
        if not dosage:
            continue
        lines.append(
            f"{key} → HAS_DOSAGE → {dosage.get('dose')} {dosage.get('frequency')}"
        )
    return lines


def _deterministic_recap(
    overall_status: Optional[str],
    interactions: List[dict],
    indications: List[dict],
    dosage: List[dict],
    allergies: List[dict],
) -> str:
    parts = []
    if overall_status == "APPROPRIATE":
        parts.append(
            "The deterministic verifier did not flag indication, dosage, "
            "interaction, or allergy matches for review."
        )
    elif overall_status == "REVIEW":
        parts.append("The deterministic verifier flagged this prescription for review.")
    else:
        parts.append("No complete verification status was available.")
    if interactions:
        parts.append(f"{len(interactions)} drug–drug interaction record(s) were found.")
    if indications:
        parts.append(f"{len(indications)} indication concern(s) were found.")
    if dosage:
        parts.append(f"{len(dosage)} dosage or frequency concern(s) were found.")
    if allergies:
        parts.append(f"{len(allergies)} possible allergy match(es) were found.")
    parts.append(
        "This summary restates structured verifier output. "
        "It is not a separate LLM safety opinion."
    )
    return " ".join(parts)
