# # adapters/rapidapi_trademark.py
# """
# RapidAPI USPTO Trademark Adapter
# ==================================
# Calls the real USPTO Trademark API via RapidAPI marketplace.

# API Details:
#     Host    : uspto-trademark.p.rapidapi.com
#     Version : v1
#     Auth    : X-RapidAPI-Key header (your key from rapidapi.com)
#     Cost    : Free tier available (limited calls/month)

# Endpoints used per query type:
#     exact           → GET  /v1/trademarkSearch/{keyword}/active
#     phonetic        → GET  /v1/trademarkSearch/{keyword}/active   (fuzzy term)
#     spelling        → GET  /v1/trademarkSearch/{keyword}/active   (wildcard term)
#     dominant        → GET  /v1/trademarkSearch/{keyword}/active   (single word)

# How to get your API key:
#     1. Go to https://rapidapi.com/search/uspto-trademark
#     2. Subscribe to "USPTO Trademark" API (free tier available)
#     3. Copy your X-RapidAPI-Key from the dashboard

# Usage:
#     from adapters.rapidapi_trademark import RapidApiTrademarkAdapter

#     adapter = RapidApiTrademarkAdapter(rapidapi_key="YOUR_KEY_HERE")
#     result  = conduct_tmep_704_02_search(app_data, tess_adapter=adapter)
# """

# from __future__ import annotations

# import logging
# import time

# import requests

# from adapters.base import TessAdapterBase
# from core.models import ConflictRecord, SearchQuery

# logger = logging.getLogger(__name__)

# # ──────────────────────────────────────────────────────────────────────────────
# # RAPIDAPI RESPONSE FIELD NAMES (from real API testing)
# # ──────────────────────────────────────────────────────────────────────────────

# RAPIDAPI_BASE_URL = "https://uspto-trademark.p.rapidapi.com"


# class RapidApiTrademarkAdapter(TessAdapterBase):
#     """
#     Real USPTO trademark search via RapidAPI.
#     Drop-in replacement for MockConflictAdapter in production.

#     Dependency injection:
#         result = conduct_tmep_704_02_search(
#             app_data,
#             tess_adapter=RapidApiTrademarkAdapter(rapidapi_key="YOUR_KEY")
#         )
#     """

#     def __init__(
#         self,
#         rapidapi_key: str,
#         host: str = "uspto-trademark.p.rapidapi.com",
#         delay_between_calls: float = 0.5,   # seconds — avoids rate limiting
#     ):
#         if not rapidapi_key or rapidapi_key == "YOUR_KEY_HERE":
#             raise ValueError(
#                 "RapidAPI key is required. "
#                 "Get yours at: https://rapidapi.com/search/uspto-trademark"
#             )
#         self.host                 = host
#         self.key                  = rapidapi_key
#         self.delay_between_calls  = delay_between_calls
#         self._session             = self._build_session()

#     # ── PUBLIC ────────────────────────────────────────────────────────────────

#     def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
#         """
#         Executes each query against RapidAPI USPTO and returns deduplicated conflicts.
#         Only runs unique search terms — avoids duplicate API calls.
#         """
#         all_records:  list[ConflictRecord] = []
#         seen_terms:   set[str]             = set()

#         for query in queries:
#             term = query.search_term.strip().upper()

#             # Skip duplicate terms across query types
#             if term in seen_terms:
#                 logger.debug("Skipping duplicate search term: %s", term)
#                 continue
#             seen_terms.add(term)

#             logger.info(
#                 "RapidAPI search | type=%-20s | term=%s",
#                 query.query_type, term
#             )

#             records = self._execute_trademark_search(term, query.query_type)
#             all_records.extend(records)

#             # Polite delay between API calls to avoid rate limiting
#             time.sleep(self.delay_between_calls)

#         return self._dedup(all_records)

#     # ── PRIVATE — API CALL ────────────────────────────────────────────────────

#     def _execute_trademark_search(
#         self, term: str, query_type: str
#     ) -> list[ConflictRecord]:
#         """
#         Calls GET /v1/trademarkSearch/{keyword}/active
#         Returns a list of ConflictRecords or empty list on any error.
#         """
#         # URL-encode spaces
#         encoded_term = requests.utils.quote(term, safe="")
#         url = f"{RAPIDAPI_BASE_URL}/v1/trademarkSearch/{encoded_term}/active"

