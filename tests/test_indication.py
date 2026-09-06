from rx_strategist.verification.indication import check_indication


def test_matching_indication_is_appropriate():
    result = check_indication("losartan", ["Hypertension"])

    assert result == {
        "status": "APPROPRIATE",
        "matched_condition": "Hypertension",
        "reason": "losartan has a matching indication.",
    }


def test_missing_indication_requires_review():
    result = check_indication("losartan", ["asthma"])

    assert result["status"] == "REVIEW"
    assert result["reason"] == "No matching indication found."
