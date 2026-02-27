# similarity/section_1207_subsections.py
"""
TMEP §1207 Subsections
======================
§1207.02 — Marks That Are Likely to Deceive
§1207.03 — Marks Previously Used in US but Not Registered
§1207.04 — Concurrent Use Registration

Each section is a self-contained analyser that takes the §704.02 output
and the application data as input, and returns a typed analysis dataclass.
"""

from __future__ import annotations
import re
from similarity.models import (
    DeceptionAnalysis, DeceptionType,
    UnregisteredMarkAnalysis,
    ConcurrentUseAnalysis, ConcurrentUseType,
)


# ──────────────────────────────────────────────────────────────────────────────
# §1207.02 — MARKS LIKELY TO DECEIVE
# ──────────────────────────────────────────────────────────────────────────────
"""
Legal standard (TMEP §1207.02):
A mark is deceptive under §2(a) if:
  1. The mark misdescribes a quality/feature of the goods
  2. Prospective purchasers are likely to believe the misdescription
  3. The misdescription is material to purchasing decisions

Unlike §2(d) confusion, deception is an absolute bar to registration.
"""

# Terms that are potentially misdescriptive if the goods don't contain them
_GEOGRAPHIC_TERMS = {
    "PARIS", "FRENCH", "ITALIAN", "SWISS", "LONDON", "AMERICAN",
    "BOSTON", "TEXAS", "FLORIDA", "CALIFORNIA", "COLORADO",
    "GERMAN", "JAPANESE", "KOREAN", "CHINESE", "RUSSIAN",
}

_MATERIAL_TERMS = {
    "GOLD", "SILVER", "DIAMOND", "PLATINUM", "LEATHER",
    "SILK", "CASHMERE", "WOOL", "COTTON", "LINEN",
    "BAMBOO", "TEAK", "MAHOGANY", "CRYSTAL", "BRONZE",
}

_INGREDIENT_TERMS = {
    "HONEY", "VANILLA", "ALOE", "VITAMIN", "HERBAL", "ORGANIC",
    "NATURAL", "FRESH", "PURE", "EXTRA VIRGIN", "AGED",
}


def analyse_1207_02(
    applied_mark:        str,
    goods_description:   str,
    ic_classes:          list[str],
) -> DeceptionAnalysis:
    """
    §1207.02 — Screens the applied-for mark for deceptive matter.

    Checks:
      1. Geographic deception — does mark claim a geographic origin
         the goods don't actually have?
      2. Material deception — does mark claim a material/ingredient
         the goods don't actually contain?

    Args:
        applied_mark:       The trademark text
        goods_description:  Goods/services description from application
        ic_classes:         IC classes

    Returns:
        DeceptionAnalysis
    """
    mark_words  = set(re.findall(r"[A-Z]+", applied_mark.upper()))
    desc_lower  = goods_description.lower()

    # ── Check geographic deception ────────────────────────────────────────────
    geo_terms_in_mark = mark_words & _GEOGRAPHIC_TERMS
    if geo_terms_in_mark:
        term = next(iter(geo_terms_in_mark))
        # Does the description confirm genuine geographic connection?
        genuine = term.lower() in desc_lower or "made in" in desc_lower
        if not genuine:
            return DeceptionAnalysis(
                deception_detected          = True,
                deception_type              = DeceptionType.GEOGRAPHIC,
                misdescriptive_term         = term,
                goods_actually_contain      = False,
                purchaser_likely_to_believe = True,
                materiality_to_purchase     = True,
                refusal_recommended         = True,
                legal_basis                 = "Trademark Act §2(a); TMEP §1207.02",
                notes = (
                    f"Mark contains geographic term '{term}' but goods description "
                    f"does not confirm genuine {term} origin. "
                    f"Deceptive under §2(a) — absolute bar to registration."
                ),
            )

    # ── Check material / ingredient deception ─────────────────────────────────
    for term in (_MATERIAL_TERMS | _INGREDIENT_TERMS):
        if term in mark_words:
            genuine = term.lower() in desc_lower
            if not genuine:
                return DeceptionAnalysis(
                    deception_detected          = True,
                    deception_type              = DeceptionType.INSTITUTION,
                    misdescriptive_term         = term,
                    goods_actually_contain      = False,
                    purchaser_likely_to_believe = True,
                    materiality_to_purchase     = True,
                    refusal_recommended         = True,
                    legal_basis                 = "Trademark Act §2(a); TMEP §1207.02",
                    notes = (
                        f"Mark contains term '{term}' suggesting goods contain/are made of "
                        f"{term}, but goods description does not confirm this. "
                        f"Potentially deceptive under §2(a)."
                    ),
                )

    return DeceptionAnalysis(
        deception_detected  = False,
        deception_type      = DeceptionType.NONE,
        refusal_recommended = False,
        notes               = "No deceptive matter detected in mark text.",
    )


# ──────────────────────────────────────────────────────────────────────────────
# §1207.03 — MARKS PREVIOUSLY USED IN US BUT NOT REGISTERED
# ──────────────────────────────────────────────────────────────────────────────
"""
Legal standard (TMEP §1207.03):
Under §2(d), confusion is also barred against marks PREVIOUSLY USED in
the US even if not registered, provided the prior user has established
common-law rights through bona fide use in commerce.

A §704.02 search may surface pending or cancelled marks that still carry
common-law rights. This section flags those conflicts.
"""

_DEAD_STATUSES = {"dead", "abandoned", "cancelled", "expired"}


