# pillar3/assessor.py

from typing import List, Dict
from pillar3.models import *


class Pillar3Assessor:

    USPTO_FEES = {
        "TEAS_PLUS": 250,
        "TEAS_STANDARD": 350,
        "PAPER": 750
    }

    def __init__(self, classes: List[ClassSummary],
                 ctx: MultiClassApplicationContext):
        self.classes = classes
        self.ctx = ctx
        self.findings: List[Pillar3Finding] = []
        self.fee_alignment_status = "aligned"   


    def run(self) -> Pillar3AssessmentResult:

        if len(self.classes) < 2:
            return Pillar3AssessmentResult(
                findings=[],
                partial_refusal_classes=[],
                division_eligible_classes=[],
                total_errors=0,
                total_warnings=0,
                is_multi_class_compliant=True,
                fee_alignment_status="aligned"         # ← FIX: hardcode here (no checks run)
            )

        refusal = self._check_partial_refusal()
        division = self._check_division()
        self._check_fee_alignment()                    # sets self.fee_alignment_status
        self._check_specimen_and_dates()

        errors   = sum(1 for f in self.findings if f.severity == "ERROR")
        warnings = sum(1 for f in self.findings if f.severity == "WARNING")

        return Pillar3AssessmentResult(
            findings=self.findings,
            partial_refusal_classes=refusal,
            division_eligible_classes=division,
            total_errors=errors,
            total_warnings=warnings,
            is_multi_class_compliant=(errors == 0),
            fee_alignment_status=self.fee_alignment_status  # ← ADD THIS LINE
        )
    # ===============================
    # §1403.04 — Partial Refusal
    # ===============================

    def _check_partial_refusal(self):

        refusal_classes = []

        for cls in self.classes:
            if cls.has_any_error():
                refusal_classes.append(cls.class_number)

                reasons = cls.p1_error_messages[:1] + cls.p2_error_messages[:1]

                self.findings.append(Pillar3Finding(
                    "§1403.04",
                    "ERROR",
                    cls.class_number,
                    f"Class {cls.class_number} subject to partial refusal. "
                    f"Reasons: {'; '.join(reasons)}",
                    "Issue partial refusal limited to this class."
                ))

        return refusal_classes

    # ===============================
    # §1403.03 — Division Logic
    # ===============================

    def _check_division(self):

        clean = [c.class_number for c in self.classes if not c.has_any_error()]
        error = [c.class_number for c in self.classes if c.has_any_error()]

        if clean and error:
            self.findings.append(Pillar3Finding(
                "§1403.03",
                "WARNING",
                0,
                f"Division recommended. Clean: {clean}, Problematic: {error}",
                "Consider dividing clean classes to proceed independently."
            ))
            return clean

        return []

    # ===============================
    # §1403.01 — Fee Check
    # ===============================
    
def _check_fee_alignment(self):
    expected = len(self.classes)
    paid = self.ctx.fees_paid_count
    if paid != expected:
        self.fee_alignment_status = "misaligned"   # ← KEEP
        self.findings.append(Pillar3Finding(        # ← FIX: was Pillar3Finding(...)
            "§1403.01",
            "ERROR",
            0,
            f"Fee mismatch. Paid: {paid}, Classes: {expected}",
            f"Submit {expected - paid} additional class fee(s)."
        ))
    else:
        self.fee_alignment_status = "aligned"       # ← KEEP

    # ===============================
    # §1403.01 — Specimen & Dates
    # ===============================

    def _check_specimen_and_dates(self):

        for cls in self.classes:

            if cls.is_use_based():

                if not cls.specimen_type:
                    self.findings.append(Pillar3Finding(
                        "§1403.01",
                        "ERROR",
                        cls.class_number,
                        "Missing specimen for use-based class.",
                        "Submit acceptable specimen."
                    ))

                if not cls.date_of_first_use or not cls.date_of_first_use_commerce:
                    self.findings.append(Pillar3Finding(
                        "§1403.01",
                        "WARNING",
                        cls.class_number,
                        "Missing dates of use.",
                        "Provide first use dates."
                    ))










# # pillar3/assessor.py

# from typing import List, Dict
# from pillar3.models import *


# class Pillar3Assessor:

#     USPTO_FEES = {
#         "TEAS_PLUS": 250,
#         "TEAS_STANDARD": 350,
#         "PAPER": 750
#     }

#     def __init__(self, classes: List[ClassSummary],
#                  ctx: MultiClassApplicationContext):
#         self.classes = classes
#         self.ctx = ctx
#         self.findings: List[Pillar3Finding] = []
#         self.fee_alignment_status = "aligned"   

#     # def run(self) -> Pillar3AssessmentResult:

#     #     if len(self.classes) < 2:
#     #         return Pillar3AssessmentResult(
#     #             findings=[],
#     #             partial_refusal_classes=[],
#     #             division_eligible_classes=[],
#     #             total_errors=0,
#     #             total_warnings=0,
#     #             is_multi_class_compliant=True
#     #             fee_alignment_status = self.fee_alignment_status
#     #         )

#     #     refusal = self._check_partial_refusal()
#     #     division = self._check_division()
#     #     self._check_fee_alignment()
#     #     self._check_specimen_and_dates()

