# core/search_engine.py
"""
TMEP §704.02 — Examining Attorney's Search
Main Engine

Final output is §1207-READY, meaning it contains:
  - applied_for_mark      → the mark being examined (structured)
  - conflict_set          → full list of conflicting marks with all fields
  - goods_services_analysis → IC class overlap analysis
  - preliminary_flag      → quick indicator of confusion risk
  - refusal_flag          → whether §2(d) refusal is possible (not decided — §1207 decides)

Architecture:
    §704.02 Search Engine  →  Returns §1207-ready package   [THIS MODULE]
            ↓
    §1207.01 Similarity Engine  →  DuPont analysis          [NEXT MODULE]
            ↓
    Office Action Generator                                  [AFTER THAT]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from adapters.base import TessAdapterBase
from adapters.tess_live import TessLiveAdapter
from core.models import (
    AUTHORITY_REFERENCE,
    DATABASE_NAME,
    RECORDS_SEARCHED,
    VARIATION_TYPES,
    ConflictRecord,
    EventTrigger,
)
from core.query_builder import build_search_queries
from core.validators import (
    ApplicationValidationError,
    SearchNotRequiredError,
    assert_search_required,
    evaluate_re_search,
    validate_and_parse,
)


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def conduct_tmep_704_02_search(
    application_data: dict,
    *,
    tess_adapter:     TessAdapterBase | None = None,
    return_audit_log: bool = False,
) -> dict | tuple[dict, dict]:
    """
    TMEP §704.02 — Examining Attorney's Search

    Returns a §1207-ready output package containing:
      - Standard §704.02 compliance fields
      - applied_for_mark       (structured mark info for §1207)
      - conflict_set           (full conflict records for §1207 scoring)
      - goods_services_analysis (IC class overlap — §1207 Factor 2 input)
      - preliminary_flag       (quick risk indicator)
      - refusal_flag           (possible §2(d) — §1207 makes final call)

    Args:
        application_data  : Raw trademark application dict
        tess_adapter      : Adapter override (default: TessLiveAdapter)
                            Use MockConflictAdapter() for tests
                            Use RapidApiTrademarkAdapter(key) for RapidAPI
        return_audit_log  : If True returns (output, audit_log) tuple

    Raises:
        ApplicationValidationError  — bad/missing input fields
        SearchNotRequiredError      — event trigger not legally required
    """

    # ── 1. VALIDATE & PARSE ───────────────────────────────────────────────────
    app = validate_and_parse(application_data)

    # ── 2. PROCEDURAL GATE ───────────────────────────────────────────────────
    assert_search_required(app.event_trigger)

    # ── 3. TIMESTAMP ─────────────────────────────────────────────────────────
    search_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── 4. BUILD SOLR QUERIES ─────────────────────────────────────────────────
    queries = build_search_queries(app.mark_text, app.goods_services)

    # ── 5. SEARCH USPTO ──────────────────────────────────────────────────────
    adapter   = tess_adapter or TessLiveAdapter()
    conflicts = adapter.search(queries)

    # ── 6. RE-SEARCH FLAG ─────────────────────────────────────────────────────
    re_search_required, re_search_basis = evaluate_re_search(app.event_trigger)

    # ── 7. §1207-READY ANALYSIS BLOCKS ───────────────────────────────────────
    applied_ic_classes      = [gs.ic_class for gs in app.goods_services]
    conflict_set            = _build_conflict_set(conflicts)
    goods_analysis          = _build_goods_analysis(applied_ic_classes, conflicts)
    preliminary_flag        = _build_preliminary_flag(conflicts, applied_ic_classes)
    refusal_flag            = _build_refusal_flag(conflicts, applied_ic_classes)

    # ── 8. COMPLIANCE STATUS ─────────────────────────────────────────────────
    compliance_status = _build_compliance_status(
        event_trigger      = app.event_trigger,
        conflicts_found    = len(conflicts),
        re_search_required = re_search_required,
        re_search_basis    = re_search_basis,
    )

    # ── 9. ASSEMBLE FULL OUTPUT ───────────────────────────────────────────────
    output: dict[str, Any] = {

        # ── §704.02 STANDARD FIELDS ──────────────────────────────────────────
        "authority_reference": AUTHORITY_REFERENCE,
        "search_conducted":    True,
        "search_timestamp":    search_timestamp,
        "search_scope": {
            "database":         DATABASE_NAME,
            "records_searched": RECORDS_SEARCHED,
            "variation_types":  VARIATION_TYPES,
        },

        # ── APPLIED-FOR MARK (structured for §1207) ───────────────────────────
        "applied_for_mark": {
            "mark_text":      app.mark_text,
            "mark_type":      app.mark_type,
            "ic_classes":     applied_ic_classes,
            "goods_services": [
                {"class": gs.ic_class, "description": gs.description}
                for gs in app.goods_services
            ],
        },

        # ── CONFLICT SET (full records for §1207 scoring) ────────────────────
        "conflict_set": conflict_set,

        # ── RESULTS SUMMARY ──────────────────────────────────────────────────
        "results_summary": {
            "total_conflicts_found":           len(conflicts),
            "conflicting_application_numbers": [c.application_number for c in conflicts],
        },

        # ── GOODS/SERVICES ANALYSIS (§1207 Factor 2 input) ───────────────────
        "goods_services_analysis": goods_analysis,

        # ── PRELIMINARY FLAG (quick risk indicator — NOT a §1207 decision) ───
        "preliminary_flag": preliminary_flag,

        # ── REFUSAL FLAG (possible §2(d) — §1207 makes the final call) ───────
        "refusal_flag": refusal_flag,

        # ── PROCEDURAL FIELDS ────────────────────────────────────────────────
        "re_search_required": re_search_required,
        "compliance_status":  compliance_status,
    }

    # ── 10. OPTIONAL AUDIT LOG ────────────────────────────────────────────────
    if return_audit_log:
        audit_log = _build_audit_log(
            app              = application_data,
            search_timestamp = search_timestamp,
            queries          = queries,
            conflicts        = conflicts,
            re_search        = re_search_required,
            re_search_basis  = re_search_basis,
        )
        return output, audit_log

    return output


# ──────────────────────────────────────────────────────────────────────────────
# §1207-READY BLOCK BUILDERS
# ──────────────────────────────────────────────────────────────────────────────

def _build_conflict_set(conflicts: list[ConflictRecord]) -> list[dict]:
    """
    Serialises conflict records into the format §1207 expects.
    Each record carries all fields §1207 needs for DuPont scoring.
    """
    return [
        {
            "application_number":   c.application_number,
            "mark_text":            c.mark_text,
            "status":               c.status,
            "ic_classes":           c.ic_classes,
            "registration_number":  c.registration_number,
            "filing_date":          c.filing_date,
            "registration_date":    c.registration_date,
            "owner_name":           c.owner_name,
            "surfaced_by":          c.surfaced_by_query_type,
        }
        for c in conflicts
    ]


def _build_goods_analysis(
    applied_classes: list[str],
    conflicts:       list[ConflictRecord],
) -> dict:
    """
    Analyses IC class overlap between the applied-for mark and each conflict.

    §1207 Factor 2 (goods/services relatedness) uses this directly.

    Overlap levels:
      same_class     → applied class == conflict class  (highest risk)
      adjacent_class → classes known to be related      (medium risk)
      no_overlap     → completely different classes     (low risk)
    """
    applied_set = set(applied_classes)

    same_class_conflicts:    list[str] = []
    adjacent_class_conflicts: list[str] = []
    no_overlap_conflicts:    list[str] = []

    for c in conflicts:
        conflict_set = set(c.ic_classes)
        if applied_set & conflict_set:
            same_class_conflicts.append(c.application_number)
        elif _has_adjacent_classes(applied_set, conflict_set):
            adjacent_class_conflicts.append(c.application_number)
        else:
            no_overlap_conflicts.append(c.application_number)

    class_overlap_detected = len(same_class_conflicts) > 0

    return {
        "applied_ic_classes":              applied_classes,
        "conflicts_with_same_class":       len(same_class_conflicts),
        "conflicts_with_adjacent_class":   len(adjacent_class_conflicts),
        "conflicts_with_no_class_overlap": len(no_overlap_conflicts),
        "class_overlap_detected":          class_overlap_detected,
        "same_class_application_numbers":  same_class_conflicts,
        # §1207 picks this up directly for Factor 2 scoring
        "factor2_input_ready":             True,
    }


def _build_preliminary_flag(
    conflicts:       list[ConflictRecord],
    applied_classes: list[str],
) -> dict:
    """
    Quick risk indicator based on search results alone.
    NOT a §1207 decision — just signals how urgently §1207 analysis is needed.

    Risk levels:
      HIGH   — exact mark match found in same IC class
      MEDIUM — similar marks found in same IC class, or exact in different class
      LOW    — no same-class conflicts, no exact matches
    """
    applied_set   = set(applied_classes)
    exact_matches = [
        c for c in conflicts
        if c.surfaced_by_query_type == "exact"
    ]
    same_class_exact = [
        c for c in exact_matches
        if set(c.ic_classes) & applied_set
    ]
    same_class_any = [
        c for c in conflicts
        if set(c.ic_classes) & applied_set
    ]

    if same_class_exact:
        level   = "HIGH"
        reason  = f"Exact mark match found in same IC class ({len(same_class_exact)} conflict(s))"
    elif same_class_any:
        level   = "MEDIUM"
        reason  = f"Conflicts found in same IC class ({len(same_class_any)} conflict(s))"
    elif conflicts:
        level   = "LOW"
        reason  = f"Conflicts found in different IC classes ({len(conflicts)} conflict(s))"
    else:
        level   = "NONE"
        reason  = "No conflicts found in any IC class"

    return {
        "risk_level":              level,       # "HIGH" | "MEDIUM" | "LOW" | "NONE"
        "reason":                  reason,
        "exact_match_count":       len(exact_matches),
        "same_class_exact_count":  len(same_class_exact),
        "same_class_total_count":  len(same_class_any),
        # §1207 uses this to prioritise which conflicts to analyse first
        "priority_conflicts":      [c.application_number for c in same_class_exact],
    }


def _build_refusal_flag(
    conflicts:       list[ConflictRecord],
    applied_classes: list[str],
) -> dict:
    """
    Signals whether a §2(d) refusal is POSSIBLE based on search results.
    §1207 makes the actual refusal decision after DuPont analysis.

    refusal_possible = True  → §1207 MUST run full analysis
    refusal_possible = False → §1207 still runs but low priority
    """
    applied_set       = set(applied_classes)
    same_class_active = [
        c for c in conflicts
        if set(c.ic_classes) & applied_set
        and c.status in ("registered", "pending")
    ]

    refusal_possible = len(same_class_active) > 0

    return {
        # Core field §1207 checks first
        "refusal_possible":           refusal_possible,

        # Number of live marks in same class — §1207 analyses each
        "same_class_active_conflicts": len(same_class_active),

        # Application numbers §1207 must prioritise
        "priority_for_1207_analysis": [c.application_number for c in same_class_active],

        # Legal basis if refusal is raised
        "potential_legal_basis":      "Trademark Act §2(d), 15 U.S.C. §1052(d)"
                                      if refusal_possible else None,

        # Always remind §1207 that it owns the final call
        "pending_1207_analysis":      True,
        "note": (
            "Refusal not yet determined. §1207.01 DuPont analysis required."
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

# IC classes that are considered "adjacent" (related goods/services)
# Source: USPTO examination guidelines
_ADJACENT_CLASS_PAIRS: set[frozenset] = {
    frozenset({"029", "030"}),   # Food items
    frozenset({"029", "031"}),   # Food / agricultural
    frozenset({"030", "032"}),   # Food / beverages
    frozenset({"032", "033"}),   # Beverages (non-alc / alc)
    frozenset({"025", "035"}),   # Clothing / retail
    frozenset({"009", "042"}),   # Software / tech services
    frozenset({"035", "036"}),   # Business / financial services
    frozenset({"041", "044"}),   # Education / health services
}


def _has_adjacent_classes(a: set[str], b: set[str]) -> bool:
    for ca in a:
        for cb in b:
            if frozenset({ca, cb}) in _ADJACENT_CLASS_PAIRS:
                return True
    return False


def _build_compliance_status(
    event_trigger:      str,
    conflicts_found:    int,
    re_search_required: bool,
    re_search_basis:    str | None,
) -> str:
    trigger_label = {
        EventTrigger.FIRST_REVIEW:    "initial examination",
        EventTrigger.REVIVAL:         "application revival (§718.07)",
        EventTrigger.AMENDMENT_GOODS: "goods/services amendment",
        EventTrigger.NEW_BASIS:       "new filing basis",
    }.get(event_trigger.lower(), event_trigger)

    parts = [
        f"Procedural search completed under {AUTHORITY_REFERENCE}",
        f"triggered by {trigger_label}.",
        f"Search conducted: YES.",
        f"Total conflicts identified: {conflicts_found}.",
    ]
    if re_search_required and re_search_basis:
        parts.append(
            f"Re-search flag set — mandatory under {re_search_basis} "
            f"due to {trigger_label}."
        )
    parts.append(
        "Matter is now procedurally cleared for §1207 likelihood-of-confusion analysis."
    )
    return " ".join(parts)


def _build_audit_log(
    app: dict, search_timestamp: str, queries: list,
    conflicts: list[ConflictRecord], re_search: bool, re_search_basis: str | None,
) -> dict:
    return {
        "audit_id":            str(uuid.uuid4()),
        "authority_reference": AUTHORITY_REFERENCE,
        "application_id":      app["application_id"],
        "mark_text":           app["mark_text"],
        "mark_type":           app["mark_type"],
        "ic_classes":          [g.get("class") for g in app["goods_services"]],
        "event_trigger":       app["event_trigger"],
        "search_timestamp":    search_timestamp,
        "database_searched":   DATABASE_NAME,
        "queries_executed": [
            {
                "query_id":    q.query_id,
                "type":        q.query_type,
                "search_term": q.search_term,
                "solr_string": q.solr_string,
                "ic_classes":  q.ic_classes,
            }
            for q in queries
        ],
        "total_queries":      len(queries),
        "conflicts_raw": [
            {
                "application_number": c.application_number,
                "mark_text":          c.mark_text,
                "status":             c.status,
                "ic_classes":         c.ic_classes,
                "surfaced_by":        c.surfaced_by_query_type,
            }
            for c in conflicts
        ],
        "re_search_required":  re_search,
        "re_search_basis":     re_search_basis,
        "procedural_status":   "SEARCH_COMPLETE",
        "downstream_gate":     "CLEARED_FOR_1207",
    }

