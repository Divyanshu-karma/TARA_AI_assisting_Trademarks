# similarity/factor4_purchase_conditions.py
"""
TMEP §1207.01 — DuPont Factor 4: Conditions of Purchase

More careful buyers (expensive/specialised goods) are LESS likely to
be confused → LOWER confusion score.
Impulse buyers (cheap/everyday goods) are MORE likely to be confused
→ HIGHER confusion score.

Legal standard (TMEP §1207.01(a)(vii)):
  Purchaser sophistication and degree of care are relevant factors.
  Sophisticated purchasers with specialised knowledge are less easily
  confused, but ordinary consumers of everyday goods receive less protection.
"""

from __future__ import annotations
from similarity.models import Factor4Score

# IC classes mapped to purchase behaviour profile
# score = confusion contribution (higher = more easily confused)
_CLASS_PURCHASE_PROFILE: dict[str, tuple[str, float]] = {
    # Everyday / impulse purchase (high confusion risk)
    "029": ("ordinary", 0.80),   # Food
    "030": ("ordinary", 0.80),   # Food staples
    "031": ("ordinary", 0.75),   # Fresh produce
    "032": ("ordinary", 0.80),   # Non-alc beverages
    "033": ("ordinary", 0.70),   # Alcoholic beverages
    "003": ("ordinary", 0.75),   # Cosmetics
    "016": ("ordinary", 0.70),   # Stationery
    "028": ("ordinary", 0.72),   # Toys / games

    # Mid-range (moderate care)
    "025": ("ordinary", 0.60),   # Clothing
    "018": ("ordinary", 0.60),   # Leather goods / bags
    "021": ("ordinary", 0.60),   # Household items
    "014": ("ordinary", 0.55),   # Jewelry (some impulse, some considered)
    "012": ("sophisticated", 0.45), # Vehicles

    # Careful / professional purchase (low confusion risk)
    "005": ("sophisticated", 0.40),  # Pharmaceuticals
    "009": ("sophisticated", 0.45),  # Electronics / software
    "010": ("expert",        0.20),  # Medical devices
    "001": ("expert",        0.15),  # Industrial chemicals
    "007": ("expert",        0.15),  # Industrial machinery
    "013": ("expert",        0.10),  # Firearms

    # Services
    "035": ("ordinary",      0.60),  # Business services
    "036": ("sophisticated", 0.40),  # Financial services
    "037": ("ordinary",      0.55),  # Repair services
    "038": ("ordinary",      0.60),  # Telecom
    "041": ("ordinary",      0.65),  # Education / entertainment
    "042": ("sophisticated", 0.45),  # Software / tech services
    "043": ("ordinary",      0.72),  # Restaurant / food services
    "044": ("sophisticated", 0.35),  # Health / medical services
    "045": ("sophisticated", 0.35),  # Legal services
}

_DEFAULT_PROFILE = ("ordinary", 0.60)


def score_factor4(applied_classes: list[str]) -> Factor4Score:
    """
    Computes DuPont Factor 4 score based on the applied-for mark's IC classes.

    A HIGH score means ordinary consumer → MORE confusion risk.
    A LOW score means sophisticated buyer → LESS confusion risk.

    Args:
        applied_classes: IC classes of the applied-for mark

    Returns:
        Factor4Score
    """
    if not applied_classes:
        return Factor4Score(
            buyer_sophistication = "ordinary",
            impulse_purchase     = True,
            composite_score      = 0.60,
            notes                = "No IC class provided — assuming ordinary consumer.",
        )

    profiles = [_CLASS_PURCHASE_PROFILE.get(c, _DEFAULT_PROFILE) for c in applied_classes]
    sophistication_levels = [p[0] for p in profiles]
    scores                = [p[1] for p in profiles]

    avg_score = sum(scores) / len(scores)

    # Overall sophistication = most conservative (lowest score = most expert)
    if "expert" in sophistication_levels:
        overall = "expert"
    elif "sophisticated" in sophistication_levels:
        overall = "sophisticated"
    else:
        overall = "ordinary"

    impulse = avg_score >= 0.70

    notes = _build_notes(applied_classes, overall, avg_score, impulse)

    return Factor4Score(
        buyer_sophistication = overall,
        impulse_purchase     = impulse,
        composite_score      = round(avg_score, 3),
        notes                = notes,
    )


def _build_notes(classes: list[str], sophistication: str, score: float, impulse: bool) -> str:
    parts = [f"IC classes: {classes}."]
    if sophistication == "expert":
        parts.append("Expert/professional buyer — confusion highly unlikely per TMEP §1207.01(a)(vii).")
    elif sophistication == "sophisticated":
        parts.append("Sophisticated buyer — exercises care in purchase decisions.")
    else:
        parts.append("Ordinary consumer — applies standard care.")
    if impulse:
        parts.append("Impulse-purchase goods — increased confusion risk.")
    return " ".join(parts)
