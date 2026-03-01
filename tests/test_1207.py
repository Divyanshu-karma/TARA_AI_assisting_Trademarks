# tests/test_1207.py
"""
Test Suite — TMEP §1207 Similarity Engine
==========================================
Covers:
  - Factor 1: Mark similarity (visual, phonetic, meaning)
  - Factor 2: Goods/services relatedness
  - Factor 3: Trade channels
  - Factor 4: Purchase conditions
  - DuPont engine: weighted scoring + decision
  - §1207.02: Deception analysis
  - §1207.03: Unregistered prior use
  - §1207.04: Concurrent use
  - similarity_engine: full output schema
  - Full pipeline: §704.02 → §1207 end-to-end

Run:
    cd D:\\conflict
    set PYTHONPATH=D:\\conflict
    python -m unittest tests.test_1207 -v
"""

import sys, os, json, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from similarity.factor1_mark_similarity    import score_factor1
from similarity.factor2_goods_relatedness  import score_factor2
from similarity.factor3_trade_channels     import score_factor3
from similarity.factor4_purchase_conditions import score_factor4
from similarity.dupont_engine              import analyse_conflict, serialise_analysis
from similarity.section_1207_subsections   import (
    analyse_1207_02, analyse_1207_03, analyse_1207_04
)
from similarity.similarity_engine          import conduct_tmep_1207_analysis
from similarity.models                     import ConfusionLikelihood, DeceptionType

from core.search_engine  import conduct_tmep_704_02_search
from adapters.mock       import MockConflictAdapter, EmptyTessAdapter


# ──────────────────────────────────────────────────────────────────────────────
# SHARED FIXTURES
# ──────────────────────────────────────────────────────────────────────────────

BASE_APP = {
    "application_id":  "123456789",
    "mark_text":       "ADAMS APPLE",
    "mark_type":       "standard_character",
    "goods_services":  [{"class": "029", "description": "Dried fruits and vegetables"}],
    "event_trigger":   "first_review",
}

IDENTICAL_CONFLICT = {
    "application_number": "987654321",
    "mark_text":          "ADAMS APPLE",
    "status":             "registered",
    "ic_classes":         ["029"],
    "owner_name":         "Test Corp",
    "filing_date":        "2018-01-01",
    "registration_date":  "2019-01-01",
    "surfaced_by":        "exact",
}

DIFFERENT_CONFLICT = {
    "application_number": "111222333",
    "mark_text":          "ZENITH CLOUD",
    "status":             "registered",
    "ic_classes":         ["042"],
    "owner_name":         "Other Corp",
    "filing_date":        "2019-01-01",
    "registration_date":  "2020-01-01",
    "surfaced_by":        "dominant",
}

DEAD_CONFLICT = {
    "application_number": "555666777",
    "mark_text":          "ADAMS APPLE CIDER",
    "status":             "abandoned",
    "ic_classes":         ["029"],
    "owner_name":         "Old Corp",
    "filing_date":        "2010-01-01",
    "registration_date":  "",
    "surfaced_by":        "exact",
}


