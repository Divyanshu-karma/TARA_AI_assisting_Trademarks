# descriptiveness/deceptive_misdescriptive.py
"""
TMEP §1209.04 — Deceptively Misdescriptive Marks

Statutory basis: Trademark Act §2(e)(1); 15 U.S.C. §1052(e)(1)

CRITICAL DISTINCTION FROM §1207.02 / §2(a):
  ┌──────────────────┬────────────────────────────┬──────────────────────────┐
  │ Provision        │ §2(a) Deceptive            │ §2(e)(1) Deceptively     │
  │                  │ (TMEP §1207.02)             │ Misdescriptive           │
  │                  │                             │ (TMEP §1209.04)          │
  ├──────────────────┼────────────────────────────┼──────────────────────────┤
  │ Absolute bar?    │ YES — never registrable    │ NO — overcomeable        │
  │ Materiality req? │ YES (3rd prong of test)    │ NO                       │
  │ Test             │ 3-prong (Budge Mfg. Co.)   │ 2-prong (Quady Winery)   │
  │ Overcome?        │ Never                      │ §2(f) acquired dist.     │
  │                  │                            │ or Supplemental Register  │
  └──────────────────┴────────────────────────────┴──────────────────────────┘

§2(e)(1) Deceptively Misdescriptive Test (In re Quady Winery, 221 USPQ 1213):
  Prong 1: Does the mark misdescribe a characteristic of the goods?
           (The misdescription must be plausible — not obviously false)
  Prong 2: Would consumers be likely to believe the misdescription?
           (Would a reasonable consumer be misled?)

If BOTH prongs are met → §2(e)(1) deceptively misdescriptive refusal.

Examples:
  "LOVEE LAMB" for synthetic car seat covers → misdescribes material
  "GLASS WAX" for wax containing no glass → misdescribes ingredient
  "SILKEASE" for clothing not made of silk → misdescribes fabric
"""

from __future__ import annotations
import re
from descriptiveness.models import DeceptiveMisdescriptiveAnalysis


# ──────────────────────────────────────────────────────────────────────────────
# MISDESCRIPTIVE TERM CATEGORIES
# ──────────────────────────────────────────────────────────────────────────────

# Maps: term → IC classes where it would be misdescriptive if goods don't contain it
_MATERIAL_TERMS: dict[str, list[str]] = {
    "SILK":       ["025", "024", "021"],
    "WOOL":       ["025", "024"],
    "COTTON":     ["025", "024"],
    "LINEN":      ["025", "024"],
    "CASHMERE":   ["025", "024"],
    "LEATHER":    ["025", "018", "016"],
    "SUEDE":      ["025", "018"],
    "VELVET":     ["025", "024"],
    "DENIM":      ["025"],
    "GOLD":       ["014", "026", "021"],
    "SILVER":     ["014", "026", "021"],
    "PLATINUM":   ["014"],
    "DIAMOND":    ["014", "021"],
    "CRYSTAL":    ["021", "033"],
    "GLASS":      ["021", "003"],
    "BRASS":      ["021", "006"],
    "COPPER":     ["021", "006"],
    "STEEL":      ["006", "021", "008"],
    "TITANIUM":   ["010", "006"],
    "BAMBOO":     ["020", "016", "021"],
    "TEAK":       ["020", "019"],
    "OAK":        ["020", "019"],
    "CEDAR":      ["020", "003"],
}

_INGREDIENT_TERMS: dict[str, list[str]] = {
    "HONEY":     ["029", "030", "003", "005"],
    "VANILLA":   ["030", "033", "032"],
    "ALOE":      ["003", "005", "044"],
    "OLIVE":     ["029", "003"],
    "LEMON":     ["029", "003", "032"],
    "MINT":      ["030", "003", "005"],
    "LAVENDER":  ["003", "005"],
    "CHARCOAL":  ["003", "029"],
    "COLLAGEN":  ["003", "005"],
    "KERATIN":   ["003"],
    "CAFFEINE":  ["032", "005", "003"],
    "VITAMIN":   ["005", "003", "029", "032"],
    "PROTEIN":   ["029", "032", "005"],
    "OMEGA":     ["005", "029"],
    "PROBIOTIC": ["005", "029"],
    "HERBAL":    ["003", "005", "029"],
    "ORGANIC":   ["029", "030", "031", "003"],
    "NATURAL":   ["003", "005", "029", "030"],
    "FRESH":     ["029", "031", "032"],
    "AGED":      ["033", "029"],
    "SMOKED":    ["029"],
}

