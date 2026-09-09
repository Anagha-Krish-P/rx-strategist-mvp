import pytest

from rx_strategist.rag.retriever import EvidenceRetriever


def test_retriever_finds_losartan_evidence():
    retriever = EvidenceRetriever.from_evidence_dir()
    hits = retriever.retrieve("losartan hypertension 50 mg once daily")

    assert hits
    assert any("losartan" in hit["id"] for hit in hits)
    assert hits[0]["score"] > 0


def test_retriever_finds_interaction_evidence_for_combo_prescription():
    retriever = EvidenceRetriever.from_evidence_dir()
    prescription = {
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

    hits = retriever.retrieve_for_prescription(prescription, k=3)
    hit_ids = {hit["id"] for hit in hits}

    assert "losartan_metformin_interaction" in hit_ids or any(
        "interaction" in hit["id"] or "interaction" in hit["text"].lower()
        for hit in hits
    )


def test_empty_query_raises_value_error():
    retriever = EvidenceRetriever.from_evidence_dir()

    with pytest.raises(ValueError, match="query"):
        retriever.retrieve("   ")
