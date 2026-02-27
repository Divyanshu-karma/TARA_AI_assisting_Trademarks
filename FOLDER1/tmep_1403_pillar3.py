"""
TMEP CHAPTER 1403 — COMBINED OR MULTIPLE-CLASS APPLICATIONS
PILLAR 3 ASSESSMENT ENGINE
==============================================================
Based on: TMEP November 2025 Edition

════════════════════════════════════════════════════════════════
  FULL PIPELINE FLOW
════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────┐
  │  PILLAR 1  (tmep_1401_assessor.py)                      │
  │  - Confirms/corrects class numbers                      │
  │  - Validates specimens per class                        │
  │  - Counts fees vs classes                               │
  │  - Flags misclassifications                             │
  │  OUTPUT: TrademarkApplication + List[AssessmentFinding] │
  └──────────────────────────┬──────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  PILLAR 2  (tmep_1402_pillar2.py)                       │
  │  - Checks identification specificity per class          │
  │  - Validates services "for others" format               │
  │  - Flags vague/indefinite terms                         │
  │  - Cross-checks accuracy against specimen               │
  │  OUTPUT: Dict[class_number → TMEP1402AnalysisResult]    │
  └──────────────────────────┬──────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  PILLAR 3  (this file)                                  │
  │  - §1403.01: Multi-class completeness checklist         │
  │  - §1403.02: Amendment scope across classes             │
  │  - §1403.03: Division eligibility analysis              │
  │  - §1403.04: Partial refusal identification             │
  │  - §1403.05: Post-filing fee verification               │
  │  - §1403.06: Surrender/amendment in registrations       │
  │  OUTPUT: Pillar3AssessmentResult (full report)          │
  └─────────────────────────────────────────────────────────┘

HOW PILLARS 1 AND 2 FEED PILLAR 3:
  - Pillar 1 class errors    → §1403.04 partial refusal candidates
  - Pillar 1 fee counts      → §1403.01 fee-per-class verification
  - Pillar 1 specimen checks → §1403.01 per-class specimen requirement
  - Pillar 1 filing_basis    → §1403.01 dates-of-use requirement
  - Pillar 2 is_definite     → §1403.01 per-class identification check
  - Pillar 2 errors          → §1403.04 adds to partial refusal scope
  - Combined P1+P2 status    → §1403.03 division eligibility logic
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ClassStatus(Enum):
    """
    Overall status of a single class in the multi-class application,
    derived from combining Pillar 1 + Pillar 2 findings.
    """
    CLEAN       = "CLEAN"         # No errors or warnings from P1 or P2
    HAS_WARNINGS = "HAS_WARNINGS" # Warnings only — can proceed with amendments
    HAS_ERRORS  = "HAS_ERRORS"    # Errors present — blocked until resolved
    REFUSAL_CANDIDATE = "REFUSAL_CANDIDATE"  # Strong refusal indicators present


class ApplicationStage(Enum):
    """Stage of the application lifecycle."""
    PRE_FILING         = "PRE_FILING"
    FILED_PENDING      = "FILED_PENDING"
    OFFICE_ACTION      = "OFFICE_ACTION"
    STATEMENT_OF_USE   = "STATEMENT_OF_USE"
    REGISTERED         = "REGISTERED"
    POST_REGISTRATION  = "POST_REGISTRATION"


# ═══════════════════════════════════════════════════════════════════════════════
# BRIDGE — Consolidated Per-Class Context from Pillars 1 and 2
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassSummary:
    """
    Single source of truth for one class, consolidating
    Pillar 1 ClassEntry data + Pillar 1 findings + Pillar 2 results.

    Build one ClassSummary per class, then pass the full list to
    Pillar3Assessor.
    """
    # ── Identity (from Pillar 1 ClassEntry) ──────────────────────────────────
    class_number: int
    class_title: str                    # e.g., "Scientific and Electronic Apparatus"
    class_category: str                 # "GOODS" or "SERVICES"
    identification: str                 # The full identification text
    filing_basis: str                   # "1(a)", "1(b)", "44(d)", "44(e)", "66(a)"
    specimen_type: str = ""
    specimen_description: str = ""
    date_of_first_use: Optional[str] = None
    date_of_first_use_commerce: Optional[str] = None
    fee_paid: bool = True

    # ── Pillar 1 Findings Summary ─────────────────────────────────────────────
    p1_error_count: int = 0
    p1_warning_count: int = 0
    p1_error_messages: List[str] = field(default_factory=list)

    # ── Pillar 2 Findings Summary ─────────────────────────────────────────────
    p2_is_definite: bool = True
    p2_error_count: int = 0
    p2_warning_count: int = 0
    p2_error_messages: List[str] = field(default_factory=list)

    # ── Computed Status (set by build_class_summary) ──────────────────────────
    status: ClassStatus = ClassStatus.CLEAN

    def has_any_error(self) -> bool:
        return self.p1_error_count > 0 or self.p2_error_count > 0

    def has_any_warning(self) -> bool:
        return self.p1_warning_count > 0 or self.p2_warning_count > 0

    def is_use_based(self) -> bool:
        return self.filing_basis in ("1(a)", "44(e)")

    def is_intent_to_use(self) -> bool:
        return self.filing_basis == "1(b)"


def build_class_summary(class_entry_dict: dict,
                         p1_findings: list,
                         p2_result_dict: Optional[dict] = None) -> ClassSummary:
    """
    Build a ClassSummary by combining:
      - class_entry_dict: raw class data (from Pillar 1 ClassEntry or plain dict)
      - p1_findings: list of Pillar 1 AssessmentFinding objects or dicts
      - p2_result_dict: optional output dict from analyze_identification_under_tmep_1402()

    Example:
        summary = build_class_summary(
            class_entry_dict={"class_number": 9, "identification": "...", ...},
            p1_findings=pillar1_result["findings"],
            p2_result_dict=pillar2_result_for_class9
        )
    """
    cls_num = int(class_entry_dict.get("class_number", 0))

    # ── Pull class metadata ───────────────────────────────────────────────────
    class_title = class_entry_dict.get("class_title", "")
    class_category = class_entry_dict.get("class_category", "")

    if not class_title or not class_category:
        try:
            from nice_classification_db import get_class_info
            info = get_class_info(cls_num)
            if info:
                class_title = class_title or info["title"]
                class_category = class_category or info["category"]
        except ImportError:
            pass

    # ── Pull Pillar 1 findings for this class ─────────────────────────────────
    def _get(f, key):
        return f[key] if isinstance(f, dict) else getattr(f, key, None)

    cls_p1_findings = [
        f for f in p1_findings
        if _get(f, "class_number") == cls_num or _get(f, "class_number") == 0
    ]
    p1_errors = [f for f in cls_p1_findings if _get(f, "severity") == "ERROR"]
    p1_warnings = [f for f in cls_p1_findings if _get(f, "severity") == "WARNING"]
    p1_error_msgs = [str(_get(f, "finding"))[:100] for f in p1_errors[:3]]

    # ── Pull Pillar 2 findings ────────────────────────────────────────────────
    p2_is_definite = True
    p2_errors = 0
    p2_warnings = 0
    p2_error_msgs = []

    if p2_result_dict:
        summary = p2_result_dict.get("summary", {})
        p2_is_definite = summary.get("is_definite", True)
        p2_errors = summary.get("errors", 0)
        p2_warnings = summary.get("warnings", 0)
        analysis = p2_result_dict.get("tmep_1402_analysis", {})
        for sf in analysis.get("subsection_findings", []):
            if isinstance(sf, dict) and sf.get("severity") == "ERROR":
                p2_error_msgs.append(sf.get("finding", "")[:100])

    # ── Compute status ────────────────────────────────────────────────────────
    total_errors = len(p1_errors) + p2_errors
    total_warnings = len(p1_warnings) + p2_warnings

    if total_errors >= 3:
        status = ClassStatus.REFUSAL_CANDIDATE
    elif total_errors > 0:
        status = ClassStatus.HAS_ERRORS
    elif total_warnings > 0:
        status = ClassStatus.HAS_WARNINGS
    else:
        status = ClassStatus.CLEAN

    return ClassSummary(
        class_number=cls_num,
        class_title=class_title,
        class_category=class_category,
        identification=class_entry_dict.get("identification", ""),
        filing_basis=class_entry_dict.get("filing_basis", "1(a)"),
        specimen_type=class_entry_dict.get("specimen_type", ""),
        specimen_description=class_entry_dict.get("specimen_description", ""),
        date_of_first_use=class_entry_dict.get("date_of_first_use"),
        date_of_first_use_commerce=class_entry_dict.get("date_of_first_use_commerce"),
        fee_paid=class_entry_dict.get("fee_paid", True),
        p1_error_count=len(p1_errors),
        p1_warning_count=len(p1_warnings),
        p1_error_messages=p1_error_msgs,
        p2_is_definite=p2_is_definite,
        p2_error_count=p2_errors,
        p2_warning_count=p2_warnings,
        p2_error_messages=p2_error_msgs,
        status=status
    )


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION-LEVEL CONTEXT (carries fee + stage info across all classes)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MultiClassApplicationContext:
    """
    Application-level context for the multi-class assessment.
    Most fields come directly from the TrademarkApplication (Pillar 1 input).
    """
    applicant_name: str = ""
    mark_text: str = ""
    filing_date: str = ""
    filing_type: str = "TEAS_PLUS"             # TEAS_PLUS | TEAS_STANDARD | PAPER
    fees_paid_count: int = 0                   # Total fees actually submitted
    total_fee_paid: float = 0.0
    application_stage: ApplicationStage = ApplicationStage.FILED_PENDING

    # Amendment context (populated when an amendment is being assessed)
    amendment_requested: bool = False
    amendment_affects_classes: List[int] = field(default_factory=list)  # [] = all
    amendment_description: str = ""

    # Division context
    division_requested: bool = False
    classes_to_divide_out: List[int] = field(default_factory=list)

    # Post-registration context
    surrender_requested: bool = False
    classes_to_surrender: List[int] = field(default_factory=list)
    post_filing_action_type: str = ""    # "amendment", "response", "surrender", ""


# ═══════════════════════════════════════════════════════════════════════════════
# FINDING MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Pillar3Finding:
    """A single finding for one §1403.xx check."""
    tmep_section: str       # §1403.01 through §1403.06
    severity: str           # ERROR | WARNING | INFO | OK
    class_number: int       # 0 = application-level
    item: str
    finding: str
    recommendation: str
    # Cross-pillar link: which P1/P2 finding triggered this
    triggered_by: str = ""  # e.g. "P1:§1401.04", "P2:§1402.03"


@dataclass
class Pillar3AssessmentResult:
    """Complete Pillar 3 output."""
    findings: List[Pillar3Finding] = field(default_factory=list)

    # §1403.03 output
    division_eligible_classes: List[int] = field(default_factory=list)
    division_recommended: bool = False

    # §1403.04 output
    partial_refusal_classes: List[int] = field(default_factory=list)
    partial_refusal_reasons: Dict[int, str] = field(default_factory=dict)

    # Overall
    is_multi_class_compliant: bool = True
    total_errors: int = 0
    total_warnings: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 3 ASSESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class Pillar3Assessor:
    """
    Runs all §1403.01–§1403.06 checks on a multi-class application,
    using consolidated ClassSummary objects built from Pillars 1 and 2.
    """

    USPTO_FEES = {
        "TEAS_PLUS": 250,
        "TEAS_STANDARD": 350,
        "PAPER": 750
    }

    def __init__(self,
                 class_summaries: List[ClassSummary],
                 app_context: MultiClassApplicationContext):
        self.classes = class_summaries
        self.ctx = app_context
        self.findings: List[Pillar3Finding] = []

    # ─────────────────────────────────────────────────────────────────────────
    # ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    def run_full_assessment(self) -> Pillar3AssessmentResult:
        """Run all §1403 checks in sequence and return the full result."""
        self.findings.clear()

        # Guard: single-class apps don't need §1403 analysis
        unique_classes = list({c.class_number for c in self.classes})
        if len(unique_classes) < 2:
            self.findings.append(Pillar3Finding(
                tmep_section="§1403",
                severity="INFO",
                class_number=0,
                item="Single-class application",
                finding="Application contains only one class. "
                        "§1403 multi-class requirements do not apply.",
                recommendation="No §1403 action required."
            ))
            return self._build_result([], [], {})

        self._check_1403_01_multi_class_requirements()
        amendment_conflicts = self._check_1403_02_amendment_review()
        division_eligible = self._check_1403_03_division_eligibility()
        refusal_classes, refusal_reasons = self._check_1403_04_partial_refusals()
        self._check_1403_05_post_filing_fees()
        self._check_1403_06_surrender_or_amendment()

        return self._build_result(division_eligible, refusal_classes, refusal_reasons)

    # ─────────────────────────────────────────────────────────────────────────
    # §1403.01 — REQUIREMENTS FOR COMBINED OR MULTIPLE-CLASS APPLICATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1403_01_multi_class_requirements(self):
        """
        §1403.01 — Five-point completeness checklist for every class.

        PILLAR INTEGRATION:
          P1 → fee_paid, specimen checks, correct class assignment
          P2 → identification definiteness (is_definite)
          P1 → filing_basis for dates-of-use requirement
        """
        section = "§1403.01"
        all_clean = True

        for cls in self.classes:
            cls_label = f"Class {cls.class_number} ({cls.class_title})"

            # ── CHECK 1: Each class has its own separate identification ───────
            if not cls.identification or len(cls.identification.strip()) < 5:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Missing identification",
                    finding="No identification of goods/services found for this class. "
                             "Every class in a multi-class application must have its own "
                             "separate identification.",
                    recommendation="Provide a complete identification of goods/services "
                                   "for this class.",
                    triggered_by="P1:ClassEntry.identification"
                ))
                all_clean = False
            elif not cls.p2_is_definite:
                # Pillar 2 found the identification non-definite — surface that here
                p2_issues = "; ".join(cls.p2_error_messages[:2]) if cls.p2_error_messages else \
                            "Identification does not meet §1402 specificity standards"
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Identification not definite (Pillar 2)",
                    finding=f"Pillar 2 (§1402) determined the identification for "
                             f"{cls_label} is NOT sufficiently definite. "
                             f"Issues: {p2_issues}",
                    recommendation="Amend the identification to meet §1402 specificity "
                                   "requirements before this class can be accepted in "
                                   "a multi-class application.",
                    triggered_by="P2:§1402.03"
                ))
                all_clean = False
            else:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="OK",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Identification",
                    finding="Separate, definite identification present for this class.",
                    recommendation="No action required."
                ))

            # ── CHECK 2: Each class has its own fee paid ──────────────────────
            # Pillar 1 sets fee_paid per class
            if not cls.fee_paid:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Fee not paid",
                    finding=f"No filing fee was paid for {cls_label}. "
                             "Every class in a multi-class application requires "
                             "a separate filing fee.",
                    recommendation=f"Submit the per-class fee "
                                   f"(${self.USPTO_FEES.get(self.ctx.filing_type, 350)}) "
                                   f"for {cls_label} to avoid deletion of this class.",
                    triggered_by="P1:§1401.04"
                ))
                all_clean = False
            else:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="OK",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Fee",
                    finding="Fee paid for this class.",
                    recommendation="No action required."
                ))

            # ── CHECK 3: Each class has its own specimen (use-based) ──────────
            if cls.is_use_based():
                if not cls.specimen_type and not cls.specimen_description:
                    self.findings.append(Pillar3Finding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=cls.class_number,
                        item=f"{cls_label} — Specimen missing",
                        finding=f"No specimen provided for {cls_label}. "
                                 "Use-based applications (§1(a)) require a separate "
                                 "specimen for each class showing the mark in actual use.",
                        recommendation="Submit a specimen showing the mark in actual commercial "
                                       "use in connection with the goods/services in this class.",
                        triggered_by="P1:§1401.06"
                    ))
                    all_clean = False
                elif cls.p1_error_count > 0 and any(
                        "specimen" in m.lower() for m in cls.p1_error_messages):
                    # Pillar 1 already flagged a specimen error — surface it in §1403 context
                    self.findings.append(Pillar3Finding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=cls.class_number,
                        item=f"{cls_label} — Specimen invalid (Pillar 1)",
                        finding=f"Pillar 1 detected a specimen issue for {cls_label}: "
                                 f"{'; '.join(m for m in cls.p1_error_messages if 'specimen' in m.lower())[:120]}",
                        recommendation="Replace the specimen with an acceptable one for this class. "
                                       "Each class must have its own valid specimen.",
                        triggered_by="P1:§1401.06"
                    ))
                    all_clean = False
                else:
                    self.findings.append(Pillar3Finding(
                        tmep_section=section,
                        severity="OK",
                        class_number=cls.class_number,
                        item=f"{cls_label} — Specimen",
                        finding=f"Specimen present: '{cls.specimen_type}'.",
                        recommendation="No action required."
                    ))
            else:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Specimen (§1(b))",
                    finding=f"Intent-to-use basis ({cls.filing_basis}). "
                             "No specimen required at this stage.",
                    recommendation="Specimen must be submitted with Statement of Use."
                ))

            # ── CHECK 4: Goods/services correctly assigned to class ───────────
            # Pillar 1 §1401.03 errors are the primary signal here
            p1_class_errors = [m for m in cls.p1_error_messages
                               if any(kw in m.lower() for kw in
                                      ["misclassif", "class", "wrong", "incorrect", "reclassif"])]

            if p1_class_errors:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Classification issue (Pillar 1)",
                    finding=f"Pillar 1 (§1401.03) detected incorrect class assignment for "
                             f"{cls_label}: {p1_class_errors[0][:120]}",
                    recommendation="Correct the class assignment per Pillar 1 recommendations "
                                   "before proceeding with multi-class filing requirements.",
                    triggered_by="P1:§1401.03"
                ))
                all_clean = False
            else:
                has_p1_class_warning = cls.p1_warning_count > 0
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="WARNING" if has_p1_class_warning else "OK",
                    class_number=cls.class_number,
                    item=f"{cls_label} — Class assignment",
                    finding=(f"Pillar 1 raised {cls.p1_warning_count} warning(s) about the "
                              "class assignment — review recommended."
                              if has_p1_class_warning else
                              "No class assignment errors detected for this class."),
                    recommendation=("Review Pillar 1 warnings for this class."
                                    if has_p1_class_warning else "No action required."),
                    triggered_by="P1:§1401.03"
                ))

            # ── CHECK 5: Dates of use provided per class (use-based) ──────────
            if cls.is_use_based():
                missing_dates = []
                if not cls.date_of_first_use:
                    missing_dates.append("date of first use anywhere")
                if not cls.date_of_first_use_commerce:
                    missing_dates.append("date of first use in commerce")

                if missing_dates:
                    self.findings.append(Pillar3Finding(
                        tmep_section=section,
                        severity="WARNING",
                        class_number=cls.class_number,
                        item=f"{cls_label} — Missing dates of use",
                        finding=f"Missing for {cls_label}: {', '.join(missing_dates)}. "
                                 "Per §1403.01, dates of use must be provided separately "
                                 "for each class in a use-based application.",
                        recommendation="Add separate dates of first use (anywhere) and "
                                       "first use in commerce for this class.",
                        triggered_by="P1:ClassEntry.date_of_first_use"
                    ))
                    all_clean = False
                else:
                    self.findings.append(Pillar3Finding(
                        tmep_section=section,
                        severity="OK",
                        class_number=cls.class_number,
                        item=f"{cls_label} — Dates of use",
                        finding=f"First use: {cls.date_of_first_use} | "
                                 f"First use in commerce: {cls.date_of_first_use_commerce}",
                        recommendation="No action required."
                    ))

        # ── Application-level fee count cross-check ───────────────────────────
        # (Pillar 1 §1401.04 already caught this, but §1403.01 requires us to
        #  confirm fees in the multi-class context specifically)
        unique_cls_count = len({c.class_number for c in self.classes})
        fees_paid = self.ctx.fees_paid_count

        if fees_paid > 0 and fees_paid != unique_cls_count:
            shortage = unique_cls_count - fees_paid
            severity = "ERROR" if shortage > 0 else "WARNING"
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity=severity,
                class_number=0,
                item=f"Application-level fee count: {fees_paid} paid, "
                     f"{unique_cls_count} classes",
                finding=f"{'UNDERPAYMENT' if shortage > 0 else 'OVERPAYMENT'}: "
                         f"{fees_paid} fee(s) submitted but {unique_cls_count} class(es) filed. "
                         f"{'Shortage: ' + str(abs(shortage)) + ' fee(s).' if shortage > 0 else 'Excess: ' + str(abs(shortage)) + ' fee(s).'}",
                recommendation=(
                    f"Submit {abs(shortage)} additional fee(s) at "
                    f"${self.USPTO_FEES.get(self.ctx.filing_type, 350)}/class. "
                    "Unpaid classes will be deleted."
                    if shortage > 0 else
                    "Request refund for excess fees or add additional classes."
                ),
                triggered_by="P1:§1401.04"
            ))
        elif fees_paid > 0:
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="OK",
                class_number=0,
                item="Application-level fee count",
                finding=f"Fee count matches class count: "
                         f"{fees_paid} fee(s) for {unique_cls_count} class(es).",
                recommendation="No action required."
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1403.02 — AMENDMENT OF COMBINED OR MULTIPLE-CLASS APPLICATION
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1403_02_amendment_review(self) -> List[int]:
        """
        §1403.02 — Amendments in multi-class applications.

        Key rules:
        1. An amendment to one class must not inadvertently broaden/alter another.
        2. Amendment cannot add new goods/services not in the original scope.
        3. Each amended class may require additional fees.

        Returns: list of class numbers with potential cross-class conflicts.
        """
        section = "§1403.02"
        conflict_classes = []

        if not self.ctx.amendment_requested:
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item="No amendment in this assessment",
                finding="No amendment has been requested. §1403.02 amendment rules "
                         "are noted for reference.",
                recommendation="When filing any amendment, ensure changes are "
                               "class-specific and do not affect other classes."
            ))
            return []

        affected = self.ctx.amendment_affects_classes
        all_class_numbers = [c.class_number for c in self.classes]

        # ── If amendment description says "all classes" or affects all ────────
        if not affected or set(affected) == set(all_class_numbers):
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="WARNING",
                class_number=0,
                item="Amendment scope: ALL classes",
                finding=f"The requested amendment appears to affect all classes "
                         f"({', '.join(f'Class {c}' for c in sorted(all_class_numbers))}). "
                         "An application-wide amendment must be reviewed carefully to ensure "
                         "it does not inadvertently narrow or alter classes that don't need changing.",
                recommendation="Confirm which classes actually need amendment. "
                               "File class-specific amendments where possible to avoid "
                               "unintended scope changes across classes.",
            ))
        else:
            # Amendment affects specific classes — check for cross-class conflicts
            non_affected = [c for c in all_class_numbers if c not in affected]

            for cls in self.classes:
                if cls.class_number not in affected:
                    continue

                # Check: does the amended class identification share any keywords
                # with non-amended classes? (potential overlap after amendment)
                amended_words = set(cls.identification.lower().split())
                for other_cls in self.classes:
                    if other_cls.class_number in affected:
                        continue
                    other_words = set(other_cls.identification.lower().split())
                    shared = amended_words & other_words - {
                        "and", "or", "for", "the", "of", "in", "a", "an",
                        "to", "with", "by", "from", "on", "at"
                    }

                    if len(shared) >= 3:
                        conflict_classes.append(cls.class_number)
                        self.findings.append(Pillar3Finding(
                            tmep_section=section,
                            severity="WARNING",
                            class_number=cls.class_number,
                            item=f"Cross-class amendment conflict: "
                                 f"Class {cls.class_number} ↔ Class {other_cls.class_number}",
                            finding=f"Amending Class {cls.class_number} may affect Class "
                                     f"{other_cls.class_number} — they share terminology: "
                                     f"{', '.join(list(shared)[:5])}. "
                                     "Per §1403.02, amendments to one class must not "
                                     "inadvertently alter the scope of another.",
                            recommendation=f"Review whether the amendment to Class {cls.class_number} "
                                           f"creates any scope overlap with Class {other_cls.class_number}. "
                                           "Amend each class separately with distinct language.",
                            triggered_by=f"P1+P2:Class{cls.class_number}↔Class{other_cls.class_number}"
                        ))

            if not conflict_classes:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="OK",
                    class_number=0,
                    item=f"Amendment scope: Class(es) "
                         f"{', '.join(str(c) for c in sorted(affected))} only",
                    finding=f"Amendment is limited to Class(es) "
                             f"{', '.join(str(c) for c in sorted(affected))}. "
                             "No obvious cross-class terminology conflicts detected.",
                    recommendation="Ensure the amendment is filed with correct class-specific "
                                   "language and any required additional fees."
                ))

        # ── Amendment broadening guard ────────────────────────────────────────
        if self.ctx.amendment_description:
            broadening_keywords = [
                "add", "adding", "expand", "include", "broader", "additional",
                "new goods", "new services", "new class"
            ]
            desc_lower = self.ctx.amendment_description.lower()
            if any(kw in desc_lower for kw in broadening_keywords):
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=0,
                    item="Amendment may attempt to broaden scope",
                    finding=f"Amendment description '{self.ctx.amendment_description[:80]}' "
                             "contains language suggesting scope broadening. "
                             "Per §1402.07 (applied through §1403.02), amendments cannot "
                             "expand the identification beyond the original filing scope.",
                    recommendation="Amendments may only CLARIFY or LIMIT the identification. "
                                   "Remove any language that adds new goods/services not "
                                   "encompassed by the original filing."
                ))

        return conflict_classes

    # ─────────────────────────────────────────────────────────────────────────
    # §1403.03 — DIVIDING OF COMBINED OR MULTIPLE-CLASS APPLICATION
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1403_03_division_eligibility(self) -> List[int]:
        """
        §1403.03 — An applicant can divide a multi-class application to let
        clean classes proceed while problematic ones are resolved separately.

        PILLAR INTEGRATION:
          - Classes with P1 errors OR P2 errors are division candidates
          - Classes without errors can be separated to proceed to registration
          - Division is especially useful when some classes are §1(a) and
            others are §1(b)

        Returns: list of class numbers eligible/recommended for division.
        """
        section = "§1403.03"
        division_eligible = []

        # Classes with errors that would benefit from division
        error_classes = [c for c in self.classes if c.has_any_error()]
        clean_classes = [c for c in self.classes if not c.has_any_error()]

        # Classes with mixed filing bases (classic division trigger)
        use_based = [c for c in self.classes if c.is_use_based()]
        intent_to_use = [c for c in self.classes if c.is_intent_to_use()]

        # ── Case 1: Specific division requested by applicant ──────────────────
        if self.ctx.division_requested:
            to_divide = self.ctx.classes_to_divide_out
            remaining = [c.class_number for c in self.classes
                        if c.class_number not in to_divide]

            # Verify divided classes meet standalone requirements
            for cls_num in to_divide:
                cls = next((c for c in self.classes if c.class_number == cls_num), None)
                if not cls:
                    continue

                issues = []
                if not cls.identification.strip():
                    issues.append("missing identification")
                if cls.is_use_based() and not cls.specimen_type:
                    issues.append("missing specimen")
                if not cls.fee_paid:
                    issues.append("fee not paid")

                if issues:
                    self.findings.append(Pillar3Finding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=cls_num,
                        item=f"Class {cls_num} — Cannot divide: incomplete requirements",
                        finding=f"Class {cls_num} cannot be divided out because it does "
                                 f"not meet standalone filing requirements: "
                                 f"{', '.join(issues)}. A divided application must be "
                                 "complete in itself.",
                        recommendation="Resolve these issues before dividing: "
                                       f"{', '.join(issues)}."
                    ))
                else:
                    division_eligible.append(cls_num)
                    self.findings.append(Pillar3Finding(
                        tmep_section=section,
                        severity="OK",
                        class_number=cls_num,
                        item=f"Class {cls_num} — Division eligible",
                        finding=f"Class {cls_num} meets all standalone requirements "
                                 "and can be divided into its own application.",
                        recommendation=f"Proceed with division request for Class {cls_num}. "
                                       "The child application will carry forward the "
                                       "original filing date."
                    ))

            if remaining:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=0,
                    item=f"Remaining after division: "
                         f"Class(es) {', '.join(str(r) for r in sorted(remaining))}",
                    finding=f"After dividing out Class(es) "
                             f"{', '.join(str(d) for d in sorted(to_divide))}, "
                             f"the parent application retains "
                             f"Class(es) {', '.join(str(r) for r in sorted(remaining))}.",
                    recommendation="Verify the parent application remains complete "
                                   "and all retained classes are properly supported."
                ))

        # ── Case 2: No division requested — assess recommendation ─────────────
        else:
            if error_classes and clean_classes:
                error_cls_nums = [c.class_number for c in error_classes]
                clean_cls_nums = [c.class_number for c in clean_classes]
                division_eligible = clean_cls_nums

                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="WARNING",
                    class_number=0,
                    item=f"Division RECOMMENDED — Clean vs. problem classes detected",
                    finding=f"DIVISION ANALYSIS (§1403.03): "
                             f"Class(es) {', '.join(f'Class {n}' for n in sorted(clean_cls_nums))} "
                             f"are clean, but "
                             f"Class(es) {', '.join(f'Class {n}' for n in sorted(error_cls_nums))} "
                             f"have errors. Without division, the errors in "
                             f"{', '.join(f'Class {n}' for n in sorted(error_cls_nums))} "
                             "will delay registration for the clean classes too.",
                    recommendation=f"Consider dividing Class(es) "
                                   f"{', '.join(str(n) for n in sorted(clean_cls_nums))} "
                                   "into a separate application so they can proceed to "
                                   "registration independently. "
                                   "File a Request to Divide (USPTO Form PTO-2302)."
                ))

            elif use_based and intent_to_use:
                itu_nums = [c.class_number for c in intent_to_use]
                use_nums = [c.class_number for c in use_based]

                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=0,
                    item=f"Mixed filing basis — potential division candidate",
                    finding=f"Application has mixed filing bases: "
                             f"Class(es) {', '.join(str(n) for n in sorted(use_nums))} "
                             f"are §1(a) use-based; "
                             f"Class(es) {', '.join(str(n) for n in sorted(itu_nums))} "
                             "are §1(b) intent-to-use. "
                             "The §1(b) classes cannot achieve registration until a "
                             "Statement of Use is filed, which may delay the §1(a) classes.",
                    recommendation=f"Consider dividing the §1(a) classes "
                                   f"({', '.join(str(n) for n in sorted(use_nums))}) "
                                   "so they can proceed to registration independently "
                                   "of the §1(b) classes."
                ))
                division_eligible = use_nums

            else:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=0,
                    item="Division not currently indicated",
                    finding="All classes appear to be at the same stage with similar "
                             "issue profiles. Division is not currently recommended.",
                    recommendation="Monitor application progress. Division may become "
                                   "appropriate if one class receives a specific refusal."
                ))

        return division_eligible

    # ─────────────────────────────────────────────────────────────────────────
    # §1403.04 — REFUSALS AS TO LESS THAN ALL CLASSES
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1403_04_partial_refusals(self) -> tuple:
        """
        §1403.04 — A refusal can apply to some classes but not all.
        A class with errors should receive a targeted refusal, not invalidate
        the entire application.

        PILLAR INTEGRATION (key method for P1 + P2 convergence):
          - P1 errors (misclassification, bad specimen, wrong class) → refusal
          - P2 non-definite identification → refusal
          - Clean classes → explicitly noted as proceeding

        Returns: (refusal_class_numbers, refusal_reasons_dict)
        """
        section = "§1403.04"
        refusal_classes = []
        refusal_reasons: Dict[int, str] = {}

        for cls in self.classes:
            reasons = []

            # ── Collect P1 error reasons ──────────────────────────────────────
            if cls.p1_error_count > 0:
                for msg in cls.p1_error_messages[:2]:
                    reasons.append(f"[Pillar 1 — §1401] {msg[:100]}")

            # ── Collect P2 error reasons ──────────────────────────────────────
            if not cls.p2_is_definite or cls.p2_error_count > 0:
                for msg in cls.p2_error_messages[:2]:
                    reasons.append(f"[Pillar 2 — §1402] {msg[:100]}")
                if not cls.p2_is_definite and not cls.p2_error_messages:
                    reasons.append("[Pillar 2 — §1402] Identification is not sufficiently definite.")

            if reasons:
                refusal_classes.append(cls.class_number)
                refusal_reasons[cls.class_number] = "; ".join(reasons)

                severity = "ERROR" if cls.status == ClassStatus.REFUSAL_CANDIDATE else "WARNING"
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity=severity,
                    class_number=cls.class_number,
                    item=f"Class {cls.class_number} — PARTIAL REFUSAL CANDIDATE",
                    finding=f"Class {cls.class_number} ({cls.class_title}) has "
                             f"{cls.p1_error_count} Pillar 1 error(s) and "
                             f"{cls.p2_error_count} Pillar 2 error(s) that constitute "
                             f"grounds for a PARTIAL REFUSAL under §1403.04. "
                             f"Reasons: {'; '.join(reasons[:2])}",
                    recommendation=f"Issue a partial refusal limited to Class {cls.class_number}. "
                                   "Do NOT refuse the entire application — other classes "
                                   "should continue to be processed. "
                                   "State each ground of refusal clearly in the Office Action.",
                    triggered_by=f"P1:{cls.p1_error_count}errors + P2:{cls.p2_error_count}errors"
                ))
            else:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="OK",
                    class_number=cls.class_number,
                    item=f"Class {cls.class_number} — No refusal grounds",
                    finding=f"Class {cls.class_number} ({cls.class_title}) has no "
                             "errors from Pillar 1 or Pillar 2. No refusal is indicated "
                             "for this class.",
                    recommendation="This class may proceed independently. "
                                   "Consider division if other classes face refusals."
                ))

        # ── Application-level refusal summary ────────────────────────────────
        if refusal_classes:
            non_refusal = [c.class_number for c in self.classes
                          if c.class_number not in refusal_classes]
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item=f"Partial refusal summary",
                finding=f"PARTIAL REFUSAL applies to: "
                         f"Class(es) {', '.join(str(c) for c in sorted(refusal_classes))}. "
                         f"Classes NOT subject to refusal: "
                         f"{', '.join(str(c) for c in sorted(non_refusal)) if non_refusal else 'None'}.",
                recommendation="Issue Office Action with partial refusal. "
                               "For each refused class, cite the specific legal ground. "
                               "For clean classes, note they are approved or being processed."
            ))

        return refusal_classes, refusal_reasons

    # ─────────────────────────────────────────────────────────────────────────
    # §1403.05 — FEES FOR POST-FILING ACTIONS, MULTIPLE CLASSES
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1403_05_post_filing_fees(self):
        """
        §1403.05 — When post-filing actions (responses, amendments, SOU) are
        filed in a multi-class application, the correct per-class fee must
        accompany actions for each affected class.
        """
        section = "§1403.05"
        stage = self.ctx.application_stage
        action = self.ctx.post_filing_action_type
        fee_per_class = self.USPTO_FEES.get(self.ctx.filing_type, 350)

        # No post-filing action in this assessment
        if not action and stage in (ApplicationStage.PRE_FILING,
                                     ApplicationStage.FILED_PENDING):
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item="No post-filing action in this assessment",
                finding="Application is at filing/pending stage. "
                         "§1403.05 post-filing fee requirements will apply if/when "
                         "responses, amendments, or Statements of Use are filed.",
                recommendation="When filing any post-filing action, ensure the "
                               "correct per-class fee is included for each affected class."
            ))
            return

        # Statement of Use (SOU) — intent-to-use classes
        itu_classes = [c for c in self.classes if c.is_intent_to_use()]
        if stage == ApplicationStage.STATEMENT_OF_USE or action == "sou":
            if itu_classes:
                sou_fee_total = len(itu_classes) * 100  # $100/class SOU fee (USPTO 2025)
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=0,
                    item=f"Statement of Use — {len(itu_classes)} class(es)",
                    finding=f"Statement of Use being filed for "
                             f"{len(itu_classes)} §1(b) class(es): "
                             f"{', '.join(f'Class {c.class_number}' for c in itu_classes)}. "
                             f"SOU fee: $100/class × {len(itu_classes)} = ${sou_fee_total}.",
                    recommendation=f"Submit SOU with ${sou_fee_total} total "
                                   f"(${100}/class for each of the "
                                   f"{len(itu_classes)} §1(b) class(es)). "
                                   "Each class needs its own specimen with the SOU."
                ))

        # Amendment response with fees
        if action in ("amendment", "response") and self.ctx.amendment_affects_classes:
            affected_count = len(self.ctx.amendment_affects_classes)
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item=f"Post-filing {action} fee — "
                     f"{affected_count} class(es) affected",
                finding=f"Post-filing {action} affects "
                         f"{affected_count} class(es): "
                         f"{', '.join(f'Class {c}' for c in sorted(self.ctx.amendment_affects_classes))}. "
                         "Verify whether additional per-class fees are required "
                         "for this type of action.",
                recommendation=f"Check USPTO fee schedule for post-filing {action} fees. "
                               f"Ensure fee is submitted for each of the "
                               f"{affected_count} affected class(es)."
            ))

        # Surrender fees (if applicable)
        if self.ctx.surrender_requested and self.ctx.classes_to_surrender:
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item=f"Surrender fee check — "
                     f"Class(es) {', '.join(str(c) for c in self.ctx.classes_to_surrender)}",
                finding="Partial surrender of classes in a multi-class registration. "
                         "Verify whether any petition or maintenance fees apply "
                         "to the surrender action.",
                recommendation="File a Section 7 Request for Amendment/Surrender "
                               "(USPTO Form) with required fees for each surrendered class."
            ))

        # General multi-class post-filing reminder
        self.findings.append(Pillar3Finding(
            tmep_section=section,
            severity="INFO",
            class_number=0,
            item="Multi-class post-filing fee rule",
            finding="Per §1403.05: in multi-class applications, post-filing actions "
                     "require separate fees for each class to which the action applies. "
                     "A single fee does not cover all classes automatically.",
            recommendation="Always verify the number of classes affected by any "
                           "post-filing action and submit the correct per-class fee amount."
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1403.06 — SURRENDER OR AMENDMENT IN MULTI-CLASS REGISTRATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1403_06_surrender_or_amendment(self):
        """
        §1403.06 — After registration, an applicant can surrender one or more
        classes while keeping others. Checks that surrendering a class doesn't
        create scope inconsistencies in the remaining classes.
        """
        section = "§1403.06"
        stage = self.ctx.application_stage

        # Only relevant post-registration
        if stage not in (ApplicationStage.REGISTERED,
                          ApplicationStage.POST_REGISTRATION):
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item=f"§1403.06 — Not yet registered (stage: {stage.value})",
                finding="Application has not yet reached registration. "
                         "§1403.06 surrender and post-registration amendment rules "
                         "will apply after registration is granted.",
                recommendation="Note for post-registration: partial surrender is possible "
                               "via Section 7 amendment. Surrendering a class is irrevocable."
            ))
            return

        if not self.ctx.surrender_requested:
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item="No surrender requested",
                finding="No surrender of classes has been requested in this assessment.",
                recommendation="If a partial surrender is needed post-registration, "
                               "file a Section 7 Request (USPTO Form SB/08). "
                               "Surrender is irrevocable — once a class is surrendered, "
                               "it cannot be reinstated."
            ))
            return

        to_surrender = self.ctx.classes_to_surrender
        to_retain = [c for c in self.classes
                     if c.class_number not in to_surrender]

        # ── Validate surrender doesn't leave registration empty ───────────────
        if len(to_surrender) >= len(self.classes):
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="ERROR",
                class_number=0,
                item="Full surrender — entire registration would be abandoned",
                finding="Surrendering all classes would result in complete abandonment "
                         "of the registration. If that is the intent, a full cancellation "
                         "should be filed instead.",
                recommendation="File a Request for Cancellation (USPTO Form) if the intent "
                               "is to abandon the entire registration. "
                               "For partial surrender, retain at least one class."
            ))
            return

        # ── Check for scope inconsistencies in retained classes ───────────────
        surrendered_cls_objects = [c for c in self.classes
                                   if c.class_number in to_surrender]
        retained_id_words = set()
        for rc in to_retain:
            retained_id_words.update(rc.identification.lower().split())

        inconsistency_found = False
        for sc in surrendered_cls_objects:
            surrendered_words = set(sc.identification.lower().split()) - {
                "and", "or", "for", "the", "of", "in", "a", "an", "to",
                "with", "by", "from", "on", "at", "namely", "including"
            }
            overlap_with_retained = surrendered_words & retained_id_words
            significant_overlap = [w for w in overlap_with_retained if len(w) > 4]

            if significant_overlap:
                inconsistency_found = True
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="WARNING",
                    class_number=sc.class_number,
                    item=f"Scope overlap: surrendering Class {sc.class_number} "
                         f"while retaining other classes",
                    finding=f"Surrendering Class {sc.class_number} ({sc.class_title}) "
                             f"may create inconsistency with retained classes. "
                             f"Shared terminology between surrendered and retained "
                             f"identifications: {', '.join(significant_overlap[:5])}. "
                             "After surrender, consumers may be confused about the "
                             "scope of the remaining registration.",
                    recommendation=f"Review whether surrendering Class {sc.class_number} "
                                   "creates gaps or ambiguity in the overall trademark scope. "
                                   "Consider whether amendments to retained class identifications "
                                   "are needed for clarity post-surrender."
                ))
            else:
                self.findings.append(Pillar3Finding(
                    tmep_section=section,
                    severity="OK",
                    class_number=sc.class_number,
                    item=f"Class {sc.class_number} — Surrender scope check",
                    finding=f"Surrendering Class {sc.class_number} ({sc.class_title}) "
                             "does not appear to create scope inconsistency with retained classes.",
                    recommendation=f"Proceed with surrender of Class {sc.class_number}. "
                                   "Remember: surrender is irrevocable."
                ))

        # ── Retained classes check ────────────────────────────────────────────
        if to_retain:
            self.findings.append(Pillar3Finding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item=f"Post-surrender retained: "
                     f"Class(es) {', '.join(str(c.class_number) for c in sorted(to_retain, key=lambda x: x.class_number))}",
                finding=f"After surrendering Class(es) "
                         f"{', '.join(str(s) for s in sorted(to_surrender))}, "
                         f"the registration will retain "
                         f"Class(es) {', '.join(str(c.class_number) for c in sorted(to_retain, key=lambda x: x.class_number))}.",
                recommendation="Ensure maintenance fees (Section 8/71 Declarations) "
                               "are paid for all RETAINED classes going forward. "
                               "Surrendered classes are excluded from future maintenance."
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD FINAL RESULT
    # ─────────────────────────────────────────────────────────────────────────

    def _build_result(self,
                      division_eligible: List[int],
                      refusal_classes: List[int],
                      refusal_reasons: Dict[int, str]) -> Pillar3AssessmentResult:

        errors = sum(1 for f in self.findings if f.severity == "ERROR")
        warnings = sum(1 for f in self.findings if f.severity == "WARNING")
        is_compliant = (errors == 0)

        return Pillar3AssessmentResult(
            findings=self.findings,
            division_eligible_classes=division_eligible,
            division_recommended=len(division_eligible) > 0,
            partial_refusal_classes=refusal_classes,
            partial_refusal_reasons=refusal_reasons,
            is_multi_class_compliant=is_compliant,
            total_errors=errors,
            total_warnings=warnings
        )


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def print_pillar3_report(result: Pillar3AssessmentResult,
                          app_context: MultiClassApplicationContext):
    """Professional legal report — Pillar 3 multi-class filing assessment."""
    _SEV   = {"ERROR": "■", "WARNING": "▲", "INFO": "◆", "OK": "✓"}
    _ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2, "OK": 3}

    def _trim(t, n=110):
        t = str(t).replace("\n", " ").strip()
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"

    line   = "─" * 70
    status = "COMPLIANT" if result.is_multi_class_compliant \
             else "NON-COMPLIANT — CORRECTIONS REQUIRED"

    print(f"\n{line}")
    print(f"  MULTI-CLASS FILING REVIEW  |  §1403")
    print(f"  Status: {status}")

    # ── Partial refusal alert (high legal significance — always show) ─────────
    if result.partial_refusal_classes:
        cls_list = ", ".join(f"Class {c}" for c in sorted(result.partial_refusal_classes))
        print(f"\n  PARTIAL REFUSAL INDICATED:  {cls_list}")
        for cls_num, reason in result.partial_refusal_reasons.items():
            print(f"    Class {cls_num}: {_trim(reason, 100)}")

    # ── Division recommendation (material to applicant strategy) ─────────────
    if result.division_recommended:
        eligible = ", ".join(f"Class {c}" for c in sorted(result.division_eligible_classes))
        print(f"\n  DIVISION RECOMMENDED")
        print(f"  Classes eligible to proceed independently: {eligible}")

    # ── Actionable findings only — no OK, no pure INFO ────────────────────────
    issues = sorted(
        [f for f in result.findings if f.severity in ("ERROR", "WARNING")],
        key=lambda x: (_ORDER.get(x.severity, 9), x.class_number)
    )

    if issues:
        print(f"\n  Filing Issues:")
        seen = set()
        for f in issues:
            key = (f.tmep_section, f.class_number, f.severity)
            if key in seen:
                continue
            seen.add(key)
            sym = _SEV.get(f.severity, "?")
            cls = f"Class {f.class_number}: " if f.class_number > 0 else ""
            print(f"  {sym} [{f.tmep_section}]  {cls}{_trim(f.finding)}")
            print(f"      → {_trim(f.recommendation)}")
    else:
        print(f"\n  No multi-class filing issues detected.")

    print(line)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def assess_multi_class_application(
        class_summaries: List[ClassSummary],
        app_context: MultiClassApplicationContext
) -> Pillar3AssessmentResult:
    """
    Main entry point for Pillar 3 assessment.

    Args:
        class_summaries : List of ClassSummary built via build_class_summary()
                          — one per class, each incorporating P1 + P2 findings
        app_context     : MultiClassApplicationContext with application-level data

    Returns:
        Pillar3AssessmentResult with all §1403 findings
    """
    assessor = Pillar3Assessor(class_summaries, app_context)
    return assessor.run_full_assessment()


# ═══════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE RUNNER — Connects Pillars 1 → 2 → 3 end-to-end
# ═══════════════════════════════════════════════════════════════════════════════

def run_full_pipeline(application_dict: dict) -> dict:
    """
    Runs the complete 3-pillar assessment pipeline on a trademark application.

    Args:
        application_dict: Same format as Pillar 1 main.py assess_trademark_application()

    Returns:
        dict with:
            pillar1  : Pillar 1 result dict (findings, summary, report)
            pillar2  : Dict[class_number → Pillar 2 result dict]
            pillar3  : Pillar3AssessmentResult
            summary  : Combined counts across all 3 pillars
    """
    # ── PILLAR 1 ──────────────────────────────────────────────────────────────
    try:
        from main import assess_trademark_application
        p1_result = assess_trademark_application(application_dict)
        p1_findings = p1_result["findings"]
        p1_app = p1_result["application"]
    except ImportError:
        print("⚠️  Pillar 1 (main.py) not found — running Pillar 3 with provided data only.")
        p1_findings = []
        p1_app = None

    # ── PILLAR 2 (per class) ──────────────────────────────────────────────────
    p2_results: Dict[int, dict] = {}
    try:
        from tmep_1402_pillar2 import (
            analyze_identification_under_tmep_1402,
            build_pillar1_context_from_dicts,
            Pillar1ClassContext
        )
        for cls_dict in application_dict.get("classes", []):
            cls_num = int(cls_dict.get("class_number", 0))
            p1_ctx = build_pillar1_context_from_dicts(cls_dict, p1_findings)
            p2_result = analyze_identification_under_tmep_1402(
                cls_dict.get("identification", ""),
                pillar1_context=p1_ctx
            )
            p2_results[cls_num] = p2_result
    except ImportError:
        print("⚠️  Pillar 2 (tmep_1402_pillar2.py) not found — skipping P2 analysis.")

    # ── BUILD CLASS SUMMARIES (P1 + P2 consolidated) ──────────────────────────
    class_summaries = []
    for cls_dict in application_dict.get("classes", []):
        cls_num = int(cls_dict.get("class_number", 0))
        summary = build_class_summary(
            class_entry_dict=cls_dict,
            p1_findings=p1_findings,
            p2_result_dict=p2_results.get(cls_num)
        )
        class_summaries.append(summary)

    # ── BUILD APPLICATION CONTEXT ─────────────────────────────────────────────
    app_ctx = MultiClassApplicationContext(
        applicant_name=application_dict.get("applicant_name", ""),
        mark_text=application_dict.get("mark_text", ""),
        filing_date=application_dict.get("filing_date", ""),
        filing_type=application_dict.get("filing_type", "TEAS_PLUS"),
        fees_paid_count=int(application_dict.get("fees_paid_count", 0)),
        total_fee_paid=float(application_dict.get("total_fee_paid", 0.0)),
        application_stage=ApplicationStage.FILED_PENDING,
        amendment_requested=application_dict.get("amendment_requested", False),
        amendment_affects_classes=application_dict.get("amendment_affects_classes", []),
        amendment_description=application_dict.get("amendment_description", ""),
        division_requested=application_dict.get("division_requested", False),
        classes_to_divide_out=application_dict.get("classes_to_divide_out", []),
        surrender_requested=application_dict.get("surrender_requested", False),
        classes_to_surrender=application_dict.get("classes_to_surrender", []),
        post_filing_action_type=application_dict.get("post_filing_action_type", "")
    )

    # ── PILLAR 3 ──────────────────────────────────────────────────────────────
    p3_result = assess_multi_class_application(class_summaries, app_ctx)

    # ── COMBINED SUMMARY ──────────────────────────────────────────────────────
    p1_summary = p1_result.get("summary", {}) if p1_findings else {}
    p2_total_errors = sum(r["summary"]["errors"] for r in p2_results.values())
    p2_total_warnings = sum(r["summary"]["warnings"] for r in p2_results.values())

    combined_summary = {
        "pillar1_errors":   p1_summary.get("errors", 0),
        "pillar1_warnings": p1_summary.get("warnings", 0),
        "pillar2_errors":   p2_total_errors,
        "pillar2_warnings": p2_total_warnings,
        "pillar3_errors":   p3_result.total_errors,
        "pillar3_warnings": p3_result.total_warnings,
        "total_errors":     p1_summary.get("errors", 0) + p2_total_errors + p3_result.total_errors,
        "total_warnings":   p1_summary.get("warnings", 0) + p2_total_warnings + p3_result.total_warnings,
        "partial_refusal_classes": p3_result.partial_refusal_classes,
        "division_recommended": p3_result.division_recommended,
        "division_eligible_classes": p3_result.division_eligible_classes,
        "overall_compliant": p3_result.is_multi_class_compliant and p1_summary.get("errors", 0) == 0
    }

    print_pillar3_report(p3_result, app_ctx)

    return {
        "pillar1": p1_result if p1_findings else {},
        "pillar2": p2_results,
        "pillar3": p3_result,
        "summary": combined_summary
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO — Run directly with sample applications
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ── DEMO 1: Multi-class with mixed errors (feeds from Pillar 1 sample 2) ──
    print("\n" + "█"*85)
    print("  DEMO 1: Multi-class app with errors — division recommended")
    print("█"*85)

    DEMO_APP_1 = {
        "applicant_name": "Global Brands LLC",
        "mark_text": "BRANDSTAR",
        "filing_date": "2024-11-20",
        "nice_edition_claimed": "12th",
        "filing_type": "TEAS_STANDARD",
        "fees_paid_count": 2,
        "total_fee_paid": 700.0,
        "amendment_requested": False,
        "division_requested": False,
        "surrender_requested": False,
        "post_filing_action_type": "",
        "classes": [
            {
                "class_number": 9,
                "identification": "Downloadable software for e-commerce management",
                "specimen_type": "website screenshot",
                "specimen_description": "screenshot showing downloadable software for sale",
                "fee_paid": True,
                "filing_basis": "1(a)",
                "date_of_first_use": "2023-01-15",
                "date_of_first_use_commerce": "2023-03-01"
            },
            {
                "class_number": 25,
                "identification": "Software for inventory management; computer programs",
                # Software in Class 25 = Pillar 1 error → Pillar 3 partial refusal
                "specimen_type": "product label",
                "specimen_description": "label on clothing item",
                "fee_paid": True,
                "filing_basis": "1(a)",
                "date_of_first_use": "2023-01-10",
                "date_of_first_use_commerce": "2023-02-01"
            },
            {
                "class_number": 42,
                "identification": "Restaurant services; catering services; hotel accommodation",
                # Post-8th Edition error: restaurant goes to Class 43, not 42
                "specimen_type": "brochure",
                "specimen_description": "advertising restaurant services",
                "fee_paid": False,    # No fee = Pillar 1 §1401.04 error
                "filing_basis": "1(a)",
                "date_of_first_use": "2022-08-15",
                "date_of_first_use_commerce": "2022-09-01"
            }
        ]
    }

    result1 = run_full_pipeline(DEMO_APP_1)
    print("\n  COMBINED PIPELINE SUMMARY:")
    for k, v in result1["summary"].items():
        print(f"    {k:30s}: {v}")

    # ── DEMO 2: Clean tech app + amendment affecting all classes ──────────────
    print("\n" + "█"*85)
    print("  DEMO 2: Clean app with amendment scope check")
    print("█"*85)

    DEMO_APP_2 = {
        "applicant_name": "TechVista Solutions Inc.",
        "mark_text": "NEXAFLOW",
        "filing_date": "2024-09-15",
        "nice_edition_claimed": "12th",
        "filing_type": "TEAS_PLUS",
        "fees_paid_count": 3,
        "total_fee_paid": 750.0,
        "amendment_requested": True,
        "amendment_affects_classes": [9],         # Only Class 9 amended
        "amendment_description": "clarify software identification",
        "division_requested": False,
        "surrender_requested": False,
        "post_filing_action_type": "",
        "classes": [
            {
                "class_number": 9,
                "identification": "Downloadable software for project management and team collaboration",
                "specimen_type": "website screenshot",
                "specimen_description": "website showing downloadable software for sale",
                "fee_paid": True,
                "filing_basis": "1(a)",
                "date_of_first_use": "2022-03-01",
                "date_of_first_use_commerce": "2022-04-15"
            },
            {
                "class_number": 42,
                "identification": "Software as a service for project management; cloud computing services for others",
                "specimen_type": "screenshot of service",
                "specimen_description": "screenshot of SaaS platform with mark",
                "fee_paid": True,
                "filing_basis": "1(a)",
                "date_of_first_use": "2022-05-01",
                "date_of_first_use_commerce": "2022-06-01"
            },
            {
                "class_number": 35,
                "identification": "Online marketplace services for software products; "
                                  "business management consulting services for others",
                "specimen_type": "advertisement",
                "specimen_description": "online advertisement for consulting services",
                "fee_paid": True,
                "filing_basis": "1(a)",
                "date_of_first_use": "2022-07-01",
                "date_of_first_use_commerce": "2022-07-15"
            }
        ]
    }

    result2 = run_full_pipeline(DEMO_APP_2)
    print("\n  COMBINED PIPELINE SUMMARY:")
    for k, v in result2["summary"].items():
        print(f"    {k:30s}: {v}")




# """
# TMEP CHAPTER 1403 — COMBINED OR MULTIPLE-CLASS APPLICATIONS
# PILLAR 3 ASSESSMENT ENGINE
# ==============================================================
# Based on: TMEP November 2025 Edition

