# rx-strategist-mvp

A small prescription verification prototype with three completed stages:

- Gemini Vision OCR of prescription images into text
- Gemini extraction of structured prescription information
- deterministic indication, dosage, interaction, and prescription verification

OCR only transcribes visible prescription text. Gemini only extracts and normalizes that text. Medical decisions are made by the deterministic verification engine.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Google Colab

Add `GEMINI_API_KEY` to Colab Secrets, then open one of the demo notebooks:

- `notebooks/rx_strategist_demo.ipynb` — paste prescription text, extract, and verify
- `notebooks/rx_strategist_ocr_demo.ipynb` — OCR a prescription image (bundled sample or your own upload), extract, and verify

Clone the repository, install the requirements, add `src` to `sys.path`, then run the notebook cells.
