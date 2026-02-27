"""
run_pipeline.py
================
FULL 3-PILLAR TRADEMARK ASSESSMENT RUNNER
==========================================
Paste your trademark application data into MY_APPLICATION below.
Then run: python run_pipeline.py

DO NOT modify main.py, tmep_1401_assessor.py, or any other file.
This is the only file you need to edit.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tmep_1403_pillar3 import run_full_pipeline


# ═══════════════════════════════════════════════════════════════════════════════
#  ✏️  PASTE YOUR APPLICATION DATA HERE
#  Change any field below to match your actual trademark application.
# ═══════════════════════════════════════════════════════════════════════════════

MY_APPLICATION = {

    # ── Basic Info ─────────────────────────────────────────────────────────────
    "applicant_name":      "TechVista Solutions Inc.",
    "mark_text":           "NEXAFLOW",
    "mark_type":           "standard_character",   # standard_character | special_form | sound
    "filing_date":         "2024-09-15",           # YYYY-MM-DD
    "nice_edition_claimed": "12th",                # 8th | 9th | 10th | 11th | 12th
    "application_serial":  "97/445001",            # optional
    "filing_type":         "TEAS_PLUS",            # TEAS_PLUS=$250 | TEAS_STANDARD=$350 | PAPER=$750

    # ── Fees ───────────────────────────────────────────────────────────────────
    "fees_paid_count":     3,       # ← number of class fees actually submitted
    "total_fee_paid":      750.0,   # ← total $ submitted

    # ── Amendment / Division / Surrender (set True only if applicable) ─────────
    "amendment_requested":       False,
    "amendment_affects_classes": [],       # e.g. [9, 42] — which classes the amendment touches
    "amendment_description":     "",       # brief description of what is being amended

    "division_requested":        False,
    "classes_to_divide_out":     [],       # e.g. [9] — classes to split into own application

    "surrender_requested":       False,    # only relevant post-registration
    "classes_to_surrender":      [],       # e.g. [25]
    "post_filing_action_type":   "",       # "amendment" | "response" | "sou" | ""

    # ── Classes ────────────────────────────────────────────────────────────────
    # Add one block per class. Copy and paste more blocks as needed.
    "classes": [

        # ── CLASS 1 ────────────────────────────────────────────────────────────
        {
            "class_number":   9,
            "identification": "Downloadable software for project management and team collaboration; "
                              "downloadable mobile applications for task tracking",

            # Specimen — what you submitted to USPTO to prove actual use
            "specimen_type":        "website screenshot",
            "specimen_description": "Screenshot of website showing downloadable software "
                                    "product for sale with mark displayed",

            "fee_paid":                    True,
            "filing_basis":                "1(a)",     # 1(a)=in use | 1(b)=intent to use
            "date_of_first_use":           "2022-03-01",
            "date_of_first_use_commerce":  "2022-04-15"
        },

        # ── CLASS 2 ────────────────────────────────────────────────────────────
        {
            "class_number":   42,
            "identification": "Software as a service featuring software for project management; "
                              "cloud computing services for others; "
                              "technical consulting in the field of software development",

            "specimen_type":        "screenshot of service",
            "specimen_description": "Screenshot of SaaS service page with mark displayed",

            "fee_paid":                    True,
            "filing_basis":                "1(a)",
            "date_of_first_use":           "2022-05-01",
            "date_of_first_use_commerce":  "2022-06-01"
        },

        # ── CLASS 3 ────────────────────────────────────────────────────────────
        {
            "class_number":   35,
            "identification": "Online marketplace services featuring software products; "
                              "business management consulting services for others",

            "specimen_type":        "advertisement",
            "specimen_description": "Online advertisement for consulting services with mark",

            "fee_paid":                    True,
            "filing_basis":                "1(a)",
            "date_of_first_use":           "2022-07-01",
            "date_of_first_use_commerce":  "2022-07-15"
        },

        # ── ADD MORE CLASSES: copy the block above and change the values ───────
    ]
}


# ═══════════════════════════════════════════════════════════════════════════════
# RUN — Do not edit below this line
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "█" * 75)
    print("  TMEP FULL PIPELINE — PILLAR 1 + PILLAR 2 + PILLAR 3")
    print("  TMEP November 2025 Edition | 12th Nice Agreement Edition")
    print("█" * 75)

    result = run_full_pipeline(MY_APPLICATION)

    # ── Print Pillar 1 report ────────────────────────────────────────────────
    print("\n" + "═" * 75)
    print("  PILLAR 1 REPORT (§1401 Classification)")
    print("═" * 75)
    if result.get("pillar1"):
        print(result["pillar1"].get("report", "(no report)"))

    # ── Print Pillar 2 report ────────────────────────────────────────────────
    print("\n" + "═" * 75)
    print("  PILLAR 2 REPORT (§1402 Identification per Class)")
    print("═" * 75)
    try:
        from tmep_1402_pillar2 import print_pillar2_report
        for cls_num, p2 in result.get("pillar2", {}).items():
            print_pillar2_report(p2, class_number=cls_num)
    except Exception as e:
        print(f"  (Pillar 2 report unavailable: {e})")

    # ── Final consolidated verdict ────────────────────────────────────────────
    summary = result.get("summary", {})
    line    = "─" * 70
    total_e = summary.get("total_errors", 0)
    total_w = summary.get("total_warnings", 0)
    overall = "COMPLIANT" if summary.get("overall_compliant") else "REQUIRES CORRECTION"

    print(f"\n{line}")
    print(f"  ASSESSMENT CONCLUSION")
    print(f"  Overall Status:  {overall}")

    if total_e:
        print(f"  {total_e} mandatory error(s) must be resolved before registration.")
    if total_w:
        print(f"  {total_w} advisory item(s) recommended for review.")
    if not total_e and not total_w:
        print(f"  No issues detected across all three assessment pillars.")

    if summary.get("partial_refusal_classes"):
        cls = ", ".join(f"Class {c}" for c in summary["partial_refusal_classes"])
        print(f"\n  Partial Refusal Indicated:  {cls}")

    if summary.get("division_recommended"):
        cls = ", ".join(f"Class {c}" for c in summary["division_eligible_classes"])
        print(f"  Division Recommended:  {cls}")

    print(f"{line}\n")




# """
# run_pipeline.py
# ================
# FULL 3-PILLAR TRADEMARK ASSESSMENT RUNNER
# ==========================================
# Paste your trademark application data into MY_APPLICATION below.
# Then run: python run_pipeline.py

