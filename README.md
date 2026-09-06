# rx-strategist-mvp

A small prescription verification prototype with two completed stages:

- deterministic indication, dosage, interaction, and prescription verification
- Gemini extraction of structured prescription information

Gemini only extracts and normalizes prescription text. Medical decisions are made by the deterministic verification engine.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Google Colab

The end-to-end flow is demonstrated in `notebooks/rx_strategist_demo.ipynb`. Add `GEMINI_API_KEY` to Colab Secrets, clone the repository, install the requirements, add `src` to `sys.path`, then run the notebook cells.
