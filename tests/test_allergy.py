from rx_strategist.models.prescription import Medication
from rx_strategist.verification.allergy import check_allergies


def test_allergy_match_is_reported():
    result = check_allergies(
        [
            Medication(
                drug="losartan",
                dose="50 mg",
                frequency="once daily",
                route="oral",
            )
        ],
        ["losartan"],
    )

    assert result["status"] == "ALLERGY_FOUND"
    assert result["matches"][0]["drug"] == "losartan"


def test_unrelated_allergy_is_not_reported():
    result = check_allergies(
        [
            Medication(
                drug="losartan",
                dose="50 mg",
                frequency="once daily",
                route="oral",
            )
        ],
        ["penicillin"],
    )

    assert result == {
        "status": "NO_ALLERGY_MATCH",
        "matches": [],
    }
