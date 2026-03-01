# similarity/models.py
"""
Data models for TMEP §1207 Similarity Engine.
All dataclasses used across all four §1207 subsections live here.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class ConfusionLikelihood(str, Enum):
    LIKELY   = "LIKELY"     # final_score >= 0.75  → §2(d) refusal
    POSSIBLE = "POSSIBLE"   # final_score >= 0.50  → manual review
    UNLIKELY = "UNLIKELY"   # final_score <  0.50  → cleared

class DeceptionType(str, Enum):
    GEOGRAPHIC    = "geographic"      # falsely suggests geographic origin
    SURNAME       = "surname"         # primarily merely a surname
    LIVING_PERSON = "living_person"   # name/likeness of living person
    INSTITUTION   = "institution"     # falsely suggests institution connection
    NONE          = "none"

class ConcurrentUseType(str, Enum):
    GEOGRAPHIC_LIMITATION = "geographic_limitation"
    PRIOR_USER_CONSENT    = "prior_user_consent"
    NOT_APPLICABLE        = "not_applicable"


# ──────────────────────────────────────────────────────────────────────────────
# FACTOR SCORE DATACLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Factor1Score:
    """§1207.01 — DuPont Factor 1: Similarity of the Marks"""
    visual_similarity:   float = 0.0   # Levenshtein-based
    phonetic_similarity: float = 0.0   # Soundex comparison
    meaning_similarity:  float = 0.0   # Semantic / dominant word match
    dominant_word_match: bool  = False
    composite_score:     float = 0.0   # Weighted average of above
    notes:               str   = ""


@dataclass
class Factor2Score:
    """§1207.01 — DuPont Factor 2: Relatedness of Goods/Services"""
    same_class:          bool  = False
    adjacent_class:      bool  = False
    description_overlap: float = 0.0   # keyword overlap in descriptions
    composite_score:     float = 0.0
    notes:               str   = ""


@dataclass
class Factor3Score:
    """§1207.01 — DuPont Factor 3: Trade Channels"""
    same_channels:      bool  = False
    overlapping_channels: bool = False
    composite_score:    float = 0.0
    notes:              str   = ""


@dataclass
class Factor4Score:
    """§1207.01 — DuPont Factor 4: Conditions of Purchase"""
    buyer_sophistication: str   = "ordinary"  # "ordinary" | "sophisticated" | "expert"
    impulse_purchase:     bool  = False
    composite_score:      float = 0.0         # HIGH score = MORE likely confused
    notes:                str   = ""


@dataclass
class DuPontScores:
    """All four DuPont factor scores for one applied-vs-conflict pair."""
    factor1: Factor1Score = field(default_factory=Factor1Score)
    factor2: Factor2Score = field(default_factory=Factor2Score)
    factor3: Factor3Score = field(default_factory=Factor3Score)
    factor4: Factor4Score = field(default_factory=Factor4Score)
    weighted_final_score: float = 0.0
    dominant_factor:      str   = ""


# ──────────────────────────────────────────────────────────────────────────────
# PER-CONFLICT ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ConflictAnalysis:
    """
    Full §1207.01 analysis result for ONE conflicting mark vs the applied-for mark.
    """
    # Identifiers
    application_number:  str
    conflicting_mark:    str
    conflicting_status:  str
    conflicting_classes: list[str]
    owner_name:          str

    # DuPont scoring
    dupont_scores:       DuPontScores = field(default_factory=DuPontScores)

    # Decision
    confusion_likelihood:  ConfusionLikelihood = ConfusionLikelihood.UNLIKELY
    confusion_likely:      bool  = False
    refusal_recommended:   bool  = False
    dominant_factor:       str   = ""
    legal_basis:           str   = ""
    examiner_notes:        str   = ""


# ──────────────────────────────────────────────────────────────────────────────
# §1207.02 — DECEPTIVE MARKS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DeceptionAnalysis:
    """§1207.02 — Analysis for marks likely to deceive."""
    deception_detected:  bool          = False
    deception_type:      DeceptionType = DeceptionType.NONE
    misdescriptive_term: str           = ""
    goods_actually_contain: bool       = False   # Does the goods contain the term?
    purchaser_likely_to_believe: bool  = False
    materiality_to_purchase:     bool  = False
    refusal_recommended:         bool  = False
    legal_basis:                 str   = ""
    notes:                       str   = ""


# ──────────────────────────────────────────────────────────────────────────────
# §1207.03 — UNREGISTERED MARKS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class UnregisteredMarkAnalysis:
    """§1207.03 — Prior use in US but not registered."""
    prior_use_detected:   bool  = False
    prior_use_territory:  str   = ""     # geographic area of prior use
    prior_use_date:       str   = ""
    conflict_with_applied: bool = False
    refusal_recommended:  bool  = False
    legal_basis:          str   = ""
    notes:                str   = ""


# ──────────────────────────────────────────────────────────────────────────────
# §1207.04 — CONCURRENT USE
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ConcurrentUseAnalysis:
    """§1207.04 — Concurrent use registration eligibility."""
    concurrent_use_possible:    bool               = False
    use_type:                   ConcurrentUseType  = ConcurrentUseType.NOT_APPLICABLE
    geographic_area_applied:    str                = ""
    geographic_area_conflicting: str               = ""
    areas_overlap:              bool               = False
    prior_user_consent_obtained: bool              = False
    registration_possible:      bool               = False
    notes:                      str                = ""


# ──────────────────────────────────────────────────────────────────────────────
# FULL §1207 OUTPUT
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Section1207Analysis:
    """
    Complete §1207 analysis output — all four subsections combined.
    This is what conduct_tmep_1207_analysis() returns.
    """
    # Header
    authority_reference:   str = "TMEP §1207.01"
    applied_for_mark:      str = ""
    applied_for_classes:   list[str] = field(default_factory=list)
    conflicts_analysed:    int = 0
    analysis_timestamp:    str = ""

    # §1207.01 — Per-conflict confusion analysis
    conflict_analyses:     list[ConflictAnalysis] = field(default_factory=list)

    # §1207.02 — Deception analysis
    deception_analysis:    DeceptionAnalysis = field(default_factory=DeceptionAnalysis)

    # §1207.03 — Unregistered prior use
    unregistered_analysis: UnregisteredMarkAnalysis = field(default_factory=UnregisteredMarkAnalysis)

    # §1207.04 — Concurrent use
    concurrent_use_analysis: ConcurrentUseAnalysis = field(default_factory=ConcurrentUseAnalysis)

    # Overall decision
    overall_confusion_likely:       bool  = False
    overall_refusal_recommended:    bool  = False
    section_2d_applicable:          bool  = False
    highest_risk_conflict:          str   = ""   # application_number
    highest_dupont_score:           float = 0.0
    compliance_status:              str   = ""
