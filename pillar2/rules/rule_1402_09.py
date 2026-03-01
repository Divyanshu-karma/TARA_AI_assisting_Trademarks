# pillar2/rules/rule_1402_09.py

import re
from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_09(IdentificationRule):

    tmep_section = "§1402.09"

    def evaluate(self, text, context=None):

        if re.search(r"\b(applicant|registrant)\b", text, re.IGNORECASE):
            return SubsectionFinding(
                self.tmep_section,
                "ERROR",
                "Identification improperly references 'applicant' or 'registrant'.",
                "Remove such references. Identification must describe goods/services only."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            "No prohibited terms detected.",
            "No action required."
        )