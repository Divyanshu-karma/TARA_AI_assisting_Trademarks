# pillar2/rules/rule_1402_02.py

from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_02(IdentificationRule):

    tmep_section = "§1402.02"

    def evaluate(self, text, context=None):

        placeholders = ["tbd", "to be determined", "see attached"]

        if any(p in text.lower() for p in placeholders):
            return SubsectionFinding(
                self.tmep_section,
                "ERROR",
                "Placeholder language present.",
                "Replace with definite goods/services."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            "Identification sufficient for filing date.",
            "No action required."
        )