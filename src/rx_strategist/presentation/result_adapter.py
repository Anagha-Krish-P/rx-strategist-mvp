import re
from typing import Any, Dict, List, Optional

DRUG_TOKEN_RE = re.compile(r"[a-z0-9]+")


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

    drug_names = [
        _text_or_missing(medication.get("drug"))
        for medication in medications
        if medication.get("drug")
    ]
    drug_tokens = _drug_tokens(drug_names)
    evidence_items = _filter_evidence(evidence_items, drug_tokens)
    api_cards = _api_evidence_cards(medications)
    evidence_items = api_cards + evidence_items

    kg_lines = [
        line
        for line in _kg_lines(kg_context)
        if _text_mentions_tokens(line, drug_tokens)
    ]
    recap = _deterministic_recap(
        verification.get("overall_status"),
        interaction_findings,
        indication_findings,
        dosage_findings,
        allergy_findings,
    )
    ocr_text = result.get("ocr_text") or result.get("raw_text") or ""
    ocr_lines = _ocr_line_rows(ocr_text)
    ocr_fields = _ocr_field_rows(patient, medications)

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
        "ocr_text": ocr_text,
        "ocr_lines": ocr_lines,
        "ocr_fields": ocr_fields,
        "ocr_lines_markdown": _markdown_table(["Line", "Text"], ocr_lines),
        "ocr_fields_markdown": _markdown_table(["Field", "Value"], ocr_fields),
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


def _drug_tokens(drug_names: List[str]) -> List[str]:
    tokens = []
    for name in drug_names:
        for token in DRUG_TOKEN_RE.findall(str(name).lower()):
            if len(token) > 3:
                tokens.append(token)
    return list(dict.fromkeys(tokens))


def _text_mentions_tokens(text: str, tokens: List[str]) -> bool:
    if not tokens:
        return False
    blob = str(text or "").lower()
    return any(token in blob for token in tokens)


def _filter_evidence(items: List[dict], tokens: List[str]) -> List[dict]:
    if not tokens:
        return []
    kept = []
    for item in items:
        blob = " ".join(
            [
                str(item.get("source") or ""),
                str(item.get("title") or ""),
                str(item.get("text") or ""),
            ]
        )
        if _text_mentions_tokens(blob, tokens):
            kept.append(item)
    return kept


def _api_evidence_cards(medications: List[dict]) -> List[dict]:
    cards = []
    seen = set()
    for medication in medications:
        lookup = medication.get("api_lookup") or {}
        if not lookup.get("resolved"):
            continue
        drug = str(medication.get("drug") or lookup.get("name") or "Medication")
        key = drug.lower()
        if key in seen:
            continue
        seen.add(key)
        parts = []
        if lookup.get("rxcui"):
            parts.append(f"RxCUI: {lookup['rxcui']}")
        ingredients = lookup.get("ingredients") or []
        if ingredients:
            parts.append("Active ingredients: " + ", ".join(str(item) for item in ingredients))
        if lookup.get("indications_text"):
            parts.append("Indications: " + lookup["indications_text"])
        if lookup.get("dosage_text"):
            parts.append("Dosage guidance: " + lookup["dosage_text"])
        source = lookup.get("source") or "public API"
        cards.append(
            {
                "source": source,
                "title": f"{drug} — API drug specification",
                "text": "\n\n".join(parts) or f"{drug} was resolved via {source}.",
                "score": None,
            }
        )
    return cards


def _ocr_line_rows(ocr_text: str) -> List[dict]:
    lines = [line.strip() for line in str(ocr_text or "").splitlines() if line.strip()]
    if not lines:
        return [{"Line": "—", "Text": "No OCR text was returned."}]
    return [{"Line": str(index), "Text": line} for index, line in enumerate(lines, start=1)]


def _ocr_field_rows(patient: dict, medications: List[dict]) -> List[dict]:
    rows = [
        {"Field": "Age", "Value": _text_or_missing(patient.get("age") if patient.get("age") not in (None, 0) else None)},
        {
            "Field": "Conditions",
            "Value": ", ".join(patient.get("conditions") or []) or "Not extracted",
        },
        {
            "Field": "Allergies",
            "Value": ", ".join(patient.get("allergies") or []) or "Not extracted",
        },
    ]
    if not medications:
        rows.append({"Field": "Medicines", "Value": "Not extracted"})
        return rows
    for index, medication in enumerate(medications, start=1):
        rows.append(
            {
                "Field": f"Medicine {index}",
                "Value": " ".join(
                    part
                    for part in [
                        medication.get("drug"),
                        medication.get("dose"),
                        medication.get("frequency"),
                        medication.get("route"),
                    ]
                    if part
                )
                or "Not extracted",
            }
        )
    return rows


def _markdown_table(headers: List[str], rows: List[dict]) -> str:
    if not rows:
        return "_No data._"
    escaped_headers = [_escape_cell(header) for header in headers]
    lines = [
        "| " + " | ".join(escaped_headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        values = [_escape_cell(row.get(header, "")) for header in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _escape_cell(value: Any) -> str:
    text = str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")
    return text.strip() or " "


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
