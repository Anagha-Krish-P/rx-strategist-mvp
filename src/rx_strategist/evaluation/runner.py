from typing import List, Optional

from rx_strategist.checking.final_checker import final_check
from rx_strategist.evaluation.cases import load_gold_cases
from rx_strategist.evaluation.metrics import compute_metrics
from rx_strategist.knowledge.graph import KnowledgeGraph
from rx_strategist.models.prescription import Prescription
from rx_strategist.rag.retriever import EvidenceRetriever
from rx_strategist.verification.verifier import verify_prescription


def score_prescription(
    prescription: dict,
    retriever: Optional[EvidenceRetriever] = None,
    graph: Optional[KnowledgeGraph] = None,
) -> dict:
    retriever = retriever or EvidenceRetriever.from_evidence_dir()
    graph = graph or KnowledgeGraph.from_drug_database()
    parsed = Prescription.model_validate(prescription)
    verification = verify_prescription(parsed)
    evidence = retriever.retrieve_for_prescription(prescription)
    kg_context = graph.context_for_prescription(prescription)
    checked = final_check(prescription, verification, evidence, kg_context)
    return {
        "verification": verification,
        "evidence": evidence,
        "kg_context": kg_context,
        "final_check": checked,
        "predicted": checked["final_decision"],
    }


def evaluate(cases: Optional[List[dict]] = None) -> dict:
    retriever = EvidenceRetriever.from_evidence_dir()
    graph = KnowledgeGraph.from_drug_database()
    rows = []
    for case in cases or load_gold_cases():
        scored = score_prescription(
            case["prescription"],
            retriever=retriever,
            graph=graph,
        )
        rows.append(
            {
                "id": case["id"],
                "description": case.get("description", ""),
                "expected": case["expected_status"],
                "predicted": scored["predicted"],
                "passed": scored["predicted"] == case["expected_status"],
                "evidence_count": scored["final_check"]["evidence_count"],
            }
        )
    return compute_metrics(rows)
