import re
from typing import Any, Dict, List, Optional

AGE_RE = re.compile(
    r"(?:age\s*[:\-]?\s*)?(\d{1,3})\s*(?:years?\s*old|years?|yrs?|y/?o)\b",
    re.IGNORECASE,
)
AGE_LABEL_RE = re.compile(r"\bage\s*[:\-]\s*(\d{1,3})\b", re.IGNORECASE)
CONDITION_LABEL_RE = re.compile(
    r"(?:(?:medical\s+)?conditions?|diagnosis|dx|indication|for)\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)


def parse_patient_from_ocr(ocr_text: str) -> Dict[str, Any]:
    text = (ocr_text or "").strip()
    if not text:
        return {"age": None, "conditions": []}

    age = _parse_age(text)
    conditions = _parse_conditions(text)
    return {"age": age, "conditions": conditions}


def patient_fields_from_extraction(extracted: Any, ocr_text: str = "") -> Dict[str, Any]:
    age = None
    conditions: List[str] = []
    patient = getattr(extracted, "patient", None)
    if patient is not None:
        raw_age = getattr(patient, "age", None)
        try:
            parsed_age = int(raw_age)
            if parsed_age > 0:
                age = parsed_age
        except (TypeError, ValueError):
            age = None
        raw_conditions = getattr(patient, "conditions", None) or []
        conditions = [str(item).strip() for item in raw_conditions if str(item).strip()]

    fallback = parse_patient_from_ocr(ocr_text)
    if age is None:
        age = fallback.get("age")
    if not conditions:
        conditions = fallback.get("conditions") or []
    return {"age": age, "conditions": conditions}


def format_conditions(conditions: Optional[List[str]]) -> str:
    return ", ".join(str(item).strip() for item in (conditions or []) if str(item).strip())


def _parse_age(text: str) -> Optional[int]:
    match = AGE_LABEL_RE.search(text) or AGE_RE.search(text)
    if not match:
        return None
    age = int(match.group(1))
    if age <= 0 or age > 120:
        return None
    return age


def _parse_conditions(text: str) -> List[str]:
    found: List[str] = []
    for line in text.splitlines():
        match = CONDITION_LABEL_RE.search(line.strip())
        if not match:
            continue
        found.extend(_split_conditions(match.group(1)))
    return list(dict.fromkeys(found))


def _split_conditions(raw: str) -> List[str]:
    parts = re.split(r"[,;/]| and ", raw)
    cleaned = []
    for part in parts:
        item = part.strip(" .")
        if item and item.lower() not in {"unknown", "none", "n/a", "nil"}:
            cleaned.append(item)
    return cleaned
