# descriptiveness/descriptiveness_engine.py
"""
TMEP §1209 — Descriptiveness Engine
=====================================
Main entry point for the full §1209 analysis.

Takes dummy application input (mark_text, goods_description, ic_classes)
and returns a complete JSON-serialisable §1209 analysis across all
four subsections.

Architecture:
    Application Input
          ↓
    conduct_tmep_1209_analysis()        [THIS MODULE]
      ├── §1209.01 continuum.py          → distinctiveness level
      ├── §1209.02 procedure_and_considerations.py → refusal ground
      ├── §1209.03 procedure_and_considerations.py → evidence analysis
      └── §1209.04 deceptive_misdescriptive.py    → misdescriptive check
          ↓
    §1209 Analysis Output (JSON-serialisable)
          ↓
    Office Action Generator            [DOWNSTREAM]

Input (dummy / real):
    {
        "application_id":  "123456789",
        "mark_text":       "FRESH DAILY",
        "mark_type":       "standard_character",
        "goods_services":  [{"class": "029", "description": "Fresh fruit"}],
        "event_trigger":   "first_review"
    }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from descriptiveness.models import (
    DistinctivenessLevel, OvercomeMethod,
)
from descriptiveness.continuum import analyse_continuum
from descriptiveness.procedure_and_considerations import (
    analyse_procedure, analyse_considerations,
)
from descriptiveness.deceptive_misdescriptive import analyse_deceptive_misdescriptive


# ──────────────────────────────────────────────────────────────────────────────
# DUMMY INPUT SAMPLES (for testing / demo without §704.02 pipeline)
# ──────────────────────────────────────────────────────────────────────────────

DUMMY_INPUTS = {
    "descriptive": {
        "application_id": "111111111",
        "mark_text":       "FRESH DAILY",
        "mark_type":       "standard_character",
        "goods_services":  [{"class": "029", "description": "Fresh fruit and vegetables"}],
        "event_trigger":   "first_review",
    },
    "generic": {
        "application_id": "222222222",
        "mark_text":       "FRUIT",
        "mark_type":       "standard_character",
        "goods_services":  [{"class": "029", "description": "Dried and fresh fruit"}],
        "event_trigger":   "first_review",
    },
    "suggestive": {
        "application_id": "333333333",
        "mark_text":       "COPPERTONE",
        "mark_type":       "standard_character",
        "goods_services":  [{"class": "003", "description": "Suntan lotion and sunscreen"}],
        "event_trigger":   "first_review",
    },
    "arbitrary": {
        "application_id": "444444444",
        "mark_text":       "APPLE",
        "mark_type":       "standard_character",
        "goods_services":  [{"class": "009", "description": "Computers and smartphones"}],
        "event_trigger":   "first_review",
    },
    "surname": {
        "application_id": "555555555",
        "mark_text":       "ADAMS APPLE",
        "mark_type":       "standard_character",
        "goods_services":  [{"class": "029", "description": "Dried fruit"}],
        "event_trigger":   "first_review",
    },
    "misdescriptive": {
        "application_id": "666666666",
        "mark_text":       "SILK TOUCH",
        "mark_type":       "standard_character",
        "goods_services":  [{"class": "025", "description": "Synthetic polyester clothing"}],
        "event_trigger":   "first_review",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def conduct_tmep_1209_analysis(
    application_data: dict,
) -> dict[str, Any]:
    """
    TMEP §1209 — Descriptiveness Analysis
    =======================================
    Accepts application dict (dummy or real) and returns complete §1209
    analysis across all four subsections.

    Args:
        application_data: Dict with keys:
            application_id, mark_text, mark_type,
            goods_services (list of {"class": str, "description": str}),
            event_trigger

    Returns:
        JSON-serialisable §1209 analysis dict.

    Raises:
        ValueError — if required fields are missing.
    """
    _validate_input(application_data)

    mark_text  = application_data["mark_text"].strip()
    ic_classes = [gs["class"] for gs in application_data["goods_services"]]
    goods_desc = " ".join(
        gs.get("description", "") for gs in application_data["goods_services"]
    )
    timestamp  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── §1209.01 — Continuum ──────────────────────────────────────────────────
    continuum = analyse_continuum(mark_text, goods_desc, ic_classes)

    # ── §1209.02 — Refusal Procedure ─────────────────────────────────────────
    procedure = analyse_procedure(
        mark_text, goods_desc, ic_classes,
        continuum.distinctiveness_level,
        continuum.distinctiveness_score,
    )

    # ── §1209.03 — Considerations / Evidence ─────────────────────────────────
    considerations = analyse_considerations(mark_text, goods_desc, ic_classes)

    # ── §1209.04 — Deceptive Misdescriptiveness ───────────────────────────────
    deceptive = analyse_deceptive_misdescriptive(mark_text, goods_desc, ic_classes)

    # ── Overall Result ────────────────────────────────────────────────────────
    refusal_recommended = procedure.refusal_warranted or deceptive.refusal_warranted
    is_absolute_bar     = procedure.is_absolute_bar
    overcome_methods    = [m.value for m in procedure.overcome_methods]
    refusal_ground      = (
        procedure.refusal_ground.value
        if procedure.refusal_warranted
        else (
            "§2(e)(1) Deceptively Misdescriptive"
            if deceptive.refusal_warranted
            else "No Refusal"
        )
    )
    compliance = _build_compliance(
        mark_text, continuum.distinctiveness_level,
        refusal_recommended, is_absolute_bar
    )

    # ── Assemble Output ───────────────────────────────────────────────────────
    return {
        # Header
        "authority_reference":  "TMEP §1209",
        "applied_for_mark":     mark_text,
        "applied_for_classes":  ic_classes,
        "goods_description":    goods_desc,
        "analysis_timestamp":   timestamp,

        # §1209.01 — Distinctiveness Continuum
        "section_1209_01": {
            "distinctiveness_level":  continuum.distinctiveness_level.value,
            "distinctiveness_score":  continuum.distinctiveness_score,
            "imagination_required":   continuum.imagination_required,
            "directly_describes":     continuum.directly_describes,
            "competitor_need":        continuum.competitor_need,
            "compound_descriptive":   continuum.compound_descriptive,
            "reasoning":              continuum.reasoning,
        },

        # §1209.02 — Refusal Procedure
        "section_1209_02": {
            "refusal_warranted":      procedure.refusal_warranted,
            "refusal_ground":         procedure.refusal_ground.value,
            "descriptiveness_type":   procedure.descriptiveness_type.value,
            "statutory_basis":        procedure.statutory_basis,
            "is_absolute_bar":        procedure.is_absolute_bar,
            "overcome_methods":       [m.value for m in procedure.overcome_methods],
            "disclaimer_required":    procedure.disclaimer_required,
            "acquired_distinctiveness_possible": procedure.acquired_distinctiveness_possible,
            "procedure_notes":        procedure.procedure_notes,
        },

        # §1209.03 — Evidence & Considerations
        "section_1209_03": {
            "dictionary_definitions_found":     considerations.dictionary_definitions_found,
            "used_descriptively_in_trade":      considerations.used_descriptively_in_trade,
            "applicant_used_descriptively":     considerations.applicant_used_descriptively,
            "competitors_use_same_term":        considerations.competitors_use_same_term,
            "immediately_conveys_info":         considerations.immediately_conveys_info,
            "evidence_strength":                considerations.evidence_strength,
            "total_evidence_count":             considerations.total_evidence_count,
            "evidence": {
                "dictionary":   [_serialise_evidence(e) for e in considerations.dictionary_evidence],
                "trade_usage":  [_serialise_evidence(e) for e in considerations.trade_usage_evidence],
                "applicant":    [_serialise_evidence(e) for e in considerations.applicant_usage_evidence],
                "competitor":   [_serialise_evidence(e) for e in considerations.competitor_usage_evidence],
            },
            "analysis_notes":   considerations.analysis_notes,
        },

        # §1209.04 — Deceptively Misdescriptive
        "section_1209_04": {
            "misdescription_detected":      deceptive.misdescription_detected,
            "misdescriptive_term":          deceptive.misdescriptive_term,
            "goods_actually_have_quality":  deceptive.goods_actually_have_quality,
            "consumers_likely_to_believe":  deceptive.consumers_likely_to_believe,
            "refusal_warranted":            deceptive.refusal_warranted,
            "overcomeable_with_2f":         deceptive.overcomeable_with_2f,
            "statutory_basis":              deceptive.statutory_basis,
            "notes":                        deceptive.notes,
            "distinction_from_2a": (
                "§2(e)(1) deceptively misdescriptive refusals ARE overcomeable "
                "with §2(f) acquired distinctiveness. Unlike §2(a) deceptive marks "
                "(TMEP §1207.02), registration is possible. TMEP §1209.04."
            ),
        },

        # Overall
        "refusal_recommended":     refusal_recommended,
        "refusal_ground":          refusal_ground,
        "is_absolute_bar":         is_absolute_bar,
        "overcome_methods":        overcome_methods,
        "distinctiveness_level":   continuum.distinctiveness_level.value,
        "compliance_status":       compliance,
    }


def conduct_tmep_1209_analysis_dummy(scenario: str = "descriptive") -> dict[str, Any]:
    """
    Convenience wrapper — runs §1209 analysis with a built-in dummy input.

    Available scenarios: "descriptive", "generic", "suggestive",
                         "arbitrary", "surname", "misdescriptive"
    """
    if scenario not in DUMMY_INPUTS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. "
            f"Choose from: {list(DUMMY_INPUTS.keys())}"
        )
    return conduct_tmep_1209_analysis(DUMMY_INPUTS[scenario])


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _validate_input(data: dict) -> None:
    required = ["mark_text", "goods_services"]
    for field in required:
        if field not in data:
            raise ValueError(
                f"§1209 analysis requires '{field}'. Got: {list(data.keys())}"
            )
    if not data["mark_text"].strip():
        raise ValueError("mark_text cannot be empty.")
    if not isinstance(data["goods_services"], list) or len(data["goods_services"]) == 0:
        raise ValueError("goods_services must be a non-empty list.")


def _serialise_evidence(e) -> dict:
    return {
        "source":  e.source,
        "excerpt": e.excerpt,
        "weight":  e.weight,
        "url":     e.url,
        "date":    e.date,
    }


def _build_compliance(
    mark: str,
    level: DistinctivenessLevel,
    refusal: bool,
    absolute: bool,
) -> str:
    parts = [f"§1209 analysis complete for mark '{mark}'."]
    parts.append(
        f"Distinctiveness level: {level.value}."
    )
    if absolute:
        parts.append(
            "Mark is GENERIC — incapable of registration. "
            "No form of acquired distinctiveness can overcome. Final refusal."
        )
    elif refusal:
        parts.append(
            "Descriptiveness refusal warranted. "
            "Applicant may overcome via §2(f) acquired distinctiveness "
            "or Supplemental Register."
        )
    else:
        parts.append(
            "No descriptiveness refusal warranted. "
            "Mark is inherently distinctive."
        )
    return " ".join(parts)
