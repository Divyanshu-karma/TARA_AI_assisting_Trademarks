# similarity/factor2_goods_relatedness.py
"""
TMEP §1207.01 — DuPont Factor 2: Relatedness of Goods/Services

Scoring logic:
  - Same IC class         → 1.0  (directly competitive goods)
  - Adjacent IC classes   → 0.65 (commonly related in trade)
  - Description keyword overlap → adds up to +0.20
  - Unrelated classes     → 0.10

Legal standard (TMEP §1207.01(a)(v)):
  Goods need not be identical to support a finding of likelihood of confusion.
  They need only be related in a manner that consumers would mistakenly believe
  they come from the same source.
"""

from __future__ import annotations
import re
from similarity.models import Factor2Score


# ──────────────────────────────────────────────────────────────────────────────
# ADJACENT CLASS TABLE
# IC class pairs that USPTO treats as commonly related in trade.
# Source: TMEP §1207.01(a)(v) and examination practice.
# ──────────────────────────────────────────────────────────────────────────────

ADJACENT_CLASSES: set[frozenset] = {
    # Food & beverage chain
    frozenset({"029", "030"}),   # Processed food / baked goods
    frozenset({"029", "031"}),   # Processed food / agricultural products
    frozenset({"030", "032"}),   # Baked goods / beverages (non-alc)
    frozenset({"032", "033"}),   # Non-alcoholic / alcoholic beverages
    frozenset({"029", "032"}),   # Processed food / non-alc beverages
    frozenset({"030", "033"}),   # Food / alcoholic beverages

    # Clothing, footwear, headgear
    frozenset({"025", "018"}),   # Clothing / leather goods
    frozenset({"025", "026"}),   # Clothing / notions & fancy goods
    frozenset({"025", "028"}),   # Clothing / sporting goods

    # Technology & software
    frozenset({"009", "042"}),   # Electronics / software services
    frozenset({"009", "038"}),   # Electronics / telecommunications
    frozenset({"038", "042"}),   # Telecom / software services
    frozenset({"009", "035"}),   # Electronics / retail/business services

    # Business & financial services
    frozenset({"035", "036"}),   # Business / financial services
    frozenset({"036", "045"}),   # Financial / legal services
    frozenset({"035", "045"}),   # Business / legal services

    # Health & wellness
    frozenset({"005", "044"}),   # Pharmaceuticals / health services
    frozenset({"010", "044"}),   # Medical devices / health services
    frozenset({"005", "010"}),   # Pharma / medical devices
    frozenset({"003", "044"}),   # Cosmetics / beauty services

    # Education & entertainment
    frozenset({"041", "035"}),   # Education / business services
    frozenset({"041", "042"}),   # Education / software services
    frozenset({"016", "041"}),   # Printed materials / education

    # Retail channels
    frozenset({"035", "040"}),   # Retail / manufacturing services
    frozenset({"039", "040"}),   # Transport / manufacturing
}

