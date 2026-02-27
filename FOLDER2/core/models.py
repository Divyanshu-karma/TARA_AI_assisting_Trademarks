# core/models.py
"""
Shared data models, enumerations, and constants.
Extracted from the original search_authority_engine.py so they can be imported
by adapters, engine, validators, and tests without circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# LEGAL AUTHORITY CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

AUTHORITY_REFERENCE  = "TMEP §704.02"
LEGAL_BASIS_REVIVAL  = "TMEP §718.07"
DATABASE_NAME        = "USPTO TESS"

RECORDS_SEARCHED: list[str] = ["registered", "pending"]

VARIATION_TYPES: list[str] = [
    "exact",
    "phonetic",
    "spelling_variation",
    "dominant_portion",
]


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class EventTrigger(str, Enum):
    """
    Exhaustive list of events that legally mandate a §704.02 search.
    Source: TMEP §704.02 and §718.07
    """
    FIRST_REVIEW   = "first_review"       # Initial examination
    REVIVAL        = "revival"            # §718.07 — revived after abandonment
    AMENDMENT_GOODS = "amendment_goods"  # New goods / identification amended
    NEW_BASIS      = "new_basis"          # New filing basis added
    UNKNOWN        = "unknown"


# Sets for fast membership tests
SEARCH_TRIGGER_EVENTS: set[str] = {
    EventTrigger.FIRST_REVIEW,
    EventTrigger.REVIVAL,
    EventTrigger.AMENDMENT_GOODS,
    EventTrigger.NEW_BASIS,
}

RE_SEARCH_TRIGGERS: set[str] = {
    EventTrigger.REVIVAL,
    EventTrigger.AMENDMENT_GOODS,
    EventTrigger.NEW_BASIS,
}


# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class GoodsServices:
    """Single IC class entry inside an application."""
    ic_class:    str
    description: str

    @classmethod
    def from_dict(cls, d: dict) -> "GoodsServices":
        return cls(
            ic_class    = d.get("class", "UNKNOWN"),
            description = d.get("description", ""),
        )


@dataclass
class ApplicationPayload:
    """
    Validated, typed representation of an incoming trademark application.
    Created by validators.py after raw dict passes schema checks.
    """
    application_id:     str
    mark_text:          str
    mark_type:          str
    goods_services:     list[GoodsServices]
    event_trigger:      str
    application_status: str = ""


@dataclass
class ConflictRecord:
    """
    A single potentially-conflicting mark returned from the USPTO TESS search.
    Normalised from the raw API JSON by the adapter.
    """
    application_number:   str
    mark_text:            str
    status:               str           # "registered" | "pending"
    ic_classes:           list[str]
    registration_number:  str = ""
    filing_date:          str = ""
    registration_date:    str = ""
    owner_name:           str = ""
    surfaced_by_query_type: str = ""    # which variation type found this record


@dataclass
class SearchQuery:
    """
    Descriptor for a single search query sent to the USPTO TESS API.
    Used both for execution and for the audit log.
    """
    query_id:    str
    query_type:  str            # one of VARIATION_TYPES
    search_term: str
    scope:       str            # "full_mark" | "word_portion"
    ic_classes:  list[str]
    solr_string: str = ""       # the actual SOLR query string sent to the API