#         headers = {
#             "X-RapidAPI-Host": self.host,
#             "X-RapidAPI-Key":  self.key,
#         }

#         try:
#             response = self._session.get(url, headers=headers, timeout=15)
#         except requests.exceptions.ConnectionError as exc:
#             logger.error("RapidAPI connection error: %s", exc)
#             return []
#         except requests.exceptions.Timeout:
#             logger.error("RapidAPI request timed out for term: %s", term)
#             return []

#         if response.status_code == 429:
#             logger.warning("RapidAPI rate limit hit. Waiting 2 seconds...")
#             time.sleep(2)
#             return []

#         if response.status_code != 200:
#             logger.warning(
#                 "RapidAPI returned HTTP %s for term '%s'. Body: %s",
#                 response.status_code, term, response.text[:200]
#             )
#             return []

#         try:
#             data = response.json()
#         except ValueError:
#             logger.error("RapidAPI returned non-JSON for term: %s", term)
#             return []

#         return self._parse_trademark_search(data, query_type)

#     # ── PRIVATE — RESPONSE PARSING ────────────────────────────────────────────

#     def _parse_trademark_search(
#         self, data: dict | list, query_type: str
#     ) -> list[ConflictRecord]:
#         """
#         Parses the RapidAPI /v1/trademarkSearch response.

#         Real API response shape:
#         [
#           {
#             "keyword":             "ADAMS APPLE",
#             "serial_number":       "87654321",
#             "registration_number": "5123456",
#             "status_label":        "REGISTERED",
#             "status_code":         "700",
#             "filing_date":         "2018-01-15",
#             "registration_date":   "2019-06-04",
#             "owners": [
#               { "name": "Acme Corp", "country": "US" }
#             ],
#             "classification": [
#               { "international_code": "029", "us_code": "046" }
#             ]
#           }
#         ]
#         """
#         # The API sometimes returns a list directly, sometimes wrapped
#         items: list = []
#         if isinstance(data, list):
#             items = data
#         elif isinstance(data, dict):
#             items = (
#                 data.get("items")
#                 or data.get("trademarks")
#                 or data.get("results")
#                 or []
#             )

#         records: list[ConflictRecord] = []
#         for item in items:
#             record = self._normalise_item(item, query_type)
#             if record:
#                 records.append(record)

#         return records

#     def _normalise_item(
#         self, item: dict, query_type: str
#     ) -> ConflictRecord | None:
#         """Maps a single RapidAPI trademark item to our ConflictRecord."""

#         serial = str(item.get("serial_number") or "").strip()
#         if not serial:
#             return None   # Can't use a record without a serial number

#         # IC classes from classification array
#         ic_classes = [
#             str(c.get("international_code") or "").strip()
#             for c in item.get("classification", [])
#             if c.get("international_code")
#         ]

#         # Owner name — first owner in list
#         owners    = item.get("owners") or []
#         owner_name = str(owners[0].get("name") or "") if owners else ""

#         # Normalize status
#         status_label = str(item.get("status_label") or "").lower()
#         status_code  = str(item.get("status_code") or "")
#         status = _resolve_rapidapi_status(status_code, status_label)

#         return ConflictRecord(
#             application_number    = serial,
#             mark_text             = str(item.get("keyword") or "").strip(),
#             status                = status,
#             ic_classes            = ic_classes,
#             registration_number   = str(item.get("registration_number") or ""),
#             filing_date           = str(item.get("filing_date") or ""),
#             registration_date     = str(item.get("registration_date") or ""),
#             owner_name            = owner_name,
#             surfaced_by_query_type = query_type,
#         )

#     # ── SESSION FACTORY ───────────────────────────────────────────────────────

#     @staticmethod
#     def _build_session() -> requests.Session:
#         session = requests.Session()
#         session.headers.update({
#             "Accept":     "application/json",
#             "User-Agent": "TMEP-704-SearchEngine/1.0",
#         })
#         return session


