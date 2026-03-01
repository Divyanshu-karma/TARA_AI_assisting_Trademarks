# config.py
"""
Central configuration for the TMEP §704.02 Search Authority Engine.
All external URLs and tunable constants live here — never scattered in logic files.
"""

# ──────────────────────────────────────────────────────────────────────────────
# USPTO API — Open Data Portal (SOLR / Lucene backend)
# Free, publicly accessible, no API key required for search queries.
# Official docs: https://developer.uspto.gov/api-catalog
# Migration note: USPTO is migrating to data.uspto.gov in early 2026.
#                 PRIMARY_URL will be updated once the new endpoint is live.
# ──────────────────────────────────────────────────────────────────────────────

# Primary: USPTO Open Data Portal trademark search (SOLR)
# TESS_API_BASE_URL = "https://developer.uspto.gov/ds-api/oa_tm/v1/records"
TESS_API_BASE_URL = "https://data.uspto.gov/ds-api/trademark/v1/records"
# Fallback: New Open Data Portal (2026 migration target)
TESS_API_FALLBACK_URL = "https://data.uspto.gov/ds-api/trademark/v1/records"

# TSDR API for status lookup by serial number
TSDR_API_BASE_URL = "https://tsdrapi.uspto.gov/ts/cd/casestatus/sn{serial_number}/info.xml"

# ──────────────────────────────────────────────────────────────────────────────
# HTTP CLIENT SETTINGS
# ──────────────────────────────────────────────────────────────────────────────

# Seconds before a single HTTP request times out
REQUEST_TIMEOUT_SECONDS = 15

# Total retries on transient failures (5xx, connection errors)
MAX_RETRIES = 3

# Seconds to wait between retries (exponential: 1s, 2s, 4s)
RETRY_BACKOFF_FACTOR = 1.0

# HTTP status codes that trigger a retry
RETRY_ON_STATUS = [429, 500, 502, 503, 504]

# ──────────────────────────────────────────────────────────────────────────────
# SEARCH RESULT PAGING
# ──────────────────────────────────────────────────────────────────────────────

# Max records per page from the API
PAGE_SIZE = 50

# Maximum pages to fetch per query (safety cap — prevents runaway pagination)
MAX_PAGES = 3   # → ceiling of 150 records per variation-type query

# ──────────────────────────────────────────────────────────────────────────────
# RESPONSE FIELD MAPPING
# Maps USPTO API JSON field names → our internal ConflictRecord field names
# Update here if USPTO renames fields in a future API version.
# ──────────────────────────────────────────────────────────────────────────────

FIELD_MAP = {
    "serialNumber":              "application_number",
    "markIdentification":        "mark_text",
    "registrationNumber":        "registration_number",
    "statusCode":                "status_code",
    "statusLabel":               "status_label",
    "internationalClassCodes":   "ic_classes",
    "filingDate":                "filing_date",
    "registrationDate":          "registration_date",
    "ownerName":                 "owner_name",
}

# Status codes the API returns that map to "registered"
REGISTERED_STATUS_CODES = {"700", "710", "720", "730"}

# Status codes that map to "pending"
PENDING_STATUS_CODES = {"100", "102", "106", "108", "900"}

# ──────────────────────────────────────────────────────────────────────────────
# USER AGENT — identifies our tool to USPTO servers
# ──────────────────────────────────────────────────────────────────────────────
USER_AGENT = "TMEP-704-SearchEngine/1.0 (USPTO Examination Tool)"
