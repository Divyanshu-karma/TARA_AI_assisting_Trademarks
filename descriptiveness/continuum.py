# descriptiveness/continuum.py
"""
TMEP §1209.01 — Distinctiveness/Descriptiveness Continuum

Legal framework:
  Abercrombie & Fitch Co. v. Hunting World, Inc., 537 F.2d 4 (2d Cir. 1976)
  establishes the spectrum from least to most distinctive:

      GENERIC → DESCRIPTIVE → SUGGESTIVE → ARBITRARY → FANCIFUL

  ┌────────────┬──────────────────────────────────────────────────────────┐
  │ Level      │ Definition + Examples                                    │
  ├────────────┼──────────────────────────────────────────────────────────┤
  │ GENERIC    │ Common name of the goods themselves.                     │
  │            │ "APPLE" for apples. Never registrable.                  │
  ├────────────┼──────────────────────────────────────────────────────────┤
  │ DESCRIPTIVE│ Immediately describes quality/feature of goods.          │
  │            │ "COLD AND CREAMY" for ice cream. Registrable only       │
  │            │ with §2(f) acquired distinctiveness.                    │
  ├────────────┼──────────────────────────────────────────────────────────┤
  │ SUGGESTIVE │ Requires imagination to connect mark to goods.           │
  │            │ "COPPERTONE" for suntan lotion. Inherently distinctive. │
  ├────────────┼──────────────────────────────────────────────────────────┤
  │ ARBITRARY  │ Real word, no connection to goods.                       │
  │            │ "APPLE" for computers. Strongest inherent mark.         │
  ├────────────┼──────────────────────────────────────────────────────────┤
  │ FANCIFUL   │ Invented / coined word. No prior meaning.                │
  │            │ "KODAK", "XEROX". Maximum protection.                   │
  └────────────┴──────────────────────────────────────────────────────────┘

Key tests applied:
  1. Imagination Test (Stix Products):
     Does a consumer need imagination to connect mark → goods?
     YES = suggestive. NO = descriptive.

  2. Competitor Need Test (in re Gyulay):
     Do competitors legitimately need to use this term?
     YES = descriptive (can't monopolise). NO = could be suggestive.

  3. Compound Descriptiveness (in re Oppedahl & Larson):
     Is each element independently descriptive of the goods?
     YES = whole mark likely descriptive.

  4. Genus / Species test for genericness (H. Marvin Ginn Corp.):
     Does the relevant public primarily use the term to refer to
     the class/genus of goods?
"""

from __future__ import annotations
import re
from descriptiveness.models import ContinuumAnalysis, DistinctivenessLevel


# ──────────────────────────────────────────────────────────────────────────────
# WORD LISTS
# ──────────────────────────────────────────────────────────────────────────────

# Coined/invented word patterns — signals FANCIFUL
_FANCIFUL_PATTERNS = [
    r"[aeiou]{3,}",        # unusual vowel cluster: KODAAK
    r"[^aeiou]{4,}",       # long consonant cluster: QWERTYX
    r"x{1}[a-z]{2,}",      # x-prefix coinages: XEROX
    r"[a-z]{2,}[0-9]+",    # alphanumeric coinages
]

# Common suffixes that signal descriptiveness for certain goods
# Mapped to IC classes where they are descriptive
_DESCRIPTIVE_SUFFIX_MAP: dict[str, list[str]] = {
    "FRESH":   ["029", "030", "031", "032", "043"],
    "PURE":    ["029", "030", "031", "032", "005"],
    "FAST":    ["039", "042", "035"],
    "QUICK":   ["039", "042", "035"],
    "SMART":   ["009", "042", "035"],
    "EASY":    ["009", "016", "035", "042"],
    "SAFE":    ["005", "010", "042", "045"],
    "SECURE":  ["042", "045", "036"],
    "CLEAN":   ["003", "029", "044"],
    "NATURAL": ["003", "005", "029", "031", "044"],
    "DIGITAL": ["009", "038", "042"],
    "ONLINE":  ["035", "038", "042"],
    "DIRECT":  ["035", "039"],
    "PREMIER": ["035", "036", "041", "043"],
    "PLUS":    ["009", "042", "005", "035"],
    "PRO":     ["009", "042", "035"],
    "MAX":     ["009", "005", "025", "032"],
    "ULTRA":   ["009", "005", "025"],
    "SUPER":   ["029", "030", "032", "043"],
    "BEST":    ["029", "030", "032", "035", "043"],
    "PRIME":   ["029", "035", "036"],
    "ELITE":   ["025", "035", "036", "041"],
    "EXPERT":  ["035", "041", "044", "045"],
    "MASTER":  ["041", "035", "037"],
    "VALUE":   ["035", "036"],
    "BUDGET":  ["035", "039"],
    "DAILY":   ["005", "016", "029"],
    "WEEKLY":  ["016", "038", "041"],
}

