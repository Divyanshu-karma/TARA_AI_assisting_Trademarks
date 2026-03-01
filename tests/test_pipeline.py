# tests/test_pipeline.py
"""
Test Suite — Pipeline Module
=============================
Covers:
  §1  PipelineState helpers      (10 tests)
  §2  Gate: clean state          ( 8 tests)
  §3  Gate: Pillar 1 errors      ( 6 tests)
  §4  Gate: Pillar 3 errors      ( 5 tests)
  §5  Gate: fee misalignment     ( 4 tests)
  §6  Gate: indefinite ID        ( 6 tests)
  §7  Gate: intent-to-use        ( 5 tests)
  §8  Gate: multi-class          ( 5 tests)
  §9  Gate: partial refusal      ( 4 tests)
  §10 Gate: output schema        ( 8 tests)
  §11 Runner: all gates open     (10 tests)
  §12 Runner: search blocked     ( 5 tests)
  §13 Runner: substantive blocked( 5 tests)
  §14 Runner: specimen blocked   ( 4 tests)
  §15 Full integration flow      ( 5 tests)

Run:
    cd D:\\conflict
    set PYTHONPATH=D:\\conflict
    python -m unittest tests.test_pipeline -v
"""

import sys, os, json, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline_state       import PipelineState
from pipeline.StructuralToSubstantiveGate import build_normalized_application
from pipeline.pipeline_runner  import run_second_half
from adapters.mock             import MockConflictAdapter, EmptyTessAdapter

