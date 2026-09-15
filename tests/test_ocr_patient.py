from rx_strategist.presentation.ocr_patient import (
    format_conditions,
    parse_patient_from_ocr,
    patient_fields_from_extraction,
)


class _Patient:
    def __init__(self, age=None, conditions=None):
        self.age = age
        self.conditions = conditions or []


class _Extracted:
    def __init__(self, patient):
        self.patient = patient


def test_parse_age_and_conditions_from_ocr():
    text = "Patient: Jane Doe\nAge: 42 years\nConditions: dry eye, bacterial conjunctivitis\nRx: Ciplox"
    parsed = parse_patient_from_ocr(text)
    assert parsed["age"] == 42
    assert parsed["conditions"] == ["dry eye", "bacterial conjunctivitis"]


def test_parse_years_old_pattern():
    parsed = parse_patient_from_ocr("55 years old, male")
    assert parsed["age"] == 55


def test_parse_empty_text():
    parsed = parse_patient_from_ocr("   ")
    assert parsed["age"] is None
    assert parsed["conditions"] == []


def test_extraction_prefers_structured_age():
    extracted = _Extracted(_Patient(age=61, conditions=["hypertension"]))
    fields = patient_fields_from_extraction(extracted, "Age: 10 years")
    assert fields["age"] == 61
    assert fields["conditions"] == ["hypertension"]


def test_extraction_falls_back_to_ocr():
    extracted = _Extracted(_Patient(age=0, conditions=[]))
    fields = patient_fields_from_extraction(extracted, "Age: 38 yrs\nDiagnosis: glaucoma")
    assert fields["age"] == 38
    assert "glaucoma" in fields["conditions"]


def test_format_conditions():
    assert format_conditions(["dry eye", " allergy "]) == "dry eye, allergy"
