# rx-strategist-mvp

A small prescription verification prototype with six stages:

1. Gemini Vision OCR of prescription images into text
2. Gemini extraction of structured prescription information
3. RAG retrieval of demo medical evidence
4. A knowledge graph of drugs, diagnoses, dosages, and interactions
5. A LangGraph workflow that orchestrates those stages
6. A final checker plus a gold-set evaluation harness

OCR only transcribes visible prescription text. Gemini only extracts and normalizes that text. Medical decisions are made by the deterministic verification engine. RAG, the knowledge graph, and the final checker attach supporting context; they do not override `APPROPRIATE` or `REVIEW`.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Google Colab

Add `GEMINI_API_KEY` to Colab Secrets when a notebook uses OCR or extraction, then open one of the demos:

- `notebooks/rx_strategist_demo.ipynb` — paste prescription text, extract, and verify
- `notebooks/rx_strategist_ocr_demo.ipynb` — OCR a prescription image, extract, and verify
- `notebooks/rx_strategist_pipeline_demo.ipynb` — RAG, knowledge graph, LangGraph workflow, final checker, and evaluation (Gemini optional)
- `notebooks/rx_strategist_ocr_pipeline_demo.ipynb` — OCR a prescription image, then run the full LangGraph pipeline (Gemini required)

Clone the repository, install the requirements, add `src` to `sys.path`, then run the notebook cells.
