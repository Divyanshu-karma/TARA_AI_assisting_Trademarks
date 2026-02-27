"""
TMEP CHAPTER 1401 — CLASSIFICATION ASSESSMENT ENGINE
=====================================================
Full PILLAR 1 Assessment System (Nov 2025 Edition)
Covers: §1401.01 through §1401.15

Each method directly maps to a specific TMEP sub-section.
"""

from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass, field
from nice_classification_db import (
    NICE_CLASSES, VALID_CLASS_NUMBERS, NICE_EDITION_TIMELINE,
    OLD_CLASS_42_SERVICES, COMMON_MISCLASSIFICATIONS,
    SPECIMEN_TYPES, USPTO_FEES,
    suggest_class_for_keyword, get_class_info
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES — Trademark Application Input Model
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassEntry:
    """Represents one class entry in a trademark application."""
    class_number: int                          # The class number claimed (e.g., 9, 25, 41)
    identification: str                        # Written description of goods/services
    specimen_type: str = ""                    # Type of specimen submitted (e.g., "product label")
    specimen_description: str = ""            # Detailed description of what the specimen shows
    fee_paid: bool = True                     # Has fee been paid for this class?
    filing_basis: str = "1(a)"               # 1(a), 1(b), 44(d), 44(e), 66(a)
    date_of_first_use: Optional[str] = None  # Date of first use anywhere
    date_of_first_use_commerce: Optional[str] = None  # Date of first use in commerce
    # Internal — set during assessment
    flags: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)


@dataclass
class TrademarkApplication:
    """Complete trademark application input model."""
    # ── Core Application Fields ─────────────────────────────────
    applicant_name: str = ""                  # Name of applicant
    mark_text: str = ""                       # The trademark text/name
    mark_type: str = "standard_character"    # standard_character, special_form, sound
    filing_date: str = ""                     # Format: YYYY-MM-DD
    nice_edition_claimed: str = "12th"       # Which Nice Agreement edition applicant used
    application_serial: str = ""             # Serial number (if assigned)
    filing_type: str = "TEAS_PLUS"           # TEAS_PLUS, TEAS_STANDARD, PAPER

    # ── Classes ──────────────────────────────────────────────────
    classes: list = field(default_factory=list)  # List of ClassEntry objects

    # ── Fee Information ──────────────────────────────────────────
    fees_paid_count: int = 0                 # How many class fees were actually paid
    total_fee_paid: float = 0.0             # Total dollar amount submitted

    # ── Flags (set during parsing) ───────────────────────────────
    is_multi_class: bool = False
    notes: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# FINDING / FLAG MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AssessmentFinding:
    """A single finding from the assessment."""
    tmep_section: str         # e.g., "§1401.03"
    severity: str             # "ERROR", "WARNING", "INFO", "OK"
    class_number: int         # 0 if applies to whole application
    item: str                 # The specific item or term flagged
    finding: str              # What was found
    recommendation: str       # What to do about it


# ═══════════════════════════════════════════════════════════════════════════════
# ASSESSMENT ENGINE — TMEP §1401.01 through §1401.15
# ═══════════════════════════════════════════════════════════════════════════════

