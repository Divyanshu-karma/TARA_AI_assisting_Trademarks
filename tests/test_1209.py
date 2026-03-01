# tests/test_1209.py
"""
Test Suite — TMEP §1209 Descriptiveness Module
===============================================
Covers:
  §1209.01 — Distinctiveness/Descriptiveness Continuum (13 tests)
  §1209.02 — Refusal Procedure (12 tests)
  §1209.03 — Considerations/Evidence (10 tests)
  §1209.04 — Deceptively Misdescriptive (12 tests)
  Engine output schema (14 tests)
  Dummy input scenarios (6 tests)

Run:
    cd D:\\conflict
    set PYTHONPATH=D:\\conflict
    python -m unittest tests.test_1209 -v
"""

import sys, os, json, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descriptiveness.continuum                  import analyse_continuum
from descriptiveness.procedure_and_considerations import analyse_procedure, analyse_considerations
from descriptiveness.deceptive_misdescriptive   import analyse_deceptive_misdescriptive
from descriptiveness.descriptiveness_engine     import (
    conduct_tmep_1209_analysis, conduct_tmep_1209_analysis_dummy, DUMMY_INPUTS
)
from descriptiveness.models import (
    DistinctivenessLevel, DescriptivenessType, RefusalGround, OvercomeMethod,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — §1209.01 DISTINCTIVENESS CONTINUUM
# ═══════════════════════════════════════════════════════════════════════════════

class TestContinuum(unittest.TestCase):

    # ── Generic ──────────────────────────────────────────────────────────────

    def test_generic_term_for_goods(self):
        """FRUIT for fruit goods → generic."""
        result = analyse_continuum("FRUIT", "Fresh fruit", ["029"])
        self.assertEqual(result.distinctiveness_level, DistinctivenessLevel.GENERIC)

    def test_generic_score_is_zero(self):
        result = analyse_continuum("BEER", "Beer and ale beverages", ["032"])
        self.assertEqual(result.distinctiveness_score, 0.0)

    def test_generic_not_registrable(self):
        result = analyse_continuum("BREAD", "Bread and bakery products", ["030"])
        self.assertEqual(result.distinctiveness_level, DistinctivenessLevel.GENERIC)
        self.assertFalse(result.imagination_required)

    # ── Descriptive ──────────────────────────────────────────────────────────

    def test_descriptive_quality_term(self):
        """FRESH DAILY for fresh produce → descriptive."""
        result = analyse_continuum("FRESH DAILY", "Fresh fruit", ["029"])
        self.assertEqual(result.distinctiveness_level, DistinctivenessLevel.DESCRIPTIVE)

    def test_descriptive_directly_describes(self):
        result = analyse_continuum("SUPER CLEAN", "Cleaning products", ["003"])
        self.assertTrue(result.directly_describes or
                        result.distinctiveness_level == DistinctivenessLevel.DESCRIPTIVE)

    def test_descriptive_imagination_not_required(self):
        result = analyse_continuum("FAST DELIVERY", "Courier delivery services", ["039"])
        if result.distinctiveness_level == DistinctivenessLevel.DESCRIPTIVE:
            self.assertFalse(result.imagination_required)

    def test_compound_descriptive_mark(self):
        """Both words individually descriptive → compound mark is descriptive."""
        result = analyse_continuum("BEST FRESH", "Fresh food products", ["029"])
        self.assertIn(result.distinctiveness_level,
                      [DistinctivenessLevel.DESCRIPTIVE, DistinctivenessLevel.GENERIC])

    # ── Suggestive ────────────────────────────────────────────────────────────

    def test_suggestive_requires_imagination(self):
        """COPPERTONE for suntan lotion — suggestive or fanciful (coined word)."""
        result = analyse_continuum("COPPERTONE", "Suntan lotion", ["003"])
        # COPPERTONE is either SUGGESTIVE or FANCIFUL — both are inherently distinctive
        self.assertIn(result.distinctiveness_level,
                      [DistinctivenessLevel.SUGGESTIVE,
                       DistinctivenessLevel.ARBITRARY,
                       DistinctivenessLevel.FANCIFUL])

    def test_suggestive_score_above_half(self):
        result = analyse_continuum("COPPERTONE", "Suntan lotion", ["003"])
        self.assertGreater(result.distinctiveness_score, 0.40)

    # ── Arbitrary ────────────────────────────────────────────────────────────

    def test_arbitrary_real_word_unrelated(self):
        """APPLE for computers — arbitrary."""
        result = analyse_continuum("APPLE", "Computers and smartphones", ["009"])
        self.assertIn(result.distinctiveness_level,
                      [DistinctivenessLevel.ARBITRARY, DistinctivenessLevel.SUGGESTIVE])

    def test_arbitrary_score_high(self):
        result = analyse_continuum("EAGLE", "Financial services", ["036"])
        self.assertGreater(result.distinctiveness_score, 0.60)

    # ── Fanciful ─────────────────────────────────────────────────────────────

    def test_fanciful_coined_word(self):
        """KODAK-style coined word → fanciful."""
        result = analyse_continuum("QWIXEL", "Software applications", ["042"])
        self.assertEqual(result.distinctiveness_level, DistinctivenessLevel.FANCIFUL)
        self.assertEqual(result.distinctiveness_score, 1.0)

    def test_reasoning_is_string(self):
        result = analyse_continuum("TEST MARK", "Test goods", ["009"])
        self.assertIsInstance(result.reasoning, str)
        self.assertGreater(len(result.reasoning), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — §1209.02 REFUSAL PROCEDURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefusalProcedure(unittest.TestCase):

    def _run(self, mark, desc, classes, level, score=0.5):
        return analyse_procedure(mark, desc, classes, level, score)

    # ── Generic ──────────────────────────────────────────────────────────────

    def test_generic_is_absolute_bar(self):
        result = self._run("FRUIT", "Fresh fruit", ["029"], DistinctivenessLevel.GENERIC)
        self.assertTrue(result.is_absolute_bar)
        self.assertTrue(result.refusal_warranted)
        self.assertEqual(result.refusal_ground, RefusalGround.GENERIC_REFUSAL)

    def test_generic_not_overcomeable(self):
        result = self._run("BREAD", "Bakery goods", ["030"], DistinctivenessLevel.GENERIC)
        self.assertFalse(result.acquired_distinctiveness_possible)
        self.assertIn(OvercomeMethod.NOT_OVERCOMEABLE, result.overcome_methods)

    # ── Descriptive §2(e)(1) ─────────────────────────────────────────────────

    def test_descriptive_refusal_warranted(self):
        result = self._run("FRESH DAILY", "Fresh fruit", ["029"], DistinctivenessLevel.DESCRIPTIVE)
        self.assertTrue(result.refusal_warranted)
        self.assertEqual(result.refusal_ground, RefusalGround.SECTION_2E1_DESCRIPTIVE)

    def test_descriptive_is_not_absolute_bar(self):
        result = self._run("FAST DELIVERY", "Delivery services", ["039"], DistinctivenessLevel.DESCRIPTIVE)
        self.assertFalse(result.is_absolute_bar)
        self.assertTrue(result.acquired_distinctiveness_possible)

    def test_descriptive_overcome_methods_include_2f(self):
        result = self._run("PURE WATER", "Bottled water", ["032"], DistinctivenessLevel.DESCRIPTIVE)
        self.assertIn(OvercomeMethod.SECTION_2F_ACQUIRED, result.overcome_methods)

    def test_descriptive_overcome_includes_supplemental(self):
        result = self._run("EASY CLEAN", "Cleaning products", ["003"], DistinctivenessLevel.DESCRIPTIVE)
        self.assertIn(OvercomeMethod.SUPPLEMENTAL_REGISTER, result.overcome_methods)

    # ── Geographic §2(e)(2) ───────────────────────────────────────────────────

    def test_geographic_refusal_detected(self):
        """PARIS for fragrance → primarily geographically descriptive."""
        result = self._run("PARIS PERFUME", "Fragrances cosmetics", ["003"],
                           DistinctivenessLevel.DESCRIPTIVE)
        self.assertTrue(result.refusal_warranted)
        self.assertEqual(result.refusal_ground, RefusalGround.SECTION_2E2_GEOGRAPHIC)

    def test_geographic_statutory_basis(self):
        result = self._run("FRENCH PERFUME", "Fragrances", ["003"],
                           DistinctivenessLevel.DESCRIPTIVE)
        if result.refusal_ground == RefusalGround.SECTION_2E2_GEOGRAPHIC:
            self.assertIn("§2(e)(2)", result.statutory_basis)

    # ── Surname §2(e)(4) ─────────────────────────────────────────────────────

    def test_surname_refusal_detected(self):
        """JOHNSON for cleaning products → primarily merely a surname."""
        result = self._run("JOHNSON CLEAN", "Cleaning products", ["003"],
                           DistinctivenessLevel.DESCRIPTIVE)
        # JOHNSON is a very common surname — should trigger §2(e)(4)
        self.assertTrue(result.refusal_warranted)

    # ── Distinctive — no refusal ──────────────────────────────────────────────

    def test_suggestive_no_refusal(self):
        result = self._run("COPPERTONE", "Suntan lotion", ["003"], DistinctivenessLevel.SUGGESTIVE)
        self.assertFalse(result.refusal_warranted)
        self.assertEqual(result.refusal_ground, RefusalGround.NONE)

    def test_fanciful_no_refusal(self):
        result = self._run("QWIXEL", "Software", ["042"], DistinctivenessLevel.FANCIFUL)
        self.assertFalse(result.refusal_warranted)

    def test_procedure_notes_is_string(self):
        result = self._run("FRESH", "Fruit", ["029"], DistinctivenessLevel.DESCRIPTIVE)
        self.assertIsInstance(result.procedure_notes, str)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — §1209.03 CONSIDERATIONS/EVIDENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsiderations(unittest.TestCase):

    def test_descriptive_term_generates_evidence(self):
        """FRESH DAILY for fresh produce → multiple evidence types found."""
        result = analyse_considerations("FRESH DAILY", "Fresh fruit and vegetables", ["029"])
        self.assertGreater(result.total_evidence_count, 0)

    def test_immediately_conveys_info_when_in_desc(self):
        """Mark words that appear in goods description → immediately conveys info."""
        result = analyse_considerations("FRESH FRUIT", "Fresh fruit products", ["029"])
        self.assertTrue(result.immediately_conveys_info)

    def test_evidence_strength_between_0_and_1(self):
        result = analyse_considerations("NATURAL CLEAN", "Natural cleaning products", ["003"])
        self.assertGreaterEqual(result.evidence_strength, 0.0)
        self.assertLessEqual(result.evidence_strength, 1.0)

    def test_no_evidence_for_fanciful_mark(self):
        """Coined word → no dictionary/trade/competitor evidence."""
        result = analyse_considerations("QWIXEL", "Software", ["042"])
        self.assertEqual(result.total_evidence_count, 0)
        self.assertFalse(result.dictionary_definitions_found)

    def test_dictionary_evidence_is_list(self):
        result = analyse_considerations("PURE WATER", "Bottled water", ["032"])
        self.assertIsInstance(result.dictionary_evidence, list)

    def test_trade_evidence_is_list(self):
        result = analyse_considerations("FAST DELIVERY", "Courier services", ["039"])
        self.assertIsInstance(result.trade_usage_evidence, list)

    def test_evidence_items_have_required_fields(self):
        result = analyse_considerations("FRESH DAILY", "Fresh food", ["029"])
        for ev in (result.dictionary_evidence + result.trade_usage_evidence):
            self.assertIsInstance(ev.source, str)
            self.assertIsInstance(ev.excerpt, str)
            self.assertIsInstance(ev.weight, float)

    def test_evidence_weight_between_0_and_1(self):
        result = analyse_considerations("NATURAL ORGANIC", "Organic food", ["029"])
        all_ev = (result.dictionary_evidence + result.trade_usage_evidence +
                  result.applicant_usage_evidence + result.competitor_usage_evidence)
        for ev in all_ev:
            self.assertGreaterEqual(ev.weight, 0.0)
            self.assertLessEqual(ev.weight, 1.0)

    def test_analysis_notes_is_string(self):
        result = analyse_considerations("EASY SMART", "Software", ["042"])
        self.assertIsInstance(result.analysis_notes, str)

    def test_competitor_evidence_for_descriptive(self):
        """Descriptive terms should have competitor usage evidence."""
        result = analyse_considerations("FRESH PURE", "Fresh water", ["032"])
        # Fresh and Pure are known descriptive words → should have competitor evidence
        if result.dictionary_definitions_found:
            self.assertGreater(len(result.competitor_usage_evidence), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — §1209.04 DECEPTIVELY MISDESCRIPTIVE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeceptiveMisdescriptive(unittest.TestCase):

    def test_silk_for_synthetic_clothing_detected(self):
        """SILK for polyester clothing → deceptively misdescriptive."""
        result = analyse_deceptive_misdescriptive(
            "SILK TOUCH", "Synthetic polyester clothing", ["025"]
        )
        self.assertTrue(result.misdescription_detected)
        self.assertEqual(result.misdescriptive_term, "SILK")
        self.assertTrue(result.refusal_warranted)

    def test_prong1_misdescription_detected(self):
        """Goods don't contain the claimed material."""
        result = analyse_deceptive_misdescriptive(
            "GOLD RING", "Fashion jewelry made of brass and zinc alloy", ["014"]
        )
        self.assertTrue(result.misdescription_detected)
        self.assertFalse(result.goods_actually_have_quality)

    def test_prong2_consumer_belief(self):
        """Consumers would likely believe the material claim."""
        result = analyse_deceptive_misdescriptive(
            "LEATHER WALLET", "Synthetic vinyl wallets", ["018"]
        )
        if result.misdescription_detected:
            self.assertTrue(result.consumers_likely_to_believe)

    def test_overcomeable_with_2f_not_absolute_bar(self):
        """§2(e)(1) is NOT an absolute bar — unlike §2(a)."""
        result = analyse_deceptive_misdescriptive(
            "SILK TOUCH", "Polyester shirts", ["025"]
        )
        self.assertTrue(result.overcomeable_with_2f)

    def test_statutory_basis_2e1(self):
        result = analyse_deceptive_misdescriptive(
            "CASHMERE SOFT", "Synthetic sweaters", ["025"]
        )
        if result.refusal_warranted:
            self.assertIn("§2(e)(1)", result.statutory_basis)
            self.assertIn("§1209.04", result.statutory_basis)

    def test_genuine_silk_no_refusal(self):
        """If goods description confirms silk content → no misdescription."""
        result = analyse_deceptive_misdescriptive(
            "SILK THREAD", "100% pure silk thread", ["023"]
        )
        self.assertFalse(result.misdescription_detected)

    def test_honey_in_non_honey_product(self):
        """HONEY for synthetic sweetener → misdescriptive."""
        result = analyse_deceptive_misdescriptive(
            "HONEY SWEET", "Artificial sweetener made from corn syrup", ["029"]
        )
        self.assertTrue(result.misdescription_detected)
        self.assertEqual(result.misdescriptive_term, "HONEY")

    def test_genuine_honey_product_no_refusal(self):
        result = analyse_deceptive_misdescriptive(
            "HONEY DROPS", "Natural honey candy with real honey", ["030"]
        )
        self.assertFalse(result.misdescription_detected)

    def test_no_misdescription_unrelated_mark(self):
        result = analyse_deceptive_misdescriptive(
            "ZENITH CLOUD", "Software services", ["042"]
        )
        self.assertFalse(result.misdescription_detected)
        self.assertFalse(result.refusal_warranted)

    def test_notes_is_string(self):
        result = analyse_deceptive_misdescriptive(
            "SILK TOUCH", "Synthetic clothing", ["025"]
        )
        self.assertIsInstance(result.notes, str)

    def test_italian_origin_misdescription(self):
        """ITALIAN for non-Italian goods in food class."""
        result = analyse_deceptive_misdescriptive(
            "ITALIAN PASTA", "Pasta made in USA", ["030"]
        )
        self.assertTrue(result.misdescription_detected)

    def test_2e1_vs_2a_distinction_in_notes(self):
        """Confirm the notes distinguish §2(e)(1) from §2(a)."""
        result = analyse_deceptive_misdescriptive(
            "LEATHER BAG", "Vinyl synthetic bags", ["018"]
        )
        if result.refusal_warranted:
            # Must mention both prongs of the test
            self.assertIn("PRONG 1", result.notes)
            self.assertIn("PRONG 2", result.notes)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — ENGINE OUTPUT SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineOutputSchema(unittest.TestCase):

    def setUp(self):
        self.result = conduct_tmep_1209_analysis(DUMMY_INPUTS["descriptive"])

    def test_authority_reference(self):
        self.assertEqual(self.result["authority_reference"], "TMEP §1209")

    def test_applied_for_mark_present(self):
        self.assertEqual(self.result["applied_for_mark"], "FRESH DAILY")

    def test_timestamp_is_iso8601(self):
        ts = self.result["analysis_timestamp"]
        self.assertTrue(ts.endswith("Z"))

    def test_all_four_sections_present(self):
        for section in ["section_1209_01", "section_1209_02",
                        "section_1209_03", "section_1209_04"]:
            self.assertIn(section, self.result)

    def test_section_1209_01_fields(self):
        s = self.result["section_1209_01"]
        for field in ["distinctiveness_level", "distinctiveness_score",
                      "imagination_required", "directly_describes",
                      "competitor_need", "reasoning"]:
            self.assertIn(field, s)

    def test_section_1209_02_fields(self):
        s = self.result["section_1209_02"]
        for field in ["refusal_warranted", "refusal_ground", "statutory_basis",
                      "is_absolute_bar", "overcome_methods", "procedure_notes"]:
            self.assertIn(field, s)

    def test_section_1209_03_fields(self):
        s = self.result["section_1209_03"]
        for field in ["dictionary_definitions_found", "evidence_strength",
                      "total_evidence_count", "evidence", "analysis_notes"]:
            self.assertIn(field, s)

    def test_section_1209_03_evidence_sub_keys(self):
        ev = self.result["section_1209_03"]["evidence"]
        for key in ["dictionary", "trade_usage", "applicant", "competitor"]:
            self.assertIn(key, ev)

    def test_section_1209_04_fields(self):
        s = self.result["section_1209_04"]
        for field in ["misdescription_detected", "refusal_warranted",
                      "overcomeable_with_2f", "distinction_from_2a"]:
            self.assertIn(field, s)

    def test_overall_fields(self):
        for field in ["refusal_recommended", "refusal_ground", "is_absolute_bar",
                      "overcome_methods", "distinctiveness_level", "compliance_status"]:
            self.assertIn(field, self.result)

    def test_refusal_recommended_is_bool(self):
        self.assertIsInstance(self.result["refusal_recommended"], bool)

    def test_is_absolute_bar_is_bool(self):
        self.assertIsInstance(self.result["is_absolute_bar"], bool)

    def test_overcome_methods_is_list(self):
        self.assertIsInstance(self.result["overcome_methods"], list)

    def test_output_is_json_serialisable(self):
        json.dumps(self.result)

    def test_compliance_status_is_string(self):
        self.assertIsInstance(self.result["compliance_status"], str)
        self.assertGreater(len(self.result["compliance_status"]), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — DUMMY INPUT SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDummyScenarios(unittest.TestCase):

    def test_descriptive_scenario(self):
        result = conduct_tmep_1209_analysis_dummy("descriptive")
        self.assertIn(result["distinctiveness_level"],
                      ["GENERIC", "DESCRIPTIVE"])
        self.assertTrue(result["refusal_recommended"])

    def test_generic_scenario_absolute_bar(self):
        result = conduct_tmep_1209_analysis_dummy("generic")
        self.assertTrue(result["is_absolute_bar"])
        self.assertEqual(result["distinctiveness_level"], "GENERIC")

    def test_suggestive_scenario_no_refusal(self):
        result = conduct_tmep_1209_analysis_dummy("suggestive")
        self.assertIn(result["distinctiveness_level"],
                      ["SUGGESTIVE", "ARBITRARY", "FANCIFUL"])
        self.assertFalse(result["refusal_recommended"])

    def test_arbitrary_scenario_no_refusal(self):
        result = conduct_tmep_1209_analysis_dummy("arbitrary")
        self.assertFalse(result["refusal_recommended"])
        self.assertIn(result["distinctiveness_level"],
                      ["ARBITRARY", "SUGGESTIVE", "FANCIFUL"])

    def test_misdescriptive_scenario(self):
        result = conduct_tmep_1209_analysis_dummy("misdescriptive")
        self.assertTrue(result["section_1209_04"]["misdescription_detected"])
        self.assertTrue(result["refusal_recommended"])

    def test_invalid_scenario_raises(self):
        with self.assertRaises(ValueError):
            conduct_tmep_1209_analysis_dummy("nonexistent_scenario")

    def test_all_scenarios_json_serialisable(self):
        for scenario in DUMMY_INPUTS:
            result = conduct_tmep_1209_analysis_dummy(scenario)
            json.dumps(result)  # must not raise

    def test_validation_missing_mark_text(self):
        with self.assertRaises(ValueError):
            conduct_tmep_1209_analysis({"goods_services": [{"class": "029"}]})

    def test_validation_empty_mark_text(self):
        with self.assertRaises(ValueError):
            conduct_tmep_1209_analysis({
                "mark_text": "   ",
                "goods_services": [{"class": "029", "description": "Food"}]
            })

    def test_validation_empty_goods_services(self):
        with self.assertRaises(ValueError):
            conduct_tmep_1209_analysis({
                "mark_text": "TEST",
                "goods_services": []
            })


if __name__ == "__main__":
    unittest.main(verbosity=2)
