# pipeline/StructuralToSubstantiveGate.py
"""
StructuralToSubstantiveGate
============================
Converts PipelineState (Pillars 1–3) → NORMALIZED_APPLICATION dict.
Computes all gate flags deterministically.

DESIGN PRINCIPLES (Strict)
  1. Extract ONLY confirmed, stable data from Pillar outputs
  2. BLOCK search if structural instability exists
  3. BLOCK substantive engines if identification is indefinite
  4. BLOCK specimen review if filing basis is not use-based
  5. Produce deterministic boolean gate flags
  6. NEVER guess — only derive from Pillar outputs
  7. Record a reason string for every block (for audit + Office Action)

What This Correctly Enforces
  Search is blocked if:
    - Multi-class non-compliant (Pillar 3)
    - Pillar 1 errors exist
    - Fee misalignment
  Substantive engines blocked if:
    - Identification indefinite (Pillar 2)
  Specimen engine blocked if:
    - Not use-based filing

Gate Decision Matrix:
  ┌──────────────────────────────┬──────────────────────────────────────────┐
  │ Condition                    │ Blocked Engines                          │
  ├──────────────────────────────┼──────────────────────────────────────────┤
  │ Pillar 1 errors > 0          │ §704.02, §1207, §1209, §904              │
  │ Pillar 3 non-compliant       │ §704.02, §1207, §1209, §904              │
  │ Fee misaligned               │ §704.02, §1207, §1209, §904              │
  │ Identification indefinite    │ §1207, §1209, §904                       │
  │ Filing basis not use-based   │ §904 only                                │
  │ All clean                    │ ALL GATES OPEN                           │
  └──────────────────────────────┴──────────────────────────────────────────┘

Legal authority:
  Search gate    → §704.02  (search only on stable, confirmed scope)
  Substantive    → §1402    (identification must be definite before §1207/§1209)
  Specimen gate  → §904     (specimen only for §1(a) and §44(e) filings)
"""

from typing import Dict, Any
from core.pipeline_state import PipelineState

_USE_BASED_FILING_BASES = {"1a", "44e"}