# ════════════════════════════════════════════════════════════════
#   FULL PIPELINE FLOW
# ════════════════════════════════════════════════════════════════

#   ┌─────────────────────────────────────────────────────────┐
#   │  PILLAR 1  (tmep_1401_assessor.py)                      │
#   │  - Confirms/corrects class numbers                      │
#   │  - Validates specimens per class                        │
#   │  - Counts fees vs classes                               │
#   │  - Flags misclassifications                             │
#   │  OUTPUT: TrademarkApplication + List[AssessmentFinding] │
#   └──────────────────────────┬──────────────────────────────┘
#                              │
#                              ▼
#   ┌─────────────────────────────────────────────────────────┐
#   │  PILLAR 2  (tmep_1402_pillar2.py)                       │
#   │  - Checks identification specificity per class          │
#   │  - Validates services "for others" format               │
#   │  - Flags vague/indefinite terms                         │
#   │  - Cross-checks accuracy against specimen               │
#   │  OUTPUT: Dict[class_number → TMEP1402AnalysisResult]    │
#   └──────────────────────────┬──────────────────────────────┘
#                              │
#                              ▼
#   ┌─────────────────────────────────────────────────────────┐
#   │  PILLAR 3  (this file)                                  │
#   │  - §1403.01: Multi-class completeness checklist         │
#   │  - §1403.02: Amendment scope across classes             │
#   │  - §1403.03: Division eligibility analysis              │
#   │  - §1403.04: Partial refusal identification             │
#   │  - §1403.05: Post-filing fee verification               │
#   │  - §1403.06: Surrender/amendment in registrations       │
#   │  OUTPUT: Pillar3AssessmentResult (full report)          │
#   └─────────────────────────────────────────────────────────┘

