from typing import List


def compute_metrics(rows: List[dict]) -> dict:
    n_cases = len(rows)
    n_correct = sum(1 for row in rows if row["predicted"] == row["expected"])
    accuracy = n_correct / n_cases if n_cases else 0.0
    return {
        "n_cases": n_cases,
        "n_correct": n_correct,
        "accuracy": round(accuracy, 4),
        "cases": rows,
    }
