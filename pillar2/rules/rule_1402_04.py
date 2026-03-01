# pillar2/rules/rule_1402_04.py

from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_04(IdentificationRule):

    tmep_section = "§1402.04"

    def evaluate(self, text, context=None):

        # Placeholder for USPTO ID Manual integration.
        # In enterprise deployment, integrate ID Manual API or local DB validation.

        return SubsectionFinding(
            self.tmep_section,
            "INFO",
            "Automatic ID Manual conformity validation not enabled.",
            "Cross-check identification against USPTO ID Manual for exact matches."
        )