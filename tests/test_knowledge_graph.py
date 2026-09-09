from rx_strategist.knowledge.graph import KnowledgeGraph


def test_graph_links_losartan_to_hypertension():
    graph = KnowledgeGraph.from_drug_database()

    assert "hypertension" in graph.indications_for("losartan")
    dosage = graph.dosage_for("losartan", "hypertension")
    assert dosage == {"dose": "50 mg", "frequency": "once daily", "condition": "hypertension"}


def test_graph_finds_losartan_metformin_interaction():
    graph = KnowledgeGraph.from_drug_database()
    interactions = graph.interactions_for(["losartan", "metformin"])

    assert len(interactions) == 1
    assert set([interactions[0]["drug_a"], interactions[0]["drug_b"]]) == {
        "losartan",
        "metformin",
    }


def test_graph_context_for_prescription_includes_known_nodes():
    graph = KnowledgeGraph.from_drug_database()
    context = graph.context_for_prescription(
        {
            "patient": {
                "conditions": ["hypertension", "type 2 diabetes"],
            },
            "medications": [
                {"drug": "losartan"},
                {"drug": "metformin"},
            ],
        }
    )

    assert len(context["drugs"]) == 2
    assert len(context["conditions"]) == 2
    assert context["interactions"]
    assert "losartan" in context["indications"]
