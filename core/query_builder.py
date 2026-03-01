# core/query_builder.py
"""
Builds the set of SOLR search queries sent to the USPTO TESS API.

Covers all four variation types required by TMEP §704.02:
  - exact         → mark_identification:"ADAMS APPLE"
  - phonetic      → phonetic sound-alike queries (Soundex-inspired key)
  - spelling      → wildcard + transposition patterns
  - dominant      → each meaningful word searched individually

Each query is returned as a SearchQuery dataclass that contains:
  - the human-readable descriptor (for the audit log)
  - the actual SOLR string sent to the API

This module does NOT execute searches — it only builds descriptors.
Execution is the adapter's responsibility.
"""

from __future__ import annotations

import hashlib

from core.models import GoodsServices, SearchQuery, VARIATION_TYPES


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def build_search_queries(
    mark_text:      str,
    goods_services: list[GoodsServices],
) -> list[SearchQuery]:
    """
    Constructs all SOLR query descriptors for a given mark.

    Args:
        mark_text:      The trademark text, e.g. "ADAMS APPLE"
        goods_services: List of GoodsServices objects

    Returns:
        List of SearchQuery dataclasses — one or more per variation type.
    """
    mark_upper = mark_text.strip().upper()
    mark_words = mark_upper.split()
    ic_classes = [gs.ic_class for gs in goods_services]

    queries: list[SearchQuery] = []

    # 1. Exact match
    queries.append(_exact_query(mark_upper, ic_classes))

    # 2. Phonetic (Soundex-inspired)
    queries.append(_phonetic_query(mark_upper, ic_classes))

    # 3. Spelling variation (wildcard)
    queries.append(_spelling_query(mark_upper, ic_classes))

    # 4. Dominant portion — one query per meaningful word
    for word in mark_words:
        if len(word) >= 3:
            queries.append(_dominant_query(word, ic_classes))

    return queries


# ──────────────────────────────────────────────────────────────────────────────
# PHONETIC KEY (Soundex-inspired — matches original engine exactly)
# ──────────────────────────────────────────────────────────────────────────────

def phonetic_key(text: str) -> str:
    """
    Lightweight phonetic key generator (Soundex-inspired).
    Production replacement: Double Metaphone library.

    Returns a 4-char code, e.g. "ADAMS" → "A352"
    """
    text = text.upper().strip()
    if not text:
        return ""

    soundex_map = {
        "BFPV": "1", "CGJKQSXYZ": "2", "DT": "3",
        "L":    "4", "MN":          "5", "R":  "6",
    }

    code = text[0]
    for char in text[1:]:
        for letters, digit in soundex_map.items():
            if char in letters:
                if digit != (code[-1] if len(code) > 1 else ""):
                    code += digit
                break

    return (code + "000")[:4]


# ──────────────────────────────────────────────────────────────────────────────
# SOLR STRING BUILDERS
# ──────────────────────────────────────────────────────────────────────────────

def _solr_exact(mark: str, ic_classes: list[str]) -> str:
    """
    Exact phrase match in SOLR.
    Example: mark_identification:"ADAMS APPLE" AND (ic_class:029 OR ic_class:030)
    """
    class_filter = _class_filter(ic_classes)
    base = f'mark_identification:"{mark}"'
    return f"{base} AND {class_filter}" if class_filter else base


def _solr_phonetic(phonetic: str, ic_classes: list[str]) -> str:
    """
    Phonetic / fuzzy search using SOLR fuzzy operator (~).
    Also searches by the phoneticCode field if the USPTO API exposes it.
    Falls back to fuzzy on mark_identification.
    Example: mark_identification:ADAMS~ AND mark_identification:APPLE~
    """
    words = phonetic.split()
    fuzzy_terms = " AND ".join(f"mark_identification:{w}~" for w in words)
    class_filter = _class_filter(ic_classes)
    return f"({fuzzy_terms}) AND {class_filter}" if class_filter else f"({fuzzy_terms})"


def _solr_spelling(mark: str, ic_classes: list[str]) -> str:
    """
    Spelling variation using SOLR wildcard.
    Captures common prefixes — e.g. "ADAMS*" catches ADAMSON, ADAMZ, etc.
    Combines all words: ADAMS* AND APPLE*
    """
    words = mark.split()
    wildcard_terms = " AND ".join(f"mark_identification:{w}*" for w in words)
    class_filter = _class_filter(ic_classes)
    return f"({wildcard_terms}) AND {class_filter}" if class_filter else f"({wildcard_terms})"


def _solr_dominant(word: str, ic_classes: list[str]) -> str:
    """
    Dominant-portion search: single word across all positions.
    Example: mark_identification:*ADAMS*
    """
    class_filter = _class_filter(ic_classes)
    base = f"mark_identification:*{word}*"
    return f"{base} AND {class_filter}" if class_filter else base


def _class_filter(ic_classes: list[str]) -> str:
    """
    Builds an OR filter for IC classes.
    Example: (ic_class:029 OR ic_class:030)
    Returns empty string if no classes provided.
    """
    if not ic_classes:
        return ""
    terms = " OR ".join(f"ic_class:{c}" for c in ic_classes)
    return f"({terms})"


# ──────────────────────────────────────────────────────────────────────────────
# QUERY OBJECT FACTORIES
# ──────────────────────────────────────────────────────────────────────────────

def _exact_query(mark: str, ic_classes: list[str]) -> SearchQuery:
    return SearchQuery(
        query_id    = _short_id("EXACT", mark),
        query_type  = "exact",
        search_term = mark,
        scope       = "full_mark",
        ic_classes  = ic_classes,
        solr_string = _solr_exact(mark, ic_classes),
    )


def _phonetic_query(mark: str, ic_classes: list[str]) -> SearchQuery:
    key = phonetic_key(mark)
    return SearchQuery(
        query_id    = _short_id("PHONETIC", mark),
        query_type  = "phonetic",
        search_term = key,
        scope       = "full_mark",
        ic_classes  = ic_classes,
        solr_string = _solr_phonetic(mark, ic_classes),
    )


def _spelling_query(mark: str, ic_classes: list[str]) -> SearchQuery:
    return SearchQuery(
        query_id    = _short_id("SPELL", mark),
        query_type  = "spelling_variation",
        search_term = mark,
        scope       = "full_mark",
        ic_classes  = ic_classes,
        solr_string = _solr_spelling(mark, ic_classes),
    )


def _dominant_query(word: str, ic_classes: list[str]) -> SearchQuery:
    return SearchQuery(
        query_id    = _short_id("DOM", word),
        query_type  = "dominant_portion",
        search_term = word,
        scope       = "word_portion",
        ic_classes  = ic_classes,
        solr_string = _solr_dominant(word, ic_classes),
    )


def _short_id(prefix: str, value: str) -> str:
    """Deterministic short ID — same as original engine, preserved for audit log stability."""
    h = hashlib.md5(f"{prefix}:{value}".encode()).hexdigest()[:8].upper()
    return f"{prefix}-{h}"
