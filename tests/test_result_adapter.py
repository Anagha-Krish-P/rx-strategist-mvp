from rx_strategist.presentation.report import build_markdown_report
from rx_strategist.presentation.result_adapter import adapt_workflow_result
from rx_strategist.presentation.session import next_upload_state


def _sample_result():
    return {
        "ocr_text": "Losartan 50 mg OD PO.",
        "prescription": {
            "patient": {
                "age": 55,
                "gender": "female",
                "conditions": ["hypertension", "type 2 diabetes"],
                "allergies": [],
                "kidney_function": "normal",
            },
            "medications": [
                {
                    "drug": "losartan",
                    "dose": "50 mg",
                    "frequency": "once daily",
                    "route": "oral",
                }
            ],
        },
        "evidence": [
            {
                "id": "losartan_hypertension",
                "title": "Losartan for hypertension",
                "text": "Losartan is used for hypertension.",
                "score": 0.8,
            }
        ],
        "verification": {
            "overall_status": "REVIEW",
            "medications": [
                {
                    "drug": "losartan",
                    "dose": "50 mg",
                    "frequency": "once daily",
                    "route": "oral",
                    "indication": {
                        "status": "APPROPRIATE",
                        "matched_condition": "hypertension",
                        "reason": "losartan has a matching indication.",
                    },
                    "dosage": {
                        "status": "APPROPRIATE",
                        "recommended": {"dose": "50 mg", "frequency": "once daily"},
                    },
                    "final_status": "APPROPRIATE",
                },
                {
                    "drug": "metformin",
                    "dose": "500 mg",
                    "frequency": "twice daily",
                    "route": "oral",
                    "indication": {
                        "status": "APPROPRIATE",
                        "matched_condition": "type 2 diabetes",
                    },
                    "dosage": {"status": "APPROPRIATE"},
                    "final_status": "APPROPRIATE",
                },
            ],
            "interaction_summary": {
                "status": "INTERACTION_FOUND",
                "interactions": [
                    {
                        "drug_a": "losartan",
                        "drug_b": "metformin",
                        "status": "INTERACTION_FOUND",
                        "details": {
                            "severity": "example",
                            "reason": "Demo interaction record",
                        },
                    }
                ],
            },
            "allergy_summary": {"status": "NO_ALLERGY_MATCH", "matches": []},
        },
        "kg_context": {
            "indications": {"losartan": ["hypertension"]},
            "interactions": [
                {"drug_a": "losartan", "drug_b": "metformin", "severity": "example"}
            ],
            "dosages": {},
        },
        "final_check": {
            "final_decision": "REVIEW",
            "notes": "Final decision matches the deterministic verification engine.",
            "supporting_evidence": [],
        },
    }


def test_adapter_maps_review_status():
    view = adapt_workflow_result(_sample_result())

    assert view["status"]["key"] == "REVIEW"
    assert view["status"]["label"] == "REVIEW RECOMMENDED"
    assert view["metrics"]["medicines"] == 2
    assert view["metrics"]["interactions"] == 1
    assert view["findings"]["interactions"][0]["medicines"] == ["losartan", "metformin"]
    assert "losartan → TREATS → hypertension" in view["kg_lines"]
    assert view["ocr_text"].startswith("Losartan")


def test_adapter_maps_appropriate_to_low_concern():
    result = _sample_result()
    result["verification"]["overall_status"] = "APPROPRIATE"
    result["verification"]["interaction_summary"] = {
        "status": "NO_KNOWN_INTERACTION",
        "interactions": [],
    }
    result["verification"]["medications"] = [
        result["verification"]["medications"][0]
    ]
    view = adapt_workflow_result(result)

    assert view["status"]["key"] == "LOW_CONCERN"
    assert "definitely safe" not in view["status"]["headline"].lower()


def test_adapter_incomplete_without_medicines():
    view = adapt_workflow_result({"verification": {"overall_status": "APPROPRIATE"}})

    assert view["status"]["key"] == "UNKNOWN"
    assert view["metrics"]["medicines"] == 0


def test_markdown_report_includes_backend_fields():
    view = adapt_workflow_result(_sample_result())
    report = build_markdown_report(view)

    assert "REVIEW RECOMMENDED" in report
    assert "losartan" in report
    assert "Demo interaction record" in report
    assert "does not replace professional clinical judgment" in report


def test_new_upload_invalidates_previous_result():
    first = next_upload_state(None, "a.png:10")
    assert first["invalidate_result"] is True
    same = next_upload_state("a.png:10", "a.png:10")
    assert same["invalidate_result"] is False
    swapped = next_upload_state("a.png:10", "b.png:20")
    assert swapped["invalidate_result"] is True
    assert swapped["file_id"] == "b.png:20"


def test_adapter_filters_demo_evidence_and_builds_ocr_tables():
    result = {
        "ocr_text": "Age: 42 years\nCiplox 500 mg BD\nRefresh Tear 1 drop TID",
        "prescription": {
            "patient": {"age": 42, "conditions": ["dry eye"], "allergies": []},
            "medications": [
                {"drug": "Ciplox", "dose": "500 mg", "frequency": "twice daily", "route": "oral"}
            ],
        },
        "evidence": [
            {
                "id": "losartan_hypertension",
                "title": "Losartan for hypertension",
                "text": "Losartan is used for hypertension.",
                "score": 0.9,
            }
        ],
        "verification": {
            "overall_status": "APPROPRIATE",
            "medications": [
                {
                    "drug": "Ciplox",
                    "dose": "500 mg",
                    "frequency": "twice daily",
                    "route": "oral",
                    "indication": {"status": "APPROPRIATE", "source": "rxnorm"},
                    "dosage": {"status": "APPROPRIATE"},
                    "final_status": "APPROPRIATE",
                    "api_lookup": {
                        "resolved": True,
                        "rxcui": "20481",
                        "ingredients": ["Ciprofloxacin"],
                        "indications_text": "Bacterial infections",
                        "dosage_text": "500 mg twice daily",
                        "source": "rxnorm/openfda",
                    },
                }
            ],
            "interaction_summary": {"status": "NO_KNOWN_INTERACTION", "interactions": []},
            "allergy_summary": {"status": "NO_ALLERGY_MATCH", "matches": []},
        },
        "kg_context": {
            "indications": {"losartan": ["hypertension"]},
            "interactions": [],
            "dosages": {},
        },
        "final_check": {"notes": "ok", "supporting_evidence": []},
    }
    view = adapt_workflow_result(result)
    assert all("losartan" not in (item["title"] + item["text"]).lower() for item in view["evidence"])
    assert view["kg_lines"] == []
    assert any("Ciprofloxacin" in item["text"] for item in view["evidence"])
    assert "| Line |" in view["ocr_lines_markdown"]
    assert "Ciplox 500 mg BD" in view["ocr_lines_markdown"]
    assert "| Field |" in view["ocr_fields_markdown"]
    assert "42" in view["ocr_fields_markdown"]
    assert "Medicine 1" in view["ocr_fields_markdown"]