# HOW PILLARS 1 AND 2 FEED PILLAR 3:
#   - Pillar 1 class errors    → §1403.04 partial refusal candidates
#   - Pillar 1 fee counts      → §1403.01 fee-per-class verification
#   - Pillar 1 specimen checks → §1403.01 per-class specimen requirement
#   - Pillar 1 filing_basis    → §1403.01 dates-of-use requirement
#   - Pillar 2 is_definite     → §1403.01 per-class identification check
#   - Pillar 2 errors          → §1403.04 adds to partial refusal scope
#   - Combined P1+P2 status    → §1403.03 division eligibility logic
# """

# from dataclasses import dataclass, field, asdict
# from typing import List, Dict, Optional
# from enum import Enum


# # ═══════════════════════════════════════════════════════════════════════════════
# # ENUMS
# # ═══════════════════════════════════════════════════════════════════════════════

# class ClassStatus(Enum):
#     """
#     Overall status of a single class in the multi-class application,
#     derived from combining Pillar 1 + Pillar 2 findings.
#     """
#     CLEAN       = "CLEAN"         # No errors or warnings from P1 or P2
#     HAS_WARNINGS = "HAS_WARNINGS" # Warnings only — can proceed with amendments
#     HAS_ERRORS  = "HAS_ERRORS"    # Errors present — blocked until resolved
#     REFUSAL_CANDIDATE = "REFUSAL_CANDIDATE"  # Strong refusal indicators present


