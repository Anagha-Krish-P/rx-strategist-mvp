from pathlib import Path
from typing import List, Optional

EVIDENCE_DIR = Path(__file__).resolve().parents[3] / "data" / "evidence"


def load_evidence_documents(evidence_dir: Optional[Path] = None) -> List[dict]:
    directory = Path(evidence_dir) if evidence_dir else EVIDENCE_DIR
    if not directory.is_dir():
        raise FileNotFoundError(f"Evidence directory not found: {directory}")

    documents = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        title = path.stem.replace("_", " ").title()
        if text.startswith("# "):
            title = text.split("\n", 1)[0][2:].strip()
        documents.append(
            {
                "id": path.stem,
                "title": title,
                "text": text,
                "path": str(path),
            }
        )
    if not documents:
        raise ValueError(f"No evidence documents found in {directory}")
    return documents