_ORIGIN_TERMS: dict[str, list[str]] = {
    # "SWISS" watches, cheese, etc.
    "SWISS":      ["014", "029", "021"],
    "ITALIAN":    ["025", "033", "029", "030"],
    "FRENCH":     ["025", "033", "029", "003"],
    "JAPANESE":   ["025", "009", "014"],
    "GERMAN":     ["012", "021", "007"],
    "COLOMBIAN":  ["030"],   # coffee
    "SCOTTISH":   ["033"],   # whisky
    "IRISH":      ["033"],   # whiskey/stout
    "JAMAICAN":   ["030", "033"],
    "CUBAN":      ["034"],   # cigars
}


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def analyse_deceptive_misdescriptive(
    mark_text:         str,
    goods_description: str,
    ic_classes:        list[str],
) -> DeceptiveMisdescriptiveAnalysis:
    """
    §1209.04 — Two-prong test for deceptive misdescriptiveness.

    Prong 1: Does the mark misdescribe the goods?
    Prong 2: Would consumers be likely to believe the misdescription?

    Args:
        mark_text:         Trademark text
        goods_description: Goods/services description
        ic_classes:        IC class list

    Returns:
        DeceptiveMisdescriptiveAnalysis
    """
    words      = set(re.findall(r"[A-Za-z]+", mark_text.upper()))
    desc_upper = goods_description.upper()

    # ── Check material terms ──────────────────────────────────────────────────
    for term, classes in _MATERIAL_TERMS.items():
        if term in words and _class_overlap(ic_classes, classes):
            prong1 = _not_in_goods(term, desc_upper)        # Mark claims it, goods don't have it
            prong2 = _consumer_would_believe_material(term)
            if prong1 and prong2:
                return _build_result(
                    term, "material composition", goods_description,
                    prong1, prong2, mark_text
                )

    # ── Check ingredient terms ────────────────────────────────────────────────
    for term, classes in _INGREDIENT_TERMS.items():
        if term in words and _class_overlap(ic_classes, classes):
            prong1 = _not_in_goods(term, desc_upper)
            prong2 = _consumer_would_believe_ingredient(term)
            if prong1 and prong2:
                return _build_result(
                    term, "ingredient/composition", goods_description,
                    prong1, prong2, mark_text
                )

    # ── Check geographic/origin terms ─────────────────────────────────────────
    for term, classes in _ORIGIN_TERMS.items():
        if term in words and _class_overlap(ic_classes, classes):
            prong1 = _not_in_goods(term, desc_upper)
            prong2 = True   # Geographic origin terms almost always believable
            if prong1:
                return _build_result(
                    term, "geographic origin", goods_description,
                    prong1, prong2, mark_text
                )

    # ── No misdescriptiveness found ───────────────────────────────────────────
    return DeceptiveMisdescriptiveAnalysis(
        misdescription_detected  = False,
        misdescriptive_term      = "",
        goods_actually_have_quality = True,
        consumers_likely_to_believe = False,
        refusal_warranted        = False,
        overcomeable_with_2f     = True,
        statutory_basis          = "",
        notes = (
            f"No deceptively misdescriptive matter detected in '{mark_text}'. "
            f"Mark does not appear to misdescribe a material, ingredient, "
            f"or characteristic of the goods."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _class_overlap(ic_classes: list[str], target_classes: list[str]) -> bool:
    return bool(set(ic_classes) & set(target_classes))


def _not_in_goods(term: str, desc_upper: str) -> bool:
    """
    Prong 1 check: Does the goods description confirm the term is accurate?
    If the term appears in the goods description → NOT misdescriptive.
    If absent → potentially misdescriptive.
    """
    # Synonyms / related confirmations in description
    confirming_terms = {
        "SILK":       {"SILK", "SILKWORM", "NATURAL FIBER"},
        "GOLD":       {"GOLD", "14K", "18K", "KARAT", "GILDED"},
        "LEATHER":    {"LEATHER", "HIDE", "GENUINE LEATHER"},
        "HONEY":      {"HONEY", "BEE", "HONEYBEE"},
        "ORGANIC":    {"ORGANIC", "CERTIFIED ORGANIC", "USDA ORGANIC"},
        "FRESH":      {"FRESH", "FRESHLY"},
        "NATURAL":    {"NATURAL", "ALL-NATURAL"},
    }
    checks = confirming_terms.get(term, {term})
    return not any(c in desc_upper for c in checks)


def _consumer_would_believe_material(term: str) -> bool:
    """
    Prong 2: Would a consumer likely believe the mark's material claim?
    Returns True for terms that consumers commonly take literally.
    """
    # Consumers typically take material composition claims literally
    high_believability = {
        "SILK", "CASHMERE", "LEATHER", "GOLD", "SILVER", "PLATINUM",
        "DIAMOND", "CRYSTAL", "TITANIUM", "BAMBOO", "STEEL"
    }
    return term in high_believability or True   # Default: material claims believed


def _consumer_would_believe_ingredient(term: str) -> bool:
    """Prong 2: Would consumers believe the ingredient claim?"""
    # Health/beauty ingredient claims are very commonly believed by consumers
    high_believability = {
        "HONEY", "ALOE", "COLLAGEN", "VITAMIN", "PROTEIN",
        "OMEGA", "PROBIOTIC", "HERBAL"
    }
    return term in high_believability or True


def _build_result(
    term: str, category: str, goods_desc: str,
    prong1: bool, prong2: bool, mark_text: str,
) -> DeceptiveMisdescriptiveAnalysis:
    return DeceptiveMisdescriptiveAnalysis(
        misdescription_detected     = True,
        misdescriptive_term         = term,
        goods_actually_have_quality = not prong1,
        consumers_likely_to_believe = prong2,
        refusal_warranted           = True,
        overcomeable_with_2f        = True,    # §2(e)(1) IS overcomeable, unlike §2(a)
        statutory_basis             = "Trademark Act §2(e)(1); 15 U.S.C. §1052(e)(1); TMEP §1209.04",
        notes = (
            f"PRONG 1 (Misdescription): Mark '{mark_text}' contains term '{term}' "
            f"suggesting the goods involve {category} of '{term}', but the goods "
            f"description does not confirm this characteristic. "
            f"PRONG 2 (Consumer Belief): Consumers encountering this mark for "
            f"these goods would likely believe the {category} claim. "
            f"Both prongs of In re Quady Winery test satisfied. "
            f"§2(e)(1) deceptively misdescriptive refusal warranted. "
            f"Unlike §2(a), this refusal IS overcomeable with §2(f) acquired "
            f"distinctiveness or amendment to the Supplemental Register."
        ),
    )
