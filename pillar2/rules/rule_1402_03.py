# pillar2/rules/rule_1402_03.py

import re
from pillar2.rules.base_rule import IdentificationRule
from pillar2.models import SubsectionFinding


class Rule1402_03(IdentificationRule):

    tmep_section = "§1402.03"

    SEVERE_VAGUE_TERMS = [
        "miscellaneous",
        "various",
        "all types",
        "any and all",
        "etc",
        "etc."
    ]

    CONTEXTUAL_TERMS = [
        "technology",
        "equipment",
        "devices",
        "systems",
        "platform"
    ]

    def evaluate(self, text, context=None):

        text_lower = text.lower()

        severe_found = [
            term for term in self.SEVERE_VAGUE_TERMS
            if re.search(rf"\b{term}\b", text_lower)
        ]

        if severe_found:
            return SubsectionFinding(
                self.tmep_section,
                "ERROR",
                f"Indefinite terminology detected: {', '.join(severe_found)}.",
                "Replace with specific, enumerated goods/services."
            )

        contextual_found = [
            term for term in self.CONTEXTUAL_TERMS
            if re.search(rf"\b{term}\b", text_lower)
        ]

        if contextual_found and not re.search(r"\b(for|namely|consisting|in the field of|used for)\b", text_lower):
            return SubsectionFinding(
                self.tmep_section,
                "WARNING",
                f"Context-dependent terminology detected: {', '.join(contextual_found)}.",
                "Add purpose qualifier (e.g., 'namely' clause) for clarity."
            )

        return SubsectionFinding(
            self.tmep_section,
            "OK",
            "Identification wording appears sufficiently specific.",
            "No action required."
        )