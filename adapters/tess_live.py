# adapters/tess_live.py
"""
Live USPTO TESS Adapter
=======================
Calls the real USPTO Open Data Portal API to search trademark records.

API Details:
    Base URL  : https://data.uspto.gov/ds-api/trademark/v1/records
    Method    : GET
    Auth      : None required (public, free)
    Query lang: Apache SOLR / Lucene syntax
    Format    : JSON

This class REPLACES the stub UsptoTessAdapter from search_authority_engine.py.
The engine uses it via dependency injection — tests swap it for MockConflictAdapter.

Rate limits:
    USPTO enforces soft rate limits (~10 req/sec). The adapter uses a retry
    strategy with exponential backoff (configured in config.py).

Migration note:
    USPTO is migrating developer.uspto.gov → data.uspto.gov (early 2026).
    When that happens, update TESS_API_BASE_URL in config.py only.
    No code changes needed in this file.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config
from adapters.base import TessAdapterBase
from core.models import ConflictRecord, SearchQuery

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# HTTP SESSION FACTORY
# ──────────────────────────────────────────────────────────────────────────────

def _build_session() -> requests.Session:
    """
    Creates a requests.Session with:
      - Automatic retries on transient failures (5xx, connection errors)
      - Exponential backoff
      - Consistent headers
    """
    retry_strategy = Retry(
        total             = config.MAX_RETRIES,
        backoff_factor    = config.RETRY_BACKOFF_FACTOR,
        status_forcelist  = config.RETRY_ON_STATUS,
        allowed_methods   = ["GET", "POST"],
        raise_on_status   = False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    session.headers.update({
        "Accept":     "application/json",
        "User-Agent": config.USER_AGENT,
    })
    return session


# ──────────────────────────────────────────────────────────────────────────────
# LIVE ADAPTER
# ──────────────────────────────────────────────────────────────────────────────

class TessLiveAdapter(TessAdapterBase):
    """
    Calls the real USPTO Open Data Portal search API.

    Usage:
        adapter = TessLiveAdapter()
        conflicts = adapter.search(queries)

    Dependency injection in engine:
        result = conduct_tmep_704_02_search(app_data)
        # engine uses TessLiveAdapter() by default

    Override in tests:
        result = conduct_tmep_704_02_search(app_data, tess_adapter=MockConflictAdapter())
    """

    def __init__(self, base_url: str = config.TESS_API_BASE_URL):
        self._base_url = base_url
        self._session  = _build_session()

    # ── PUBLIC ────────────────────────────────────────────────────────────────

    def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
        """
        Executes each query against the USPTO API and returns deduplicated results.
        """
        all_records: list[ConflictRecord] = []

        for query in queries:
            logger.info(
                "Executing §704.02 query | type=%s | term=%s | solr=%s",
                query.query_type, query.search_term, query.solr_string,
            )
            records = self._execute_query(query)
            for rec in records:
                rec.surfaced_by_query_type = query.query_type
            all_records.extend(records)

        return self._dedup(all_records)

    # ── PRIVATE ───────────────────────────────────────────────────────────────

    def _execute_query(self, query: SearchQuery) -> list[ConflictRecord]:
        """
        Pages through all results for a single SOLR query.

        Handles:
          - Pagination (start / rows)
          - HTTP errors (logs + returns empty on failure rather than crashing)
          - Response parsing + normalization
        """
        records:  list[ConflictRecord] = []
        start:    int                  = 0

        for page in range(config.MAX_PAGES):
            params = {
                "criteria": query.solr_string,
                "start":    start,
                "rows":     config.PAGE_SIZE,
            }

            try:
                # response = self._session.post(
                #     self._base_url,
                #     json   = params,   # USPTO now expects JSON body
                #     timeout = config.REQUEST_TIMEOUT_SECONDS,
                # )
                response = self._session.get(
                    self._base_url,
                    params  = params,
                    timeout = config.REQUEST_TIMEOUT_SECONDS,
                )
            except requests.exceptions.ConnectionError as exc:
                logger.error("USPTO API connection error: %s", exc)
                break
            except requests.exceptions.Timeout:
                logger.error("USPTO API request timed out (timeout=%ss)", config.REQUEST_TIMEOUT_SECONDS)
                break

            if response.status_code != 200:
                logger.warning(
                    "USPTO API returned HTTP %s for query '%s'. Body: %s",
                    response.status_code, query.solr_string, response.text[:200],
                )
                break

            try:
                data = response.json()
            except ValueError:
                logger.error("USPTO API returned non-JSON response: %s", response.text[:200])
                break

            page_records = self._parse_response(data)
            records.extend(page_records)

            # Check if more pages exist
            total_found = self._total_found(data)
            logger.debug("Page %d | found %d of %d total", page + 1, len(page_records), total_found)

            if start + config.PAGE_SIZE >= total_found:
                break   # All pages consumed

            start += config.PAGE_SIZE

        return records

    def _parse_response(self, data: dict[str, Any]) -> list[ConflictRecord]:
        """
        Parses a USPTO API JSON response into a list of ConflictRecords.

        Expected response shape (USPTO Open Data Portal):
        {
          "response": {
            "numFound": 42,
            "docs": [
              {
                "serialNumber": "87654321",
                "markIdentification": "ADAMS APPLE",
                "statusCode": "700",
                "statusLabel": "Registered",
                "internationalClassCodes": ["029"],
                "filingDate": "2018-01-15",
                "registrationDate": "2019-06-04",
                "ownerName": "Acme Corp"
              },
              ...
            ]
          }
        }
        """
        docs: list[dict] = (
            data.get("response", {}).get("docs", [])
            or data.get("docs", [])        # Some API versions omit the "response" wrapper
        )

        records: list[ConflictRecord] = []
        for doc in docs:
            record = self._normalise_doc(doc)
            if record:
                records.append(record)

        return records

    def _normalise_doc(self, doc: dict[str, Any]) -> ConflictRecord | None:
        """
        Maps a raw USPTO API document to a ConflictRecord using config.FIELD_MAP.
        Returns None if the document is missing a serial number (unusable record).
        """
        app_number = (
            doc.get("serialNumber")
            or doc.get("serial_number")
            or doc.get(config.FIELD_MAP.get("serialNumber", "serialNumber"))
        )
        if not app_number:
            logger.debug("Skipping doc with no serialNumber: %s", doc)
            return None

        mark_text = (
            doc.get("markIdentification")
            or doc.get("mark_identification")
            or ""
        )

        status_code = str(doc.get("statusCode") or doc.get("status_code") or "")
        status = _resolve_status(status_code, doc.get("statusLabel", ""))

        ic_raw = doc.get("internationalClassCodes") or doc.get("ic_classes") or []
        ic_classes = ic_raw if isinstance(ic_raw, list) else [ic_raw]

        return ConflictRecord(
            application_number  = str(app_number),
            mark_text           = mark_text,
            status              = status,
            ic_classes          = [str(c) for c in ic_classes],
            registration_number = str(doc.get("registrationNumber") or ""),
            filing_date         = str(doc.get("filingDate")         or ""),
            registration_date   = str(doc.get("registrationDate")   or ""),
            owner_name          = str(doc.get("ownerName")          or ""),
        )

    @staticmethod
    def _total_found(data: dict[str, Any]) -> int:
        """Extracts total result count from the API response."""
        return int(
            data.get("response", {}).get("numFound", 0)
            or data.get("numFound", 0)
            or 0
        )


# ──────────────────────────────────────────────────────────────────────────────
# STATUS RESOLUTION HELPER
# ──────────────────────────────────────────────────────────────────────────────

def _resolve_status(status_code: str, status_label: str) -> str:
    """
    Maps a USPTO status code / label to our normalized status string.
    Falls back to inspecting the label text if the code is unknown.
    """
    if status_code in config.REGISTERED_STATUS_CODES:
        return "registered"
    if status_code in config.PENDING_STATUS_CODES:
        return "pending"

    # Fallback: inspect label text
    label_lower = status_label.lower()
    if "registered" in label_lower or "live" in label_lower:
        return "registered"
    if "pending" in label_lower or "filed" in label_lower or "published" in label_lower:
        return "pending"

    return "unknown"