# DO NOT modify main.py, tmep_1401_assessor.py, or any other file.
# This is the only file you need to edit.
# """

# import sys
# import os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from tmep_1403_pillar3 import run_full_pipeline


# # ═══════════════════════════════════════════════════════════════════════════════
# #  ✏️  PASTE YOUR APPLICATION DATA HERE
# #  Change any field below to match your actual trademark application.
# # ═══════════════════════════════════════════════════════════════════════════════

# MY_APPLICATION = {

#     # ── Basic Info ─────────────────────────────────────────────────────────────
#     "applicant_name":      "TechVista Solutions Inc.",
#     "mark_text":           "NEXAFLOW",
#     "mark_type":           "standard_character",   # standard_character | special_form | sound
#     "filing_date":         "2024-09-15",           # YYYY-MM-DD
#     "nice_edition_claimed": "12th",                # 8th | 9th | 10th | 11th | 12th
#     "application_serial":  "97/445001",            # optional
#     "filing_type":         "TEAS_PLUS",            # TEAS_PLUS=$250 | TEAS_STANDARD=$350 | PAPER=$750

#     # ── Fees ───────────────────────────────────────────────────────────────────
#     "fees_paid_count":     3,       # ← number of class fees actually submitted
#     "total_fee_paid":      750.0,   # ← total $ submitted

#     # ── Amendment / Division / Surrender (set True only if applicable) ─────────
#     "amendment_requested":       False,
#     "amendment_affects_classes": [],       # e.g. [9, 42] — which classes the amendment touches
#     "amendment_description":     "",       # brief description of what is being amended

#     "division_requested":        False,
#     "classes_to_divide_out":     [],       # e.g. [9] — classes to split into own application

#     "surrender_requested":       False,    # only relevant post-registration
#     "classes_to_surrender":      [],       # e.g. [25]
#     "post_filing_action_type":   "",       # "amendment" | "response" | "sou" | ""

#     # ── Classes ────────────────────────────────────────────────────────────────
#     # Add one block per class. Copy and paste more blocks as needed.
#     "classes": [

#         # ── CLASS 1 ────────────────────────────────────────────────────────────
#         {
#             "class_number":   9,
#             "identification": "Downloadable software for project management and team collaboration; "
#                               "downloadable mobile applications for task tracking",

#             # Specimen — what you submitted to USPTO to prove actual use
#             "specimen_type":        "website screenshot",
#             "specimen_description": "Screenshot of website showing downloadable software "
#                                     "product for sale with mark displayed",

