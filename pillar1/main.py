"""
main.py
========
PILLAR 1 ENTRY POINT — TMEP §1401 Classification Engine
Production-Safe Version
"""

from typing import Dict, Any, List

from tmep_1401_assessor import (
    TMEP1401Assessor,
    TrademarkApplication,
    ClassEntry,
)

from tmep_1401_report import TMEP1401ReportGenerator
from intake_validator import validate_structural_integrity


# =========================================================
# SAFE TYPE HELPERS
# =========================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# =========================================================
# PARSE STRUCTURED JSON → DATACLASS MODEL
# =========================================================

def parse_application(app_dict: Dict[str, Any]) -> TrademarkApplication:

    class_entries: List[ClassEntry] = []

    for cls in app_dict.get("classes", []):

        class_number = safe_int(cls.get("class_number"))

        entry = ClassEntry(
            class_number=class_number,
            identification=str(cls.get("identification", "")).strip(),
            specimen_type=str(cls.get("specimen_type", "")).strip(),
            specimen_description=str(cls.get("specimen_description", "")).strip(),
            fee_paid=bool(cls.get("fee_paid", True)),
            filing_basis=str(cls.get("filing_basis", "")).strip(),
            date_of_first_use=cls.get("date_of_first_use"),
            date_of_first_use_commerce=cls.get("date_of_first_use_commerce"),
        )

        class_entries.append(entry)

    unique_classes = {c.class_number for c in class_entries if c.class_number > 0}

    return TrademarkApplication(
        applicant_name=str(app_dict.get("applicant_name", "")).strip(),
        mark_text=str(app_dict.get("mark_text", "")).strip(),
        mark_type=str(app_dict.get("mark_type", "")).strip(),
        filing_date=str(app_dict.get("filing_date", "")).strip(),
        nice_edition_claimed=str(app_dict.get("nice_edition_claimed", "12th")),
        application_serial=str(app_dict.get("application_serial", "")).strip(),
        filing_type=str(app_dict.get("filing_type", "TEAS_PLUS")),
        classes=class_entries,
        fees_paid_count=safe_int(app_dict.get("fees_paid_count", len(unique_classes))),
        total_fee_paid=safe_float(app_dict.get("total_fee_paid", 0.0)),
        is_multi_class=len(unique_classes) > 1,
        notes=str(app_dict.get("notes", "")),
    )


# =========================================================
# MAIN ENGINE FUNCTION
# =========================================================

def assess_trademark_application(app_dict: Dict[str, Any]) -> Dict[str, Any]:

    structural_errors = validate_structural_integrity(app_dict)

    if structural_errors:
        return {
            "application": None,
            "findings": [],
            "report": "STRUCTURAL INTAKE FAILURE:\n\n" + "\n".join(structural_errors),
            "summary": {
                "total": 0,
                "errors": len(structural_errors),
                "warnings": 0,
                "info": 0,
                "ok": 0,
            },
            "has_errors": True,
            "has_warnings": False,
        }

    application = parse_application(app_dict)

    # Fee-to-class reconciliation
    unique_class_count = len({c.class_number for c in application.classes})
    if application.fees_paid_count != unique_class_count:
        return {
            "application": application,
            "findings": [],
            "report": (
                "STRUCTURAL INTAKE FAILURE:\n\n"
                "Fee count does not match number of classes."
            ),
            "summary": {
                "total": 1,
                "errors": 1,
                "warnings": 0,
                "info": 0,
                "ok": 0,
            },
            "has_errors": True,
            "has_warnings": False,
        }

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
        "summary": summary,
        "has_errors": summary["errors"] > 0,
        "has_warnings": summary["warnings"] > 0,
    }


# =========================================================
# FULL 3-PILLAR PIPELINE (SAFE VERSION)
# =========================================================

def run_full_pipeline(app_dict):

    p1_result = assess_trademark_application(app_dict)

    # 🚨 STOP PIPELINE IF STRUCTURAL OR P1 ERROR
    if p1_result["has_errors"] and p1_result["application"] is None:
        return {
            "pillar1": p1_result,
            "pillar2": None,
            "pillar3": None,
            "overall_compliant": False,
        }

    from tmep_1402_pillar2 import run_pillar2
    from tmep_1403_pillar3 import run_pillar3

    p2_result = run_pillar2(
        p1_result["application"],
        p1_result["findings"],
    )

    p3_result = run_pillar3(
        p1_result["application"],
        p1_result["findings"],
        p2_result,
    )

    overall_compliant = (
        not p1_result["has_errors"]
        and not p3_result.get("has_errors", False)
    )

    return {
        "pillar1": p1_result,
        "pillar2": p2_result,
        "pillar3": p3_result,
        "overall_compliant": overall_compliant,
    }





# # modify new block of code in below code
# """
# main.py
# ========
# PILLAR 1 ENTRY POINT — TMEP §1401 Classification Engine

# Purpose:
# Accept structured trademark application JSON
# Run TMEP1401Assessor
# Return structured result for UI layer

# No CLI.
# No sample data.
# No test harness.
# Pure engine adapter.
# """

# from typing import Dict, Any

# from tmep_1401_assessor import (
#     TMEP1401Assessor,
#     TrademarkApplication,
#     ClassEntry,
#     AssessmentFinding
# )

# from tmep_1401_report import TMEP1401ReportGenerator


# # =========================================================
# # PARSE STRUCTURED JSON → DATACLASS MODEL
# # =========================================================

# def parse_application(app_dict: Dict[str, Any]) -> TrademarkApplication:
#     """
#     Convert structured JSON into TrademarkApplication object.
#     Expected format matches Adaptive Parser output.
#     """