from tests.pipeline_fixtures import (
    make_clean_state, make_p1_error_state, make_p3_noncompliant_state,
    make_fee_misaligned_state, make_indefinite_id_state,
    make_intent_to_use_state, make_multi_class_state, make_partial_refusal_state,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PipelineState helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineState(unittest.TestCase):

    def test_is_structurally_clean_true(self):
        state = make_clean_state()
        self.assertTrue(state.is_structurally_clean())

    def test_is_structurally_clean_false_p1_errors(self):
        state = make_p1_error_state()
        self.assertFalse(state.is_structurally_clean())

    def test_is_structurally_clean_false_p3_errors(self):
        state = make_p3_noncompliant_state()
        self.assertFalse(state.is_structurally_clean())

    def test_get_confirmed_classes_single(self):
        state = make_clean_state()
        classes = state.get_confirmed_classes()
        self.assertIn('029', classes)   # zero-padded string

    def test_get_confirmed_classes_multi(self):
        state = make_multi_class_state()
        classes = state.get_confirmed_classes()
        self.assertEqual(len(classes), 2)

    def test_get_partial_refusal_classes(self):
        state = make_partial_refusal_state()
        self.assertIn("030", state.get_partial_refusal_classes())

    def test_get_clean_classes_excludes_partial_refusal(self):
        state = make_partial_refusal_state()
        clean = state.get_clean_classes()
        self.assertNotIn("030", clean)

    def test_get_identification_by_class_has_segments(self):
        state = make_clean_state()
        mapping = state.get_identification_by_class()
        self.assertIn(29, mapping)
        self.assertIsInstance(mapping[29], list)

    def test_to_dict_is_serialisable(self):
        state = make_clean_state()
        json.dumps(state.to_dict())

    def test_to_dict_contains_required_keys(self):
        state = make_clean_state()
        d = state.to_dict()
        for key in ["raw_input", "pillar1_output", "pillar2_output",
                    "pillar3_output", "created_at"]:
            self.assertIn(key, d)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Gate: clean state (all gates open)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateClean(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_clean_state())

    def test_cleared_for_search_true(self):
        self.assertTrue(self.norm["cleared_for_search"])

    def test_cleared_for_substantive_true(self):
        self.assertTrue(self.norm["cleared_for_substantive"])

    def test_cleared_for_specimen_true(self):
        self.assertTrue(self.norm["cleared_for_specimen"])

    def test_no_block_reasons(self):
        self.assertEqual(self.norm["search_block_reason"],      "")
        self.assertEqual(self.norm["substantive_block_reason"], "")
        self.assertEqual(self.norm["specimen_block_reason"],    "")

    def test_mark_text_preserved(self):
        self.assertEqual(self.norm["mark_text"], "ADAMS APPLE")

    def test_goods_services_is_list(self):
        self.assertIsInstance(self.norm["goods_services"], list)
        self.assertGreater(len(self.norm["goods_services"]), 0)

    def test_event_trigger_is_first_review(self):
        self.assertEqual(self.norm["event_trigger"], "first_review")

    def test_output_is_json_serialisable(self):
        json.dumps(self.norm)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Gate: Pillar 1 errors
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatePillar1Errors(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_p1_error_state())

    def test_search_blocked(self):
        self.assertFalse(self.norm["cleared_for_search"])

    def test_substantive_blocked(self):
        self.assertFalse(self.norm["cleared_for_substantive"])

    def test_specimen_blocked(self):
        self.assertFalse(self.norm["cleared_for_specimen"])

    def test_search_block_reason_mentions_1401(self):
        self.assertIn("§1401", self.norm["search_block_reason"])

    def test_search_block_reason_mentions_error_count(self):
        reason = self.norm["search_block_reason"]
        self.assertIn("2", reason)   # 2 errors in fixture

    def test_output_serialisable(self):
        json.dumps(self.norm)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Gate: Pillar 3 non-compliant
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatePillar3NonCompliant(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_p3_noncompliant_state())

    def test_search_blocked(self):
        self.assertFalse(self.norm["cleared_for_search"])

    def test_substantive_blocked(self):
        self.assertFalse(self.norm["cleared_for_substantive"])

    def test_block_reason_mentions_1403(self):
        self.assertIn("§1403", self.norm["search_block_reason"])

    def test_is_multi_class_compliant_false(self):
        self.assertFalse(self.norm["is_multi_class_compliant"])

    def test_output_serialisable(self):
        json.dumps(self.norm)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Gate: fee misalignment
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateFeeMisaligned(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_fee_misaligned_state())

    def test_search_blocked_on_fee_misalignment(self):
        self.assertFalse(self.norm["cleared_for_search"])

    def test_block_reason_mentions_810(self):
        self.assertIn("§810", self.norm["search_block_reason"])

    def test_fee_alignment_status_misaligned(self):
        self.assertEqual(self.norm["fee_alignment_status"], "misaligned")

    def test_output_serialisable(self):
        json.dumps(self.norm)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Gate: indefinite identification
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateIndefiniteID(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_indefinite_id_state())

    def test_search_cleared_despite_indefinite_id(self):
        """§704.02 can still run — only substantive is blocked by indefinite ID."""
        self.assertTrue(self.norm["cleared_for_search"])

    def test_substantive_blocked(self):
        self.assertFalse(self.norm["cleared_for_substantive"])

    def test_specimen_blocked(self):
        self.assertFalse(self.norm["cleared_for_specimen"])

    def test_substantive_block_reason_mentions_1402(self):
        self.assertIn("§1402", self.norm["substantive_block_reason"])

    def test_specimen_block_reason_contains_substantive_reason(self):
        # Specimen inherits substantive blocks
        self.assertIn("§1402", self.norm["specimen_block_reason"])

    def test_output_serialisable(self):
        json.dumps(self.norm)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Gate: intent-to-use filing
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateIntentToUse(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_intent_to_use_state())

    def test_search_cleared(self):
        self.assertTrue(self.norm["cleared_for_search"])

    def test_substantive_cleared(self):
        self.assertTrue(self.norm["cleared_for_substantive"])

    def test_specimen_blocked_intent_to_use(self):
        """§904 does not apply to 1(b) intent-to-use filings."""
        self.assertFalse(self.norm["cleared_for_specimen"])

    def test_specimen_block_reason_mentions_filing_basis(self):
        self.assertIn("1b", self.norm["specimen_block_reason"])

    def test_output_serialisable(self):
        json.dumps(self.norm)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Gate: multi-class application
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateMultiClass(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_multi_class_state())

    def test_all_gates_open(self):
        self.assertTrue(self.norm["cleared_for_search"])
        self.assertTrue(self.norm["cleared_for_substantive"])
        self.assertTrue(self.norm["cleared_for_specimen"])

    def test_two_confirmed_classes(self):
        self.assertEqual(len(self.norm["confirmed_class_numbers"]), 2)

    def test_goods_services_has_two_entries(self):
        self.assertEqual(len(self.norm["goods_services"]), 2)

    def test_goods_services_classes_correct(self):
        classes = {gs["class"] for gs in self.norm["goods_services"]}
        self.assertIn("009", classes)
        self.assertIn("042", classes)

    def test_output_serialisable(self):
        json.dumps(self.norm)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Gate: partial refusal
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatePartialRefusal(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_partial_refusal_state())

    def test_partial_refusal_classes_populated(self):
        self.assertIn("030", self.norm["partial_refusal_classes"])

    def test_clean_classes_excludes_partial(self):
        self.assertNotIn("030", self.norm["clean_classes"])
        self.assertIn("029", self.norm["clean_classes"])

    def test_division_candidates_populated(self):
        self.assertIn("030", self.norm["division_candidates"])

    def test_all_gates_still_open(self):
        """Partial refusal doesn't block engines — just flags the class."""
        self.assertTrue(self.norm["cleared_for_search"])
        self.assertTrue(self.norm["cleared_for_substantive"])


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — Gate: output schema
# ═══════════════════════════════════════════════════════════════════════════════

class TestGateOutputSchema(unittest.TestCase):

    def setUp(self):
        self.norm = build_normalized_application(make_clean_state())

    def test_required_keys_present(self):
        required = [
            "confirmed_class_numbers", "per_class_identification",
            "is_multi_class_compliant", "partial_refusal_classes",
            "division_candidates", "fee_alignment_status",
            "clean_classes", "procedural_issues", "filing_basis",
            "application_id", "mark_text", "mark_type",
            "goods_services", "event_trigger",
            "cleared_for_search", "cleared_for_substantive", "cleared_for_specimen",
            "search_block_reason", "substantive_block_reason", "specimen_block_reason",
        ]
        for key in required:
            self.assertIn(key, self.norm, f"Missing key: {key}")

    def test_gate_flags_are_booleans(self):
        for flag in ["cleared_for_search", "cleared_for_substantive", "cleared_for_specimen"]:
            self.assertIsInstance(self.norm[flag], bool)

    def test_block_reasons_are_strings(self):
        for key in ["search_block_reason", "substantive_block_reason", "specimen_block_reason"]:
            self.assertIsInstance(self.norm[key], str)

    def test_confirmed_class_numbers_is_list(self):
        self.assertIsInstance(self.norm["confirmed_class_numbers"], list)

    def test_goods_services_entries_have_class_and_description(self):
        for gs in self.norm["goods_services"]:
            self.assertIn("class",       gs)
            self.assertIn("description", gs)

    def test_per_class_identification_is_dict(self):
        self.assertIsInstance(self.norm["per_class_identification"], dict)

    def test_filing_basis_is_string(self):
        self.assertIsInstance(self.norm["filing_basis"], str)

    def test_procedural_issues_is_list(self):
        self.assertIsInstance(self.norm["procedural_issues"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — Runner: all gates open (mock adapter)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunnerAllOpen(unittest.TestCase):

    def setUp(self):
        norm = build_normalized_application(make_clean_state())
        self.result = run_second_half(norm, tess_adapter=MockConflictAdapter())

    def test_pipeline_status_complete(self):
        self.assertEqual(self.result["pipeline_status"], "complete")

    def test_no_blocked_engines(self):
        self.assertEqual(self.result["blocked_engines"], [])

    def test_search_engine_ran(self):
        self.assertIn("§704.02", self.result["run_engines"])

    def test_1207_engine_ran(self):
        self.assertIn("§1207", self.result["run_engines"])

    def test_1209_engine_ran(self):
        self.assertIn("§1209", self.result["run_engines"])

    def test_specimen_stub_ran(self):
        self.assertIn("§904 (stub)", self.result["run_engines"])

    def test_search_result_present(self):
        self.assertIsNotNone(self.result["search_result"])

    def test_similarity_result_present(self):
        self.assertIsNotNone(self.result["similarity_result"])

    def test_descriptiveness_result_present(self):
        self.assertIsNotNone(self.result["descriptiveness_result"])

    def test_output_is_json_serialisable(self):
        json.dumps(self.result)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — Runner: search blocked
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunnerSearchBlocked(unittest.TestCase):

    def setUp(self):
        norm = build_normalized_application(make_p1_error_state())
        self.result = run_second_half(norm, tess_adapter=MockConflictAdapter())

    def test_pipeline_status_blocked_at_search(self):
        self.assertEqual(self.result["pipeline_status"], "blocked_at_search_gate")

    def test_search_not_in_run_engines(self):
        self.assertNotIn("§704.02", self.result["run_engines"])

    def test_all_engines_blocked(self):
        blocked = self.result["blocked_engines"]
        for eng in ["§704.02", "§1207", "§1209", "§904"]:
            self.assertIn(eng, blocked)

    def test_search_result_is_none(self):
        self.assertIsNone(self.result["search_result"])

    def test_output_is_json_serialisable(self):
        json.dumps(self.result)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — Runner: substantive blocked
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunnerSubstantiveBlocked(unittest.TestCase):

    def setUp(self):
        norm = build_normalized_application(make_indefinite_id_state())
        self.result = run_second_half(norm, tess_adapter=MockConflictAdapter())

    def test_pipeline_status_blocked_at_substantive(self):
        self.assertEqual(self.result["pipeline_status"], "blocked_at_substantive_gate")

    def test_search_did_run(self):
        self.assertIn("§704.02", self.result["run_engines"])

    def test_1207_blocked(self):
        self.assertIn("§1207", self.result["blocked_engines"])

    def test_1209_blocked(self):
        self.assertIn("§1209", self.result["blocked_engines"])

    def test_similarity_result_is_none(self):
        self.assertIsNone(self.result["similarity_result"])


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — Runner: specimen blocked (intent-to-use)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunnerSpecimenBlocked(unittest.TestCase):

    def setUp(self):
        norm = build_normalized_application(make_intent_to_use_state())
        self.result = run_second_half(norm, tess_adapter=MockConflictAdapter())

    def test_search_ran(self):
        self.assertIn("§704.02", self.result["run_engines"])

    def test_substantive_ran(self):
        self.assertIn("§1207", self.result["run_engines"])
        self.assertIn("§1209", self.result["run_engines"])

    def test_specimen_blocked(self):
        self.assertIn("§904", self.result["blocked_engines"])

    def test_specimen_result_is_none(self):
        self.assertIsNone(self.result["specimen_result"])


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 15 — Full integration flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullIntegration(unittest.TestCase):

    def test_clean_state_end_to_end(self):
        """PipelineState → gate → runner → aggregated result."""
        state  = make_clean_state()
        norm   = build_normalized_application(state)
        result = run_second_half(norm, tess_adapter=MockConflictAdapter())

        self.assertIsNotNone(result["search_result"])
        self.assertIsNotNone(result["similarity_result"])
        self.assertIsNotNone(result["descriptiveness_result"])
        self.assertIsNotNone(result["aggregated_refusals"])
        self.assertEqual(result["pipeline_status"], "complete")
        json.dumps(result)

    def test_aggregated_refusals_per_class_structure(self):
        """Aggregator (stub) returns per-class refusal flags."""
        state  = make_clean_state()
        norm   = build_normalized_application(state)
        result = run_second_half(norm, tess_adapter=MockConflictAdapter())

        agg = result["aggregated_refusals"]
        self.assertIn("per_class_refusals", agg)
        for cls_data in agg["per_class_refusals"].values():
            for field in ["procedural_error", "classification_error",
                          "identification_error", "likelihood_of_confusion",
                          "descriptiveness", "specimen_error", "overall_refusal"]:
                self.assertIn(field, cls_data)

    def test_gate_status_in_runner_output(self):
        """Runner output always includes gate_status from the image's Legal Alignment table."""
        state  = make_clean_state()
        norm   = build_normalized_application(state)
        result = run_second_half(norm, tess_adapter=MockConflictAdapter())

        gs = result["gate_status"]
        self.assertIn("search",      gs)
        self.assertIn("substantive", gs)
        self.assertIn("specimen",    gs)
        self.assertIn("procedural",  gs)
        self.assertEqual(gs["search"]["legal_authority"],      "§704.02")
        self.assertEqual(gs["substantive"]["legal_authority"], "§1207 / §1209")
        self.assertEqual(gs["specimen"]["legal_authority"],    "§904")
        self.assertEqual(gs["procedural"]["legal_authority"],  "§800")

    def test_no_search_on_unstable_scope(self):
        """Core rule from image: No search on unstable scope."""
        state  = make_p3_noncompliant_state()
        norm   = build_normalized_application(state)
        result = run_second_half(norm, tess_adapter=MockConflictAdapter())
        self.assertIsNone(result["search_result"])

    def test_no_substantive_on_indefinite_id(self):
        """Core rule from image: No substantive analysis on indefinite ID."""
        state  = make_indefinite_id_state()
        norm   = build_normalized_application(state)
        result = run_second_half(norm, tess_adapter=MockConflictAdapter())
        self.assertIsNone(result["similarity_result"])
        self.assertIsNone(result["descriptiveness_result"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