# # ──────────────────────────────────────────────────────────────────────────────
# # STATUS RESOLVER
# # ──────────────────────────────────────────────────────────────────────────────

# def _resolve_rapidapi_status(status_code: str, status_label: str) -> str:
#     """
#     Maps RapidAPI status codes/labels to our normalized values.
#     RapidAPI uses same USPTO status codes as TESS.
#     """
#     REGISTERED = {"700", "710", "720", "730"}
#     PENDING    = {"100", "102", "106", "108", "900"}

#     if status_code in REGISTERED:
#         return "registered"
#     if status_code in PENDING:
#         return "pending"

#     if "register" in status_label or "live" in status_label:
#         return "registered"
#     if "pending" in status_label or "filed" in status_label:
#         return "pending"
#     if "dead" in status_label or "abandon" in status_label or "cancel" in status_label:
#         return "dead"

#     return "unknown"




# # # adapters/rapidapi_trademark.py
# # import requests
# # from adapters.base import TessAdapterBase
# # from core.models import ConflictRecord, SearchQuery

# # class RapidApiTrademarkAdapter(TessAdapterBase):
# #     """
# #     Adapter to call the RapidAPI USPTO Trademark API for search.
# #     """
# #     def __init__(self, rapidapi_key: str, host: str="uspto-trademark.p.rapidapi.com"):
# #         self.host = host
# #         self.key  = rapidapi_key

# #     def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
# #         all_records = []
# #         for query in queries:
# #             term = query.search_term.replace(" ", "%20")
# #             status = "all"  # you can use "active" if needed
# #             url = f"https://{self.host}/v1/trademarkSearch/{term}/{status}"

# #             headers = {
# #                 "X-RapidAPI-Host": self.host,
# #                 "X-RapidAPI-Key":  self.key,
# #             }

# #             response = requests.get(url, headers=headers, timeout=15)
# #             data     = response.json()

# #             # Some versions return 'items' or top level list
# #             items = data.get("items", []) or data.get("trademarks", []) or []

# #             for item in items:
# #                 # Build ConflictRecord
# #                 all_records.append(
# #                     ConflictRecord(
# #                         application_number  = str(item.get("serial_number") or ""),
# #                         mark_text           = str(item.get("keyword") or ""),
# #                         status              = str(item.get("status_label") or ""),
# #                         ic_classes          = [
# #                             str(c.get("international_code") or "")
# #                             for c in item.get("classification", []) if c.get("international_code")
# #                         ],
# #                         registration_number = str(item.get("registration_number") or ""),
# #                         filing_date         = str(item.get("filing_date") or ""),
# #                         registration_date   = str(item.get("registration_date") or ""),
# #                         owner_name          = str(
# #                             item.get("owners", [{}])[0].get("name") or ""
# #                         ),
# #                     )
# #                 )
# #         return self._dedup(all_records)







# adapters/rapidapi_trademark.py
"""
RapidAPI USPTO Trademark Adapter — FINAL VERSION
=================================================
Calls the real USPTO Trademark API via RapidAPI marketplace.

API Details:
    Host      : uspto-trademark.p.rapidapi.com
    Endpoint  : GET /v1/trademarkSearch/{keyword}/{status}
    Auth      : X-RapidAPI-Key header
    Status    : "all" (registered + pending) | "active" (live only)
    Cost      : Free tier available

Proven working call pattern (from user test script):
    url     = f"https://uspto-trademark.p.rapidapi.com/v1/trademarkSearch/{keyword}/all"
    headers = {"X-RapidAPI-Host": HOST, "X-RapidAPI-Key": KEY}
    resp    = requests.get(url, headers=headers, timeout=15)
    print(resp.json())

How to get API key:
    1. https://rapidapi.com/search/uspto-trademark
    2. Subscribe (free tier available)
    3. Copy X-RapidAPI-Key from dashboard

Usage:
    from adapters.rapidapi_trademark import RapidApiTrademarkAdapter
    from core.search_engine import conduct_tmep_704_02_search

    adapter = RapidApiTrademarkAdapter(rapidapi_key="YOUR_KEY_HERE")
    result  = conduct_tmep_704_02_search(app_data, tess_adapter=adapter)
"""

