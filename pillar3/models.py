# pillar3/models.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ClassStatus(Enum):
    CLEAN = "CLEAN"
    HAS_WARNINGS = "HAS_WARNINGS"
    HAS_ERRORS = "HAS_ERRORS"
    REFUSAL_CANDIDATE = "REFUSAL_CANDIDATE"


class ApplicationStage(Enum):
    PRE_FILING = "PRE_FILING"
    FILED_PENDING = "FILED_PENDING"
    OFFICE_ACTION = "OFFICE_ACTION"
    STATEMENT_OF_USE = "STATEMENT_OF_USE"
    REGISTERED = "REGISTERED"
    POST_REGISTRATION = "POST_REGISTRATION"


@dataclass
class ClassSummary:
    class_number: int
    class_title: str
    class_category: str
    identification: str
    filing_basis: str
    specimen_type: str = ""
    specimen_description: str = ""
    date_of_first_use: Optional[str] = None
    date_of_first_use_commerce: Optional[str] = None
    fee_paid: bool = True

    # Pillar 1
    p1_error_count: int = 0
    p1_warning_count: int = 0
    p1_error_messages: List[str] = field(default_factory=list)

    # Pillar 2
    p2_is_definite: bool = True
    p2_error_count: int = 0
    p2_warning_count: int = 0
    p2_error_messages: List[str] = field(default_factory=list)

    status: ClassStatus = ClassStatus.CLEAN

    def has_any_error(self):
        return self.p1_error_count > 0 or self.p2_error_count > 0

    def is_use_based(self):
        return self.filing_basis in ("1(a)", "44(e)")

    def is_intent_to_use(self):
        return self.filing_basis == "1(b)"


@dataclass
class MultiClassApplicationContext:
    filing_type: str = "TEAS_PLUS"
    fees_paid_count: int = 0
    total_fee_paid: float = 0.0
    application_stage: ApplicationStage = ApplicationStage.FILED_PENDING
    amendment_requested: bool = False
    amendment_affects_classes: List[int] = field(default_factory=list)
    division_requested: bool = False
    classes_to_divide_out: List[int] = field(default_factory=list)
    surrender_requested: bool = False
    classes_to_surrender: List[int] = field(default_factory=list)
    fee_alignment_status: str = "aligned"   # add this field

@dataclass
class Pillar3Finding:
    tmep_section: str
    severity: str
    class_number: int
    finding: str
    recommendation: str


@dataclass
class Pillar3AssessmentResult:
    findings: List[Pillar3Finding]
    partial_refusal_classes: List[int]
    division_eligible_classes: List[int]
    total_errors: int
    total_warnings: int
    is_multi_class_compliant: bool
    fee_alignment_status:      str = "aligned" 