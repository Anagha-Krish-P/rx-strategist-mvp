DRUG_DATABASE = {
    "losartan": {
        "indications": [
            "hypertension",
            "diabetic nephropathy"
        ],
        "dosages": {
            "hypertension": {
                "dose": "50 mg",
                "frequency": "once daily"
            },
            "diabetic nephropathy": {
                "dose": "50 mg",
                "frequency": "once daily"
            }
        }
    },
    "metformin": {
        "indications": [
            "type 2 diabetes"
        ],
        "dosages": {
            "type 2 diabetes": {
                "dose": "500 mg",
                "frequency": "twice daily"
            }
        }
    }
}

INTERACTIONS = {
    "losartan": {
        "metformin": {
            "severity": "example",
            "reason": "Demo interaction record"
        }
    },
    "metformin": {
        "losartan": {
            "severity": "example",
            "reason": "Demo interaction record"
        }
    }
}