# class ApplicationStage(Enum):
#     """Stage of the application lifecycle."""
#     PRE_FILING         = "PRE_FILING"
#     FILED_PENDING      = "FILED_PENDING"
#     OFFICE_ACTION      = "OFFICE_ACTION"
#     STATEMENT_OF_USE   = "STATEMENT_OF_USE"
#     REGISTERED         = "REGISTERED"
#     POST_REGISTRATION  = "POST_REGISTRATION"


# # ═══════════════════════════════════════════════════════════════════════════════
# # BRIDGE — Consolidated Per-Class Context from Pillars 1 and 2
# # ═══════════════════════════════════════════════════════════════════════════════

# @dataclass
# class ClassSummary:
#     """
#     Single source of truth for one class, consolidating
#     Pillar 1 ClassEntry data + Pillar 1 findings + Pillar 2 results.

#     Build one ClassSummary per class, then pass the full list to
#     Pillar3Assessor.
#     """
#     # ── Identity (from Pillar 1 ClassEntry) ──────────────────────────────────
#     class_number: int
#     class_title: str                    # e.g., "Scientific and Electronic Apparatus"
#     class_category: str                 # "GOODS" or "SERVICES"
#     identification: str                 # The full identification text
#     filing_basis: str                   # "1(a)", "1(b)", "44(d)", "44(e)", "66(a)"
#     specimen_type: str = ""
#     specimen_description: str = ""
#     date_of_first_use: Optional[str] = None
#     date_of_first_use_commerce: Optional[str] = None
#     fee_paid: bool = True

