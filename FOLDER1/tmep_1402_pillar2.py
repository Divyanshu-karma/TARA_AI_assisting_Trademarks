"""
TMEP CHAPTER 1402 — IDENTIFICATION OF GOODS AND SERVICES
PILLAR 2 ASSESSMENT ENGINE
==========================================================
Based on: TMEP November 2025 Edition

PILLAR FLOW:
    Pillar 1 Output (ClassEntry + AssessmentFinding list)
         ↓
    Pillar 2 — Identification Assessment (this file)
         ↓
    Pillar 3 — Multi-Class Filing Requirements

HOW PILLAR 1 FEEDS PILLAR 2:
    - Pillar 1 confirms/corrects the class number → Pillar 2 uses confirmed class
      to validate whether the identification is appropriate for that class
    - Pillar 1 detects specimen type → Pillar 2 §1402.05 uses it to check
      accuracy of identification against what specimen actually shows
    - Pillar 1 flags misclassified items → Pillar 2 skips accuracy checks
      on those items (no point validating wording in wrong class)
    - Pillar 1 filing basis (1(a) vs 1(b)) → Pillar 2 §1402.10 applies
      different rules for intent-to-use applications
"""

import re
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# ─── UNCHANGED FROM YOUR ORIGINAL — KEPT VERBATIM ───────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class IdentificationRecord:
    """
    Stores applicant's identification EXACTLY as submitted.
    No normalization, no trimming, no case modification.
    """
    original_text: str

    def get_verbatim(self) -> str:
        """Returns the exact wording as filed."""
        return self.original_text


# ═══════════════════════════════════════════════════════════════════════════════
# ─── ADDED: PILLAR 1 CONTEXT BRIDGE ─────────────────────────────────────────
# Lightweight container to carry Pillar 1 results into Pillar 2.
# You don't need to import the full Pillar 1 module — just pass these fields.
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Pillar1ClassContext:
    """
    Carries the relevant Pillar 1 findings for a single class entry
    into the Pillar 2 assessment.

    Populate this from your Pillar 1 ClassEntry + AssessmentFinding objects.
    """
    class_number: int                    # Confirmed (or suspected) class from Pillar 1
    class_title: str                     # e.g., "Scientific and Electronic Apparatus"
    class_category: str                  # "GOODS" or "SERVICES"
    filing_basis: str                    # "1(a)", "1(b)", "44(d)", etc.
    specimen_type: str = ""             # From Pillar 1 ClassEntry
    specimen_description: str = ""     # From Pillar 1 ClassEntry
    has_pillar1_class_error: bool = False   # True if Pillar 1 flagged a misclassification ERROR
    has_pillar1_class_warning: bool = False # True if Pillar 1 flagged a class WARNING
    pillar1_error_summary: str = ""    # Brief summary of Pillar 1 errors for this class


