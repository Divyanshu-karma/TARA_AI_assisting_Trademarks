# pillar2/rules/rule_1402_01.py

from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_01(IdentificationRule):

    tmep_section = "§1402.01"

    def evaluate(self, text, context=None):

        if not text.strip():
            return SubsectionFinding(
                self.tmep_section,
                "ERROR",
                "Identification is blank.",
                "Provide specific goods/services."
            )

        segments = [s.strip() for s in text.split(";") if s.strip()]

        if not segments:
            return SubsectionFinding(
                self.tmep_section,
                "ERROR",
                "No separable goods/services identified.",
                "Separate items using semicolons."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            f"{len(segments)} item(s) identified.",
            "No action required."
        )