from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from rx_strategist.checking.final_checker import final_check
from rx_strategist.knowledge.graph import KnowledgeGraph
from rx_strategist.models.prescription import Prescription
from rx_strategist.rag.retriever import EvidenceRetriever
from rx_strategist.verification.verifier import verify_prescription


class PipelineState(TypedDict, total=False):
    api_key: Optional[str]
    image_path: Optional[str]
    raw_text: Optional[str]
    ocr_text: str
    prescription: dict
    patient_overrides: dict
    evidence: list
    verification: dict
    kg_context: dict
    final_check: dict


def route_input(state: PipelineState) -> str:
    if state.get("image_path"):
        return "ocr"
    return "extract"


def ocr_node(state: PipelineState) -> dict:
    image_path = state.get("image_path")
    if not image_path:
        return {}
    api_key = state.get("api_key")
    if not api_key:
        raise ValueError("A Gemini API key is required for OCR.")
    from rx_strategist.ocr.gemini_ocr import GeminiPrescriptionOCR

    text = GeminiPrescriptionOCR(api_key=api_key).ocr_image(image_path)
    return {"ocr_text": text, "raw_text": text}


def apply_patient_overrides(prescription: dict, overrides: Optional[dict]) -> dict:
    if not overrides:
        return prescription
    patient = dict(prescription.get("patient") or {})
    if overrides.get("age") is not None and overrides.get("age") != "":
        patient["age"] = int(overrides["age"])
    if overrides.get("conditions") is not None:
        patient["conditions"] = [
            item.strip()
            for item in overrides["conditions"]
            if str(item).strip()
        ]
    if overrides.get("allergies") is not None:
        patient["allergies"] = [
            item.strip()
            for item in overrides["allergies"]
            if str(item).strip()
        ]
    patient.setdefault("gender", "unknown")
    patient.setdefault("kidney_function", "unknown")
    patient.setdefault("conditions", [])
    patient.setdefault("allergies", [])
    if "age" not in patient:
        patient["age"] = 0
    updated = dict(prescription)
    updated["patient"] = patient
    return updated


def extract_node(state: PipelineState) -> dict:
    prescription = state.get("prescription")
    if not prescription:
        raw_text = state.get("raw_text")
        if not raw_text:
            raise ValueError("Provide a prescription, raw_text, or image_path.")
        api_key = state.get("api_key")
        if not api_key:
            raise ValueError("A Gemini API key is required to extract prescription text.")
        from rx_strategist.extraction.gemini_extractor import GeminiPrescriptionExtractor

        extracted = GeminiPrescriptionExtractor(api_key=api_key).extract_prescription(
            raw_text
        )
        prescription = extracted.model_dump()
    prescription = apply_patient_overrides(
        prescription,
        state.get("patient_overrides"),
    )
    return {"prescription": prescription}


def retrieve_node(state: PipelineState) -> dict:
    retriever = EvidenceRetriever.from_evidence_dir()
    return {"evidence": retriever.retrieve_for_prescription(state["prescription"])}


def verify_node(state: PipelineState) -> dict:
    parsed = Prescription.model_validate(state["prescription"])
    return {"verification": verify_prescription(parsed)}


def kg_lookup_node(state: PipelineState) -> dict:
    graph = KnowledgeGraph.from_drug_database()
    return {"kg_context": graph.context_for_prescription(state["prescription"])}


def final_check_node(state: PipelineState) -> dict:
    checked = final_check(
        state["prescription"],
        state["verification"],
        state.get("evidence") or [],
        state.get("kg_context") or {},
    )
    return {"final_check": checked}


def build_workflow():
    graph = StateGraph(PipelineState)
    graph.add_node("ocr", ocr_node)
    graph.add_node("extract", extract_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("verify", verify_node)
    graph.add_node("kg_lookup", kg_lookup_node)
    graph.add_node("final_check", final_check_node)
    graph.add_conditional_edges(
        START,
        route_input,
        {"ocr": "ocr", "extract": "extract"},
    )
    graph.add_edge("ocr", "extract")
    graph.add_edge("extract", "retrieve")
    graph.add_edge("retrieve", "verify")
    graph.add_edge("verify", "kg_lookup")
    graph.add_edge("kg_lookup", "final_check")
    graph.add_edge("final_check", END)
    return graph.compile()


_WORKFLOW = None


def get_workflow():
    global _WORKFLOW
    if _WORKFLOW is None:
        _WORKFLOW = build_workflow()
    return _WORKFLOW


def run_workflow(**state):
    prescription = state.get("prescription")
    if prescription is not None and hasattr(prescription, "model_dump"):
        state = dict(state)
        state["prescription"] = prescription.model_dump()
    return get_workflow().invoke(state)