def build_normalized_application(state: PipelineState) -> Dict[str, Any]:
    """
    Bridge layer: PipelineState → NORMALIZED_APPLICATION dict.

    Args:
        state: PipelineState from the 1st half (Pillars 1–3)

    Returns:
        NORMALIZED_APPLICATION dict — ready for pipeline_runner.run_second_half()
    """

    # ─────────────────────────────────────────────
    # EXTRACT CORE STRUCTURAL DATA
    # ─────────────────────────────────────────────

    raw = state.raw_input
    p1  = state.pillar1_output
    p2  = state.pillar2_output
    p3  = state.pillar3_output

    confirmed_classes   = state.get_confirmed_classes()
    partial_refusals    = state.get_partial_refusal_classes()
    division_candidates = state.get_division_candidates()
    clean_classes       = state.get_clean_classes()

    # Identification mapping — zero-pad to standard 3-digit class format
    per_class_identification = {}
    for cls, result in p2.items():
        analysis = result.get("tmep_1402_analysis", {})
        segments = analysis.get("identified_goods_services", [])
        per_class_identification[_pad_class(cls)] = segments

    # Fee alignment
    fee_alignment_status = (
        "aligned"
        if raw.get("fees_paid_count", 0) == len(raw.get("classes", []))
        else "misaligned"
    )

    # Filing basis (dominant — first class or top-level)
    filing_basis = ""
    if raw.get("classes"):
        filing_basis = str(raw["classes"][0].get("filing_basis", "")).lower()
    else:
        filing_basis = str(raw.get("filing_basis", "")).lower()

    # ─────────────────────────────────────────────
    # GATE LOGIC — deterministic, no guessing
    # ─────────────────────────────────────────────

    p1_errors    = p1.get("summary", {}).get("errors", 0)
    p3_compliant = getattr(p3, "is_multi_class_compliant", True)

    # ── GATE 1: §704.02 Search ───────────────────────────────────────────────
    search_blocks = []
    if p1_errors > 0:
        search_blocks.append(
            f"Pillar 1 classification errors ({p1_errors}) — scope unstable. §1401."
        )
    if not p3_compliant:
        search_blocks.append(
            "Pillar 3 multi-class non-compliant — "
            "search scope not finalized. §1403."
        )
    if fee_alignment_status == "misaligned":
        search_blocks.append(
            "Fee misalignment detected — class count unconfirmed. §810."
        )

    cleared_for_search  = len(search_blocks) == 0
    search_block_reason = " | ".join(search_blocks)

    # ── GATE 2: §1207 + §1209 Substantive ────────────────────────────────────
    identification_indefinite = False
    for cls, result in p2.items():
        summary = result.get("summary", {})
        if not summary.get("is_definite", True):
            identification_indefinite = True
            break

    substantive_blocks = list(search_blocks)           # inherits search blocks
    if identification_indefinite:
        substantive_blocks.append(
            "Identification indefinite in one or more classes — "
            "§1207/§1209 cannot run on indefinite goods/services. §1402."
        )

    cleared_for_substantive  = len(substantive_blocks) == 0
    substantive_block_reason = " | ".join(substantive_blocks)

    # ── GATE 3: §904 Specimen ─────────────────────────────────────────────────
    specimen_blocks = list(substantive_blocks)         # inherits substantive blocks
    if filing_basis not in _USE_BASED_FILING_BASES:
        specimen_blocks.append(
            f"Filing basis '{filing_basis}' is not use-based — "
            f"§904 applies only to §1(a) and §44(e) filings."
        )

    cleared_for_specimen  = len(specimen_blocks) == 0
    specimen_block_reason = " | ".join(specimen_blocks)

    # Procedural placeholder (§800 engine not yet built)
    procedural_issues = _extract_procedural_issues(raw)

    # Build goods_services in engine format
    goods_services = _build_goods_services(
        raw, per_class_identification, confirmed_classes
    )

    # ─────────────────────────────────────────────
    # BUILD NORMALIZED APPLICATION
    # ─────────────────────────────────────────────

    normalized = {
        # ── From Pillar 1
        "confirmed_class_numbers":  confirmed_classes,

        # ── From Pillar 2
        "per_class_identification": per_class_identification,

        # ── From Pillar 3
        "is_multi_class_compliant": p3_compliant,
        "partial_refusal_classes":  partial_refusals,
        "division_candidates":      division_candidates,
        "fee_alignment_status":     fee_alignment_status,
        "clean_classes":            clean_classes,

        # ── From §800 (placeholder)
        "procedural_issues": procedural_issues,
        "filing_basis":      filing_basis,
        "entity_type":       raw.get("entity_type", ""),

        # ── Core mark fields (read by all engines)
        "application_id": raw.get("application_serial", ""),
        "mark_text":      raw.get("mark_text", ""),
        "mark_type":      raw.get("mark_type", "standard_character"),
        "goods_services": goods_services,
        "event_trigger":  "first_review",

        # ── Gate flags — deterministic booleans
        "cleared_for_search":      cleared_for_search,
        "cleared_for_substantive": cleared_for_substantive,
        "cleared_for_specimen":    cleared_for_specimen,

        # ── Block reasons (for audit log + Office Action)
        "search_block_reason":      search_block_reason,
        "substantive_block_reason": substantive_block_reason,
        "specimen_block_reason":    specimen_block_reason,
    }

    return normalized


# ──────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ──────────────────────────────────────────────────────────────────────────────


def _pad_class(cls) -> str:
    """Zero-pads IC class numbers to 3 digits: 9 → '009', 42 → '042'."""
    return str(int(cls)).zfill(3)


def _build_goods_services(
    raw: Dict[str, Any],
    per_class_identification: Dict[str, Any],
    confirmed_classes: list,
) -> list:
    """
    Builds goods_services in engine format: [{"class": "009", "description": "..."}, ...]
    Priority:
      1. Pillar 2 identified_goods_services (authoritative)
      2. Raw input class descriptions (fallback)
    """
    result = []
    for cls in confirmed_classes:
        cls_str  = str(cls)
        segments = (per_class_identification.get(cls_str)
                    or per_class_identification.get(cls, []))
        if segments:
            desc = "; ".join(str(s) for s in segments)
        else:
            desc = _raw_description_for_class(raw, cls_str)
        result.append({"class": cls_str, "description": desc})

    if not result:
        for raw_cls in raw.get("classes", []):
            result.append({
                "class":       str(raw_cls.get("class_number",
                                               raw_cls.get("class", ""))),
                "description": str(raw_cls.get("description", "")),
            })
    return result


def _raw_description_for_class(raw: Dict[str, Any], cls: str) -> str:
    for raw_cls in raw.get("classes", []):
        raw_num = str(raw_cls.get("class_number", raw_cls.get("class", "")))
        if raw_num == str(cls):
            return str(raw_cls.get("description", ""))
    return ""


def _extract_procedural_issues(raw: Dict[str, Any]) -> list:
    """
    §800 placeholder checks.
    Replace with state.section800_output.get("issues", []) when §800 is built.
    """
    issues = []
    if not raw.get("signature"):
        issues.append("signature_missing")
    if not raw.get("applicant_name"):
        issues.append("applicant_name_missing")
    if raw.get("power_of_attorney_required") and not raw.get("power_of_attorney"):
        issues.append("power_of_attorney_missing")
    return issues
