from main import assess_trademark_application

sample = {
    "applicant_name": "Test Corp",
    "mark_text": "TESTMARK",
    "mark_type": "standard_character",
    "filing_date": "2024-01-01",
    "nice_edition_claimed": "12th",
    "application_serial": "99/123456",
    "filing_type": "TEAS_PLUS",
    "fees_paid_count": 1,
    "total_fee_paid": 250.0,
    "notes": "",
    "classes": [
        {
            "class_number": 9,
            "identification": "Downloadable software for financial management",
            "specimen_type": "",
            "specimen_description": "",
            "fee_paid": True,
            "filing_basis": "1(a)",
            "date_of_first_use": "",
            "date_of_first_use_commerce": ""
        }
    ]
}

result = assess_trademark_application(sample)

print(result["report"])
print("\nSummary:", result["summary"])