#     # ── Pillar 1 Findings Summary ─────────────────────────────────────────────
#     p1_error_count: int = 0
#     p1_warning_count: int = 0
#     p1_error_messages: List[str] = field(default_factory=list)

#     # ── Pillar 2 Findings Summary ─────────────────────────────────────────────
#     p2_is_definite: bool = True
#     p2_error_count: int = 0
#     p2_warning_count: int = 0
#     p2_error_messages: List[str] = field(default_factory=list)

#     # ── Computed Status (set by build_class_summary) ──────────────────────────
#     status: ClassStatus = ClassStatus.CLEAN

#     def has_any_error(self) -> bool:
#         return self.p1_error_count > 0 or self.p2_error_count > 0

#     def has_any_warning(self) -> bool:
#         return self.p1_warning_count > 0 or self.p2_warning_count > 0

#     def is_use_based(self) -> bool:
#         return self.filing_basis in ("1(a)", "44(e)")

#     def is_intent_to_use(self) -> bool:
#         return self.filing_basis == "1(b)"


# def build_class_summary(class_entry_dict: dict,
#                          p1_findings: list,
#                          p2_result_dict: Optional[dict] = None) -> ClassSummary:
#     """
#     Build a ClassSummary by combining:
#       - class_entry_dict: raw class data (from Pillar 1 ClassEntry or plain dict)
#       - p1_findings: list of Pillar 1 AssessmentFinding objects or dicts
#       - p2_result_dict: optional output dict from analyze_identification_under_tmep_1402()

#     Example:
#         summary = build_class_summary(
#             class_entry_dict={"class_number": 9, "identification": "...", ...},
#             p1_findings=pillar1_result["findings"],
#             p2_result_dict=pillar2_result_for_class9
#         )
#     """
#     cls_num = int(class_entry_dict.get("class_number", 0))

#     # ── Pull class metadata ───────────────────────────────────────────────────
#     class_title = class_entry_dict.get("class_title", "")
#     class_category = class_entry_dict.get("class_category", "")

#     if not class_title or not class_category:
#         try:
#             from nice_classification_db import get_class_info
#             info = get_class_info(cls_num)
#             if info:
#                 class_title = class_title or info["title"]
#                 class_category = class_category or info["category"]
#         except ImportError:
#             pass

#     # ── Pull Pillar 1 findings for this class ─────────────────────────────────
#     def _get(f, key):
#         return f[key] if isinstance(f, dict) else getattr(f, key, None)

#     cls_p1_findings = [
#         f for f in p1_findings
#         if _get(f, "class_number") == cls_num or _get(f, "class_number") == 0
#     ]
#     p1_errors = [f for f in cls_p1_findings if _get(f, "severity") == "ERROR"]
#     p1_warnings = [f for f in cls_p1_findings if _get(f, "severity") == "WARNING"]
#     p1_error_msgs = [str(_get(f, "finding"))[:100] for f in p1_errors[:3]]

#     # ── Pull Pillar 2 findings ────────────────────────────────────────────────
#     p2_is_definite = True
#     p2_errors = 0
#     p2_warnings = 0
#     p2_error_msgs = []

#     if p2_result_dict:
#         summary = p2_result_dict.get("summary", {})
#         p2_is_definite = summary.get("is_definite", True)
#         p2_errors = summary.get("errors", 0)
#         p2_warnings = summary.get("warnings", 0)
#         analysis = p2_result_dict.get("tmep_1402_analysis", {})
#         for sf in analysis.get("subsection_findings", []):
#             if isinstance(sf, dict) and sf.get("severity") == "ERROR":
#                 p2_error_msgs.append(sf.get("finding", "")[:100])

#     # ── Compute status ────────────────────────────────────────────────────────
#     total_errors = len(p1_errors) + p2_errors
#     total_warnings = len(p1_warnings) + p2_warnings

#     if total_errors >= 3:
#         status = ClassStatus.REFUSAL_CANDIDATE
#     elif total_errors > 0:
#         status = ClassStatus.HAS_ERRORS
#     elif total_warnings > 0:
#         status = ClassStatus.HAS_WARNINGS
#     else:
#         status = ClassStatus.CLEAN

#     return ClassSummary(
#         class_number=cls_num,
#         class_title=class_title,
#         class_category=class_category,
#         identification=class_entry_dict.get("identification", ""),
#         filing_basis=class_entry_dict.get("filing_basis", "1(a)"),
#         specimen_type=class_entry_dict.get("specimen_type", ""),
#         specimen_description=class_entry_dict.get("specimen_description", ""),
#         date_of_first_use=class_entry_dict.get("date_of_first_use"),
#         date_of_first_use_commerce=class_entry_dict.get("date_of_first_use_commerce"),
#         fee_paid=class_entry_dict.get("fee_paid", True),
#         p1_error_count=len(p1_errors),
#         p1_warning_count=len(p1_warnings),
#         p1_error_messages=p1_error_msgs,
#         p2_is_definite=p2_is_definite,
#         p2_error_count=p2_errors,
#         p2_warning_count=p2_warnings,
#         p2_error_messages=p2_error_msgs,
#         status=status
#     )


# # ═══════════════════════════════════════════════════════════════════════════════
# # APPLICATION-LEVEL CONTEXT (carries fee + stage info across all classes)
# # ═══════════════════════════════════════════════════════════════════════════════

# @dataclass
# class MultiClassApplicationContext:
#     """
#     Application-level context for the multi-class assessment.
#     Most fields come directly from the TrademarkApplication (Pillar 1 input).
#     """
#     applicant_name: str = ""
#     mark_text: str = ""
#     filing_date: str = ""
#     filing_type: str = "TEAS_PLUS"             # TEAS_PLUS | TEAS_STANDARD | PAPER
#     fees_paid_count: int = 0                   # Total fees actually submitted
#     total_fee_paid: float = 0.0
#     application_stage: ApplicationStage = ApplicationStage.FILED_PENDING

#     # Amendment context (populated when an amendment is being assessed)
#     amendment_requested: bool = False
#     amendment_affects_classes: List[int] = field(default_factory=list)  # [] = all
#     amendment_description: str = ""

#     # Division context
#     division_requested: bool = False
#     classes_to_divide_out: List[int] = field(default_factory=list)

#     # Post-registration context
#     surrender_requested: bool = False
#     classes_to_surrender: List[int] = field(default_factory=list)
#     post_filing_action_type: str = ""    # "amendment", "response", "surrender", ""


# # ═══════════════════════════════════════════════════════════════════════════════
# # FINDING MODEL
# # ═══════════════════════════════════════════════════════════════════════════════

# @dataclass
# class Pillar3Finding:
#     """A single finding for one §1403.xx check."""
#     tmep_section: str       # §1403.01 through §1403.06
#     severity: str           # ERROR | WARNING | INFO | OK
#     class_number: int       # 0 = application-level
#     item: str
#     finding: str
#     recommendation: str
#     # Cross-pillar link: which P1/P2 finding triggered this
#     triggered_by: str = ""  # e.g. "P1:§1401.04", "P2:§1402.03"


# @dataclass
# class Pillar3AssessmentResult:
#     """Complete Pillar 3 output."""
#     findings: List[Pillar3Finding] = field(default_factory=list)

#     # §1403.03 output
#     division_eligible_classes: List[int] = field(default_factory=list)
#     division_recommended: bool = False

#     # §1403.04 output
#     partial_refusal_classes: List[int] = field(default_factory=list)
#     partial_refusal_reasons: Dict[int, str] = field(default_factory=dict)

#     # Overall
#     is_multi_class_compliant: bool = True
#     total_errors: int = 0
#     total_warnings: int = 0


# # ═══════════════════════════════════════════════════════════════════════════════
# # PILLAR 3 ASSESSOR
# # ═══════════════════════════════════════════════════════════════════════════════

# class Pillar3Assessor:
#     """
#     Runs all §1403.01–§1403.06 checks on a multi-class application,
#     using consolidated ClassSummary objects built from Pillars 1 and 2.
#     """

#     USPTO_FEES = {
#         "TEAS_PLUS": 250,
#         "TEAS_STANDARD": 350,
#         "PAPER": 750
#     }

#     def __init__(self,
#                  class_summaries: List[ClassSummary],
#                  app_context: MultiClassApplicationContext):
#         self.classes = class_summaries
#         self.ctx = app_context
#         self.findings: List[Pillar3Finding] = []

#     # ─────────────────────────────────────────────────────────────────────────
#     # ENTRY POINT
#     # ─────────────────────────────────────────────────────────────────────────

#     def run_full_assessment(self) -> Pillar3AssessmentResult:
#         """Run all §1403 checks in sequence and return the full result."""
#         self.findings.clear()

#         # Guard: single-class apps don't need §1403 analysis
#         unique_classes = list({c.class_number for c in self.classes})
#         if len(unique_classes) < 2:
#             self.findings.append(Pillar3Finding(
#                 tmep_section="§1403",
#                 severity="INFO",
#                 class_number=0,
#                 item="Single-class application",
#                 finding="Application contains only one class. "
#                         "§1403 multi-class requirements do not apply.",
#                 recommendation="No §1403 action required."
#             ))
#             return self._build_result([], [], {})

#         self._check_1403_01_multi_class_requirements()
#         amendment_conflicts = self._check_1403_02_amendment_review()
#         division_eligible = self._check_1403_03_division_eligibility()
#         refusal_classes, refusal_reasons = self._check_1403_04_partial_refusals()
#         self._check_1403_05_post_filing_fees()
#         self._check_1403_06_surrender_or_amendment()

#         return self._build_result(division_eligible, refusal_classes, refusal_reasons)

#     # ─────────────────────────────────────────────────────────────────────────
#     # §1403.01 — REQUIREMENTS FOR COMBINED OR MULTIPLE-CLASS APPLICATIONS
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1403_01_multi_class_requirements(self):
#         """
#         §1403.01 — Five-point completeness checklist for every class.

#         PILLAR INTEGRATION:
#           P1 → fee_paid, specimen checks, correct class assignment
#           P2 → identification definiteness (is_definite)
#           P1 → filing_basis for dates-of-use requirement
#         """
#         section = "§1403.01"
#         all_clean = True

#         for cls in self.classes:
#             cls_label = f"Class {cls.class_number} ({cls.class_title})"

#             # ── CHECK 1: Each class has its own separate identification ───────
#             if not cls.identification or len(cls.identification.strip()) < 5:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="ERROR",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Missing identification",
#                     finding="No identification of goods/services found for this class. "
#                              "Every class in a multi-class application must have its own "
#                              "separate identification.",
#                     recommendation="Provide a complete identification of goods/services "
#                                    "for this class.",
#                     triggered_by="P1:ClassEntry.identification"
#                 ))
#                 all_clean = False
#             elif not cls.p2_is_definite:
#                 # Pillar 2 found the identification non-definite — surface that here
#                 p2_issues = "; ".join(cls.p2_error_messages[:2]) if cls.p2_error_messages else \
#                             "Identification does not meet §1402 specificity standards"
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="ERROR",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Identification not definite (Pillar 2)",
#                     finding=f"Pillar 2 (§1402) determined the identification for "
#                              f"{cls_label} is NOT sufficiently definite. "
#                              f"Issues: {p2_issues}",
#                     recommendation="Amend the identification to meet §1402 specificity "
#                                    "requirements before this class can be accepted in "
#                                    "a multi-class application.",
#                     triggered_by="P2:§1402.03"
#                 ))
#                 all_clean = False
#             else:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="OK",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Identification",
#                     finding="Separate, definite identification present for this class.",
#                     recommendation="No action required."
#                 ))

#             # ── CHECK 2: Each class has its own fee paid ──────────────────────
#             # Pillar 1 sets fee_paid per class
#             if not cls.fee_paid:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="ERROR",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Fee not paid",
#                     finding=f"No filing fee was paid for {cls_label}. "
#                              "Every class in a multi-class application requires "
#                              "a separate filing fee.",
#                     recommendation=f"Submit the per-class fee "
#                                    f"(${self.USPTO_FEES.get(self.ctx.filing_type, 350)}) "
#                                    f"for {cls_label} to avoid deletion of this class.",
#                     triggered_by="P1:§1401.04"
#                 ))
#                 all_clean = False
#             else:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="OK",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Fee",
#                     finding="Fee paid for this class.",
#                     recommendation="No action required."
#                 ))

#             # ── CHECK 3: Each class has its own specimen (use-based) ──────────
#             if cls.is_use_based():
#                 if not cls.specimen_type and not cls.specimen_description:
#                     self.findings.append(Pillar3Finding(
#                         tmep_section=section,
#                         severity="ERROR",
#                         class_number=cls.class_number,
#                         item=f"{cls_label} — Specimen missing",
#                         finding=f"No specimen provided for {cls_label}. "
#                                  "Use-based applications (§1(a)) require a separate "
#                                  "specimen for each class showing the mark in actual use.",
#                         recommendation="Submit a specimen showing the mark in actual commercial "
#                                        "use in connection with the goods/services in this class.",
#                         triggered_by="P1:§1401.06"
#                     ))
#                     all_clean = False
#                 elif cls.p1_error_count > 0 and any(
#                         "specimen" in m.lower() for m in cls.p1_error_messages):
#                     # Pillar 1 already flagged a specimen error — surface it in §1403 context
#                     self.findings.append(Pillar3Finding(
#                         tmep_section=section,
#                         severity="ERROR",
#                         class_number=cls.class_number,
#                         item=f"{cls_label} — Specimen invalid (Pillar 1)",
#                         finding=f"Pillar 1 detected a specimen issue for {cls_label}: "
#                                  f"{'; '.join(m for m in cls.p1_error_messages if 'specimen' in m.lower())[:120]}",
#                         recommendation="Replace the specimen with an acceptable one for this class. "
#                                        "Each class must have its own valid specimen.",
#                         triggered_by="P1:§1401.06"
#                     ))
#                     all_clean = False
#                 else:
#                     self.findings.append(Pillar3Finding(
#                         tmep_section=section,
#                         severity="OK",
#                         class_number=cls.class_number,
#                         item=f"{cls_label} — Specimen",
#                         finding=f"Specimen present: '{cls.specimen_type}'.",
#                         recommendation="No action required."
#                     ))
#             else:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="INFO",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Specimen (§1(b))",
#                     finding=f"Intent-to-use basis ({cls.filing_basis}). "
#                              "No specimen required at this stage.",
#                     recommendation="Specimen must be submitted with Statement of Use."
#                 ))