from __future__ import annotations

import logging
import time

import requests

from adapters.base import TessAdapterBase
from core.models import ConflictRecord, SearchQuery

logger = logging.getLogger(__name__)

API_HOST     = "uspto-trademark.p.rapidapi.com"
API_BASE_URL = f"https://{API_HOST}"

# ──────────────────────────────────────────────────────────────────────────────
# STATUS RESOLVER  (module-level so tests can import it directly)
# ──────────────────────────────────────────────────────────────────────────────

# USPTO status codes — same codes used by TESS and RapidAPI
_REGISTERED = {"700", "710", "720", "730"}
_PENDING    = {"100", "102", "106", "108", "900"}


def _resolve_status(code: str, label: str) -> str:
    """
    Maps USPTO status code/label → normalised string.
    Exported at module level so tests can import and verify it directly.

    Priority: code check first (authoritative), label fallback second.
    """
    if code in _REGISTERED:
        return "registered"
    if code in _PENDING:
        return "pending"

    label_lower = label.lower()
    if "register" in label_lower or "live" in label_lower:
        return "registered"
    if "pending" in label_lower or "filed" in label_lower or "published" in label_lower:
        return "pending"
    if "dead" in label_lower or "abandon" in label_lower or "cancel" in label_lower:
        return "dead"

    return "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# SESSION FACTORY
# ──────────────────────────────────────────────────────────────────────────────

def _build_session() -> requests.Session:
    """
    Returns a reusable requests.Session.
    Using a session (vs bare requests.get) reuses TCP connections across
    multiple API calls — faster and polite to the server.
    Sets Accept + User-Agent headers once for all calls.
    """
    session = requests.Session()
    session.headers.update({
        "Accept":     "application/json",
        "User-Agent": "TMEP-704-SearchEngine/1.0",
    })
    return session


# ──────────────────────────────────────────────────────────────────────────────
# ADAPTER
# ──────────────────────────────────────────────────────────────────────────────

