# Dosage guardrails

Verification compares the prescribed dose and frequency with the demo knowledge base.

Losartan hypertension: 50 mg once daily.
Metformin type 2 diabetes: 500 mg twice daily.

If the prescribed dose or frequency does not match the recommended values,
the dosage check returns REVIEW even when the indication matches.
Unknown drugs also require REVIEW because they are missing from the knowledge base.