def build_pillar1_context_from_dicts(class_entry_dict: dict,
                                      pillar1_findings: list) -> "Pillar1ClassContext":
    """
    Helper to build Pillar1ClassContext from raw dicts (when not using full Pillar 1 objects).
    
    Args:
        class_entry_dict: A dict with keys: class_number, identification, specimen_type,
                          specimen_description, filing_basis
        pillar1_findings: List of AssessmentFinding dicts (or objects with .severity,
                          .class_number, .finding attributes) from Pillar 1
    
    Example:
        ctx = build_pillar1_context_from_dicts(
            {"class_number": 9, "filing_basis": "1(a)", "specimen_type": "website screenshot", ...},
            pillar1_result["findings"]
        )
    """
    cls_num = int(class_entry_dict.get("class_number", 0))

    # Pull relevant findings for this class from Pillar 1
    class_findings = []
    for f in pillar1_findings:
        # Support both dict and object
        fn = f if isinstance(f, dict) else f.__dict__
        if fn.get("class_number", -1) == cls_num or fn.get("class_number", -1) == 0:
            class_findings.append(fn)

    errors = [f for f in class_findings if f.get("severity") == "ERROR"]
    warnings = [f for f in class_findings if f.get("severity") == "WARNING"]
    error_summary = "; ".join(e.get("finding", "")[:80] for e in errors[:2]) if errors else ""

    # Try to get class info if nice_classification_db is available
    class_title = ""
    class_category = ""
    try:
        from nice_classification_db import get_class_info
        info = get_class_info(cls_num)
        if info:
            class_title = info["title"]
            class_category = info["category"]
    except ImportError:
        pass

    return Pillar1ClassContext(
        class_number=cls_num,
        class_title=class_title,
        class_category=class_category,
        filing_basis=class_entry_dict.get("filing_basis", "1(a)"),
        specimen_type=class_entry_dict.get("specimen_type", ""),
        specimen_description=class_entry_dict.get("specimen_description", ""),
        has_pillar1_class_error=len(errors) > 0,
        has_pillar1_class_warning=len(warnings) > 0,
        pillar1_error_summary=error_summary
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ─── RESULT MODEL — EXPANDED FROM YOUR ORIGINAL ──────────────────────────────
# Added: per-subsection findings list so each check is traceable
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SubsectionFinding:
    """A single finding tied to a specific TMEP §1402.xx sub-section."""
    tmep_section: str     # e.g., "§1402.03"
    severity: str         # "ERROR", "WARNING", "INFO", "OK"
    item: str             # What was checked
    finding: str          # What was found
    recommendation: str   # What to do


@dataclass
class TMEP1402AnalysisResult:
    # ── Your original fields — UNCHANGED ─────────────────────────────────────
    is_definite: bool
    identified_goods_services: List[str]
    purpose_detected: bool
    vague_terms_found: List[str]
    structural_issues: List[str]
    reasoning: str
    # ── ADDED: Per-subsection breakdown ──────────────────────────────────────
    subsection_findings: List[SubsectionFinding] = field(default_factory=list)
    pillar1_dependency_note: str = ""  # Notes how Pillar 1 results affected this assessment


# ═══════════════════════════════════════════════════════════════════════════════
# TMEP §1402 LENS ENGINE — IMPROVED
# ═══════════════════════════════════════════════════════════════════════════════

class TMEP1402Lens:
    """
    Applies the controlling questions under TMEP §1402:
    Does the wording clearly identify particular goods/services
    and their commercial purpose in sufficiently definite terms?

    CHANGED from original:
    - Accepts optional Pillar1ClassContext for cross-pillar validation
    - Each check now maps to a specific §1402.xx sub-section
    - is_definite logic is more nuanced (weighted, not all-or-nothing)
    - Added §1402.05, §1402.09, §1402.10, §1402.11 checks
    """

    # ── UNCHANGED from your original ─────────────────────────────────────────
    VAGUE_TERMS = [
        "including",
        "and related",
        "etc",
        "etc.",
        "products",
        "services",           # vague ONLY when used alone (see _check_1402_03)
        "solutions",
        "technology",
        "equipment",
        "devices",
        "materials",
        "systems",
        "components",
        "platform",
        # ADDED — additional indefinite terms per USPTO practice
        "miscellaneous",
        "various",
        "all types",
        "any",
        "type of",
        "kind of",
        "and the like",
        "other",              # as a standalone catch-all
    ]

    PURPOSE_PATTERNS = [
        r"\bfor\b",
        r"\bnamely\b",
        r"\bconsisting of\b",
        r"\bin the field of\b",
        r"\bused for\b"
    ]

    # ADDED — Terms banned per §1402.09
    BANNED_TERMS_1402_09 = ["applicant", "registrant"]

    # ADDED — Service identification must describe activity rendered FOR others
    SERVICE_ACTIVITY_PATTERNS = [
        r"\bservices for\b",
        r"\bservices in the (nature|field)\b",
        r"\bproviding\b",
        r"\brendering\b",
        r"\boffering\b",
        r"\bconsulting\b",
    ]

    def __init__(self, identification_text: str,
                 pillar1_context: Optional[Pillar1ClassContext] = None):
        self.text = identification_text
        self.p1 = pillar1_context   # None if running standalone without Pillar 1

    # ─────────────────────────────────────────────────────────────────────────
    # UNCHANGED from your original
    # ─────────────────────────────────────────────────────────────────────────

    def extract_candidate_goods(self) -> List[str]:
        """
        Extracts potential goods/services by splitting on semicolons.
        TMEP §1402.01: Semicolons separate distinct categories.
        """
        segments = re.split(r";", self.text)
        cleaned = [seg.strip() for seg in segments if seg.strip()]
        return cleaned

    def detect_purpose_language(self) -> bool:
        """Detects whether the ID specifies purpose qualifiers."""
        for pattern in self.PURPOSE_PATTERNS:
            if re.search(pattern, self.text, re.IGNORECASE):
                return True
        return False

    def detect_vague_terms(self) -> List[str]:
        """Flags indefinite or catch-all terminology."""
        found = []
        for term in self.VAGUE_TERMS:
            pattern = rf"\b{re.escape(term)}(?:\b|\.|\s|$)"
            if re.search(pattern, self.text, re.IGNORECASE) and term not in found:
                # CHANGED: "services" alone is vague; "services for X" is not
                if term == "services":
                    if not re.search(r"\bservices\s+(for|in|of|namely|consisting)\b",
                                     self.text, re.IGNORECASE):
                        found.append(term)
                else:
                    found.append(term)
        return found

    def detect_structural_issues(self) -> List[str]:
        """
        Flags structural issues — UNCHANGED from your original.
        """
        issues = []
        and_count = len(re.findall(r"\band\b", self.text, re.IGNORECASE))
        if and_count > 3:
            issues.append("Excessive conjunction stacking ('and') may indicate over-breadth.")
        if re.search(r"[\(\)\[\]\{\}]", self.text):
            issues.append("Parentheses or brackets detected. Prohibited under TMEP §1402.12.")
        return issues

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.01: General specificity check
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_01(self, segments: List[str]) -> SubsectionFinding:
        """§1402.01 — Identification must list particular goods/services."""
        if not segments:
            return SubsectionFinding(
                tmep_section="§1402.01",
                severity="ERROR",
                item="Identification text",
                finding="Identification is empty or cannot be parsed into distinct goods/services.",
                recommendation="Provide a clear, itemized list of goods/services separated by semicolons."
            )
        return SubsectionFinding(
            tmep_section="§1402.01",
            severity="OK",
            item=f"{len(segments)} item(s) identified",
            finding=f"Identification contains {len(segments)} item(s): "
                    f"{'; '.join(s[:40] for s in segments[:3])}{'...' if len(segments)>3 else ''}",
            recommendation="No action required."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.02: Filing date entitlement
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_02(self, segments: List[str]) -> SubsectionFinding:
        """
        §1402.02 — Identification must be complete enough at filing to
        secure the filing date. Completely blank or placeholder text fails.
        """
        placeholders = ["tbd", "to be determined", "see attached", "n/a",
                        "[insert]", "xxx", "your goods here"]
        text_lower = self.text.lower().strip()

        if any(p in text_lower for p in placeholders):
            return SubsectionFinding(
                tmep_section="§1402.02",
                severity="ERROR",
                item="Placeholder text detected",
                finding="Identification contains placeholder or incomplete text. "
                        "Application will not be entitled to its filing date.",
                recommendation="Replace placeholder text with a complete, definite identification "
                               "of actual goods/services."
            )
        if len(text_lower) < 10:
            return SubsectionFinding(
                tmep_section="§1402.02",
                severity="ERROR",
                item="Identification too short",
                finding="Identification is too brief to secure a filing date.",
                recommendation="Provide a complete identification of goods/services."
            )
        return SubsectionFinding(
            tmep_section="§1402.02",
            severity="OK",
            item="Filing date entitlement",
            finding="Identification appears complete enough to support filing date entitlement.",
            recommendation="No action required."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.03: Specificity of terms (uses your original vague detection)
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_03(self, vague_found: List[str]) -> SubsectionFinding:
        """
        §1402.03 — Terms must be specific enough. Vague or indefinite terms
        are unacceptable. CHANGED: severity is weighted — standalone vague
        terms are WARNING; structural vague terms are ERROR.
        """
        severe_vague = [t for t in vague_found
                        if t in ["miscellaneous", "various", "all types", "any",
                                 "and the like", "etc", "etc."]]
        mild_vague = [t for t in vague_found if t not in severe_vague]

        if severe_vague:
            return SubsectionFinding(
                tmep_section="§1402.03",
                severity="ERROR",
                item=f"Indefinite terms: {', '.join(severe_vague)}",
                finding=f"Severely indefinite terms found: {', '.join(severe_vague)}. "
                        "These are categorically unacceptable under USPTO practice.",
                recommendation="Remove all indefinite terms. Replace with specific, "
                               "enumerated goods/services."
            )
        if mild_vague:
            return SubsectionFinding(
                tmep_section="§1402.03",
                severity="WARNING",
                item=f"Potentially vague terms: {', '.join(mild_vague)}",
                finding=f"Possibly indefinite terms found: {', '.join(mild_vague)}. "
                        "These may be acceptable with additional specificity.",
                recommendation=f"Review terms: {', '.join(mild_vague)}. "
                               "Add 'namely' clauses to specify exact goods/services."
            )
        return SubsectionFinding(
            tmep_section="§1402.03",
            severity="OK",
            item="Specificity check",
            finding="No indefinite terms detected. Identification appears sufficiently specific.",
            recommendation="No action required."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.05: Accuracy — cross-checked against Pillar 1 specimen
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_05(self) -> SubsectionFinding:
        """
        §1402.05 — Identification must accurately reflect what the applicant
        actually offers, as evidenced by the specimen (from Pillar 1).

        KEY PILLAR 1 INTEGRATION POINT:
        Pillar 1 gives us the specimen_description. Here we check whether
        the identification text is consistent with what the specimen shows.
        """
        if not self.p1:
            return SubsectionFinding(
                tmep_section="§1402.05",
                severity="INFO",
                item="Accuracy check (no Pillar 1 context)",
                finding="No Pillar 1 context provided. Cannot cross-check identification "
                        "accuracy against specimen.",
                recommendation="Run with Pillar 1 context for full §1402.05 accuracy check."
            )

        # If Pillar 1 already flagged a class ERROR, accuracy check is secondary
        if self.p1.has_pillar1_class_error:
            return SubsectionFinding(
                tmep_section="§1402.05",
                severity="WARNING",
                item=f"Class {self.p1.class_number} — Accuracy deferred",
                finding="Pillar 1 detected a classification ERROR for this class. "
                        "Accuracy of identification cannot be confirmed until the class "
                        f"is corrected. Pillar 1 issue: {self.p1.pillar1_error_summary[:100]}",
                recommendation="Resolve Pillar 1 classification errors first, then "
                               "re-assess identification accuracy in the correct class."
            )

        # Intent-to-use: no specimen yet, different accuracy standard
        if self.p1.filing_basis == "1(b)":
            return SubsectionFinding(
                tmep_section="§1402.05",
                severity="INFO",
                item=f"Class {self.p1.class_number} — §1(b) accuracy standard",
                finding="Intent-to-use application (§1(b)). Identification must accurately "
                        "reflect goods/services applicant has a bona fide intention to use. "
                        "Specimen not yet required — accuracy will be verified at SOU stage.",
                recommendation="Ensure identification reflects actual intended use. "
                               "Overly broad identifications may cause problems at SOU stage."
            )

        # Cross-check identification text against specimen description
        id_lower = self.text.lower()
        spec_lower = self.p1.specimen_description.lower()

        if not spec_lower:
            return SubsectionFinding(
                tmep_section="§1402.05",
                severity="INFO",
                item="No specimen description from Pillar 1",
                finding="Specimen description not available for accuracy cross-check.",
                recommendation="Provide specimen description in Pillar 1 class entry for full check."
            )

        # Look for obvious mismatches: words in specimen not in identification
        id_words = set(re.findall(r"\b\w{4,}\b", id_lower))
        spec_words = set(re.findall(r"\b\w{4,}\b", spec_lower))
        overlap = id_words & spec_words
        overlap_ratio = len(overlap) / max(len(spec_words), 1)

        if overlap_ratio < 0.1 and len(spec_words) > 3:
            return SubsectionFinding(
                tmep_section="§1402.05",
                severity="WARNING",
                item="Low overlap between identification and specimen",
                finding=f"Low conceptual overlap between identification and specimen description "
                        f"(~{int(overlap_ratio*100)}% word overlap). "
                        "Identification may not accurately reflect the actual goods/services "
                        "shown in the specimen.",
                recommendation="Review whether identification accurately describes what the "
                               "specimen actually shows. Amend if over-broad or misaligned."
            )

        return SubsectionFinding(
            tmep_section="§1402.05",
            severity="OK",
            item="Accuracy vs. specimen",
            finding=f"Identification appears consistent with the specimen provided "
                    f"(~{int(overlap_ratio*100)}% conceptual overlap).",
            recommendation="No action required."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.09: Banned terms "Applicant" / "Registrant"
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_09(self) -> SubsectionFinding:
        """
        §1402.09 — The terms "applicant" and "registrant" must not appear
        in the identification of goods or services.
        """
        found_banned = []
        for term in self.BANNED_TERMS_1402_09:
            if re.search(rf"\b{term}\b", self.text, re.IGNORECASE):
                found_banned.append(term)

        if found_banned:
            return SubsectionFinding(
                tmep_section="§1402.09",
                severity="ERROR",
                item=f"Banned terms found: {', '.join(found_banned)}",
                finding=f"The term(s) '{', '.join(found_banned)}' appear in the identification. "
                        "Per §1402.09, 'applicant' and 'registrant' are inappropriate "
                        "in identifications of goods and services.",
                recommendation=f"Remove '{', '.join(found_banned)}' from the identification. "
                               "Rewrite the relevant clause without reference to the applicant/registrant."
            )
        return SubsectionFinding(
            tmep_section="§1402.09",
            severity="OK",
            item="Banned terms check",
            finding="No prohibited terms ('applicant', 'registrant') found.",
            recommendation="No action required."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.10: §1(b) intent-to-use specific requirements
    # KEY PILLAR 1 INTEGRATION: filing_basis comes from Pillar 1 ClassEntry
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_10(self) -> SubsectionFinding:
        """
        §1402.10 — For §1(b) intent-to-use applications, the identification
        must still be complete and definite at filing (same standard as §1(a)).
        
        Uses filing_basis from Pillar 1 context.
        """
        basis = self.p1.filing_basis if self.p1 else "1(a)"

        if basis != "1(b)":
            return SubsectionFinding(
                tmep_section="§1402.10",
                severity="INFO",
                item=f"Filing basis: {basis}",
                finding=f"Application is filed under {basis}, not §1(b). "
                        "§1402.10 intent-to-use requirements do not apply.",
                recommendation="No action required."
            )

        # For §1(b): check for future-tense or speculative wording
        future_tense_patterns = [
            r"\bwill\b", r"\bintend\b", r"\bplanning to\b",
            r"\bproposed\b", r"\bfuture\b"
        ]
        found_future = [p.strip(r"\b") for p in future_tense_patterns
                       if re.search(p, self.text, re.IGNORECASE)]

        if found_future:
            return SubsectionFinding(
                tmep_section="§1402.10",
                severity="WARNING",
                item="Future-tense language in §1(b) identification",
                finding="Identification contains future-tense or speculative language "
                        f"({', '.join(found_future)}). Even for §1(b) applications, "
                        "the identification must describe goods/services definitively, "
                        "not contingently.",
                recommendation="Remove future-tense wording. State goods/services definitively "
                               "as if already in use (the filing basis covers the intent — "
                               "the identification does not need to reflect it)."
            )

        return SubsectionFinding(
            tmep_section="§1402.10",
            severity="OK",
            item="§1(b) identification format",
            finding="§1(b) identification is stated definitively without future-tense language.",
            recommendation="No action required. Remember: specimen must be filed with SOU."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.11: Services must be described as activities for others
    # KEY PILLAR 1 INTEGRATION: class_category from Pillar 1 ClassEntry
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_11(self) -> SubsectionFinding:
        """
        §1402.11 — Services must be identified as activities performed FOR OTHERS,
        not as internal activities of the applicant.
        
        Uses class_category from Pillar 1 context to determine if this applies.
        """
        # Determine if this is a services class
        is_services = False
        if self.p1:
            is_services = (self.p1.class_category == "SERVICES")
        else:
            # Fallback: detect service language if no Pillar 1 context
            is_services = bool(re.search(r"\bservice[s]?\b", self.text, re.IGNORECASE))

        if not is_services:
            return SubsectionFinding(
                tmep_section="§1402.11",
                severity="INFO",
                item="§1402.11 services check",
                finding="This appears to be a goods class. §1402.11 services format "
                        "requirement does not apply.",
                recommendation="No action required."
            )

        # Check for service activity language
        has_service_activity = any(
            re.search(p, self.text, re.IGNORECASE)
            for p in self.SERVICE_ACTIVITY_PATTERNS
        )

        # Check for internal-activity framing (bad: "managing our databases")
        internal_patterns = [r"\bour\b", r"\bmy\b", r"\bthe company'?s\b", r"\binternal\b"]
        has_internal = any(re.search(p, self.text, re.IGNORECASE) for p in internal_patterns)

        if has_internal:
            return SubsectionFinding(
                tmep_section="§1402.11",
                severity="ERROR",
                item="Internal-activity language in service identification",
                finding="Identification appears to describe the applicant's own internal activities "
                        "rather than services rendered FOR OTHERS. Services must be described "
                        "as activities performed for the benefit of third parties.",
                recommendation="Rewrite as: 'providing X services for others in the field of Y' "
                               "or 'X services rendered to others, namely...'"
            )

        if not has_service_activity:
            return SubsectionFinding(
                tmep_section="§1402.11",
                severity="WARNING",
                item="Service identification format",
                finding="Service identification does not explicitly state the activity is "
                        "rendered for others. Per §1402.11, services must be described as "
                        "activities performed for third parties.",
                recommendation="Add language such as 'providing', 'rendering', or "
                               "'offering...for others' to clarify the commercial nature."
            )

        return SubsectionFinding(
            tmep_section="§1402.11",
            severity="OK",
            item="Service activity format",
            finding="Identification correctly describes a service activity rendered for others.",
            recommendation="No action required."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ADDED — §1402.12: Parentheses/Brackets (your original detect, now mapped)
    # ─────────────────────────────────────────────────────────────────────────

    def _check_1402_12(self, structural_issues: List[str]) -> SubsectionFinding:
        """§1402.12 — Parentheses and brackets are prohibited."""
        bracket_issues = [i for i in structural_issues if "Parentheses" in i or "brackets" in i]
        if bracket_issues:
            return SubsectionFinding(
                tmep_section="§1402.12",
                severity="ERROR",
                item="Parentheses/brackets in identification",
                finding=bracket_issues[0],
                recommendation="Remove all parentheses ( ), brackets [ ], and braces { } from "
                               "the identification. Rewrite any parenthetical clarifications "
                               "as direct language."
            )
        return SubsectionFinding(
            tmep_section="§1402.12",
            severity="OK",
            item="Parentheses/brackets check",
            finding="No parentheses or brackets found.",
            recommendation="No action required."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN EVALUATE METHOD — YOUR ORIGINAL STRUCTURE + SUBSECTION INTEGRATION
    # ─────────────────────────────────────────────────────────────────────────

    def evaluate(self) -> TMEP1402AnalysisResult:
        # ── Run your original shared detectors ───────────────────────────────
        goods_segments = self.extract_candidate_goods()
        purpose_flag = self.detect_purpose_language()
        vague_found = self.detect_vague_terms()
        structural_flags = self.detect_structural_issues()

        # ── Run all per-subsection checks ─────────────────────────────────────
        findings = [
            self._check_1402_01(goods_segments),
            self._check_1402_02(goods_segments),
            self._check_1402_03(vague_found),
            self._check_1402_05(),        # ← uses Pillar 1 context
            self._check_1402_09(),
            self._check_1402_10(),        # ← uses Pillar 1 filing_basis
            self._check_1402_11(),        # ← uses Pillar 1 class_category
            self._check_1402_12(structural_flags),
        ]

        # ── CHANGED: is_definite now weighted, not all-or-nothing ────────────
        error_count = sum(1 for f in findings if f.severity == "ERROR")
        warning_count = sum(1 for f in findings if f.severity == "WARNING")
        is_definite = (error_count == 0)   # Only hard errors block definiteness

        # ── Build reasoning (your original structure, now using subsection findings) ──
        reasoning_parts = []
        if is_definite and warning_count == 0:
            reasoning_parts.append(
                "The identification appears to list particular goods/services "
                "with sufficient specificity under TMEP §1402."
            )
        elif is_definite and warning_count > 0:
            reasoning_parts.append(
                "The identification meets minimum §1402 standards but has "
                f"{warning_count} warning(s) that should be addressed."
            )
        else:
            reasoning_parts.append(
                "The identification does not sufficiently identify particular goods/services "
                f"as required by TMEP §1402. {error_count} error(s) must be corrected."
            )

        if vague_found:
            reasoning_parts.append(f"Vague terminology: {', '.join(vague_found)}.")
        if not purpose_flag:
            reasoning_parts.append(
                "No explicit commercial purpose qualifier detected "
                "(may be required depending on class)."
            )
        if structural_flags:
            reasoning_parts.extend(structural_flags)

        # ── Pillar 1 dependency note ──────────────────────────────────────────
        p1_note = ""
        if self.p1:
            p1_note = (
                f"Assessed in context of Class {self.p1.class_number} "
                f"({self.p1.class_title}) [{self.p1.class_category}] "
                f"as determined by Pillar 1. "
                f"Filing basis: {self.p1.filing_basis}. "
            )
            if self.p1.has_pillar1_class_error:
                p1_note += (
                    "⚠️ Pillar 1 flagged a classification ERROR — some Pillar 2 "
                    "checks are deferred until class is corrected."
                )
        else:
            p1_note = "No Pillar 1 context — standalone assessment only."

        return TMEP1402AnalysisResult(
            is_definite=is_definite,
            identified_goods_services=goods_segments,
            purpose_detected=purpose_flag,
            vague_terms_found=vague_found,
            structural_issues=structural_flags,
            reasoning=" ".join(reasoning_parts),
            subsection_findings=findings,
            pillar1_dependency_note=p1_note
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — UNCHANGED SIGNATURE + OVERLOAD WITH PILLAR 1 CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_identification_under_tmep_1402(identification_text: str,
                                            pillar1_context: Optional[Pillar1ClassContext] = None
                                            ) -> Dict:
    """
    End-to-end pipeline for TMEP §1402 evaluation.

    BACKWARD COMPATIBLE — can still be called with just identification_text.
    Add pillar1_context for full cross-pillar assessment.

    Args:
        identification_text: The exact identification as filed
        pillar1_context: Optional. Pass a Pillar1ClassContext built from
                         Pillar 1 results for specimen accuracy, filing basis,
                         and class category checks.

    Returns:
        dict with:
            - verbatim_text
            - tmep_1402_analysis (full TMEP1402AnalysisResult as dict)
            - summary (counts by severity)
    """
    record = IdentificationRecord(original_text=identification_text)
    verbatim = record.get_verbatim()

    lens = TMEP1402Lens(verbatim, pillar1_context=pillar1_context)
    result = lens.evaluate()

    analysis_dict = asdict(result)
    summary = {
        "total_findings": len(result.subsection_findings),
        "errors": sum(1 for f in result.subsection_findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in result.subsection_findings if f.severity == "WARNING"),
        "info": sum(1 for f in result.subsection_findings if f.severity == "INFO"),
        "ok": sum(1 for f in result.subsection_findings if f.severity == "OK"),
        "is_definite": result.is_definite,
    }

    return {
        "verbatim_text": verbatim,
        "tmep_1402_analysis": analysis_dict,
        "summary": summary
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT PRINTER — ADDED for readable output
# ═══════════════════════════════════════════════════════════════════════════════

def print_pillar2_report(result_dict: Dict, class_number: int = 0):
    """Professional legal report — Pillar 2 identification assessment."""
    _SEV = {"ERROR": "■", "WARNING": "▲", "INFO": "◆", "OK": "✓"}

    def _trim(t, n=110):
        t = str(t).replace("\n", " ").strip()
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"

    analysis = result_dict["tmep_1402_analysis"]
    summary  = result_dict["summary"]
    label    = f"Class {class_number}" if class_number else "Identification"
    status   = "DEFINITE" if summary["is_definite"] else "NOT DEFINITE — REQUIRES AMENDMENT"

    line = "─" * 70
    print(f"\n{line}")
    print(f"  IDENTIFICATION REVIEW  |  {label}  |  §1402")
    print(f"  Status: {status}")

    # Surface only actionable findings — skip OK and pure INFO
    issues = [f for f in analysis.get("subsection_findings", [])
              if f["severity"] in ("ERROR", "WARNING")]

    if issues:
        print(f"\n  Issues Identified:")
        for f in issues:
            sym = _SEV.get(f["severity"], "?")
            print(f"  {sym} [{f['tmep_section']}]  {_trim(f['finding'])}")
            print(f"      → {_trim(f['recommendation'])}")
    else:
        print(f"\n  No identification issues detected.")

    # Show P1 context note only if it contains a meaningful warning
    p1_note = analysis.get("pillar1_dependency_note", "")
    if "ERROR" in p1_note or "⚠" in p1_note:
        print(f"\n  Note:  {_trim(p1_note, 120)}")

    print(line)


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK TEST — Shows standalone and with Pillar 1 context
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ── Test 1: Your original example — STANDALONE (no Pillar 1) ─────────────
    print("\n--- TEST 1: Standalone (your original example) ---")
    result = analyze_identification_under_tmep_1402(
        "Computer software (downloadable) for managing databases; "
        "Clothing, namely, shirts, pants, and shoes; and related tech."
    )
    print_pillar2_report(result)

    # ── Test 2: With Pillar 1 context — §1(b) intent-to-use ──────────────────
    print("\n--- TEST 2: With Pillar 1 context (§1(b) intent-to-use) ---")
    ctx = Pillar1ClassContext(
        class_number=42,
        class_title="Scientific and Technology Services",
        class_category="SERVICES",
        filing_basis="1(b)",
        specimen_type="",
        specimen_description="",
        has_pillar1_class_error=False,
        has_pillar1_class_warning=False
    )
    result2 = analyze_identification_under_tmep_1402(
        "Software as a service featuring artificial intelligence tools; "
        "cloud computing services for others in the field of data analytics",
        pillar1_context=ctx
    )
    print_pillar2_report(result2, class_number=42)

    # ── Test 3: Misclassification from Pillar 1 defers accuracy check ─────────
    print("\n--- TEST 3: Pillar 1 class ERROR defers accuracy check ---")
    ctx_error = Pillar1ClassContext(
        class_number=25,
        class_title="Clothing and Footwear",
        class_category="GOODS",
        filing_basis="1(a)",
        specimen_type="product label",
        specimen_description="product label on clothing",
        has_pillar1_class_error=True,
        pillar1_error_summary="Software placed in Class 25 (clothing) — misclassification"
    )
    result3 = analyze_identification_under_tmep_1402(
        "Software for inventory management; computer programs for retail management",
        pillar1_context=ctx_error
    )
    print_pillar2_report(result3, class_number=25)

    # ── Test 4: Services without 'for others' language ────────────────────────
    print("\n--- TEST 4: Services identification missing 'for others' ---")
    ctx_svc = Pillar1ClassContext(
        class_number=41,
        class_title="Education and Entertainment Services",
        class_category="SERVICES",
        filing_basis="1(a)",
        specimen_type="website screenshot",
        specimen_description="screenshot of online education platform"
    )
    result4 = analyze_identification_under_tmep_1402(
        "Educational training programs; entertainment events including concerts and shows",
        pillar1_context=ctx_svc
    )
    print_pillar2_report(result4, class_number=41)











# """
# TMEP CHAPTER 1402 — IDENTIFICATION OF GOODS AND SERVICES
# PILLAR 2 ASSESSMENT ENGINE
# ==========================================================
# Based on: TMEP November 2025 Edition

# PILLAR FLOW:
#     Pillar 1 Output (ClassEntry + AssessmentFinding list)
#          ↓
#     Pillar 2 — Identification Assessment (this file)
#          ↓
#     Pillar 3 — Multi-Class Filing Requirements

# HOW PILLAR 1 FEEDS PILLAR 2:
#     - Pillar 1 confirms/corrects the class number → Pillar 2 uses confirmed class
#       to validate whether the identification is appropriate for that class
#     - Pillar 1 detects specimen type → Pillar 2 §1402.05 uses it to check
#       accuracy of identification against what specimen actually shows
#     - Pillar 1 flags misclassified items → Pillar 2 skips accuracy checks
#       on those items (no point validating wording in wrong class)
#     - Pillar 1 filing basis (1(a) vs 1(b)) → Pillar 2 §1402.10 applies
#       different rules for intent-to-use applications
# """

# import re
# from dataclasses import dataclass, asdict, field
# from typing import List, Dict, Optional


# # ═══════════════════════════════════════════════════════════════════════════════
# # ─── UNCHANGED FROM YOUR ORIGINAL — KEPT VERBATIM ───────────────────────────
# # ═══════════════════════════════════════════════════════════════════════════════

# @dataclass
# class IdentificationRecord:
#     """
#     Stores applicant's identification EXACTLY as submitted.
#     No normalization, no trimming, no case modification.
#     """
#     original_text: str

#     def get_verbatim(self) -> str:
#         """Returns the exact wording as filed."""
#         return self.original_text


# # ═══════════════════════════════════════════════════════════════════════════════
# # ─── ADDED: PILLAR 1 CONTEXT BRIDGE ─────────────────────────────────────────
# # Lightweight container to carry Pillar 1 results into Pillar 2.
# # You don't need to import the full Pillar 1 module — just pass these fields.
# # ═══════════════════════════════════════════════════════════════════════════════

# @dataclass
# class Pillar1ClassContext:
#     """
#     Carries the relevant Pillar 1 findings for a single class entry
#     into the Pillar 2 assessment.

#     Populate this from your Pillar 1 ClassEntry + AssessmentFinding objects.
#     """
#     class_number: int                    # Confirmed (or suspected) class from Pillar 1
#     class_title: str                     # e.g., "Scientific and Electronic Apparatus"
#     class_category: str                  # "GOODS" or "SERVICES"
#     filing_basis: str                    # "1(a)", "1(b)", "44(d)", etc.
#     specimen_type: str = ""             # From Pillar 1 ClassEntry
#     specimen_description: str = ""     # From Pillar 1 ClassEntry
#     has_pillar1_class_error: bool = False   # True if Pillar 1 flagged a misclassification ERROR
#     has_pillar1_class_warning: bool = False # True if Pillar 1 flagged a class WARNING
#     pillar1_error_summary: str = ""    # Brief summary of Pillar 1 errors for this class


# def build_pillar1_context_from_dicts(class_entry_dict: dict,
#                                       pillar1_findings: list) -> "Pillar1ClassContext":
#     """
#     Helper to build Pillar1ClassContext from raw dicts (when not using full Pillar 1 objects).
    
#     Args:
#         class_entry_dict: A dict with keys: class_number, identification, specimen_type,
#                           specimen_description, filing_basis
#         pillar1_findings: List of AssessmentFinding dicts (or objects with .severity,
#                           .class_number, .finding attributes) from Pillar 1
    
#     Example:
#         ctx = build_pillar1_context_from_dicts(
#             {"class_number": 9, "filing_basis": "1(a)", "specimen_type": "website screenshot", ...},
#             pillar1_result["findings"]
#         )
#     """
#     cls_num = int(class_entry_dict.get("class_number", 0))

#     # Pull relevant findings for this class from Pillar 1
#     class_findings = []
#     for f in pillar1_findings:
#         # Support both dict and object
#         fn = f if isinstance(f, dict) else f.__dict__
#         if fn.get("class_number", -1) == cls_num or fn.get("class_number", -1) == 0:
#             class_findings.append(fn)

#     errors = [f for f in class_findings if f.get("severity") == "ERROR"]
#     warnings = [f for f in class_findings if f.get("severity") == "WARNING"]
#     error_summary = "; ".join(e.get("finding", "")[:80] for e in errors[:2]) if errors else ""

#     # Try to get class info if nice_classification_db is available
#     class_title = ""
#     class_category = ""
#     try:
#         from nice_classification_db import get_class_info
#         info = get_class_info(cls_num)
#         if info:
#             class_title = info["title"]
#             class_category = info["category"]
#     except ImportError:
#         pass

#     return Pillar1ClassContext(
#         class_number=cls_num,
#         class_title=class_title,
#         class_category=class_category,
#         filing_basis=class_entry_dict.get("filing_basis", "1(a)"),
#         specimen_type=class_entry_dict.get("specimen_type", ""),
#         specimen_description=class_entry_dict.get("specimen_description", ""),
#         has_pillar1_class_error=len(errors) > 0,
#         has_pillar1_class_warning=len(warnings) > 0,
#         pillar1_error_summary=error_summary
#     )


# # ═══════════════════════════════════════════════════════════════════════════════
# # ─── RESULT MODEL — EXPANDED FROM YOUR ORIGINAL ──────────────────────────────
# # Added: per-subsection findings list so each check is traceable
# # ═══════════════════════════════════════════════════════════════════════════════

# @dataclass
# class SubsectionFinding:
#     """A single finding tied to a specific TMEP §1402.xx sub-section."""
#     tmep_section: str     # e.g., "§1402.03"
#     severity: str         # "ERROR", "WARNING", "INFO", "OK"
#     item: str             # What was checked
#     finding: str          # What was found
#     recommendation: str   # What to do


# @dataclass
# class TMEP1402AnalysisResult:
#     # ── Your original fields — UNCHANGED ─────────────────────────────────────
#     is_definite: bool
#     identified_goods_services: List[str]
#     purpose_detected: bool
#     vague_terms_found: List[str]
#     structural_issues: List[str]
#     reasoning: str
#     # ── ADDED: Per-subsection breakdown ──────────────────────────────────────
#     subsection_findings: List[SubsectionFinding] = field(default_factory=list)
#     pillar1_dependency_note: str = ""  # Notes how Pillar 1 results affected this assessment


# # ═══════════════════════════════════════════════════════════════════════════════
# # TMEP §1402 LENS ENGINE — IMPROVED
# # ═══════════════════════════════════════════════════════════════════════════════

# class TMEP1402Lens:
#     """
#     Applies the controlling questions under TMEP §1402:
#     Does the wording clearly identify particular goods/services
#     and their commercial purpose in sufficiently definite terms?

#     CHANGED from original:
#     - Accepts optional Pillar1ClassContext for cross-pillar validation
#     - Each check now maps to a specific §1402.xx sub-section
#     - is_definite logic is more nuanced (weighted, not all-or-nothing)
#     - Added §1402.05, §1402.09, §1402.10, §1402.11 checks
#     """

#     # ── UNCHANGED from your original ─────────────────────────────────────────
#     VAGUE_TERMS = [
#         "including",
#         "and related",
#         "etc",
#         "etc.",
#         "products",
#         "services",           # vague ONLY when used alone (see _check_1402_03)
#         "solutions",
#         "technology",
#         "equipment",
#         "devices",
#         "materials",
#         "systems",
#         "components",
#         "platform",
#         # ADDED — additional indefinite terms per USPTO practice
#         "miscellaneous",
#         "various",
#         "all types",
#         "any",
#         "type of",
#         "kind of",
#         "and the like",
#         "other",              # as a standalone catch-all
#     ]

#     PURPOSE_PATTERNS = [
#         r"\bfor\b",
#         r"\bnamely\b",
#         r"\bconsisting of\b",
#         r"\bin the field of\b",
#         r"\bused for\b"
#     ]

#     # ADDED — Terms banned per §1402.09
#     BANNED_TERMS_1402_09 = ["applicant", "registrant"]

#     # ADDED — Service identification must describe activity rendered FOR others
#     SERVICE_ACTIVITY_PATTERNS = [
#         r"\bservices for\b",
#         r"\bservices in the (nature|field)\b",
#         r"\bproviding\b",
#         r"\brendering\b",
#         r"\boffering\b",
#         r"\bconsulting\b",
#     ]

#     def __init__(self, identification_text: str,
#                  pillar1_context: Optional[Pillar1ClassContext] = None):
#         self.text = identification_text
#         self.p1 = pillar1_context   # None if running standalone without Pillar 1

#     # ─────────────────────────────────────────────────────────────────────────
#     # UNCHANGED from your original
#     # ─────────────────────────────────────────────────────────────────────────

#     def extract_candidate_goods(self) -> List[str]:
#         """
#         Extracts potential goods/services by splitting on semicolons.
#         TMEP §1402.01: Semicolons separate distinct categories.
#         """
#         segments = re.split(r";", self.text)
#         cleaned = [seg.strip() for seg in segments if seg.strip()]
#         return cleaned

#     def detect_purpose_language(self) -> bool:
#         """Detects whether the ID specifies purpose qualifiers."""
#         for pattern in self.PURPOSE_PATTERNS:
#             if re.search(pattern, self.text, re.IGNORECASE):
#                 return True
#         return False

#     def detect_vague_terms(self) -> List[str]:
#         """Flags indefinite or catch-all terminology."""
#         found = []
#         for term in self.VAGUE_TERMS:
#             pattern = rf"\b{re.escape(term)}(?:\b|\.|\s|$)"
#             if re.search(pattern, self.text, re.IGNORECASE) and term not in found:
#                 # CHANGED: "services" alone is vague; "services for X" is not
#                 if term == "services":
#                     if not re.search(r"\bservices\s+(for|in|of|namely|consisting)\b",
#                                      self.text, re.IGNORECASE):
#                         found.append(term)
#                 else:
#                     found.append(term)
#         return found

#     def detect_structural_issues(self) -> List[str]:
#         """
#         Flags structural issues — UNCHANGED from your original.
#         """
#         issues = []
#         and_count = len(re.findall(r"\band\b", self.text, re.IGNORECASE))
#         if and_count > 3:
#             issues.append("Excessive conjunction stacking ('and') may indicate over-breadth.")
#         if re.search(r"[\(\)\[\]\{\}]", self.text):
#             issues.append("Parentheses or brackets detected. Prohibited under TMEP §1402.12.")
#         return issues

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.01: General specificity check
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_01(self, segments: List[str]) -> SubsectionFinding:
#         """§1402.01 — Identification must list particular goods/services."""
#         if not segments:
#             return SubsectionFinding(
#                 tmep_section="§1402.01",
#                 severity="ERROR",
#                 item="Identification text",
#                 finding="Identification is empty or cannot be parsed into distinct goods/services.",
#                 recommendation="Provide a clear, itemized list of goods/services separated by semicolons."
#             )
#         return SubsectionFinding(
#             tmep_section="§1402.01",
#             severity="OK",
#             item=f"{len(segments)} item(s) identified",
#             finding=f"Identification contains {len(segments)} item(s): "
#                     f"{'; '.join(s[:40] for s in segments[:3])}{'...' if len(segments)>3 else ''}",
#             recommendation="No action required."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.02: Filing date entitlement
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_02(self, segments: List[str]) -> SubsectionFinding:
#         """
#         §1402.02 — Identification must be complete enough at filing to
#         secure the filing date. Completely blank or placeholder text fails.
#         """
#         placeholders = ["tbd", "to be determined", "see attached", "n/a",
#                         "[insert]", "xxx", "your goods here"]
#         text_lower = self.text.lower().strip()

#         if any(p in text_lower for p in placeholders):
#             return SubsectionFinding(
#                 tmep_section="§1402.02",
#                 severity="ERROR",
#                 item="Placeholder text detected",
#                 finding="Identification contains placeholder or incomplete text. "
#                         "Application will not be entitled to its filing date.",
#                 recommendation="Replace placeholder text with a complete, definite identification "
#                                "of actual goods/services."
#             )
#         if len(text_lower) < 10:
#             return SubsectionFinding(
#                 tmep_section="§1402.02",
#                 severity="ERROR",
#                 item="Identification too short",
#                 finding="Identification is too brief to secure a filing date.",
#                 recommendation="Provide a complete identification of goods/services."
#             )
#         return SubsectionFinding(
#             tmep_section="§1402.02",
#             severity="OK",
#             item="Filing date entitlement",
#             finding="Identification appears complete enough to support filing date entitlement.",
#             recommendation="No action required."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.03: Specificity of terms (uses your original vague detection)
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_03(self, vague_found: List[str]) -> SubsectionFinding:
#         """
#         §1402.03 — Terms must be specific enough. Vague or indefinite terms
#         are unacceptable. CHANGED: severity is weighted — standalone vague
#         terms are WARNING; structural vague terms are ERROR.
#         """
#         severe_vague = [t for t in vague_found
#                         if t in ["miscellaneous", "various", "all types", "any",
#                                  "and the like", "etc", "etc."]]
#         mild_vague = [t for t in vague_found if t not in severe_vague]

#         if severe_vague:
#             return SubsectionFinding(
#                 tmep_section="§1402.03",
#                 severity="ERROR",
#                 item=f"Indefinite terms: {', '.join(severe_vague)}",
#                 finding=f"Severely indefinite terms found: {', '.join(severe_vague)}. "
#                         "These are categorically unacceptable under USPTO practice.",
#                 recommendation="Remove all indefinite terms. Replace with specific, "
#                                "enumerated goods/services."
#             )
#         if mild_vague:
#             return SubsectionFinding(
#                 tmep_section="§1402.03",
#                 severity="WARNING",
#                 item=f"Potentially vague terms: {', '.join(mild_vague)}",
#                 finding=f"Possibly indefinite terms found: {', '.join(mild_vague)}. "
#                         "These may be acceptable with additional specificity.",
#                 recommendation=f"Review terms: {', '.join(mild_vague)}. "
#                                "Add 'namely' clauses to specify exact goods/services."
#             )
#         return SubsectionFinding(
#             tmep_section="§1402.03",
#             severity="OK",
#             item="Specificity check",
#             finding="No indefinite terms detected. Identification appears sufficiently specific.",
#             recommendation="No action required."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.05: Accuracy — cross-checked against Pillar 1 specimen
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_05(self) -> SubsectionFinding:
#         """
#         §1402.05 — Identification must accurately reflect what the applicant
#         actually offers, as evidenced by the specimen (from Pillar 1).

#         KEY PILLAR 1 INTEGRATION POINT:
#         Pillar 1 gives us the specimen_description. Here we check whether
#         the identification text is consistent with what the specimen shows.
#         """
#         if not self.p1:
#             return SubsectionFinding(
#                 tmep_section="§1402.05",
#                 severity="INFO",
#                 item="Accuracy check (no Pillar 1 context)",
#                 finding="No Pillar 1 context provided. Cannot cross-check identification "
#                         "accuracy against specimen.",
#                 recommendation="Run with Pillar 1 context for full §1402.05 accuracy check."
#             )

#         # If Pillar 1 already flagged a class ERROR, accuracy check is secondary
#         if self.p1.has_pillar1_class_error:
#             return SubsectionFinding(
#                 tmep_section="§1402.05",
#                 severity="WARNING",
#                 item=f"Class {self.p1.class_number} — Accuracy deferred",
#                 finding="Pillar 1 detected a classification ERROR for this class. "
#                         "Accuracy of identification cannot be confirmed until the class "
#                         f"is corrected. Pillar 1 issue: {self.p1.pillar1_error_summary[:100]}",
#                 recommendation="Resolve Pillar 1 classification errors first, then "
#                                "re-assess identification accuracy in the correct class."
#             )

#         # Intent-to-use: no specimen yet, different accuracy standard
#         if self.p1.filing_basis == "1(b)":
#             return SubsectionFinding(
#                 tmep_section="§1402.05",
#                 severity="INFO",
#                 item=f"Class {self.p1.class_number} — §1(b) accuracy standard",
#                 finding="Intent-to-use application (§1(b)). Identification must accurately "
#                         "reflect goods/services applicant has a bona fide intention to use. "
#                         "Specimen not yet required — accuracy will be verified at SOU stage.",
#                 recommendation="Ensure identification reflects actual intended use. "
#                                "Overly broad identifications may cause problems at SOU stage."
#             )

#         # Cross-check identification text against specimen description
#         id_lower = self.text.lower()
#         spec_lower = self.p1.specimen_description.lower()

#         if not spec_lower:
#             return SubsectionFinding(
#                 tmep_section="§1402.05",
#                 severity="INFO",
#                 item="No specimen description from Pillar 1",
#                 finding="Specimen description not available for accuracy cross-check.",
#                 recommendation="Provide specimen description in Pillar 1 class entry for full check."
#             )

#         # Look for obvious mismatches: words in specimen not in identification
#         id_words = set(re.findall(r"\b\w{4,}\b", id_lower))
#         spec_words = set(re.findall(r"\b\w{4,}\b", spec_lower))
#         overlap = id_words & spec_words
#         overlap_ratio = len(overlap) / max(len(spec_words), 1)

#         if overlap_ratio < 0.1 and len(spec_words) > 3:
#             return SubsectionFinding(
#                 tmep_section="§1402.05",
#                 severity="WARNING",
#                 item="Low overlap between identification and specimen",
#                 finding=f"Low conceptual overlap between identification and specimen description "
#                         f"(~{int(overlap_ratio*100)}% word overlap). "
#                         "Identification may not accurately reflect the actual goods/services "
#                         "shown in the specimen.",
#                 recommendation="Review whether identification accurately describes what the "
#                                "specimen actually shows. Amend if over-broad or misaligned."
#             )

#         return SubsectionFinding(
#             tmep_section="§1402.05",
#             severity="OK",
#             item="Accuracy vs. specimen",
#             finding=f"Identification appears consistent with the specimen provided "
#                     f"(~{int(overlap_ratio*100)}% conceptual overlap).",
#             recommendation="No action required."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.09: Banned terms "Applicant" / "Registrant"
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_09(self) -> SubsectionFinding:
#         """
#         §1402.09 — The terms "applicant" and "registrant" must not appear
#         in the identification of goods or services.
#         """
#         found_banned = []
#         for term in self.BANNED_TERMS_1402_09:
#             if re.search(rf"\b{term}\b", self.text, re.IGNORECASE):
#                 found_banned.append(term)

#         if found_banned:
#             return SubsectionFinding(
#                 tmep_section="§1402.09",
#                 severity="ERROR",
#                 item=f"Banned terms found: {', '.join(found_banned)}",
#                 finding=f"The term(s) '{', '.join(found_banned)}' appear in the identification. "
#                         "Per §1402.09, 'applicant' and 'registrant' are inappropriate "
#                         "in identifications of goods and services.",
#                 recommendation=f"Remove '{', '.join(found_banned)}' from the identification. "
#                                "Rewrite the relevant clause without reference to the applicant/registrant."
#             )
#         return SubsectionFinding(
#             tmep_section="§1402.09",
#             severity="OK",
#             item="Banned terms check",
#             finding="No prohibited terms ('applicant', 'registrant') found.",
#             recommendation="No action required."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.10: §1(b) intent-to-use specific requirements
#     # KEY PILLAR 1 INTEGRATION: filing_basis comes from Pillar 1 ClassEntry
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_10(self) -> SubsectionFinding:
#         """
#         §1402.10 — For §1(b) intent-to-use applications, the identification
#         must still be complete and definite at filing (same standard as §1(a)).
        
#         Uses filing_basis from Pillar 1 context.
#         """
#         basis = self.p1.filing_basis if self.p1 else "1(a)"

#         if basis != "1(b)":
#             return SubsectionFinding(
#                 tmep_section="§1402.10",
#                 severity="INFO",
#                 item=f"Filing basis: {basis}",
#                 finding=f"Application is filed under {basis}, not §1(b). "
#                         "§1402.10 intent-to-use requirements do not apply.",
#                 recommendation="No action required."
#             )

#         # For §1(b): check for future-tense or speculative wording
#         future_tense_patterns = [
#             r"\bwill\b", r"\bintend\b", r"\bplanning to\b",
#             r"\bproposed\b", r"\bfuture\b"
#         ]
#         found_future = [p.strip(r"\b") for p in future_tense_patterns
#                        if re.search(p, self.text, re.IGNORECASE)]

#         if found_future:
#             return SubsectionFinding(
#                 tmep_section="§1402.10",
#                 severity="WARNING",
#                 item="Future-tense language in §1(b) identification",
#                 finding="Identification contains future-tense or speculative language "
#                         f"({', '.join(found_future)}). Even for §1(b) applications, "
#                         "the identification must describe goods/services definitively, "
#                         "not contingently.",
#                 recommendation="Remove future-tense wording. State goods/services definitively "
#                                "as if already in use (the filing basis covers the intent — "
#                                "the identification does not need to reflect it)."
#             )

#         return SubsectionFinding(
#             tmep_section="§1402.10",
#             severity="OK",
#             item="§1(b) identification format",
#             finding="§1(b) identification is stated definitively without future-tense language.",
#             recommendation="No action required. Remember: specimen must be filed with SOU."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.11: Services must be described as activities for others
#     # KEY PILLAR 1 INTEGRATION: class_category from Pillar 1 ClassEntry
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_11(self) -> SubsectionFinding:
#         """
#         §1402.11 — Services must be identified as activities performed FOR OTHERS,
#         not as internal activities of the applicant.
        
#         Uses class_category from Pillar 1 context to determine if this applies.
#         """
#         # Determine if this is a services class
#         is_services = False
#         if self.p1:
#             is_services = (self.p1.class_category == "SERVICES")
#         else:
#             # Fallback: detect service language if no Pillar 1 context
#             is_services = bool(re.search(r"\bservice[s]?\b", self.text, re.IGNORECASE))

#         if not is_services:
#             return SubsectionFinding(
#                 tmep_section="§1402.11",
#                 severity="INFO",
#                 item="§1402.11 services check",
#                 finding="This appears to be a goods class. §1402.11 services format "
#                         "requirement does not apply.",
#                 recommendation="No action required."
#             )

#         # Check for service activity language
#         has_service_activity = any(
#             re.search(p, self.text, re.IGNORECASE)
#             for p in self.SERVICE_ACTIVITY_PATTERNS
#         )

#         # Check for internal-activity framing (bad: "managing our databases")
#         internal_patterns = [r"\bour\b", r"\bmy\b", r"\bthe company'?s\b", r"\binternal\b"]
#         has_internal = any(re.search(p, self.text, re.IGNORECASE) for p in internal_patterns)

#         if has_internal:
#             return SubsectionFinding(
#                 tmep_section="§1402.11",
#                 severity="ERROR",
#                 item="Internal-activity language in service identification",
#                 finding="Identification appears to describe the applicant's own internal activities "
#                         "rather than services rendered FOR OTHERS. Services must be described "
#                         "as activities performed for the benefit of third parties.",
#                 recommendation="Rewrite as: 'providing X services for others in the field of Y' "
#                                "or 'X services rendered to others, namely...'"
#             )

#         if not has_service_activity:
#             return SubsectionFinding(
#                 tmep_section="§1402.11",
#                 severity="WARNING",
#                 item="Service identification format",
#                 finding="Service identification does not explicitly state the activity is "
#                         "rendered for others. Per §1402.11, services must be described as "
#                         "activities performed for third parties.",
#                 recommendation="Add language such as 'providing', 'rendering', or "
#                                "'offering...for others' to clarify the commercial nature."
#             )

#         return SubsectionFinding(
#             tmep_section="§1402.11",
#             severity="OK",
#             item="Service activity format",
#             finding="Identification correctly describes a service activity rendered for others.",
#             recommendation="No action required."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ADDED — §1402.12: Parentheses/Brackets (your original detect, now mapped)
#     # ─────────────────────────────────────────────────────────────────────────

#     def _check_1402_12(self, structural_issues: List[str]) -> SubsectionFinding:
#         """§1402.12 — Parentheses and brackets are prohibited."""
#         bracket_issues = [i for i in structural_issues if "Parentheses" in i or "brackets" in i]
#         if bracket_issues:
#             return SubsectionFinding(
#                 tmep_section="§1402.12",
#                 severity="ERROR",
#                 item="Parentheses/brackets in identification",
#                 finding=bracket_issues[0],
#                 recommendation="Remove all parentheses ( ), brackets [ ], and braces { } from "
#                                "the identification. Rewrite any parenthetical clarifications "
#                                "as direct language."
#             )
#         return SubsectionFinding(
#             tmep_section="§1402.12",
#             severity="OK",
#             item="Parentheses/brackets check",
#             finding="No parentheses or brackets found.",
#             recommendation="No action required."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # MAIN EVALUATE METHOD — YOUR ORIGINAL STRUCTURE + SUBSECTION INTEGRATION
#     # ─────────────────────────────────────────────────────────────────────────

#     def evaluate(self) -> TMEP1402AnalysisResult:
#         # ── Run your original shared detectors ───────────────────────────────
#         goods_segments = self.extract_candidate_goods()
#         purpose_flag = self.detect_purpose_language()
#         vague_found = self.detect_vague_terms()
#         structural_flags = self.detect_structural_issues()

#         # ── Run all per-subsection checks ─────────────────────────────────────
#         findings = [
#             self._check_1402_01(goods_segments),
#             self._check_1402_02(goods_segments),
#             self._check_1402_03(vague_found),
#             self._check_1402_05(),        # ← uses Pillar 1 context
#             self._check_1402_09(),
#             self._check_1402_10(),        # ← uses Pillar 1 filing_basis
#             self._check_1402_11(),        # ← uses Pillar 1 class_category
#             self._check_1402_12(structural_flags),
#         ]

#         # ── CHANGED: is_definite now weighted, not all-or-nothing ────────────
#         error_count = sum(1 for f in findings if f.severity == "ERROR")
#         warning_count = sum(1 for f in findings if f.severity == "WARNING")
#         is_definite = (error_count == 0)   # Only hard errors block definiteness

#         # ── Build reasoning (your original structure, now using subsection findings) ──
#         reasoning_parts = []
#         if is_definite and warning_count == 0:
#             reasoning_parts.append(
#                 "The identification appears to list particular goods/services "
#                 "with sufficient specificity under TMEP §1402."
#             )
#         elif is_definite and warning_count > 0:
#             reasoning_parts.append(
#                 "The identification meets minimum §1402 standards but has "
#                 f"{warning_count} warning(s) that should be addressed."
#             )
#         else:
#             reasoning_parts.append(
#                 "The identification does not sufficiently identify particular goods/services "
#                 f"as required by TMEP §1402. {error_count} error(s) must be corrected."
#             )

#         if vague_found:
#             reasoning_parts.append(f"Vague terminology: {', '.join(vague_found)}.")
#         if not purpose_flag:
#             reasoning_parts.append(
#                 "No explicit commercial purpose qualifier detected "
#                 "(may be required depending on class)."
#             )
#         if structural_flags:
#             reasoning_parts.extend(structural_flags)

#         # ── Pillar 1 dependency note ──────────────────────────────────────────
#         p1_note = ""
#         if self.p1:
#             p1_note = (
#                 f"Assessed in context of Class {self.p1.class_number} "
#                 f"({self.p1.class_title}) [{self.p1.class_category}] "
#                 f"as determined by Pillar 1. "
#                 f"Filing basis: {self.p1.filing_basis}. "
#             )
#             if self.p1.has_pillar1_class_error:
#                 p1_note += (
#                     "⚠️ Pillar 1 flagged a classification ERROR — some Pillar 2 "
#                     "checks are deferred until class is corrected."
#                 )
#         else:
#             p1_note = "No Pillar 1 context — standalone assessment only."

#         return TMEP1402AnalysisResult(
#             is_definite=is_definite,
#             identified_goods_services=goods_segments,
#             purpose_detected=purpose_flag,
#             vague_terms_found=vague_found,
#             structural_issues=structural_flags,
#             reasoning=" ".join(reasoning_parts),
#             subsection_findings=findings,
#             pillar1_dependency_note=p1_note
#         )


# # ═══════════════════════════════════════════════════════════════════════════════
# # PUBLIC API — UNCHANGED SIGNATURE + OVERLOAD WITH PILLAR 1 CONTEXT
# # ═══════════════════════════════════════════════════════════════════════════════

# def analyze_identification_under_tmep_1402(identification_text: str,
#                                             pillar1_context: Optional[Pillar1ClassContext] = None
#                                             ) -> Dict:
#     """
#     End-to-end pipeline for TMEP §1402 evaluation.

#     BACKWARD COMPATIBLE — can still be called with just identification_text.
#     Add pillar1_context for full cross-pillar assessment.

#     Args:
#         identification_text: The exact identification as filed
#         pillar1_context: Optional. Pass a Pillar1ClassContext built from
#                          Pillar 1 results for specimen accuracy, filing basis,
#                          and class category checks.

#     Returns:
#         dict with:
#             - verbatim_text
#             - tmep_1402_analysis (full TMEP1402AnalysisResult as dict)
#             - summary (counts by severity)
#     """
#     record = IdentificationRecord(original_text=identification_text)
#     verbatim = record.get_verbatim()

#     lens = TMEP1402Lens(verbatim, pillar1_context=pillar1_context)
#     result = lens.evaluate()

#     analysis_dict = asdict(result)
#     summary = {
#         "total_findings": len(result.subsection_findings),
#         "errors": sum(1 for f in result.subsection_findings if f.severity == "ERROR"),
#         "warnings": sum(1 for f in result.subsection_findings if f.severity == "WARNING"),
#         "info": sum(1 for f in result.subsection_findings if f.severity == "INFO"),
#         "ok": sum(1 for f in result.subsection_findings if f.severity == "OK"),
#         "is_definite": result.is_definite,
#     }

#     return {
#         "verbatim_text": verbatim,
#         "tmep_1402_analysis": analysis_dict,
#         "summary": summary
#     }


# # ═══════════════════════════════════════════════════════════════════════════════
# # REPORT PRINTER — ADDED for readable output
# # ═══════════════════════════════════════════════════════════════════════════════

# def print_pillar2_report(result_dict: Dict, class_number: int = 0):
#     """Prints a human-readable Pillar 2 report from the analyze function output."""
#     SEVERITY_SYMBOLS = {"ERROR": "🔴 ERROR", "WARNING": "🟡 WARNING",
#                         "INFO": "🔵 INFO",  "OK": "✅ OK"}
#     border = "═" * 80
#     print(f"\n{border}")
#     label = f"Class {class_number}" if class_number else "Standalone"
#     print(f"  TMEP §1402 — IDENTIFICATION ASSESSMENT [{label}]")
#     print(border)
#     print(f"  Verbatim Text : {result_dict['verbatim_text'][:100]}{'...' if len(result_dict['verbatim_text'])>100 else ''}")

#     analysis = result_dict["tmep_1402_analysis"]
#     summary = result_dict["summary"]

#     print(f"\n  Overall       : {'✅ DEFINITE' if summary['is_definite'] else '🔴 NOT DEFINITE'}")
#     print(f"  Errors        : {summary['errors']}  |  Warnings: {summary['warnings']}  "
#           f"|  OK: {summary['ok']}")
#     print(f"\n  Pillar 1 Note : {analysis.get('pillar1_dependency_note', 'N/A')}")
#     print(f"\n  Reasoning     : {analysis['reasoning']}")

#     print(f"\n{'─'*80}")
#     print("  FINDINGS BY SUBSECTION:")
#     for f in analysis.get("subsection_findings", []):
#         sym = SEVERITY_SYMBOLS.get(f["severity"], f["severity"])
#         print(f"\n  [{f['tmep_section']}] {sym}")
#         print(f"    Item       : {f['item']}")
#         print(f"    Finding    : {f['finding']}")
#         print(f"    Action     : {f['recommendation']}")
#     print(f"\n{border}\n")


# # ═══════════════════════════════════════════════════════════════════════════════
# # QUICK TEST — Shows standalone and with Pillar 1 context
# # ═══════════════════════════════════════════════════════════════════════════════

# if __name__ == "__main__":

#     # ── Test 1: Your original example — STANDALONE (no Pillar 1) ─────────────
#     print("\n--- TEST 1: Standalone (your original example) ---")
#     result = analyze_identification_under_tmep_1402(
#         "Computer software (downloadable) for managing databases; "
#         "Clothing, namely, shirts, pants, and shoes; and related tech."
#     )
#     print_pillar2_report(result)

#     # ── Test 2: With Pillar 1 context — §1(b) intent-to-use ──────────────────
#     print("\n--- TEST 2: With Pillar 1 context (§1(b) intent-to-use) ---")
#     ctx = Pillar1ClassContext(
#         class_number=42,
#         class_title="Scientific and Technology Services",
#         class_category="SERVICES",
#         filing_basis="1(b)",
#         specimen_type="",
#         specimen_description="",
#         has_pillar1_class_error=False,
#         has_pillar1_class_warning=False
#     )
#     result2 = analyze_identification_under_tmep_1402(
#         "Software as a service featuring artificial intelligence tools; "
#         "cloud computing services for others in the field of data analytics",
#         pillar1_context=ctx
#     )
#     print_pillar2_report(result2, class_number=42)

#     # ── Test 3: Misclassification from Pillar 1 defers accuracy check ─────────
#     print("\n--- TEST 3: Pillar 1 class ERROR defers accuracy check ---")
#     ctx_error = Pillar1ClassContext(
#         class_number=25,
#         class_title="Clothing and Footwear",
#         class_category="GOODS",
#         filing_basis="1(a)",
#         specimen_type="product label",
#         specimen_description="product label on clothing",
#         has_pillar1_class_error=True,
#         pillar1_error_summary="Software placed in Class 25 (clothing) — misclassification"
#     )
#     result3 = analyze_identification_under_tmep_1402(
#         "Software for inventory management; computer programs for retail management",
#         pillar1_context=ctx_error
#     )
#     print_pillar2_report(result3, class_number=25)

#     # ── Test 4: Services without 'for others' language ────────────────────────
#     print("\n--- TEST 4: Services identification missing 'for others' ---")
#     ctx_svc = Pillar1ClassContext(
#         class_number=41,
#         class_title="Education and Entertainment Services",
#         class_category="SERVICES",
#         filing_basis="1(a)",
#         specimen_type="website screenshot",
#         specimen_description="screenshot of online education platform"
#     )
#     result4 = analyze_identification_under_tmep_1402(
#         "Educational training programs; entertainment events including concerts and shows",
#         pillar1_context=ctx_svc
#     )
#     print_pillar2_report(result4, class_number=41)