#             "fee_paid":                    True,
#             "filing_basis":                "1(a)",     # 1(a)=in use | 1(b)=intent to use
#             "date_of_first_use":           "2022-03-01",
#             "date_of_first_use_commerce":  "2022-04-15"
#         },

#         # ── CLASS 2 ────────────────────────────────────────────────────────────
#         {
#             "class_number":   42,
#             "identification": "Software as a service featuring software for project management; "
#                               "cloud computing services for others; "
#                               "technical consulting in the field of software development",

#             "specimen_type":        "screenshot of service",
#             "specimen_description": "Screenshot of SaaS service page with mark displayed",

#             "fee_paid":                    True,
#             "filing_basis":                "1(a)",
#             "date_of_first_use":           "2022-05-01",
#             "date_of_first_use_commerce":  "2022-06-01"
#         },

#         # ── CLASS 3 ────────────────────────────────────────────────────────────
#         {
#             "class_number":   35,
#             "identification": "Online marketplace services featuring software products; "
#                               "business management consulting services for others",

#             "specimen_type":        "advertisement",
#             "specimen_description": "Online advertisement for consulting services with mark",

#             "fee_paid":                    True,
#             "filing_basis":                "1(a)",
#             "date_of_first_use":           "2022-07-01",
#             "date_of_first_use_commerce":  "2022-07-15"
#         },

#         # ── ADD MORE CLASSES: copy the block above and change the values ───────
#     ]
# }


# # ═══════════════════════════════════════════════════════════════════════════════
# # RUN — Do not edit below this line
# # ═══════════════════════════════════════════════════════════════════════════════

# if __name__ == "__main__":
#     print("\n" + "█" * 75)
#     print("  TMEP FULL PIPELINE — PILLAR 1 + PILLAR 2 + PILLAR 3")
#     print("  TMEP November 2025 Edition | 12th Nice Agreement Edition")
#     print("█" * 75)

#     result = run_full_pipeline(MY_APPLICATION)

#     # ── Print Pillar 1 report ────────────────────────────────────────────────
#     print("\n" + "═" * 75)
#     print("  PILLAR 1 REPORT (§1401 Classification)")
#     print("═" * 75)
#     if result.get("pillar1"):
#         print(result["pillar1"].get("report", "(no report)"))

#     # ── Print Pillar 2 report ────────────────────────────────────────────────
#     print("\n" + "═" * 75)
#     print("  PILLAR 2 REPORT (§1402 Identification per Class)")
#     print("═" * 75)
#     try:
#         from tmep_1402_pillar2 import print_pillar2_report
#         for cls_num, p2 in result.get("pillar2", {}).items():
#             print_pillar2_report(p2, class_number=cls_num)
#     except Exception as e:
#         print(f"  (Pillar 2 report unavailable: {e})")

#     # ── Pillar 3 already printed inside run_full_pipeline() ─────────────────
#     print("\n" + "═" * 75)
#     print("  COMBINED SUMMARY — ALL 3 PILLARS")
#     print("═" * 75)
#     summary = result.get("summary", {})
#     overall = "✅ COMPLIANT" if summary.get("overall_compliant") else "🔴 REQUIRES CORRECTION"
#     print(f"  Overall Status   : {overall}")
#     print(f"  Pillar 1 Errors  : {summary.get('pillar1_errors', 0)}")
#     print(f"  Pillar 1 Warnings: {summary.get('pillar1_warnings', 0)}")
#     print(f"  Pillar 2 Errors  : {summary.get('pillar2_errors', 0)}")
#     print(f"  Pillar 2 Warnings: {summary.get('pillar2_warnings', 0)}")
#     print(f"  Pillar 3 Errors  : {summary.get('pillar3_errors', 0)}")
#     print(f"  Pillar 3 Warnings: {summary.get('pillar3_warnings', 0)}")
#     print(f"  ─────────────────────────────────")
#     print(f"  Total Errors     : {summary.get('total_errors', 0)}")
#     print(f"  Total Warnings   : {summary.get('total_warnings', 0)}")

#     if summary.get("partial_refusal_classes"):
#         print(f"\n  🚨 Partial Refusal Classes : "
#               f"{', '.join(f'Class {c}' for c in summary['partial_refusal_classes'])}")

#     if summary.get("division_recommended"):
#         print(f"\n  📂 Division Recommended for : "
#               f"{', '.join(f'Class {c}' for c in summary['division_eligible_classes'])}")

#     print()