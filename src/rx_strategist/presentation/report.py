from datetime import datetime, timezone
from typing import Any, Dict, List


def _join(values: List[Any]) -> str:
    return ", ".join(str(item) for item in values if item) or "None recorded"


def build_markdown_report(view: Dict[str, Any]) -> str:
    patient = view.get("patient") or {}
    status = view.get("status") or {}
    findings = view.get("findings") or {}
    lines = [
        "# Rx-Strategist Safety Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Overall Assessment",
        "",
        f"**{status.get('label', 'UNKNOWN / INCOMPLETE')}**",
        "",
        status.get("headline", ""),
        "",
        "## Patient Profile",
        "",
        f"- Age: {patient.get('age', 'Not extracted')}",
        f"- Conditions: {_join(patient.get('conditions') or [])}",
        f"- Allergies: {_join(patient.get('allergies') or [])}",
        f"- Kidney function: {patient.get('kidney_function', 'Not extracted')}",
        "",
        "## Medicines",
        "",
    ]
    medicines = view.get("medicines") or []
    if not medicines:
        lines.append("No medicines were identified.")
    else:
        lines.append("| Medicine | Dose | Frequency | Verification | Risk |")
        lines.append("|---|---|---|---|---|")
        for row in medicines:
            lines.append(
                f"| {row['Medicine']} | {row['Dose']} | {row['Frequency']} | "
                f"{row['Verification']} | {row['Risk']} |"
            )
    lines.extend(["", "## Safety Findings", ""])
    _append_finding_section(lines, "Drug–Drug Interactions", findings.get("interactions"))
    _append_finding_section(lines, "Indication Concerns", findings.get("indications"))
    _append_finding_section(lines, "Dosage / Frequency Concerns", findings.get("dosage"))
    _append_finding_section(lines, "Allergy Concerns", findings.get("allergies"))

    lines.extend(["", "## Evidence", ""])
    evidence = view.get("evidence") or []
    if not evidence:
        lines.append("No evidence items were retrieved.")
    else:
        for item in evidence:
            score = item.get("score")
            score_bit = f" (relevance {score})" if score is not None else ""
            lines.append(f"### {item.get('title')}{score_bit}")
            lines.append("")
            lines.append(f"Source: `{item.get('source')}`")
            lines.append("")
            lines.append(item.get("text") or "")
            lines.append("")

    lines.extend(
        [
            "## AI Safety Explanation",
            "",
            view.get("explanation_notes") or "No explanation notes were returned.",
            "",
            view.get("explanation_recap") or "",
            "",
            "## Extracted Prescription Text",
            "",
            view.get("ocr_lines_markdown") or "",
            "",
            view.get("ocr_fields_markdown") or "",
            "",
            "## Clinical Review Notice",
            "",
            "This system provides AI-assisted medication safety information "
            "and does not replace professional clinical judgment.",
            "",
        ]
    )
    return "\n".join(lines)


def _append_finding_section(lines: List[str], title: str, items: List[dict]):
    lines.append(f"### {title}")
    lines.append("")
    if not items:
        lines.append("None reported by the current analysis.")
        lines.append("")
        return
    for item in items:
        medicines = _join(item.get("medicines") or [])
        lines.append(f"- **{item.get('severity', 'Review')}** — {medicines}")
        lines.append(f"  - Why: {item.get('reason')}")
        lines.append(f"  - Recommendation: {item.get('recommendation')}")
    lines.append("")
