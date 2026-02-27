# adapters/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from core.models import ConflictRecord, SearchQuery

class TessAdapterBase(ABC):

    @abstractmethod
    def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
        ...

    def _dedup(self, records: list[ConflictRecord]) -> list[ConflictRecord]:
        seen: set[str] = set()
        result: list[ConflictRecord] = []
        for rec in records:
            if rec.application_number and rec.application_number not in seen:
                seen.add(rec.application_number)
                result.append(rec)
        return result