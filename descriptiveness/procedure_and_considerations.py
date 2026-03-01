# descriptiveness/procedure_and_considerations.py
"""
TMEP §1209.02 — Procedure for Descriptiveness and/or Genericness Refusal
TMEP §1209.03 — Considerations Relevant to Determination

§1209.02 — Determines:
  - Which statutory ground (§2(e)(1), §2(e)(2), §2(e)(4), §2(e)(5))
  - Whether refusal is warranted
  - How applicant may overcome
  - Whether disclaimer is appropriate

§1209.03 — Gathers and weighs evidence:
  (a) Dictionary definitions
  (b) Trade publication / media usage
  (c) Applicant's own use of term descriptively
  (d) Competitor usage of same term
  (e) Whether term immediately conveys info about goods
  (f) Industry usage / need to use the term
"""

from __future__ import annotations
import re
from descriptiveness.models import (
    RefusalProcedureAnalysis, ConsiderationsAnalysis,
    DescriptiveEvidence, DistinctivenessLevel,
    RefusalGround, DescriptivenessType, OvercomeMethod,
)


# ──────────────────────────────────────────────────────────────────────────────
# GEOGRAPHIC TERMS — §2(e)(2)
# ──────────────────────────────────────────────────────────────────────────────

_GEOGRAPHIC_TERMS = {
    # US States
    "ALASKA", "ALABAMA", "ARIZONA", "ARKANSAS", "CALIFORNIA", "COLORADO",
    "CONNECTICUT", "DELAWARE", "FLORIDA", "GEORGIA", "HAWAII", "IDAHO",
    "ILLINOIS", "INDIANA", "IOWA", "KANSAS", "KENTUCKY", "LOUISIANA",
    "MAINE", "MARYLAND", "MASSACHUSETTS", "MICHIGAN", "MINNESOTA",
    "MISSISSIPPI", "MISSOURI", "MONTANA", "NEBRASKA", "NEVADA",
    "HAMPSHIRE", "JERSEY", "MEXICO", "YORK", "CAROLINA", "DAKOTA",
    "OHIO", "OKLAHOMA", "OREGON", "PENNSYLVANIA", "RHODE", "TENNESSEE",
    "TEXAS", "UTAH", "VERMONT", "VIRGINIA", "WASHINGTON", "WISCONSIN",
    "WYOMING",
    # Major cities
    "BOSTON", "CHICAGO", "DALLAS", "DENVER", "DETROIT", "HOUSTON",
    "MIAMI", "NASHVILLE", "ORLANDO", "PORTLAND", "SEATTLE", "PHOENIX",
    # Countries / regions
    "AMERICAN", "FRENCH", "ITALIAN", "GERMAN", "SWISS", "JAPANESE",
    "KOREAN", "CHINESE", "BRITISH", "ENGLISH", "IRISH", "AUSTRALIAN",
    "CANADIAN", "MEXICAN", "SPANISH", "DUTCH", "NORDIC", "SCANDINAVIAN",
    "EUROPEAN", "ASIAN", "LATIN", "TROPICAL", "ARCTIC", "ALPINE",
    "MEDITERRANEAN", "PACIFIC", "ATLANTIC",
    # International cities
    "PARIS", "LONDON", "ROME", "MILAN", "TOKYO", "BERLIN", "VIENNA",
    "BARCELONA", "AMSTERDAM", "SYDNEY", "TORONTO", "SEOUL", "BEIJING",
}

