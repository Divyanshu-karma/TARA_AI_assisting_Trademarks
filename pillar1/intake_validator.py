def validate_structural_integrity(app_dict):

    errors = []

    if not app_dict.get("application_serial"):
        errors.append("Missing serial number.")

    if not app_dict.get("filing_date"):
        errors.append("Missing filing date.")

    if not app_dict.get("mark_text"):
        errors.append("Missing mark literal element.")

    if app_dict.get("mark_type") == "unknown":
        errors.append("Unrecognized mark type.")

    if app_dict.get("total_fee_paid", 0) <= 0:
        errors.append("Fee not properly extracted.")

    if not app_dict.get("classes"):
        errors.append("No classes detected.")

    for cls in app_dict.get("classes", []):
        if not cls.get("identification"):
            errors.append(f"Class {cls.get('class_number')} missing identification.")

    return errors