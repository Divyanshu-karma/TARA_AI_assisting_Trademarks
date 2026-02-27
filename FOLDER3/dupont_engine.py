# similarity/dupont_engine.py
"""
TMEP §1207.01 — DuPont Engine
Combines all four DuPont factors into a weighted final score and decision.

Weights (legally calibrated):
    Factor 1 (Mark Similarity)    → 40%  — most important
    Factor 2 (Goods Relatedness)  → 35%  — second most important
    Factor 3 (Trade Channels)     → 15%
    Factor 4 (Purchase Conditions)→ 10%

Decision thresholds:
    >= 0.75 → LIKELY confusion    → §2(d) refusal recommended
    >= 0.50 → POSSIBLE confusion  → flag for manual review
    <  0.50 → UNLIKELY confusion  → cleared

Legal authority:
    In re E.I. du Pont de Nemours & Co., 476 F.2d 1357 (C.C.P.A. 1973)
    TMEP §1207.01
"""

from __future__ import annotations
from similarity.models import (
    ConflictAnalysis, ConfusionLikelihood, DuPontScores,
    Factor1Score, Factor2Score, Factor3Score, Factor4Score,
)
from similarity.factor1_mark_similarity    import score_factor1
from similarity.factor2_goods_relatedness  import score_factor2
from similarity.factor3_trade_channels     import score_factor3
from similarity.factor4_purchase_conditions import score_factor4

# ──────────────────────────────────────────────────────────────────────────────
# WEIGHTS
# ──────────────────────────────────────────────────────────────────────────────
W1 = 0.40   # Mark similarity
W2 = 0.35   # Goods relatedness
W3 = 0.15   # Trade channels
W4 = 0.10   # Purchase conditions

THRESHOLD_LIKELY   = 0.75
THRESHOLD_POSSIBLE = 0.50


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def analyse_conflict(
    applied_mark:         str,
    applied_classes:      list[str],
    applied_description:  str,
    conflict_record:      dict,
) -> ConflictAnalysis:
    """
    Runs full DuPont analysis for ONE conflict record vs the applied-for mark.

    Args:
        applied_mark:        Text of the applied-for mark  e.g. "ADAMS APPLE"
        applied_classes:     IC classes of applied-for     e.g. ["029"]
        applied_description: Goods description             e.g. "Dried fruits"
        conflict_record:     Dict from §704.02 conflict_set

    Returns:
        ConflictAnalysis with all scores + final decision
    """
    conflicting_mark    = conflict_record.get("mark_text",           "")
    conflicting_classes = conflict_record.get("ic_classes",          [])
    conflict_desc       = " ".join(conflicting_classes)   # fallback description

    # ── Score all 4 factors ───────────────────────────────────────────────────
    f1 = score_factor1(applied_mark, conflicting_mark)
    f2 = score_factor2(
        applied_classes, conflicting_classes,
        applied_description, conflict_desc,
    )
    f3 = score_factor3(applied_classes, conflicting_classes)
    f4 = score_factor4(applied_classes)

    # ── Weighted final score ─────────────────────────────────────────────────
    weighted = (
        f1.composite_score * W1 +
        f2.composite_score * W2 +
        f3.composite_score * W3 +
        f4.composite_score * W4
    )
    weighted = round(weighted, 4)

    # ── Decision ─────────────────────────────────────────────────────────────
    likelihood, confusion_likely, refusal = _decide(weighted)

    # ── Dominant factor ──────────────────────────────────────────────────────
    dom_factor = _dominant_factor(f1, f2, f3, f4)

    # ── Legal basis ─────────────────────────────────────────────────────────
    legal_basis = (
        "Trademark Act §2(d), 15 U.S.C. §1052(d); TMEP §1207.01(b)(i)"
        if refusal else ""
    )

    dupont = DuPontScores(
        factor1              = f1,
        factor2              = f2,
        factor3              = f3,
        factor4              = f4,
        weighted_final_score = weighted,
        dominant_factor      = dom_factor,
    )

    return ConflictAnalysis(
        application_number  = conflict_record.get("application_number", ""),
        conflicting_mark    = conflicting_mark,
        conflicting_status  = conflict_record.get("status",             ""),
        conflicting_classes = conflicting_classes,
        owner_name          = conflict_record.get("owner_name",         ""),
        dupont_scores       = dupont,
        confusion_likelihood = likelihood,
        confusion_likely    = confusion_likely,
        refusal_recommended = refusal,
        dominant_factor     = dom_factor,
        legal_basis         = legal_basis,
        examiner_notes      = _build_examiner_notes(
                                  applied_mark, conflicting_mark,
                                  weighted, likelihood, dom_factor
                              ),
    )


