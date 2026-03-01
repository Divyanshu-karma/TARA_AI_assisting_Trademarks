# pillar3/service.py

from typing import List
from .models import *
from .assessor import Pillar3Assessor


def build_class_summary(class_dict, p1_findings, p2_result):

    p1_errors = [
        f for f in p1_findings
        if getattr(f, "class_number", None) == class_dict["class_number"]
        and getattr(f, "severity", "") == "ERROR"
    ]

    p2_summary = p2_result.get("summary", {}) if p2_result else {}

    return ClassSummary(
        class_number=class_dict["class_number"],
        class_title=class_dict.get("class_title", ""),
        class_category=class_dict.get("class_category", ""),
        identification=class_dict.get("identification", ""),
        filing_basis=class_dict.get("filing_basis", "1(a)"),
        specimen_type=class_dict.get("specimen_type", ""),
        specimen_description=class_dict.get("specimen_description", ""),
        date_of_first_use=class_dict.get("date_of_first_use"),
        date_of_first_use_commerce=class_dict.get("date_of_first_use_commerce"),
        fee_paid=class_dict.get("fee_paid", True),
        p1_error_count=len(p1_errors),
        p1_error_messages=[getattr(e, "finding", "") for e in p1_errors],
        p2_is_definite=p2_summary.get("is_definite", True),
        p2_error_count=p2_summary.get("errors", 0),
        p2_error_messages=[
            f["finding"]
            for f in p2_result.get("tmep_1402_analysis", {}).get("subsection_findings", [])
            if f.get("severity") == "ERROR"
        ] if p2_result else []
    )


def run_pillar3(application_dict: dict,
                p1_output: dict,
                p2_output: dict):

    # ─────────────────────────────────────────────
    # BUILD CLASS SUMMARIES
    # ─────────────────────────────────────────────
    class_summaries: List[ClassSummary] = []

    for cls in application_dict.get("classes", []):
        class_number = cls.get("class_number")
        p2_result = p2_output.get(class_number)

        summary = build_class_summary(
            class_dict=cls,
            p1_findings=p1_output.get("findings", []),
            p2_result=p2_result
        )

        class_summaries.append(summary)

    # ─────────────────────────────────────────────
    # BUILD APPLICATION CONTEXT
    # ─────────────────────────────────────────────
    # app_context = MultiClassApplicationContext(
    #     applicant_name=application_dict.get("applicant_name", ""),
    #     mark_text=application_dict.get("mark_text", ""),
    #     filing_date=application_dict.get("filing_date", ""),
    #     filing_type=application_dict.get("filing_type", "TEAS_PLUS"),
    #     fees_paid_count=application_dict.get("fees_paid_count", 0),
    #     total_fee_paid=application_dict.get("total_fee_paid", 0.0)
    # )
    app_context = MultiClassApplicationContext(
        filing_type=application_dict.get("filing_type", "TEAS_PLUS"),
        fees_paid_count=application_dict.get("fees_paid_count", 0),
        total_fee_paid=application_dict.get("total_fee_paid", 0.0)
    )
    # ─────────────────────────────────────────────
    # RUN ASSESSOR
    # ─────────────────────────────────────────────
    assessor = Pillar3Assessor(class_summaries, app_context)
    return assessor.run()



# # pillar3/service.py

# from typing import List
# from pillar3.models import *
# from pillar3.assessor import Pillar3Assessor


# def build_class_summary(class_dict, p1_findings, p2_result):

#     p1_errors = [f for f in p1_findings
#                  if getattr(f, "class_number", None) == class_dict["class_number"]
#                  and getattr(f, "severity", "") == "ERROR"]

#     p2_summary = p2_result.get("summary", {}) if p2_result else {}

#     return ClassSummary(
#         class_number=class_dict["class_number"],
#         class_title=class_dict.get("class_title", ""),
#         class_category=class_dict.get("class_category", ""),
#         identification=class_dict.get("identification", ""),
#         filing_basis=class_dict.get("filing_basis", "1(a)"),
#         specimen_type=class_dict.get("specimen_type", ""),
#         specimen_description=class_dict.get("specimen_description", ""),
#         date_of_first_use=class_dict.get("date_of_first_use"),
#         date_of_first_use_commerce=class_dict.get("date_of_first_use_commerce"),
#         fee_paid=class_dict.get("fee_paid", True),
#         p1_error_count=len(p1_errors),
#         p1_error_messages=[getattr(e, "finding", "") for e in p1_errors],
#         p2_is_definite=p2_summary.get("is_definite", True),
#         p2_error_count=p2_summary.get("errors", 0),
#         p2_error_messages=[
#             f["finding"] for f in p2_result.get("findings", [])
#             if f["severity"] == "ERROR"
#         ] if p2_result else []
#     )


# def run_pillar3(class_summaries: List[ClassSummary],
#                 app_context: MultiClassApplicationContext):

#     assessor = Pillar3Assessor(class_summaries, app_context)
#     return assessor.run()