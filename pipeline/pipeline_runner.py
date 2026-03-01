# pipeline/pipeline_runner.py
"""
PipelineRunner — Orchestrates the entire 2nd half.
====================================================
Receives NORMALIZED_APPLICATION dict from StructuralToSubstantiveGate.
Enforces gate flags. Runs each engine only when its gate is open.

Full execution flow (from image / legal alignment table):

    normalized_app = build_normalized_application(state)
                        ↓
    run_second_half(normalized_app)
                        ↓
       ┌────────────────────────────────┐
       │  GATE: cleared_for_search?     │
       │  Legal Authority: §704.02      │
       └────────────────┬───────────────┘
                        ↓ YES
                 §704.02 Search Engine
                        ↓
       ┌────────────────────────────────┐
       │  GATE: cleared_for_substantive?│
       │  Legal Authority: §1207/§1209  │
       └────────────────┬───────────────┘
                        ↓ YES
          §1207 Similarity  +  §1209 Descriptiveness
                        ↓
       ┌────────────────────────────────┐
       │  GATE: cleared_for_specimen?   │
       │  Legal Authority: §904         │
       └────────────────┬───────────────┘
                        ↓ YES
               §904 Specimen Review (stub)
                        ↓
               Decision Aggregator (stub)
                        ↓
                  PipelineResult dict

Gate enforcement:
  - cleared_for_search = False  → §704.02 blocked → §1207/§1209/§904 also blocked
  - cleared_for_substantive = False → §1207/§1209 blocked → §904 also blocked
  - cleared_for_specimen = False → §904 blocked only
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.search_engine import conduct_tmep_704_02_search
from similarity.similarity_engine import conduct_tmep_1207_analysis
from descriptiveness.descriptiveness_engine import conduct_tmep_1209_analysis


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def run_second_half(
    normalized_app: Dict[str, Any],
    *,
    tess_adapter=None,
    geographic_area: str = "United States",
) -> Dict[str, Any]:
    """
    Runs all 2nd-half engines on a NORMALIZED_APPLICATION dict.

    Args:
        normalized_app:  Output of build_normalized_application(state)
        tess_adapter:    Injectable search adapter (for tests / overrides)
        geographic_area: Geographic area for §1207.04 concurrent use analysis

    Returns:
        PipelineResult dict — JSON-serialisable, ready for Decision Aggregator.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result: Dict[str, Any] = {
        "application_id":     normalized_app.get("application_id", ""),
        "mark_text":          normalized_app.get("mark_text", ""),
        "analysis_timestamp": timestamp,
        "pipeline_version":   "1.0.0",

        # Gate status (mirrors the image's Legal Alignment table)
        "gate_status": {
            "search":      {
                "cleared":           normalized_app["cleared_for_search"],
                "reason":            normalized_app.get("search_block_reason", ""),
                "legal_authority":   "§704.02",
            },
            "substantive": {
                "cleared":           normalized_app["cleared_for_substantive"],
                "reason":            normalized_app.get("substantive_block_reason", ""),
                "legal_authority":   "§1207 / §1209",
            },
            "specimen":    {
                "cleared":           normalized_app["cleared_for_specimen"],
                "reason":            normalized_app.get("specimen_block_reason", ""),
                "legal_authority":   "§904",
            },
            "procedural":  {
                "issues":            normalized_app.get("procedural_issues", []),
                "legal_authority":   "§800",
            },
        },

        # Engine outputs
        "search_result":          None,
        "similarity_result":      None,
        "descriptiveness_result": None,
        "specimen_result":        None,     # stub — §904 not yet built
        "aggregated_refusals":    None,     # stub — aggregator not yet built

        "run_engines":     [],
        "blocked_engines": [],
        "pipeline_status": "pending",
    }

    # Engine input format (what §704.02, §1207, §1209 accept)
    engine_input = {
        "application_id": normalized_app.get("application_id", ""),
        "mark_text":      normalized_app.get("mark_text", ""),
        "mark_type":      normalized_app.get("mark_type", "standard_character"),
        "goods_services": normalized_app.get("goods_services", []),
        "event_trigger":  normalized_app.get("event_trigger", "first_review"),
    }

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 1 — §704.02 Search
    # ══════════════════════════════════════════════════════════════════════════
    if not normalized_app["cleared_for_search"]:
        result["blocked_engines"] += ["§704.02", "§1207", "§1209", "§904"]
        result["pipeline_status"]  = "blocked_at_search_gate"
        return result

    try:
        search_result = conduct_tmep_704_02_search(
            engine_input, tess_adapter=tess_adapter
        )
        result["search_result"]  = search_result
        result["run_engines"].append("§704.02")
    except Exception as exc:
        result["blocked_engines"] += ["§704.02", "§1207", "§1209", "§904"]
        result["gate_status"]["search"]["error"] = str(exc)
        result["pipeline_status"] = "search_engine_error"
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 2 — §1207 + §1209 Substantive
    # ══════════════════════════════════════════════════════════════════════════
    if not normalized_app["cleared_for_substantive"]:
        result["blocked_engines"] += ["§1207", "§1209", "§904"]
        result["pipeline_status"]  = "blocked_at_substantive_gate"
        # Aggregation still possible from search result alone
        result["aggregated_refusals"] = _aggregate_refusals(
            normalized_app, search_result, None, None, None
        )
        return result

    # §1207 — Likelihood of Confusion
    try:
        similarity_result = conduct_tmep_1207_analysis(
            search_result, geographic_area=geographic_area
        )
        result["similarity_result"] = similarity_result
        result["run_engines"].append("§1207")
    except Exception as exc:
        result["blocked_engines"].append("§1207")
        result["gate_status"]["substantive"]["error_1207"] = str(exc)
        similarity_result = None

    # §1209 — Descriptiveness
    try:
        descriptiveness_result = conduct_tmep_1209_analysis(engine_input)
        result["descriptiveness_result"] = descriptiveness_result
        result["run_engines"].append("§1209")
    except Exception as exc:
        result["blocked_engines"].append("§1209")
        result["gate_status"]["substantive"]["error_1209"] = str(exc)
        descriptiveness_result = None

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 3 — §904 Specimen
    # ══════════════════════════════════════════════════════════════════════════
    if not normalized_app["cleared_for_specimen"]:
        result["blocked_engines"].append("§904")
    else:
        result["specimen_result"] = _specimen_stub(normalized_app)
        result["run_engines"].append("§904 (stub)")

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 4 — Decision Aggregator (stub)
    # ══════════════════════════════════════════════════════════════════════════
    result["aggregated_refusals"] = _aggregate_refusals(
        normalized_app,
        search_result,
        result["similarity_result"],
        result["descriptiveness_result"],
        result["specimen_result"],
    )
    result["run_engines"].append("aggregator (stub)")
    result["pipeline_status"] = _compute_final_status(result)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# STUBS — replace with real modules when built
