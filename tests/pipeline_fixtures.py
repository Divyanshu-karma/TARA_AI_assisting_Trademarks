# tests/pipeline_fixtures.py
"""
Shared fixtures for pipeline tests.

Provides factory functions that build realistic PipelineState objects
for all gate scenarios without requiring the real 1st-half modules.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from core.pipeline_state import PipelineState


# ──────────────────────────────────────────────────────────────────────────────
# MINIMAL PILLAR 3 STUB
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Pillar3Stub:
    """Minimal Pillar3AssessmentResult substitute for tests."""
    is_multi_class_compliant: bool    = True
    total_errors:             int     = 0
    partial_refusal_classes:  list    = None
    division_eligible_classes: list   = None

    def __post_init__(self):
        if self.partial_refusal_classes is None:
            self.partial_refusal_classes = []
        if self.division_eligible_classes is None:
            self.division_eligible_classes = []


# ──────────────────────────────────────────────────────────────────────────────
# RAW INPUT TEMPLATES
# ──────────────────────────────────────────────────────────────────────────────

_RAW_CLEAN = {
    "application_serial": "12345678",
    "mark_text":          "ADAMS APPLE",
    "mark_type":          "standard_character",
    "applicant_name":     "Test Corp",
    "signature":          "John Doe",
    "entity_type":        "corporation",
    "filing_basis":       "1a",
    "fees_paid_count":    1,
    "classes": [
        {
            "class_number": "029",
            "description":  "Dried fruits and vegetables",
            "filing_basis": "1a",
        }
    ],
}

_RAW_MULTI_CLASS_CLEAN = {
    "application_serial": "99887766",
    "mark_text":          "ZENITH CLOUD",
    "mark_type":          "standard_character",
    "applicant_name":     "Acme Corp",
    "signature":          "Jane Smith",
    "entity_type":        "corporation",
    "filing_basis":       "1a",
    "fees_paid_count":    2,
    "classes": [
        {"class_number": "009", "description": "Computer software",    "filing_basis": "1a"},
        {"class_number": "042", "description": "Software as a service","filing_basis": "1a"},
    ],
}

_RAW_INTENT_TO_USE = dict(_RAW_CLEAN)
_RAW_INTENT_TO_USE["filing_basis"] = "1b"
_RAW_INTENT_TO_USE["classes"] = [
    {"class_number": "029", "description": "Dried fruit", "filing_basis": "1b"}
]


# ──────────────────────────────────────────────────────────────────────────────
# PILLAR OUTPUT TEMPLATES
# ──────────────────────────────────────────────────────────────────────────────

def _p1_clean(errors: int = 0) -> dict:
    return {
        "summary":     {"errors": errors, "warnings": 0},
        "application": {},
        "report":      "Pillar 1 complete.",
    }


def _p2_definite(classes: list[str], descriptions: dict[str, str] = None) -> dict:
    """Pillar 2 output with is_definite=True for all classes."""
    result = {}
    for cls in classes:
        desc = (descriptions or {}).get(cls, f"Goods in class {cls}")
        result[int(cls)] = {
            "summary":          {"is_definite": True, "errors": 0},
            "tmep_1402_analysis": {
                "identified_goods_services": [desc],
                "is_definite": True,
            },
        }
    return result


def _p2_indefinite(classes: list[str]) -> dict:
    """Pillar 2 output with is_definite=False — blocks substantive engines."""
    result = {}
    for cls in classes:
        result[int(cls)] = {
            "summary":          {"is_definite": False, "errors": 1},
            "tmep_1402_analysis": {
                "identified_goods_services": [],
                "is_definite": False,
            },
        }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE STATE FACTORIES
# ──────────────────────────────────────────────────────────────────────────────

def make_clean_state() -> PipelineState:
    """
    All gates open:
      - Pillar 1 clean
      - Pillar 3 compliant
      - Identification definite
      - Use-based filing (1a)
      - Fees aligned
    Expected: cleared_for_search=True, cleared_for_substantive=True, cleared_for_specimen=True
    """
    return PipelineState(
        raw_input      = _RAW_CLEAN,
        pillar1_output = _p1_clean(errors=0),
        pillar2_output = _p2_definite(["029"], {"029": "Dried fruits and vegetables"}),
        pillar3_output = Pillar3Stub(is_multi_class_compliant=True, total_errors=0),
    )


def make_p1_error_state() -> PipelineState:
    """
    Pillar 1 has errors → ALL gates blocked.
    Expected: cleared_for_search=False, cleared_for_substantive=False, cleared_for_specimen=False
    """
    return PipelineState(
        raw_input      = _RAW_CLEAN,
        pillar1_output = _p1_clean(errors=2),
        pillar2_output = _p2_definite(["029"]),
        pillar3_output = Pillar3Stub(is_multi_class_compliant=True, total_errors=0),
    )


def make_p3_noncompliant_state() -> PipelineState:
    """
    Pillar 3 non-compliant → ALL gates blocked.
    Expected: cleared_for_search=False
    """
    return PipelineState(
        raw_input      = _RAW_CLEAN,
        pillar1_output = _p1_clean(errors=0),
        pillar2_output = _p2_definite(["029"]),
        pillar3_output = Pillar3Stub(is_multi_class_compliant=False, total_errors=3),
    )


def make_fee_misaligned_state() -> PipelineState:
    """
    Fee misalignment (paid 1, filed 2) → search gate blocked.
    Expected: cleared_for_search=False
    """
    raw = dict(_RAW_CLEAN)
    raw["fees_paid_count"] = 1
    raw["classes"] = [
        {"class_number": "029", "description": "Dried fruit",  "filing_basis": "1a"},
        {"class_number": "030", "description": "Baked goods",  "filing_basis": "1a"},
    ]
    return PipelineState(
        raw_input      = raw,
        pillar1_output = _p1_clean(errors=0),
        pillar2_output = _p2_definite(["029", "030"]),
        pillar3_output = Pillar3Stub(is_multi_class_compliant=True, total_errors=0),
    )


def make_indefinite_id_state() -> PipelineState:
    """
    Identification indefinite → search open, substantive blocked.
    Expected: cleared_for_search=True, cleared_for_substantive=False
    """
    return PipelineState(
        raw_input      = _RAW_CLEAN,
        pillar1_output = _p1_clean(errors=0),
        pillar2_output = _p2_indefinite(["029"]),
        pillar3_output = Pillar3Stub(is_multi_class_compliant=True, total_errors=0),
    )


def make_intent_to_use_state() -> PipelineState:
    """
    Intent-to-use filing (1b) → specimen gate blocked.
    Expected: cleared_for_search=True, cleared_for_substantive=True, cleared_for_specimen=False
    """
    raw = dict(_RAW_INTENT_TO_USE)
    raw["fees_paid_count"] = 1
    return PipelineState(
        raw_input      = raw,
        pillar1_output = _p1_clean(errors=0),
        pillar2_output = _p2_definite(["029"], {"029": "Dried fruit"}),
        pillar3_output = Pillar3Stub(is_multi_class_compliant=True, total_errors=0),
    )


def make_multi_class_state() -> PipelineState:
    """
    Multi-class, all clean.
    Expected: all gates open, 2 classes confirmed.
    """
    raw = dict(_RAW_MULTI_CLASS_CLEAN)
    raw["fees_paid_count"] = 2
    return PipelineState(
        raw_input      = raw,
        pillar1_output = _p1_clean(errors=0),
        pillar2_output = _p2_definite(
            ["009", "042"],
            {"009": "Computer software", "042": "Software as a service"},
        ),
        pillar3_output = Pillar3Stub(is_multi_class_compliant=True, total_errors=0),
    )


def make_partial_refusal_state() -> PipelineState:
    """
    One class flagged for partial refusal.
    Expected: class 030 in partial_refusal_classes.
    """
    raw = dict(_RAW_MULTI_CLASS_CLEAN)
    raw["fees_paid_count"] = 2
    raw["classes"] = [
        {"class_number": "029", "description": "Dried fruit",  "filing_basis": "1a"},
        {"class_number": "030", "description": "Baked goods",  "filing_basis": "1a"},
    ]
    return PipelineState(
        raw_input      = raw,
        pillar1_output = _p1_clean(errors=0),
        pillar2_output = _p2_definite(["029", "030"]),
        pillar3_output = Pillar3Stub(
            is_multi_class_compliant = True,
            total_errors             = 0,
            partial_refusal_classes  = ["030"],
            division_eligible_classes = ["030"],
        ),
    )
