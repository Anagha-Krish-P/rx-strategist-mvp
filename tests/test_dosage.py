from rx_strategist.verification.dosage import check_dosage


def test_matching_dosage_is_appropriate():
    result = check_dosage(
        "metformin", "type 2 diabetes", "500 mg", "twice daily"
    )

    assert result["status"] == "APPROPRIATE"
    assert result["recommended"] == {
        "dose": "500 mg",
        "frequency": "twice daily",
    }


def test_non_matching_dosage_requires_review():
    result = check_dosage(
        "metformin", "type 2 diabetes", "1000 mg", "twice daily"
    )

    assert result["status"] == "REVIEW"
    assert result["prescribed"]["dose"] == "1000 mg"
