import os
from google import genai
from google.colab import userdata
from google.genai import types
from rx_strategist.models.prescription import ExtractedPrescription

api_key = userdata.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

SYSTEM_PROMPT = """
You are a prescription information extraction system.

Your job is ONLY to extract structured information
from prescription text.

Do NOT decide whether a medication is appropriate.
Do NOT provide medical advice.
Do NOT invent missing patient information.

If information is missing:
- use an empty list for missing lists
- use "unknown" for unknown fields

Normalize common prescription abbreviations:

OD -> once daily
BD -> twice daily
BID -> twice daily
TID -> three times daily
PO -> oral

Extract only information present in the input.
"""

def extract_prescription(text):
    response = client.models.generate_content(
        model="models/gemini-3.5-flash-lite",
        contents=f"""
{SYSTEM_PROMPT}

Prescription text:

{text}
""",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedPrescription
        )
    )
    return ExtractedPrescription.model_validate_json(
        response.text
    )
