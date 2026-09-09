from rx_strategist.evaluation.runner import evaluate, score_prescription


def test_score_prescription_flags_demo_interaction():
    scored = score_prescription(
        {
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
                },
                {
                    "drug": "metformin",
                    "dose": "500 mg",
                    "frequency": "twice daily",
                    "route": "oral",
                },
            ],
        }
    )

    assert scored["predicted"] == "REVIEW"
    assert scored["verification"]["overall_status"] == "REVIEW"
    assert scored["final_check"]["final_decision"] == "REVIEW"
    assert scored["evidence"]
    assert scored["kg_context"]["interactions"]


def test_gold_evaluation_is_accurate():
    report = evaluate()

    assert report["n_cases"] == 6
    assert report["n_correct"] == report["n_cases"]
    assert report["accuracy"] == 1.0
    assert all(case["passed"] for case in report["cases"])