#     #     errors = sum(1 for f in self.findings if f.severity == "ERROR")
#     #     warnings = sum(1 for f in self.findings if f.severity == "WARNING")

#     #     return Pillar3AssessmentResult(
#     #         findings=self.findings,
#     #         partial_refusal_classes=refusal,
#     #         division_eligible_classes=division,
#     #         total_errors=errors,
#     #         total_warnings=warnings,
#     #         is_multi_class_compliant=(errors == 0)
#     #     )
#     def run(self) -> Pillar3AssessmentResult:

#         if len(self.classes) < 2:
#             return Pillar3AssessmentResult(
#                 findings=[],
#                 partial_refusal_classes=[],
#                 division_eligible_classes=[],
#                 total_errors=0,
#                 total_warnings=0,
#                 is_multi_class_compliant=True,
#                 fee_alignment_status="aligned"         # ← FIX: hardcode here (no checks run)
#             )

#         refusal = self._check_partial_refusal()
#         division = self._check_division()
#         self._check_fee_alignment()                    # sets self.fee_alignment_status
#         self._check_specimen_and_dates()

#         errors   = sum(1 for f in self.findings if f.severity == "ERROR")
#         warnings = sum(1 for f in self.findings if f.severity == "WARNING")

#         return Pillar3AssessmentResult(
#             findings=self.findings,
#             partial_refusal_classes=refusal,
#             division_eligible_classes=division,
#             total_errors=errors,
#             total_warnings=warnings,
#             is_multi_class_compliant=(errors == 0),
#             fee_alignment_status=self.fee_alignment_status  # ← ADD THIS LINE
#         )
#     # ===============================
#     # §1403.04 — Partial Refusal
#     # ===============================

#     def _check_partial_refusal(self):

#         refusal_classes = []

#         for cls in self.classes:
#             if cls.has_any_error():
#                 refusal_classes.append(cls.class_number)

#                 reasons = cls.p1_error_messages[:1] + cls.p2_error_messages[:1]

#                 self.findings.append(Pillar3Finding(
#                     "§1403.04",
#                     "ERROR",
#                     cls.class_number,
#                     f"Class {cls.class_number} subject to partial refusal. "
#                     f"Reasons: {'; '.join(reasons)}",
#                     "Issue partial refusal limited to this class."
#                 ))

#         return refusal_classes

#     # ===============================
#     # §1403.03 — Division Logic
#     # ===============================

#     def _check_division(self):

#         clean = [c.class_number for c in self.classes if not c.has_any_error()]
#         error = [c.class_number for c in self.classes if c.has_any_error()]

#         if clean and error:
#             self.findings.append(Pillar3Finding(
#                 "§1403.03",
#                 "WARNING",
#                 0,
#                 f"Division recommended. Clean: {clean}, Problematic: {error}",
#                 "Consider dividing clean classes to proceed independently."
#             ))
#             return clean

#         return []

#     # ===============================
#     # §1403.01 — Fee Check
#     # ===============================
    
#     # def _check_fee_alignment(self):

#     #     expected = len(self.classes)
#     #     paid = self.ctx.fees_paid_count

#     #     if paid != expected:
#     #         self.findings.append(Pillar3Finding(
#     #             "§1403.01",
#     #             "ERROR",
#     #             0,
#     #             f"Fee mismatch. Paid: {paid}, Classes: {expected}",
#     #             f"Submit {expected-paid} additional class fee(s)."
#     #         ))
#     # In _check_fee_alignment(), store the status:
#     # def _check_fee_alignment(self):
#     #     expected = len(self.classes)
#     #     paid = self.ctx.fees_paid_count
#     #     if paid != expected:
#     #         self.fee_alignment_status = "misaligned"   # ← store it
#     #         self.findings.append(Pillar3Finding(...))
#     #     else:
#     #         self.fee_alignment_status = "aligned"
# def _check_fee_alignment(self):
#     expected = len(self.classes)
#     paid = self.ctx.fees_paid_count
#     if paid != expected:
#         self.fee_alignment_status = "misaligned"   # ← KEEP
#         self.findings.append(Pillar3Finding(        # ← FIX: was Pillar3Finding(...)
#             "§1403.01",
#             "ERROR",
#             0,
#             f"Fee mismatch. Paid: {paid}, Classes: {expected}",
#             f"Submit {expected - paid} additional class fee(s)."
#         ))
#     else:
#         self.fee_alignment_status = "aligned"       # ← KEEP

#     # ===============================
#     # §1403.01 — Specimen & Dates
#     # ===============================

#     def _check_specimen_and_dates(self):

#         for cls in self.classes:

#             if cls.is_use_based():

#                 if not cls.specimen_type:
#                     self.findings.append(Pillar3Finding(
#                         "§1403.01",
#                         "ERROR",
#                         cls.class_number,
#                         "Missing specimen for use-based class.",
#                         "Submit acceptable specimen."
#                     ))

#                 if not cls.date_of_first_use or not cls.date_of_first_use_commerce:
#                     self.findings.append(Pillar3Finding(
#                         "§1403.01",
#                         "WARNING",
#                         cls.class_number,
#                         "Missing dates of use.",
#                         "Provide first use dates."
#                     ))