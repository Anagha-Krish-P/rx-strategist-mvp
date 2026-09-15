import math
import re
from collections import Counter
from typing import List, Optional, Sequence

from rx_strategist.rag.corpus import load_evidence_documents

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def query_from_prescription(prescription: dict) -> str:
    patient = prescription.get("patient", {})
    parts = list(patient.get("conditions", []))
    parts.extend(patient.get("allergies", []))
    kidney = patient.get("kidney_function")
    if kidney:
        parts.append(str(kidney))
        parts.append("kidney")
    for medication in prescription.get("medications", []):
        parts.extend(
            [
                medication.get("drug", ""),
                medication.get("dose", ""),
                medication.get("frequency", ""),
                medication.get("route", ""),
            ]
        )
    parts.extend(["indication", "dosage", "interaction"])
    return " ".join(str(part) for part in parts if part)


def _prescribed_drug_tokens(prescription: dict) -> List[str]:
    tokens = []
    for medication in prescription.get("medications", []) or []:
        drug = str(medication.get("drug") or "")
        for token in TOKEN_RE.findall(drug.lower()):
            if len(token) > 3:
                tokens.append(token)
    return list(dict.fromkeys(tokens))


def _hit_mentions_tokens(hit: dict, tokens: Sequence[str]) -> bool:
    blob = " ".join(
        [
            str(hit.get("id") or ""),
            str(hit.get("title") or ""),
            str(hit.get("text") or ""),
        ]
    ).lower()
    return any(token in blob for token in tokens)


class EvidenceRetriever:
    def __init__(self, documents: Sequence[dict]):
        if not documents:
            raise ValueError("At least one evidence document is required.")
        self.documents = list(documents)
        self._doc_tokens = [tokenize(self._doc_text(doc)) for doc in self.documents]
        self._idf = self._build_idf(self._doc_tokens)
        self._vectors = [
            self._tfidf_vector(tokens, self._idf) for tokens in self._doc_tokens
        ]

    @classmethod
    def from_evidence_dir(cls, evidence_dir: Optional[str] = None) -> "EvidenceRetriever":
        return cls(load_evidence_documents(evidence_dir))

    def retrieve(self, query: str, k: int = 3) -> List[dict]:
        if not query or not query.strip():
            raise ValueError("A retrieval query is required.")
        query_vector = self._tfidf_vector(tokenize(query), self._idf)
        scored = []
        for document, vector in zip(self.documents, self._vectors):
            score = _cosine_similarity(query_vector, vector)
            if score <= 0:
                continue
            scored.append(
                {
                    "id": document["id"],
                    "title": document["title"],
                    "text": document["text"],
                    "score": round(score, 4),
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:k]

    def retrieve_for_prescription(self, prescription: dict, k: int = 3) -> List[dict]:
        queries = [query_from_prescription(prescription)]
        drugs = [
            medication.get("drug", "")
            for medication in prescription.get("medications", [])
            if medication.get("drug")
        ]
        for drug in drugs:
            queries.append(f"{drug} indication dosage")
        for index, drug_a in enumerate(drugs):
            for drug_b in drugs[index + 1 :]:
                queries.append(f"{drug_a} {drug_b} interaction")

        merged = {}
        for query in queries:
            for hit in self.retrieve(query, k=k):
                current = merged.get(hit["id"])
                if current is None or hit["score"] > current["score"]:
                    merged[hit["id"]] = hit
        ranked = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
        tokens = _prescribed_drug_tokens(prescription)
        if not tokens:
            return []
        filtered = [hit for hit in ranked if _hit_mentions_tokens(hit, tokens)]
        return filtered[:k]

    @staticmethod
    def _doc_text(document: dict) -> str:
        return f"{document.get('title', '')} {document.get('text', '')}"

    @staticmethod
    def _build_idf(doc_tokens: Sequence[List[str]]) -> dict:
        n_docs = len(doc_tokens)
        df = Counter()
        for tokens in doc_tokens:
            df.update(set(tokens))
        return {
            term: math.log((n_docs + 1) / (count + 1)) + 1
            for term, count in df.items()
        }

    @staticmethod
    def _tfidf_vector(tokens: Sequence[str], idf: dict) -> Counter:
        tf = Counter(tokens)
        length = float(len(tokens)) or 1.0
        return Counter(
            {
                term: (count / length) * idf.get(term, 0.0)
                for term, count in tf.items()
            }
        )


def _cosine_similarity(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(term, 0.0) for term, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
