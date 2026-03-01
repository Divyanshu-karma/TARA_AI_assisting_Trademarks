# pillar2/rules/rule_1402_05.py

import re
from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_05(IdentificationRule):

    tmep_section = "§1402.05"

    def evaluate(self, text, context=None):

        if not context or not context.specimen_description:
            return SubsectionFinding(
                self.tmep_section,
                "INFO",
                "No specimen available.",
                "Verify accuracy during examination."
            )

        id_words = set(re.findall(r"\b\w{4,}\b", text.lower()))
        spec_words = set(re.findall(r"\b\w{4,}\b", context.specimen_description.lower()))

        if len(id_words & spec_words) == 0:
            return SubsectionFinding(
                self.tmep_section,
                "WARNING",
                "Identification may not match specimen.",
                "Review for overbreadth."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            "Identification consistent with specimen.",
            "No action required."
        )