# ──────────────────────────────────────────────────────────────────────────────

def _specimen_stub(app: Dict[str, Any]) -> Dict[str, Any]:
    """§904 Specimen Review — STUB. Replace with specimen/ module."""
    return {
        "authority_reference": "TMEP §904",
        "status":              "NOT_IMPLEMENTED",
        "filing_basis":        app.get("filing_basis", ""),
        "classes_requiring_specimen": app.get("clean_classes", []),
        "note": (
            "§904 specimen review engine not yet built. "
            "Filing basis confirmed use-based — specimen review is required. "
            "Build specimen/ module next."
        ),
    }


def _aggregate_refusals(
    normalized_app:  Dict[str, Any],
    search_result:   Optional[Dict],
    similarity:      Optional[Dict],
    descriptiveness: Optional[Dict],
    specimen:        Optional[Dict],
) -> Dict[str, Any]:
    """
    Decision Aggregator — STUB.
    Produces per-class refusal flag map from all engine outputs.
    Replace with aggregator/ module when built.

    Final output shape (what the real aggregator will produce):
    {
        "009": {
            "procedural_error":        False,
            "classification_error":    False,
            "identification_error":    False,
            "likelihood_of_confusion": True,
            "descriptiveness":         False,
            "specimen_error":          False,
            "overall_refusal":         True,
        }
    }
    """
    per_class: Dict[str, Dict] = {}

    # §1207 conflict check
    confusion = False
    if similarity:
        analyses  = similarity.get("section_1207_01", {}).get("dupont_analyses", [])
        confusion = any(a.get("refusal_recommended") for a in analyses)

    # §1209 descriptiveness check
    desc_refusal = bool(
        descriptiveness and descriptiveness.get("refusal_recommended")
    )

    for cls in normalized_app.get("confirmed_class_numbers", []):
        partial = cls in normalized_app.get("partial_refusal_classes", [])
        overall = confusion or desc_refusal or partial

        per_class[cls] = {
            "procedural_error":        bool(normalized_app.get("procedural_issues")),
            "classification_error":    partial,
            "identification_error":    not normalized_app.get("is_multi_class_compliant", True),
            "likelihood_of_confusion": confusion,
            "descriptiveness":         desc_refusal,
            "specimen_error":          False,   # populated by real §904 engine
            "overall_refusal":         overall,
        }

    return {
        "authority_reference":   "Decision Aggregator (stub)",
        "status":                "STUB — replace with aggregator/ module",
        "per_class_refusals":    per_class,
        "any_refusal":           any(v["overall_refusal"] for v in per_class.values()),
        "partial_refusal_classes":  normalized_app.get("partial_refusal_classes", []),
        "division_candidates":      normalized_app.get("division_candidates", []),
        "fee_alignment_status":     normalized_app.get("fee_alignment_status", ""),
    }


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _compute_final_status(result: Dict) -> str:
    blocked = result["blocked_engines"]
    if not blocked:
        return "complete"
    if "§704.02" in blocked:
        return "blocked_at_search_gate"
    if "§1207" in blocked and "§1209" in blocked:
        return "blocked_at_substantive_gate"
    if "§904" in blocked:
        return "blocked_at_specimen_gate"
    return "partial_complete"