def analyse_1207_03(
    conflict_set: list[dict],
    applied_classes: list[str],
) -> UnregisteredMarkAnalysis:
    """
    §1207.03 — Identifies conflicts from prior use marks not currently registered.

    Looks for conflicts in the §704.02 conflict_set that:
      - Have status "dead" / "abandoned" (may still have common-law rights)
      - Are in the same IC class as the applied-for mark

    Args:
        conflict_set:     List of conflict dicts from §704.02 output
        applied_classes:  IC classes of the applied-for mark

    Returns:
        UnregisteredMarkAnalysis
    """
    applied_set  = set(applied_classes)
    prior_use_conflicts = []

    for c in conflict_set:
        status         = str(c.get("status") or "").lower()
        conflict_classes = set(c.get("ic_classes") or [])
        filing_date    = c.get("filing_date") or ""

        # Flag dead marks in same class — may still have common-law rights
        if status in _DEAD_STATUSES and (conflict_classes & applied_set):
            prior_use_conflicts.append({
                "application_number": c.get("application_number"),
                "mark_text":          c.get("mark_text"),
                "status":             status,
                "filing_date":        filing_date,
            })

    if prior_use_conflicts:
        earliest = sorted(prior_use_conflicts, key=lambda x: x["filing_date"])
        first    = earliest[0]
        return UnregisteredMarkAnalysis(
            prior_use_detected    = True,
            prior_use_territory   = "United States (nationwide presumed)",
            prior_use_date        = first["filing_date"],
            conflict_with_applied = True,
            refusal_recommended   = True,
            legal_basis           = "Trademark Act §2(d); TMEP §1207.03",
            notes = (
                f"{len(prior_use_conflicts)} dead/abandoned mark(s) in same IC class detected. "
                f"Earliest: '{first['mark_text']}' (filed {first['filing_date']}). "
                f"Prior user may retain common-law rights despite abandonment. "
                f"Examiner should investigate whether use in commerce has continued."
            ),
        )

    return UnregisteredMarkAnalysis(
        prior_use_detected    = False,
        conflict_with_applied = False,
        refusal_recommended   = False,
        notes = "No prior-use unregistered conflicts detected in same IC class.",
    )


# ──────────────────────────────────────────────────────────────────────────────
# §1207.04 — CONCURRENT USE REGISTRATION
# ──────────────────────────────────────────────────────────────────────────────
"""
Legal standard (TMEP §1207.04):
An applicant who has used a mark concurrently with another user in
different geographic areas may be entitled to a concurrent use
registration limiting the registration to a specific territory.

Concurrent use is available ONLY if:
  - Applicant used the mark before the conflicting mark's registration date
  - OR the conflicting registrant consents
  - AND the geographic areas of use do not overlap
"""


def analyse_1207_04(
    applied_mark:        str,
    applied_classes:     list[str],
    conflict_set:        list[dict],
    geographic_area_applied: str = "United States",
) -> ConcurrentUseAnalysis:
    """
    §1207.04 — Evaluates whether concurrent use registration is possible.

    Concurrent use is possible when:
      1. Conflicts exist (otherwise no need for concurrent use)
      2. The applicant's geographic area differs from the conflicting user's area
      3. No overlap in geographic territories

    Args:
        applied_mark:             Applied-for mark text
        applied_classes:          IC classes
        conflict_set:             Conflicts from §704.02
        geographic_area_applied:  Where applicant uses the mark

    Returns:
        ConcurrentUseAnalysis
    """
    applied_set = set(applied_classes)

    # Only relevant if there are same-class conflicts
    same_class_conflicts = [
        c for c in conflict_set
        if set(c.get("ic_classes") or []) & applied_set
        and str(c.get("status") or "").lower() in ("registered", "pending")
    ]

    if not same_class_conflicts:
        return ConcurrentUseAnalysis(
            concurrent_use_possible = False,
            use_type                = ConcurrentUseType.NOT_APPLICABLE,
            notes = "No same-class active conflicts — concurrent use registration not applicable.",
        )

    # Geographic analysis
    # In real implementation this would parse TSDR geographic use statements.
    # Here we flag the possibility and recommend examiner investigation.
    conflict_areas = [
        c.get("owner_name", "Unknown owner") for c in same_class_conflicts
    ]

    areas_overlap = geographic_area_applied.lower() == "united states"
    # Full US coverage → overlap is likely → concurrent use harder to obtain

    can_be_concurrent = not areas_overlap

    return ConcurrentUseAnalysis(
        concurrent_use_possible     = can_be_concurrent,
        use_type                    = (
            ConcurrentUseType.GEOGRAPHIC_LIMITATION
            if can_be_concurrent
            else ConcurrentUseType.NOT_APPLICABLE
        ),
        geographic_area_applied     = geographic_area_applied,
        geographic_area_conflicting = "Unknown — examiner investigation required",
        areas_overlap               = areas_overlap,
        prior_user_consent_obtained = False,
        registration_possible       = can_be_concurrent,
        notes = (
            f"{len(same_class_conflicts)} same-class active conflict(s). "
            + (
                "Geographic areas appear to overlap — concurrent use registration "
                "unlikely without consent of prior registrant. "
                "Applicant may submit consent agreement under TMEP §1207.04."
                if areas_overlap else
                "Potentially distinct geographic areas — concurrent use investigation warranted. "
                "See TMEP §1207.04 for concurrent use application requirements."
            )
        ),
    )
