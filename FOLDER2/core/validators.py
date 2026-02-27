# core/validators.py
"""
Input validation and trigger-gate logic.

Moved from search_authority_engine.py — same rules, now with typed returns
so the engine receives ApplicationPayload instead of raw dicts.
"""

from __future__ import annotations

from core.models import (
    ApplicationPayload,
    GoodsServices,
    SEARCH_TRIGGER_EVENTS,
    RE_SEARCH_TRIGGERS,
    LEGAL_BASIS_REVIVAL,
)


# ──────────────────────────────────────────────────────────────────────────────
# EXCEPTIONS
# ──────────────────────────────────────────────────────────────────────────────

class ApplicationValidationError(ValueError):
    """Raised when the incoming application payload fails schema validation."""


class SearchNotRequiredError(Exception):
    """
    Raised when the supplied event trigger does not legally mandate
    a §704.02 search. Prevents unnecessary or erroneous search records.
    """


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED FIELD SCHEMA
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS: dict[str, type] = {
    "application_id": str,
    "mark_text":      str,
    "mark_type":      str,
    "goods_services": list,
    "event_trigger":  str,
}


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC VALIDATORS
# ──────────────────────────────────────────────────────────────────────────────

def validate_and_parse(raw: dict) -> ApplicationPayload:
    """
    Validates the raw application dict and returns a typed ApplicationPayload.

    Raises:
        ApplicationValidationError — missing fields, wrong types, empty values.
    """
    # 1. Field presence + type check
    for field_name, expected_type in REQUIRED_FIELDS.items():
        if field_name not in raw:
            raise ApplicationValidationError(
                f"Missing required field: '{field_name}'. "
                f"§704.02 search cannot proceed without complete application data."
            )
        if not isinstance(raw[field_name], expected_type):
            raise ApplicationValidationError(
                f"Field '{field_name}' must be of type {expected_type.__name__}. "
                f"Received: {type(raw[field_name]).__name__}."
            )

    # 2. Non-empty string checks
    if not raw["mark_text"].strip():
        raise ApplicationValidationError("'mark_text' must not be empty.")

    # 3. Non-empty list check
    if not raw["goods_services"]:
        raise ApplicationValidationError("'goods_services' list must not be empty.")

    # 4. Build typed payload
    return ApplicationPayload(
        application_id     = raw["application_id"],
        mark_text          = raw["mark_text"].strip(),
        mark_type          = raw["mark_type"],
        goods_services     = [GoodsServices.from_dict(g) for g in raw["goods_services"]],
        event_trigger      = raw["event_trigger"].lower(),
        application_status = raw.get("application_status", ""),
    )


def is_search_required(event_trigger: str) -> bool:
    """
    Returns True if the event legally mandates a §704.02 search.
    Case-insensitive.
    """
    return event_trigger.lower() in SEARCH_TRIGGER_EVENTS


def assert_search_required(event_trigger: str) -> None:
    """
    Raises SearchNotRequiredError if event_trigger does not mandate a search.
    Used as a guard at the top of the engine.
    """
    if not is_search_required(event_trigger):
        raise SearchNotRequiredError(
            f"Event trigger '{event_trigger}' does not mandate a §704.02 search. "
            f"Required triggers: {sorted(SEARCH_TRIGGER_EVENTS)}"
        )


def evaluate_re_search(event_trigger: str) -> tuple[bool, str | None]:
    """
    Determines if a re-search flag is required per TMEP §718.07.

    Returns:
        (re_search_required: bool, legal_basis: str | None)
    """
    if event_trigger.lower() in RE_SEARCH_TRIGGERS:
        return True, LEGAL_BASIS_REVIVAL
    return False, None
