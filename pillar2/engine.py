# # pillar2/engine.py

# from typing import List
# from pillar2.models import IdentificationAnalysis
# from pillar2.rules.rule_1402_03 import Rule1402_03
# from pillar2.rules.rule_1402_10 import Rule1402_10


# class IdentificationEngine:

#     def __init__(self):
#         self.rules = [
#             Rule1402_03(),
#             Rule1402_10(),
#             # Add more rules here
#         ]

#     def run(self, text: str, context=None) -> IdentificationAnalysis:

#         findings = []
#         for rule in self.rules:
#             result = rule.evaluate(text, context)
#             findings.append(result)

#         errors = [f for f in findings if f.severity == "ERROR"]

#         is_definite = len(errors) == 0

#         reasoning = (
#             "Identification satisfies §1402 standards."
#             if is_definite
#             else "Identification contains errors under §1402."
#         )

#         return IdentificationAnalysis(
#             is_definite=is_definite,
#             findings=findings,
#             reasoning=reasoning
#         )

# pillar2/engine.py

from pillar2.models import IdentificationAnalysis
from pillar2.rules.rule_1402_01 import Rule1402_01
from pillar2.rules.rule_1402_02 import Rule1402_02
from pillar2.rules.rule_1402_03 import Rule1402_03
from pillar2.rules.rule_1402_04 import Rule1402_04
from pillar2.rules.rule_1402_05 import Rule1402_05
from pillar2.rules.rule_1402_09 import Rule1402_09
from pillar2.rules.rule_1402_10 import Rule1402_10
from pillar2.rules.rule_1402_11 import Rule1402_11
from pillar2.rules.rule_1402_12 import Rule1402_12


class Pillar2Engine:

    def __init__(self):
        self.rules = [
            Rule1402_01(),
            Rule1402_02(),
            Rule1402_03(),
            Rule1402_04(),
            Rule1402_05(),
            Rule1402_09(),
            Rule1402_10(),
            Rule1402_11(),
            Rule1402_12(),
        ]

    def analyze(self, text, context=None):

        findings = [rule.evaluate(text, context) for rule in self.rules]

        errors = [f for f in findings if f.severity == "ERROR"]

        return IdentificationAnalysis(
            is_definite=len(errors) == 0,
            findings=findings
        )