# Common surnames — §2(e)(4)
_COMMON_SURNAMES = {
    "SMITH", "JONES", "JOHNSON", "WILLIAMS", "BROWN", "DAVIS", "MILLER",
    "WILSON", "MOORE", "TAYLOR", "ANDERSON", "THOMAS", "JACKSON", "WHITE",
    "HARRIS", "MARTIN", "THOMPSON", "GARCIA", "MARTINEZ", "ROBINSON",
    "CLARK", "RODRIGUEZ", "LEWIS", "LEE", "WALKER", "HALL", "ALLEN",
    "YOUNG", "HERNANDEZ", "KING", "WRIGHT", "LOPEZ", "HILL", "SCOTT",
    "GREEN", "ADAMS", "BAKER", "GONZALEZ", "NELSON", "CARTER", "MITCHELL",
    "PEREZ", "ROBERTS", "TURNER", "PHILLIPS", "CAMPBELL", "PARKER", "EVANS",
    "EDWARDS", "COLLINS", "STEWART", "SANCHEZ", "MORRIS", "ROGERS", "REED",
    "COOK", "MORGAN", "BELL", "MURPHY", "BAILEY", "RIVERA", "COOPER",
    "COX", "HOWARD", "WARD", "TORRES", "PETERSON", "GRAY", "RAMIREZ",
    "JAMES", "WATSON", "BROOKS", "KELLY", "SANDERS", "PRICE", "BENNETT",
    "WOOD", "BARNES", "ROSS", "HENDERSON", "COLEMAN", "JENKINS", "PERRY",
}

# Functional terms — §2(e)(5) — shapes/features necessary for goods to work
_FUNCTIONAL_TERMS = {
    "GRIP", "HANDLE", "SPOUT", "NOZZLE", "VALVE", "HINGE", "LATCH",
    "SLOT", "PORT", "SOCKET", "CONNECTOR", "CLIP", "CLASP", "LATCH",
}


# ──────────────────────────────────────────────────────────────────────────────
# §1209.02 — REFUSAL PROCEDURE
# ──────────────────────────────────────────────────────────────────────────────

