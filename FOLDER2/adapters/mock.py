# adapters/mock.py
"""
Mock TESS Adapters for testing.
Replaces the inline MockConflictAdapter from the original tests.py.

Two mock variants are provided:
  - MockConflictAdapter   — returns fixed conflicts (matches original test fixture exactly)
  - EmptyTessAdapter      — returns no conflicts (tests the zero-conflict path)
  - ConfigurableMockAdapter — caller provides the conflict list (parametric tests)
"""

from __future__ import annotations

from core.models import ConflictRecord, SearchQuery
from adapters.base import TessAdapterBase


# ──────────────────────────────────────────────────────────────────────────────
# ORIGINAL MOCK — preserves exact behaviour from the old tests.py
# ──────────────────────────────────────────────────────────────────────────────

class MockConflictAdapter(TessAdapterBase):
    """
    Returns a fixed set of fake conflicts, identical to the original tests.py fixture.

    Exact query  → 2 records
    Phonetic     → 1 record  (deduplicated across all queries)
    Total        → 3 unique records
    """

    _EXACT_RECORDS = [
        ConflictRecord(
            application_number = "987654321",
            mark_text          = "ADAMS APPLE",
            status             = "registered",
            ic_classes         = ["029"],
        ),
        ConflictRecord(
            application_number = "876543219",
            mark_text          = "ADAMS APPLE CO",
            status             = "pending",
            ic_classes         = ["029"],
        ),
    ]

    _PHONETIC_RECORDS = [
        ConflictRecord(
            application_number = "765432198",
            mark_text          = "ADAMZ APPEL",
            status             = "pending",
            ic_classes         = ["029"],
        ),
    ]

    def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
        all_records: list[ConflictRecord] = []
        for query in queries:
            if query.query_type == "exact":
                records = [
                    ConflictRecord(**vars(r)) for r in self._EXACT_RECORDS
                ]
            elif query.query_type == "phonetic":
                records = [
                    ConflictRecord(**vars(r)) for r in self._PHONETIC_RECORDS
                ]
            else:
                records = []

            for rec in records:
                rec.surfaced_by_query_type = query.query_type

            all_records.extend(records)

        return self._dedup(all_records)


# ──────────────────────────────────────────────────────────────────────────────
# EMPTY MOCK — no conflicts found (clean search)
# ──────────────────────────────────────────────────────────────────────────────

class EmptyTessAdapter(TessAdapterBase):
    """Returns zero conflicts. Used to test clean-search paths."""

    def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURABLE MOCK — inject any conflict list at test time
# ──────────────────────────────────────────────────────────────────────────────

class ConfigurableMockAdapter(TessAdapterBase):
    """
    Returns whatever conflict list you hand it at construction time.
    Useful for parametric tests where you need precise control over results.

    Usage:
        adapter = ConfigurableMockAdapter([
            ConflictRecord(application_number="111", mark_text="ACME", ...),
        ])
        result = conduct_tmep_704_02_search(app, tess_adapter=adapter)
    """

    def __init__(self, conflicts: list[ConflictRecord]):
        self._conflicts = conflicts

    def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
        # Tag each record with the first query type (simulates real surfacing)
        first_type = queries[0].query_type if queries else "exact"
        for rec in self._conflicts:
            if not rec.surfaced_by_query_type:
                rec.surfaced_by_query_type = first_type
        return self._dedup(self._conflicts)
