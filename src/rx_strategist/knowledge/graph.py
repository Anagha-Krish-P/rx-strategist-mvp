from typing import Dict, List, Optional

from rx_strategist.knowledge.drug_database import DRUG_DATABASE, INTERACTIONS


def _drug_id(name: str) -> str:
    return f"drug:{name.lower()}"


def _condition_id(name: str) -> str:
    return f"condition:{name.lower()}"


class KnowledgeGraph:
    def __init__(self):
        self.nodes: Dict[str, dict] = {}
        self.edges: List[dict] = []

    def add_node(self, node_id: str, node_type: str, **properties) -> dict:
        node = {"id": node_id, "type": node_type}
        node.update(properties)
        self.nodes[node_id] = node
        return node

    def add_edge(self, source: str, target: str, relation: str, **properties) -> dict:
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
        }
        edge.update(properties)
        self.edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[dict]:
        return self.nodes.get(node_id)

    def neighbors(
        self,
        node_id: str,
        relation: Optional[str] = None,
        direction: str = "out",
    ) -> List[dict]:
        matches = []
        for edge in self.edges:
            if relation and edge["relation"] != relation:
                continue
            if direction == "out" and edge["source"] == node_id:
                neighbor = self.nodes.get(edge["target"])
                if neighbor:
                    matches.append({"node": neighbor, "edge": edge})
            elif direction == "in" and edge["target"] == node_id:
                neighbor = self.nodes.get(edge["source"])
                if neighbor:
                    matches.append({"node": neighbor, "edge": edge})
        return matches

    def indications_for(self, drug_name: str) -> List[str]:
        return [
            item["node"]["name"]
            for item in self.neighbors(_drug_id(drug_name), relation="TREATS")
        ]

    def dosage_for(self, drug_name: str, condition: str) -> Optional[dict]:
        for item in self.neighbors(_drug_id(drug_name), relation="HAS_DOSAGE"):
            edge = item["edge"]
            if edge.get("condition") == condition.lower():
                return {
                    "dose": edge["dose"],
                    "frequency": edge["frequency"],
                    "condition": edge["condition"],
                }
        return None

    def interactions_for(self, drug_names: List[str]) -> List[dict]:
        normalized = [name.lower() for name in drug_names]
        seen = set()
        results = []
        for i, drug_a in enumerate(normalized):
            for drug_b in normalized[i + 1 :]:
                pair = tuple(sorted((drug_a, drug_b)))
                if pair in seen:
                    continue
                seen.add(pair)
                for item in self.neighbors(_drug_id(drug_a), relation="INTERACTS_WITH"):
                    if item["node"]["id"] == _drug_id(drug_b):
                        results.append(
                            {
                                "drug_a": drug_a,
                                "drug_b": drug_b,
                                "severity": item["edge"].get("severity"),
                                "reason": item["edge"].get("reason"),
                            }
                        )
        return results

    def context_for_prescription(self, prescription: dict) -> dict:
        medications = prescription.get("medications", [])
        drug_names = [medication["drug"] for medication in medications]
        conditions = prescription.get("patient", {}).get("conditions", [])
        return {
            "drugs": [
                self.get_node(_drug_id(name))
                for name in drug_names
                if self.get_node(_drug_id(name))
            ],
            "conditions": [
                self.get_node(_condition_id(condition))
                for condition in conditions
                if self.get_node(_condition_id(condition))
            ],
            "indications": {
                name: self.indications_for(name) for name in drug_names
            },
            "dosages": {
                f"{medication['drug']}:{condition}": self.dosage_for(
                    medication["drug"], condition
                )
                for medication in medications
                for condition in conditions
            },
            "interactions": self.interactions_for(drug_names),
        }

    @classmethod
    def from_drug_database(cls) -> "KnowledgeGraph":
        graph = cls()
        for drug_name, record in DRUG_DATABASE.items():
            graph.add_node(_drug_id(drug_name), "Drug", name=drug_name)
            for condition in record["indications"]:
                condition_key = _condition_id(condition)
                if condition_key not in graph.nodes:
                    graph.add_node(condition_key, "Condition", name=condition)
                graph.add_edge(
                    _drug_id(drug_name),
                    condition_key,
                    "TREATS",
                )
            for condition, dosage in record["dosages"].items():
                condition_key = _condition_id(condition)
                if condition_key not in graph.nodes:
                    graph.add_node(condition_key, "Condition", name=condition)
                graph.add_edge(
                    _drug_id(drug_name),
                    condition_key,
                    "HAS_DOSAGE",
                    condition=condition,
                    dose=dosage["dose"],
                    frequency=dosage["frequency"],
                )
        seen_pairs = set()
        for drug_a, partners in INTERACTIONS.items():
            graph.add_node(_drug_id(drug_a), "Drug", name=drug_a)
            for drug_b, details in partners.items():
                pair = tuple(sorted((drug_a, drug_b)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                graph.add_node(_drug_id(drug_b), "Drug", name=drug_b)
                graph.add_edge(
                    _drug_id(drug_a),
                    _drug_id(drug_b),
                    "INTERACTS_WITH",
                    severity=details.get("severity"),
                    reason=details.get("reason"),
                )
                graph.add_edge(
                    _drug_id(drug_b),
                    _drug_id(drug_a),
                    "INTERACTS_WITH",
                    severity=details.get("severity"),
                    reason=details.get("reason"),
                )
        return graph
