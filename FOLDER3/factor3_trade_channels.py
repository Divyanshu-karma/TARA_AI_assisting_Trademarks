# similarity/factor3_trade_channels.py
"""
TMEP §1207.01 — DuPont Factor 3: Trade Channels

If goods travel through the same channels (retail stores, online, direct),
consumers are more likely to encounter both marks and be confused.

Legal standard (TMEP §1207.01(a)(vi)):
  When the goods/services of the parties are identical, the trade channels
  are presumed to be the same unless the record indicates otherwise.
"""

from __future__ import annotations
from similarity.models import Factor3Score

# IC classes whose primary trade channels are general retail / mass market
_MASS_MARKET_CLASSES = {
    "029", "030", "031", "032", "033",  # Food & beverage
    "025", "018", "026", "027",          # Fashion / textiles
    "028", "016", "021",                 # Toys, stationery, household
    "003", "005",                        # Cosmetics, OTC pharma
}

# Classes sold primarily through specialised / professional channels
_SPECIALISED_CLASSES = {
    "010",  # Medical devices
    "001",  # Industrial chemicals
    "007",  # Industrial machinery
    "013",  # Firearms
    "015",  # Musical instruments (specialist retail)
}

# Service classes — online / professional channels
_SERVICE_CLASSES = {
    "035", "036", "037", "038", "039",
    "040", "041", "042", "043", "044", "045",
}


def score_factor3(
    applied_classes:     list[str],
    conflicting_classes: list[str],
) -> Factor3Score:
    """
    Scores trade channel similarity.

    Rule:
      - Same IC class → presume same channels → score 0.90
      - Both in mass market classes → overlapping channels → 0.75
      - Both in service classes → online channels → 0.70
      - Both in specialised → possible overlap → 0.50
      - Mixed → low overlap → 0.25
    """
    applied_set     = set(applied_classes)
    conflicting_set = set(conflicting_classes)

    same_class   = bool(applied_set & conflicting_set)
    both_mass    = _all_in(applied_set, _MASS_MARKET_CLASSES) and \
                   _all_in(conflicting_set, _MASS_MARKET_CLASSES)
    both_service = _all_in(applied_set, _SERVICE_CLASSES) and \
                   _all_in(conflicting_set, _SERVICE_CLASSES)
    both_special = _all_in(applied_set, _SPECIALISED_CLASSES) and \
                   _all_in(conflicting_set, _SPECIALISED_CLASSES)

    if same_class:
        score    = 0.90
        same     = True
        overlap  = True
        notes    = "Same IC class — trade channels presumed identical per TMEP §1207.01(a)(vi)."
    elif both_mass:
        score    = 0.75
        same     = False
        overlap  = True
        notes    = "Both marks in mass-market classes — likely share retail/online channels."
    elif both_service:
        score    = 0.70
        same     = False
        overlap  = True
        notes    = "Both marks in service classes — likely share online/professional channels."
    elif both_special:
        score    = 0.50
        same     = False
        overlap  = True
        notes    = "Both in specialised channels — possible channel overlap."
    else:
        score    = 0.25
        same     = False
        overlap  = False
        notes    = "Different trade channel profiles — limited channel overlap expected."

    return Factor3Score(
        same_channels       = same,
        overlapping_channels = overlap,
        composite_score     = round(score, 3),
        notes               = notes,
    )


def _all_in(classes: set[str], target: set[str]) -> bool:
    return bool(classes) and all(c in target for c in classes)
