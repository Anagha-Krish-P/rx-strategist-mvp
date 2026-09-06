from rx_strategist.models.prescription import Medication
from rx_strategist.verification.interaction import check_interactions


def test_known_interaction_is_reported():
    result = check_interactions([
        Medication(drug="losartan", dose="50 mg", frequency="once daily", route="PO"),
        Medication(drug="metformin", dose="500 mg", frequency="twice daily", route="PO"),
    ])

    assert result["status"] == "INTERACTION_FOUND"
    assert len(result["interactions"]) == 1


def test_unknown_interaction_is_not_reported():
    result = check_interactions([
        Medication(drug="losartan", dose="50 mg", frequency="once daily", route="PO"),
        Medication(drug="aspirin", dose="81 mg", frequency="once daily", route="PO"),
    ])

    assert result == {
        "status": "NO_KNOWN_INTERACTION",
        "interactions": [],
    }
