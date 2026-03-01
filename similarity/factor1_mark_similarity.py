# similarity/factor1_mark_similarity.py
"""
TMEP §1207.01 — DuPont Factor 1: Similarity of the Marks

Evaluates three dimensions:
  1. Visual similarity   — how alike the marks look (Levenshtein distance)
  2. Phonetic similarity — how alike they sound (Soundex comparison)
  3. Meaning similarity  — do they share dominant / meaningful words

Legal standard (TMEP §1207.01(b)):
  Marks are compared in their entireties, but more weight is given to
  the dominant portion. Similarities in any one dimension can be enough
  to find the marks confusingly similar.

No external libraries required — all algorithms are self-contained.
"""

from __future__ import annotations
import re
from similarity.models import Factor1Score

# ──────────────────────────────────────────────────────────────────────────────
# WEIGHTS WITHIN FACTOR 1
# ──────────────────────────────────────────────────────────────────────────────
_W_VISUAL   = 0.40
_W_PHONETIC = 0.35
_W_MEANING  = 0.25

# Words legally considered "weak" / disclaimed — given less weight
_WEAK_WORDS = {
    "THE", "A", "AN", "AND", "OF", "FOR", "IN", "ON", "AT", "BY",
    "CO", "COMPANY", "CORP", "INC", "LLC", "LTD", "BRAND", "GROUP",
}


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def score_factor1(applied_mark: str, conflicting_mark: str) -> Factor1Score:
    """
    Computes DuPont Factor 1 score between two mark texts.

    Args:
        applied_mark:     The mark being examined  e.g. "ADAMS APPLE"
        conflicting_mark: The conflicting mark      e.g. "ADAMZ APPEL"

    Returns:
        Factor1Score with individual dimension scores + composite.
    """
    a = _normalise(applied_mark)
    b = _normalise(conflicting_mark)

    if not a or not b:
        return Factor1Score(notes="One or both marks are empty.")

    visual   = _visual_similarity(a, b)
    phonetic = _phonetic_similarity(a, b)
    meaning, dom_match = _meaning_similarity(a, b)

    # Dominant word match boosts composite score
    boost = 0.05 if dom_match else 0.0

    composite = min(1.0, (
        visual   * _W_VISUAL +
        phonetic * _W_PHONETIC +
        meaning  * _W_MEANING +
        boost
    ))

    notes = _build_notes(a, b, visual, phonetic, meaning, dom_match)

    return Factor1Score(
        visual_similarity   = round(visual,    3),
        phonetic_similarity = round(phonetic,  3),
        meaning_similarity  = round(meaning,   3),
        dominant_word_match = dom_match,
        composite_score     = round(composite, 3),
        notes               = notes,
    )


# ──────────────────────────────────────────────────────────────────────────────
# VISUAL SIMILARITY — Levenshtein normalised
# ──────────────────────────────────────────────────────────────────────────────

def _visual_similarity(a: str, b: str) -> float:
    """
    Normalised Levenshtein distance → similarity score.
    score = 1.0 means identical, 0.0 means completely different.
    Compares full mark strings (spaces included).
    """
    dist = _levenshtein(a, b)
    max_len = max(len(a), len(b), 1)
    return 1.0 - (dist / max_len)


def _levenshtein(s: str, t: str) -> int:
    """Classic dynamic-programming Levenshtein edit distance."""
    m, n = len(s), len(t)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return dp[n]


# ──────────────────────────────────────────────────────────────────────────────
# PHONETIC SIMILARITY — Soundex comparison
# ──────────────────────────────────────────────────────────────────────────────

def _phonetic_similarity(a: str, b: str) -> float:
    """
    Compares Soundex codes of each word pair.
    For multi-word marks, takes the average similarity across word pairs.
    """
    words_a = [w for w in a.split() if w not in _WEAK_WORDS]
    words_b = [w for w in b.split() if w not in _WEAK_WORDS]

    if not words_a or not words_b:
        return _soundex_pair_score(a.replace(" ", ""), b.replace(" ", ""))

    # Compare word by word (zip — shorter mark limits comparison)
    scores = []
    for wa, wb in zip(words_a, words_b):
        scores.append(_soundex_pair_score(wa, wb))

    # Also compare full-mark concatenation
    scores.append(_soundex_pair_score(
        "".join(words_a), "".join(words_b)
    ))

    return sum(scores) / len(scores)


def _soundex_pair_score(a: str, b: str) -> float:
    """1.0 if Soundex codes match, partial credit for first-char match."""
    sa, sb = _soundex(a), _soundex(b)
    if sa == sb:
        return 1.0
    if sa and sb and sa[0] == sb[0]:
        # First character matches — give partial credit based on digit overlap
        matching = sum(x == y for x, y in zip(sa[1:], sb[1:]))
        return 0.4 + (matching / 3) * 0.4
    return 0.0


def _soundex(text: str) -> str:
    """Standard Soundex algorithm — returns 4-char code."""
    text = re.sub(r"[^A-Z]", "", text.upper())
    if not text:
        return ""
    soundex_map = str.maketrans(
        "BFPVCGJKQSXZDTLMNR",
        "111122222222334556"
    )
    code  = text[0]
    prev  = text[0].translate(soundex_map)
    for ch in text[1:]:
        digit = ch.translate(soundex_map)
        if digit != "0" and digit != prev:
            code += digit
        prev = digit
        if len(code) == 4:
            break
    return (code + "000")[:4]


# ──────────────────────────────────────────────────────────────────────────────
# MEANING SIMILARITY — Dominant word overlap
# ──────────────────────────────────────────────────────────────────────────────

def _meaning_similarity(a: str, b: str) -> tuple[float, bool]:
    """
    Compares meaningful (non-weak) words between two marks.

    Returns:
        (score: float, dominant_word_match: bool)

    dominant_word_match = True if the FIRST meaningful word is identical,
    which under TMEP §1207.01(b)(viii) gives the marks a similar commercial
    impression regardless of other differences.
    """
    words_a = [w for w in a.split() if w not in _WEAK_WORDS]
    words_b = [w for w in b.split() if w not in _WEAK_WORDS]

    if not words_a or not words_b:
        return 0.0, False

    set_a = set(words_a)
    set_b = set(words_b)

    # Jaccard similarity on meaningful word sets
    intersection = set_a & set_b
    union        = set_a | set_b
    jaccard      = len(intersection) / len(union) if union else 0.0

    # Dominant word = first meaningful word
    dominant_match = words_a[0] == words_b[0]

    # Boost Jaccard if dominant word matches
    score = min(1.0, jaccard + (0.3 if dominant_match else 0.0))

    return score, dominant_match


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Uppercase, strip punctuation, collapse spaces."""
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _build_notes(
    a: str, b: str,
    visual: float, phonetic: float, meaning: float, dom_match: bool
) -> str:
    parts = [f"Comparing '{a}' vs '{b}'."]
    if visual   >= 0.85: parts.append("Visually highly similar.")
    elif visual >= 0.60: parts.append("Visually moderately similar.")
    else:                parts.append("Visually dissimilar.")

    if phonetic >= 0.80: parts.append("Phonetically highly similar.")
    elif phonetic >= 0.50: parts.append("Phonetically moderately similar.")

    if dom_match:
        parts.append("Dominant word is identical — strong commercial impression overlap.")
    elif meaning >= 0.50:
        parts.append("Significant word-meaning overlap detected.")

    return " ".join(parts)