# IC class descriptions used for keyword overlap analysis
IC_CLASS_DESCRIPTIONS: dict[str, str] = {
    "001": "chemicals industrial scientific",
    "002": "paints coatings colorants",
    "003": "cosmetics cleaning preparations beauty",
    "004": "lubricants fuels candles",
    "005": "pharmaceuticals medical preparations health",
    "006": "metal goods hardware construction",
    "007": "machines engines tools industrial",
    "008": "hand tools cutlery implements",
    "009": "electronics computers software scientific instruments",
    "010": "medical devices surgical instruments healthcare",
    "011": "lighting heating cooking appliances",
    "012": "vehicles transportation automobile",
    "013": "firearms explosives ammunition",
    "014": "jewelry precious metals watches",
    "015": "musical instruments",
    "016": "paper printed materials stationery books",
    "017": "rubber plastics gaskets insulation",
    "018": "leather bags luggage handbags",
    "019": "building construction materials",
    "020": "furniture mirrors picture frames",
    "021": "household utensils cookware glassware",
    "022": "ropes nets canvas sail",
    "023": "yarn thread textile",
    "024": "fabrics textiles linen",
    "025": "clothing footwear headgear apparel fashion",
    "026": "lace embroidery ribbons buttons",
    "027": "floor coverings rugs carpets",
    "028": "games toys sporting goods recreation",
    "029": "food meat fish fruit vegetables dairy processed",
    "030": "coffee tea cocoa sugar flour bread cereal baked goods",
    "031": "agricultural products fresh fruit vegetables plants",
    "032": "beverages non-alcoholic beer juice water soda",
    "033": "alcoholic beverages wine spirits liquor",
    "034": "tobacco smoking",
    "035": "business services advertising retail management",
    "036": "financial insurance banking real estate services",
    "037": "construction repair installation services",
    "038": "telecommunications broadcasting communication",
    "039": "transportation delivery storage travel",
    "040": "treatment materials manufacturing processing",
    "041": "education entertainment sports training",
    "042": "software technology scientific research services",
    "043": "food beverage restaurant hotel services",
    "044": "medical health beauty services",
    "045": "legal security personal social services",
}


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def score_factor2(
    applied_classes:      list[str],
    conflicting_classes:  list[str],
    applied_description:  str = "",
    conflict_description: str = "",
) -> Factor2Score:
    """
    Computes DuPont Factor 2 score.

    Args:
        applied_classes:      IC classes of the applied-for mark
        conflicting_classes:  IC classes of the conflicting mark
        applied_description:  Goods/services description of applied-for
        conflict_description: Goods/services description of conflicting mark

    Returns:
        Factor2Score with composite_score 0.0–1.0
    """
    applied_set     = set(applied_classes)
    conflicting_set = set(conflicting_classes)

    # 1. Same class?
    same_class = bool(applied_set & conflicting_set)

    # 2. Adjacent class?
    adjacent = False
    if not same_class:
        adjacent = _has_adjacent(applied_set, conflicting_set)

    # 3. Description keyword overlap
    desc_overlap = _description_overlap(applied_description, conflict_description)

    # 4. Composite score
    if same_class:
        base = 1.0
    elif adjacent:
        base = 0.65
    else:
        base = 0.10

    composite = min(1.0, base + desc_overlap * 0.20)

    notes = _build_notes(
        applied_classes, conflicting_classes,
        same_class, adjacent, desc_overlap
    )

    return Factor2Score(
        same_class          = same_class,
        adjacent_class      = adjacent,
        description_overlap = round(desc_overlap, 3),
        composite_score     = round(composite,    3),
        notes               = notes,
    )


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _has_adjacent(a: set[str], b: set[str]) -> bool:
    for ca in a:
        for cb in b:
            if frozenset({ca, cb}) in ADJACENT_CLASSES:
                return True
    return False


def _description_overlap(desc_a: str, desc_b: str) -> float:
    """Jaccard similarity on meaningful words in the two descriptions."""
    if not desc_a or not desc_b:
        return 0.0
    words_a = _keywords(desc_a)
    words_b = _keywords(desc_b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union        = words_a | words_b
    return len(intersection) / len(union)


def _keywords(text: str) -> set[str]:
    """Extract meaningful lowercase words (3+ chars, not stopwords)."""
    stopwords = {"the", "and", "for", "of", "in", "a", "an", "or", "with"}
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {w for w in words if w not in stopwords}


def _build_notes(
    applied: list[str], conflicting: list[str],
    same: bool, adjacent: bool, desc: float
) -> str:
    parts = [f"Applied classes: {applied}. Conflicting classes: {conflicting}."]
    if same:
        parts.append("Same IC class — goods/services directly competitive.")
    elif adjacent:
        parts.append("Adjacent IC classes — goods/services commonly related in trade.")
    else:
        parts.append("No IC class overlap or adjacency detected.")
    if desc >= 0.30:
        parts.append(f"Description keyword overlap: {desc:.0%}.")
    return " ".join(parts)
