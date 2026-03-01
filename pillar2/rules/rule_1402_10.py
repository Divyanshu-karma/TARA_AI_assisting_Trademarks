# pillar2/rules/rule_1402_10.py

import re
from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_10(IdentificationRule):

    tmep_section = "§1402.10"

    def evaluate(self, text, context=None):

        if not context or context.filing_basis != "1(b)":
            return SubsectionFinding(
                self.tmep_section,
                "INFO",
                "Not a §1(b) application.",
                "No action required."
            )

        if re.search(r"\b(will|intend|planning to|proposed|future)\b", text, re.IGNORECASE):
            return SubsectionFinding(
                self.tmep_section,
                "WARNING",
                "Future-tense or speculative language detected in §1(b) identification.",
                "State goods/services definitively; remove speculative wording."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            "§1(b) identification format acceptable.",
            "No action required."
        )