def analyse_procedure(
    mark_text:             str,
    goods_description:     str,
    ic_classes:            list[str],
    distinctiveness_level: DistinctivenessLevel,
    distinctiveness_score: float,
) -> RefusalProcedureAnalysis:
    """
    §1209.02 — Determines the correct §2(e) refusal ground and procedure.

    Decision tree:
      1. Generic?          → No refusal ground needed (absolute bar, §1209.01)
      2. Geographic?       → §2(e)(2)
      3. Surname?          → §2(e)(4)
      4. Functional?       → §2(e)(5)
      5. Merely descriptive? → §2(e)(1)
      6. Distinctive?      → No refusal
    """
    words = re.findall(r"[A-Za-z]+", mark_text.upper())

    # ── GENERIC — Absolute bar ────────────────────────────────────────────────
    if distinctiveness_level == DistinctivenessLevel.GENERIC:
        return RefusalProcedureAnalysis(
            refusal_warranted      = True,
            refusal_ground         = RefusalGround.GENERIC_REFUSAL,
            descriptiveness_type   = DescriptivenessType.GENERIC,
            statutory_basis        = "Trademark Act §1, §2, §45; 15 U.S.C. §1051-1052, §1127",
            is_absolute_bar        = True,
            overcome_methods       = [OvercomeMethod.NOT_OVERCOMEABLE],
            disclaimer_required    = False,
            acquired_distinctiveness_possible = False,
            procedure_notes = (
                "Generic mark — incapable of registration on either the Principal "
                "or Supplemental Register. No form of evidence can make a generic "
                "term registrable. Refusal is final. "
                "See In re Merrill Lynch, Pierce, Fenner & Smith Inc., "
                "828 F.2d 1567 (Fed. Cir. 1987)."
            ),
        )

    # ── GEOGRAPHIC — §2(e)(2) ─────────────────────────────────────────────────
    geo_words = [w for w in words if w in _GEOGRAPHIC_TERMS]
    if geo_words:
        term = geo_words[0]
        # Geographic descriptiveness requires goods/place association
        goods_upper = goods_description.upper()
        associated  = term in goods_upper or any(
            c in ["029", "030", "031", "003", "033", "025", "014"] for c in ic_classes
        )
        if associated:
            return RefusalProcedureAnalysis(
                refusal_warranted      = True,
                refusal_ground         = RefusalGround.SECTION_2E2_GEOGRAPHIC,
                descriptiveness_type   = DescriptivenessType.PRIMARILY_GEOGRAPHIC,
                statutory_basis        = "Trademark Act §2(e)(2); 15 U.S.C. §1052(e)(2)",
                is_absolute_bar        = False,
                overcome_methods       = [
                    OvercomeMethod.SECTION_2F_ACQUIRED,
                    OvercomeMethod.SUPPLEMENTAL_REGISTER,
                    OvercomeMethod.ARGUMENT_ON_MERITS,
                ],
                disclaimer_required    = False,
                acquired_distinctiveness_possible = True,
                procedure_notes = (
                    f"Mark contains geographic term '{term}' that is primarily "
                    f"geographically descriptive of the goods' origin. "
                    f"Applicant may overcome with §2(f) acquired distinctiveness "
                    f"or seek registration on the Supplemental Register. "
                    f"TMEP §1210."
                ),
            )

    # ── SURNAME — §2(e)(4) ────────────────────────────────────────────────────
    surname_words = [w for w in words if w in _COMMON_SURNAMES]
    if surname_words and len(surname_words) / max(len(words), 1) >= 0.50:
        term = surname_words[0]
        return RefusalProcedureAnalysis(
            refusal_warranted      = True,
            refusal_ground         = RefusalGround.SECTION_2E4_SURNAME,
            descriptiveness_type   = DescriptivenessType.PRIMARILY_SURNAME,
            statutory_basis        = "Trademark Act §2(e)(4); 15 U.S.C. §1052(e)(4)",
            is_absolute_bar        = False,
            overcome_methods       = [
                OvercomeMethod.SECTION_2F_ACQUIRED,
                OvercomeMethod.SUPPLEMENTAL_REGISTER,
                OvercomeMethod.ARGUMENT_ON_MERITS,
            ],
            disclaimer_required    = False,
            acquired_distinctiveness_possible = True,
            procedure_notes = (
                f"Mark '{mark_text}' is primarily merely a surname. "
                f"'{term}' appears as a surname in telephone directories and "
                f"public records. Consumers would perceive this primarily as a surname "
                f"rather than a source identifier. Overcome with §2(f) or "
                f"Supplemental Register. TMEP §1211."
            ),
        )

    # ── MERELY DESCRIPTIVE — §2(e)(1) ────────────────────────────────────────
    if distinctiveness_level == DistinctivenessLevel.DESCRIPTIVE:
        # Determine if disclaimer alone is sufficient
        # A disclaimer is appropriate when only PART of the mark is descriptive
        partial_only = distinctiveness_score > 0.30   # has some distinctive elements
        disclaimer_ok = partial_only

        return RefusalProcedureAnalysis(
            refusal_warranted      = True,
            refusal_ground         = RefusalGround.SECTION_2E1_DESCRIPTIVE,
            descriptiveness_type   = DescriptivenessType.MERELY_DESCRIPTIVE,
            statutory_basis        = "Trademark Act §2(e)(1); 15 U.S.C. §1052(e)(1)",
            is_absolute_bar        = False,
            overcome_methods       = [
                OvercomeMethod.SECTION_2F_ACQUIRED,
                OvercomeMethod.SUPPLEMENTAL_REGISTER,
                OvercomeMethod.ARGUMENT_ON_MERITS,
                *(  [OvercomeMethod.AMENDMENT_TO_MARK]
                    if disclaimer_ok else [] ),
            ],
            disclaimer_required    = disclaimer_ok,
            acquired_distinctiveness_possible = True,
            procedure_notes = (
                f"Mark '{mark_text}' is merely descriptive of the goods/services "
                f"under §2(e)(1). The mark immediately conveys information about "
                f"a quality, feature, or characteristic of the goods. "
                + (
                    "A disclaimer of the descriptive term(s) may be required "
                    "if other distinctive elements are present. "
                    if disclaimer_ok else ""
                ) +
                "Applicant may overcome by submitting evidence of §2(f) "
                "acquired distinctiveness or amending to the Supplemental Register. "
                "TMEP §1212 (acquired distinctiveness evidence requirements)."
            ),
        )

    # ── NO REFUSAL ────────────────────────────────────────────────────────────
    return RefusalProcedureAnalysis(
        refusal_warranted      = False,
        refusal_ground         = RefusalGround.NONE,
        descriptiveness_type   = DescriptivenessType.NONE,
        statutory_basis        = "",
        is_absolute_bar        = False,
        overcome_methods       = [],
        disclaimer_required    = False,
        acquired_distinctiveness_possible = False,
        procedure_notes = (
            f"Mark '{mark_text}' is {distinctiveness_level.value.lower()}. "
            f"No §2(e) descriptiveness refusal warranted."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# §1209.03 — CONSIDERATIONS / EVIDENCE ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────

def analyse_considerations(
    mark_text:         str,
    goods_description: str,
    ic_classes:        list[str],
) -> ConsiderationsAnalysis:
    """
    §1209.03 — Gathers and weighs evidence relevant to descriptiveness.

    In production, this would query:
      - USPTO TSDR database for applicant's own use
      - Online dictionaries (Merriam-Webster, Dictionary.com)
      - Google/Bing for trade publication usage
      - USPTO TESS for how other registrants use the term

    Here we analyse the mark text and goods description to simulate the
    evidence-gathering process with structured dummy findings.

    TMEP §1209.03 key considerations:
      (a) whether the term appears in the dictionary
      (b) whether applicant uses the term to describe goods
      (c) whether competitors use same or similar terms
      (d) whether the term is commonly used in the relevant industry
      (e) whether the mark immediately conveys info about the goods
    """
    words       = re.findall(r"[A-Za-z]+", mark_text.upper())
    desc_upper  = goods_description.upper()

    # ── Simulate dictionary evidence ──────────────────────────────────────────
    dict_evidence: list[DescriptiveEvidence] = []
    known_desc_words = _get_known_descriptive_words(words, ic_classes)
    for word in known_desc_words:
        dict_evidence.append(DescriptiveEvidence(
            source  = "dictionary",
            excerpt = (
                f"'{word}': Merriam-Webster defines this as a common English word "
                f"directly describing a characteristic of goods in this category."
            ),
            weight  = 0.80,
            url     = f"https://www.merriam-webster.com/dictionary/{word.lower()}",
            date    = "n/a",
        ))

    # ── Simulate trade publication usage ──────────────────────────────────────
    trade_evidence: list[DescriptiveEvidence] = []
    words_in_desc = [w for w in words if w in desc_upper]
    if words_in_desc:
        for word in words_in_desc:
            trade_evidence.append(DescriptiveEvidence(
                source  = "trade_publication",
                excerpt = (
                    f"Industry publications in the relevant field routinely use "
                    f"'{word}' to describe products of this type without trademark "
                    f"significance."
                ),
                weight  = 0.70,
                url     = "",
                date    = "n/a",
            ))

    # ── Simulate applicant usage evidence ─────────────────────────────────────
    applicant_evidence: list[DescriptiveEvidence] = []
    if words_in_desc:
        applicant_evidence.append(DescriptiveEvidence(
            source  = "applicant_usage",
            excerpt = (
                f"Applicant's own specimen/description uses '{words_in_desc[0]}' "
                f"in a descriptive manner to identify a feature of the goods, "
                f"not as a source indicator."
            ),
            weight  = 0.90,    # Applicant's own descriptive use is highly probative
            url     = "",
            date    = "n/a",
        ))

    # ── Simulate competitor usage evidence ────────────────────────────────────
    competitor_evidence: list[DescriptiveEvidence] = []
    for word in known_desc_words[:2]:   # limit to 2 for brevity
        competitor_evidence.append(DescriptiveEvidence(
            source  = "competitor_usage",
            excerpt = (
                f"A search of the USPTO register reveals multiple third-party "
                f"registrations and applications using '{word}' descriptively "
                f"for similar goods, indicating competitors need to use this term."
            ),
            weight  = 0.65,
            url     = "https://www.uspto.gov/trademarks/search",
            date    = "n/a",
        ))

    # ── Compute evidence strength ─────────────────────────────────────────────
    all_evidence = (dict_evidence + trade_evidence +
                    applicant_evidence + competitor_evidence)
    if all_evidence:
        total_weight = sum(e.weight for e in all_evidence)
        evidence_strength = min(1.0, total_weight / (len(all_evidence) * 1.0))
    else:
        evidence_strength = 0.0

    immediately_conveys = bool(words_in_desc)
    used_in_trade       = bool(trade_evidence)
    applicant_used      = bool(applicant_evidence)
    competitors_use     = bool(competitor_evidence)

    notes = _build_considerations_notes(
        mark_text, immediately_conveys, used_in_trade,
        applicant_used, competitors_use, evidence_strength
    )

    return ConsiderationsAnalysis(
        dictionary_evidence       = dict_evidence,
        trade_usage_evidence      = trade_evidence,
        applicant_usage_evidence  = applicant_evidence,
        competitor_usage_evidence = competitor_evidence,
        dictionary_definitions_found = bool(dict_evidence),
        used_descriptively_in_trade  = used_in_trade,
        applicant_used_descriptively = applicant_used,
        competitors_use_same_term    = competitors_use,
        immediately_conveys_info     = immediately_conveys,
        evidence_strength            = round(evidence_strength, 3),
        total_evidence_count         = len(all_evidence),
        analysis_notes               = notes,
    )


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

_UNIVERSAL_DESCRIPTIVE = {
    "FRESH", "PURE", "CLEAN", "NATURAL", "ORGANIC", "HEALTHY", "PREMIUM",
    "QUALITY", "CLASSIC", "TRADITIONAL", "ORIGINAL", "GENUINE", "AUTHENTIC",
    "ADVANCED", "INNOVATIVE", "NEW", "IMPROVED", "BETTER", "BEST", "GREAT",
    "FAST", "QUICK", "EASY", "SIMPLE", "SAFE", "SECURE", "RELIABLE",
    "SMART", "INTELLIGENT", "PROFESSIONAL", "EXPERT", "MASTER", "ULTRA",
    "SUPER", "MEGA", "MAXI", "MINI", "MICRO", "NANO", "PLUS", "PRO",
    "MAX", "PRIME", "ELITE", "ULTIMATE", "COMPLETE", "TOTAL", "FULL",
    "LIGHT", "LITE", "STRONG", "BOLD", "BRIGHT", "CLEAR", "SOFT", "SMOOTH",
    "RICH", "GOLDEN", "VALUE", "BUDGET", "DIRECT", "ONLINE", "DIGITAL",
    "DAILY", "EXPRESS", "RAPID", "INSTANT", "GLOBAL",
}


def _get_known_descriptive_words(words: list[str], ic_classes: list[str]) -> list[str]:
    result = []
    for w in words:
        if w in _UNIVERSAL_DESCRIPTIVE and w not in result:
            result.append(w)
    return result


def _build_considerations_notes(
    mark: str, immediately: bool, trade: bool,
    applicant: bool, competitors: bool, strength: float,
) -> str:
    parts = [f"§1209.03 considerations analysis for '{mark}'."]
    if immediately:
        parts.append("Mark immediately conveys information about the goods.")
    if applicant:
        parts.append(
            "Applicant's own usage suggests descriptive rather than "
            "trademark use."
        )
    if trade:
        parts.append("Term used descriptively in trade publications.")
    if competitors:
        parts.append("Competitors use same/similar terms — supports descriptiveness.")
    parts.append(f"Overall evidence strength: {strength:.0%}.")
    return " ".join(parts)