# Words that are generic for specific IC classes
_GENERIC_TERMS_BY_CLASS: dict[str, set[str]] = {
    "029": {"FOOD", "MEAT", "FISH", "FRUIT", "VEGETABLE", "DAIRY", "CHEESE",
            "BUTTER", "MILK", "CREAM", "APPLE", "ORANGE", "BEEF", "CHICKEN"},
    "030": {"BREAD", "CAKE", "FLOUR", "SUGAR", "COFFEE", "TEA", "PASTA",
            "CEREAL", "COOKIE", "CRACKER", "PASTRY"},
    "032": {"BEER", "ALE", "WATER", "JUICE", "SODA", "BEVERAGE", "DRINK"},
    "033": {"WINE", "SPIRITS", "VODKA", "WHISKEY", "RUM", "GIN", "LIQUOR"},
    "025": {"SHIRT", "PANTS", "DRESS", "JACKET", "SHOE", "BOOT", "HAT",
            "CLOTHING", "APPAREL", "WEAR", "FOOTWEAR"},
    "009": {"SOFTWARE", "APP", "APPLICATION", "PROGRAM", "HARDWARE",
            "DEVICE", "COMPUTER", "PHONE"},
    "035": {"SERVICE", "SERVICES", "CONSULTING", "MANAGEMENT", "BUSINESS"},
    "036": {"BANK", "BANKING", "INSURANCE", "FINANCIAL", "FINANCE", "FUND"},
    "042": {"TECHNOLOGY", "TECH", "PLATFORM", "CLOUD", "DATA", "DIGITAL"},
    "044": {"HEALTH", "MEDICAL", "CARE", "WELLNESS", "CLINIC", "THERAPY"},
    "043": {"RESTAURANT", "CAFE", "HOTEL", "DINING", "CATERING"},
}

# Descriptive quality/feature terms across all goods
_UNIVERSAL_DESCRIPTIVE: set[str] = {
    "FRESH", "PURE", "CLEAN", "NATURAL", "ORGANIC", "HEALTHY", "PREMIUM",
    "QUALITY", "CLASSIC", "TRADITIONAL", "ORIGINAL", "GENUINE", "AUTHENTIC",
    "ADVANCED", "INNOVATIVE", "NEW", "IMPROVED", "BETTER", "BEST", "GREAT",
    "FAST", "QUICK", "EASY", "SIMPLE", "SAFE", "SECURE", "RELIABLE",
    "SMART", "INTELLIGENT", "PROFESSIONAL", "EXPERT", "MASTER", "ULTRA",
    "SUPER", "MEGA", "MAXI", "MINI", "MICRO", "NANO", "PLUS", "PRO",
    "MAX", "PRIME", "ELITE", "ULTIMATE", "COMPLETE", "TOTAL", "FULL",
    "LIGHT", "LITE", "STRONG", "BOLD", "BRIGHT", "CLEAR", "SOFT", "SMOOTH",
    "RICH", "GOLDEN", "SILVER", "WHITE", "BLACK", "RED", "BLUE", "GREEN",
    "VALUE", "BUDGET", "AFFORDABLE", "DIRECT", "ONLINE", "DIGITAL", "GLOBAL",
    "DAILY", "WEEKLY", "EXPRESS", "RAPID", "INSTANT",
}