def serialise_analysis(ca: ConflictAnalysis) -> dict:
    """
    Converts a ConflictAnalysis dataclass → plain dict for JSON output.
    This is what §1207 returns in the conflict_analyses list.
    """
    d = ca.dupont_scores
    return {
        "application_number":  ca.application_number,
        "conflicting_mark":    ca.conflicting_mark,
        "conflicting_status":  ca.conflicting_status,
        "conflicting_classes": ca.conflicting_classes,
        "owner_name":          ca.owner_name,
        "dupont_scores": {
            "factor1_mark_similarity": {
                "visual":    d.factor1.visual_similarity,
                "phonetic":  d.factor1.phonetic_similarity,
                "meaning":   d.factor1.meaning_similarity,
                "dominant_word_match": d.factor1.dominant_word_match,
                "score":     d.factor1.composite_score,
                "notes":     d.factor1.notes,
            },
            "factor2_goods_relatedness": {
                "same_class":    d.factor2.same_class,
                "adjacent_class": d.factor2.adjacent_class,
                "desc_overlap":  d.factor2.description_overlap,
                "score":         d.factor2.composite_score,
                "notes":         d.factor2.notes,
            },
            "factor3_trade_channels": {
                "same_channels":       d.factor3.same_channels,
                "overlapping_channels": d.factor3.overlapping_channels,
                "score":               d.factor3.composite_score,
                "notes":               d.factor3.notes,
            },
            "factor4_purchase_conditions": {
                "buyer_sophistication": d.factor4.buyer_sophistication,
                "impulse_purchase":     d.factor4.impulse_purchase,
                "score":                d.factor4.composite_score,
                "notes":                d.factor4.notes,
            },
            "weighted_final_score": d.weighted_final_score,
            "dominant_factor":      d.dominant_factor,
        },
        "confusion_likelihood":  ca.confusion_likelihood.value,
        "confusion_likely":      ca.confusion_likely,
        "refusal_recommended":   ca.refusal_recommended,
        "legal_basis":           ca.legal_basis,
        "examiner_notes":        ca.examiner_notes,
    }


# ──────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _decide(score: float) -> tuple[ConfusionLikelihood, bool, bool]:
    if score >= THRESHOLD_LIKELY:
        return ConfusionLikelihood.LIKELY, True, True
    if score >= THRESHOLD_POSSIBLE:
        return ConfusionLikelihood.POSSIBLE, False, False
    return ConfusionLikelihood.UNLIKELY, False, False


def _dominant_factor(
    f1: Factor1Score, f2: Factor2Score,
    f3: Factor3Score, f4: Factor4Score,
) -> str:
    scores = {
        "factor1_mark_similarity":      f1.composite_score * W1,
        "factor2_goods_relatedness":    f2.composite_score * W2,
        "factor3_trade_channels":       f3.composite_score * W3,
        "factor4_purchase_conditions":  f4.composite_score * W4,
    }
    return max(scores, key=scores.get)


def _build_examiner_notes(
    applied: str, conflicting: str,
    score: float, likelihood: ConfusionLikelihood,
    dom_factor: str,
) -> str:
    lines = [
        f"Applied-for mark '{applied}' vs conflicting mark '{conflicting}'.",
        f"Weighted DuPont score: {score:.4f}.",
        f"Confusion likelihood: {likelihood.value}.",
        f"Dominant contributing factor: {dom_factor}.",
    ]
    if likelihood == ConfusionLikelihood.LIKELY:
        lines.append(
            "§2(d) refusal recommended. "
            "Applicant may overcome by submitting consent agreement or "
            "arguing differences in goods/channels."
        )
    elif likelihood == ConfusionLikelihood.POSSIBLE:
        lines.append(
            "Borderline case — manual examiner review recommended before issuing Office Action."
        )
    else:
        lines.append("Marks sufficiently distinct. No §2(d) refusal warranted on this conflict.")
    return " ".join(lines)
