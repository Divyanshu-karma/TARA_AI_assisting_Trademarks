# pillar2/rules/rule_1402_11.py

import re
from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_11(IdentificationRule):

    tmep_section = "§1402.11"

    def evaluate(self, text, context=None):

        if context and context.class_category != "SERVICES":
            return SubsectionFinding(
                self.tmep_section,
                "INFO",
                "Goods class — services rule not applicable.",
                "No action required."
            )

        if re.search(r"\b(our|my|internal|company's)\b", text, re.IGNORECASE):
            return SubsectionFinding(
                self.tmep_section,
                "ERROR",
                "Service identification appears to describe internal activities.",
                "Rewrite to describe services rendered for others."
            )

        if not re.search(r"\b(providing|rendering|offering|for others)\b", text, re.IGNORECASE):
            return SubsectionFinding(
                self.tmep_section,
                "WARNING",
                "Service identification may not clearly indicate activity performed for others.",
                "Add wording such as 'providing services for others'."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            "Service identification properly formatted.",
            "No action required."
        )