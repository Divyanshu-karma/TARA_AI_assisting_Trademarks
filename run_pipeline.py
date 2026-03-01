# run_pipeline.py
"""
USPTO Trademark Examination Pipeline — Unified Runner
======================================================
Chains the complete 1st half + 2nd half into a single call.

FULL EXECUTION FLOW
-------------------
RAW INPUT (dict or JSON string)
    ↓
inputLayer.parser_pipeline      → canonical APPLICATION_DICT
    ↓
pillar1.service (§1401)         → Classification integrity
    ↓
pillar2.service (§1402)         → Identification integrity
    ↓
pillar3.service (§1403)         → Multi-class structural integrity
    ↓
core.pipeline_state.PipelineState  → Bridge object
    ↓
pipeline.StructuralToSubstantiveGate → NORMALIZED_APPLICATION + gate flags
    ↓
   [GATE 1: cleared_for_search?      legal: §704.02]
   [GATE 2: cleared_for_substantive? legal: §1402  ]
   [GATE 3: cleared_for_specimen?    legal: §904   ]
    ↓
pipeline.pipeline_runner → §704.02 → §1207 → §1209 → §904(stub) → Aggregator(stub)
    ↓
core.result_store → saves JSON to results/

USAGE
-----
    # Default demo (mock adapter, no network)
    python run_pipeline.py

    # With live USPTO adapter
    python run_pipeline.py --live

    # With RapidAPI (requires RAPIDAPI_KEY in .env)
    python run_pipeline.py --rapidapi

    # Pass a custom application JSON file
    python run_pipeline.py --input my_application.json

    # Import in code
    from run_pipeline import run_full_pipeline
    result = run_full_pipeline(application_dict)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from core.pipeline_state import PipelineState
from core.result_store   import ResultStore
from core.logger         import setup_logger


from inputLayer.parser_pipeline import run_extraction_pipeline, parse_application
from pillar1.service import run_pillar1
from pillar2.service import run_pillar2
from pillar3.service import run_pillar3

from pipeline.StructuralToSubstantiveGate import build_normalized_application
from pipeline.pipeline_runner             import run_second_half

logger = setup_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def run_full_pipeline(
    application_input:  dict | str,
    *,
    tess_adapter        = None,
    geographic_area:    str  = "United States",
    save_result:        bool = True,
) -> dict[str, Any]:
    """
    Runs the complete USPTO trademark examination pipeline end-to-end.

    Args:
        application_input:  Application dict or raw JSON string.
        tess_adapter:       Search adapter override.
                            None → TessLiveAdapter (real USPTO).
                            MockConflictAdapter() → no network (tests).
                            RapidApiTrademarkAdapter(key) → RapidAPI.
        geographic_area:    For §1207.04 concurrent-use geographic analysis.
        save_result:        If True, persists result JSON to results/ folder.

    Returns:
        Full pipeline result dict — always JSON-serialisable.
    """
    logger.info("=" * 60)
    logger.info("USPTO TRADEMARK EXAMINATION PIPELINE — START")
    logger.info("=" * 60)

    # ── 0. INPUT LAYER ────────────────────────────────────────────────────────
    logger.info("[Stage 0] Input Layer — parsing & normalising.")
    # application_dict = run_extraction_pipeline(application_input)
    # Stage 0 — route by input type
    if isinstance(application_input, dict):
        # Already structured dict — skip PDF extraction entirely
        application_dict = parse_application(application_input)

    elif isinstance(application_input, str) and application_input.endswith(".pdf"):
        # PDF file path string
        pipeline_result  = run_extraction_pipeline(application_input)
        application_dict = parse_application(pipeline_result["data"])

    elif isinstance(application_input, str):
        # Raw JSON string
        import json
        application_dict = parse_application(json.loads(application_input))

    else:
        # Bytes / Streamlit UploadedFile / file-like object
        pipeline_result  = run_extraction_pipeline(application_input)
        application_dict = parse_application(pipeline_result["data"])
    serial = application_dict.get("application_serial", "unknown")
    logger.info(
        f"  Mark: '{application_dict['mark_text']}' | "
        f"Serial: {serial} | "
        f"Classes: {len(application_dict.get('classes', []))}"
    )

    # ── 1. PILLAR 1 — §1401 Classification ───────────────────────────────────
    logger.info("[Stage 1] Pillar 1 — §1401 Classification Engine.")
    p1_output = run_pillar1(application_dict)
    logger.info(f"  Errors: {p1_output['summary']['errors']}")

    # ── 2. PILLAR 2 — §1402 Identification ───────────────────────────────────
    logger.info("[Stage 2] Pillar 2 — §1402 Identification Engine.")
    p2_output = run_pillar2(application_dict, p1_output)
    logger.info(f"  Classes processed: {len(p2_output)}")

    # ── 3. PILLAR 3 — §1403 Multi-Class Structure ─────────────────────────────
    logger.info("[Stage 3] Pillar 3 — §1403 Multi-Class Engine.")
    p3_output = run_pillar3(application_dict, p1_output, p2_output)
    logger.info(
        f"  Compliant: {p3_output.is_multi_class_compliant} | "
        f"Errors: {p3_output.total_errors}"
    )

    # ── 4. PIPELINE STATE — bridge object ─────────────────────────────────────
    logger.info("[Stage 4] Building PipelineState (1st→2nd half bridge).")
    state = PipelineState(
        raw_input      = application_dict,
        pillar1_output = p1_output,
        pillar2_output = p2_output,
        pillar3_output = p3_output,
    )
    logger.info(f"  Structurally clean: {state.is_structurally_clean()}")

    # ── 5. GATE ────────────────────────────────────────────────────────────────
    logger.info("[Stage 5] StructuralToSubstantiveGate — computing gate flags.")
    normalized_app = build_normalized_application(state)
    _log_gates(normalized_app)

    # ── 6. 2ND HALF ────────────────────────────────────────────────────────────
    logger.info("[Stage 6] Running 2nd-half engines.")
    second_half = run_second_half(
        normalized_app,
        tess_adapter    = tess_adapter,
        geographic_area = geographic_area,
    )
    logger.info(
        f"  Status: {second_half['pipeline_status']} | "
        f"Ran: {second_half['run_engines']}"
    )

    # ── 7. FULL RESULT ─────────────────────────────────────────────────────────
    full_result = {
        "pipeline_version":    "1.0.0",
        "authority_chain": [
            "TMEP §1401", "TMEP §1402", "TMEP §1403",
            "TMEP §704.02", "TMEP §1207.01", "TMEP §1209",
            "TMEP §904 (stub)", "Decision Aggregator (stub)",
        ],
        "application_serial":  serial,
        "mark_text":           application_dict["mark_text"],
        "structurally_clean":  state.is_structurally_clean(),

        # 1st-half summaries
        "pillar1_summary":     p1_output.get("summary"),
        "pillar2_classes":     list(p2_output.keys()),
        "pillar3_summary": {
            "is_multi_class_compliant":  p3_output.is_multi_class_compliant,
            "total_errors":              p3_output.total_errors,
            "partial_refusal_classes":   p3_output.partial_refusal_classes,
            "division_candidates":       p3_output.division_eligible_classes,
            "fee_alignment_status":      p3_output.fee_alignment_status,
        },

        # Gate flags
        "gate_flags": {
            "cleared_for_search":       normalized_app["cleared_for_search"],
            "cleared_for_substantive":  normalized_app["cleared_for_substantive"],
            "cleared_for_specimen":     normalized_app["cleared_for_specimen"],
            "search_block_reason":      normalized_app["search_block_reason"],
            "substantive_block_reason": normalized_app["substantive_block_reason"],
            "specimen_block_reason":    normalized_app["specimen_block_reason"],
        },

        # 2nd-half results
        "search_result":          second_half.get("search_result"),
        "similarity_result":      second_half.get("similarity_result"),
        "descriptiveness_result": second_half.get("descriptiveness_result"),
        "specimen_result":        second_half.get("specimen_result"),
        "aggregated_refusals":    second_half.get("aggregated_refusals"),
        "gate_status":            second_half.get("gate_status"),

        "pipeline_status":  second_half["pipeline_status"],
        "run_engines":      second_half["run_engines"],
        "blocked_engines":  second_half["blocked_engines"],
    }

    # ── 8. SAVE ────────────────────────────────────────────────────────────────
    if save_result:
        store = ResultStore()
        path  = store.save(full_result, serial)
        full_result["saved_to"] = path
        logger.info(f"  Saved → {path}")

    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE — {full_result['pipeline_status']}")
    logger.info("=" * 60)
    return full_result


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _log_gates(norm: dict) -> None:
    pairs = [
        ("§704.02 Search",     "cleared_for_search",      "search_block_reason"),
        ("§1207/§1209 Subst.", "cleared_for_substantive", "substantive_block_reason"),
        ("§904 Specimen",      "cleared_for_specimen",    "specimen_block_reason"),
    ]
    for label, flag, reason in pairs:
        ok  = norm[flag]
        sym = "✓ OPEN" if ok else "✗ BLOCKED"
        logger.info(f"  Gate [{label:22s}] {sym}")
        if not ok and norm.get(reason):
            logger.info(f"    → {norm[reason]}")


def _build_demo_app() -> dict:
    return {
        "application_serial": "87654321",
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


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="USPTO Trademark Examination Pipeline"
    )
    parser.add_argument("--input",    type=str, default=None,
                        help="Path to application JSON file")
    parser.add_argument("--live",     action="store_true",
                        help="Use TessLiveAdapter (real USPTO API)")
    parser.add_argument("--rapidapi", action="store_true",
                        help="Use RapidAPI adapter (requires RAPIDAPI_KEY in .env)")
    parser.add_argument("--no-save",  action="store_true",
                        help="Skip saving result to results/ folder")
    args = parser.parse_args()

    # Load application JSON
    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            app_input = json.load(fh)
    else:
        app_input = _build_demo_app()

    # Select adapter
    if args.rapidapi:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("RAPIDAPI_KEY", "")
        if not key:
            print("ERROR: RAPIDAPI_KEY not set in .env")
            sys.exit(1)
        from adapters.rapidapi_trademark import RapidApiTrademarkAdapter
        adapter = RapidApiTrademarkAdapter(rapidapi_key=key)
        print("Adapter: RapidAPI")
    elif args.live:
        from adapters.tess_live import TessLiveAdapter
        adapter = TessLiveAdapter()
        print("Adapter: USPTO Live (TESS)")
    else:
        from adapters.mock import MockConflictAdapter
        adapter = MockConflictAdapter()
        print("Adapter: Mock (no network)")

    result = run_full_pipeline(
        app_input,
        tess_adapter = adapter,
        save_result  = not args.no_save,
    )

    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    print(f"  Mark:            {result['mark_text']}")
    print(f"  Status:          {result['pipeline_status']}")
    print(f"  Structurally OK: {result['structurally_clean']}")
    print(f"  Engines run:     {result['run_engines']}")
    print(f"  Engines blocked: {result['blocked_engines']}")
    agg = result.get("aggregated_refusals") or {}
    print(f"  Any refusal:     {agg.get('any_refusal', 'N/A')}")
    if result.get("saved_to"):
        print(f"  Saved to:        {result['saved_to']}")
    print("\nFull JSON:")
    print(json.dumps(result, indent=2, default=str))

# # for first half
# # run_pipeline.py

# from core.pipeline_state import PipelineState
# from core.result_store import ResultStore
# from core.logger import setup_logger

# from pillar1.service import run_pillar1
# from pillar2.service import run_pillar2
# from pillar3.service import run_pillar3 


# logger = setup_logger()


# def run_full_pipeline(application_dict, save_result=True):

#     logger.info("Starting full trademark examination pipeline.")

#     # ─────────────────────────────────────────────
#     # PILLAR 1
#     # ─────────────────────────────────────────────
#     logger.info("Running Pillar 1 — Classification Engine.")
#     p1_output = run_pillar1(application_dict)

#     # ─────────────────────────────────────────────
#     # PILLAR 2
#     # ─────────────────────────────────────────────
#     logger.info("Running Pillar 2 — Identification Engine.")
#     p2_output = run_pillar2(application_dict, p1_output)

#     # ─────────────────────────────────────────────
#     # PILLAR 3
#     # ─────────────────────────────────────────────
#     logger.info("Running Pillar 3 — Multi-Class Engine.")
#     p3_output = run_pillar3(application_dict, p1_output, p2_output)

#     # ─────────────────────────────────────────────
#     # BUILD PIPELINE STATE
#     # ─────────────────────────────────────────────
#     state = PipelineState(
#         raw_input=application_dict,
#         pillar1_output=p1_output,
#         pillar2_output=p2_output,
#         pillar3_output=p3_output
#     )

#     logger.info(
#         f"Pipeline complete. Structural clean: {state.is_structurally_clean()}"
#     )

#     # ─────────────────────────────────────────────
#     # OPTIONAL PERSISTENCE
#     # ─────────────────────────────────────────────
#     if save_result:
#         store = ResultStore()
#         serial = application_dict.get("application_serial", "application")
#         path = store.save(state, serial)
#         logger.info(f"Pipeline result saved to {path}")

#     return state