def _make_704_result(conflicts: list[dict]) -> dict:
    """Build a minimal §704.02-style result for §1207 testing."""
    return {
        "authority_reference": "TMEP §704.02",
        "search_conducted":    True,
        "applied_for_mark": {
            "mark_text":      "ADAMS APPLE",
            "mark_type":      "standard_character",
            "ic_classes":     ["029"],
            "goods_services": [{"class": "029", "description": "Dried fruits"}],
        },
        "conflict_set":              conflicts,
        "results_summary": {
            "total_conflicts_found":           len(conflicts),
            "conflicting_application_numbers": [c["application_number"] for c in conflicts],
        },
        "goods_services_analysis": {"class_overlap_detected": True, "factor2_input_ready": True},
        "preliminary_flag":        {"risk_level": "HIGH"},
        "refusal_flag":            {"refusal_possible": True, "pending_1207_analysis": True},
        "re_search_required":      False,
        "compliance_status":       "Search complete.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — FACTOR 1: MARK SIMILARITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactor1MarkSimilarity(unittest.TestCase):

    def test_identical_marks_score_near_1(self):
        s = score_factor1("ADAMS APPLE", "ADAMS APPLE")
        self.assertGreaterEqual(s.composite_score, 0.95)

    def test_completely_different_marks_score_low(self):
        s = score_factor1("ADAMS APPLE", "ZENITH CLOUD")
        self.assertLess(s.composite_score, 0.45)

    def test_phonetic_variant_scores_high(self):
        # "ADAMZ APPEL" is visually + phonetically close to "ADAMS APPLE"
        # Composite > 0.55 is realistic for a misspelled variant
        s = score_factor1("ADAMS APPLE", "ADAMZ APPEL")
        self.assertGreater(s.composite_score, 0.55)

    def test_dominant_word_match_detected(self):
        s = score_factor1("ADAMS FRUIT", "ADAMS BERRY")
        self.assertTrue(s.dominant_word_match)

    def test_no_dominant_match_different_first_word(self):
        s = score_factor1("GOLDEN APPLE", "SILVER APPLE")
        self.assertFalse(s.dominant_word_match)

    def test_visual_similarity_field_present(self):
        s = score_factor1("APPLE", "APPL")
        self.assertIsInstance(s.visual_similarity, float)
        self.assertGreater(s.visual_similarity, 0.70)

    def test_phonetic_similarity_field_present(self):
        s = score_factor1("SMITH", "SMYTH")
        self.assertIsInstance(s.phonetic_similarity, float)
        self.assertGreater(s.phonetic_similarity, 0.50)

    def test_meaning_similarity_field_present(self):
        s = score_factor1("ADAMS APPLE", "ADAMS APPLE JUICE")
        self.assertIsInstance(s.meaning_similarity, float)

    def test_scores_are_between_0_and_1(self):
        s = score_factor1("BRAND X", "BRAND Z")
        for val in [s.visual_similarity, s.phonetic_similarity,
                    s.meaning_similarity, s.composite_score]:
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)

    def test_notes_is_string(self):
        s = score_factor1("TEST MARK", "TEST BRAND")
        self.assertIsInstance(s.notes, str)
        self.assertGreater(len(s.notes), 0)

    def test_empty_mark_returns_gracefully(self):
        s = score_factor1("", "ADAMS APPLE")
        self.assertEqual(s.composite_score, 0.0)

    def test_single_word_marks(self):
        # "APPLE" vs "APPEL" — visually close, phonetically identical Soundex
        s = score_factor1("APPLE", "APPEL")
        self.assertGreater(s.composite_score, 0.40)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — FACTOR 2: GOODS RELATEDNESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactor2GoodsRelatedness(unittest.TestCase):

    def test_same_class_scores_1(self):
        s = score_factor2(["029"], ["029"])
        self.assertEqual(s.composite_score, 1.0)
        self.assertTrue(s.same_class)

    def test_adjacent_classes_score_mid(self):
        s = score_factor2(["029"], ["030"])   # food / baked goods
        self.assertTrue(s.adjacent_class)
        self.assertGreaterEqual(s.composite_score, 0.60)

    def test_unrelated_classes_score_low(self):
        s = score_factor2(["029"], ["042"])   # food / software
        self.assertFalse(s.same_class)
        self.assertFalse(s.adjacent_class)
        self.assertLess(s.composite_score, 0.35)

    def test_description_overlap_boosts_score(self):
        s_no_desc   = score_factor2(["029"], ["030"])
        s_with_desc = score_factor2(
            ["029"], ["030"],
            "dried fruit", "fruit preserves"
        )
        self.assertGreaterEqual(s_with_desc.composite_score, s_no_desc.composite_score)

    def test_multiple_classes_same(self):
        s = score_factor2(["029", "030"], ["029", "031"])
        self.assertTrue(s.same_class)

    def test_composite_score_between_0_and_1(self):
        for ca, cb in [("029", "029"), ("029", "030"), ("029", "042"), ("009", "045")]:
            s = score_factor2([ca], [cb])
            self.assertGreaterEqual(s.composite_score, 0.0)
            self.assertLessEqual(s.composite_score, 1.0)

    def test_notes_present(self):
        s = score_factor2(["029"], ["029"])
        self.assertIn("029", s.notes)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — FACTOR 3: TRADE CHANNELS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactor3TradeChannels(unittest.TestCase):

    def test_same_class_presumed_same_channels(self):
        s = score_factor3(["029"], ["029"])
        self.assertTrue(s.same_channels)
        self.assertGreaterEqual(s.composite_score, 0.85)

    def test_both_mass_market_overlapping(self):
        s = score_factor3(["029"], ["030"])
        self.assertTrue(s.overlapping_channels)

    def test_different_channel_types_low_score(self):
        s = score_factor3(["010"], ["029"])  # medical vs food
        self.assertLess(s.composite_score, 0.60)

    def test_score_between_0_and_1(self):
        s = score_factor3(["042"], ["009"])
        self.assertGreaterEqual(s.composite_score, 0.0)
        self.assertLessEqual(s.composite_score, 1.0)

    def test_both_service_classes_overlap(self):
        s = score_factor3(["035"], ["036"])
        self.assertTrue(s.overlapping_channels)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — FACTOR 4: PURCHASE CONDITIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactor4PurchaseConditions(unittest.TestCase):

    def test_food_class_ordinary_buyer_high_score(self):
        s = score_factor4(["029"])
        self.assertEqual(s.buyer_sophistication, "ordinary")
        self.assertTrue(s.impulse_purchase)
        self.assertGreater(s.composite_score, 0.70)

    def test_medical_devices_expert_buyer_low_score(self):
        s = score_factor4(["010"])
        self.assertEqual(s.buyer_sophistication, "expert")
        self.assertFalse(s.impulse_purchase)
        self.assertLess(s.composite_score, 0.30)

    def test_financial_services_sophisticated_buyer(self):
        s = score_factor4(["036"])
        self.assertEqual(s.buyer_sophistication, "sophisticated")

    def test_empty_classes_defaults_to_ordinary(self):
        s = score_factor4([])
        self.assertEqual(s.buyer_sophistication, "ordinary")

    def test_score_between_0_and_1(self):
        for cls in ["029", "010", "036", "042", "025"]:
            s = score_factor4([cls])
            self.assertGreaterEqual(s.composite_score, 0.0)
            self.assertLessEqual(s.composite_score, 1.0)

    def test_notes_is_string(self):
        s = score_factor4(["029"])
        self.assertIsInstance(s.notes, str)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — DUPONT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDuPontEngine(unittest.TestCase):

    def test_identical_mark_same_class_refusal_recommended(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        self.assertTrue(ca.refusal_recommended)
        self.assertTrue(ca.confusion_likely)
        self.assertEqual(ca.confusion_likelihood, ConfusionLikelihood.LIKELY)

    def test_completely_different_mark_no_refusal(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", DIFFERENT_CONFLICT)
        self.assertFalse(ca.refusal_recommended)
        self.assertFalse(ca.confusion_likely)

    def test_weighted_score_between_0_and_1(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        s  = ca.dupont_scores.weighted_final_score
        self.assertGreaterEqual(s, 0.0)
        self.assertLessEqual(s, 1.0)

    def test_high_score_for_identical_mark(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        self.assertGreater(ca.dupont_scores.weighted_final_score, 0.75)

    def test_low_score_for_different_mark(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", DIFFERENT_CONFLICT)
        self.assertLess(ca.dupont_scores.weighted_final_score, 0.50)

    def test_dominant_factor_is_string(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        self.assertIsInstance(ca.dominant_factor, str)
        self.assertIn("factor", ca.dominant_factor)

    def test_legal_basis_present_when_refusal(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        self.assertIn("§2(d)", ca.legal_basis)

    def test_legal_basis_empty_when_no_refusal(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", DIFFERENT_CONFLICT)
        self.assertEqual(ca.legal_basis, "")

    def test_serialise_produces_dict(self):
        ca   = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        data = serialise_analysis(ca)
        self.assertIsInstance(data, dict)
        self.assertIn("dupont_scores",       data)
        self.assertIn("confusion_likely",    data)
        self.assertIn("refusal_recommended", data)

    def test_serialise_is_json_serialisable(self):
        ca   = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        data = serialise_analysis(ca)
        json.dumps(data)   # must not raise

    def test_all_four_factors_in_serialised_output(self):
        ca   = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        data = serialise_analysis(ca)
        scores = data["dupont_scores"]
        for key in ["factor1_mark_similarity", "factor2_goods_relatedness",
                    "factor3_trade_channels", "factor4_purchase_conditions",
                    "weighted_final_score"]:
            self.assertIn(key, scores)

    def test_confusion_likelihood_values(self):
        ca = analyse_conflict("ADAMS APPLE", ["029"], "Dried fruits", IDENTICAL_CONFLICT)
        self.assertIn(ca.confusion_likelihood.value, ["LIKELY", "POSSIBLE", "UNLIKELY"])


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — §1207.02 DECEPTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSection1207_02(unittest.TestCase):

    def test_geographic_deception_detected(self):
        """Mark says PARIS but goods have no Paris connection."""
        result = analyse_1207_02("PARIS PERFUME", "synthetic fragrance", ["003"])
        self.assertTrue(result.deception_detected)
        self.assertEqual(result.deception_type, DeceptionType.GEOGRAPHIC)
        self.assertTrue(result.refusal_recommended)
        self.assertIn("§2(a)", result.legal_basis)

    def test_genuine_geographic_no_deception(self):
        """Mark says SWISS but description confirms Swiss origin."""
        result = analyse_1207_02("SWISS CHEESE", "genuine swiss cheese made in switzerland", ["029"])
        self.assertFalse(result.deception_detected)

    def test_material_deception_detected(self):
        """Mark says GOLD but goods are not gold."""
        result = analyse_1207_02("GOLD RING", "fashion jewelry plastic", ["014"])
        self.assertTrue(result.deception_detected)
        self.assertTrue(result.refusal_recommended)

    def test_genuine_material_no_deception(self):
        """Mark says SILK but goods description confirms silk."""
        result = analyse_1207_02("SILK TOUCH", "silk fabric garments", ["024"])
        self.assertFalse(result.deception_detected)

    def test_clean_mark_no_deception(self):
        result = analyse_1207_02("ADAMS APPLE", "dried fruits", ["029"])
        self.assertFalse(result.deception_detected)
        self.assertFalse(result.refusal_recommended)

    def test_notes_is_string(self):
        result = analyse_1207_02("ADAMS APPLE", "dried fruits", ["029"])
        self.assertIsInstance(result.notes, str)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — §1207.03 UNREGISTERED PRIOR USE
# ═══════════════════════════════════════════════════════════════════════════════

class TestSection1207_03(unittest.TestCase):

    def test_dead_same_class_conflict_detected(self):
        result = analyse_1207_03([DEAD_CONFLICT], ["029"])
        self.assertTrue(result.prior_use_detected)
        self.assertTrue(result.conflict_with_applied)
        self.assertTrue(result.refusal_recommended)
        self.assertIn("§2(d)", result.legal_basis)

    def test_registered_conflict_not_flagged(self):
        """Registered marks are handled by §1207.01 — not §1207.03."""
        result = analyse_1207_03([IDENTICAL_CONFLICT], ["029"])
        self.assertFalse(result.prior_use_detected)

    def test_dead_different_class_not_flagged(self):
        dead_diff_class = dict(DEAD_CONFLICT)
        dead_diff_class["ic_classes"] = ["042"]
        result = analyse_1207_03([dead_diff_class], ["029"])
        self.assertFalse(result.prior_use_detected)

    def test_empty_conflict_set_no_prior_use(self):
        result = analyse_1207_03([], ["029"])
        self.assertFalse(result.prior_use_detected)
        self.assertFalse(result.refusal_recommended)

    def test_notes_is_string(self):
        result = analyse_1207_03([DEAD_CONFLICT], ["029"])
        self.assertIsInstance(result.notes, str)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — §1207.04 CONCURRENT USE
# ═══════════════════════════════════════════════════════════════════════════════

class TestSection1207_04(unittest.TestCase):

    def test_no_conflicts_not_applicable(self):
        from similarity.models import ConcurrentUseType
        result = analyse_1207_04("ADAMS APPLE", ["029"], [])
        self.assertFalse(result.concurrent_use_possible)
        self.assertEqual(result.use_type, ConcurrentUseType.NOT_APPLICABLE)

    def test_nationwide_use_overlap_detected(self):
        result = analyse_1207_04(
            "ADAMS APPLE", ["029"], [IDENTICAL_CONFLICT],
            geographic_area_applied="United States"
        )
        self.assertTrue(result.areas_overlap)

    def test_regional_use_possible_concurrent(self):
        result = analyse_1207_04(
            "ADAMS APPLE", ["029"], [IDENTICAL_CONFLICT],
            geographic_area_applied="Northeast United States"
        )
        # Not full US → concurrent use may be possible
        self.assertTrue(result.concurrent_use_possible)

    def test_notes_is_string(self):
        result = analyse_1207_04("ADAMS APPLE", ["029"], [IDENTICAL_CONFLICT])
        self.assertIsInstance(result.notes, str)
        self.assertGreater(len(result.notes), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — SIMILARITY ENGINE OUTPUT SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimilarityEngineOutput(unittest.TestCase):

    def setUp(self):
        self.input = _make_704_result([IDENTICAL_CONFLICT])
        self.result = conduct_tmep_1207_analysis(self.input)

    def test_authority_reference(self):
        self.assertEqual(self.result["authority_reference"], "TMEP §1207.01")

    def test_applied_for_mark_present(self):
        self.assertEqual(self.result["applied_for_mark"], "ADAMS APPLE")

    def test_conflicts_analysed_count(self):
        self.assertEqual(self.result["conflicts_analysed"], 1)

    def test_timestamp_present(self):
        self.assertIn("analysis_timestamp", self.result)
        self.assertTrue(self.result["analysis_timestamp"].endswith("Z"))

    def test_section_1207_01_present(self):
        self.assertIn("section_1207_01", self.result)
        s = self.result["section_1207_01"]
        self.assertIn("dupont_analyses", s)
        self.assertIn("total_refusals_found", s)

    def test_section_1207_02_present(self):
        self.assertIn("section_1207_02", self.result)
        s = self.result["section_1207_02"]
        self.assertIn("deception_detected", s)
        self.assertIn("refusal_recommended", s)

    def test_section_1207_03_present(self):
        self.assertIn("section_1207_03", self.result)
        s = self.result["section_1207_03"]
        self.assertIn("prior_use_detected", s)

    def test_section_1207_04_present(self):
        self.assertIn("section_1207_04", self.result)
        s = self.result["section_1207_04"]
        self.assertIn("concurrent_use_possible", s)

    def test_overall_refusal_recommended_is_bool(self):
        self.assertIsInstance(self.result["overall_refusal_recommended"], bool)

    def test_overall_confusion_likely_is_bool(self):
        self.assertIsInstance(self.result["overall_confusion_likely"], bool)

    def test_section_2d_applicable_is_bool(self):
        self.assertIsInstance(self.result["section_2d_applicable"], bool)

    def test_highest_dupont_score_is_float(self):
        self.assertIsInstance(self.result["highest_dupont_score"], float)

    def test_compliance_status_is_string(self):
        self.assertIsInstance(self.result["compliance_status"], str)

    def test_output_is_json_serialisable(self):
        json.dumps(self.result)

    def test_identical_conflict_triggers_refusal(self):
        self.assertTrue(self.result["overall_refusal_recommended"])
        self.assertTrue(self.result["section_2d_applicable"])

    def test_no_conflicts_no_refusal(self):
        result = conduct_tmep_1207_analysis(_make_704_result([]))
        self.assertFalse(result["overall_refusal_recommended"])
        self.assertFalse(result["overall_confusion_likely"])

    def test_raises_without_applied_for_mark(self):
        bad = _make_704_result([])
        del bad["applied_for_mark"]
        with self.assertRaises(ValueError):
            conduct_tmep_1207_analysis(bad)

    def test_raises_without_conflict_set(self):
        bad = _make_704_result([])
        del bad["conflict_set"]
        with self.assertRaises(ValueError):
            conduct_tmep_1207_analysis(bad)

    def test_dupont_analyses_list_correct_length(self):
        result = conduct_tmep_1207_analysis(_make_704_result([IDENTICAL_CONFLICT, DIFFERENT_CONFLICT]))
        self.assertEqual(len(result["section_1207_01"]["dupont_analyses"]), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — FULL PIPELINE §704.02 → §1207
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullPipeline(unittest.TestCase):
    """End-to-end: §704.02 search → §1207 analysis in one flow."""

    def test_pipeline_with_mock_conflicts(self):
        """MockConflictAdapter returns 3 conflicts → §1207 analyses all 3."""
        search = conduct_tmep_704_02_search(BASE_APP, tess_adapter=MockConflictAdapter())
        result = conduct_tmep_1207_analysis(search)

        self.assertEqual(result["authority_reference"], "TMEP §1207.01")
        self.assertEqual(result["conflicts_analysed"], 3)
        self.assertIsInstance(result["overall_refusal_recommended"], bool)
        self.assertIsInstance(result["overall_confusion_likely"], bool)
        json.dumps(result)   # full output must be JSON-serialisable

    def test_pipeline_with_empty_conflicts(self):
        """No conflicts → no refusal, cleared for approval."""
        search = conduct_tmep_704_02_search(BASE_APP, tess_adapter=EmptyTessAdapter())
        result = conduct_tmep_1207_analysis(search)

        self.assertFalse(result["overall_refusal_recommended"])
        self.assertFalse(result["overall_confusion_likely"])
        self.assertIn("cleared for approval", result["compliance_status"].lower())

    def test_pipeline_output_has_all_sections(self):
        search = conduct_tmep_704_02_search(BASE_APP, tess_adapter=MockConflictAdapter())
        result = conduct_tmep_1207_analysis(search)

        for section in ["section_1207_01", "section_1207_02",
                        "section_1207_03", "section_1207_04"]:
            self.assertIn(section, result, f"Missing {section} in pipeline output")

    def test_pipeline_dupont_scores_present_per_conflict(self):
        search = conduct_tmep_704_02_search(BASE_APP, tess_adapter=MockConflictAdapter())
        result = conduct_tmep_1207_analysis(search)

        analyses = result["section_1207_01"]["dupont_analyses"]
        self.assertEqual(len(analyses), 3)
        for a in analyses:
            self.assertIn("dupont_scores", a)
            self.assertIn("weighted_final_score", a["dupont_scores"])
            self.assertIn("confusion_likely", a)
            self.assertIn("refusal_recommended", a)

    def test_pipeline_revival_trigger(self):
        """Revival trigger sets re_search_required — §1207 should still work."""
        app = dict(BASE_APP)
        app["event_trigger"] = "revival"
        search = conduct_tmep_704_02_search(app, tess_adapter=MockConflictAdapter())
        self.assertTrue(search["re_search_required"])
        result = conduct_tmep_1207_analysis(search)
        self.assertEqual(result["conflicts_analysed"], 3)

    def test_pipeline_json_fully_serialisable(self):
        search = conduct_tmep_704_02_search(BASE_APP, tess_adapter=MockConflictAdapter())
        result = conduct_tmep_1207_analysis(search)
        # Both §704.02 and §1207 outputs must be serialisable
        json.dumps(search)
        json.dumps(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
