# pillar2/rules/rule_1402_12.py

import re
from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_12(IdentificationRule):

    tmep_section = "§1402.12"

    def evaluate(self, text, context=None):

        if re.search(r"[()\[\]{}]", text):
            return SubsectionFinding(
                self.tmep_section,
                "ERROR",
                "Parentheses or brackets detected in identification.",
                "Remove parentheses and brackets; rewrite text directly."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            "No prohibited punctuation detected.",
            "No action required."
        )