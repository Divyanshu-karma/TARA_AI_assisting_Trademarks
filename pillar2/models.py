# pillar2/models.py
# pillar2/models.py

from dataclasses import dataclass, field
from typing import List


@dataclass
class SubsectionFinding:
    tmep_section: str
    severity: str  # ERROR | WARNING | INFO | OK
    finding: str
    recommendation: str


@dataclass
class IdentificationAnalysis:
    is_definite: bool
    findings: List[SubsectionFinding] = field(default_factory=list)

    
# from dataclasses import dataclass, field
# from typing import List


# @dataclass
# class SubsectionFinding:
#     tmep_section: str
#     severity: str  # ERROR | WARNING | INFO | OK
#     item: str
#     finding: str
#     recommendation: str


# @dataclass
# class IdentificationAnalysis:
#     is_definite: bool
#     findings: List[SubsectionFinding]
#     reasoning: str
#     pillar1_note: str = ""