# descriptiveness/models.py
"""
Data models for TMEP §1209 Descriptiveness Module.

§1209 covers:
  §1209.01 — Distinctiveness/Descriptiveness Continuum
  §1209.02 — Procedure for Descriptiveness and/or Genericness Refusal
  §1209.03 — Considerations Relevant to Determination
  §1209.04 — Deceptively Misdescriptive Marks
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


# ──────────────────────────────────────────────────────────────────────────────
# §1209.01 — THE DISTINCTIVENESS CONTINUUM
# Abercrombie & Fitch Co. v. Hunting World, Inc., 537 F.2d 4 (2d Cir. 1976)
# ──────────────────────────────────────────────────────────────────────────────

class DistinctivenessLevel(str, Enum):
    GENERIC      = "GENERIC"       # Never registrable — the common name of goods
    DESCRIPTIVE  = "DESCRIPTIVE"   # §2(e)(1) — registrable only with §2(f) acquired distinctiveness
    SUGGESTIVE   = "SUGGESTIVE"    # Inherently distinctive — requires imagination to connect to goods
    ARBITRARY    = "ARBITRARY"     # Common word applied to unrelated goods — inherently distinctive
    FANCIFUL     = "FANCIFUL"      # Coined word — strongest protection

class DescriptivenessType(str, Enum):
    """Specific type of §2(e) descriptiveness ground."""
    MERELY_DESCRIPTIVE            = "merely_descriptive"        # §2(e)(1)
    DECEPTIVELY_MISDESCRIPTIVE    = "deceptively_misdescriptive"  # §2(e)(1)
    PRIMARILY_GEOGRAPHIC          = "primarily_geographically_descriptive"  # §2(e)(2)
    PRIMARILY_SURNAME             = "primarily_merely_a_surname"  # §2(e)(4)
    FUNCTIONAL                    = "functional"                  # §2(e)(5)
    GENERIC                       = "generic"                     # §1209.01(a)
    NONE                          = "none"

class RefusalGround(str, Enum):
    SECTION_2E1_DESCRIPTIVE       = "§2(e)(1) Merely Descriptive"
    SECTION_2E1_MISDESCRIPTIVE    = "§2(e)(1) Deceptively Misdescriptive"
    SECTION_2E2_GEOGRAPHIC        = "§2(e)(2) Primarily Geographically Descriptive"
    SECTION_2E4_SURNAME           = "§2(e)(4) Primarily Merely a Surname"
    SECTION_2E5_FUNCTIONAL        = "§2(e)(5) Functional"
    GENERIC_REFUSAL               = "§1209.01(a) Generic — Incapable of Registration"
    NONE                          = "No Descriptiveness Refusal"

class OvercomeMethod(str, Enum):
    """How an applicant can overcome a §2(e) refusal."""
    SECTION_2F_ACQUIRED           = "§2(f) Acquired Distinctiveness"
    SUPPLEMENTAL_REGISTER         = "Supplemental Register (§23)"
    AMENDMENT_TO_MARK             = "Amendment to Mark / Disclaimer"
    ARGUMENT_ON_MERITS            = "Argument — Mark Not Merely Descriptive"
    NOT_OVERCOMEABLE              = "Not overcomeable (generic / absolute bar)"


# ──────────────────────────────────────────────────────────────────────────────
# EVIDENCE TYPES — §1209.03
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DescriptiveEvidence:
    """A single piece of evidence supporting a descriptiveness finding."""
    source:       str    # "dictionary", "trade_publication", "applicant_usage", "competitor_usage"
    excerpt:      str    # The relevant text or finding
    weight:       float  # 0.0–1.0 — how probative this evidence is
    url:          str    = ""
    date:         str    = ""


# ──────────────────────────────────────────────────────────────────────────────
# §1209.01 — CONTINUUM ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ContinuumAnalysis:
    """
    §1209.01 — Positions the mark on the Abercrombie distinctiveness spectrum.

    The "imagination test": does a consumer need to use imagination to
    connect the mark to the goods? If yes → suggestive or above.
    """
    mark_text:             str
    goods_description:     str
    ic_classes:            list[str]

    distinctiveness_level: DistinctivenessLevel = DistinctivenessLevel.SUGGESTIVE
    imagination_required:  bool   = True    # False → descriptive/generic
    directly_describes:    bool   = False   # True → likely descriptive
    competitor_need:       bool   = False   # Do competitors need this term?
    compound_descriptive:  bool   = False   # Each part separately descriptive?
    distinctiveness_score: float  = 0.0     # 0.0 = generic, 1.0 = fanciful
    reasoning:             str    = ""


# ──────────────────────────────────────────────────────────────────────────────
# §1209.02 — REFUSAL PROCEDURE ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RefusalProcedureAnalysis:
    """
    §1209.02 — Determines which §2(e) ground applies and what procedural
    steps the examiner should take.
    """
    refusal_warranted:     bool              = False
    refusal_ground:        RefusalGround     = RefusalGround.NONE
    descriptiveness_type:  DescriptivenessType = DescriptivenessType.NONE
    statutory_basis:       str              = ""
    is_absolute_bar:       bool             = False   # Generic = can never register
    overcome_methods:      list[OvercomeMethod] = field(default_factory=list)
    disclaimer_required:   bool             = False   # Examiner may require disclaimer of descriptive term
    acquired_distinctiveness_possible: bool = False
    procedure_notes:       str              = ""


# ──────────────────────────────────────────────────────────────────────────────
# §1209.03 — CONSIDERATIONS / EVIDENCE
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ConsiderationsAnalysis:
    """
    §1209.03 — Evidence-based analysis of descriptiveness factors.

    Key considerations per TMEP §1209.03:
      (a) Dictionary evidence
      (b) Trade publication usage
      (c) Applicant's own descriptive use
      (d) Competitor need to use the term
      (e) Whether term immediately conveys info about goods
      (f) Degree to which term is used in the relevant industry
    """
    # Evidence gathered
    dictionary_evidence:      list[DescriptiveEvidence] = field(default_factory=list)
    trade_usage_evidence:     list[DescriptiveEvidence] = field(default_factory=list)
    applicant_usage_evidence: list[DescriptiveEvidence] = field(default_factory=list)
    competitor_usage_evidence: list[DescriptiveEvidence] = field(default_factory=list)

    # Findings from evidence
    dictionary_definitions_found:    bool  = False
    used_descriptively_in_trade:      bool  = False
    applicant_used_descriptively:     bool  = False
    competitors_use_same_term:        bool  = False
    immediately_conveys_info:         bool  = False

    # Aggregate evidence strength
    evidence_strength:     float = 0.0    # 0.0–1.0 how strong the refusal evidence is
    total_evidence_count:  int   = 0
    analysis_notes:        str   = ""


# ──────────────────────────────────────────────────────────────────────────────
# §1209.04 — DECEPTIVELY MISDESCRIPTIVE
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DeceptiveMisdescriptiveAnalysis:
    """
    §1209.04 — Deceptively Misdescriptive under §2(e)(1).

    Different from §1207.02 (§2(a) deceptive — absolute bar).
    §2(e)(1) deceptively misdescriptive = overcomeable with §2(f).

    Test (In re Quady Winery, 221 USPQ 1213 (TTAB 1984)):
      1. Does the mark misdescribe the goods?
      2. Would consumers be likely to believe the misdescription?
    Note: Unlike §2(a), materiality to purchase is NOT required for §2(e)(1).
    """
    misdescription_detected:         bool  = False
    misdescriptive_term:             str   = ""
    goods_actually_have_quality:     bool  = False   # Does the good actually have this quality?
    consumers_likely_to_believe:     bool  = False
    refusal_warranted:               bool  = False
    overcomeable_with_2f:            bool  = True    # §2(e)(1) IS overcomeable unlike §2(a)
    statutory_basis:                 str   = ""
    notes:                           str   = ""


# ──────────────────────────────────────────────────────────────────────────────
# FULL §1209 OUTPUT
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Section1209Analysis:
    """
    Complete §1209 analysis — all four subsections combined.
    Returned by conduct_tmep_1209_analysis().
    """
    # Header
    authority_reference:   str = "TMEP §1209"
    applied_for_mark:      str = ""
    applied_for_classes:   list[str] = field(default_factory=list)
    goods_description:     str = ""
    analysis_timestamp:    str = ""

    # §1209.01 — Continuum positioning
    continuum:             ContinuumAnalysis = field(
                               default_factory=lambda: ContinuumAnalysis("", "", [])
                           )

    # §1209.02 — Refusal procedure
    procedure:             RefusalProcedureAnalysis = field(
                               default_factory=RefusalProcedureAnalysis
                           )

    # §1209.03 — Considerations / evidence
    considerations:        ConsiderationsAnalysis = field(
                               default_factory=ConsiderationsAnalysis
                           )

    # §1209.04 — Deceptive misdescriptiveness
    deceptive_misdescriptive: DeceptiveMisdescriptiveAnalysis = field(
                               default_factory=DeceptiveMisdescriptiveAnalysis
                           )

    # Overall result
    refusal_recommended:   bool  = False
    refusal_ground:        str   = ""
    is_absolute_bar:       bool  = False
    overcome_methods:      list[str] = field(default_factory=list)
    distinctiveness_level: str   = ""
    compliance_status:     str   = ""
