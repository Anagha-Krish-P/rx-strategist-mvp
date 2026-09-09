from rx_strategist.checking.final_checker import final_check


def test_final_check_does_not_override_review():
    result = final_check(
        prescription={
            "medications": [{"drug": "losartan"}, {"drug": "metformin"}],
        },
        verification={"overall_status": "REVIEW"},
        evidence=[
            {
                "id": "losartan_metformin_interaction",
                "title": "Losartan and metformin interaction",
                "score": 0.8,
                "text": "Demo interaction between losartan and metformin.",
            }
        ],
        kg_context={"interactions": [{"drug_a": "losartan", "drug_b": "metformin"}]},
    )

    assert result["final_decision"] == "REVIEW"
    assert result["verification_status"] == "REVIEW"
    assert result["evidence_count"] == 1
    assert "losartan" in result["evidence_coverage"]["covered_drugs"]
    assert result["supporting_evidence"][0]["id"] == "losartan_metformin_interaction"


def test_final_check_keeps_appropriate_status():
    result = final_check(
        prescription={"medications": [{"drug": "losartan"}]},
        verification={"overall_status": "APPROPRIATE"},
        evidence=[],
    )

    assert result["final_decision"] == "APPROPRIATE"
    assert result["checker_status"] == "COMPLETE"
    assert result["evidence_coverage"]["missing_drugs"] == ["losartan"]
