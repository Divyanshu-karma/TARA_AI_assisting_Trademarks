# pillar1/service.py

from typing import Dict, Any
from .tmep_1401_assessor import (
    TMEP1401Assessor,
    TrademarkApplication,
    ClassEntry
)
from .tmep_1401_report import TMEP1401ReportGenerator


# =========================================================
# JSON → TrademarkApplication
# =========================================================

def _parse_application(app_dict: Dict[str, Any]) -> TrademarkApplication:

    class_entries = []

    for cls in app_dict.get("classes", []):
        entry = ClassEntry(
            class_number=int(cls.get("class_number", 0)),
            identification=cls.get("identification", ""),
            specimen_type=cls.get("specimen_type", ""),
            specimen_description=cls.get("specimen_description", ""),
            fee_paid=cls.get("fee_paid", True),
            filing_basis=cls.get("filing_basis", "1a"),
            date_of_first_use=cls.get("date_of_first_use"),
            date_of_first_use_commerce=cls.get("date_of_first_use_commerce"),
        )
        class_entries.append(entry)

    return TrademarkApplication(
        applicant_name=app_dict.get("applicant_name", ""),
        mark_text=app_dict.get("mark_text", ""),
        mark_type=app_dict.get("mark_type", "standard_character"),
        filing_date=app_dict.get("filing_date", ""),
        nice_edition_claimed=app_dict.get("nice_edition_claimed", "12th"),
        application_serial=app_dict.get("application_serial", ""),
        filing_type=app_dict.get("filing_type", "TEAS_PLUS"),
        classes=class_entries,
        fees_paid_count=int(app_dict.get("fees_paid_count", 0)),
        total_fee_paid=float(app_dict.get("total_fee_paid", 0.0)),
        is_multi_class=len(class_entries) > 1,
        notes=app_dict.get("notes", "")
    )


# =========================================================
# PUBLIC ENTRY
# =========================================================

def run_pillar1(application_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consumes structured JSON from inputLayer.
    Returns exact contract required by PipelineState.
    """

    application = _parse_application(application_dict)

    assessor = TMEP1401Assessor(application)
    findings = assessor.run_full_assessment()

    reporter = TMEP1401ReportGenerator(application, findings)
    report = reporter.generate_full_report()

    summary = {
        "total": len(findings),
        "errors": sum(1 for f in findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in findings if f.severity == "WARNING"),
        "info": sum(1 for f in findings if f.severity == "INFO"),
        "ok": sum(1 for f in findings if f.severity == "OK"),
    }

    return {
        "application": application,
        "findings": findings,
        "report": report,
        "summary": summary
    }