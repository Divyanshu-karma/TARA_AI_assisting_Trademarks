# similarity/similarity_engine.py
"""
TMEP §1207.01 — Likelihood of Confusion Similarity Engine
==========================================================
Main entry point. Takes §704.02 output directly and returns
full §1207 analysis across all four subsections.

Architecture:
    §704.02 output  →  conduct_tmep_1207_analysis()  →  §1207 analysis package
                                    ↓
                        Office Action Generator  [DOWNSTREAM]

Input:  The dict returned by conduct_tmep_704_02_search()
Output: Complete §1207 analysis dict — JSON serialisable
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from similarity.models import Section1207Analysis
from similarity.dupont_engine import analyse_conflict, serialise_analysis
from similarity.section_1207_subsections import (
    analyse_1207_02,
    analyse_1207_03,
    analyse_1207_04,
)


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def conduct_tmep_1207_analysis(
    search_result: dict,
    *,
    geographic_area: str = "United States",
) -> dict[str, Any]:
    """
    TMEP §1207 — Likelihood of Confusion Analysis
    ===============================================
    Takes the output of conduct_tmep_704_02_search() and performs full
    §1207 analysis across all four subsections.

    Args:
        search_result:   Output dict from conduct_tmep_704_02_search()
        geographic_area: Applicant's geographic area of use (for §1207.04)

    Returns:
        Complete §1207 analysis as a JSON-serialisable dict.

    Raises:
        ValueError — if search_result is missing required §704.02 fields.
    """
    # ── 1. EXTRACT §704.02 INPUTS ─────────────────────────────────────────────
    _validate_search_result(search_result)

    afm              = search_result["applied_for_mark"]
    applied_mark     = afm["mark_text"]
    applied_classes  = afm["ic_classes"]
    applied_desc     = " ".join(
        gs.get("description", "") for gs in afm.get("goods_services", [])
    )
    conflict_set     = search_result.get("conflict_set", [])

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── 2. §1207.01 — RUN DUPONT ANALYSIS PER CONFLICT ───────────────────────
    conflict_analyses = []
    for conflict in conflict_set:
        ca = analyse_conflict(
            applied_mark        = applied_mark,
            applied_classes     = applied_classes,
            applied_description = applied_desc,
            conflict_record     = conflict,
        )
        conflict_analyses.append(ca)

    # ── 3. §1207.02 — DECEPTION ANALYSIS ─────────────────────────────────────
    deception = analyse_1207_02(applied_mark, applied_desc, applied_classes)

    # ── 4. §1207.03 — UNREGISTERED PRIOR USE ─────────────────────────────────
    unregistered = analyse_1207_03(conflict_set, applied_classes)

    # ── 5. §1207.04 — CONCURRENT USE ─────────────────────────────────────────
    concurrent = analyse_1207_04(
        applied_mark            = applied_mark,
        applied_classes         = applied_classes,
        conflict_set            = conflict_set,
        geographic_area_applied = geographic_area,
    )

    # ── 6. OVERALL DECISION ───────────────────────────────────────────────────
    refusals         = [ca for ca in conflict_analyses if ca.refusal_recommended]
    confusion_likely = [ca for ca in conflict_analyses if ca.confusion_likely]

    overall_refusal  = (
        len(refusals) > 0
        or deception.refusal_recommended
        or unregistered.refusal_recommended
    )
    overall_confusion = len(confusion_likely) > 0
    section_2d        = overall_refusal

    # Highest risk conflict
    if conflict_analyses:
        top = max(conflict_analyses,
                  key=lambda ca: ca.dupont_scores.weighted_final_score)
        highest_risk_app    = top.application_number
        highest_dupont_score = top.dupont_scores.weighted_final_score
    else:
        highest_risk_app    = ""
        highest_dupont_score = 0.0

    # ── 7. COMPLIANCE STATUS ──────────────────────────────────────────────────
    compliance = _build_compliance(
        applied_mark, len(conflict_analyses),
        overall_refusal, overall_confusion, section_2d
    )

    # ── 8. ASSEMBLE OUTPUT ────────────────────────────────────────────────────
    return {
        # Header
        "authority_reference":   "TMEP §1207.01",
        "applied_for_mark":      applied_mark,
        "applied_for_classes":   applied_classes,
        "conflicts_analysed":    len(conflict_analyses),
        "analysis_timestamp":    timestamp,

        # §1207.01 — Per-conflict DuPont results
        "section_1207_01": {
            "dupont_analyses":       [serialise_analysis(ca) for ca in conflict_analyses],
            "total_refusals_found":  len(refusals),
            "total_likely_confusion": len(confusion_likely),
        },

        # §1207.02 — Deception
        "section_1207_02": {
            "deception_detected":    deception.deception_detected,
            "deception_type":        deception.deception_type.value,
            "misdescriptive_term":   deception.misdescriptive_term,
            "refusal_recommended":   deception.refusal_recommended,
            "legal_basis":           deception.legal_basis,
            "notes":                 deception.notes,
        },

        # §1207.03 — Unregistered prior use
        "section_1207_03": {
            "prior_use_detected":    unregistered.prior_use_detected,
            "prior_use_date":        unregistered.prior_use_date,
            "conflict_detected":     unregistered.conflict_with_applied,
            "refusal_recommended":   unregistered.refusal_recommended,
            "legal_basis":           unregistered.legal_basis,
            "notes":                 unregistered.notes,
        },

        # §1207.04 — Concurrent use
        "section_1207_04": {
            "concurrent_use_possible":  concurrent.concurrent_use_possible,
            "use_type":                 concurrent.use_type.value,
            "geographic_area_applied":  concurrent.geographic_area_applied,
            "areas_overlap":            concurrent.areas_overlap,
            "registration_possible":    concurrent.registration_possible,
            "notes":                    concurrent.notes,
        },

        # Overall decision
        "overall_confusion_likely":       overall_confusion,
        "overall_refusal_recommended":    overall_refusal,
        "section_2d_applicable":          section_2d,
        "highest_risk_conflict":          highest_risk_app,
        "highest_dupont_score":           highest_dupont_score,
        "compliance_status":              compliance,
    }


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _validate_search_result(result: dict) -> None:
    """Ensures the §704.02 output has the fields §1207 needs."""
    required = ["applied_for_mark", "conflict_set"]
    for field in required:
        if field not in result:
            raise ValueError(
                f"§1207 analysis requires '{field}' in search_result. "
                f"Ensure conduct_tmep_704_02_search() completed successfully. "
                f"Got fields: {list(result.keys())}"
            )
    if "mark_text" not in result["applied_for_mark"]:
        raise ValueError(
            "search_result['applied_for_mark'] must contain 'mark_text'."
        )


def _build_compliance(
    mark: str, n_conflicts: int,
    overall_refusal: bool, confusion_likely: bool, section_2d: bool,
) -> str:
    parts = [
        f"§1207 analysis complete for mark '{mark}'.",
        f"{n_conflicts} conflict(s) analysed using DuPont framework.",
    ]
    if overall_refusal:
        parts.append(
            "§2(d) refusal recommended. "
            "Matter forwarded to Office Action Generator."
        )
    elif confusion_likely:
        parts.append(
            "Borderline confusion detected. Manual examiner review recommended."
        )
    else:
        parts.append(
            "No likelihood of confusion found. Mark cleared for approval consideration."
        )
    return " ".join(parts)