#             # ── CHECK 4: Goods/services correctly assigned to class ───────────
#             # Pillar 1 §1401.03 errors are the primary signal here
#             p1_class_errors = [m for m in cls.p1_error_messages
#                                if any(kw in m.lower() for kw in
#                                       ["misclassif", "class", "wrong", "incorrect", "reclassif"])]

#             if p1_class_errors:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="ERROR",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Classification issue (Pillar 1)",
#                     finding=f"Pillar 1 (§1401.03) detected incorrect class assignment for "
#                              f"{cls_label}: {p1_class_errors[0][:120]}",
#                     recommendation="Correct the class assignment per Pillar 1 recommendations "
#                                    "before proceeding with multi-class filing requirements.",
#                     triggered_by="P1:§1401.03"
#                 ))
#                 all_clean = False
#             else:
#                 has_p1_class_warning = cls.p1_warning_count > 0
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="WARNING" if has_p1_class_warning else "OK",
#                     class_number=cls.class_number,
#                     item=f"{cls_label} — Class assignment",
#                     finding=(f"Pillar 1 raised {cls.p1_warning_count} warning(s) about the "
#                               "class assignment — review recommended."
#                               if has_p1_class_warning else
#                               "No class assignment errors detected for this class."),
#                     recommendation=("Review Pillar 1 warnings for this class."
#                                     if has_p1_class_warning else "No action required."),
#                     triggered_by="P1:§1401.03"
#                 ))

#             # ── CHECK 5: Dates of use provided per class (use-based) ──────────
#             if cls.is_use_based():
#                 missing_dates = []
#                 if not cls.date_of_first_use:
#                     missing_dates.append("date of first use anywhere")
#                 if not cls.date_of_first_use_commerce:
#                     missing_dates.append("date of first use in commerce")

#                 if missing_dates:
#                     self.findings.append(Pillar3Finding(
#                         tmep_section=section,
#                         severity="WARNING",
#                         class_number=cls.class_number,
#                         item=f"{cls_label} — Missing dates of use",
#                         finding=f"Missing for {cls_label}: {', '.join(missing_dates)}. "
#                                  "Per §1403.01, dates of use must be provided separately "
#                                  "for each class in a use-based application.",
#                         recommendation="Add separate dates of first use (anywhere) and "
#                                        "first use in commerce for this class.",
#                         triggered_by="P1:ClassEntry.date_of_first_use"
#                     ))
#                     all_clean = False
#                 else:
#                     self.findings.append(Pillar3Finding(
#                         tmep_section=section,
#                         severity="OK",
#                         class_number=cls.class_number,
#                         item=f"{cls_label} — Dates of use",
#                         finding=f"First use: {cls.date_of_first_use} | "
#                                  f"First use in commerce: {cls.date_of_first_use_commerce}",
#                         recommendation="No action required."
#                     ))

#         # ── Application-level fee count cross-check ───────────────────────────
#         # (Pillar 1 §1401.04 already caught this, but §1403.01 requires us to
#         #  confirm fees in the multi-class context specifically)
#         unique_cls_count = len({c.class_number for c in self.classes})
#         fees_paid = self.ctx.fees_paid_count

#         if fees_paid > 0 and fees_paid != unique_cls_count:
#             shortage = unique_cls_count - fees_paid
#             severity = "ERROR" if shortage > 0 else "WARNING"
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity=severity,
#                 class_number=0,
#                 item=f"Application-level fee count: {fees_paid} paid, "
#                      f"{unique_cls_count} classes",
#                 finding=f"{'UNDERPAYMENT' if shortage > 0 else 'OVERPAYMENT'}: "
#                          f"{fees_paid} fee(s) submitted but {unique_cls_count} class(es) filed. "
#                          f"{'Shortage: ' + str(abs(shortage)) + ' fee(s).' if shortage > 0 else 'Excess: ' + str(abs(shortage)) + ' fee(s).'}",
#                 recommendation=(
#                     f"Submit {abs(shortage)} additional fee(s) at "
#                     f"${self.USPTO_FEES.get(self.ctx.filing_type, 350)}/class. "
#                     "Unpaid classes will be deleted."
#                     if shortage > 0 else
#                     "Request refund for excess fees or add additional classes."
#                 ),
#                 triggered_by="P1:§1401.04"
#             ))
#         elif fees_paid > 0:
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="OK",
#                 class_number=0,
#                 item="Application-level fee count",
#                 finding=f"Fee count matches class count: "
#                          f"{fees_paid} fee(s) for {unique_cls_count} class(es).",
#                 recommendation="No action required."
#             ))

#     # ─────────────────────────────────────────────────────────────────────────
#     # §1403.02 — AMENDMENT OF COMBINED OR MULTIPLE-CLASS APPLICATION
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1403_02_amendment_review(self) -> List[int]:
#         """
#         §1403.02 — Amendments in multi-class applications.

#         Key rules:
#         1. An amendment to one class must not inadvertently broaden/alter another.
#         2. Amendment cannot add new goods/services not in the original scope.
#         3. Each amended class may require additional fees.

#         Returns: list of class numbers with potential cross-class conflicts.
#         """
#         section = "§1403.02"
#         conflict_classes = []

#         if not self.ctx.amendment_requested:
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item="No amendment in this assessment",
#                 finding="No amendment has been requested. §1403.02 amendment rules "
#                          "are noted for reference.",
#                 recommendation="When filing any amendment, ensure changes are "
#                                "class-specific and do not affect other classes."
#             ))
#             return []

#         affected = self.ctx.amendment_affects_classes
#         all_class_numbers = [c.class_number for c in self.classes]

#         # ── If amendment description says "all classes" or affects all ────────
#         if not affected or set(affected) == set(all_class_numbers):
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="WARNING",
#                 class_number=0,
#                 item="Amendment scope: ALL classes",
#                 finding=f"The requested amendment appears to affect all classes "
#                          f"({', '.join(f'Class {c}' for c in sorted(all_class_numbers))}). "
#                          "An application-wide amendment must be reviewed carefully to ensure "
#                          "it does not inadvertently narrow or alter classes that don't need changing.",
#                 recommendation="Confirm which classes actually need amendment. "
#                                "File class-specific amendments where possible to avoid "
#                                "unintended scope changes across classes.",
#             ))
#         else:
#             # Amendment affects specific classes — check for cross-class conflicts
#             non_affected = [c for c in all_class_numbers if c not in affected]

#             for cls in self.classes:
#                 if cls.class_number not in affected:
#                     continue

#                 # Check: does the amended class identification share any keywords
#                 # with non-amended classes? (potential overlap after amendment)
#                 amended_words = set(cls.identification.lower().split())
#                 for other_cls in self.classes:
#                     if other_cls.class_number in affected:
#                         continue
#                     other_words = set(other_cls.identification.lower().split())
#                     shared = amended_words & other_words - {
#                         "and", "or", "for", "the", "of", "in", "a", "an",
#                         "to", "with", "by", "from", "on", "at"
#                     }

#                     if len(shared) >= 3:
#                         conflict_classes.append(cls.class_number)
#                         self.findings.append(Pillar3Finding(
#                             tmep_section=section,
#                             severity="WARNING",
#                             class_number=cls.class_number,
#                             item=f"Cross-class amendment conflict: "
#                                  f"Class {cls.class_number} ↔ Class {other_cls.class_number}",
#                             finding=f"Amending Class {cls.class_number} may affect Class "
#                                      f"{other_cls.class_number} — they share terminology: "
#                                      f"{', '.join(list(shared)[:5])}. "
#                                      "Per §1403.02, amendments to one class must not "
#                                      "inadvertently alter the scope of another.",
#                             recommendation=f"Review whether the amendment to Class {cls.class_number} "
#                                            f"creates any scope overlap with Class {other_cls.class_number}. "
#                                            "Amend each class separately with distinct language.",
#                             triggered_by=f"P1+P2:Class{cls.class_number}↔Class{other_cls.class_number}"
#                         ))

#             if not conflict_classes:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="OK",
#                     class_number=0,
#                     item=f"Amendment scope: Class(es) "
#                          f"{', '.join(str(c) for c in sorted(affected))} only",
#                     finding=f"Amendment is limited to Class(es) "
#                              f"{', '.join(str(c) for c in sorted(affected))}. "
#                              "No obvious cross-class terminology conflicts detected.",
#                     recommendation="Ensure the amendment is filed with correct class-specific "
#                                    "language and any required additional fees."
#                 ))

#         # ── Amendment broadening guard ────────────────────────────────────────
#         if self.ctx.amendment_description:
#             broadening_keywords = [
#                 "add", "adding", "expand", "include", "broader", "additional",
#                 "new goods", "new services", "new class"
#             ]
#             desc_lower = self.ctx.amendment_description.lower()
#             if any(kw in desc_lower for kw in broadening_keywords):
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="ERROR",
#                     class_number=0,
#                     item="Amendment may attempt to broaden scope",
#                     finding=f"Amendment description '{self.ctx.amendment_description[:80]}' "
#                              "contains language suggesting scope broadening. "
#                              "Per §1402.07 (applied through §1403.02), amendments cannot "
#                              "expand the identification beyond the original filing scope.",
#                     recommendation="Amendments may only CLARIFY or LIMIT the identification. "
#                                    "Remove any language that adds new goods/services not "
#                                    "encompassed by the original filing."
#                 ))

#         return conflict_classes

#     # ─────────────────────────────────────────────────────────────────────────
#     # §1403.03 — DIVIDING OF COMBINED OR MULTIPLE-CLASS APPLICATION
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1403_03_division_eligibility(self) -> List[int]:
#         """
#         §1403.03 — An applicant can divide a multi-class application to let
#         clean classes proceed while problematic ones are resolved separately.

#         PILLAR INTEGRATION:
#           - Classes with P1 errors OR P2 errors are division candidates
#           - Classes without errors can be separated to proceed to registration
#           - Division is especially useful when some classes are §1(a) and
#             others are §1(b)

#         Returns: list of class numbers eligible/recommended for division.
#         """
#         section = "§1403.03"
#         division_eligible = []

#         # Classes with errors that would benefit from division
#         error_classes = [c for c in self.classes if c.has_any_error()]
#         clean_classes = [c for c in self.classes if not c.has_any_error()]

#         # Classes with mixed filing bases (classic division trigger)
#         use_based = [c for c in self.classes if c.is_use_based()]
#         intent_to_use = [c for c in self.classes if c.is_intent_to_use()]

#         # ── Case 1: Specific division requested by applicant ──────────────────
#         if self.ctx.division_requested:
#             to_divide = self.ctx.classes_to_divide_out
#             remaining = [c.class_number for c in self.classes
#                         if c.class_number not in to_divide]

#             # Verify divided classes meet standalone requirements
#             for cls_num in to_divide:
#                 cls = next((c for c in self.classes if c.class_number == cls_num), None)
#                 if not cls:
#                     continue

#                 issues = []
#                 if not cls.identification.strip():
#                     issues.append("missing identification")
#                 if cls.is_use_based() and not cls.specimen_type:
#                     issues.append("missing specimen")
#                 if not cls.fee_paid:
#                     issues.append("fee not paid")

#                 if issues:
#                     self.findings.append(Pillar3Finding(
#                         tmep_section=section,
#                         severity="ERROR",
#                         class_number=cls_num,
#                         item=f"Class {cls_num} — Cannot divide: incomplete requirements",
#                         finding=f"Class {cls_num} cannot be divided out because it does "
#                                  f"not meet standalone filing requirements: "
#                                  f"{', '.join(issues)}. A divided application must be "
#                                  "complete in itself.",
#                         recommendation="Resolve these issues before dividing: "
#                                        f"{', '.join(issues)}."
#                     ))
#                 else:
#                     division_eligible.append(cls_num)
#                     self.findings.append(Pillar3Finding(
#                         tmep_section=section,
#                         severity="OK",
#                         class_number=cls_num,
#                         item=f"Class {cls_num} — Division eligible",
#                         finding=f"Class {cls_num} meets all standalone requirements "
#                                  "and can be divided into its own application.",
#                         recommendation=f"Proceed with division request for Class {cls_num}. "
#                                        "The child application will carry forward the "
#                                        "original filing date."
#                     ))

#             if remaining:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="INFO",
#                     class_number=0,
#                     item=f"Remaining after division: "
#                          f"Class(es) {', '.join(str(r) for r in sorted(remaining))}",
#                     finding=f"After dividing out Class(es) "
#                              f"{', '.join(str(d) for d in sorted(to_divide))}, "
#                              f"the parent application retains "
#                              f"Class(es) {', '.join(str(r) for r in sorted(remaining))}.",
#                     recommendation="Verify the parent application remains complete "
#                                    "and all retained classes are properly supported."
#                 ))

#         # ── Case 2: No division requested — assess recommendation ─────────────
#         else:
#             if error_classes and clean_classes:
#                 error_cls_nums = [c.class_number for c in error_classes]
#                 clean_cls_nums = [c.class_number for c in clean_classes]
#                 division_eligible = clean_cls_nums

#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="WARNING",
#                     class_number=0,
#                     item=f"Division RECOMMENDED — Clean vs. problem classes detected",
#                     finding=f"DIVISION ANALYSIS (§1403.03): "
#                              f"Class(es) {', '.join(f'Class {n}' for n in sorted(clean_cls_nums))} "
#                              f"are clean, but "
#                              f"Class(es) {', '.join(f'Class {n}' for n in sorted(error_cls_nums))} "
#                              f"have errors. Without division, the errors in "
#                              f"{', '.join(f'Class {n}' for n in sorted(error_cls_nums))} "
#                              "will delay registration for the clean classes too.",
#                     recommendation=f"Consider dividing Class(es) "
#                                    f"{', '.join(str(n) for n in sorted(clean_cls_nums))} "
#                                    "into a separate application so they can proceed to "
#                                    "registration independently. "
#                                    "File a Request to Divide (USPTO Form PTO-2302)."
#                 ))

