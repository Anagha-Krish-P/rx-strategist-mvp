import json
from pathlib import Path
from typing import List, Optional

CASES_PATH = Path(__file__).resolve().parents[3] / "data" / "evaluation" / "gold_cases.json"


def load_gold_cases(path: Optional[Path] = None) -> List[dict]:
    cases_path = Path(path) if path else CASES_PATH
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if not cases:
        raise ValueError(f"No gold cases found in {cases_path}")
    return cases