#     class_entries = []

#     for cls in app_dict.get("classes", []):
#         entry = ClassEntry(
#             class_number=int(cls.get("class_number", 0)),
#             identification=cls.get("identification", ""),
#             specimen_type=cls.get("specimen_type", ""),
#             specimen_description=cls.get("specimen_description", ""),
#             fee_paid=cls.get("fee_paid", True),
#             filing_basis=cls.get("filing_basis", "1(a)"),
#             date_of_first_use=cls.get("date_of_first_use"),
#             date_of_first_use_commerce=cls.get("date_of_first_use_commerce"),
#         )
#         class_entries.append(entry)

#     unique_classes = set(c.class_number for c in class_entries)

#     return TrademarkApplication(
#         applicant_name=app_dict.get("applicant_name", ""),
#         mark_text=app_dict.get("mark_text", ""),
#         mark_type=app_dict.get("mark_type", "standard_character"),
#         filing_date=app_dict.get("filing_date", ""),
#         nice_edition_claimed=app_dict.get("nice_edition_claimed", "12th"),
#         application_serial=app_dict.get("application_serial", ""),
#         filing_type=app_dict.get("filing_type", "TEAS_PLUS"),
#         classes=class_entries,
#         fees_paid_count=int(app_dict.get("fees_paid_count", len(unique_classes))),
#         total_fee_paid=float(app_dict.get("total_fee_paid", 0.0)),
#         is_multi_class=len(unique_classes) > 1,
#         notes=app_dict.get("notes", "")
#     )


# # =========================================================
# # MAIN ENGINE FUNCTION
# # =========================================================

# def assess_trademark_application(app_dict: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Primary entry point used by Streamlit UI.

#     Input:
#         structured trademark JSON

#     Output:
#         {
#             "application": TrademarkApplication,
#             "findings": List[AssessmentFinding],
#             "report": str,
#             "summary": dict,
#             "has_errors": bool,
#             "has_warnings": bool
#         }
#     """

#     # 1️⃣ Parse JSON → dataclass
#     application = parse_application(app_dict)

#     # 2️⃣ Run Pillar 1 assessment
#     assessor = TMEP1401Assessor(application)
#     findings = assessor.run_full_assessment()

#     # 3️⃣ Generate professional legal report
#     reporter = TMEP1401ReportGenerator(application, findings)
#     report = reporter.generate_full_report()

#     # 4️⃣ Build summary
#     summary = {
#         "total": len(findings),
#         "errors": sum(1 for f in findings if f.severity == "ERROR"),
#         "warnings": sum(1 for f in findings if f.severity == "WARNING"),
#         "info": sum(1 for f in findings if f.severity == "INFO"),
#         "ok": sum(1 for f in findings if f.severity == "OK"),
#     }

#     return {
#         "application": application,
#         "findings": findings,
#         "report": report,
#         "summary": summary,
#         "has_errors": summary["errors"] > 0,
#         "has_warnings": summary["warnings"] > 0
#     }

# # =========================================================
# # FULL 3-PILLAR PIPELINE
# # =========================================================

# def run_full_pipeline(app_dict):

#     # ---- PILLAR 1 ----
#     p1_result = assess_trademark_application(app_dict)

#     # ---- PILLAR 2 ----
#     from tmep_1402_pillar2 import run_pillar2
#     p2_result = run_pillar2(p1_result["application"], p1_result["findings"])

#     # ---- PILLAR 3 ----
#     from tmep_1403_pillar3 import run_pillar3
#     p3_result = run_pillar3(
#         p1_result["application"],
#         p1_result["findings"],
#         p2_result
#     )

#     overall_compliant = (
#         not p1_result["has_errors"] and
#         not p3_result.get("has_errors", False)
#     )

#     return {
#         "pillar1": p1_result,
#         "pillar2": p2_result,
#         "pillar3": p3_result,
#         "overall_compliant": overall_compliant
#     }









# # main.py

# from pathlib import Path
# import json

# from src.parsing.parse_tmep_html import parse_tmep_html
# from src.processing.normalize_sections import (
#     normalize_sections,
#     save_normalized_sections
# )


# # ---------------------------------------------
# # Paths
# # ---------------------------------------------

# RAW_HTML_DIR = Path("data/raw/tmep-nov2025-html/TMEP")
# OUTPUT_PATH = Path("data/parsed/tmep_sections.json")


# def main():

#     if not RAW_HTML_DIR.exists():
#         raise FileNotFoundError(f"Raw HTML directory not found: {RAW_HTML_DIR}")

#     all_sections = []

#     # -------------------------------------------------
#     # Iterate through all TMEP HTML files
#     # -------------------------------------------------
#     html_files = sorted(RAW_HTML_DIR.glob("*.html"))

#     print(f"📄 Found {len(html_files)} HTML files")

#     for html_file in html_files:
#         print(f"🔎 Parsing: {html_file.name}")

#         sections = parse_tmep_html(html_file)
#         all_sections.extend(sections)

#     print(f"📦 Total raw sections extracted: {len(all_sections)}")

#     # -------------------------------------------------
#     # Normalize Sections
#     # -------------------------------------------------
#     normalized = normalize_sections(all_sections)

#     print(f"✅ Total normalized sections: {len(normalized)}")

#     # -------------------------------------------------
#     # Save to data/parsed/
#     # -------------------------------------------------
#     save_normalized_sections(normalized, OUTPUT_PATH)

#     print("=" * 60)
#     print(f"💾 Saved normalized sections to: {OUTPUT_PATH}")
#     print("=" * 60)


# if __name__ == "__main__":
#     main()