class TMEP1401Assessor:
    """
    Performs the full TMEP §1401 (Classification) assessment on
    a trademark application, producing structured findings per sub-section.
    """

    def __init__(self, application: TrademarkApplication):
        self.app = application
        self.findings: list[AssessmentFinding] = []
        self.assessment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ─────────────────────────────────────────────────────────────────────────
    # ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    def run_full_assessment(self) -> list[AssessmentFinding]:
        """
        Runs all §1401.01–§1401.15 checks in sequence.
        Returns all findings.
        """
        self.findings.clear()
        self._check_1401_01_statutory_authority()
        self._check_1401_02_international_classification_adopted()
        self._check_1401_03_designation_of_class()
        self._check_1401_04_classification_determines_fees()
        self._check_1401_05_criteria_for_classification()
        self._check_1401_06_specimen_related_to_classification()
        self._check_1401_07_specimen_discloses_special_characteristics()
        self._check_1401_08_classification_and_identification()
        self._check_1401_09_implementation_of_nice_changes()
        self._check_1401_10_effective_date_id_manual()
        self._check_1401_11_class42_restructuring_8th_edition()
        self._check_1401_12_9th_edition_changes()
        self._check_1401_13_10th_edition_changes()
        self._check_1401_14_11th_edition_changes()
        self._check_1401_15_12th_edition_changes()
        return self.findings

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.01 — STATUTORY AUTHORITY
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_01_statutory_authority(self):
        """
        §1401.01 — Confirms USPTO authority under Lanham Act §30 (15 U.S.C. §1112)
        to classify goods/services and prescribe fees per class.
        This is a foundational validity check — confirms the application is
        subject to USPTO jurisdiction (U.S.-based or international treaty basis).
        """
        section = "§1401.01"

        # Check filing basis to confirm USPTO jurisdiction applies
        valid_bases = ["1(a)", "1(b)", "44(d)", "44(e)", "66(a)"]
        found_invalid_basis = False

        for cls_entry in self.app.classes:
            if cls_entry.filing_basis not in valid_bases:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls_entry.class_number,
                    item=f"Filing basis: '{cls_entry.filing_basis}'",
                    finding="Invalid or unrecognized filing basis. USPTO jurisdiction requires "
                            "a recognized basis under the Lanham Act.",
                    recommendation=f"Correct filing basis to one of: {', '.join(valid_bases)}."
                ))
                found_invalid_basis = True

        if not found_invalid_basis:
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="OK",
                class_number=0,
                item="Filing Basis",
                finding="All filing bases are recognized under the Lanham Act. "
                         "USPTO statutory authority to classify and charge per-class fees is confirmed "
                         "(15 U.S.C. §1112; Lanham Act §30).",
                recommendation="No action required."
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.02 — INTERNATIONAL CLASSIFICATION ADOPTED
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_02_international_classification_adopted(self):
        """
        §1401.02 — USPTO uses the International (Nice) Classification system.
        Confirms all class numbers in the application are valid Nice Classification
        numbers (1–45) and not custom, obsolete, or non-standard designations.
        """
        section = "§1401.02"
        invalid_classes_found = []

        for cls_entry in self.app.classes:
            if cls_entry.class_number not in VALID_CLASS_NUMBERS:
                invalid_classes_found.append(cls_entry.class_number)
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls_entry.class_number,
                    item=f"Class {cls_entry.class_number}",
                    finding=f"Class number {cls_entry.class_number} is NOT a valid "
                             f"International (Nice) Classification number. "
                             f"Valid classes are 1–45 under the Nice Agreement.",
                    recommendation="Replace with a valid Nice Classification class number (1–45). "
                                   "Consult the USPTO ID Manual or TMEP §1401.02."
                ))

        if not invalid_classes_found:
            classes_used = [c.class_number for c in self.app.classes]
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="OK",
                class_number=0,
                item="Nice Classification System Compliance",
                finding=f"All class numbers ({', '.join(map(str, sorted(classes_used)))}) are valid "
                         f"International Nice Classification numbers under the Nice Agreement "
                         f"(adopted by USPTO per 37 C.F.R. §2.85).",
                recommendation="No action required."
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.03 — DESIGNATION OF CLASS
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_03_designation_of_class(self):
        """
        §1401.03 — Each good or service must be assigned to its CORRECT class.
        The nature of the goods/services determines the class — not applicant preference.
        This method checks each identification against its claimed class using
        keyword analysis and known misclassification patterns.
        """
        section = "§1401.03"

        for cls_entry in self.app.classes:
            claimed_class = cls_entry.class_number
            id_text = cls_entry.identification.lower().strip()
            class_info = get_class_info(claimed_class)

            if not class_info:
                continue  # Already flagged in §1401.02

            # ── Step A: Check against known misclassification patterns ─────
            misclassification_found = False
            for (kw, wrong_class), (correct_class, reason) in COMMON_MISCLASSIFICATIONS.items():
                if kw in id_text and wrong_class == claimed_class and correct_class != claimed_class:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=claimed_class,
                        item=f'"{kw}" in Class {claimed_class}',
                        finding=f"MISCLASSIFICATION DETECTED: '{kw}' is placed in Class {claimed_class} "
                                 f"({class_info['title']}), but this is incorrect. {reason}",
                        recommendation=f"Move '{kw}' to Class {correct_class} "
                                       f"({get_class_info(correct_class)['title'] if get_class_info(correct_class) else 'see TMEP'})."
                    ))
                    misclassification_found = True

            # ── Step B: Keyword-based class suggestion check ───────────────
            # Split identification into individual terms and verify each
            id_terms = [t.strip() for t in id_text.replace(";", ",").split(",") if t.strip()]

            for term in id_terms:
                suggestions = suggest_class_for_keyword(term)
                if suggestions:
                    top_suggested_class = suggestions[0][0]
                    top_score = suggestions[0][2]

                    if top_suggested_class != claimed_class and top_score >= 5:
                        # Only flag if the top suggestion is not the claimed class
                        # and has a meaningful confidence score
                        top_cls_info = get_class_info(top_suggested_class)
                        self.findings.append(AssessmentFinding(
                            tmep_section=section,
                            severity="WARNING",
                            class_number=claimed_class,
                            item=f'Term: "{term}" in Class {claimed_class}',
                            finding=f"Possible classification mismatch: '{term}' appears to match "
                                     f"Class {top_suggested_class} ({top_cls_info['title']}) "
                                     f"more closely than Class {claimed_class} ({class_info['title']}).",
                            recommendation=f"Verify whether '{term}' belongs in Class {top_suggested_class} "
                                           f"({top_cls_info['title']}) instead of Class {claimed_class}. "
                                           f"Per §1401.05: nature of goods/services determines class."
                        ))

            # ── Step C: Confirm class category alignment ──────────────────
            # Check: is applicant putting a service description in a goods class or vice versa?
            category = class_info["category"]
            service_indicators = [
                "service", "services", "providing", "rendering", "consulting",
                "management of", "repair of", "installation of", "development of"
            ]
            goods_indicators = [
                "downloadable", "printed", "physical", "apparatus", "device", "equipment",
                "machine", "clothing", "food", "beverage", "chemical"
            ]

            is_service_language = any(si in id_text for si in service_indicators)
            is_goods_language = any(gi in id_text for gi in goods_indicators)

            if category == "GOODS" and is_service_language and not is_goods_language:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="WARNING",
                    class_number=claimed_class,
                    item=f"Category mismatch in Class {claimed_class} ({class_info['title']})",
                    finding=f"The identification '{cls_entry.identification}' appears to describe a SERVICE "
                             f"(contains service language: {[si for si in service_indicators if si in id_text]}), "
                             f"but Class {claimed_class} is a GOODS class.",
                    recommendation="Review the identification. Services must be placed in Classes 35–45. "
                                   "Consider which service class (35–45) is appropriate."
                ))
            elif category == "SERVICES" and is_goods_language and not is_service_language:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="WARNING",
                    class_number=claimed_class,
                    item=f"Category mismatch in Class {claimed_class} ({class_info['title']})",
                    finding=f"The identification '{cls_entry.identification}' appears to describe GOODS, "
                             f"but Class {claimed_class} is a SERVICES class.",
                    recommendation="Review the identification. Goods must be placed in Classes 1–34."
                ))

            # ── Step D: Record OK if no issues found ──────────────────────
            if not misclassification_found:
                has_warning = any(
                    f.tmep_section == section and f.class_number == claimed_class
                    for f in self.findings
                )
                if not has_warning:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="OK",
                        class_number=claimed_class,
                        item=f"Class {claimed_class}: {cls_entry.identification[:60]}{'...' if len(cls_entry.identification)>60 else ''}",
                        finding=f"Class designation appears correct. Class {claimed_class} "
                                 f"({class_info['title']}) is consistent with the "
                                 f"identification provided.",
                        recommendation="No action required."
                    ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.04 — CLASSIFICATION DETERMINES NUMBER OF FEES
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_04_classification_determines_fees(self):
        """
        §1401.04 — Each class requires a separate filing fee.
        The number of classes = the number of fees due.
        Check: fees paid count vs. number of distinct classes claimed.
        """
        section = "§1401.04"

        # Count distinct classes
        claimed_classes = [c.class_number for c in self.app.classes]
        distinct_classes = sorted(set(claimed_classes))
        num_distinct = len(distinct_classes)
        fees_paid = self.app.fees_paid_count

        # Check for duplicate class entries
        if len(claimed_classes) != len(distinct_classes):
            duplicates = [cls for cls in distinct_classes
                         if claimed_classes.count(cls) > 1]
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="WARNING",
                class_number=0,
                item=f"Duplicate class entries: {duplicates}",
                finding=f"Class(es) {duplicates} appear more than once in the application. "
                         f"Each class should appear once with a consolidated identification.",
                recommendation="Consolidate all goods/services for each class into a single "
                               "class entry. Duplicate class entries may cause processing issues."
            ))

        # Calculate expected fees
        fee_per_class = USPTO_FEES.get(self.app.filing_type, USPTO_FEES["TEAS_STANDARD"])
        expected_fee_total = num_distinct * fee_per_class
        actual_fee_total = self.app.total_fee_paid if self.app.total_fee_paid > 0 else fees_paid * fee_per_class

        # Check fee count vs class count
        if fees_paid == 0:
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="INFO",
                class_number=0,
                item="Fee Count Not Specified",
                finding="The number of fees paid was not specified in the application input. "
                         "Cannot perform fee count verification.",
                recommendation=f"Verify that {num_distinct} fee(s) were submitted — one per class: "
                               f"Classes {', '.join(map(str, distinct_classes))}. "
                               f"At {self.app.filing_type} rate: ${fee_per_class}/class = "
                               f"${expected_fee_total} total."
            ))
        elif fees_paid < num_distinct:
            shortage = num_distinct - fees_paid
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="ERROR",
                class_number=0,
                item=f"Fee Shortage: {fees_paid} fees paid, {num_distinct} classes claimed",
                finding=f"UNDERPAYMENT DETECTED: Application claims {num_distinct} class(es) "
                         f"({', '.join(map(str, distinct_classes))}) but only {fees_paid} fee(s) "
                         f"were submitted. Shortfall: {shortage} fee(s) = "
                         f"${shortage * fee_per_class} at {self.app.filing_type} rate.",
                recommendation=f"Submit {shortage} additional fee(s) of ${fee_per_class} each "
                               f"(${shortage * fee_per_class} total) to cover all classes. "
                               f"Failure to pay per-class fees will result in the uncovered "
                               f"class(es) being deleted from the application."
            ))
        elif fees_paid > num_distinct:
            excess = fees_paid - num_distinct
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="WARNING",
                class_number=0,
                item=f"Fee Excess: {fees_paid} fees paid, {num_distinct} classes claimed",
                finding=f"OVERPAYMENT: {fees_paid} fees paid but only {num_distinct} class(es) claimed. "
                         f"Excess: {excess} fee(s) = ${excess * fee_per_class}.",
                recommendation="Request refund of overpaid fees or add additional classes to match "
                               "the number of fees submitted."
            ))
        else:
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="OK",
                class_number=0,
                item="Fee Verification",
                finding=f"Fee count CORRECT: {fees_paid} fee(s) paid for {num_distinct} class(es). "
                         f"Classes: {', '.join(map(str, distinct_classes))}. "
                         f"Filing type: {self.app.filing_type} (${fee_per_class}/class). "
                         f"Total: ${fees_paid * fee_per_class}.",
                recommendation="No action required."
            ))

        # Check individual class fee flags
        for cls_entry in self.app.classes:
            if not cls_entry.fee_paid:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls_entry.class_number,
                    item=f"Class {cls_entry.class_number} — No fee",
                    finding=f"No filing fee has been paid for Class {cls_entry.class_number}. "
                             f"Per §1401.04, each class requires a separate fee.",
                    recommendation=f"Submit ${fee_per_class} ({self.app.filing_type}) "
                                   f"for Class {cls_entry.class_number}."
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.05 — CRITERIA ON WHICH CLASSIFICATION IS BASED
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_05_criteria_for_classification(self):
        """
        §1401.05 — Classification criteria:
        - GOODS: Classified by their NATURE/COMPOSITION (what they ARE)
        - SERVICES: Classified by their FUNCTION/PURPOSE (what they DO, for whose benefit)
        
        Applies analytical logic to flag ambiguous terms that could span 
        multiple classes, particularly digital goods vs. digital services.
        """
        section = "§1401.05"

        # Known ambiguous term pairs that are commonly confused
        ambiguous_pairs = [
            {
                "term": "music",
                "goods_form": "downloadable music",
                "goods_class": 9,
                "goods_reason": "Downloadable music is a DIGITAL PRODUCT (what it is = a file) → Class 9",
                "service_form": "music streaming service",
                "service_class": 41,
                "service_reason": "Music streaming is an ENTERTAINMENT SERVICE (what it does = entertains) → Class 41"
            },
            {
                "term": "video",
                "goods_form": "downloadable video content",
                "goods_class": 9,
                "goods_reason": "Downloadable video is a DIGITAL PRODUCT → Class 9",
                "service_form": "video streaming service",
                "service_class": 41,
                "service_reason": "Video streaming is an ENTERTAINMENT SERVICE → Class 41"
            },
            {
                "term": "software",
                "goods_form": "downloadable software",
                "goods_class": 9,
                "goods_reason": "Downloadable software is a DIGITAL PRODUCT → Class 9",
                "service_form": "software as a service",
                "service_class": 42,
                "service_reason": "SaaS is a TECHNOLOGY SERVICE (what it does = provides tech access) → Class 42"
            },
            {
                "term": "book",
                "goods_form": "downloadable ebooks",
                "goods_class": 9,
                "goods_reason": "Downloadable ebooks are DIGITAL PRODUCTS → Class 9",
                "service_form": "printed books",
                "service_class": 16,
                "service_reason": "Printed books are PHYSICAL GOODS (paper products) → Class 16"
            },
            {
                "term": "food",
                "goods_form": "packaged food products",
                "goods_class": 30,
                "goods_reason": "Packaged food is a PHYSICAL PRODUCT (what it is = food) → Class 29/30",
                "service_form": "restaurant food service",
                "service_class": 43,
                "service_reason": "Restaurant is a FOOD SERVICE (what it does = serves meals) → Class 43"
            },
            {
                "term": "education",
                "goods_form": "educational printed materials",
                "goods_class": 16,
                "goods_reason": "Printed educational materials are GOODS → Class 16",
                "service_form": "educational services",
                "service_class": 41,
                "service_reason": "Educational services are SERVICES (what they do = educate) → Class 41"
            }
        ]

        for cls_entry in self.app.classes:
            id_text = cls_entry.identification.lower()
            class_info = get_class_info(cls_entry.class_number)
            if not class_info:
                continue

            # Check for ambiguous terms
            for pair in ambiguous_pairs:
                if pair["term"] in id_text:
                    # Evaluate whether identification is goods or service form
                    has_download = any(w in id_text for w in
                                      ["download", "downloadable", "recorded", "digital file"])
                    has_service_language = any(w in id_text for w in
                                              ["service", "streaming", "providing", "access to"])
                    has_print = any(w in id_text for w in ["printed", "paper", "physical"])

                    # Build contextual advisory
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="INFO",
                        class_number=cls_entry.class_number,
                        item=f'Ambiguous term: "{pair["term"]}" in Class {cls_entry.class_number}',
                        finding=f"CLASSIFICATION CRITERIA ANALYSIS for '{pair['term']}':\n"
                                 f"   • If this is a PRODUCT (goods form) → "
                                 f"Class {pair['goods_class']}: {pair['goods_reason']}\n"
                                 f"   • If this is a SERVICE (service form) → "
                                 f"Class {pair['service_class']}: {pair['service_reason']}\n"
                                 f"   Current placement: Class {cls_entry.class_number} "
                                 f"({class_info['title']}). "
                                 f"[Per §1401.05: goods = classified by nature; "
                                 f"services = classified by function]",
                        recommendation=f"Confirm identification clearly distinguishes between "
                                       f"the PRODUCT form (→ Class {pair['goods_class']}) and "
                                       f"the SERVICE form (→ Class {pair['service_class']}). "
                                       f"If both forms are offered, file in BOTH classes with "
                                       f"separate identifications."
                    ))

            # Verify goods/services classification logic is respected
            category = class_info["category"]
            if category == "GOODS":
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=cls_entry.class_number,
                    item=f"Classification Logic — Class {cls_entry.class_number} (GOODS)",
                    finding=f"Class {cls_entry.class_number} is a GOODS class. "
                             f"Per §1401.05, classification is based on the NATURE/COMPOSITION "
                             f"of the goods — what the product physically IS.",
                    recommendation="Ensure identification describes the product by its nature "
                                   "(e.g., material, form, composition) not its marketing purpose."
                ))
            else:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=cls_entry.class_number,
                    item=f"Classification Logic — Class {cls_entry.class_number} (SERVICES)",
                    finding=f"Class {cls_entry.class_number} is a SERVICES class. "
                             f"Per §1401.05, classification is based on the FUNCTION/PURPOSE "
                             f"of the service — what activity is performed and for whose benefit.",
                    recommendation="Ensure identification describes the service activity clearly "
                                   "(e.g., 'providing X for Y' or 'X services for others in the field of Y')."
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.06 — SPECIMEN(S) AS RELATED TO CLASSIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_06_specimen_related_to_classification(self):
        """
        §1401.06 — The specimen must show the mark being used IN CONNECTION WITH
        the specific goods/services in the claimed class.
        
        Checks:
        - Specimen type is appropriate for goods vs. services
        - Specimen content aligns with the class category
        - No mismatch between what specimen shows and what class covers
        """
        section = "§1401.06"

        for cls_entry in self.app.classes:
            # Skip if no specimen submitted (intent-to-use applications)
            if cls_entry.filing_basis == "1(b)":
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=cls_entry.class_number,
                    item=f"Class {cls_entry.class_number} — Intent to Use (§1(b))",
                    finding="No specimen required at this stage for §1(b) intent-to-use applications. "
                             "Specimen must be submitted with the Statement of Use (SOU) "
                             "after the mark is used in commerce.",
                    recommendation="Ensure specimen is filed with SOU when the mark is put into use."
                ))
                continue

            if not cls_entry.specimen_type and not cls_entry.specimen_description:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="ERROR",
                    class_number=cls_entry.class_number,
                    item=f"Class {cls_entry.class_number} — Specimen Missing",
                    finding=f"No specimen was provided for Class {cls_entry.class_number}. "
                             f"For §1(a) use-based applications, a specimen showing actual "
                             f"use of the mark is required.",
                    recommendation="Submit an acceptable specimen showing the mark in actual use "
                                   "in connection with the goods/services in this class."
                ))
                continue

            class_info = get_class_info(cls_entry.class_number)
            if not class_info:
                continue

            category = class_info["category"]
            specimen_type_lower = cls_entry.specimen_type.lower()
            specimen_desc_lower = cls_entry.specimen_description.lower()

            # ── Check specimen type validity for goods vs. services ───────
            if category == "GOODS":
                invalid_goods_specimens = SPECIMEN_TYPES["goods_invalid"]
                valid_goods_specimens = SPECIMEN_TYPES["goods_valid"]

                is_invalid = any(inv in specimen_type_lower for inv in invalid_goods_specimens)
                is_valid = any(val in specimen_type_lower for val in valid_goods_specimens)

                if is_invalid and not is_valid:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=cls_entry.class_number,
                        item=f"Class {cls_entry.class_number} specimen: '{cls_entry.specimen_type}'",
                        finding=f"UNACCEPTABLE SPECIMEN for GOODS: '{cls_entry.specimen_type}' "
                                 f"is not an acceptable specimen for goods in Class {cls_entry.class_number}. "
                                 f"For goods, the specimen must show the mark directly on the goods, "
                                 f"their packaging, or a point-of-sale display.",
                        recommendation=f"Replace specimen with an acceptable goods specimen such as: "
                                       f"{', '.join(valid_goods_specimens)}."
                    ))

            elif category == "SERVICES":
                invalid_service_specimens = SPECIMEN_TYPES["services_invalid"]
                valid_service_specimens = SPECIMEN_TYPES["services_valid"]

                is_invalid = any(inv in specimen_type_lower for inv in invalid_service_specimens)
                is_valid = any(val in specimen_type_lower for val in valid_service_specimens)

                if is_invalid and not is_valid:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=cls_entry.class_number,
                        item=f"Class {cls_entry.class_number} specimen: '{cls_entry.specimen_type}'",
                        finding=f"UNACCEPTABLE SPECIMEN for SERVICES: '{cls_entry.specimen_type}' "
                                 f"is not an acceptable specimen for services in Class {cls_entry.class_number}. "
                                 f"For services, the specimen must show the mark being used in the "
                                 f"rendering or advertising of the services.",
                        recommendation=f"Replace specimen with an acceptable services specimen such as: "
                                       f"{', '.join(valid_service_specimens)}."
                    ))

            # ── Cross-check specimen description against class ────────────
            # Look for obvious mismatches (specimen shows different goods/services)
            specimen_class_keywords = (class_info.get("keywords", []))
            specimen_matches_class = any(
                kw in specimen_desc_lower for kw in specimen_class_keywords[:20]
            )

            # Check for clear class mismatches in specimen
            class_mismatch_detected = False
            all_other_classes = {cn: ci for cn, ci in NICE_CLASSES.items()
                                 if cn != cls_entry.class_number}

            # Check for strong keywords from OTHER classes in specimen description
            for other_cn, other_ci in all_other_classes.items():
                other_strong_kws = other_ci["keywords"][:10]
                other_matches = sum(1 for kw in other_strong_kws if kw in specimen_desc_lower)
                own_matches = sum(1 for kw in specimen_class_keywords[:10]
                                 if kw in specimen_desc_lower)

                if other_matches > own_matches and other_matches >= 2:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="WARNING",
                        class_number=cls_entry.class_number,
                        item=f"Specimen mismatch with Class {cls_entry.class_number}",
                        finding=f"Specimen description appears to match Class {other_cn} "
                                 f"({other_ci['title']}) more closely than "
                                 f"Class {cls_entry.class_number} ({class_info['title']}). "
                                 f"Specimen: '{cls_entry.specimen_description[:100]}...'",
                        recommendation=f"Verify the specimen actually shows use of the mark "
                                       f"in connection with the goods/services in "
                                       f"Class {cls_entry.class_number}, not Class {other_cn}."
                    ))
                    class_mismatch_detected = True
                    break

            if not class_mismatch_detected:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="OK",
                    class_number=cls_entry.class_number,
                    item=f"Class {cls_entry.class_number} specimen alignment",
                    finding=f"Specimen ('{cls_entry.specimen_type}') appears consistent with "
                             f"Class {cls_entry.class_number} ({class_info['title']}). "
                             f"No obvious class mismatch detected.",
                    recommendation="Confirm specimen clearly shows the mark in actual use "
                                   "in connection with the identified goods/services."
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.07 — SPECIMEN DISCLOSES SPECIAL CHARACTERISTICS
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_07_specimen_discloses_special_characteristics(self):
        """
        §1401.07 — The specimen may reveal that the actual goods/services have
        special characteristics that differ from the written identification,
        potentially requiring a class change.
        
        Classic example: Applicant says "printed manuals" (Class 16) but specimen
        shows downloadable online content (→ reclassify to Class 9).
        """
        section = "§1401.07"

        # Known specimen-based reclassification triggers
        reclassification_triggers = [
            {
                "claimed_description_keywords": ["printed manual", "printed guide", "printed instruction"],
                "claimed_class": 16,
                "specimen_reveals_keywords": ["download", "online", "digital", "software", "app", "website"],
                "true_class": 9,
                "reason": "Specimen shows ONLINE/DOWNLOADABLE content. "
                          "Printed manuals → Class 16, but downloadable/online content → Class 9."
            },
            {
                "claimed_description_keywords": ["physical software", "software disk", "cd-rom"],
                "claimed_class": 9,
                "specimen_reveals_keywords": ["service", "cloud", "saas", "subscription", "access to"],
                "true_class": 42,
                "reason": "Specimen reveals this is a SOFTWARE SERVICE (SaaS/cloud), "
                          "not a downloadable product. Software products → Class 9, "
                          "but software services → Class 42."
            },
            {
                "claimed_description_keywords": ["clothing", "apparel", "t-shirt"],
                "claimed_class": 25,
                "specimen_reveals_keywords": ["restaurant", "menu", "food service", "dining", "catering"],
                "true_class": 43,
                "reason": "Specimen shows RESTAURANT/FOOD SERVICES, not clothing. "
                          "Clothing → Class 25, but restaurant services → Class 43."
            },
            {
                "claimed_description_keywords": ["book", "publication"],
                "claimed_class": 16,
                "specimen_reveals_keywords": ["download", "ebook", "digital", "epub", "kindle"],
                "true_class": 9,
                "reason": "Specimen shows DOWNLOADABLE/DIGITAL format. "
                          "Printed books → Class 16, but downloadable ebooks → Class 9."
            },
            {
                "claimed_description_keywords": ["software", "application", "app"],
                "claimed_class": 9,
                "specimen_reveals_keywords": ["web-based", "saas", "subscription service", "cloud service",
                                               "hosted service", "no download"],
                "true_class": 42,
                "reason": "Specimen reveals a WEB-BASED/SAAS service, not a downloaded product. "
                          "Downloadable software → Class 9, but SaaS/cloud services → Class 42."
            }
        ]

        for cls_entry in self.app.classes:
            if not cls_entry.specimen_description:
                continue

            spec_desc_lower = cls_entry.specimen_description.lower()
            id_text_lower = cls_entry.identification.lower()

            triggered = False
            for trigger in reclassification_triggers:
                # Check if the identification matches the trigger
                id_matches = any(kw in id_text_lower
                                for kw in trigger["claimed_description_keywords"])
                # Check if the specimen reveals the trigger characteristics
                spec_reveals = any(kw in spec_desc_lower
                                  for kw in trigger["specimen_reveals_keywords"])

                if id_matches and spec_reveals:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=cls_entry.class_number,
                        item=f"Specimen reveals reclassification need — Class {cls_entry.class_number}",
                        finding=f"RECLASSIFICATION REQUIRED: The specimen reveals special characteristics "
                                 f"that conflict with the current class designation.\n"
                                 f"   • Identification says: '{cls_entry.identification[:80]}'\n"
                                 f"   • Specimen reveals: {trigger['reason']}\n"
                                 f"   • Current Class: {cls_entry.class_number} → "
                                 f"Correct Class: {trigger['true_class']}",
                        recommendation=f"Amend classification from Class {cls_entry.class_number} "
                                       f"to Class {trigger['true_class']} and update the "
                                       f"identification accordingly. The specimen's actual content "
                                       f"controls classification per §1401.07."
                    ))
                    triggered = True
                    break

            if not triggered and cls_entry.specimen_description:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="OK",
                    class_number=cls_entry.class_number,
                    item=f"Class {cls_entry.class_number} — Specimen characteristic review",
                    finding=f"No special characteristics detected in the specimen that would "
                             f"require reclassification from Class {cls_entry.class_number}. "
                             f"Specimen appears consistent with the identification provided.",
                    recommendation="No reclassification required based on specimen characteristics."
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.08 — CLASSIFICATION AND THE IDENTIFICATION OF GOODS AND SERVICES
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_08_classification_and_identification(self):
        """
        §1401.08 — The class number AND the written identification must be
        consistent and aligned. They must tell the same story.
        
        Cross-checks each class entry to confirm:
        1. Class number matches the described goods/services
        2. All goods/services in the identification fall within the same class
        3. No goods/services from different classes are bundled together
        """
        section = "§1401.08"

        for cls_entry in self.app.classes:
            claimed_class = cls_entry.class_number
            class_info = get_class_info(claimed_class)
            if not class_info:
                continue

            id_text = cls_entry.identification
            id_text_lower = id_text.lower()

            # ── Check 1: Entire identification consistency ─────────────────
            # Split the identification into individual items and check each
            id_items = [item.strip() for item in id_text.replace(";", ",").split(",")
                       if item.strip()]

            misaligned_items = []
            for item in id_items:
                suggestions = suggest_class_for_keyword(item)
                if suggestions:
                    top_class = suggestions[0][0]
                    top_score = suggestions[0][2]
                    if top_class != claimed_class and top_score >= 7:
                        misaligned_items.append({
                            "item": item,
                            "suggested_class": top_class,
                            "suggested_title": get_class_info(top_class)["title"] if get_class_info(top_class) else "Unknown"
                        })

            if misaligned_items:
                for mi in misaligned_items:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="WARNING",
                        class_number=claimed_class,
                        item=f"'{mi['item']}' in Class {claimed_class}",
                        finding=f"ALIGNMENT ISSUE: The item '{mi['item']}' is listed under "
                                 f"Class {claimed_class} ({class_info['title']}), but it appears "
                                 f"to better align with Class {mi['suggested_class']} "
                                 f"({mi['suggested_title']}). "
                                 f"Class and identification must tell the same story (§1401.08).",
                        recommendation=f"Either: (a) move '{mi['item']}' to Class {mi['suggested_class']}, "
                                       f"or (b) confirm that this item is indeed a "
                                       f"{class_info['title'].lower()} product/service and amend "
                                       f"the identification to clarify."
                    ))

            # ── Check 2: Bundling of multiple classes in one entry ─────────
            # Look for obvious cross-class bundling
            cross_class_indicators = []
            other_classes_suggested = set()

            for item in id_items:
                suggestions = suggest_class_for_keyword(item)
                if suggestions:
                    top_class = suggestions[0][0]
                    if top_class != claimed_class and suggestions[0][2] >= 5:
                        other_classes_suggested.add(top_class)

            if len(other_classes_suggested) >= 2:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="WARNING",
                    class_number=claimed_class,
                    item=f"Class {claimed_class} — Possible multi-class bundling",
                    finding=f"The identification for Class {claimed_class} may contain goods/services "
                             f"from multiple different classes. Items in this entry may belong to "
                             f"Classes: {', '.join(map(str, sorted(other_classes_suggested)))} "
                             f"as well as Class {claimed_class}.",
                    recommendation="Review the identification and separate goods/services into their "
                                   "correct individual classes. Each class must have only goods/services "
                                   "that properly belong in that class."
                ))
            else:
                # If no issues, give an OK
                already_flagged = any(
                    f.tmep_section == section and f.class_number == claimed_class
                    and f.severity in ["ERROR", "WARNING"]
                    for f in self.findings
                )
                if not already_flagged:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="OK",
                        class_number=claimed_class,
                        item=f"Class {claimed_class} — Class/Identification Alignment",
                        finding=f"Class {claimed_class} ({class_info['title']}) and the "
                                 f"identification appear consistent and aligned. "
                                 f"The written description is coherent with the class designation.",
                        recommendation="No action required."
                    ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.09 — IMPLEMENTATION OF CHANGES TO THE NICE AGREEMENT
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_09_implementation_of_nice_changes(self):
        """
        §1401.09 — Changes to the Nice Agreement are implemented by the USPTO
        after providing notice. Applicants must use the current edition's
        classification at the time of filing.
        
        Checks: Is the Nice edition claimed still valid and current?
        """
        section = "§1401.09"

        edition_used = self.app.nice_edition_claimed
        filing_date_str = self.app.filing_date
        current_edition = "12th"  # As of Nov 2025 TMEP

        if edition_used not in NICE_EDITION_TIMELINE:
            self.findings.append(AssessmentFinding(
                tmep_section=section,
                severity="WARNING",
                class_number=0,
                item=f"Nice Edition: '{edition_used}'",
                finding=f"Unrecognized or unspecified Nice Agreement edition: '{edition_used}'. "
                         f"Cannot verify edition-specific compliance.",
                recommendation=f"Confirm the application uses the {current_edition} Edition "
                               f"of the Nice Agreement (current as of Nov 2025)."
            ))
            return

        edition_info = NICE_EDITION_TIMELINE[edition_used]

        # Validate filing date against edition
        if filing_date_str:
            try:
                filing_dt = datetime.strptime(filing_date_str, "%Y-%m-%d").date()
                edition_start = datetime.strptime(edition_info["start"], "%Y-%m-%d").date()
                edition_end = datetime.strptime(edition_info["end"], "%Y-%m-%d").date()

                if filing_dt < edition_start:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=0,
                        item=f"Edition/Date mismatch: {edition_used} edition, filed {filing_date_str}",
                        finding=f"Filing date {filing_date_str} predates the {edition_used} Edition "
                                 f"(effective {edition_info['start']}). "
                                 f"The edition claimed was not yet in effect at filing.",
                        recommendation=f"Use the edition that was in effect on the filing date. "
                                       f"Check TMEP §1401.09-§1401.15 for edition effective dates."
                    ))
                elif filing_dt > edition_end and edition_used != current_edition:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="WARNING",
                        class_number=0,
                        item=f"Outdated edition: {edition_used} (filed {filing_date_str})",
                        finding=f"Application uses the {edition_used} Edition of the Nice Agreement, "
                                 f"but a newer edition was in effect on the filing date {filing_date_str}. "
                                 f"Current edition: {current_edition}.",
                        recommendation=f"Update classification to the {current_edition} Edition "
                                       f"requirements. Review §1401.15 for current edition changes."
                    ))
                else:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="OK",
                        class_number=0,
                        item=f"Nice Edition Version Check",
                        finding=f"Application uses the {edition_used} Edition of the Nice Agreement, "
                                 f"which was in effect on filing date {filing_date_str} "
                                 f"(Edition effective: {edition_info['start']} to "
                                 f"{'present' if edition_info['end'] == '9999-12-31' else edition_info['end']}).",
                        recommendation=f"No edition conflict detected. "
                                       f"{'This is the current edition.' if edition_used == current_edition else ''}"
                    ))
            except ValueError:
                self.findings.append(AssessmentFinding(
                    tmep_section=section,
                    severity="INFO",
                    class_number=0,
                    item="Filing date format",
                    finding="Filing date could not be parsed. Unable to verify Nice edition validity against filing date.",
                    recommendation="Provide filing date in YYYY-MM-DD format for edition compliance check."
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.10 — EFFECTIVE DATE OF CHANGES TO USPTO ID MANUAL
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_10_effective_date_id_manual(self):
        """
        §1401.10 — The ID Manual is updated periodically. New acceptable terms
        and class changes take effect on specific dates. Terms acceptable today
        may not have been acceptable on the filing date.
        
        Checks for terms that may be outdated relative to the filing date or
        that reference recently added acceptable language.
        """
        section = "§1401.10"

        # Terms added/changed after specific dates
        recently_added_terms = [
            {
                "term": "non-fungible token",
                "nft": "downloadable digital files authenticated by non-fungible tokens",
                "added_after": "2022-01-01",
                "correct_class": 9,
                "note": "NFT-related downloadable goods were added to Class 9 in the ID Manual "
                        "after USPTO guidance in 2022."
            },
            {
                "term": "artificial intelligence",
                "added_after": "2019-01-01",
                "correct_class": 42,
                "note": "AI-specific service descriptions were formally added to the ID Manual "
                        "in updated USPTO guidance."
            },
            {
                "term": "cryptocurrency",
                "added_after": "2014-01-01",
                "correct_class": 36,
                "note": "Cryptocurrency financial services were added to Class 36 ID Manual entries."
            }
        ]

        filing_date_str = self.app.filing_date

        for cls_entry in self.app.classes:
            id_text_lower = cls_entry.identification.lower()

            for term_info in recently_added_terms:
                if term_info["term"] in id_text_lower:
                    if filing_date_str:
                        try:
                            filing_dt = datetime.strptime(filing_date_str, "%Y-%m-%d").date()
                            added_dt = datetime.strptime(term_info["added_after"], "%Y-%m-%d").date()

                            if filing_dt < added_dt:
                                self.findings.append(AssessmentFinding(
                                    tmep_section=section,
                                    severity="WARNING",
                                    class_number=cls_entry.class_number,
                                    item=f"'{term_info['term']}' — ID Manual date check",
                                    finding=f"The term '{term_info['term']}' in the identification "
                                             f"may not have been accepted in the ID Manual at the "
                                             f"time of filing ({filing_date_str}). "
                                             f"{term_info['note']}",
                                    recommendation=f"Verify this term was acceptable in the USPTO ID Manual "
                                                   f"at the time of filing. If not, amend to use language "
                                                   f"acceptable as of the filing date."
                                ))
                            else:
                                self.findings.append(AssessmentFinding(
                                    tmep_section=section,
                                    severity="INFO",
                                    class_number=cls_entry.class_number,
                                    item=f"'{term_info['term']}' — Modern term detected",
                                    finding=f"Modern/specialized term '{term_info['term']}' detected. "
                                             f"{term_info['note']} "
                                             f"This term is acceptable in the current ID Manual.",
                                    recommendation=f"Ensure identification uses the exact accepted "
                                                   f"ID Manual language for this term in Class {term_info['correct_class']}."
                                ))
                        except ValueError:
                            pass

        # General notice
        self.findings.append(AssessmentFinding(
            tmep_section=section,
            severity="INFO",
            class_number=0,
            item="ID Manual Compliance",
            finding="Per §1401.10, identification language must conform to ID Manual entries "
                     "as they existed at the time the registration is sought (not just at filing). "
                     "The ID Manual is updated periodically and applicants must use current "
                     "acceptable identification at time of registration.",
            recommendation="Verify all identification language against the current USPTO ID Manual "
                           "at: https://idm.uspto.gov. Use pre-approved ID Manual language where possible."
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.11 — CLASS 42 RESTRUCTURING (8TH EDITION)
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_11_class42_restructuring_8th_edition(self):
        """
        §1401.11 — The 8th Edition of the Nice Agreement (effective January 1, 2002)
        split the old Class 42 into four new classes:
        - New Class 42: Scientific/tech services
        - New Class 43: Food and drink services / accommodation
        - New Class 44: Medical/veterinary/beauty/agricultural services
        - New Class 45: Legal/security/personal/social services
        
        Applications using old Class 42 for restaurant, medical, legal, or social
        services need to be reclassified.
        """
        section = "§1401.11"

        # Services that used to be in old Class 42 pre-8th Edition
        old_class_42_misplacements = {
            "restaurant": (43, "Food/restaurant services → Class 43 (split from old Class 42 in 8th Ed.)"),
            "food service": (43, "Food services → Class 43"),
            "hotel": (43, "Hotel/accommodation → Class 43"),
            "catering": (43, "Catering services → Class 43"),
            "accommodation": (43, "Accommodation → Class 43"),
            "medical service": (44, "Medical services → Class 44 (split from old Class 42 in 8th Ed.)"),
            "dental service": (44, "Dental services → Class 44"),
            "veterinary": (44, "Veterinary services → Class 44"),
            "beauty service": (44, "Beauty services → Class 44"),
            "salon": (44, "Salon services → Class 44"),
            "healthcare": (44, "Healthcare services → Class 44"),
            "legal service": (45, "Legal services → Class 45 (split from old Class 42 in 8th Ed.)"),
            "law firm": (45, "Law firm services → Class 45"),
            "security guard": (45, "Security guard services → Class 45"),
            "social service": (45, "Social services → Class 45"),
        }

        for cls_entry in self.app.classes:
            if cls_entry.class_number != 42:
                continue

            id_text_lower = cls_entry.identification.lower()

            for service_term, (correct_class, reason) in old_class_42_misplacements.items():
                if service_term in id_text_lower:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=42,
                        item=f"'{service_term}' in Class 42",
                        finding=f"POST-8TH EDITION CLASS 42 VIOLATION: '{service_term}' is placed "
                                 f"in Class 42, but this service was moved to Class {correct_class} "
                                 f"when the 8th Edition of the Nice Agreement restructured Class 42 "
                                 f"(effective Jan 1, 2002). {reason}",
                        recommendation=f"Move '{service_term}' from Class 42 to Class {correct_class}. "
                                       f"Class 42 (post-8th Edition) covers only scientific and "
                                       f"technological services, IT services, and software-related services."
                    ))

        # Also check if filing date is pre-8th edition and Class 42 is used
        if self.app.filing_date:
            try:
                filing_dt = datetime.strptime(self.app.filing_date, "%Y-%m-%d").date()
                edition_8_start = date(2002, 1, 1)  # Effective date

                if filing_dt < edition_8_start:
                    # Pre-8th edition application — old Class 42 rules MAY apply
                    for cls_entry in self.app.classes:
                        if cls_entry.class_number in [43, 44, 45]:
                            self.findings.append(AssessmentFinding(
                                tmep_section=section,
                                severity="INFO",
                                class_number=cls_entry.class_number,
                                item=f"Pre-8th Edition filing using Class {cls_entry.class_number}",
                                finding=f"This application has a filing date ({self.app.filing_date}) "
                                         f"BEFORE the 8th Edition restructuring of Class 42 "
                                         f"(effective Jan 1, 2002). Classes 43, 44, and 45 "
                                         f"did not exist before this date.",
                                recommendation="Review the application against the edition in effect "
                                               "at the time of filing. Consult §1401.11 for "
                                               "transition rules for pre-8th Edition applications."
                            ))
                            break
                else:
                    # Check that no old Class 42 services exist in other classes as a reminder
                    class_42_entries = [c for c in self.app.classes if c.class_number == 42]
                    if not class_42_entries:
                        self.findings.append(AssessmentFinding(
                            tmep_section=section,
                            severity="INFO",
                            class_number=0,
                            item="Class 42 Restructuring Check",
                            finding="No Class 42 entries in this application. "
                                     "Note: As of 8th Edition (Jan 1, 2002), Class 42 covers only "
                                     "scientific/technological/IT services. "
                                     "Restaurant services → Class 43; Medical → Class 44; "
                                     "Legal → Class 45.",
                            recommendation="No action required for §1401.11."
                        ))
                    else:
                        # Class 42 exists - check it's being used for correct services
                        for cls42 in class_42_entries:
                            id_lower = cls42.identification.lower()
                            has_tech_service = any(
                                kw in id_lower for kw in [
                                    "software", "technology", "it service", "computer",
                                    "research", "cloud", "saas", "data", "programming",
                                    "cybersecurity", "network", "engineering service"
                                ]
                            )
                            if has_tech_service:
                                self.findings.append(AssessmentFinding(
                                    tmep_section=section,
                                    severity="OK",
                                    class_number=42,
                                    item="Class 42 usage (post-8th Edition)",
                                    finding="Class 42 is being used for technology/scientific services "
                                             "consistent with the post-8th Edition restructuring.",
                                    recommendation="No action required."
                                ))
            except ValueError:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.12 — 9TH EDITION CHANGES
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_12_9th_edition_changes(self):
        """
        §1401.12 — 9th Edition (2002–2006) changes.
        Notable: Further refinements to Class 41 (education/entertainment) and Class 42.
        Some services previously in Class 41 moved; new service descriptions added.
        """
        section = "§1401.12"

        # Key 9th Edition changes to check
        ninth_edition_changes = [
            {
                "old_placement": (41, "Internet access provider"),
                "new_class": 38,
                "note": "Internet access provider services: Class 41 → Class 38 (Telecom) in 9th Ed."
            }
        ]

        for cls_entry in self.app.classes:
            id_text_lower = cls_entry.identification.lower()

            for change in ninth_edition_changes:
                old_class, old_term = change["old_placement"]
                if cls_entry.class_number == old_class and old_term.lower() in id_text_lower:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="WARNING",
                        class_number=cls_entry.class_number,
                        item=f"'{old_term}' in Class {old_class}",
                        finding=f"9TH EDITION CHANGE: '{old_term}' was reclassified from "
                                 f"Class {old_class} to Class {change['new_class']} "
                                 f"in the 9th Edition. {change['note']}",
                        recommendation=f"Move '{old_term}' from Class {old_class} to "
                                       f"Class {change['new_class']}."
                    ))

        self.findings.append(AssessmentFinding(
            tmep_section=section,
            severity="INFO",
            class_number=0,
            item="9th Edition Nice Agreement Review",
            finding="9th Edition (2002–2006): Key changes included refinements to educational "
                     "and entertainment services (Class 41), further definition of Class 42 "
                     "technology services, and movement of internet-related services to Class 38. "
                     "No critical violations detected under 9th Edition rules in this application.",
            recommendation="If application was filed during 2002–2006, verify against 9th Edition "
                           "ID Manual entries. For current applications, 12th Edition applies."
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.13 — 10TH EDITION CHANGES
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_13_10th_edition_changes(self):
        """
        §1401.13 — 10th Edition (2007–2011) changes.
        Notable: Major expansion of Class 9 to include DOWNLOADABLE DIGITAL CONTENT.
        Downloadable music, video, and software explicitly added to Class 9.
        """
        section = "§1401.13"

        # 10th Edition: Class 9 expanded to include downloadable digital content
        digital_content_terms = [
            "downloadable music", "downloadable video", "downloadable ringtone",
            "downloadable image", "downloadable audio", "downloadable software",
            "downloadable ebook", "downloadable digital content"
        ]

        for cls_entry in self.app.classes:
            id_text_lower = cls_entry.identification.lower()

            # Check if digital content terms are in wrong class
            for term in digital_content_terms:
                if term in id_text_lower and cls_entry.class_number != 9:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="ERROR",
                        class_number=cls_entry.class_number,
                        item=f"'{term}' in Class {cls_entry.class_number}",
                        finding=f"10TH EDITION CHANGE VIOLATION: '{term}' is a DOWNLOADABLE DIGITAL "
                                 f"PRODUCT. Per the 10th Edition expansion of Class 9 (effective 2007), "
                                 f"all downloadable digital content belongs in Class 9 — "
                                 f"not in Class {cls_entry.class_number}.",
                        recommendation=f"Move '{term}' to Class 9 (Scientific and Electronic Apparatus). "
                                       f"Class 9 now explicitly includes downloadable digital content "
                                       f"per §1401.13 and 10th Edition Nice Agreement."
                    ))

            # Check if Class 9 is used correctly for digital content
            if cls_entry.class_number == 9:
                has_digital = any(term in id_text_lower for term in digital_content_terms)
                if has_digital:
                    self.findings.append(AssessmentFinding(
                        tmep_section=section,
                        severity="OK",
                        class_number=9,
                        item="Class 9 — Downloadable digital content",
                        finding="Downloadable digital content correctly placed in Class 9 "
                                 "per 10th Edition Nice Agreement expansion.",
                        recommendation="Ensure identification specifies 'downloadable' to distinguish "
                                       "from streaming services (which go in Class 41/42)."
                    ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.14 — 11TH EDITION CHANGES
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_14_11th_edition_changes(self):
        """
        §1401.14 — 11th Edition (2012–2022) changes.
        Notable: 
        - Class 35 expanded: Online marketplace/retail store services added
        - Class 38 expanded: Social media platform services, online chat
        - Class 42 expanded: Software as a Service (SaaS), cloud computing, 
          Platform as a Service (PaaS), Infrastructure as a Service (IaaS)
        """
        section = "§1401.14"

        eleventh_edition_checks = [
            {
                "term": "online marketplace",
                "expected_class": 35,
                "note": "11th Ed.: Online marketplace/platform services added explicitly to Class 35."
            },
            {
                "term": "retail store",
                "expected_class": 35,
                "note": "11th Ed.: Online retail store services confirmed in Class 35."
            },
            {
                "term": "social media",
                "expected_class": 38,
                "note": "11th Ed.: Social media platform services added to Class 38 (telecom)."
            },
            {
                "term": "online social network",
                "expected_class": 38,
                "note": "11th Ed.: Online social networking services → Class 38."
            },
            {
                "term": "saas",
                "expected_class": 42,
                "note": "11th Ed.: Software as a Service (SaaS) explicitly codified in Class 42."
            },
            {
                "term": "cloud computing",
                "expected_class": 42,
                "note": "11th Ed.: Cloud computing services added to Class 42."
            },
            {
                "term": "platform as a service",
                "expected_class": 42,
                "note": "11th Ed.: PaaS services → Class 42."
            }
        ]

        for cls_entry in self.app.classes:
            id_text_lower = cls_entry.identification.lower()

            for check in eleventh_edition_checks:
                if check["term"] in id_text_lower:
                    if cls_entry.class_number != check["expected_class"]:
                        self.findings.append(AssessmentFinding(
                            tmep_section=section,
                            severity="ERROR",
                            class_number=cls_entry.class_number,
                            item=f"'{check['term']}' in Class {cls_entry.class_number}",
                            finding=f"11TH EDITION CHANGE: '{check['term']}' should be in "
                                     f"Class {check['expected_class']} per 11th Edition changes. "
                                     f"{check['note']} "
                                     f"Currently placed in Class {cls_entry.class_number}.",
                            recommendation=f"Move '{check['term']}' to Class {check['expected_class']}."
                        ))
                    else:
                        self.findings.append(AssessmentFinding(
                            tmep_section=section,
                            severity="OK",
                            class_number=cls_entry.class_number,
                            item=f"'{check['term']}' classification (11th Edition)",
                            finding=f"'{check['term']}' correctly placed in Class {cls_entry.class_number} "
                                     f"per 11th Edition Nice Agreement changes.",
                            recommendation="No action required."
                        ))

    # ─────────────────────────────────────────────────────────────────────────
    # §1401.15 — 12TH EDITION CHANGES (CURRENT — Nov 2025)
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1401_15_12th_edition_changes(self):
        """
        §1401.15 — 12th Edition (current, effective Jan 1, 2023) changes.
        Notable:
        - AI/Machine learning services explicitly in Class 42
        - NFT-related digital goods in Class 9
        - Blockchain-based services in Class 42
        - Virtual goods/metaverse goods in Class 9
        - Downloadable virtual items → Class 9
        - Online identity verification → Class 42 or Class 45
        """
        section = "§1401.15"

        twelfth_edition_checks = [
            {
                "term": "artificial intelligence",
                "expected_class": 42,
                "wrong_class_examples": [9, 35],
                "note": "12th Ed.: AI services (AI software development, AI consulting) → Class 42."
            },
            {
                "term": "machine learning",
                "expected_class": 42,
                "wrong_class_examples": [9, 35],
                "note": "12th Ed.: Machine learning services → Class 42."
            },
            {
                "term": "non-fungible token",
                "expected_class": 9,
                "wrong_class_examples": [35, 36],
                "note": "12th Ed.: NFT digital files/goods → Class 9. NFT marketplace services → Class 35."
            },
            {
                "term": "nft",
                "expected_class": 9,
                "wrong_class_examples": [35, 36, 42],
                "note": "12th Ed.: Downloadable NFT goods → Class 9. "
                        "NFT authentication services → Class 42."
            },
            {
                "term": "virtual goods",
                "expected_class": 9,
                "wrong_class_examples": [28, 35],
                "note": "12th Ed.: Virtual/digital goods (metaverse items, in-game items) → Class 9."
            },
            {
                "term": "blockchain",
                "expected_class": 42,
                "wrong_class_examples": [9, 36],
                "note": "12th Ed.: Blockchain technology services → Class 42. "
                        "Blockchain financial services → Class 36."
            },
            {
                "term": "metaverse",
                "expected_class": 41,
                "wrong_class_examples": [9, 42],
                "note": "12th Ed.: Metaverse entertainment/virtual events → Class 41. "
                        "Virtual goods within metaverse → Class 9."
            }
        ]

        for cls_entry in self.app.classes:
            id_text_lower = cls_entry.identification.lower()

            for check in twelfth_edition_checks:
                if check["term"] in id_text_lower:
                    if cls_entry.class_number in check.get("wrong_class_examples", []):
                        self.findings.append(AssessmentFinding(
                            tmep_section=section,
                            severity="WARNING",
                            class_number=cls_entry.class_number,
                            item=f"'{check['term']}' in Class {cls_entry.class_number}",
                            finding=f"12TH EDITION (CURRENT) NOTE: '{check['term']}' may be "
                                     f"misplaced in Class {cls_entry.class_number}. "
                                     f"{check['note']}",
                            recommendation=f"Per the 12th Edition Nice Agreement (current), "
                                           f"consider whether '{check['term']}' belongs in "
                                           f"Class {check['expected_class']}. "
                                           f"Review the latest USPTO ID Manual entries."
                        ))
                    elif cls_entry.class_number == check["expected_class"]:
                        self.findings.append(AssessmentFinding(
                            tmep_section=section,
                            severity="OK",
                            class_number=cls_entry.class_number,
                            item=f"'{check['term']}' — 12th Edition compliance",
                            finding=f"'{check['term']}' correctly placed in Class {cls_entry.class_number} "
                                     f"per 12th Edition Nice Agreement (current edition). {check['note']}",
                            recommendation="No action required."
                        ))

        # General 12th Edition notice
        self.findings.append(AssessmentFinding(
            tmep_section=section,
            severity="INFO",
            class_number=0,
            item="12th Edition (Current) Compliance — Nov 2025",
            finding="This assessment is based on the 12th Edition of the Nice Agreement "
                     "(effective January 1, 2023), which is the current edition as of Nov 2025. "
                     "Key additions: AI/ML services (Class 42), virtual goods/NFTs (Class 9), "
                     "blockchain services (Class 42), metaverse entertainment (Class 41).",
            recommendation="Ensure all identification language conforms to 12th Edition requirements "
                           "and current USPTO ID Manual entries."
        ))