# Common word — appears in dictionaries — BUT not descriptive of any particular goods
# signals ARBITRARY (real word, unrelated to goods)
_COMMON_WORDS: set[str] = {
    "APPLE", "AMAZON", "SHELL", "ORACLE", "JAGUAR", "MUSTANG", "ECLIPSE",
    "PIONEER", "SUMMIT", "HORIZON", "SUNRISE", "FALCON", "EAGLE", "ARROW",
    "BRIDGE", "HARBOR", "MEADOW", "RIVER", "MOUNTAIN", "VALLEY", "FOREST",
    "STONE", "IRON", "COPPER", "AMBER", "CEDAR", "ATLAS", "PHOENIX",
    "TITAN", "ZENITH", "APEX", "CROWN", "BADGE", "SHIELD", "ANCHOR",
    "COMPASS", "PRISM", "NEXUS", "VERTEX", "DELTA", "SIGMA", "ALPHA",
}


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def analyse_continuum(
    mark_text:         str,
    goods_description: str,
    ic_classes:        list[str],
) -> ContinuumAnalysis:
    """
    §1209.01 — Positions the mark on the distinctiveness continuum.

    Args:
        mark_text:         The trademark text e.g. "ADAMS APPLE"
        goods_description: Goods/services description e.g. "Dried fruits"
        ic_classes:        IC classes e.g. ["029"]

    Returns:
        ContinuumAnalysis with distinctiveness_level and reasoning.
    """
    words        = _extract_words(mark_text)
    mark_upper   = mark_text.upper()
    desc_upper   = goods_description.upper()

    # ── Test 1: Generic? ─────────────────────────────────────────────────────
    generic_words = _find_generic_words(words, ic_classes)
    if generic_words and len(generic_words) == len(words):
        # All meaningful words are generic for these goods
        return ContinuumAnalysis(
            mark_text             = mark_text,
            goods_description     = goods_description,
            ic_classes            = ic_classes,
            distinctiveness_level = DistinctivenessLevel.GENERIC,
            imagination_required  = False,
            directly_describes    = True,
            competitor_need       = True,
            distinctiveness_score = 0.0,
            reasoning = (
                f"Mark '{mark_text}' is the common/generic name for the goods. "
                f"Generic terms ({', '.join(generic_words)}) are incapable of "
                f"functioning as source identifiers. §2(e)(1) — generic refusal. "
                f"See H. Marvin Ginn Corp., 228 USPQ 527 (Fed. Cir. 1986)."
            ),
        )

    # ── Test 2: Fanciful? (coined word) ──────────────────────────────────────
    if _is_fanciful(words):
        return ContinuumAnalysis(
            mark_text             = mark_text,
            goods_description     = goods_description,
            ic_classes            = ic_classes,
            distinctiveness_level = DistinctivenessLevel.FANCIFUL,
            imagination_required  = True,
            directly_describes    = False,
            competitor_need       = False,
            distinctiveness_score = 1.0,
            reasoning = (
                f"Mark '{mark_text}' appears to be a coined or invented term "
                f"with no dictionary meaning related to the goods. "
                f"Fanciful marks receive maximum trademark protection."
            ),
        )

    # ── Test 3: Arbitrary? (real word, no connection to goods) ───────────────
    arbitrary_words = [w for w in words if w in _COMMON_WORDS]
    descriptive_words = _find_descriptive_words(words, ic_classes)
    if arbitrary_words and not descriptive_words:
        return ContinuumAnalysis(
            mark_text             = mark_text,
            goods_description     = goods_description,
            ic_classes            = ic_classes,
            distinctiveness_level = DistinctivenessLevel.ARBITRARY,
            imagination_required  = True,
            directly_describes    = False,
            competitor_need       = False,
            distinctiveness_score = 0.90,
            reasoning = (
                f"Mark '{mark_text}' uses a known word ('{arbitrary_words[0]}') "
                f"with no descriptive connection to the goods. "
                f"Arbitrary marks are inherently distinctive. "
                f"Classic example: 'APPLE' for computers."
            ),
        )

    # ── Test 4: Descriptive? ─────────────────────────────────────────────────
    desc_score = _descriptiveness_score(words, ic_classes, goods_description)
    directly_describes = _directly_describes_goods(words, goods_description, ic_classes)
    competitor_need    = _competitors_need_term(words, ic_classes)
    compound_desc      = _is_compound_descriptive(words, ic_classes)

    if desc_score >= 0.60 or directly_describes or compound_desc:
        reasoning = _build_descriptive_reasoning(
            mark_text, words, ic_classes, desc_score, directly_describes,
            competitor_need, compound_desc
        )
        return ContinuumAnalysis(
            mark_text             = mark_text,
            goods_description     = goods_description,
            ic_classes            = ic_classes,
            distinctiveness_level = DistinctivenessLevel.DESCRIPTIVE,
            imagination_required  = False,
            directly_describes    = directly_describes,
            competitor_need       = competitor_need,
            compound_descriptive  = compound_desc,
            distinctiveness_score = round(1.0 - desc_score, 3),
            reasoning             = reasoning,
        )

    # ── Test 5: Suggestive (default if not generic/fanciful/arbitrary/descriptive)
    score = round(0.50 + (1.0 - desc_score) * 0.30, 3)
    return ContinuumAnalysis(
        mark_text             = mark_text,
        goods_description     = goods_description,
        ic_classes            = ic_classes,
        distinctiveness_level = DistinctivenessLevel.SUGGESTIVE,
        imagination_required  = True,
        directly_describes    = False,
        competitor_need       = False,
        compound_descriptive  = False,
        distinctiveness_score = min(0.85, score),
        reasoning = (
            f"Mark '{mark_text}' requires a degree of imagination, thought, or "
            f"perception to connect it to the goods/services. "
            f"No direct descriptive connection found. Inherently distinctive."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _extract_words(text: str) -> list[str]:
    """Uppercase alpha words only, no stopwords."""
    stopwords = {"THE", "A", "AN", "AND", "OF", "FOR", "IN", "BY", "WITH"}
    words = re.findall(r"[A-Za-z]+", text.upper())
    return [w for w in words if w not in stopwords and len(w) > 1]


def _find_generic_words(words: list[str], ic_classes: list[str]) -> list[str]:
    """Returns any words that are generic for the given IC classes."""
    generic = []
    for w in words:
        for cls in ic_classes:
            if cls in _GENERIC_TERMS_BY_CLASS and w in _GENERIC_TERMS_BY_CLASS[cls]:
                if w not in generic:
                    generic.append(w)
    return generic


def _find_descriptive_words(words: list[str], ic_classes: list[str]) -> list[str]:
    """Returns words that are descriptive for these IC classes."""
    desc = []
    for w in words:
        if w in _UNIVERSAL_DESCRIPTIVE:
            if w not in desc:
                desc.append(w)
        if w in _DESCRIPTIVE_SUFFIX_MAP:
            for cls in ic_classes:
                if cls in _DESCRIPTIVE_SUFFIX_MAP[w]:
                    if w not in desc:
                        desc.append(w)
    return desc


def _is_fanciful(words: list[str]) -> bool:
    """True if the mark looks like a coined/invented term."""
    if not words:
        return False
    for word in words:
        w = word.lower()
        # Check for unusual letter patterns (signals coinages)
        for pattern in _FANCIFUL_PATTERNS:
            if re.search(pattern, w):
                return True
        # Very short words (2-3 chars) that aren't acronyms are often fanciful
        if len(w) <= 3 and w.isalpha() and w.upper() not in _UNIVERSAL_DESCRIPTIVE:
            return True
        # Long words (10+) not in common vocabulary
        if len(w) >= 10 and w.upper() not in _COMMON_WORDS:
            return True
    return False


def _descriptiveness_score(
    words: list[str], ic_classes: list[str], goods_desc: str
) -> float:
    """
    Returns a score 0.0–1.0 for how descriptive the mark is.
    Higher = more descriptive.
    """
    if not words:
        return 0.0

    desc_words  = _find_descriptive_words(words, ic_classes)
    total       = len(words)
    desc_count  = len(desc_words)

    base_score  = desc_count / total

    # Boost if descriptive words appear in the goods description
    desc_upper  = goods_desc.upper()
    boost = sum(0.15 for w in desc_words if w in desc_upper)
    boost = min(0.30, boost)

    return min(1.0, base_score + boost)


def _directly_describes_goods(
    words: list[str], goods_desc: str, ic_classes: list[str]
) -> bool:
    """
    True if the mark directly describes a feature/quality/characteristic
    of the specific goods. Tests: does the mark literally appear in
    the goods description?
    """
    desc_upper = goods_desc.upper()
    mark_words_in_desc = sum(1 for w in words if w in desc_upper)
    # More than half the mark words appear directly in goods description → descriptive
    return mark_words_in_desc > 0 and (mark_words_in_desc / max(len(words), 1)) >= 0.50


def _competitors_need_term(words: list[str], ic_classes: list[str]) -> bool:
    """
    True if competitors in the same field would legitimately need to use
    these terms to describe their own goods/services.
    """
    desc_words = _find_descriptive_words(words, ic_classes)
    generic_words = _find_generic_words(words, ic_classes)
    return len(desc_words) > 0 or len(generic_words) > 0


def _is_compound_descriptive(words: list[str], ic_classes: list[str]) -> bool:
    """
    True if each word in the compound mark is independently descriptive,
    making the whole mark descriptive. (In re Oppedahl & Larson, 71 USPQ2d 1370)
    """
    if len(words) < 2:
        return False
    desc_words  = set(_find_descriptive_words(words, ic_classes))
    generic_words = set(_find_generic_words(words, ic_classes))
    all_desc    = desc_words | generic_words
    # All words must be independently descriptive/generic
    return all(w in all_desc for w in words)


def _build_descriptive_reasoning(
    mark_text: str, words: list[str], ic_classes: list[str],
    score: float, directly: bool, competitor: bool, compound: bool
) -> str:
    parts = [f"Mark '{mark_text}' appears merely descriptive under §2(e)(1)."]
    desc_words = _find_descriptive_words(words, ic_classes)
    if desc_words:
        parts.append(
            f"The term(s) '{', '.join(desc_words)}' directly describe "
            f"a feature/quality of the goods in IC class {ic_classes}."
        )
    if directly:
        parts.append(
            "The mark immediately conveys information about the goods "
            "without requiring imagination (fails Stix Products imagination test)."
        )
    if competitor:
        parts.append(
            "Competitors legitimately need to use this term to describe "
            "their goods, supporting a finding of descriptiveness. "
            "(In re Gyulay, 820 F.2d 1216)"
        )
    if compound:
        parts.append(
            "Each component of the compound mark is independently descriptive — "
            "the whole mark is therefore descriptive. (In re Oppedahl & Larson)"
        )
    return " ".join(parts)