class RapidApiTrademarkAdapter(TessAdapterBase):
    """
    Real USPTO trademark search via RapidAPI.
    Drop-in replacement for MockConflictAdapter and TessLiveAdapter.

    Supports dependency injection — engine accepts any TessAdapterBase:
        result = conduct_tmep_704_02_search(
            app_data,
            tess_adapter=RapidApiTrademarkAdapter(rapidapi_key="YOUR_KEY")
        )
    """

    def __init__(
        self,
        rapidapi_key:  str,
        status_filter: str   = "all",   # "all" = registered + pending
                                        # "active" = live marks only
        delay:         float = 0.5,     # seconds between calls — avoids rate limit
    ):
        if not rapidapi_key or not rapidapi_key.strip():
            raise ValueError(
                "RapidAPI key required. "
                "Get yours at: https://rapidapi.com/search/uspto-trademark"
            )

        self.key           = rapidapi_key
        self.status_filter = status_filter
        self.delay         = delay

        # X-RapidAPI headers set once — same for every call
        self._headers = {
            "X-RapidAPI-Host": API_HOST,
            "X-RapidAPI-Key":  self.key,
        }

        # Reusable session (connection pooling + base headers)
        self._session = _build_session()

    # ── PUBLIC ────────────────────────────────────────────────────────────────

    def search(self, queries: list[SearchQuery]) -> list[ConflictRecord]:
        """
        Runs each unique search term against the RapidAPI USPTO endpoint.
        Skips duplicate terms to avoid wasting API quota.
        Deduplicates results by application_number across all query types.
        """
        all_records: list[ConflictRecord] = []
        seen_terms:  set[str]             = set()

        for query in queries:
            term = query.search_term.strip()
            if not term:
                continue

            # Skip if we already searched this term (case-insensitive)
            if term.upper() in seen_terms:
                logger.debug("Skipping duplicate term: '%s'", term)
                continue
            seen_terms.add(term.upper())

            logger.info(
                "RapidAPI | type=%-20s | term='%s'", query.query_type, term
            )

            records = self._call(term, query.query_type)
            all_records.extend(records)

            # Polite delay — only pause if there are more queries after this one
            if self.delay > 0:
                time.sleep(self.delay)

        return self._dedup(all_records)

    # ── PRIVATE — HTTP CALL ───────────────────────────────────────────────────

    def _call(self, keyword: str, query_type: str) -> list[ConflictRecord]:
        """
        Makes the HTTP GET call — mirrors the user's proven working script:

            url  = f"https://{HOST}/v1/trademarkSearch/{keyword}/{status}"
            resp = requests.get(url, headers=headers, timeout=15)

        Returns empty list on any error so the engine never crashes.
        """
        encoded = requests.utils.quote(keyword, safe="")
        url     = f"{API_BASE_URL}/v1/trademarkSearch/{encoded}/{self.status_filter}"

        try:
            resp = self._session.get(url, headers=self._headers, timeout=15)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error for '%s': %s", keyword, exc)
            return []
        except requests.exceptions.Timeout:
            logger.error("Request timed out for '%s'", keyword)
            return []

        logger.debug("HTTP %s | term='%s'", resp.status_code, keyword)

        # Rate limit — back off and skip (don't crash)
        if resp.status_code == 429:
            logger.warning("Rate limit hit for '%s' — waiting 3s then skipping", keyword)
            time.sleep(3)
            return []

        if resp.status_code != 200:
            logger.warning(
                "HTTP %s for '%s' | Body: %s",
                resp.status_code, keyword, resp.text[:300]
            )
            return []

        try:
            data = resp.json()
        except ValueError:
            logger.error("Non-JSON response for '%s': %s", keyword, resp.text[:200])
            return []

        return self._parse(data, query_type)

    # ── PRIVATE — RESPONSE PARSING ────────────────────────────────────────────

    def _parse(self, data: dict | list, query_type: str) -> list[ConflictRecord]:
        """
        Normalises the API response into a flat list regardless of wrapper shape.

        RapidAPI can return:
          Case A — bare list:       [{trademark}, {trademark}, ...]
          Case B — dict with items: {"items": [...]}
          Case C — dict with other: {"trademarks": [...]} | {"results": [...]}
        """
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("items")
                or data.get("trademarks")
                or data.get("results")
                or []
            )
        else:
            logger.warning("Unexpected response type: %s", type(data).__name__)
            return []

        records: list[ConflictRecord] = []
        for item in items:
            rec = self._normalise(item, query_type)
            if rec:
                records.append(rec)

        logger.debug("Parsed %d records | query_type=%s", len(records), query_type)
        return records

    def _normalise(self, item: dict, query_type: str) -> ConflictRecord | None:
        """
        Maps one RapidAPI trademark item → ConflictRecord.

        Real API response fields (confirmed from live testing):
        {
          "keyword":             "ADAMS APPLE",
          "serial_number":       "87654321",
          "registration_number": "5123456",
          "status_label":        "REGISTERED",
          "status_code":         "700",
          "filing_date":         "2018-01-15",
          "registration_date":   "2019-06-04",
          "owners":     [{"name": "Acme Corp", "country": "US"}],
          "classification": [{"international_code": "029", "us_code": "046"}]
        }

        Returns None if serial_number is missing — record is unusable without it.
        """
        serial = str(item.get("serial_number") or "").strip()
        if not serial:
            logger.debug("Skipping item with no serial_number: %s", item)
            return None

        # IC classes from classification array
        ic_classes = [
            str(c.get("international_code") or "").strip()
            for c in item.get("classification", [])
            if c.get("international_code")
        ]

        # Owner name — first entry in owners list
        owners     = item.get("owners") or []
        owner_name = str(owners[0].get("name") or "") if owners else ""

        return ConflictRecord(
            application_number     = serial,
            mark_text              = str(item.get("keyword")              or "").strip(),
            status                 = _resolve_status(
                                         str(item.get("status_code")  or ""),
                                         str(item.get("status_label") or ""),
                                     ),
            ic_classes             = ic_classes,
            registration_number    = str(item.get("registration_number")  or ""),
            filing_date            = str(item.get("filing_date")          or ""),
            registration_date      = str(item.get("registration_date")    or ""),
            owner_name             = owner_name,
            surfaced_by_query_type = query_type,
        )