#             elif use_based and intent_to_use:
#                 itu_nums = [c.class_number for c in intent_to_use]
#                 use_nums = [c.class_number for c in use_based]

#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="INFO",
#                     class_number=0,
#                     item=f"Mixed filing basis — potential division candidate",
#                     finding=f"Application has mixed filing bases: "
#                              f"Class(es) {', '.join(str(n) for n in sorted(use_nums))} "
#                              f"are §1(a) use-based; "
#                              f"Class(es) {', '.join(str(n) for n in sorted(itu_nums))} "
#                              "are §1(b) intent-to-use. "
#                              "The §1(b) classes cannot achieve registration until a "
#                              "Statement of Use is filed, which may delay the §1(a) classes.",
#                     recommendation=f"Consider dividing the §1(a) classes "
#                                    f"({', '.join(str(n) for n in sorted(use_nums))}) "
#                                    "so they can proceed to registration independently "
#                                    "of the §1(b) classes."
#                 ))
#                 division_eligible = use_nums

#             else:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="INFO",
#                     class_number=0,
#                     item="Division not currently indicated",
#                     finding="All classes appear to be at the same stage with similar "
#                              "issue profiles. Division is not currently recommended.",
#                     recommendation="Monitor application progress. Division may become "
#                                    "appropriate if one class receives a specific refusal."
#                 ))

#         return division_eligible

#     # ─────────────────────────────────────────────────────────────────────────
#     # §1403.04 — REFUSALS AS TO LESS THAN ALL CLASSES
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1403_04_partial_refusals(self) -> tuple:
#         """
#         §1403.04 — A refusal can apply to some classes but not all.
#         A class with errors should receive a targeted refusal, not invalidate
#         the entire application.

#         PILLAR INTEGRATION (key method for P1 + P2 convergence):
#           - P1 errors (misclassification, bad specimen, wrong class) → refusal
#           - P2 non-definite identification → refusal
#           - Clean classes → explicitly noted as proceeding

#         Returns: (refusal_class_numbers, refusal_reasons_dict)
#         """
#         section = "§1403.04"
#         refusal_classes = []
#         refusal_reasons: Dict[int, str] = {}

#         for cls in self.classes:
#             reasons = []

#             # ── Collect P1 error reasons ──────────────────────────────────────
#             if cls.p1_error_count > 0:
#                 for msg in cls.p1_error_messages[:2]:
#                     reasons.append(f"[Pillar 1 — §1401] {msg[:100]}")

#             # ── Collect P2 error reasons ──────────────────────────────────────
#             if not cls.p2_is_definite or cls.p2_error_count > 0:
#                 for msg in cls.p2_error_messages[:2]:
#                     reasons.append(f"[Pillar 2 — §1402] {msg[:100]}")
#                 if not cls.p2_is_definite and not cls.p2_error_messages:
#                     reasons.append("[Pillar 2 — §1402] Identification is not sufficiently definite.")

#             if reasons:
#                 refusal_classes.append(cls.class_number)
#                 refusal_reasons[cls.class_number] = "; ".join(reasons)

#                 severity = "ERROR" if cls.status == ClassStatus.REFUSAL_CANDIDATE else "WARNING"
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity=severity,
#                     class_number=cls.class_number,
#                     item=f"Class {cls.class_number} — PARTIAL REFUSAL CANDIDATE",
#                     finding=f"Class {cls.class_number} ({cls.class_title}) has "
#                              f"{cls.p1_error_count} Pillar 1 error(s) and "
#                              f"{cls.p2_error_count} Pillar 2 error(s) that constitute "
#                              f"grounds for a PARTIAL REFUSAL under §1403.04. "
#                              f"Reasons: {'; '.join(reasons[:2])}",
#                     recommendation=f"Issue a partial refusal limited to Class {cls.class_number}. "
#                                    "Do NOT refuse the entire application — other classes "
#                                    "should continue to be processed. "
#                                    "State each ground of refusal clearly in the Office Action.",
#                     triggered_by=f"P1:{cls.p1_error_count}errors + P2:{cls.p2_error_count}errors"
#                 ))
#             else:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="OK",
#                     class_number=cls.class_number,
#                     item=f"Class {cls.class_number} — No refusal grounds",
#                     finding=f"Class {cls.class_number} ({cls.class_title}) has no "
#                              "errors from Pillar 1 or Pillar 2. No refusal is indicated "
#                              "for this class.",
#                     recommendation="This class may proceed independently. "
#                                    "Consider division if other classes face refusals."
#                 ))

#         # ── Application-level refusal summary ────────────────────────────────
#         if refusal_classes:
#             non_refusal = [c.class_number for c in self.classes
#                           if c.class_number not in refusal_classes]
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item=f"Partial refusal summary",
#                 finding=f"PARTIAL REFUSAL applies to: "
#                          f"Class(es) {', '.join(str(c) for c in sorted(refusal_classes))}. "
#                          f"Classes NOT subject to refusal: "
#                          f"{', '.join(str(c) for c in sorted(non_refusal)) if non_refusal else 'None'}.",
#                 recommendation="Issue Office Action with partial refusal. "
#                                "For each refused class, cite the specific legal ground. "
#                                "For clean classes, note they are approved or being processed."
#             ))

#         return refusal_classes, refusal_reasons

#     # ─────────────────────────────────────────────────────────────────────────
#     # §1403.05 — FEES FOR POST-FILING ACTIONS, MULTIPLE CLASSES
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1403_05_post_filing_fees(self):
#         """
#         §1403.05 — When post-filing actions (responses, amendments, SOU) are
#         filed in a multi-class application, the correct per-class fee must
#         accompany actions for each affected class.
#         """
#         section = "§1403.05"
#         stage = self.ctx.application_stage
#         action = self.ctx.post_filing_action_type
#         fee_per_class = self.USPTO_FEES.get(self.ctx.filing_type, 350)

#         # No post-filing action in this assessment
#         if not action and stage in (ApplicationStage.PRE_FILING,
#                                      ApplicationStage.FILED_PENDING):
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item="No post-filing action in this assessment",
#                 finding="Application is at filing/pending stage. "
#                          "§1403.05 post-filing fee requirements will apply if/when "
#                          "responses, amendments, or Statements of Use are filed.",
#                 recommendation="When filing any post-filing action, ensure the "
#                                "correct per-class fee is included for each affected class."
#             ))
#             return

#         # Statement of Use (SOU) — intent-to-use classes
#         itu_classes = [c for c in self.classes if c.is_intent_to_use()]
#         if stage == ApplicationStage.STATEMENT_OF_USE or action == "sou":
#             if itu_classes:
#                 sou_fee_total = len(itu_classes) * 100  # $100/class SOU fee (USPTO 2025)
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="INFO",
#                     class_number=0,
#                     item=f"Statement of Use — {len(itu_classes)} class(es)",
#                     finding=f"Statement of Use being filed for "
#                              f"{len(itu_classes)} §1(b) class(es): "
#                              f"{', '.join(f'Class {c.class_number}' for c in itu_classes)}. "
#                              f"SOU fee: $100/class × {len(itu_classes)} = ${sou_fee_total}.",
#                     recommendation=f"Submit SOU with ${sou_fee_total} total "
#                                    f"(${100}/class for each of the "
#                                    f"{len(itu_classes)} §1(b) class(es)). "
#                                    "Each class needs its own specimen with the SOU."
#                 ))

#         # Amendment response with fees
#         if action in ("amendment", "response") and self.ctx.amendment_affects_classes:
#             affected_count = len(self.ctx.amendment_affects_classes)
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item=f"Post-filing {action} fee — "
#                      f"{affected_count} class(es) affected",
#                 finding=f"Post-filing {action} affects "
#                          f"{affected_count} class(es): "
#                          f"{', '.join(f'Class {c}' for c in sorted(self.ctx.amendment_affects_classes))}. "
#                          "Verify whether additional per-class fees are required "
#                          "for this type of action.",
#                 recommendation=f"Check USPTO fee schedule for post-filing {action} fees. "
#                                f"Ensure fee is submitted for each of the "
#                                f"{affected_count} affected class(es)."
#             ))

#         # Surrender fees (if applicable)
#         if self.ctx.surrender_requested and self.ctx.classes_to_surrender:
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item=f"Surrender fee check — "
#                      f"Class(es) {', '.join(str(c) for c in self.ctx.classes_to_surrender)}",
#                 finding="Partial surrender of classes in a multi-class registration. "
#                          "Verify whether any petition or maintenance fees apply "
#                          "to the surrender action.",
#                 recommendation="File a Section 7 Request for Amendment/Surrender "
#                                "(USPTO Form) with required fees for each surrendered class."
#             ))

#         # General multi-class post-filing reminder
#         self.findings.append(Pillar3Finding(
#             tmep_section=section,
#             severity="INFO",
#             class_number=0,
#             item="Multi-class post-filing fee rule",
#             finding="Per §1403.05: in multi-class applications, post-filing actions "
#                      "require separate fees for each class to which the action applies. "
#                      "A single fee does not cover all classes automatically.",
#             recommendation="Always verify the number of classes affected by any "
#                            "post-filing action and submit the correct per-class fee amount."
#         ))

#     # ─────────────────────────────────────────────────────────────────────────
#     # §1403.06 — SURRENDER OR AMENDMENT IN MULTI-CLASS REGISTRATIONS
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1403_06_surrender_or_amendment(self):
#         """
#         §1403.06 — After registration, an applicant can surrender one or more
#         classes while keeping others. Checks that surrendering a class doesn't
#         create scope inconsistencies in the remaining classes.
#         """
#         section = "§1403.06"
#         stage = self.ctx.application_stage

#         # Only relevant post-registration
#         if stage not in (ApplicationStage.REGISTERED,
#                           ApplicationStage.POST_REGISTRATION):
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item=f"§1403.06 — Not yet registered (stage: {stage.value})",
#                 finding="Application has not yet reached registration. "
#                          "§1403.06 surrender and post-registration amendment rules "
#                          "will apply after registration is granted.",
#                 recommendation="Note for post-registration: partial surrender is possible "
#                                "via Section 7 amendment. Surrendering a class is irrevocable."
#             ))
#             return

#         if not self.ctx.surrender_requested:
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item="No surrender requested",
#                 finding="No surrender of classes has been requested in this assessment.",
#                 recommendation="If a partial surrender is needed post-registration, "
#                                "file a Section 7 Request (USPTO Form SB/08). "
#                                "Surrender is irrevocable — once a class is surrendered, "
#                                "it cannot be reinstated."
#             ))
#             return

#         to_surrender = self.ctx.classes_to_surrender
#         to_retain = [c for c in self.classes
#                      if c.class_number not in to_surrender]

#         # ── Validate surrender doesn't leave registration empty ───────────────
#         if len(to_surrender) >= len(self.classes):
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="ERROR",
#                 class_number=0,
#                 item="Full surrender — entire registration would be abandoned",
#                 finding="Surrendering all classes would result in complete abandonment "
#                          "of the registration. If that is the intent, a full cancellation "
#                          "should be filed instead.",
#                 recommendation="File a Request for Cancellation (USPTO Form) if the intent "
#                                "is to abandon the entire registration. "
#                                "For partial surrender, retain at least one class."
#             ))
#             return

#         # ── Check for scope inconsistencies in retained classes ───────────────
#         surrendered_cls_objects = [c for c in self.classes
#                                    if c.class_number in to_surrender]
#         retained_id_words = set()
#         for rc in to_retain:
#             retained_id_words.update(rc.identification.lower().split())

#         inconsistency_found = False
#         for sc in surrendered_cls_objects:
#             surrendered_words = set(sc.identification.lower().split()) - {
#                 "and", "or", "for", "the", "of", "in", "a", "an", "to",
#                 "with", "by", "from", "on", "at", "namely", "including"
#             }
#             overlap_with_retained = surrendered_words & retained_id_words
#             significant_overlap = [w for w in overlap_with_retained if len(w) > 4]

#             if significant_overlap:
#                 inconsistency_found = True
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="WARNING",
#                     class_number=sc.class_number,
#                     item=f"Scope overlap: surrendering Class {sc.class_number} "
#                          f"while retaining other classes",
#                     finding=f"Surrendering Class {sc.class_number} ({sc.class_title}) "
#                              f"may create inconsistency with retained classes. "
#                              f"Shared terminology between surrendered and retained "
#                              f"identifications: {', '.join(significant_overlap[:5])}. "
#                              "After surrender, consumers may be confused about the "
#                              "scope of the remaining registration.",
#                     recommendation=f"Review whether surrendering Class {sc.class_number} "
#                                    "creates gaps or ambiguity in the overall trademark scope. "
#                                    "Consider whether amendments to retained class identifications "
#                                    "are needed for clarity post-surrender."
#                 ))
#             else:
#                 self.findings.append(Pillar3Finding(
#                     tmep_section=section,
#                     severity="OK",
#                     class_number=sc.class_number,
#                     item=f"Class {sc.class_number} — Surrender scope check",
#                     finding=f"Surrendering Class {sc.class_number} ({sc.class_title}) "
#                              "does not appear to create scope inconsistency with retained classes.",
#                     recommendation=f"Proceed with surrender of Class {sc.class_number}. "
#                                    "Remember: surrender is irrevocable."
#                 ))

#         # ── Retained classes check ────────────────────────────────────────────
#         if to_retain:
#             self.findings.append(Pillar3Finding(
#                 tmep_section=section,
#                 severity="INFO",
#                 class_number=0,
#                 item=f"Post-surrender retained: "
#                      f"Class(es) {', '.join(str(c.class_number) for c in sorted(to_retain, key=lambda x: x.class_number))}",
#                 finding=f"After surrendering Class(es) "
#                          f"{', '.join(str(s) for s in sorted(to_surrender))}, "
#                          f"the registration will retain "
#                          f"Class(es) {', '.join(str(c.class_number) for c in sorted(to_retain, key=lambda x: x.class_number))}.",
#                 recommendation="Ensure maintenance fees (Section 8/71 Declarations) "
#                                "are paid for all RETAINED classes going forward. "
#                                "Surrendered classes are excluded from future maintenance."
#             ))

#     # ─────────────────────────────────────────────────────────────────────────
#     # BUILD FINAL RESULT
#     # ─────────────────────────────────────────────────────────────────────────

#     def _build_result(self,
#                       division_eligible: List[int],
#                       refusal_classes: List[int],
#                       refusal_reasons: Dict[int, str]) -> Pillar3AssessmentResult:

#         errors = sum(1 for f in self.findings if f.severity == "ERROR")
#         warnings = sum(1 for f in self.findings if f.severity == "WARNING")
#         is_compliant = (errors == 0)

#         return Pillar3AssessmentResult(
#             findings=self.findings,
#             division_eligible_classes=division_eligible,
#             division_recommended=len(division_eligible) > 0,
#             partial_refusal_classes=refusal_classes,
#             partial_refusal_reasons=refusal_reasons,
#             is_multi_class_compliant=is_compliant,
#             total_errors=errors,
#             total_warnings=warnings
#         )


# # ═══════════════════════════════════════════════════════════════════════════════
# # REPORT GENERATOR
# # ═══════════════════════════════════════════════════════════════════════════════

# def print_pillar3_report(result: Pillar3AssessmentResult,
#                           app_context: MultiClassApplicationContext):
#     """Prints a formatted Pillar 3 assessment report."""
#     SYMBOLS = {"ERROR": "🔴 ERROR", "WARNING": "🟡 WARNING",
#                "INFO": "🔵 INFO", "OK": "✅ OK"}
#     SECTION_TITLES = {
#         "§1403.01": "Requirements for Combined/Multiple-Class Applications",
#         "§1403.02": "Amendment of Combined/Multiple-Class Application",
#         "§1403.03": "Dividing of Combined/Multiple-Class Application",
#         "§1403.04": "Refusals as to Less Than All Classes",
#         "§1403.05": "Fees for Post-Filing Actions, Multiple Classes",
#         "§1403.06": "Surrender or Amendment in Multiple-Class Registrations",
#         "§1403":    "General Multi-Class Assessment",
#     }

#     border = "═" * 85
#     print(f"\n{border}")
#     print("  TMEP §1403 — PILLAR 3: MULTIPLE-CLASS APPLICATION ASSESSMENT")
#     print("  Based on: TMEP November 2025 Edition | 12th Nice Agreement Edition")
#     print(border)
#     print(f"  Applicant : {app_context.applicant_name or '(not specified)'}")
#     print(f"  Mark      : {app_context.mark_text or '(not specified)'}")
#     print(f"  Stage     : {app_context.application_stage.value}")
#     print(f"  Filing    : {app_context.filing_type}")

#     status_sym = "✅ COMPLIANT" if result.is_multi_class_compliant else \
#                  "🔴 NON-COMPLIANT — CORRECTIONS REQUIRED"
#     print(f"\n  Overall   : {status_sym}")
#     print(f"  Errors    : {result.total_errors}  |  Warnings: {result.total_warnings}")

#     if result.partial_refusal_classes:
#         print(f"\n  🚨 PARTIAL REFUSAL CANDIDATES: "
#               f"Class(es) {', '.join(str(c) for c in sorted(result.partial_refusal_classes))}")

#     if result.division_recommended:
#         print(f"\n  📂 DIVISION RECOMMENDED — "
#               f"Class(es) {', '.join(str(c) for c in sorted(result.division_eligible_classes))} "
#               f"can proceed independently")

#     # Group and print by section
#     sections_order = ["§1403", "§1403.01", "§1403.02", "§1403.03",
#                       "§1403.04", "§1403.05", "§1403.06"]

#     for section in sections_order:
#         section_findings = [f for f in result.findings if f.tmep_section == section]
#         if not section_findings:
#             continue

#         print(f"\n{'─'*85}")
#         print(f"  {section} — {SECTION_TITLES.get(section, section)}")
#         print(f"{'─'*85}")

#         # Sort: errors first
#         section_findings.sort(key=lambda x: {"ERROR": 0, "WARNING": 1, "INFO": 2, "OK": 3}
#                                               .get(x.severity, 9))

#         for f in section_findings:
#             cls_label = f"[Class {f.class_number:02d}]" if f.class_number > 0 else "[Application]"
#             sym = SYMBOLS.get(f.severity, f.severity)
#             print(f"\n  {sym} — {cls_label}")
#             print(f"    Item       : {f.item}")
#             print(f"    Finding    : {f.finding[:200]}{'...' if len(f.finding) > 200 else ''}")
#             print(f"    Action     : {f.recommendation[:180]}{'...' if len(f.recommendation) > 180 else ''}")
#             if f.triggered_by:
#                 print(f"    Source     : {f.triggered_by}")

#     print(f"\n{border}\n")


# # ═══════════════════════════════════════════════════════════════════════════════
# # PUBLIC API
# # ═══════════════════════════════════════════════════════════════════════════════

# def assess_multi_class_application(
#         class_summaries: List[ClassSummary],
#         app_context: MultiClassApplicationContext
# ) -> Pillar3AssessmentResult:
#     """
#     Main entry point for Pillar 3 assessment.

#     Args:
#         class_summaries : List of ClassSummary built via build_class_summary()
#                           — one per class, each incorporating P1 + P2 findings
#         app_context     : MultiClassApplicationContext with application-level data

#     Returns:
#         Pillar3AssessmentResult with all §1403 findings
#     """
#     assessor = Pillar3Assessor(class_summaries, app_context)
#     return assessor.run_full_assessment()


# # ═══════════════════════════════════════════════════════════════════════════════
# # FULL PIPELINE RUNNER — Connects Pillars 1 → 2 → 3 end-to-end
# # ═══════════════════════════════════════════════════════════════════════════════

# def run_full_pipeline(application_dict: dict) -> dict:
#     """
#     Runs the complete 3-pillar assessment pipeline on a trademark application.

#     Args:
#         application_dict: Same format as Pillar 1 main.py assess_trademark_application()

#     Returns:
#         dict with:
#             pillar1  : Pillar 1 result dict (findings, summary, report)
#             pillar2  : Dict[class_number → Pillar 2 result dict]
#             pillar3  : Pillar3AssessmentResult
#             summary  : Combined counts across all 3 pillars
#     """
#     # ── PILLAR 1 ──────────────────────────────────────────────────────────────
#     try:
#         from main import assess_trademark_application
#         p1_result = assess_trademark_application(application_dict)
#         p1_findings = p1_result["findings"]
#         p1_app = p1_result["application"]
#     except ImportError:
#         print("⚠️  Pillar 1 (main.py) not found — running Pillar 3 with provided data only.")
#         p1_findings = []
#         p1_app = None

#     # ── PILLAR 2 (per class) ──────────────────────────────────────────────────
#     p2_results: Dict[int, dict] = {}
#     try:
#         from tmep_1402_pillar2 import (
#             analyze_identification_under_tmep_1402,
#             build_pillar1_context_from_dicts,
#             Pillar1ClassContext
#         )
#         for cls_dict in application_dict.get("classes", []):
#             cls_num = int(cls_dict.get("class_number", 0))
#             p1_ctx = build_pillar1_context_from_dicts(cls_dict, p1_findings)
#             p2_result = analyze_identification_under_tmep_1402(
#                 cls_dict.get("identification", ""),
#                 pillar1_context=p1_ctx
#             )
#             p2_results[cls_num] = p2_result
#     except ImportError:
#         print("⚠️  Pillar 2 (tmep_1402_pillar2.py) not found — skipping P2 analysis.")

#     # ── BUILD CLASS SUMMARIES (P1 + P2 consolidated) ──────────────────────────
#     class_summaries = []
#     for cls_dict in application_dict.get("classes", []):
#         cls_num = int(cls_dict.get("class_number", 0))
#         summary = build_class_summary(
#             class_entry_dict=cls_dict,
#             p1_findings=p1_findings,
#             p2_result_dict=p2_results.get(cls_num)
#         )
#         class_summaries.append(summary)

#     # ── BUILD APPLICATION CONTEXT ─────────────────────────────────────────────
#     app_ctx = MultiClassApplicationContext(
#         applicant_name=application_dict.get("applicant_name", ""),
#         mark_text=application_dict.get("mark_text", ""),
#         filing_date=application_dict.get("filing_date", ""),
#         filing_type=application_dict.get("filing_type", "TEAS_PLUS"),
#         fees_paid_count=int(application_dict.get("fees_paid_count", 0)),
#         total_fee_paid=float(application_dict.get("total_fee_paid", 0.0)),
#         application_stage=ApplicationStage.FILED_PENDING,
#         amendment_requested=application_dict.get("amendment_requested", False),
#         amendment_affects_classes=application_dict.get("amendment_affects_classes", []),
#         amendment_description=application_dict.get("amendment_description", ""),
#         division_requested=application_dict.get("division_requested", False),
#         classes_to_divide_out=application_dict.get("classes_to_divide_out", []),
#         surrender_requested=application_dict.get("surrender_requested", False),
#         classes_to_surrender=application_dict.get("classes_to_surrender", []),
#         post_filing_action_type=application_dict.get("post_filing_action_type", "")
#     )

#     # ── PILLAR 3 ──────────────────────────────────────────────────────────────
#     p3_result = assess_multi_class_application(class_summaries, app_ctx)

#     # ── COMBINED SUMMARY ──────────────────────────────────────────────────────
#     p1_summary = p1_result.get("summary", {}) if p1_findings else {}
#     p2_total_errors = sum(r["summary"]["errors"] for r in p2_results.values())
#     p2_total_warnings = sum(r["summary"]["warnings"] for r in p2_results.values())

#     combined_summary = {
#         "pillar1_errors":   p1_summary.get("errors", 0),
#         "pillar1_warnings": p1_summary.get("warnings", 0),
#         "pillar2_errors":   p2_total_errors,
#         "pillar2_warnings": p2_total_warnings,
#         "pillar3_errors":   p3_result.total_errors,
#         "pillar3_warnings": p3_result.total_warnings,
#         "total_errors":     p1_summary.get("errors", 0) + p2_total_errors + p3_result.total_errors,
#         "total_warnings":   p1_summary.get("warnings", 0) + p2_total_warnings + p3_result.total_warnings,
#         "partial_refusal_classes": p3_result.partial_refusal_classes,
#         "division_recommended": p3_result.division_recommended,
#         "division_eligible_classes": p3_result.division_eligible_classes,
#         "overall_compliant": p3_result.is_multi_class_compliant and p1_summary.get("errors", 0) == 0
#     }

#     print_pillar3_report(p3_result, app_ctx)

#     return {
#         "pillar1": p1_result if p1_findings else {},
#         "pillar2": p2_results,
#         "pillar3": p3_result,
#         "summary": combined_summary
#     }


# # ═══════════════════════════════════════════════════════════════════════════════
# # DEMO — Run directly with sample applications
# # ═══════════════════════════════════════════════════════════════════════════════

# if __name__ == "__main__":

#     # ── DEMO 1: Multi-class with mixed errors (feeds from Pillar 1 sample 2) ──
#     print("\n" + "█"*85)
#     print("  DEMO 1: Multi-class app with errors — division recommended")
#     print("█"*85)

#     DEMO_APP_1 = {
#         "applicant_name": "Global Brands LLC",
#         "mark_text": "BRANDSTAR",
#         "filing_date": "2024-11-20",
#         "nice_edition_claimed": "12th",
#         "filing_type": "TEAS_STANDARD",
#         "fees_paid_count": 2,
#         "total_fee_paid": 700.0,
#         "amendment_requested": False,
#         "division_requested": False,
#         "surrender_requested": False,
#         "post_filing_action_type": "",
#         "classes": [
#             {
#                 "class_number": 9,
#                 "identification": "Downloadable software for e-commerce management",
#                 "specimen_type": "website screenshot",
#                 "specimen_description": "screenshot showing downloadable software for sale",
#                 "fee_paid": True,
#                 "filing_basis": "1(a)",
#                 "date_of_first_use": "2023-01-15",
#                 "date_of_first_use_commerce": "2023-03-01"
#             },
#             {
#                 "class_number": 25,
#                 "identification": "Software for inventory management; computer programs",
#                 # Software in Class 25 = Pillar 1 error → Pillar 3 partial refusal
#                 "specimen_type": "product label",
#                 "specimen_description": "label on clothing item",
#                 "fee_paid": True,
#                 "filing_basis": "1(a)",
#                 "date_of_first_use": "2023-01-10",
#                 "date_of_first_use_commerce": "2023-02-01"
#             },
#             {
#                 "class_number": 42,
#                 "identification": "Restaurant services; catering services; hotel accommodation",
#                 # Post-8th Edition error: restaurant goes to Class 43, not 42
#                 "specimen_type": "brochure",
#                 "specimen_description": "advertising restaurant services",
#                 "fee_paid": False,    # No fee = Pillar 1 §1401.04 error
#                 "filing_basis": "1(a)",
#                 "date_of_first_use": "2022-08-15",
#                 "date_of_first_use_commerce": "2022-09-01"
#             }
#         ]
#     }

#     result1 = run_full_pipeline(DEMO_APP_1)
#     print("\n  COMBINED PIPELINE SUMMARY:")
#     for k, v in result1["summary"].items():
#         print(f"    {k:30s}: {v}")

#     # ── DEMO 2: Clean tech app + amendment affecting all classes ──────────────
#     print("\n" + "█"*85)
#     print("  DEMO 2: Clean app with amendment scope check")
#     print("█"*85)

#     DEMO_APP_2 = {
#         "applicant_name": "TechVista Solutions Inc.",
#         "mark_text": "NEXAFLOW",
#         "filing_date": "2024-09-15",
#         "nice_edition_claimed": "12th",
#         "filing_type": "TEAS_PLUS",
#         "fees_paid_count": 3,
#         "total_fee_paid": 750.0,
#         "amendment_requested": True,
#         "amendment_affects_classes": [9],         # Only Class 9 amended
#         "amendment_description": "clarify software identification",
#         "division_requested": False,
#         "surrender_requested": False,
#         "post_filing_action_type": "",
#         "classes": [
#             {
#                 "class_number": 9,
#                 "identification": "Downloadable software for project management and team collaboration",
#                 "specimen_type": "website screenshot",
#                 "specimen_description": "website showing downloadable software for sale",
#                 "fee_paid": True,
#                 "filing_basis": "1(a)",
#                 "date_of_first_use": "2022-03-01",
#                 "date_of_first_use_commerce": "2022-04-15"
#             },
#             {
#                 "class_number": 42,
#                 "identification": "Software as a service for project management; cloud computing services for others",
#                 "specimen_type": "screenshot of service",
#                 "specimen_description": "screenshot of SaaS platform with mark",
#                 "fee_paid": True,
#                 "filing_basis": "1(a)",
#                 "date_of_first_use": "2022-05-01",
#                 "date_of_first_use_commerce": "2022-06-01"
#             },
#             {
#                 "class_number": 35,
#                 "identification": "Online marketplace services for software products; "
#                                   "business management consulting services for others",
#                 "specimen_type": "advertisement",
#                 "specimen_description": "online advertisement for consulting services",
#                 "fee_paid": True,
#                 "filing_basis": "1(a)",
#                 "date_of_first_use": "2022-07-01",
#                 "date_of_first_use_commerce": "2022-07-15"
#             }
#         ]
#     }

#     result2 = run_full_pipeline(DEMO_APP_2)
#     print("\n  COMBINED PIPELINE SUMMARY:")
#     for k, v in result2["summary"].items():
#         print(f"    {k:30s}: {v}")
